"""Conversation history API router."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.schemas.message import (
    ConversationHistoryResponse,
    MessageCreate,
    MessageResponse,
)
from app.services.conversation_service import ConversationService
from app.services.redis_service import session_service

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
