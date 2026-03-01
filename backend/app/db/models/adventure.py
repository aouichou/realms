"""
Adventure and AdventureMemory models for RPG adventures and AI DM memory storage.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback if pgvector is not installed
    from sqlalchemy import ARRAY, Float

    Vector = lambda _: ARRAY(Float)  # noqa: E731

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import EventType


class Adventure(Base):
    """Custom generated adventure model"""

    __tablename__ = "adventures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Questionnaire responses
    setting: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "haunted_castle"
    goal: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "rescue_mission"
    tone: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "epic_heroic"

    # Generated content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Adventure structure
    # Format: [{"scene_number": 1, "title": "...", "description": "...", "encounters": [...], "npcs": [...], "loot": [...]}, ...]
    scenes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)

    # Metadata
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    character = relationship("Character")

    def __repr__(self) -> str:
        return f"<Adventure(id={self.id}, title='{self.title}', character_id={self.character_id})>"


class AdventureMemory(Base):
    """Memory storage for AI DM with semantic search via pgvector"""

    __tablename__ = "adventure_memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Event classification
    event_type: Mapped[EventType] = mapped_column(
        Enum(
            EventType,
            values_callable=lambda x: [e.value for e in x],
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )

    # Content and embedding
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Embedding stored as vector(1024) in PostgreSQL via pgvector extension
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1024), nullable=True)

    # Importance scoring (1-10 scale)
    importance: Mapped[int] = mapped_column(Integer, default=5, nullable=False, index=True)

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Tags and relationships
    tags: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )  # ["combat", "boss_fight"]
    npcs_involved: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )  # [npc_name, ...]  Changed from UUID to String for unnamed NPCs
    locations: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )  # ["Goblin Cave", "Forest"]
    items_involved: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )  # ["Magic Sword", "Key"]

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    session = relationship("GameSession", back_populates="memories")

    def __repr__(self) -> str:
        return f"<AdventureMemory(id={self.id}, event_type={self.event_type}, importance={self.importance})>"
