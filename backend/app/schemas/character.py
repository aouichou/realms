"""Character schemas for API request/response validation."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CharacterBase(BaseModel):
    """Base character schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="Character name")
    character_class: str = Field(..., description="D&D class: Fighter, Wizard, Rogue, or Cleric")
    race: str = Field(..., description="D&D race: Human, Elf, Dwarf, or Halfling")
    background: Optional[str] = Field(None, description="Character backstory")
    personality: Optional[str] = Field(None, description="Personality traits for AI")
    
    @field_validator('character_class')
    @classmethod
    def validate_class(cls, v: str) -> str:
        """Validate D&D class."""
        valid_classes = [
            'Barbarian', 'Bard', 'Cleric', 'Druid', 'Fighter', 'Monk',
            'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock', 'Wizard'
        ]
        # Case-insensitive validation with capitalization
        v_capitalized = v.capitalize()
        if v_capitalized not in valid_classes:
            raise ValueError(f'Invalid class. Must be one of: {", ".join(valid_classes)}')
        return v_capitalized
    
    @field_validator('race')
    @classmethod
    def validate_race(cls, v: str) -> str:
        """Validate D&D race."""
        valid_races = [
            'Dragonborn', 'Dwarf', 'Elf', 'Gnome', 'Half-Elf', 'Halfling',
            'Half-Orc', 'Human', 'Tiefling'
        ]
        # Case-insensitive validation
        for race in valid_races:
            if v.lower() == race.lower():
                return race
        raise ValueError(f'Invalid race. Must be one of: {", ".join(valid_races)}')
        return v


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
    known_spells: Optional[list[str]] = Field(None, description="List of known spells (for known casters)")
    cantrips: Optional[list[str]] = Field(None, description="List of cantrips known")
    asi_distribution: Optional[dict] = Field(None, description="ASI distribution by level")
    
    def get_ability_scores(self) -> dict:
        """Get ability scores as dict, preferring ability_scores object."""
        if self.ability_scores:
            return {
                'strength': self.ability_scores.strength,
                'dexterity': self.ability_scores.dexterity,
                'constitution': self.ability_scores.constitution,
                'intelligence': self.ability_scores.intelligence,
                'wisdom': self.ability_scores.wisdom,
                'charisma': self.ability_scores.charisma,
            }
        return {
            'strength': self.strength or 10,
            'dexterity': self.dexterity or 10,
            'constitution': self.constitution or 10,
            'intelligence': self.intelligence or 10,
            'wisdom': self.wisdom or 10,
            'charisma': self.charisma or 10,
        }


class CharacterUpdate(BaseModel):
    """Schema for updating a character."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    background: Optional[str] = None
    personality: Optional[str] = None
    hp_current: Optional[int] = Field(None, ge=0)


class CharacterResponse(CharacterBase):
    """Schema for character API responses."""
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
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CharacterListResponse(BaseModel):
    """Schema for paginated character list responses."""
    characters: list[CharacterResponse]
    total: int
    page: int
    page_size: int
