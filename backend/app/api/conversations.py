"""Conversation history API router."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import Character, CharacterQuest, Quest, QuestState
from app.observability.logger import get_logger, log_context
from app.schemas.dm_response import DMResponse, PlayerActionRequest, RollRequest
from app.schemas.message import (
    ConversationHistoryResponse,
    MessageCreate,
    MessageResponse,
)
from app.services.context_window_manager import get_context_manager
from app.services.conversation_service import ConversationService
from app.services.dm_engine import DMEngine
from app.services.image_service import ImageService
from app.services.memory_capture import MemoryCaptureService
from app.services.redis_service import session_service
from app.services.roll_executor import RollExecutor
from app.services.roll_parser import RollParser
from app.services.summarization_service import SummarizationService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("/messages", response_model=MessageResponse, status_code=201)
async def create_message(
    message_data: MessageCreate,
    save_to_redis: bool = Query(True, description="Also save to Redis"),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation message.

    Args:
        message_data: Message data
        save_to_redis: Whether to also save to Redis
        db: Database session

    Returns:
        Created message
    """
    # Save to PostgreSQL
    message = await ConversationService.create_message(db, message_data)

    # Optionally save to Redis for active session
    if save_to_redis:
        await session_service.add_message_to_history(
            session_id=message_data.session_id,
            role=message_data.role,
            content=message_data.content,
            tokens_used=message_data.tokens_used,
        )

    return message


