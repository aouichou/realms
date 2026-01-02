"""Spell and character spell schemas"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from uuid import UUID
from datetime import datetime


class SpellBase(BaseModel):
    """Base spell schema"""
    name: str = Field(..., min_length=1, max_length=100)
    level: int = Field(..., ge=0, le=9, description="Spell level (0=cantrip)")
    school: str
    casting_time: str
    range: str
    duration: str
    verbal: bool = False
    somatic: bool = False
    material: Optional[str] = None
    description: str
    is_concentration: bool = False
    is_ritual: bool = False
    damage_dice: Optional[str] = None
    damage_type: Optional[str] = None
    save_ability: Optional[str] = None
    available_to_classes: Optional[Dict[str, bool]] = None


class SpellCreate(SpellBase):
    """Schema for creating a new spell"""
    pass


class SpellResponse(SpellBase):
    """Schema for spell response"""
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True


class SpellListResponse(BaseModel):
    """Schema for list of spells with pagination"""
    spells: List[SpellResponse]
    total: int
    page: int
    page_size: int


class CharacterSpellCreate(BaseModel):
    """Schema for adding a spell to a character"""
    spell_id: UUID
    is_known: bool = True
    is_prepared: bool = False


class CharacterSpellUpdate(BaseModel):
    """Schema for updating character spell status"""
    is_known: Optional[bool] = None
    is_prepared: Optional[bool] = None


class CharacterSpellResponse(BaseModel):
    """Schema for character spell response"""
    id: UUID
    character_id: UUID
    spell_id: UUID
    is_known: bool
    is_prepared: bool
    spell: SpellResponse
    created_at: datetime
    
    class Config:
        from_attributes = True


class PrepareSpellsRequest(BaseModel):
    """Schema for preparing daily spells"""
    spell_ids: List[UUID] = Field(..., description="List of spell IDs to prepare")


class CastSpellRequest(BaseModel):
    """Schema for casting a spell"""
    spell_id: UUID
    spell_level: int = Field(..., ge=1, le=9, description="Spell slot level to use")
    target_id: Optional[UUID] = None


class CastSpellResponse(BaseModel):
    """Schema for spell casting response"""
    character_id: UUID
    character_name: str
    spell_name: str
    spell_level: int
    slot_level_used: int
    damage_roll: Optional[str] = None
    total_damage: Optional[int] = None
    description: str
    remaining_slots: Dict[str, int]


class SpellSlotsResponse(BaseModel):
    """Schema for character spell slots"""
    character_id: UUID
    character_name: str
    spell_slots: Dict[str, Dict[str, int]]  # {"1": {"total": 4, "used": 1}, ...}
    
    class Config:
        from_attributes = True
