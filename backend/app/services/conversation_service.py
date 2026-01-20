"""Conversation message service for database operations."""

import uuid
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ConversationMessage
from app.schemas.message import MessageCreate


class ConversationService:
    """Service for conversation message operations."""

    @staticmethod
    async def create_message(db: AsyncSession, message_data: MessageCreate) -> ConversationMessage:
        """Create a new conversation message.

        Args:
            db: Database session
            message_data: Message creation data

        Returns:
            Created message
        """
        message = ConversationMessage(
            id=uuid.uuid4(),
            session_id=message_data.session_id,
            role=message_data.role,
            content=message_data.content,
            tokens_used=message_data.tokens_used,
            scene_image_url=message_data.scene_image_url,
        )

        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def get_session_messages(
        db: AsyncSession, session_id: UUID, limit: Optional[int] = 100, offset: int = 0
    ) -> tuple[list[ConversationMessage], int]:
        """Get messages for a session.

        Args:
            db: Database session
            session_id: Session UUID
            limit: Maximum messages to return
            offset: Pagination offset

        Returns:
            Tuple of (messages list, total count)
        """
        # Get total count
        count_result = await db.execute(
            select(func.count())
            .select_from(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
        )
        total = count_result.scalar() or 0

        # Get messages
        query = (
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.desc())
        )

        if limit:
            query = query.limit(limit)

        query = query.offset(offset)

        result = await db.execute(query)
        messages = result.scalars().all()

        # Reverse to get chronological order
        return list(reversed(messages)), total

    @staticmethod
    async def get_recent_messages(
        db: AsyncSession, session_id: UUID, count: int = 20
    ) -> list[ConversationMessage]:
        """Get recent messages for context window.

        Args:
            db: Database session
            session_id: Session UUID
            count: Number of recent messages

        Returns:
            List of recent messages in chronological order
        """
        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(count)
        )
        messages = result.scalars().all()
        return list(reversed(messages))

    @staticmethod
    async def get_total_tokens(db: AsyncSession, session_id: UUID) -> int:
        """Get total tokens used in a session.

        Args:
            db: Database session
            session_id: Session UUID

        Returns:
            Total tokens used
        """
        result = await db.execute(
            select(func.sum(ConversationMessage.tokens_used)).where(
                ConversationMessage.session_id == session_id
            )
        )
        total = result.scalar()
        return total or 0

    @staticmethod
    async def delete_session_messages(db: AsyncSession, session_id: UUID) -> int:
        """Delete all messages for a session.

        Args:
            db: Database session
            session_id: Session UUID

        Returns:
            Number of messages deleted
        """
        result = await db.execute(
            select(ConversationMessage).where(ConversationMessage.session_id == session_id)
        )
        messages = result.scalars().all()

        for message in messages:
            await db.delete(message)

        await db.commit()
        return len(messages)
