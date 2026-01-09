"""
Active effects API endpoints
Manage temporary buffs, debuffs, and conditions on characters
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.services.effects_service import EffectsService

router = APIRouter(prefix="/api/effects", tags=["effects"])


@router.get("/character/{character_id}")
async def get_character_effects(
    character_id: int,
    session_id: Optional[UUID] = Query(None, description="Filter by session ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all active effects for a character

    Args:
        character_id: Character ID
        session_id: Optional session ID to filter effects

    Returns:
        List of active effects
    """
    service = EffectsService(db)
    effects = await service.get_active_effects(character_id, session_id)

    return {
        "character_id": character_id,
        "session_id": str(session_id) if session_id else None,
        "effects": [effect.to_dict() for effect in effects],
        "count": len(effects),
    }


@router.delete("/{effect_id}")
async def remove_effect(
    effect_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove an active effect

    Args:
        effect_id: Effect UUID

    Returns:
        Success message
    """
    service = EffectsService(db)
    success = await service.remove_effect(effect_id)

    if not success:
        raise HTTPException(status_code=404, detail="Effect not found")

    return {
        "success": True,
        "message": "Effect removed successfully",
    }


@router.post("/character/{character_id}/break-concentration")
async def break_concentration(
    character_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Break all concentration effects for a character

    Used when character takes damage or loses concentration

    Args:
        character_id: Character ID

    Returns:
        Number of effects broken
    """
    service = EffectsService(db)
    count = await service.break_concentration(character_id)

    return {
        "character_id": character_id,
        "effects_broken": count,
        "message": f"Broke concentration on {count} effect(s)"
        if count > 0
        else "No concentration effects active",
    }


@router.post("/session/{session_id}/round-end")
async def process_round_end(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Process end of combat round for all characters in session

    Decrements round-based duration effects

    Args:
        session_id: Session UUID

    Returns:
        List of expired effect names
    """
    service = EffectsService(db)
    expired = await service.process_round_end(session_id)

    return {
        "session_id": str(session_id),
        "expired_effects": expired,
        "count": len(expired),
    }


@router.post("/character/{character_id}/rest")
async def process_rest(
    character_id: int,
    rest_type: str = Query(..., regex="^(short|long)$", description="Type of rest: short or long"),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove effects that end on rest

    Args:
        character_id: Character ID
        rest_type: "short" or "long"

    Returns:
        Number of effects removed
    """
    service = EffectsService(db)
    is_long_rest = rest_type == "long"
    count = await service.process_rest(character_id, is_long_rest)

    return {
        "character_id": character_id,
        "rest_type": rest_type,
        "effects_removed": count,
        "message": f"Removed {count} effect(s) after {rest_type} rest",
    }


@router.post("/cleanup")
async def cleanup_expired_effects(
    db: AsyncSession = Depends(get_db),
):
    """
    Cleanup all time-expired effects across all characters

    This should be called periodically (e.g., every minute)

    Returns:
        Number of effects cleaned up
    """
    service = EffectsService(db)
    count = await service.cleanup_expired_effects()

    return {
        "effects_cleaned": count,
        "message": f"Cleaned up {count} expired effect(s)",
    }
