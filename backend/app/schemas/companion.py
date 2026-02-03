"""
Pydantic schemas for companion-related API requests and responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CompanionChatRequest(BaseModel):
    """Request to send a message to a companion."""

    companion_id: UUID = Field(..., description="ID of the companion to chat with")
    message: str = Field(..., min_length=1, max_length=2000, description="Message to send")
    share_with_dm: bool = Field(
        default=False, description="Whether to share this conversation with the DM"
    )


class CompanionChatResponse(BaseModel):
    """Response from companion chat."""

    message_id: UUID = Field(..., description="ID of the saved message")
    companion_response: str = Field(..., description="Companion's response")
    companion_message_id: UUID = Field(..., description="ID of the companion's response message")


class CompanionConversationMessage(BaseModel):
    """A single message in a companion conversation."""

    id: UUID
    companion_id: UUID
    character_id: UUID
    role: str  # "player" or "companion"
    message: str
    shared_with_dm: bool
    created_at: datetime

    class Config:
        from_attributes = True
