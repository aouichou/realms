"""Ownership verification helpers for defense-in-depth IDOR prevention.

These functions verify that the authenticated user owns the requested resource
before allowing operations. They return the verified object or raise HTTP 404.

Using 404 (not 403) to avoid leaking information about resource existence.
"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Character, CombatEncounter, GameSession


async def verify_character_ownership(
    db: AsyncSession, character_id: UUID, user_id: UUID
) -> Character:
    """Verify character exists and belongs to user.

    Returns the character if owned, raises 404 otherwise.
    """
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if not character or character.user_id != user_id:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


async def verify_session_ownership(
    db: AsyncSession, session_id: UUID, user_id: UUID
) -> GameSession:
    """Verify session exists and belongs to user.

    Returns the session if owned, raises 404 otherwise.
    """
    result = await db.execute(select(GameSession).where(GameSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def verify_combat_ownership(
    db: AsyncSession, combat_id: UUID, user_id: UUID
) -> CombatEncounter:
    """Verify combat encounter exists and its session belongs to user.

    Returns the combat encounter if owned, raises 404 otherwise.
    """
    result = await db.execute(
        select(CombatEncounter)
        .join(GameSession, CombatEncounter.session_id == GameSession.id)
        .where(CombatEncounter.id == combat_id, GameSession.user_id == user_id)
    )
    combat = result.scalar_one_or_none()
    if not combat:
        raise HTTPException(status_code=404, detail="Combat encounter not found")
    return combat
