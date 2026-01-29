"""
Companion database model for AI-driven NPCs that travel with players.
Companions are linked to creatures for stats but have unique personalities.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class Companion(Base):
    """
    AI-driven companion NPC that travels with the player.

    Companions use creature stat blocks for combat but have unique:
    - Personality traits and goals
    - Conversation memory
    - Relationship dynamics with player
    - Individual avatars
    """

    __tablename__ = "companions"

    id = Column(Integer, primary_key=True, index=True)

    # Relationships
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False, index=True)
    creature_id = Column(Integer, ForeignKey("creatures.id"), nullable=False, index=True)

    # Core identity
    name = Column(String(100), nullable=False)  # Companion's unique name (e.g., "Elara Swiftwind")
    creature_name = Column(
        String(100), nullable=False
    )  # Original creature type (e.g., "Elf Scout")

    # AI personality & story
    personality = Column(Text, nullable=False)  # "brave, loyal, curious, witty"
    goals = Column(Text)  # "Find her missing brother"
    secrets = Column(Text)  # Hidden motivations known only to companion AI
    background = Column(Text)  # Backstory for avatar generation and roleplay

    # Relationship dynamics
    relationship_status = Column(
        String(50), default="just_met"
    )  # just_met, ally, friend, trusted, suspicious
    loyalty = Column(Integer, default=50)  # 0-100, affects behavior and decisions

    # Combat stats (copied from creature on creation, modified during play)
    hp = Column(Integer, nullable=False)
    max_hp = Column(Integer, nullable=False)
    ac = Column(Integer, nullable=False)

    # Ability scores (copied from creature)
    strength = Column(Integer)
    dexterity = Column(Integer)
    constitution = Column(Integer)
    intelligence = Column(Integer)
    wisdom = Column(Integer)
    charisma = Column(Integer)

    # Additional combat data from creature
    actions = Column(JSONB)  # Available actions in combat
    special_traits = Column(JSONB)  # Special abilities
    speed = Column(JSONB)  # Movement speeds

    # AI memory system
    conversation_memory = Column(JSONB, default=list)  # Recent 20 exchanges
    important_events = Column(JSONB, default=list)  # Key story moments

    # Visual representation
    avatar_url = Column(String(500))  # Generated companion portrait

    # State management
    is_active = Column(Boolean, default=True)  # Present in current scene
    is_alive = Column(Boolean, default=True)  # Has companion died?
    death_save_successes = Column(Integer, default=0)  # Combat tracking
    death_save_failures = Column(Integer, default=0)  # Combat tracking

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    character = relationship("Character", back_populates="companions")
    creature = relationship("Creature")

    def to_dict(self) -> dict:
        """Convert companion to dictionary for API responses."""
        return {
            "id": self.id,
            "character_id": self.character_id,
            "name": self.name,
            "creature_name": self.creature_name,
            "personality": self.personality,
            "goals": self.goals,
            "relationship_status": self.relationship_status,
            "loyalty": self.loyalty,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "ac": self.ac,
            "strength": self.strength,
            "dexterity": self.dexterity,
            "constitution": self.constitution,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "charisma": self.charisma,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
            "is_alive": self.is_alive,
            "actions": self.actions,
            "special_traits": self.special_traits,
            "speed": self.speed,
        }

    def get_stat_modifier(self, ability_score: int | None) -> int:
        """Calculate D&D 5e ability modifier from score."""
        if ability_score is None:
            return 0
        return (ability_score - 10) // 2

    def add_conversation_memory(self, role: str, content: str) -> None:
        """Add exchange to companion memory, keep last 20."""
        if self.conversation_memory is None:
            self.conversation_memory = []

        memory_entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Ensure it's a list before appending
        if not isinstance(self.conversation_memory, list):
            self.conversation_memory = []

        self.conversation_memory.append(memory_entry)

        # Keep only last 20 exchanges
        if isinstance(self.conversation_memory, list) and len(self.conversation_memory) > 20:
            self.conversation_memory = self.conversation_memory[-20:]

    def add_important_event(self, event: str) -> None:
        """Track key story moments."""
        if self.important_events is None:
            self.important_events = []

        event_entry = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.important_events.append(event_entry)
