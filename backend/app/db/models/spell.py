"""
Spell model for D&D 5e spells
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import CastingTime, SpellSchool


class Spell(Base):
    """Spell model for D&D 5e spells"""

    __tablename__ = "spells"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 0 = cantrip
    school: Mapped[SpellSchool] = mapped_column(
        Enum(
            SpellSchool,
            values_callable=lambda x: [e.value for e in x],
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
    )

    # Casting details
    casting_time: Mapped[CastingTime] = mapped_column(
        Enum(
            CastingTime,
            values_callable=lambda x: [e.value for e in x],
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
    )
    range: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., "30 feet", "Self", "Touch"
    duration: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., "Instantaneous", "1 minute"

    # Components
    verbal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    somatic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    material: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )  # Material components if any

    # Spell details
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_concentration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_ritual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Damage/healing if applicable
    damage_dice: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # e.g., "1d6", "3d8"
    damage_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # e.g., "fire", "cold"

    # Upcasting formula for damage scaling (e.g., "+1d6" means add 1d6 per level above base)
    upcast_damage_dice: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # e.g., "+1d6", "+1d8", "+1"

    # Material component cost tracking
    material_cost: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Cost in gold pieces
    material_consumed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Whether material is consumed on casting

    # Saving throw if applicable
    save_ability: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # e.g., "dexterity", "wisdom"

    # Classes that can learn this spell
    available_to_classes: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=dict
    )  # {"wizard": True, "cleric": True}

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    character_spells = relationship("CharacterSpell", back_populates="spell")

    # Indexes
    __table_args__ = (Index("ix_spells_level_school", "level", "school"),)

    def __repr__(self) -> str:
        return f"<Spell(id={self.id}, name={self.name}, level={self.level})>"
