"""SQLAlchemy database models for Mistral Realms"""
import uuid
from datetime import datetime
from typing import Optional
from enum import Enum as PyEnum

from sqlalchemy import (
    String, Integer, Boolean, DateTime, Text, Enum, ForeignKey,
    Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class CharacterType(str, PyEnum):
    """Character type enumeration"""
    PLAYER = "player"
    COMPANION = "companion"
    NPC = "npc"


class CharacterClass(str, PyEnum):
    """D&D 5e character classes"""
    BARBARIAN = "Barbarian"
    BARD = "Bard"
    CLERIC = "Cleric"
    DRUID = "Druid"
    FIGHTER = "Fighter"
    MONK = "Monk"
    PALADIN = "Paladin"
    RANGER = "Ranger"
    ROGUE = "Rogue"
    SORCERER = "Sorcerer"
    WARLOCK = "Warlock"
    WIZARD = "Wizard"


class CharacterRace(str, PyEnum):
    """D&D 5e character races"""
    DRAGONBORN = "Dragonborn"
    DWARF = "Dwarf"
    ELF = "Elf"
    GNOME = "Gnome"
    HALFELF = "Half-Elf"
    HALFORC = "Half-Orc"
    HALFLING = "Halfling"
    HUMAN = "Human"
    TIEFLING = "Tiefling"


class ItemType(str, PyEnum):
    """Item type categories"""
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    QUEST = "quest"
    MISC = "misc"


class SpellSchool(str, PyEnum):
    """D&D 5e schools of magic"""
    ABJURATION = "Abjuration"
    CONJURATION = "Conjuration"
    DIVINATION = "Divination"
    ENCHANTMENT = "Enchantment"
    EVOCATION = "Evocation"
    ILLUSION = "Illusion"
    NECROMANCY = "Necromancy"
    TRANSMUTATION = "Transmutation"


class CastingTime(str, PyEnum):
    """Spell casting time"""
    ACTION = "1 action"
    BONUS_ACTION = "1 bonus action"
    REACTION = "1 reaction"
    MINUTE = "1 minute"
    TEN_MINUTES = "10 minutes"
    HOUR = "1 hour"
    RITUAL = "1 minute (ritual)"



class MessageRole(str, PyEnum):
    """Conversation message roles"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class User(Base):
    """User account model"""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    characters = relationship("Character", back_populates="user", cascade="all, delete-orphan")
    game_sessions = relationship("GameSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"


class Character(Base):
    """Character model for players, companions, and NPCs"""
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,  # NPCs don't belong to users
        index=True
    )
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    character_type: Mapped[CharacterType] = mapped_column(
        Enum(CharacterType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=CharacterType.PLAYER,
        index=True
    )
    character_class: Mapped[CharacterClass] = mapped_column(
        Enum(CharacterClass, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    race: Mapped[CharacterRace] = mapped_column(
        Enum(CharacterRace, values_callable=lambda x: [e.value for e in x]),
        nullable=False
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
    
    # Additional attributes for AI companions and NPCs
    background: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personality: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="characters")
    player_sessions = relationship(
        "GameSession",
        back_populates="character",
        foreign_keys="GameSession.character_id",
        cascade="all, delete-orphan"
    )
    companion_sessions = relationship(
        "GameSession",
        back_populates="companion",
        foreign_keys="GameSession.companion_id"
    )
    items = relationship("Item", back_populates="character", cascade="all, delete-orphan")
    character_spells = relationship("CharacterSpell", back_populates="character", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("ix_characters_user_type", "user_id", "character_type"),
    )

    def __repr__(self) -> str:
        return f"<Character(id={self.id}, name={self.name}, class={self.character_class})>"


class GameSession(Base):
    """Game session model tracking active adventures"""
    __tablename__ = "game_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    companion_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    current_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Flexible game state storage (inventory, quest log, world state, etc.)
    state_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        index=True
    )

    # Relationships
    user = relationship("User", back_populates="game_sessions")
    character = relationship(
        "Character",
        back_populates="player_sessions",
        foreign_keys=[character_id]
    )
    companion = relationship(
        "Character",
        back_populates="companion_sessions",
        foreign_keys=[companion_id]
    )
    messages = relationship("ConversationMessage", back_populates="session", cascade="all, delete-orphan")
    combat_encounters = relationship("CombatEncounter", back_populates="session", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("ix_game_sessions_user_active", "user_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<GameSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class ConversationMessage(Base):
    """Conversation message model for persistent chat history"""
    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    # Relationships
    session = relationship("GameSession", back_populates="messages")

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ConversationMessage(id={self.id}, session_id={self.session_id}, role={self.role})>"


class Item(Base):
    """Item model for character inventory"""
    __tablename__ = "items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    item_type: Mapped[ItemType] = mapped_column(
        Enum(ItemType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    
    # Weight in pounds (D&D 5e standard)
    weight: Mapped[float] = mapped_column(Integer, default=0, nullable=False)
    
    # Value in gold pieces
    value: Mapped[float] = mapped_column(Integer, default=0, nullable=False)
    
    # Flexible storage for item-specific properties
    # Examples: damage_dice, ac_bonus, attack_bonus, charges, effects, etc.
    properties: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Inventory management
    equipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    character = relationship("Character", back_populates="items")

    # Indexes
    __table_args__ = (
        Index("ix_items_character_type", "character_id", "item_type"),
        Index("ix_items_character_equipped", "character_id", "equipped"),
    )

    def __repr__(self) -> str:
        return f"<Item(id={self.id}, name={self.name}, type={self.item_type})>"


class Spell(Base):
    """Spell model for D&D 5e spells"""
    __tablename__ = "spells"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 0 = cantrip
    school: Mapped[SpellSchool] = mapped_column(
        Enum(SpellSchool, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    
    # Casting details
    casting_time: Mapped[CastingTime] = mapped_column(
        Enum(CastingTime, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    range: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "30 feet", "Self", "Touch"
    duration: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "Instantaneous", "1 minute"
    
    # Components
    verbal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    somatic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    material: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # Material components if any
    
    # Spell details
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_concentration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_ritual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Damage/healing if applicable
    damage_dice: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g., "1d6", "3d8"
    damage_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g., "fire", "cold"
    
    # Saving throw if applicable
    save_ability: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g., "dexterity", "wisdom"
    
    # Classes that can learn this spell
    available_to_classes: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict
    )  # {"wizard": True, "cleric": True}
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    character_spells = relationship("CharacterSpell", back_populates="spell")

    # Indexes
    __table_args__ = (
        Index("ix_spells_level_school", "level", "school"),
    )

    def __repr__(self) -> str:
        return f"<Spell(id={self.id}, name={self.name}, level={self.level})>"


class CharacterSpell(Base):
    """Junction table for character spells (known/prepared)"""
    __tablename__ = "character_spells"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    spell_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("spells.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Spell status for this character
    is_known: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_prepared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

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


class CombatEncounter(Base):
    """Combat encounter tracking model"""
    __tablename__ = "combat_encounters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
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
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    session = relationship("GameSession", back_populates="combat_encounters")

    # Indexes
    __table_args__ = (
        Index("ix_combat_session_active", "session_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<CombatEncounter(id={self.id}, session_id={self.session_id}, active={self.is_active})>"

