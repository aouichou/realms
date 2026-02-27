"""Character schemas for API request/response validation."""

from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CharacterBase(BaseModel):
    """Base character schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100, description="Character name")
    character_class: str = Field(..., description="D&D class: Fighter, Wizard, Rogue, or Cleric")
    race: str = Field(..., description="D&D race: Human, Elf, Dwarf, or Halfling")
    background: Optional[str] = Field(None, description="Character backstory")
    personality: Optional[str] = Field(None, description="Personality traits for AI")

    @field_validator("character_class")
    @classmethod
    def validate_class(cls, v: str) -> str:
        """Validate D&D class."""
        valid_classes = [
            "Barbarian",
            "Bard",
            "Cleric",
            "Druid",
            "Fighter",
            "Monk",
            "Paladin",
            "Ranger",
            "Rogue",
            "Sorcerer",
            "Warlock",
            "Wizard",
        ]
        # Case-insensitive validation with capitalization
        v_capitalized = v.capitalize()
        if v_capitalized not in valid_classes:
            raise ValueError(f"Invalid class. Must be one of: {', '.join(valid_classes)}")
        return v_capitalized

    @field_validator("race")
    @classmethod
    def validate_race(cls, v: str) -> str:
        """Validate D&D race."""
        valid_races = [
            "Dragonborn",
            "Dwarf",
            "Elf",
            "Gnome",
            "Half-Elf",
            "Halfling",
            "Half-Orc",
            "Human",
            "Tiefling",
        ]
        # Case-insensitive validation
        for race in valid_races:
            if v.lower() == race.lower():
                return race
        raise ValueError(f"Invalid race. Must be one of: {', '.join(valid_races)}")


class AbilityScores(BaseModel):
    """Ability scores sub-schema."""

    strength: int = Field(..., ge=1, le=20)
    dexterity: int = Field(..., ge=1, le=20)
    constitution: int = Field(..., ge=1, le=20)
    intelligence: int = Field(..., ge=1, le=20)
    wisdom: int = Field(..., ge=1, le=20)
    charisma: int = Field(..., ge=1, le=20)


class CharacterCreate(CharacterBase):
    """Schema for creating a new character."""

    level: int = Field(1, ge=1, le=20, description="Character level (1-20)")

    # Accept either individual stats OR ability_scores object
    ability_scores: Optional[AbilityScores] = None
    strength: Optional[int] = Field(None, ge=1, le=20, description="Strength stat (1-20)")
    dexterity: Optional[int] = Field(None, ge=1, le=20, description="Dexterity stat (1-20)")
    constitution: Optional[int] = Field(None, ge=1, le=20, description="Constitution stat (1-20)")
    intelligence: Optional[int] = Field(None, ge=1, le=20, description="Intelligence stat (1-20)")
    wisdom: Optional[int] = Field(None, ge=1, le=20, description="Wisdom stat (1-20)")
    charisma: Optional[int] = Field(None, ge=1, le=20, description="Charisma stat (1-20)")

    # New D&D 5e fields
    skill_proficiencies: Optional[list[str]] = Field(None, description="List of proficient skills")
    background_name: Optional[str] = Field(
        None, max_length=100, description="Character background name"
    )
    background_description: Optional[str] = Field(
        None, max_length=1000, description="Character background story"
    )
    background_skill_proficiencies: Optional[list[str]] = Field(
        None, description="Skills granted by background"
    )
    known_spells: Optional[list[str]] = Field(
        None, description="List of known spells (for known casters)"
    )
    cantrips: Optional[list[str]] = Field(None, description="List of cantrips known")
    asi_distribution: Optional[dict] = Field(None, description="ASI distribution by level")

    def get_ability_scores(self) -> dict:
        """Get ability scores as dict, preferring ability_scores object."""
        if self.ability_scores:
            return {
                "strength": self.ability_scores.strength,
                "dexterity": self.ability_scores.dexterity,
                "constitution": self.ability_scores.constitution,
                "intelligence": self.ability_scores.intelligence,
                "wisdom": self.ability_scores.wisdom,
                "charisma": self.ability_scores.charisma,
            }
        return {
            "strength": self.strength or 10,
            "dexterity": self.dexterity or 10,
            "constitution": self.constitution or 10,
            "intelligence": self.intelligence or 10,
            "wisdom": self.wisdom or 10,
            "charisma": self.charisma or 10,
        }


class CharacterUpdate(BaseModel):
    """Schema for updating a character - all fields are optional."""

    model_config = {"extra": "forbid"}

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    background: Optional[str] = Field(default=None)
    personality: Optional[str] = Field(default=None)
    hp_current: Optional[int] = Field(default=None, ge=0)
    skill_proficiencies: Optional[list[str]] = Field(default=None)
    background_name: Optional[str] = Field(default=None, max_length=100)
    background_description: Optional[str] = Field(default=None, max_length=1000)
    background_skill_proficiencies: Optional[list[str]] = Field(default=None)
    # D&D 5e Personality System
    personality_trait: Optional[str] = Field(default=None)
    ideal: Optional[str] = Field(default=None)
    bond: Optional[str] = Field(default=None)
    flaw: Optional[str] = Field(default=None)
    # Character motivation
    motivation: Optional[str] = Field(default=None, max_length=100)


class CharacterResponse(CharacterBase):
    """Schema for character API responses."""

    model_config = {"from_attributes": True}

    id: UUID
    user_id: Optional[UUID] = None
    character_type: str
    level: int
    hp_current: int
    hp_max: int
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int
    skill_proficiencies: Optional[list[str]] = None
    background_name: Optional[str] = None
    background_description: Optional[str] = None
    background_skill_proficiencies: Optional[list[str]] = None
    # D&D 5e Personality System
    personality_trait: Optional[str] = None
    ideal: Optional[str] = None
    bond: Optional[str] = None
    flaw: Optional[str] = None
    # Character motivation
    motivation: Optional[str] = None
    # D&D 5e Currency
    gold: int = Field(default=0, description="Gold pieces")
    silver: int = Field(default=0, description="Silver pieces")
    copper: int = Field(default=0, description="Copper pieces")
    created_at: datetime
    updated_at: datetime


class CharacterListResponse(BaseModel):
    """Schema for paginated character list responses."""

    characters: Sequence[CharacterResponse]
    total: int
    page: int
    page_size: int
