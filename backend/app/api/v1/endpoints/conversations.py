"""Conversation history API router."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import Character, CharacterQuest, Quest, QuestState
from app.observability.logger import get_logger, log_context
from app.observability.tracing import get_tracer, trace_async
from app.schemas.dm_response import DMResponse, PlayerActionRequest, RollRequest
from app.schemas.message import (
    ConversationHistoryResponse,
    MessageCreate,
    MessageResponse,
)
from app.services.context_window_manager import get_context_manager
from app.services.conversation_service import ConversationService
from app.services.dm_engine import DMEngine
from app.services.image_detection_service import get_image_detection_service
from app.services.memory_capture import MemoryCaptureService
from app.services.redis_service import session_service
from app.services.roll_executor import RollExecutor
from app.services.roll_parser import RollParser, detect_roll_request_from_narration
from app.services.summarization_service import SummarizationService
from app.utils.character_stats import build_character_stats_context
from app.utils.spell_detector import consume_spell_slot, detect_spell_cast

logger = get_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/messages", response_model=MessageResponse, status_code=201)
@trace_async("conversations.create_message")
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
@trace_async("conversations.start_conversation")
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
    # Get language from request headers
    from app.i18n import get_language

    language = get_language()

    if language == "fr":
        opening_narration = (
            f"Bienvenue, {character.name} !\n\n"
            f"Vous vous trouvez à {session.current_location or 'le début de votre voyage'}. "
            f"En tant que {character.race.value} {character.character_class.value} de niveau {character.level}, "
            f"vous êtes prêt pour tous les défis qui vous attendent.\n\n"
            f"Que voulez-vous faire ?"
        )
    else:
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
        scene_image_url=None,
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
@trace_async("conversations.send_player_action")
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
    logger.info(
        f"=== ACTION ENDPOINT START === session={request.session_id}, character={request.character_id}"
    )
    # Set logging context for this request
    with log_context(
        session_id=(
            int(str(request.session_id).replace("-", "")[:8], 16) if request.session_id else 0
        ),
        character_id=int(str(request.character_id).replace("-", "")[:8], 16),
    ):
        logger.info(
            "Player action received", extra={"extra_data": {"action_length": len(request.action)}}
        )

        # RL-148: Performance measurement - start timing
        import time

        perf_start_total = time.time()
        perf_timings = {}

        # Get character for context
        logger.info(f"Fetching character {request.character_id}")
        perf_start_db = time.time()
        try:
            result = await db.execute(select(Character).where(Character.id == request.character_id))
            character = result.scalar_one_or_none()
            logger.info(f"Character fetched: {character is not None}")
        except Exception as e:
            logger.error(f"ERROR fetching character: {type(e).__name__}: {e}")
            raise
        perf_timings["character_fetch"] = time.time() - perf_start_db

        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Get session for conversation history
        session_id = UUID(request.session_id) if request.session_id else None
        conversation_history = []
        summary_context = None

        if session_id:
            logger.info(f"Getting recent messages for session {session_id}")
            try:
                recent_messages = await ConversationService.get_recent_messages(
                    db, session_id, count=20
                )
                logger.info(f"Got {len(recent_messages)} recent messages")
            except Exception as e:
                logger.error(f"ERROR getting recent messages: {type(e).__name__}: {e}")
                raise
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

                    # GAME-DESIGN.md: Store summary as memory with vector embedding
                    if summary_context and session_id:
                        try:
                            await MemoryCaptureService.capture_summary(
                                db=db,
                                session_id=session_id,
                                summary=summary_context,
                                message_count=len(all_messages),
                            )
                        except Exception as mem_err:
                            logger.warning(f"Failed to capture summary memory: {mem_err}")

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

        # RL-126: Add detailed character stats for game mechanics
        stats_context = build_character_stats_context(character)
        character_context["stats"] = stats_context

        # Add background and personality for richer roleplay
        if character.background:
            character_context["background"] = character.background
        if character.personality:
            character_context["personality"] = character.personality
        if character.background_name:
            character_context["background_name"] = character.background_name
        if character.background_description:
            character_context["background_description"] = character.background_description
        if character.personality_trait:
            character_context["personality_trait"] = character.personality_trait
        if character.ideal:
            character_context["ideal"] = character.ideal
        if character.bond:
            character_context["bond"] = character.bond
        if character.flaw:
            character_context["flaw"] = character.flaw

        # Add spell slot information for spellcasters (stored in JSONB field)
        if character.spell_slots:
            character_context["spell_slots"] = character.spell_slots

        # Count prepared spells
        from app.db.models import CharacterSpell

        logger.info(f"Querying prepared spells for character {character.id}")
        try:
            prepared_spells_result = await db.execute(
                select(CharacterSpell).where(
                    CharacterSpell.character_id == character.id,
                    CharacterSpell.is_prepared,
                )
            )
            prepared_spells = prepared_spells_result.scalars().all()
            logger.info(f"Found {len(prepared_spells)} prepared spells")
        except Exception as e:
            logger.error(f"ERROR querying prepared spells: {type(e).__name__}: {e}")
            raise
        character_context["prepared_spells_count"] = len(prepared_spells)

    # Add active quest info if any
    logger.info(f"Querying active quest for character {request.character_id}")
    try:
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
        logger.info(f"Active quest found: {active_quest is not None}")
    except Exception as e:
        logger.error(f"ERROR querying active quest: {type(e).__name__}: {e}")
        raise
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
        perf_start_memory = time.time()
        try:
            from app.services.memory_service import MemoryService

            memory_context = await MemoryService.get_context_for_ai(
                db=db, session_id=session_id, current_situation=action_text, max_memories=5
            )
        except Exception as e:
            # Memory system is optional, don't fail if it errors
            logger.warning(f"Failed to fetch memory context: {e}")
        perf_timings["memory_fetch"] = time.time() - perf_start_memory

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

    # RL-148: Performance measurement - DM narration timing
    import time

    perf_start_dm = time.time()

    # Get DM response
    from app.i18n import get_language

    language = get_language()
    dm_engine = DMEngine()

    # RL-129: Pass character and db for tool calling
    result = await dm_engine.narrate(
        user_action=action_text,
        conversation_history=conversation_history,
        character_context=character_context,
        memory_context=combined_context,
        language=language,
        character=character,
        db=db,
        use_tools=True,  # Enable Mistral tool calling
    )

    perf_dm_duration = time.time() - perf_start_dm

    # Safety check: Ensure narration is not empty
    if not result.get("narration") or not result["narration"].strip():
        logger.error(f"DM engine returned empty narration. Full result: {result}")
        result["narration"] = "The magical energies swirl uncertainly as the spell takes effect..."

    logger.info(
        f"DM narration completed in {perf_dm_duration:.2f}s",
        extra={
            "extra_data": {
                "dm_duration_seconds": perf_dm_duration,
                "narration_length": len(result["narration"]),
                "chars_per_second": (
                    len(result["narration"]) / perf_dm_duration if perf_dm_duration > 0 else 0
                ),
            }
        },
    )

    # Parse for dice roll tags
    narration = result["narration"]
    roll_requests_data = []

    # RL-128: Auto-detect spell casting and consume spell slots
    spell_warnings = []
    try:
        spell_name, spell_level, spell_warning, spell_suggestion = await detect_spell_cast(
            player_action=request.action, character=character, db=db
        )

        # Handle spell suggestions (typos detected)
        if spell_suggestion:
            spell_warnings.append(spell_suggestion)
            logger.info(f"Spell suggestion: {spell_suggestion}")

        # Handle spell warnings (unknown spell or other issues)
        if spell_warning:
            spell_warnings.append(spell_warning)
            logger.info(f"Spell warning: {spell_warning}")

        if spell_name and spell_level is not None:
            logger.info(
                f"Spell cast detected: {spell_name} (Level {spell_level}) by {character.name}"
            )

            # Consume spell slot (cantrips return True without consuming)
            slot_consumed, slot_warning = consume_spell_slot(character, spell_level)

            if slot_warning:
                spell_warnings.append(slot_warning)
                logger.warning(f"Slot consumption warning: {slot_warning}")

            if slot_consumed:
                # Use flag_modified to mark JSONB field as changed
                from sqlalchemy.orm.attributes import flag_modified

                flag_modified(character, "spell_slots")
                await db.flush()  # Persist to database
                await db.commit()  # Commit the transaction

                if spell_level > 0:
                    remaining = (character.spell_slots or {}).get(str(spell_level), 0)
                    logger.info(
                        f"Spell slot consumed: Level {spell_level} for {spell_name}. "
                        f"Remaining slots: {remaining}"
                    )
                else:
                    logger.info(f"Cantrip cast: {spell_name} (no slot consumed)")
            else:
                logger.warning(
                    f"Failed to consume spell slot for {spell_name} (Level {spell_level})"
                )
    except Exception as spell_err:
        logger.warning(f"Spell detection failed: {spell_err}")
        # Don't fail the request if spell detection errors

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

    player_roll_request = None
    player_roll_requests = []

    if RollParser.has_roll_tags(narration):
        logger.info(
            "Roll tags detected in DM narration",
            extra={"extra_data": {"session_id": str(session_id), "narration": narration}},
        )
        tracer = get_tracer()
        with tracer.start_as_current_span("rolls.parse_tags") as span:
            span.set_attribute("rolls.has_tags", True)
            span.set_attribute("session_id", str(session_id))
            cleaned_narration, roll_requests = RollParser.parse_narration(narration)
        result["narration"] = cleaned_narration
        logger.info(
            "Parsed roll requests",
            extra={
                "extra_data": {
                    "count": len(roll_requests),
                    "types": [r.roll_type.value for r in roll_requests],
                    "player_rolls": sum(1 for r in roll_requests if r.is_player_roll),
                    "npc_rolls": sum(1 for r in roll_requests if not r.is_player_roll),
                }
            },
        )

        # Execute NPC rolls automatically, collect player roll requests
        for roll_request in roll_requests:
            if roll_request.is_player_roll:
                logger.info(
                    f"Player roll detected: {roll_request.roll_type.value} - {roll_request.description}",
                    extra={"extra_data": {"roll_request": roll_request.__dict__}},
                )
                player_roll_requests.append(
                    {
                        "type": roll_request.roll_type.value,
                        "dice": roll_request.dice_notation,
                        "ability": roll_request.ability.value if roll_request.ability else None,
                        "skill": roll_request.skill,
                        "dc": roll_request.dc,
                        "advantage": roll_request.advantage,
                        "disadvantage": roll_request.disadvantage,
                        "description": roll_request.description,
                    }
                )
                if player_roll_request is None:
                    player_roll_request = player_roll_requests[0]
                continue

            try:
                logger.info(
                    f"Auto-executing NPC roll: {roll_request.roll_type.value} - {roll_request.description}",
                    extra={"extra_data": {"roll_request": roll_request.__dict__}},
                )
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
                logger.error(f"Failed to execute NPC roll: {e}")
                # Continue without this roll rather than failing entire request

    # RL-127: Natural language roll detection (fallback if no tags found)
    # Skip when player is submitting a roll result — DM is narrating an outcome, not requesting a new roll
    _action_lower = request.action.lower().strip()
    _is_responding_to_roll = (
        request.roll_result is not None  # structured roll from UI dice roller
        or "[ROLL RESULT:" in action_text  # formatted roll result in action
        or _action_lower.startswith("i rolled")
        or _action_lower.startswith("rolled a")
        or _action_lower.startswith("i got a")
    )
    if not player_roll_requests and not _is_responding_to_roll:
        logger.info("No [ROLL:...] tags found, attempting natural language detection")
        detected_roll = detect_roll_request_from_narration(result["narration"])

        if detected_roll:
            logger.info(
                "Natural language roll detected",
                extra={
                    "extra_data": {
                        "roll_type": detected_roll["roll_type"],
                        "ability": detected_roll.get("ability"),
                        "skill": detected_roll.get("skill"),
                        "dc": detected_roll.get("dc"),
                        "detected_text": detected_roll["detected_text"],
                    }
                },
            )

            # Convert to player roll request format
            nl_roll_request = {
                "type": detected_roll["roll_type"],
                "dice": "d20",  # Most D&D checks use d20
                "ability": detected_roll.get("ability"),
                "skill": detected_roll.get("skill"),
                "dc": detected_roll.get("dc"),
                "advantage": None,
                "disadvantage": None,
                "description": detected_roll["detected_text"],
            }

            player_roll_requests.append(nl_roll_request)
            player_roll_request = nl_roll_request

            logger.info(
                f"Natural language roll request created: {detected_roll['roll_type']} "
                f"({detected_roll.get('skill') or detected_roll.get('ability')})"
            )

    # Build result with roll data
    response_data = {
        "narration": result["narration"],
        "tokens_used": result["tokens_used"],
        "roll_request": player_roll_request,
        "roll_requests": player_roll_requests if player_roll_requests else None,
        "quest_complete": result.get("quest_complete"),
        "rolls": roll_requests_data if roll_requests_data else None,
        "warnings": spell_warnings if spell_warnings else None,
    }

    # Check for tool-based roll request format (from request_player_roll tool)
    if result.get("roll_request") and player_roll_request is None:
        tool_roll = result["roll_request"]

        # Transform tool executor format to RollRequest schema the frontend expects
        # Tool executor returns: {type, ability_or_skill, dc, advantage, disadvantage, description}
        # Frontend expects: {type, dice, ability, skill, dc, advantage, disadvantage, description}

        # Map roll_type to frontend type
        roll_type_map = {
            "ability_check": "check",
            "saving_throw": "save",
            "attack": "attack",
        }
        frontend_type = roll_type_map.get(tool_roll["type"], tool_roll["type"])

        # Parse ability_or_skill into ability and skill
        ability_or_skill = tool_roll.get("ability_or_skill", "")
        ability = None
        skill = None

        # Abilities are uppercase (STR, DEX, CON, INT, WIS, CHA)
        abilities = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

        if tool_roll["type"] == "saving_throw":
            # For saves, ability_or_skill is the ability
            ability = ability_or_skill if ability_or_skill in abilities else None
        elif tool_roll["type"] == "ability_check":
            # For checks, ability_or_skill is usually a skill
            # We capitalize first letter for consistency
            skill = ability_or_skill.lower() if ability_or_skill else None
        # For attacks, ability_or_skill is "melee" or "ranged" which we don't need to map

        response_data["roll_request"] = {
            "type": frontend_type,
            "dice": "1d20",  # Standard roll dice
            "ability": ability,
            "skill": skill,
            "dc": tool_roll.get("dc"),
            "advantage": tool_roll.get("advantage", False),
            "disadvantage": tool_roll.get("disadvantage", False),
            "description": tool_roll.get("description", ""),
        }

    # Generate scene image for significant moments (BEFORE saving messages)
    # Uses semantic similarity detection - works in any language (French, English, etc.)
    scene_image_url = None

    logger.info("Checking scene significance for image generation")
    try:
        (
            is_significant,
            similarity_score,
            matched_template,
        ) = get_image_detection_service().is_significant_scene(
            narration=result["narration"], player_action=request.action
        )
        logger.info(
            f"Scene significance check complete: is_significant={is_significant}, "
            f"similarity={similarity_score:.3f}, template='{matched_template}'"
        )
    except Exception as img_detect_err:
        logger.error(f"Image detection failed: {img_detect_err}", exc_info=True)
        is_significant = False
        similarity_score = 0.0
        matched_template = None

    if is_significant:
        try:
            logger.info(
                f"Generating image for significant scene "
                f"(similarity: {similarity_score:.3f}, template: '{matched_template}')"
            )
            from app.services.image_service import image_service

            # Build character context for image
            char_desc = None
            if character:
                char_desc = (
                    f"{character.name}, {character.race.value} {character.character_class.value}"
                )

            # Generate or reuse image
            scene_image_url = await image_service.generate_scene_image(
                scene_description=result["narration"],
                db=db,
                use_cache=True,
                character_description=char_desc,
            )

            if scene_image_url:
                logger.info(f"Scene image ready: {scene_image_url}")
            else:
                logger.info("Image generation skipped (rate limit or disabled)")

        except Exception as e:
            logger.error(f"Failed to generate scene image: {e}")
            # Image generation is optional, don't fail the request
            # Rollback the failed transaction to allow subsequent operations
            try:
                await db.rollback()
                logger.info("Transaction rolled back after image generation failure")
            except Exception as rb_err:
                logger.error(f"Failed to rollback after image error: {rb_err}")

    # Save to conversation history if session provided
    if session_id:
        logger.info(f"About to save player message for session {session_id}")
        try:
            # Save player message
            player_msg = MessageCreate(
                session_id=session_id,
                role="user",
                content=request.action,
                tokens_used=0,
            )
            logger.info(f"Player message object created: {player_msg}")
            await ConversationService.create_message(db, player_msg)
            logger.info("Player message saved successfully")
        except Exception as e:
            logger.error(f"FAILED to save player message: {type(e).__name__}: {e}")
            raise

        # Save DM response with scene image URL
        dm_msg = MessageCreate(
            session_id=session_id,
            role="assistant",
            content=result["narration"],
            tokens_used=result["tokens_used"],
            scene_image_url=scene_image_url,  # Now this is defined
        )
        await ConversationService.create_message(db, dm_msg)

        # Capture dialogue memory
        try:
            # Enhanced memory capture system - detect event types automatically
            narration_lower = result["narration"].lower()
            action_lower = action_text.lower()

            # Detect event type and capture appropriately
            event_captured = False

            # 1. Combat events (high priority)
            combat_keywords = [
                "attack",
                "damage",
                "hit",
                "combat",
                "initiative",
                "strike",
                "defeat",
                "victory",
                "flee",
            ]
            if any(
                keyword in narration_lower or keyword in action_lower for keyword in combat_keywords
            ):
                # Extract combatant names (basic NPC detection)
                combatants = []
                for word in result["narration"].split():
                    if word and word[0].isupper() and len(word) > 2:
                        combatants.append(word.strip(",.!?"))

                # Determine outcome
                outcome = "in_progress"
                if any(
                    word in narration_lower for word in ["victory", "defeated", "won", "triumph"]
                ):
                    outcome = "victory"
                elif any(word in narration_lower for word in ["defeat", "died", "death", "fallen"]):
                    outcome = "defeat"
                elif any(word in narration_lower for word in ["flee", "retreat", "escape"]):
                    outcome = "flee"

                await MemoryCaptureService.capture_combat_event(
                    db=db,
                    session_id=session_id,
                    combatant_names=combatants[:5],  # Limit to 5
                    outcome=outcome,
                    details=f"{action_text} - {result['narration'][:300]}",
                    importance=8 if "victory" in outcome or "defeat" in outcome else 7,
                )
                event_captured = True
                logger.info(f"Captured COMBAT memory: {outcome}, combatants: {combatants[:3]}")

            # 2. NPC Dialogue (already handled above, but enhance)
            if not event_captured:
                npcs = []
                for line in result["narration"].split("\n"):
                    if ":" in line:
                        potential_npc = line.split(":")[0].strip()
                        if potential_npc and len(potential_npc) < 30 and potential_npc[0].isupper():
                            npcs.append(potential_npc)

                if npcs:
                    await MemoryCaptureService.capture_dialogue(
                        db=db,
                        session_id=session_id,
                        npc_name=npcs[0],
                        dialogue=f"{action_text[:200]} - {result['narration'][:400]}",
                    )
                    event_captured = True
                    logger.info(f"Captured DIALOGUE memory with NPC: {npcs[0]}")

            # 3. Discovery/Location changes (important for continuity)
            discovery_keywords = [
                "discover",
                "find",
                "found",
                "notice",
                "see",
                "arrive",
                "enter",
                "reach",
            ]
            if not event_captured and any(
                keyword in narration_lower for keyword in discovery_keywords
            ):
                await MemoryService.store_memory(
                    db=db,
                    session_id=session_id,
                    event_type="discovery",
                    content=f"Discovery: {action_text} - {result['narration'][:400]}",
                    importance=6,
                    tags=["discovery", "exploration"],
                )
                event_captured = True
                logger.info("Captured DISCOVERY memory")

            # 4. Generic important interaction (fallback)
            if not event_captured and len(result["narration"]) > 100:
                # Store as general interaction if DM response is substantial
                await MemoryService.store_memory(
                    db=db,
                    session_id=session_id,
                    event_type="npc_interaction",
                    content=f"{action_text[:150]} - {result['narration'][:350]}",
                    importance=5,
                    tags=["interaction"],
                )
                logger.debug("Captured generic INTERACTION memory")

        except Exception as e:
            logger.warning(f"Failed to capture event memory: {e}", exc_info=True)

    # Generate companion responses if any active companions (RL-131)
    companion_responses = []
    try:
        from app.db.models import Companion
        from app.services.companion_service import CompanionService

        # Get active companions for this character
        result_companions = await db.execute(
            select(Companion).where(
                Companion.character_id == request.character_id,
                Companion.is_active,
                Companion.is_alive,
            )
        )
        active_companions = result_companions.scalars().all()

        if active_companions:
            logger.info(
                f"Found {len(active_companions)} active companions for character {request.character_id}"
            )

            # Determine if in combat
            # Combat detection - not currently used but available for future enhancement
            # combat_keywords = [
            #     "combat",
            #     "attack",
            #     "initiative",
            #     "roll for initiative",
            #     "enemy",
            #     "enemies",
            # ]
            # in_combat = any(keyword in result["narration"].lower() for keyword in combat_keywords)

            # Get recent conversation context (last 3 messages)
            recent_context = []
            if session_id and len(conversation_history) > 0:
                recent_context = conversation_history[-3:]

            # Initialize companion service
            from app.services.provider_selector import provider_selector

            ai_provider = provider_selector.get_current_provider()
            if not ai_provider:
                logger.warning("AI service unavailable, skipping companion responses")
            else:
                companion_service = CompanionService(ai_provider)

                # Check each companion and generate responses
                for companion in active_companions:
                    try:
                        # Check if companion should respond
                        should_respond = await companion_service.should_companion_respond(
                            companion=companion,
                            player_action=request.action,
                            dm_narration=result["narration"],
                        )

                        if should_respond:
                            logger.info(f"Companion {companion.name} will respond")

                            # Generate companion response
                            companion_message = await companion_service.generate_companion_response(
                                companion=companion,
                                player_action=request.action,
                                dm_narration=result["narration"],
                                recent_context=recent_context,
                                character=character,
                            )

                            if companion_message:
                                # Save companion message to conversation history
                                if session_id:
                                    companion_msg = MessageCreate(
                                        session_id=session_id,
                                        role="companion",
                                        content=companion_message,
                                        tokens_used=0,  # Gemini doesn't provide token counts
                                        companion_id=companion.id,  # type: ignore[arg-type]
                                    )
                                    await ConversationService.create_message(db, companion_msg)
                                    logger.info(f"Saved companion message from {companion.name}")

                                # Add to response data
                                companion_responses.append(
                                    {
                                        "companion_id": str(companion.id),
                                        "companion_name": companion.name,
                                        "message": companion_message,
                                        "loyalty": companion.loyalty,
                                        "relationship_status": companion.relationship_status.value,
                                    }
                                )

                                logger.info(f"Generated response from companion {companion.name}")
                        else:
                            logger.debug(f"Companion {companion.name} chose not to respond")

                    except Exception as companion_err:
                        logger.warning(
                            f"Failed to generate response for companion {companion.id}: {companion_err}"
                        )
                        continue

    except Exception as e:
        logger.warning(f"Failed to process companions: {e}")

    # Build response
    roll_request = None
    if response_data.get("roll_request"):
        roll_request = RollRequest(**response_data["roll_request"])

    # RL-148: Final performance summary
    perf_total_duration = time.time() - perf_start_total
    logger.info(
        f"✅ Total request completed in {perf_total_duration:.2f}s",
        extra={
            "extra_data": {
                "total_duration_seconds": perf_total_duration,
                "timings": {
                    "character_fetch": perf_timings.get("character_fetch", 0),
                    "memory_fetch": perf_timings.get("memory_fetch", 0),
                    "dm_narration": perf_dm_duration,
                    "other": perf_total_duration - sum(perf_timings.values()) - perf_dm_duration,
                },
                "dm_percentage": (
                    (perf_dm_duration / perf_total_duration * 100) if perf_total_duration > 0 else 0
                ),
            }
        },
    )

    return DMResponse(
        response=result["narration"],
        roll_request=roll_request,
        roll_requests=(
            [RollRequest(**req) for req in response_data["roll_requests"]]
            if response_data.get("roll_requests")
            else None
        ),
        quest_complete_id=result.get("quest_complete_id"),
        scene_image_url=scene_image_url,
        tokens_used=result["tokens_used"],
        rolls=response_data.get("rolls"),
        companion_speech=(
            companion_responses[0]["message"] if companion_responses else None
        ),  # Legacy field for backward compat
        companion_responses=(
            companion_responses if companion_responses else None
        ),  # New field with full companion data
        warnings=response_data.get("warnings"),
        tool_calls_made=result.get("tool_calls_made"),  # RL-129: Mistral tool calls
        character_updates=result.get("character_updates"),  # RL-129: Character state changes
    )


@router.get("/{session_id}", response_model=ConversationHistoryResponse)
@trace_async("conversations.get_history")
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
@trace_async("conversations.get_recent")
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
@trace_async("conversations.delete_history")
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
