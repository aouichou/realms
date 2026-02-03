"""
API endpoints for companion management.
Handles fetching, creating, and managing AI-driven companion NPCs.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.base import get_db
from app.db.models.character import Character
from app.db.models.companion import Companion
from app.db.models.companion_conversation import CompanionConversation
from app.db.models.user import User
from app.middleware.auth import get_current_user
from app.observability.logger import get_logger
from app.observability.tracing import trace_async
from app.schemas.companion import (
    CompanionChatRequest,
    CompanionChatResponse,
    CompanionConversationMessage,
)
from app.services.companion_service import CompanionService
from app.services.gemini_service import GeminiService

logger = get_logger(__name__)

router = APIRouter()


@router.get("/characters/{character_id}/companions")
@trace_async("companions.get_character_companions")
async def get_character_companions(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    Get all companions for a character.

    Returns:
        List of companions with their current state
    """
    # Verify character belongs to user
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.user_id == current_user.id,
            Character.deleted_at.is_(None),
        )
    )
    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found or does not belong to you",
        )

    # Fetch all companions for this character
    result = await db.execute(
        select(Companion)
        .where(Companion.character_id == character_id)
        .order_by(Companion.created_at.desc())
    )
    companions = result.scalars().all()

    return [companion.to_dict() for companion in companions]


@router.get("/characters/{character_id}/companions/active")
@trace_async("companions.get_active_companions")
async def get_active_companions(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    Get only active companions for a character (present in current scene).

    Returns:
        List of active companions
    """
    # Verify character belongs to user
    result = await db.execute(
        select(Character).where(
            Character.id == character_id,
            Character.user_id == current_user.id,
            Character.deleted_at.is_(None),
        )
    )
    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found or does not belong to you",
        )

    # Fetch only active companions
    result = await db.execute(
        select(Companion)
        .where(
            Companion.character_id == character_id,
            Companion.is_active == True,  # noqa: E712
            Companion.is_alive == True,  # noqa: E712
        )
        .order_by(Companion.created_at.desc())
    )
    companions = result.scalars().all()

    return [companion.to_dict() for companion in companions]


@router.get("/companions/{companion_id}")
@trace_async("companions.get_companion")
async def get_companion(
    companion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get detailed information about a specific companion.

    Returns:
        Companion details including stats and memory
    """
    # Fetch companion and verify ownership through character
    result = await db.execute(
        select(Companion)
        .join(Character, Companion.character_id == Character.id)
        .where(
            Companion.id == companion_id,
            Character.user_id == current_user.id,
            Character.deleted_at.is_(None),
        )
    )
    companion = result.scalar_one_or_none()

    if not companion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Companion not found or does not belong to you",
        )

    companion_data = companion.to_dict()

    # Include memory and events if present
    if companion.conversation_memory is not None:  # type: ignore[comparison-overlap]
        companion_data["conversation_memory"] = companion.conversation_memory
    if companion.important_events is not None:  # type: ignore[comparison-overlap]
        companion_data["important_events"] = companion.important_events

    return companion_data


@router.patch("/companions/{companion_id}/loyalty")
@trace_async("companions.update_loyalty")
async def update_companion_loyalty(
    companion_id: int,
    loyalty_change: int,
    event_description: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Update companion loyalty based on player actions.

    Args:
        companion_id: ID of companion to update
        loyalty_change: Change in loyalty (-100 to +100)
        event_description: Description of what caused the change

    Returns:
        Updated companion data
    """
    # Fetch companion and verify ownership
    result = await db.execute(
        select(Companion)
        .join(Character, Companion.character_id == Character.id)
        .where(
            Companion.id == companion_id,
            Character.user_id == current_user.id,
            Character.deleted_at.is_(None),
        )
    )
    companion = result.scalar_one_or_none()

    if not companion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Companion not found or does not belong to you",
        )

    # Import here to avoid circular imports
    from app.config import settings
    from app.services.companion_service import CompanionService
    from app.services.gemini_service import GeminiService

    # Get Gemini service for companion
    gemini_config = settings.ai_providers_config.get("gemini", {})
    gemini_service = GeminiService(
        api_key=gemini_config.get("api_key"),
        model=gemini_config.get("model", "gemini-1.5-flash"),
        priority=gemini_config.get("priority", 1),
    )
    companion_service = CompanionService(gemini_service)

    # Update loyalty
    await companion_service.update_companion_loyalty(
        companion=companion,
        event_description=event_description,
        loyalty_change=loyalty_change,
        db=db,
    )

    return companion.to_dict()


@router.patch("/companions/{companion_id}/active")
@trace_async("companions.toggle_active")
async def toggle_companion_active(
    companion_id: int,
    is_active: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Toggle whether companion is active (present in current scene).

    Args:
        companion_id: ID of companion to update
        is_active: Whether companion should be active

    Returns:
        Updated companion data
    """
    # Fetch companion and verify ownership
    result = await db.execute(
        select(Companion)
        .join(Character, Companion.character_id == Character.id)
        .where(
            Companion.id == companion_id,
            Character.user_id == current_user.id,
            Character.deleted_at.is_(None),
        )
    )
    companion = result.scalar_one_or_none()

    if not companion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Companion not found or does not belong to you",
        )

    companion.is_active = is_active  # type: ignore[assignment]
    await db.commit()
    await db.refresh(companion)

    logger.info(f"Companion {companion.name} set to {'active' if is_active else 'inactive'}")

    return companion.to_dict()


