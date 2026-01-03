"""API endpoints for D&D 5e rules helpers."""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from app.utils.dnd_rules import (
    ASI_LEVELS,
    RACIAL_BONUSES,
    CLASS_SKILLS,
    ALL_SKILLS,
    calculate_asi_count,
    get_skill_choices,
    calculate_proficiency_bonus
)

router = APIRouter(prefix="/rules", tags=["D&D 5e Rules"])


class ASIInfo(BaseModel):
    """ASI information response."""
    asi_count: int = Field(..., description="Number of ASIs earned")
    asi_levels: list[int] = Field(..., description="Levels where ASIs are granted")
    total_points: int = Field(..., description="Total ASI points to distribute (2 per ASI)")


class RacialBonusInfo(BaseModel):
    """Racial bonus information."""
    race: str
    bonuses: dict[str, int]


class ClassSkillInfo(BaseModel):
    """Class skill selection information."""
    character_class: str
    skills_count: int = Field(..., description="Number of skills to select")
    available_skills: list[str] | str = Field(..., description="List of available skills or 'any'")


@router.get("/asi/{character_class}/{level}", response_model=ASIInfo)
async def get_asi_info(character_class: str, level: int):
    """Get ASI information for a character class and level.
    
    Args:
        character_class: Character class (Fighter, Wizard, etc.)
        level: Character level (1-20)
        
    Returns:
        ASI count, levels, and total points to distribute
    """
    if character_class not in ASI_LEVELS:
        return {"error": f"Unknown class: {character_class}"}
    
    asi_count = calculate_asi_count(character_class, level)
    asi_levels = [lvl for lvl in ASI_LEVELS[character_class] if lvl <= level]
    
    return ASIInfo(
        asi_count=asi_count,
        asi_levels=asi_levels,
        total_points=asi_count * 2
    )


@router.get("/racial-bonuses", response_model=list[RacialBonusInfo])
async def get_all_racial_bonuses():
    """Get all racial ability score bonuses.
    
    Returns:
        List of racial bonuses for all races
    """
    return [
        RacialBonusInfo(race=race, bonuses=bonuses)
        for race, bonuses in RACIAL_BONUSES.items()
    ]


@router.get("/racial-bonuses/{race}", response_model=RacialBonusInfo)
async def get_racial_bonus(race: str):
    """Get racial ability score bonuses for a specific race.
    
    Args:
        race: Character race
        
    Returns:
        Racial bonuses for the race
    """
    if race not in RACIAL_BONUSES:
        return {"error": f"Unknown race: {race}"}
    
    return RacialBonusInfo(race=race, bonuses=RACIAL_BONUSES[race])


@router.get("/class-skills", response_model=list[ClassSkillInfo])
async def get_all_class_skills():
    """Get skill selection options for all classes.
    
    Returns:
        List of class skill information
    """
    return [
        ClassSkillInfo(
            character_class=class_name,
            skills_count=info['count'],
            available_skills=info['choices']
        )
        for class_name, info in CLASS_SKILLS.items()
    ]


@router.get("/class-skills/{character_class}", response_model=ClassSkillInfo)
async def get_class_skills(character_class: str):
    """Get skill selection options for a specific class.
    
    Args:
        character_class: Character class
        
    Returns:
        Skill selection information
    """
    skill_info = get_skill_choices(character_class)
    
    return ClassSkillInfo(
        character_class=character_class,
        skills_count=skill_info['count'],
        available_skills=skill_info['choices']
    )


@router.get("/skills", response_model=list[str])
async def get_all_skills():
    """Get list of all D&D 5e skills.
    
    Returns:
        List of all skill names
    """
    return ALL_SKILLS


@router.get("/proficiency-bonus/{level}", response_model=dict)
async def get_proficiency_bonus_by_level(level: int):
    """Calculate proficiency bonus for a character level.
    
    Args:
        level: Character level (1-20)
        
    Returns:
        Proficiency bonus for the level
    """
    if level < 1 or level > 20:
        return {"error": "Level must be between 1 and 20"}
    
    return {
        "level": level,
        "proficiency_bonus": calculate_proficiency_bonus(level)
    }
