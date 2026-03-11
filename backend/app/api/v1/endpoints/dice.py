"""Dice rolling API endpoints."""

import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.schemas.ability_check import (
    SKILL_TO_ABILITY,
    Ability,
    AbilityCheckRequest,
    AbilityCheckResponse,
)
from app.schemas.dice import DiceRollRequest, DiceRollResponse
from app.services.character_service import CharacterService
from app.services.dice_service import DiceService

router = APIRouter(prefix="/dice", tags=["dice"])


@router.post("/roll", response_model=DiceRollResponse)
async def roll_dice(request: DiceRollRequest) -> DiceRollResponse:
    """Roll dice according to D&D notation.

    Args:
        request: Dice roll request with notation and roll type

    Returns:
        Dice roll response with results and breakdown

    Raises:
        HTTPException: If dice notation is invalid
    """
    try:
        rolls, modifier, total = await DiceService.roll_dice(request.dice, request.roll_type)

        breakdown = DiceService.format_breakdown(request.dice, rolls, modifier, total)

        return DiceRollResponse(
            notation=request.dice,
            roll_type=request.roll_type,
            individual_rolls=rolls,
            modifier=modifier,
            total=total,
            reason=request.reason,
            breakdown=breakdown,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid dice notation")


@router.post("/check", response_model=AbilityCheckResponse)
async def ability_check(
    request: AbilityCheckRequest, db: AsyncSession = Depends(get_db)
) -> AbilityCheckResponse:
    """Perform a D&D 5e ability check or skill roll.

    This endpoint:
    1. Looks up the character to get their ability scores
    2. Calculates ability modifier and proficiency bonus
    3. Rolls 1d20 (or 2d20 for advantage/disadvantage)
    4. Adds modifiers and proficiency (if applicable)
    5. Checks against DC if provided

    Args:
        request: Ability check request
        db: Database session

    Returns:
        Ability check result with success/failure if DC provided

    Raises:
        HTTPException: 404 if character not found, 400 if advantage and disadvantage both true
    """
    # Validate advantage/disadvantage
    if request.advantage and request.disadvantage:
        raise HTTPException(status_code=400, detail="Cannot have both advantage and disadvantage")

    # Get character
    character = await CharacterService.get_character(db, request.character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Get ability score
    ability_scores = {
        Ability.STRENGTH: character.strength,
        Ability.DEXTERITY: character.dexterity,
        Ability.CONSTITUTION: character.constitution,
        Ability.INTELLIGENCE: character.intelligence,
        Ability.WISDOM: character.wisdom,
        Ability.CHARISMA: character.charisma,
    }
    ability_score = ability_scores[request.ability]
    ability_modifier = CharacterService.calculate_ability_modifier(ability_score)
    proficiency_bonus = CharacterService.calculate_proficiency_bonus(character.level)

    # Check if skill matches ability
    if request.skill:
        expected_ability = SKILL_TO_ABILITY.get(request.skill)
        if expected_ability and expected_ability != request.ability:
            raise HTTPException(
                status_code=400,
                detail=f"{request.skill.value} uses {expected_ability.value}, not {request.ability.value}",
            )

    # For now, assume no skill proficiencies (we'll add this later)
    # TODO: Add skill_proficiencies to Character model
    is_proficient = False

    # Roll d20 (or 2d20 for advantage/disadvantage)
    if request.advantage or request.disadvantage:
        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        rolls = [roll1, roll2]

        if request.advantage:
            roll = max(rolls)
        else:  # disadvantage
            roll = min(rolls)
    else:
        roll = random.randint(1, 20)
        rolls = [roll]

    # Calculate total
    total = roll + ability_modifier
    if is_proficient:
        total += proficiency_bonus

    # Build breakdown string
    breakdown_parts = [f"1d20({roll})"]
    if ability_modifier != 0:
        sign = "+" if ability_modifier > 0 else ""
        breakdown_parts.append(f"{sign}{ability_modifier} ({request.ability.value[:3].upper()})")
    if is_proficient:
        breakdown_parts.append(f"+{proficiency_bonus} (proficiency)")
    breakdown = " ".join(breakdown_parts) + f" = {total}"

    # Check DC if provided
    success = None
    if request.dc is not None:
        success = total >= request.dc

    return AbilityCheckResponse(
        character_id=request.character_id,
        character_name=character.name,
        ability=request.ability,
        skill=request.skill,
        ability_score=ability_score,
        ability_modifier=ability_modifier,
        proficiency_bonus=proficiency_bonus,
        is_proficient=is_proficient,
        roll=roll,
        rolls=rolls,
        advantage=request.advantage,
        disadvantage=request.disadvantage,
        total=total,
        breakdown=breakdown,
        dc=request.dc,
        success=success,
        reason=request.reason,
    )
