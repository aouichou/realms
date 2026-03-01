"""Redis session management service."""

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import redis.asyncio as redis

from app.config import settings
from app.observability.logger import get_logger

logger = get_logger(__name__)


class RedisSessionService:
    """Service for managing game sessions in Redis."""

    # Redis key prefixes
    SESSION_STATE_PREFIX = "session:state:"
    SESSION_HISTORY_PREFIX = "session:history:"
    SESSION_TTL = 86400  # 24 hours in seconds

    # Guest token management
    GUEST_TOKEN_PREFIX = "guest:token:"
    GUEST_TOKEN_TTL = 86400 * 7  # 7 days

    def __init__(self):
        """Initialize Redis connection pool."""
        self._redis: Optional[redis.Redis] = None

    @property
    def redis(self) -> Optional[redis.Redis]:
        """Get Redis client instance."""
        return self._redis

    async def connect(self):
        """Establish Redis connection."""
        if self._redis is None:
            self._redis = await redis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
            logger.info("Redis connection established")

    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis connection closed")

    def _get_state_key(self, session_id: UUID) -> str:
        """Get Redis key for session state."""
        return f"{self.SESSION_STATE_PREFIX}{session_id}"

    def _get_history_key(self, session_id: UUID) -> str:
        """Get Redis key for conversation history."""
        return f"{self.SESSION_HISTORY_PREFIX}{session_id}"

    async def create_session_state(
        self,
        session_id: UUID,
        character_id: UUID,
        companion_id: Optional[UUID] = None,
        current_location: Optional[str] = None,
        initial_state: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create new session state in Redis.

        Args:
            session_id: Session UUID
            character_id: Player character ID
            companion_id: Optional companion character ID
            current_location: Starting location
            initial_state: Optional initial game state

        Returns:
            Created session state
        """
        await self.connect()

        state = {
            "session_id": str(session_id),
            "character_id": str(character_id),
            "companion_id": str(companion_id) if companion_id else None,
            "current_location": current_location,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "state": initial_state or {},
        }

        key = self._get_state_key(session_id)
        if self._redis:
            await self._redis.setex(key, self.SESSION_TTL, json.dumps(state))

        logger.info(f"Created session state: {session_id}")
        return state

    async def get_session_state(self, session_id: UUID) -> Optional[dict[str, Any]]:
        """Get session state from Redis.

        Args:
            session_id: Session UUID

        Returns:
            Session state or None if not found
        """
        await self.connect()

        key = self._get_state_key(session_id)
        data = await self._redis.get(key)  # type: ignore[misc]

        if data:
            return json.loads(data)
        return None

    async def update_session_state(
        self,
        session_id: UUID,
        current_location: Optional[str] = None,
        state_updates: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Update session state in Redis.

        Args:
            session_id: Session UUID
            current_location: New location (optional)
            state_updates: State updates to merge (optional)

        Returns:
            Updated session state or None if session not found
        """
        await self.connect()

        current_state = await self.get_session_state(session_id)
        if not current_state:
            return None

        # Update fields
        if current_location is not None:
            current_state["current_location"] = current_location

        if state_updates:
            current_state["state"].update(state_updates)

        current_state["last_updated"] = datetime.now(timezone.utc).isoformat()

        # Save back to Redis with TTL refresh
        key = self._get_state_key(session_id)
        if self._redis:
            await self._redis.setex(key, self.SESSION_TTL, json.dumps(current_state))

        logger.info(f"Updated session state: {session_id}")
        return current_state

    async def delete_session_state(self, session_id: UUID) -> bool:
        """Delete session state from Redis.

        Args:
            session_id: Session UUID

        Returns:
            True if deleted, False if not found
        """
        await self.connect()

        state_key = self._get_state_key(session_id)
        history_key = self._get_history_key(session_id)

        if not self._redis:
            return False

        deleted = await self._redis.delete(state_key, history_key)

        if deleted > 0:
            logger.info(f"Deleted session state: {session_id}")
            return True
        return False

    async def add_message_to_history(
        self, session_id: UUID, role: str, content: str, tokens_used: Optional[int] = None
    ) -> int:
        """Add a message to conversation history.

        Args:
            session_id: Session UUID
            role: Message role (user, assistant, system)
            content: Message content
            tokens_used: Optional token count

        Returns:
            New history length
        """
        await self.connect()

        message = {
            "role": role,
            "content": content,
            "tokens_used": tokens_used,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if not self._redis:
            return 0

        key = self._get_history_key(session_id)
        length = await self._redis.rpush(key, json.dumps(message))  # type: ignore[misc]

        # Set TTL on first message
        if length == 1:
            await self._redis.expire(key, self.SESSION_TTL)

        logger.debug(f"Added message to session {session_id} history (length: {length})")
        return length

    async def get_conversation_history(
        self, session_id: UUID, limit: Optional[int] = 20
    ) -> list[dict[str, Any]]:
        """Get recent conversation history.

        Args:
            session_id: Session UUID
            limit: Maximum number of messages to retrieve (default: 20)

        Returns:
            List of messages, newest first
        """
        await self.connect()

        if not self._redis:
            return []

        key = self._get_history_key(session_id)

        # Get last N messages
        msg_limit = limit if limit is not None else 20
        messages = await self._redis.lrange(key, -msg_limit, -1)  # type: ignore[misc]

        # Parse and reverse (newest first)
        parsed = [json.loads(msg) for msg in messages]
        parsed.reverse()

        return parsed

    async def clear_conversation_history(self, session_id: UUID) -> bool:
        """Clear conversation history for a session.

        Args:
            session_id: Session UUID

        Returns:
            True if cleared, False if not found
        """
        await self.connect()

        if not self._redis:
            return False

        key = self._get_history_key(session_id)
        deleted = await self._redis.delete(key)

        if deleted > 0:
            logger.info(f"Cleared conversation history: {session_id}")
            return True
        return False

    async def refresh_ttl(self, session_id: UUID) -> bool:
        """Refresh TTL for session state and history.

        Args:
            session_id: Session UUID

        Returns:
            True if refreshed, False if session not found
        """
        await self.connect()

        if not self._redis:
            return False

        state_key = self._get_state_key(session_id)
        history_key = self._get_history_key(session_id)

        refreshed = await self._redis.expire(state_key, self.SESSION_TTL)
        await self._redis.expire(history_key, self.SESSION_TTL)

        return refreshed > 0

    # ------------------------------------------------------------------
    # Guest token management
    # ------------------------------------------------------------------

    async def store_guest_token(self, guest_token: str, user_id: str) -> None:
        """Store a guest token mapping to user ID in Redis."""
        await self.connect()
        if self._redis:
            key = f"{self.GUEST_TOKEN_PREFIX}{guest_token}"
            await self._redis.setex(key, self.GUEST_TOKEN_TTL, user_id)
            logger.info(f"Stored guest token mapping for user {user_id}")

    async def get_guest_user_id(self, guest_token: str) -> str | None:
        """Look up user ID from guest token."""
        await self.connect()
        if self._redis:
            key = f"{self.GUEST_TOKEN_PREFIX}{guest_token}"
            return await self._redis.get(key)
        return None

    async def delete_guest_token(self, guest_token: str) -> None:
        """Remove a guest token (after account claiming)."""
        await self.connect()
        if self._redis:
            key = f"{self.GUEST_TOKEN_PREFIX}{guest_token}"
            await self._redis.delete(key)
            logger.info("Deleted guest token")

    # Token revocation
    TOKEN_BLACKLIST_PREFIX = "token:revoked:"

    async def revoke_token(self, jti: str, expires_in: int) -> None:
        """Add a token JTI to the blacklist until it expires naturally."""
        await self.connect()
        if self._redis:
            key = f"{self.TOKEN_BLACKLIST_PREFIX}{jti}"
            await self._redis.setex(key, expires_in, "1")

    async def is_token_revoked(self, jti: str) -> bool:
        """Check if a token has been revoked."""
        await self.connect()
        if self._redis:
            key = f"{self.TOKEN_BLACKLIST_PREFIX}{jti}"
            return await self._redis.exists(key) > 0
        return False  # Fail open if Redis unavailable


# Global session service instance
session_service = RedisSessionService()
