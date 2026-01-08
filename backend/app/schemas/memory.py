"""Schemas for adventure memory system"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    """Schema for creating a new memory"""

    session_id: UUID
    event_type: str = Field(..., description="Type of event (combat, dialogue, discovery, etc.)")
    content: str = Field(..., min_length=1, description="Description of the event")
    importance: int = Field(5, ge=1, le=10, description="Importance score (1-10)")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    npcs_involved: Optional[List[str]] = Field(None, description="NPC names/IDs")
    locations: Optional[List[str]] = Field(None, description="Location names")
    items_involved: Optional[List[str]] = Field(None, description="Item names")


class MemoryResponse(BaseModel):
    """Schema for memory response"""

    id: UUID
    session_id: UUID
    event_type: str
    content: str
    importance: int
    timestamp: datetime
    tags: Optional[List[str]]
    npcs_involved: Optional[List[str]]
    locations: Optional[List[str]]
    items_involved: Optional[List[str]]
    created_at: datetime

    class Config:
        from_attributes = True


class MemorySearchRequest(BaseModel):
    """Schema for semantic memory search"""

    session_id: UUID
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(10, ge=1, le=50, description="Max results to return")
    min_importance: Optional[int] = Field(
        None, ge=1, le=10, description="Minimum importance filter"
    )
    event_types: Optional[List[str]] = Field(None, description="Filter by event types")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")


class MemorySearchResponse(BaseModel):
    """Schema for memory search results"""

    memories: List[MemoryResponse]
    total: int
    query: str


class MemoryContextResponse(BaseModel):
    """Schema for AI DM context injection"""

    relevant_memories: List[str] = Field(description="Formatted memories for AI context")
    memory_ids: List[UUID] = Field(description="IDs of memories used")
    context_length: int = Field(description="Total character count of memories")
