"""SQLAlchemy database models for Mistral Realms"""
import uuid
from datetime import datetime
from typing import Optional
from enum import Enum as PyEnum

from sqlalchemy import (
    String, Integer, Boolean, DateTime, Text, Enum, JSON, ForeignKey,
    Index, UniqueConstraint
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
    FIGHTER = "Fighter"
    WIZARD = "Wizard"
    ROGUE = "Rogue"
    CLERIC = "Cleric"


class CharacterRace(str, PyEnum):
    """D&D 5e character races"""
    HUMAN = "Human"
    ELF = "Elf"
    DWARF = "Dwarf"
    HALFLING = "Halfling"


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
        Enum(CharacterType),
        nullable=False,
        default=CharacterType.PLAYER,
        index=True
    )
    character_class: Mapped[CharacterClass] = mapped_column(
        Enum(CharacterClass),
        nullable=False
    )
    race: Mapped[CharacterRace] = mapped_column(
        Enum(CharacterRace),
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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
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
        Enum(MessageRole),
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
