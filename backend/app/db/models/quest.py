"""
Quest model for quests assigned to characters
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
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
from app.db.models.enums import QuestState


class Quest(Base):
    """Quest model"""

    __tablename__ = "quests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    state: Mapped[QuestState] = mapped_column(
        Enum(
            QuestState,
            values_callable=lambda x: [e.value for e in x],
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
        default=QuestState.NOT_STARTED,
        index=True,
    )

    # Quest giver (optional NPC reference)
    quest_giver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id", ondelete="SET NULL"), nullable=True
    )

    # Rewards (stored as JSONB)
    # Format: {"xp": 100, "gold": 50, "items": ["Potion of Healing"]}
    rewards: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    objectives = relationship(
        "QuestObjective", back_populates="quest", cascade="all, delete-orphan"
    )
    character_quests = relationship(
        "CharacterQuest", back_populates="quest", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Quest(id={self.id}, title={self.title}, state={self.state})>"


class QuestObjective(Base):
    """Quest objective model"""

    __tablename__ = "quest_objectives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quests.id", ondelete="CASCADE"), nullable=False, index=True
    )

    description: Mapped[str] = mapped_column(Text, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)  # Display order
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    quest = relationship("Quest", back_populates="objectives")

    def __repr__(self) -> str:
        return f"<QuestObjective(id={self.id}, quest_id={self.quest_id}, completed={self.is_completed})>"
