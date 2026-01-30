"""
API endpoints for companion management.
Handles fetching, creating, and managing AI-driven companion NPCs.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models.character import Character
from app.db.models.companion import Companion
from app.db.models.user import User
from app.middleware.auth import get_current_user
from app.observability.logger import get_logger
from app.observability.tracing import trace_async

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
