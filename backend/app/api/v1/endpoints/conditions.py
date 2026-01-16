"""
Character conditions and status effects API endpoints
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Character, CharacterCondition, ConditionType

router = APIRouter(prefix="/conditions", tags=["conditions"])


class AddConditionRequest(BaseModel):
    condition: str  # Condition name (e.g., "Blinded", "Poisoned")
    duration: int = 0  # Duration in rounds/minutes, 0 = indefinite
    source: Optional[str] = None  # Source of condition (spell, ability, etc.)


class ConditionResponse(BaseModel):
    id: str
    condition: str
    duration: int
    source: Optional[str]
    applied_at: str

    class Config:
        from_attributes = True


# Condition descriptions and effects
CONDITION_EFFECTS = {
    "Blinded": {
        "description": "A blinded creature can't see and automatically fails any ability check that requires sight.",
        "effects": ["Attack rolls have disadvantage", "Attacks against have advantage"],
    },
    "Charmed": {
        "description": "A charmed creature can't attack the charmer or target the charmer with harmful abilities or magical effects.",
        "effects": ["Can't attack charmer", "Charmer has advantage on social checks"],
    },
    "Deafened": {
        "description": "A deafened creature can't hear and automatically fails any ability check that requires hearing.",
        "effects": ["Auto-fail hearing checks"],
    },
    "Frightened": {
        "description": "A frightened creature has disadvantage on ability checks and attack rolls while the source of its fear is within line of sight.",
        "effects": [
            "Disadvantage on checks/attacks while source visible",
            "Can't move closer to source",
        ],
    },
    "Grappled": {
        "description": "A grappled creature's speed becomes 0, and it can't benefit from any bonus to its speed.",
        "effects": ["Speed = 0", "No speed bonuses"],
    },
    "Incapacitated": {
        "description": "An incapacitated creature can't take actions or reactions.",
        "effects": ["Can't take actions", "Can't take reactions"],
    },
    "Invisible": {
        "description": "An invisible creature is impossible to see without the aid of magic or a special sense.",
        "effects": [
            "Attack rolls have advantage",
            "Attacks against have disadvantage",
            "Hide without cover",
        ],
    },
    "Paralyzed": {
        "description": "A paralyzed creature is incapacitated and can't move or speak.",
        "effects": [
            "Incapacitated",
            "Auto-fail STR/DEX saves",
            "Attacks have advantage",
            "Hits within 5ft are crits",
        ],
    },
    "Petrified": {
        "description": "A petrified creature is transformed, along with any nonmagical object it is wearing or carrying, into a solid inanimate substance (usually stone).",
        "effects": [
            "Weight x10",
            "Stops aging",
            "Incapacitated",
            "Auto-fail STR/DEX saves",
            "Resistance to all damage",
            "Immune to poison/disease",
        ],
    },
    "Poisoned": {
        "description": "A poisoned creature has disadvantage on attack rolls and ability checks.",
        "effects": ["Disadvantage on attacks", "Disadvantage on ability checks"],
    },
    "Prone": {
        "description": "A prone creature's only movement option is to crawl, unless it stands up and thereby ends the condition.",
        "effects": [
            "Disadvantage on attacks",
            "Attacks within 5ft have advantage",
            "Attacks beyond 5ft have disadvantage",
        ],
    },
    "Restrained": {
        "description": "A restrained creature's speed becomes 0, and it can't benefit from any bonus to its speed.",
        "effects": [
            "Speed = 0",
            "Disadvantage on attacks",
            "Disadvantage on DEX saves",
            "Attacks against have advantage",
        ],
    },
    "Stunned": {
        "description": "A stunned creature is incapacitated, can't move, and can speak only falteringly.",
        "effects": [
            "Incapacitated",
            "Can't move",
            "Auto-fail STR/DEX saves",
            "Attacks against have advantage",
        ],
    },
    "Unconscious": {
        "description": "An unconscious creature is incapacitated, can't move or speak, and is unaware of its surroundings.",
        "effects": [
            "Incapacitated",
            "Can't move/speak",
            "Drops held items",
            "Falls prone",
            "Auto-fail STR/DEX saves",
            "Attacks have advantage",
            "Hits within 5ft are crits",
        ],
    },
}


@router.post("/characters/{character_id}/conditions")
async def add_condition(
    character_id: int, request: AddConditionRequest, db: Session = Depends(get_db)
):
    """
    Add a condition to a character
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Validate condition
    try:
        condition_type = ConditionType(request.condition)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid condition: {request.condition}. Must be one of: {', '.join([c.value for c in ConditionType])}",
        )

    # Check if condition already exists
    existing = (
        db.query(CharacterCondition)
        .filter(
            CharacterCondition.character_id == character_id,
            CharacterCondition.condition == condition_type,
        )
        .first()
    )

    if existing:
        # Update duration if new one is longer
        if request.duration > existing.duration:
            existing.duration = request.duration
            existing.source = request.source or existing.source
            db.commit()
            db.refresh(existing)

        return {
            "message": f"Condition {condition_type.value} updated",
            "condition": ConditionResponse(
                id=str(existing.id),
                condition=existing.condition.value,
                duration=existing.duration,
                source=existing.source,
                applied_at=existing.applied_at.isoformat(),
            ),
        }

    # Create new condition
    condition = CharacterCondition(
        character_id=character_id,
        condition=condition_type,
        duration=request.duration,
        source=request.source,
    )
    db.add(condition)
    db.commit()
    db.refresh(condition)

    effects = CONDITION_EFFECTS.get(request.condition, {})

    return {
        "message": f"Condition {condition_type.value} applied",
        "condition": ConditionResponse(
            id=str(condition.id),
            condition=condition.condition.value,
            duration=condition.duration,
            source=condition.source,
            applied_at=condition.applied_at.isoformat(),
        ),
        "effects": effects.get("effects", []),
        "description": effects.get("description", ""),
    }


@router.delete("/characters/{character_id}/conditions/{condition_id}")
async def remove_condition(character_id: int, condition_id: str, db: Session = Depends(get_db)):
    """
    Remove a condition from a character
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    condition = (
        db.query(CharacterCondition)
        .filter(
            CharacterCondition.id == condition_id, CharacterCondition.character_id == character_id
        )
        .first()
    )

    if not condition:
        raise HTTPException(status_code=404, detail="Condition not found")

    condition_name = condition.condition.value
    db.delete(condition)
    db.commit()

    return {"message": f"Condition {condition_name} removed", "character_id": character_id}


@router.get("/characters/{character_id}/conditions")
async def get_conditions(character_id: int, db: Session = Depends(get_db)):
    """
    Get all active conditions for a character
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    conditions = (
        db.query(CharacterCondition).filter(CharacterCondition.character_id == character_id).all()
    )

    condition_list = []
    for condition in conditions:
        effects = CONDITION_EFFECTS.get(condition.condition.value, {})
        condition_list.append(
            {
                "id": str(condition.id),
                "condition": condition.condition.value,
                "duration": condition.duration,
                "source": condition.source,
                "applied_at": condition.applied_at.isoformat(),
                "effects": effects.get("effects", []),
                "description": effects.get("description", ""),
            }
        )

    return {
        "character_id": character_id,
        "conditions": condition_list,
        "count": len(condition_list),
    }


@router.get("/conditions/effects")
async def get_condition_effects():
    """
    Get all condition effects and descriptions
    """
    return {
        "conditions": {
            name: {"description": info["description"], "effects": info["effects"]}
            for name, info in CONDITION_EFFECTS.items()
        }
    }