@router.post("/companions/chat", response_model=CompanionChatResponse)
@trace_async("companions.chat")
async def chat_with_companion(
    request: CompanionChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanionChatResponse:
    """
    Send a message to a companion and receive a response.

    If share_with_dm is True, the conversation will be saved to the database
    and visible to the DM. Otherwise, it's ephemeral (only stored in companion memory).

    Args:
        request: Chat request with companion_id, message, and share_with_dm flag

    Returns:
        Companion's response and message IDs
    """
    # Fetch companion and verify ownership through character
    result = await db.execute(
        select(Companion)
        .join(Character, Companion.character_id == Character.id)
        .where(
            Companion.id == request.companion_id,
            Character.user_id == current_user.id,
            Character.deleted_at.is_(None),
        )
    )
    companion = result.scalar_one_or_none()

    if not companion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Companion not found or does not belong to you",
        )

    # Get character for context
    result = await db.execute(
        select(Character).where(
            Character.id == companion.character_id,
            Character.deleted_at.is_(None),
        )
    )
    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found",
        )

    # Initialize Gemini service for companion
    gemini_service = GeminiService(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        priority=1,
    )
    companion_service = CompanionService(gemini_service)

    # Build context for companion response
    recent_context = []
    if companion.conversation_memory:
        for memory in companion.conversation_memory[-10:]:
            role = memory.get("role", "")
            content = memory.get("content", "")
            if role == "player":
                recent_context.append({"role": "user", "content": content})
            elif role == "companion":
                recent_context.append({"role": "assistant", "content": content})

    # Generate companion response
    try:
        companion_response = await companion_service.generate_companion_response(
            companion=companion,
            player_action=request.message,
            dm_narration="",  # Direct chat, no DM narration
            recent_context=recent_context,
            character=character,
        )
    except Exception as e:
        logger.error(f"Failed to generate companion response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate companion response",
        )

    # Save to database if sharing with DM
    player_message_id = None
    companion_message_id = None

    if request.share_with_dm:
        # Save player message
        player_message = CompanionConversation(
            companion_id=companion.id,
            character_id=character.id,
            role="player",
            message=request.message,
            shared_with_dm=True,
        )
        db.add(player_message)

        # Save companion response
        companion_message = CompanionConversation(
            companion_id=companion.id,
            character_id=character.id,
            role="companion",
            message=companion_response,
            shared_with_dm=True,
        )
        db.add(companion_message)

        await db.commit()
        await db.refresh(player_message)
        await db.refresh(companion_message)

        player_message_id = player_message.id
        companion_message_id = companion_message.id

        logger.info(
            f"Saved shared conversation for companion '{companion.name}' (char: {character.id})"
        )
    else:
        # Generate temporary UUIDs for non-shared messages
        import uuid

        player_message_id = uuid.uuid4()
        companion_message_id = uuid.uuid4()

        logger.info(f"Ephemeral chat with companion '{companion.name}' (not shared with DM)")

    # Update companion in database (memory updated by generate_companion_response)
    await db.commit()

    return CompanionChatResponse(
        message_id=player_message_id,
        companion_response=companion_response,
        companion_message_id=companion_message_id,
    )


@router.get("/companions/{companion_id}/conversations")
@trace_async("companions.get_conversations")
async def get_companion_conversations(
    companion_id: UUID,
    shared_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CompanionConversationMessage]:
    """
    Get conversation history for a companion.

    By default, only returns messages shared with DM.
    Players can see all their own conversations (shared or not).

    Args:
        companion_id: ID of the companion
        shared_only: If True, only return messages shared with DM

    Returns:
        List of conversation messages
    """
    # Fetch companion and verify ownership through character
    result = await db.execute(
        select(Companion)
        .join(Character, Companion.character_id == Character.id)
        .where(
            Companion.id == companion_id,
            Character.user_id == current_user.id,
            Character.deleted_at.is_(None),
        )
    )
    companion = result.scalar_one_or_none()

    if not companion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Companion not found or does not belong to you",
        )

    # Build query for conversations
    query = select(CompanionConversation).where(CompanionConversation.companion_id == companion_id)

    if shared_only:
        query = query.where(CompanionConversation.shared_with_dm == True)  # noqa: E712

    query = query.order_by(CompanionConversation.created_at.asc())

    result = await db.execute(query)
    conversations = result.scalars().all()

    return [
        CompanionConversationMessage(
            id=conv.id,
            companion_id=conv.companion_id,
            character_id=conv.character_id,
            role=conv.role,
            message=conv.message,
            shared_with_dm=conv.shared_with_dm,
            created_at=conv.created_at,
        )
        for conv in conversations
    ]
