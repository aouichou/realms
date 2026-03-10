"""
Rest mechanics API endpoints
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Character, CharacterClass, User
from app.middleware.auth import get_current_active_user

router = APIRouter(prefix="/rest", tags=["rest"])


class RestRequest(BaseModel):
    rest_type: str  # 'short' or 'long'
    hit_dice_spent: List[int] = []  # List of hit dice rolls for short rest


# Hit dice by class (same as progression)
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


@router.post("/characters/{character_id}/rest")
async def take_rest(
    character_id: UUID,
    request: RestRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Take a short or long rest
    Short rest: Spend hit dice to recover HP
    Long rest: Restore all HP, spell slots, and half of spent hit dice
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character or character.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Character not found")

    # Get character's hit die
    hit_die = CLASS_HIT_DICE.get(character.character_class, 8)
    con_modifier = (character.constitution - 10) // 2

    if request.rest_type == "short":
        # Short rest - spend hit dice to recover HP
        hp_recovered = 0

        for roll in request.hit_dice_spent:
            # Validate roll is within hit die range
            if roll < 1 or roll > hit_die:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid hit die roll: {roll}. Must be between 1 and {hit_die}",
                )

            # Add roll + CON modifier (minimum 1 HP per die)
            hp_from_die = max(1, roll + con_modifier)
            hp_recovered += hp_from_die

        # Apply HP recovery (can't exceed max HP)
        new_hp = min(character.hp_max, character.hp_current + hp_recovered)
        actual_hp_recovered = new_hp - character.hp_current
        character.hp_current = new_hp

        db.commit()

        return {
            "rest_type": "short",
            "hit_dice_spent": len(request.hit_dice_spent),
            "hp_recovered": actual_hp_recovered,
            "current_hp": character.hp_current,
            "max_hp": character.hp_max,
            "message": f"Short rest complete. Recovered {actual_hp_recovered} HP.",
        }

    elif request.rest_type == "long":
        # Long rest - full HP and spell slot restoration
        hp_before = character.hp_current
        character.hp_current = character.hp_max
        hp_recovered = character.hp_max - hp_before

        # Restore all spell slots
        if character.spell_slots:
            for level_str in character.spell_slots:
                if (
                    isinstance(character.spell_slots[level_str], dict)
                    and "total" in character.spell_slots[level_str]
                ):
                    character.spell_slots[level_str]["used"] = 0

        db.commit()

        return {
            "rest_type": "long",
            "hp_recovered": hp_recovered,
            "current_hp": character.hp_current,
            "max_hp": character.hp_max,
            "spell_slots_restored": bool(character.spell_slots),
            "message": "Long rest complete. Fully rested and ready for adventure!",
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rest type: {request.rest_type}. Must be 'short' or 'long'",
        )


@router.get("/characters/{character_id}/rest-status")
async def get_rest_status(
    character_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get character's rest status
    Shows available hit dice and spell slot status
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character or character.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Character not found")

    # Get hit die info
    hit_die = CLASS_HIT_DICE.get(character.character_class, 8)

    # In D&D 5e, you have hit dice equal to your level
    # For simplicity, assuming all hit dice are available (tracking spending would require another field)
    available_hit_dice = character.level

    # Get spell slot status
    spell_slot_status = {}
    if character.spell_slots:
        for level_str, slots in character.spell_slots.items():
            if isinstance(slots, dict) and "total" in slots:
                spell_slot_status[level_str] = {
                    "total": slots["total"],
                    "used": slots.get("used", 0),
                    "remaining": slots["total"] - slots.get("used", 0),
                }

    return {
        "character_id": character.id,
        "current_hp": character.hp_current,
        "max_hp": character.hp_max,
        "hp_percent": (
            round((character.hp_current / character.hp_max) * 100, 1) if character.hp_max > 0 else 0
        ),
        "hit_die_type": f"d{hit_die}",
        "available_hit_dice": available_hit_dice,
        "spell_slots": spell_slot_status,
        "needs_rest": character.hp_current < character.hp_max
        or any(
            slots.get("used", 0) > 0
            for slots in (character.spell_slots or {}).values()
            if isinstance(slots, dict)
        ),
    }
