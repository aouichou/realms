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
        valid_classes = ['Fighter', 'Wizard', 'Rogue', 'Cleric']
        if v not in valid_classes:
            raise ValueError(f'Invalid class. Must be one of: {", ".join(valid_classes)}')
        return v
    
    @field_validator('race')
    @classmethod
    def validate_race(cls, v: str) -> str:
        """Validate D&D race."""
        valid_races = ['Human', 'Elf', 'Dwarf', 'Halfling']
        if v not in valid_races:
            raise ValueError(f'Invalid race. Must be one of: {", ".join(valid_races)}')
        return v


class CharacterCreate(CharacterBase):
    """Schema for creating a new character."""
    # Base stats - use defaults or allow custom values
    strength: int = Field(10, ge=3, le=18, description="Strength stat (3-18)")
    dexterity: int = Field(10, ge=3, le=18, description="Dexterity stat (3-18)")
    constitution: int = Field(10, ge=3, le=18, description="Constitution stat (3-18)")
    intelligence: int = Field(10, ge=3, le=18, description="Intelligence stat (3-18)")
    wisdom: int = Field(10, ge=3, le=18, description="Wisdom stat (3-18)")
    charisma: int = Field(10, ge=3, le=18, description="Charisma stat (3-18)")


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
