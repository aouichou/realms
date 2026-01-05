"""
Character progression and leveling API endpoints
"""

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.spells import get_spell_slots_for_class
from app.db.base import get_db
from app.db.models import Character, CharacterClass

router = APIRouter(prefix="/api", tags=["progression"])


class AddXPRequest(BaseModel):
    amount: int


class LevelUpRequest(BaseModel):
    ability_increases: Dict[str, int] = {}  # e.g., {"strength": 1, "dexterity": 1}
    hp_roll: int = 0  # 0 means take average


# XP thresholds for each level (D&D 5e)
XP_THRESHOLDS = {
    1: 0,
    2: 300,
    3: 900,
    4: 2700,
    5: 6500,
    6: 14000,
    7: 23000,
    8: 34000,
    9: 48000,
    10: 64000,
    11: 85000,
    12: 100000,
    13: 120000,
    14: 140000,
    15: 165000,
    16: 195000,
    17: 225000,
    18: 265000,
    19: 305000,
    20: 355000,
}

# Hit dice by class
CLASS_HIT_DICE = {
    CharacterClass.FIGHTER: 10,
    CharacterClass.BARBARIAN: 12,
    CharacterClass.RANGER: 10,
    CharacterClass.ROGUE: 8,
    CharacterClass.CLERIC: 8,
    CharacterClass.WIZARD: 6,
    CharacterClass.SORCERER: 6,
    CharacterClass.BARD: 8,
    CharacterClass.DRUID: 8,
    CharacterClass.MONK: 8,
    CharacterClass.PALADIN: 10,
    CharacterClass.WARLOCK: 8,
}


def get_proficiency_bonus(level: int) -> int:
    """Calculate proficiency bonus based on level"""
    return 2 + ((level - 1) // 4)


def get_xp_for_level(level: int) -> int:
    """Get XP required for a given level"""
    return XP_THRESHOLDS.get(level, XP_THRESHOLDS[20])


def can_level_up(xp: int, current_level: int) -> bool:
    """Check if character has enough XP to level up"""
    if current_level >= 20:
        return False
    next_level_xp = get_xp_for_level(current_level + 1)
    return xp >= next_level_xp


@router.post("/characters/{character_id}/add-xp")
async def add_experience(character_id: int, request: AddXPRequest, db: Session = Depends(get_db)):
    """
    Add experience points to a character
    Returns updated XP and whether character can level up
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Add XP
    character.experience_points += request.amount
    db.commit()

    # Check if can level up
    can_level = can_level_up(character.experience_points, character.level)
    next_level_xp = get_xp_for_level(character.level + 1) if character.level < 20 else None

    return {
        "character_id": character.id,
        "experience_points": character.experience_points,
        "level": character.level,
        "can_level_up": can_level,
        "xp_to_next_level": next_level_xp - character.experience_points if next_level_xp else None,
        "xp_added": request.amount,
    }


@router.get("/characters/{character_id}/xp-progress")
async def get_xp_progress(character_id: int, db: Session = Depends(get_db)):
    """
    Get character's XP progress and leveling information
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    current_level_xp = get_xp_for_level(character.level)
    next_level_xp = get_xp_for_level(character.level + 1) if character.level < 20 else None

    if next_level_xp:
        xp_in_level = character.experience_points - current_level_xp
        xp_needed = next_level_xp - current_level_xp
        progress_percent = (xp_in_level / xp_needed) * 100
    else:
        progress_percent = 100.0

    return {
        "character_id": character.id,
        "level": character.level,
        "experience_points": character.experience_points,
        "current_level_xp": current_level_xp,
        "next_level_xp": next_level_xp,
        "progress_percent": round(progress_percent, 1),
        "can_level_up": can_level_up(character.experience_points, character.level),
    }


@router.post("/characters/{character_id}/level-up")
async def level_up_character(
    character_id: int, request: LevelUpRequest, db: Session = Depends(get_db)
):
    """
    Level up a character
    Grants HP increase, updates proficiency bonus, updates spell slots
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Check if can level up
    if not can_level_up(character.experience_points, character.level):
        raise HTTPException(
            status_code=400,
            detail=f"Not enough XP to level up. Need {get_xp_for_level(character.level + 1)} XP",
        )

    if character.level >= 20:
        raise HTTPException(status_code=400, detail="Already at maximum level")

    new_level = character.level + 1

    # Get hit die for class
    hit_die = CLASS_HIT_DICE.get(character.character_class, 8)

    # Calculate HP increase
    con_modifier = (character.constitution - 10) // 2
    if request.hp_roll > 0:
        # Use provided roll
        hp_increase = min(request.hp_roll, hit_die) + con_modifier
    else:
        # Take average (rounded up)
        hp_increase = ((hit_die // 2) + 1) + con_modifier

    # Ensure minimum 1 HP gained
    hp_increase = max(1, hp_increase)

    # Update character
    character.level = new_level
    character.hp_max += hp_increase
    character.hp_current += hp_increase  # Also heal on level up!

    # Apply ability score increases (every 4 levels)
    if new_level in [4, 8, 12, 16, 19]:
        total_increases = sum(request.ability_increases.values())
        if total_increases != 2:
            raise HTTPException(
                status_code=400,
                detail=f"Must increase ability scores by exactly 2 points total (got {total_increases})",
            )

        # Apply increases
        for ability, increase in request.ability_increases.items():
            if ability not in [
                "strength",
                "dexterity",
                "constitution",
                "intelligence",
                "wisdom",
                "charisma",
            ]:
                raise HTTPException(status_code=400, detail=f"Invalid ability: {ability}")

            if increase < 0 or increase > 2:
                raise HTTPException(
                    status_code=400, detail="Each ability can increase by 0-2 points"
                )

            current_value = getattr(character, ability)
            new_value = min(20, current_value + increase)  # Cap at 20
            setattr(character, ability, new_value)

            # Update carrying capacity if strength increased
            if ability == "strength":
                character.carrying_capacity = character.strength * 15

    # Update spell slots for spellcasting classes
    is_caster = character.character_class in [
        CharacterClass.WIZARD,
        CharacterClass.CLERIC,
        CharacterClass.SORCERER,
        CharacterClass.BARD,
        CharacterClass.DRUID,
        CharacterClass.WARLOCK,
    ]

    new_spell_slots = {}
    if is_caster:
        new_spell_slots = get_spell_slots_for_class(character.character_class, new_level)
        character.spell_slots = {
            str(level): {"total": total, "used": 0}
            for level, total in new_spell_slots.items()
            if total > 0
        }

    db.commit()
    db.refresh(character)

    # Calculate new proficiency bonus
    new_prof_bonus = get_proficiency_bonus(new_level)

    return {
        "success": True,
        "character_id": character.id,
        "new_level": new_level,
        "hp_gained": hp_increase,
        "new_hp_max": character.hp_max,
        "new_proficiency_bonus": new_prof_bonus,
        "ability_increases": request.ability_increases,
        "new_spell_slots": new_spell_slots if new_spell_slots else None,
        "message": f"Congratulations! {character.name} is now level {new_level}!",
    }
