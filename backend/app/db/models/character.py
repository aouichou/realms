"""
Character model for players, companions, and NPCs
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import (
    CharacterClass,
    CharacterRace,
    CharacterType,
    ConditionType,
)


class Character(Base):
    """Character model for players, companions, and NPCs"""

    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,  # NPCs don't belong to users
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    character_type: Mapped[CharacterType] = mapped_column(
        Enum(
            CharacterType,
            values_callable=lambda x: [e.value for e in x],
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
        default=CharacterType.PLAYER,
        index=True,
    )
    character_class: Mapped[CharacterClass] = mapped_column(
        Enum(
            CharacterClass,
            values_callable=lambda x: [e.value for e in x],
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
    )
    race: Mapped[CharacterRace] = mapped_column(
        Enum(
            CharacterRace,
            values_callable=lambda x: [e.value for e in x],
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
    )
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Hit Points
    hp_current: Mapped[int] = mapped_column(Integer, nullable=False)
    hp_max: Mapped[int] = mapped_column(Integer, nullable=False)

    # Ability Scores
    strength: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    dexterity: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    constitution: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    intelligence: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    wisdom: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    charisma: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # Carrying capacity (calculated as STR * 15 lbs per D&D 5e rules)
    # Stored for quick access, should be updated when strength changes
    carrying_capacity: Mapped[int] = mapped_column(Integer, default=150, nullable=False)

    # Spell slots tracking (for spellcasting classes)
    # Format: {"1": {"total": 2, "used": 0}, "2": {"total": 0, "used": 0}, ...}
    spell_slots: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    # Active concentration tracking (UUID of spell being concentrated on)
    active_concentration_spell: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Skill proficiencies (list of skill names)
    skill_proficiencies: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    # Background information
    background_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    background_description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    background_skill_proficiencies: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, default=list
    )

    # Known spells (for Bard, Sorcerer, Ranger, Warlock, etc.)
    known_spells: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    # Prepared spells (for Wizard, Cleric, Druid, Paladin)
    prepared_spells: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    # Cantrips known
    cantrips: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    # ASI distribution tracking
    # Format: {"4": {"strength": 2}, "8": {"dexterity": 1, "constitution": 1}, ...}
    asi_distribution: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)

    # Experience points for leveling
    experience_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # D&D 5e Currency System (gp = gold, sp = silver, cp = copper)
    # Conversion: 1 gp = 10 sp = 100 cp
    gold: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Gold pieces")
    silver: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Silver pieces")
    copper: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Copper pieces")

    # Additional attributes for AI companions and NPCs
    background: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personality: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # D&D 5e Personality System (Step 5 of character creation)
    personality_trait: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ideal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bond: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    flaw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Character motivation (Step 6 of character creation)
    motivation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
        comment="Soft delete timestamp",
    )

    # Relationships
    user = relationship("User", back_populates="characters")
    game_sessions = relationship(
        "GameSession",
        back_populates="character",
        foreign_keys="GameSession.character_id",
        cascade="all, delete-orphan",
    )
    companion_sessions = relationship(
        "GameSession", back_populates="companion", foreign_keys="GameSession.companion_id"
    )
    items = relationship("Item", back_populates="character", cascade="all, delete-orphan")
    character_spells = relationship(
        "CharacterSpell", back_populates="character", cascade="all, delete-orphan"
    )
    conditions = relationship(
        "CharacterCondition", back_populates="character", cascade="all, delete-orphan"
    )
    companions = relationship("Companion", back_populates="character", cascade="all, delete-orphan")
    active_effects = relationship(
        "ActiveEffect", back_populates="character", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (Index("ix_characters_user_type", "user_id", "character_type"),)

    def __repr__(self) -> str:
        return f"<Character(id={self.id}, name={self.name}, class={self.character_class})>"


class CharacterSpell(Base):
    """Junction table for character spells (known/prepared)"""

    __tablename__ = "character_spells"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    spell_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("spells.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Spell status for this character
    is_known: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_prepared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    character = relationship("Character", back_populates="character_spells")
    spell = relationship("Spell", back_populates="character_spells")

    # Indexes
    __table_args__ = (
        Index("ix_character_spells_char_spell", "character_id", "spell_id", unique=True),
        Index("ix_character_spells_prepared", "character_id", "is_prepared"),
    )

    def __repr__(self) -> str:
        return f"<CharacterSpell(character_id={self.character_id}, spell_id={self.spell_id})>"


class CharacterCondition(Base):
    """Character condition tracking model"""

    __tablename__ = "character_conditions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    condition: Mapped[ConditionType] = mapped_column(
        Enum(
            ConditionType,
            values_callable=lambda x: [e.value for e in x],
            create_type=False,
            native_enum=False,
        ),
        nullable=False,
    )

    # Duration in rounds (combat) or minutes (out of combat), 0 = indefinite
    duration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Source of condition (spell name, ability, etc.)
    source: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    character = relationship("Character", back_populates="conditions")

    def __repr__(self) -> str:
        return f"<CharacterCondition(id={self.id}, condition={self.condition}, character_id={self.character_id})>"


class CharacterQuest(Base):
    """Character-Quest relationship (tracks which characters have which quests)"""

    __tablename__ = "character_quests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quests.id", ondelete="CASCADE"), nullable=False, index=True
    )

    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    character = relationship("Character")
    quest = relationship("Quest", back_populates="character_quests")

    # Unique constraint - character can only have quest once
    __table_args__ = (Index("ix_character_quest_unique", "character_id", "quest_id", unique=True),)

    def __repr__(self) -> str:
        return f"<CharacterQuest(character_id={self.character_id}, quest_id={self.quest_id})>"
