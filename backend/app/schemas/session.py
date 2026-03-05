"""Session schemas for API request/response validation."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    """Schema for creating a new game session."""

    character_id: UUID = Field(..., description="Player character ID")
    companion_id: Optional[UUID] = Field(None, description="Optional companion character ID")
    current_location: Optional[str] = Field(None, max_length=255, description="Starting location")


class SessionUpdate(BaseModel):
    """Schema for updating a session."""

    model_config = {"extra": "forbid"}

    current_location: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = Field(default=None)


class SessionStateUpdate(BaseModel):
    """Schema for updating session state in Redis."""

    current_location: Optional[str] = None
    state_data: Optional[dict[str, Any]] = Field(None, description="Game state data")


class SessionResponse(BaseModel):
    """Schema for session API responses."""

    id: UUID
    user_id: Optional[UUID] = None
    character_id: UUID
    companion_id: Optional[UUID] = None
    is_active: bool
    current_location: Optional[str] = None
    started_at: datetime
    last_activity_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionWithState(SessionResponse):
    """Session response including active state from Redis."""

    state: Optional[dict[str, Any]] = Field(None, description="Active session state from Redis")
    conversation_history: Optional[list[dict[str, str]]] = Field(
        None, description="Recent messages"
    )
