"""Conversation message schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Schema for creating a message."""

    session_id: UUID
    role: str = Field(..., description="Message role: user, assistant, companion, or system")
    content: str = Field(..., min_length=1)
    tokens_used: Optional[int] = Field(None, ge=0)
    scene_image_url: Optional[str] = None
    companion_id: Optional[UUID] = None  # RL-131: Link to companion if role is 'companion'


class MessageResponse(BaseModel):
    """Schema for message responses."""

    id: UUID
    session_id: UUID
    role: str
    content: str
    tokens_used: Optional[int]
    scene_image_url: Optional[str] = None
    companion_id: Optional[UUID] = None  # RL-131: Link to companion if role is 'companion'
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationHistoryResponse(BaseModel):
    """Schema for conversation history response."""

    session_id: UUID
    messages: list[MessageResponse]
    total_messages: int
    total_tokens: Optional[int] = None
