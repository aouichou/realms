"""Adventure generation schemas"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SceneStructure(BaseModel):
    """Structure for a single scene in an adventure"""

    scene_number: int
    title: str
    description: str
    encounters: list[str] = Field(default_factory=list)
    npcs: list[dict[str, Any]] = Field(default_factory=list)
    loot: list[dict[str, Any]] = Field(default_factory=list)


class AdventureCreate(BaseModel):
    """Schema for creating a new adventure"""

    character_id: UUID
    setting: str = Field(..., description="Adventure setting (e.g., haunted_castle)")
    goal: str = Field(..., description="Adventure goal (e.g., rescue_mission)")
    tone: str = Field(..., description="Adventure tone (e.g., epic_heroic)")


class AdventureResponse(BaseModel):
    """Schema for adventure API responses"""

    id: UUID
    character_id: UUID
    setting: str
    goal: str
    tone: str
    title: str
    description: str
    scenes: list[dict[str, Any]]
    is_completed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdventureUpdate(BaseModel):
    """Schema for updating an adventure"""

    title: str | None = None
    description: str | None = None
    scenes: list[dict[str, Any]] | None = None
    is_completed: bool | None = None
