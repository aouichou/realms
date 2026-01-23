"""Database model for game sessions."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GameSession(Base):
    """Game session model tracking active adventures"""

    __tablename__ = "game_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    companion_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    current_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Flexible game state storage (inventory, quest log, world state, etc.)
    state_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    user = relationship("User", back_populates="game_sessions")
    character = relationship(
        "Character", back_populates="game_sessions", foreign_keys=[character_id]
    )
    companion = relationship(
        "Character", back_populates="companion_sessions", foreign_keys=[companion_id]
    )
    messages = relationship(
        "ConversationMessage", back_populates="session", cascade="all, delete-orphan"
    )
    combat_encounters = relationship(
        "CombatEncounter", back_populates="session", cascade="all, delete-orphan"
    )
    memories = relationship(
        "AdventureMemory", back_populates="session", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (Index("ix_game_sessions_user_active", "user_id", "is_active"),)

    def __repr__(self) -> str:
        return f"<GameSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"
