"""Active Effects Model

Tracks temporary buffs, debuffs, conditions, and spell effects on characters.
Examples: Bless, Haste, Poisoned, Concentrating on Spell X
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models import Character
    from app.db.models.game_session import GameSession


class EffectType(str, Enum):
    """Types of effects in D&D 5e"""

    BUFF = "buff"  # Positive effect (Bless, Haste, Bardic Inspiration)
    DEBUFF = "debuff"  # Negative effect (Bane, Slow, Faerie Fire)
    CONDITION = "condition"  # Status condition (Poisoned, Paralyzed, Stunned)
    CONCENTRATION = "concentration"  # Spell requiring concentration
    RAGE = "rage"  # Barbarian rage
    INSPIRATION = "inspiration"  # Bardic inspiration die
    TEMP_HP = "temp_hp"  # Temporary hit points
    CUSTOM = "custom"  # Other effects


class EffectDuration(str, Enum):
    """Duration types for effects"""

    ROUNDS = "rounds"  # Combat rounds
    MINUTES = "minutes"
    HOURS = "hours"
    UNTIL_LONG_REST = "until_long_rest"
    UNTIL_SHORT_REST = "until_short_rest"
    CONCENTRATION = "concentration"  # Ends if concentration broken
    PERMANENT = "permanent"  # Until removed by magic
    INSTANT = "instant"  # Applied once then removed


class ActiveEffect(Base):
    """
    Active effect on a character.

    Tracks temporary buffs, debuffs, conditions, and spell effects.
    Effects can have durations, stack, and be removed by various triggers.
    """

    __tablename__ = "active_effects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    character_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Effect identification
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    effect_type: Mapped[EffectType] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Source information
    source: Mapped[str] = mapped_column(
        String(200), nullable=True
    )  # "Bless spell", "Poisoned by trap"
    source_character_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # Who cast the spell/caused effect

    # Duration tracking
    duration_type: Mapped[EffectDuration] = mapped_column(String(50), nullable=False)
    duration_value: Mapped[int] = mapped_column(
        Integer, nullable=True
    )  # Number of rounds/minutes/hours
    rounds_remaining: Mapped[int] = mapped_column(
        Integer, nullable=True
    )  # Countdown for round-based effects
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )  # Absolute expiration time

    # Effect mechanics
    bonus_value: Mapped[int] = mapped_column(
        Integer, nullable=True, default=0
    )  # +X to rolls, AC, etc.
    dice_bonus: Mapped[str] = mapped_column(String(20), nullable=True)  # "1d4", "1d8", etc.
    advantage: Mapped[bool] = mapped_column(Boolean, default=False)  # Grants advantage
    disadvantage: Mapped[bool] = mapped_column(Boolean, default=False)  # Imposes disadvantage

    # Stacking rules
    stacks: Mapped[bool] = mapped_column(Boolean, default=False)  # Can multiple instances exist?
    stack_count: Mapped[int] = mapped_column(Integer, default=1)  # How many times is it stacked?

    # Concentration tracking (for spells)
    requires_concentration: Mapped[bool] = mapped_column(Boolean, default=False)
    concentration_dc: Mapped[int] = mapped_column(Integer, nullable=True, default=10)

    # Status flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_visible: Mapped[bool] = mapped_column(
        Boolean, default=True
    )  # Should players see this effect?

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    character: Mapped["Character"] = relationship("Character", back_populates="active_effects")
    session: Mapped["GameSession"] = relationship("GameSession", back_populates="active_effects")

    def __repr__(self) -> str:
        return f"<ActiveEffect(id={self.id}, name={self.name}, type={self.effect_type}, char={self.character_id})>"

    def is_expired(self) -> bool:
        """Check if effect has expired based on time or rounds."""
        if not self.is_active:
            return True

        if self.duration_type == EffectDuration.INSTANT:
            return True

        if self.rounds_remaining is not None and self.rounds_remaining <= 0:
            return True

        if self.expires_at and datetime.utcnow() >= self.expires_at:
            return True

        return False

    def decrement_duration(self) -> bool:
        """
        Decrement round-based duration by 1.

        Returns:
            True if effect expired, False if still active
        """
        if self.rounds_remaining is not None and self.rounds_remaining > 0:
            self.rounds_remaining -= 1
            if self.rounds_remaining <= 0:
                self.is_active = False
                return True
        return False

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.effect_type.value,
            "description": self.description,
            "source": self.source,
            "duration_type": self.duration_type.value,
            "rounds_remaining": self.rounds_remaining,
            "bonus_value": self.bonus_value,
            "dice_bonus": self.dice_bonus,
            "advantage": self.advantage,
            "disadvantage": self.disadvantage,
            "requires_concentration": self.requires_concentration,
            "is_active": self.is_active,
            "stack_count": self.stack_count,
        }
