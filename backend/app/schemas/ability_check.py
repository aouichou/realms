"""Ability check and skill roll schemas"""

from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Ability(str, Enum):
    """D&D 5e abilities"""

    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"


class Skill(str, Enum):
    """D&D 5e skills"""

    # Strength
    ATHLETICS = "athletics"

    # Dexterity
    ACROBATICS = "acrobatics"
    SLEIGHT_OF_HAND = "sleight_of_hand"
    STEALTH = "stealth"

    # Intelligence
    ARCANA = "arcana"
    HISTORY = "history"
    INVESTIGATION = "investigation"
    NATURE = "nature"
    RELIGION = "religion"

    # Wisdom
    ANIMAL_HANDLING = "animal_handling"
    INSIGHT = "insight"
    MEDICINE = "medicine"
    PERCEPTION = "perception"
    SURVIVAL = "survival"

    # Charisma
    DECEPTION = "deception"
    INTIMIDATION = "intimidation"
    PERFORMANCE = "performance"
    PERSUASION = "persuasion"


# Skill to ability mapping
SKILL_TO_ABILITY = {
    Skill.ATHLETICS: Ability.STRENGTH,
    Skill.ACROBATICS: Ability.DEXTERITY,
    Skill.SLEIGHT_OF_HAND: Ability.DEXTERITY,
    Skill.STEALTH: Ability.DEXTERITY,
    Skill.ARCANA: Ability.INTELLIGENCE,
    Skill.HISTORY: Ability.INTELLIGENCE,
    Skill.INVESTIGATION: Ability.INTELLIGENCE,
    Skill.NATURE: Ability.INTELLIGENCE,
    Skill.RELIGION: Ability.INTELLIGENCE,
    Skill.ANIMAL_HANDLING: Ability.WISDOM,
    Skill.INSIGHT: Ability.WISDOM,
    Skill.MEDICINE: Ability.WISDOM,
    Skill.PERCEPTION: Ability.WISDOM,
    Skill.SURVIVAL: Ability.WISDOM,
    Skill.DECEPTION: Ability.CHARISMA,
    Skill.INTIMIDATION: Ability.CHARISMA,
    Skill.PERFORMANCE: Ability.CHARISMA,
    Skill.PERSUASION: Ability.CHARISMA,
}


class AbilityCheckRequest(BaseModel):
    """Request for an ability check or skill roll"""

    character_id: UUID
    ability: Ability
    skill: Optional[Skill] = None
    dc: Optional[int] = Field(None, ge=1, le=30, description="Difficulty Class (DC)")
    advantage: bool = Field(False, description="Roll with advantage (2d20, take higher)")
    disadvantage: bool = Field(False, description="Roll with disadvantage (2d20, take lower)")
    reason: Optional[str] = Field(None, description="Reason for the check")


class AbilityCheckResponse(BaseModel):
    """Response for an ability check or skill roll"""

    character_id: UUID
    character_name: str
    ability: Ability
    skill: Optional[Skill]
    ability_score: int
    ability_modifier: int
    proficiency_bonus: int
    is_proficient: bool

    # Roll details
    roll: int
    rolls: list[int]  # Multiple rolls if advantage/disadvantage
    advantage: bool
    disadvantage: bool

    # Total calculation
    total: int
    breakdown: str

    # DC check
    dc: Optional[int]
    success: Optional[bool]

    reason: Optional[str]
