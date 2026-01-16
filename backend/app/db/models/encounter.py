"""
Encounter models for general and combat encounters
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Encounter(Base):
    """General encounter model"""

    __tablename__ = "encounters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    participants: Mapped[list] = mapped_column(JSONB, nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Additional data stored as JSONB
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<Encounter(id={self.id}, name={self.name})>"


class CombatEncounter(Base):
    """Combat encounter tracking model"""

    __tablename__ = "combat_encounters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Combat state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    current_turn: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Participants: list of {character_id, name, initiative, hp_current, hp_max, ac, is_enemy}
    participants: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Turn order: sorted list of participant indices
    turn_order: Mapped[list] = mapped_column(JSONB, nullable=False)

    # Combat log: list of action descriptions
    combat_log: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    session = relationship("GameSession", back_populates="combat_encounters")

    def __repr__(self) -> str:
        return f"<CombatEncounter(id={self.id}, session_id={self.session_id}, round={self.round_number})>"
