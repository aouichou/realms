"""Save/Load System for Game Sessions"""

import json
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Character, GameSession
from app.services.redis_service import session_service


class SaveService:
    """Service for saving and loading game sessions"""

    @staticmethod
    async def save_game(
        db: AsyncSession, session_id: UUID, save_name: Optional[str] = None, overwrite: bool = False
    ) -> Dict:
        """Save current game state

        Args:
            db: Database session
            session_id: Game session ID
            save_name: Optional name for the save
            overwrite: If True, overwrite existing save with same name

        Returns:
            Dict with save information

        Raises:
            ValueError: If save name already exists and overwrite is False
        """
        # Get session from database
        result = await db.execute(select(GameSession).where(GameSession.id == session_id))
        game_session = result.scalar_one_or_none()

        if not game_session:
            raise ValueError(f"Session {session_id} not found")

        # Get character
        character = await db.get(Character, game_session.character_id)

        # Generate save name if not provided
        if not save_name:
            save_name = f"Auto-save {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"

        # Check for duplicate save name (unless overwriting)
        if not overwrite and session_service.redis:
            # Check if a save with this name already exists for this session
            save_key = f"save:{session_id}"
            existing_save = await session_service.redis.get(save_key)  # type: ignore[misc]

            if existing_save:
                existing_data = json.loads(existing_save)
                if existing_data.get("save_name") == save_name:
                    raise ValueError(f"A save named '{save_name}' already exists")

        # Get session state from Redis
        redis_state = await session_service.get_session_state(session_id)

        # Create save data
        save_data = {
            "save_name": save_name,
            "session_id": str(session_id),
            "character_id": str(game_session.character_id),
            "character_name": character.name if character else "Unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "game_data": {
                "location": game_session.current_location,
                "state_snapshot": game_session.state_snapshot or {},
                "redis_state": redis_state,
            },
        }

        # Store in Redis with session ID as key
        save_key = f"save:{session_id}"
        if session_service.redis:
            await session_service.redis.setex(
                save_key,
                60 * 60 * 24 * 30,  # 30 days TTL
                json.dumps(save_data),
            )  # type: ignore[misc]

        return save_data

    @staticmethod
    async def load_game(db: AsyncSession, session_id: UUID) -> Optional[Dict]:
        """Load saved game state

        Args:
            db: Database session
            session_id: Game session ID to load

        Returns:
            Dict with save data or None if not found
        """
        save_key = f"save:{session_id}"
        if not session_service.redis:
            return None

        save_data = await session_service.redis.get(save_key)  # type: ignore[misc]

        if not save_data:
            return None

        return json.loads(save_data)

    @staticmethod
    async def auto_save(db: AsyncSession, session_id: UUID) -> Dict:
        """Perform automatic save

        Args:
            db: Database session
            session_id: Game session ID

        Returns:
            Dict with save information
        """
        return await SaveService.save_game(
            db,
            session_id,
            save_name=f"Auto-save {datetime.now(timezone.utc).strftime('%H:%M')}",
        )

    @staticmethod
    async def list_saves(db: AsyncSession, user_id: UUID) -> list[Dict]:
        """List all saves for a user

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of save dictionaries
        """
        # Get all sessions for user
        result = await db.execute(select(GameSession).where(GameSession.user_id == user_id))
        sessions = result.scalars().all()

        saves = []
        for session in sessions:
            save_key = f"save:{session.id}"
            if session_service.redis:
                save_data = await session_service.redis.get(save_key)  # type: ignore[misc]
                if save_data:
                    saves.append(json.loads(save_data))

        return sorted(saves, key=lambda x: x["timestamp"], reverse=True)

    @staticmethod
    async def delete_save(db: AsyncSession, session_id: UUID) -> bool:
        """Delete a saved game

        Args:
            db: Database session
            session_id: Game session ID to delete

        Returns:
            True if save was deleted, False if not found
        """
        save_key = f"save:{session_id}"
        if not session_service.redis:
            return False

        # Delete from Redis
        deleted = await session_service.redis.delete(save_key)  # type: ignore[misc]
        return deleted > 0