@router.post("/start", response_model=DMResponse)
async def start_conversation(
    request: dict,
    db: AsyncSession = Depends(get_db),
):
    """Start a new conversation session with opening narration.

    Args:
        request: Dict with session_id
        db: Database session

    Returns:
        DM response with opening narration
    """
    session_id = UUID(request.get("session_id"))
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    # Check if there are existing messages - if yes, this isn't a new session
    existing_messages = await ConversationService.get_recent_messages(db, session_id, count=1)
    if existing_messages:
        raise HTTPException(
            status_code=400,
            detail="Session already has messages. Use /action endpoint for continued conversation.",
        )

    # Get the session to find the adventure
    from app.db.models import GameSession

    result = await db.execute(select(GameSession).where(GameSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get character for context
    result = await db.execute(select(Character).where(Character.id == session.character_id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Check if this session was created from a custom adventure
    # by checking the adventure_select page which passes the adventure in the redirect
    # For now, we'll create a generic opening based on location
    opening_narration = (
        f"Welcome, {character.name}!\n\n"
        f"You find yourself at {session.current_location or 'the beginning of your journey'}. "
        f"As a level {character.level} {character.race.value} {character.character_class.value}, "
        f"you are ready for whatever challenges lie ahead.\n\n"
        f"What would you like to do?"
    )

    # Save the opening message
    dm_msg = MessageCreate(
        session_id=session_id,
        role="assistant",
        content=opening_narration,
        tokens_used=0,
    )
    await ConversationService.create_message(db, dm_msg)

    return DMResponse(
        response=opening_narration,
        roll_request=None,
        quest_complete_id=None,
        scene_image_url=None,
        tokens_used=0,
    )


@router.post("/action", response_model=DMResponse)
async def send_player_action(
    request: PlayerActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send player action and get DM response with optional roll request.

    Args:
        request: Player action request
        db: Database session

    Returns:
        DM response with optional roll request
    """
    # Set logging context for this request
    with log_context(
        session_id=int(str(request.session_id).replace("-", "")[:8], 16),
        character_id=int(str(request.character_id).replace("-", "")[:8], 16),
    ):
        logger.info(
            "Player action received", extra={"extra_data": {"action_length": len(request.action)}}
        )

        # Get character for context
        result = await db.execute(select(Character).where(Character.id == request.character_id))
        character = result.scalar_one_or_none()
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Get session for conversation history
        session_id = UUID(request.session_id) if request.session_id else None
        conversation_history = []
        summary_context = None

        if session_id:
            recent_messages = await ConversationService.get_recent_messages(
                db, session_id, count=20
            )
            all_messages = [
                {"role": msg.role.value, "content": msg.content} for msg in recent_messages
            ]

            # Use summarization if conversation is long (>10 messages)
            if SummarizationService.should_summarize(len(all_messages), threshold=10):
                try:
                    (
                        summary_context,
                        conversation_history,
                    ) = await SummarizationService.get_summarized_context(
                        all_messages, character_name=character.name, keep_recent=3
                    )
                    logger.info(
                        "Using summarized context",
                        extra={
                            "extra_data": {
                                "messages_count": len(all_messages),
                                "summary_kept": len(conversation_history),
                            }
                        },
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to summarize conversation", extra={"extra_data": {"error": str(e)}}
                    )
                    # Fallback to recent messages only
                    conversation_history = all_messages[-10:]
            else:
                # Short conversation, use all messages
                conversation_history = all_messages

        # Build character context
        character_context = {
            "name": character.name,
            "race": character.race.value,
            "class": character.character_class.value,
            "level": character.level,
            "hp_current": character.hp_current,
            "hp_max": character.hp_max,
        }

    # Add spell slot information for spellcasters
    spell_slots = {
        "level_1": {"current": character.spell_slots_1, "max": character.spell_slots_1_max},
        "level_2": {"current": character.spell_slots_2, "max": character.spell_slots_2_max},
        "level_3": {"current": character.spell_slots_3, "max": character.spell_slots_3_max},
        "level_4": {"current": character.spell_slots_4, "max": character.spell_slots_4_max},
        "level_5": {"current": character.spell_slots_5, "max": character.spell_slots_5_max},
        "level_6": {"current": character.spell_slots_6, "max": character.spell_slots_6_max},
        "level_7": {"current": character.spell_slots_7, "max": character.spell_slots_7_max},
        "level_8": {"current": character.spell_slots_8, "max": character.spell_slots_8_max},
        "level_9": {"current": character.spell_slots_9, "max": character.spell_slots_9_max},
    }

    # Only include spell slots if character has any
    if any(slot["max"] > 0 for slot in spell_slots.values()):
        character_context["spell_slots"] = spell_slots

        # Count prepared spells
        from app.db.models import CharacterSpell

        prepared_spells_result = await db.execute(
            select(CharacterSpell).where(
                CharacterSpell.character_id == character.id,
                CharacterSpell.is_prepared,
            )
        )
        prepared_spells = prepared_spells_result.scalars().all()
        character_context["prepared_spells_count"] = len(prepared_spells)

    # Add active quest info if any
    active_quest_result = await db.execute(
        select(Quest)
        .join(CharacterQuest, CharacterQuest.quest_id == Quest.id)
        .where(
            CharacterQuest.character_id == request.character_id,
            Quest.state == QuestState.IN_PROGRESS,
        )
        .limit(1)
    )
    active_quest = active_quest_result.scalar_one_or_none()
    if active_quest:
        character_context["active_quest_id"] = str(active_quest.id)
        character_context["active_quest_title"] = active_quest.title

    # If roll result provided, format it into the action
    action_text = request.action
    if request.roll_result:
        roll_info = request.roll_result
        action_text = f"{request.action}\n\n[ROLL RESULT: {roll_info.get('type', 'roll')} - Total: {roll_info.get('total')} (rolled {roll_info.get('roll')}, modifier {roll_info.get('modifier', 0)})"
        if roll_info.get("success") is not None:
            action_text += f", {'SUCCESS' if roll_info['success'] else 'FAILURE'}]"
        else:
            action_text += "]"

    # Fetch relevant memories for context (RAG pattern)
    memory_context = None
    if session_id:
        try:
            from app.services.memory_service import MemoryService

            memory_context = await MemoryService.get_context_for_ai(
                db=db, session_id=session_id, current_situation=action_text, max_memories=5
            )
        except Exception as e:
            # Memory system is optional, don't fail if it errors
            logger.warning(f"Failed to fetch memory context: {e}")

    # Combine summary and memory contexts
    combined_context = None
    if summary_context and memory_context:
        combined_context = f"{summary_context}\n\n{memory_context}"
    elif summary_context:
        combined_context = summary_context
    elif memory_context:
        combined_context = memory_context

    # Apply context window management (prune if needed)
    context_manager = get_context_manager()

    # Build preliminary messages for token counting
    # This mimics what DMEngine._build_messages will create
    preliminary_messages = []
    preliminary_messages.append({"role": "system", "content": "DM_SYSTEM_PROMPT"})  # Placeholder
    if character_context:
        preliminary_messages.append({"role": "system", "content": "CHARACTER_CONTEXT"})
    if combined_context:
        preliminary_messages.append({"role": "system", "content": combined_context})
    preliminary_messages.extend(conversation_history)
    preliminary_messages.append({"role": "user", "content": action_text})

    # Check context size and prune if needed
    context_stats = context_manager.get_context_stats(preliminary_messages)
    logger.info(
        f"Context stats: {context_stats['total_tokens']}/{context_stats['max_tokens']} tokens "
        f"({context_stats['usage_percent']}%), {context_stats['message_count']} messages"
    )

    if context_stats["is_over_limit"]:
        logger.warning("Context exceeds limit, pruning conversation history...")
        conversation_history, tokens_removed = context_manager.prune_messages(
            conversation_history, keep_recent=3
        )
        logger.info(f"Pruned {tokens_removed} tokens from conversation history")

    # Get DM response
    dm_engine = DMEngine()
    result = await dm_engine.narrate(
        user_action=action_text,
        conversation_history=conversation_history,
        character_context=character_context,
        memory_context=combined_context,
    )

    # Parse for dice roll tags
    narration = result["narration"]
    roll_requests_data = []

    # DEV LOG: Log full DM response for debugging
    logger.info(
        "DM Response Generated",
        extra={
            "extra_data": {
                "session_id": str(session_id),
                "character_id": str(request.character_id),
                "narration_length": len(narration),
                "narration_preview": narration[:200],
                "has_roll_tags": RollParser.has_roll_tags(narration),
            }
        },
    )

    if RollParser.has_roll_tags(narration):
        logger.info(
            "Roll tags detected in DM narration",
            extra={"extra_data": {"session_id": str(session_id), "narration": narration}},
        )
        cleaned_narration, roll_requests = RollParser.parse_narration(narration)
        result["narration"] = cleaned_narration
        logger.info(
            "Parsed roll requests",
            extra={
                "extra_data": {
                    "count": len(roll_requests),
                    "types": [r.roll_type.value for r in roll_requests],
                }
            },
        )

        # Execute rolls automatically
        for roll_request in roll_requests:
            try:
                roll_result = RollExecutor.execute_roll(
                    dice_notation=roll_request.dice_notation,
                    roll_type=roll_request.roll_type,
                    character=character,
                    ability=roll_request.ability,
                    dc=roll_request.dc,
                    advantage=roll_request.advantage,
                    disadvantage=roll_request.disadvantage,
                    description=roll_request.description,
                )

                # Format roll result for frontend
                roll_requests_data.append(
                    {
                        "type": roll_request.roll_type.value,
                        "description": roll_request.description,
                        "notation": roll_result.notation,
                        "rolls": roll_result.rolls,
                        "modifier": roll_result.modifier,
                        "total": roll_result.total,
                        "dc": roll_result.dc,
                        "success": roll_result.success,
                        "advantage": roll_result.advantage,
                        "disadvantage": roll_result.disadvantage,
                        "is_critical": roll_result.is_critical,
                        "is_critical_fail": roll_result.is_critical_fail,
                    }
                )
            except Exception as e:
                logger.error(f"Failed to execute roll: {e}")
                # Continue without this roll rather than failing entire request

    # Build result with roll data
    response_data = {
        "narration": result["narration"],
        "tokens_used": result["tokens_used"],
        "roll_request": None,
        "quest_complete": result.get("quest_complete"),
        "rolls": roll_requests_data if roll_requests_data else None,
    }

    # Check for legacy roll request format (keep for backward compatibility)
    if result.get("roll_request"):
        response_data["roll_request"] = result["roll_request"]

    # Save to conversation history if session provided
    if session_id:
        # Save player message
        player_msg = MessageCreate(
            session_id=session_id,
            role="user",
            content=request.action,
            tokens_used=0,
        )
        await ConversationService.create_message(db, player_msg)

        # Save DM response
        dm_msg = MessageCreate(
            session_id=session_id,
            role="assistant",
            content=result["narration"],
            tokens_used=result["tokens_used"],
        )
        await ConversationService.create_message(db, dm_msg)

        # Capture dialogue memory
        try:
            # Extract NPC names from narration (basic heuristic)
            npcs = []
            for line in result["narration"].split("\n"):
                if ":" in line:
                    potential_npc = line.split(":")[0].strip()
                    if potential_npc and len(potential_npc) < 30:
                        npcs.append(potential_npc)

            # Capture the interaction
            await MemoryCaptureService.capture_dialogue(
                db=db,
                session_id=session_id,
                npc_name=npcs[0] if npcs else "Unknown",
                dialogue=f"{action_text}\n{result['narration'][:500]}",
            )
        except Exception as e:
            logger.warning(f"Failed to capture dialogue memory: {e}")

    # Generate scene image if scene change detected
    scene_image_url = None
    if dm_engine.detect_scene_change(result["narration"], request.action):
        try:
            logger.info("Scene change detected, generating image...")
            scene_description = dm_engine.extract_scene_description(
                result["narration"], character_context
            )
            scene_image_url = await ImageService.generate_scene_image(scene_description)
            logger.info(f"Scene image generated: {scene_image_url}")
        except Exception as e:
            logger.error(f"Failed to generate scene image: {e}")
            # Image generation is optional, don't fail the request

    # Generate companion response if appropriate
    companion_response = None
    try:
        from app.services.companion_service import CompanionService

        # Determine trigger based on game state
        companion_trigger = None

        # Check for combat start
        combat_keywords = [
            "combat",
            "attack",
            "initiative",
            "roll for initiative",
            "enemy",
            "enemies",
        ]
        if any(keyword in result["narration"].lower() for keyword in combat_keywords):
            companion_trigger = "combat_start"

        # Check for player low HP
        if character.current_hp and character.max_hp:
            hp_percent = character.current_hp / character.max_hp
            if hp_percent < 0.3:
                companion_trigger = "player_low_hp"

        # Check for victory
        victory_keywords = ["defeated", "victory", "won", "slain", "killed the"]
        if any(keyword in result["narration"].lower() for keyword in victory_keywords):
            companion_trigger = "victory"

        # Check for puzzle/riddle
        puzzle_keywords = ["puzzle", "riddle", "mystery", "clue", "solve"]
        if any(keyword in result["narration"].lower() for keyword in puzzle_keywords):
            companion_trigger = "puzzle"

        # Generate companion speech if trigger detected
        if companion_trigger:
            # Build game context
            game_context = {
                "player_hp": character.current_hp or character.max_hp,
                "player_max_hp": character.max_hp,
                "in_combat": companion_trigger == "combat_start",
                "location": request.action[:100],  # Use action as context
                "situation": result["narration"][:200],
            }

            # Use default companion personality (helpful)
            # Frontend will override with user's selected personality
            companion_response = await CompanionService.generate_companion_speech(
                personality="helpful",
                companion_name="Aria",
                companion_race="Elf",
                companion_class="Wizard",
                trigger=companion_trigger,
                context=game_context,
                user_message=request.action,
            )
            logger.info(f"Generated companion response for trigger: {companion_trigger}")
    except Exception as e:
        logger.warning(f"Failed to generate companion response: {e}")

    # Build response
    roll_request = None
    if result.get("roll_request"):
        roll_request = RollRequest(**result["roll_request"])

    return DMResponse(
        response=result["narration"],
        roll_request=roll_request,
        quest_complete_id=result.get("quest_complete_id"),
        scene_image_url=scene_image_url,
        tokens_used=result["tokens_used"],
        rolls=response_data.get("rolls"),
        companion_speech=companion_response,
    )


@router.get("/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: UUID,
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Max messages"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    source: str = Query("database", description="Source: 'database' or 'redis'"),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation history for a session.

    Args:
        session_id: Session UUID
        limit: Maximum messages to return
        offset: Pagination offset
        source: Data source ('database' for PostgreSQL, 'redis' for active cache)
        db: Database session

    Returns:
        Conversation history
    """
    if source == "redis":
        # Get from Redis (active session cache)
        redis_messages = await session_service.get_conversation_history(session_id, limit=limit)

        # Convert Redis format to response format
        messages = []
        for msg in redis_messages:
            messages.append(
                MessageResponse(
                    id=UUID(int=0),  # Redis doesn't have IDs
                    session_id=session_id,
                    role=msg["role"],
                    content=msg["content"],
                    tokens_used=msg.get("tokens_used"),
                    created_at=msg["timestamp"],
                )
            )

        return ConversationHistoryResponse(
            session_id=session_id, messages=messages, total_messages=len(messages)
        )

    else:
        # Get from PostgreSQL (persistent storage)
        messages, total = await ConversationService.get_session_messages(
            db, session_id, limit=limit, offset=offset
        )

        total_tokens = await ConversationService.get_total_tokens(db, session_id)

        return ConversationHistoryResponse(
            session_id=session_id,
            messages=list(messages),
            total_messages=total,
            total_tokens=total_tokens,
        )


@router.get("/{session_id}/recent", response_model=list[MessageResponse])
async def get_recent_messages(
    session_id: UUID,
    count: int = Query(20, ge=1, le=100, description="Number of recent messages"),
    db: AsyncSession = Depends(get_db),
):
    """Get recent messages for context window.

    Args:
        session_id: Session UUID
        count: Number of recent messages
        db: Database session

    Returns:
        List of recent messages
    """
    messages = await ConversationService.get_recent_messages(db, session_id, count)
    return messages


@router.delete("/{session_id}", status_code=204)
async def delete_conversation_history(
    session_id: UUID,
    include_redis: bool = Query(True, description="Also clear Redis cache"),
    db: AsyncSession = Depends(get_db),
):
    """Delete conversation history for a session.

    Args:
        session_id: Session UUID
        include_redis: Whether to also clear Redis cache
        db: Database session
    """
    # Delete from PostgreSQL
    await ConversationService.delete_session_messages(db, session_id)

    # Optionally clear Redis cache
    if include_redis:
        await session_service.clear_conversation_history(session_id)
