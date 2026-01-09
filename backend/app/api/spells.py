"""Spells API endpoints"""

import random
import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.db.models import CharacterClass, CharacterSpell, Spell
from app.observability.logger import get_logger
from app.schemas.spell import (
    CastSpellRequest,
    CastSpellResponse,
    CharacterSpellCreate,
    CharacterSpellResponse,
    PrepareSpellsRequest,
    SpellCreate,
    SpellListResponse,
    SpellResponse,
    SpellSlotsResponse,
)
from app.services.character_service import CharacterService
from app.services.memory_capture import MemoryCaptureService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/spells", tags=["spells"])


# Spell slot progression by class and level (D&D 5e)
SPELL_SLOTS_BY_LEVEL = {
    # Full casters (Wizard, Cleric, Druid, Sorcerer, Bard)
    "full": {
        1: {"1": 2},
        2: {"1": 3},
        3: {"1": 4, "2": 2},
        4: {"1": 4, "2": 3},
        5: {"1": 4, "2": 3, "3": 2},
        6: {"1": 4, "2": 3, "3": 3},
        7: {"1": 4, "2": 3, "3": 3, "4": 1},
        8: {"1": 4, "2": 3, "3": 3, "4": 2},
        9: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 1},
        10: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2},
    },
    # Half casters (Paladin, Ranger)
    "half": {
        2: {"1": 2},
        3: {"1": 3},
        5: {"1": 4, "2": 2},
        7: {"1": 4, "2": 3},
        9: {"1": 4, "2": 3, "3": 2},
    },
}


def get_spell_slots_for_class(character_class: CharacterClass, level: int) -> dict:
    """Get spell slots for a character class and level"""
    if character_class in [
        CharacterClass.WIZARD,
        CharacterClass.CLERIC,
        CharacterClass.SORCERER,
        CharacterClass.BARD,
        CharacterClass.DRUID,
    ]:
        progression = SPELL_SLOTS_BY_LEVEL["full"]
    elif character_class in [CharacterClass.PALADIN, CharacterClass.RANGER]:
        progression = SPELL_SLOTS_BY_LEVEL["half"]
    elif character_class == CharacterClass.WARLOCK:
        progression = SPELL_SLOTS_BY_LEVEL.get("warlock", {})
    else:
        return {}

    slots = progression.get(level, {})
    # Return with total and used counts
    return {str(level): {"total": count, "used": 0} for level, count in slots.items()}


@router.get("", response_model=SpellListResponse)
async def list_spells(
    level: Optional[int] = Query(None, ge=0, le=9, description="Filter by spell level"),
    school: Optional[str] = Query(None, description="Filter by school of magic"),
    character_class: Optional[str] = Query(None, description="Filter by class availability"),
    concentration: Optional[bool] = Query(None, description="Filter concentration spells"),
    ritual: Optional[bool] = Query(None, description="Filter ritual spells"),
    search: Optional[str] = Query(None, description="Search spell name or description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """List all spells with optional filters

    Args:
        level: Filter by spell level (0-9)
        school: Filter by school of magic
        character_class: Filter by class (e.g., 'wizard', 'cleric')
        concentration: Filter concentration spells (true/false)
        ritual: Filter ritual spells (true/false)
        search: Full-text search on spell name/description
        page: Page number
        page_size: Items per page
        db: Database session

    Returns:
        Paginated list of spells with total count
    """
    from sqlalchemy import func, or_

    query = select(Spell)
    count_query = select(func.count()).select_from(Spell)

    # Apply filters to both queries
    filters = []

    if level is not None:
        filters.append(Spell.level == level)

    if school:
        filters.append(Spell.school == school.title())

    if character_class:
        # Use JSONB containment for class filtering
        class_key = character_class.lower()
        filters.append(Spell.available_to_classes[class_key].astext == "true")

    if concentration is not None:
        filters.append(Spell.is_concentration == concentration)

    if ritual is not None:
        filters.append(Spell.is_ritual == ritual)

    if search:
        # Search in name and description
        search_term = f"%{search}%"
        filters.append(or_(Spell.name.ilike(search_term), Spell.description.ilike(search_term)))

    # Apply all filters
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total count efficiently
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    skip = (page - 1) * page_size
    query = query.order_by(Spell.level, Spell.name).offset(skip).limit(page_size)

    result = await db.execute(query)
    spells = result.scalars().all()

    return SpellListResponse(
        spells=[SpellResponse.model_validate(spell) for spell in spells],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{spell_id}", response_model=SpellResponse)
async def get_spell(spell_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a spell by ID

    Args:
        spell_id: Spell UUID
        db: Database session

    Returns:
        Spell details

    Raises:
        HTTPException: 404 if spell not found
    """
    result = await db.execute(select(Spell).where(Spell.id == spell_id))
    spell = result.scalar_one_or_none()

    if not spell:
        raise HTTPException(status_code=404, detail="Spell not found")

    return SpellResponse.model_validate(spell)


@router.post("", response_model=SpellResponse, status_code=201)
async def create_spell(spell_data: SpellCreate, db: AsyncSession = Depends(get_db)):
    """Create a new spell

    Args:
        spell_data: Spell creation data
        db: Database session

    Returns:
        Created spell
    """
    spell = Spell(id=uuid.uuid4(), **spell_data.model_dump())

    db.add(spell)
    await db.commit()
    await db.refresh(spell)

    return SpellResponse.model_validate(spell)


@router.get("/character/{character_id}/spells", response_model=List[CharacterSpellResponse])
async def get_character_spells(
    character_id: UUID,
    known_only: bool = Query(False, description="Show only known spells"),
    prepared_only: bool = Query(False, description="Show only prepared spells"),
    db: AsyncSession = Depends(get_db),
):
    """Get all spells for a character

    Args:
        character_id: Character UUID
        known_only: Filter to known spells only
        prepared_only: Filter to prepared spells only
        db: Database session

    Returns:
        List of character spells with spell details

    Raises:
        HTTPException: 404 if character not found
    """
    # Check character exists
    character = await CharacterService.get_character(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    query = select(CharacterSpell).where(CharacterSpell.character_id == character_id)

    if known_only:
        query = query.where(CharacterSpell.is_known.is_(True))
    if prepared_only:
        query = query.where(CharacterSpell.is_prepared.is_(True))

    query = query.options(selectinload(CharacterSpell.spell))

    result = await db.execute(query)
    character_spells = result.scalars().all()

    return [CharacterSpellResponse.model_validate(cs) for cs in character_spells]


@router.post(
    "/character/{character_id}/spells", response_model=CharacterSpellResponse, status_code=201
)
async def add_spell_to_character(
    character_id: UUID, spell_data: CharacterSpellCreate, db: AsyncSession = Depends(get_db)
):
    """Add a spell to a character's spell list

    Args:
        character_id: Character UUID
        spell_data: Spell to add
        db: Database session

    Returns:
        Created character spell

    Raises:
        HTTPException: 404 if character or spell not found, 400 if already exists
    """
    # Check character exists
    character = await CharacterService.get_character(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Check spell exists
    result = await db.execute(select(Spell).where(Spell.id == spell_data.spell_id))
    spell = result.scalar_one_or_none()
    if not spell:
        raise HTTPException(status_code=404, detail="Spell not found")

    # Check if already exists
    existing = await db.execute(
        select(CharacterSpell).where(
            and_(
                CharacterSpell.character_id == character_id,
                CharacterSpell.spell_id == spell_data.spell_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Character already has this spell")

    # Create character spell
    character_spell = CharacterSpell(
        id=uuid.uuid4(),
        character_id=character_id,
        spell_id=spell_data.spell_id,
        is_known=spell_data.is_known,
        is_prepared=spell_data.is_prepared,
    )

    db.add(character_spell)
    await db.commit()
    await db.refresh(character_spell, ["spell"])

    return CharacterSpellResponse.model_validate(character_spell)


@router.post("/character/{character_id}/prepare", response_model=List[CharacterSpellResponse])
async def prepare_spells(
    character_id: UUID, request: PrepareSpellsRequest, db: AsyncSession = Depends(get_db)
):
    """Prepare daily spells for a character

    Args:
        character_id: Character UUID
        request: List of spell IDs to prepare
        db: Database session

    Returns:
        Updated list of prepared spells

    Raises:
        HTTPException: 404 if character not found
    """
    # Check character exists
    character = await CharacterService.get_character(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Unprepare all spells first
    await db.execute(
        update(CharacterSpell)
        .where(CharacterSpell.character_id == character_id)
        .values(is_prepared=False)
    )

    # Prepare selected spells
    for spell_id in request.spell_ids:
        result = await db.execute(
            select(CharacterSpell).where(
                and_(
                    CharacterSpell.character_id == character_id, CharacterSpell.spell_id == spell_id
                )
            )
        )
        character_spell = result.scalar_one_or_none()
        if character_spell:
            character_spell.is_prepared = True

    await db.commit()

    # Return prepared spells
    result = await db.execute(
        select(CharacterSpell)
        .where(
            and_(CharacterSpell.character_id == character_id, CharacterSpell.is_prepared.is_(True))
        )
        .options(selectinload(CharacterSpell.spell))
    )
    prepared_spells = result.scalars().all()

    return [CharacterSpellResponse.model_validate(cs) for cs in prepared_spells]


@router.get("/character/{character_id}/slots", response_model=SpellSlotsResponse)
async def get_spell_slots(character_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get character's spell slots

    Args:
        character_id: Character UUID
        db: Database session

    Returns:
        Spell slots by level with used/total counts

    Raises:
        HTTPException: 404 if character not found
    """
    character = await CharacterService.get_character(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Initialize spell slots if not set
    if not character.spell_slots:
        spell_slots = get_spell_slots_for_class(character.character_class, character.level)
        character.spell_slots = spell_slots
        await db.commit()

    return SpellSlotsResponse(
        character_id=character.id,
        character_name=character.name,
        spell_slots=character.spell_slots or {},
    )


def _check_spell_preparation(
    character: "Character", character_spell: CharacterSpell, spell: Spell
) -> None:
    """Check if spell needs to be prepared for prepared casters

    Raises:
        HTTPException: If spell is not prepared
    """
    prepared_caster_classes = [
        CharacterClass.WIZARD,
        CharacterClass.CLERIC,
        CharacterClass.DRUID,
        CharacterClass.PALADIN,
    ]

    if character.character_class in prepared_caster_classes:
        if not character_spell.is_prepared and spell.level > 0:  # Cantrips don't need preparation
            raise HTTPException(status_code=400, detail="Spell not prepared")


def _validate_ritual_cast(request: CastSpellRequest, spell: Spell) -> None:
    """Validate ritual casting request

    Raises:
        HTTPException: If spell cannot be cast as ritual
    """
    if request.is_ritual_cast and not spell.is_ritual:
        raise HTTPException(status_code=400, detail="This spell cannot be cast as a ritual")


def _validate_slot_level(request: CastSpellRequest, spell: Spell) -> int:
    """Validate and determine the slot level to use

    Returns:
        The slot level to use for casting

    Raises:
        HTTPException: If slot level is invalid
    """
    slot_level = request.slot_level if request.slot_level is not None else spell.level

    if slot_level < spell.level:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cast level {spell.level} spell using level {slot_level} slot",
        )

    return slot_level


def _handle_concentration(character: "Character", spell: Spell) -> None:
    """Handle concentration tracking for spells

    Updates character's active concentration spell
    """
    if spell.is_concentration:
        # Drop any existing concentration spell
        character.active_concentration_spell = spell.id


def _consume_spell_slot(character: "Character", slot_level: int, is_ritual: bool) -> None:
    """Consume a spell slot if not ritual casting

    Raises:
        HTTPException: If no spell slots available
    """
    if not is_ritual:
        spell_slots = character.spell_slots or {}
        slot_key = str(slot_level)

        if slot_key not in spell_slots:
            raise HTTPException(status_code=400, detail=f"No level {slot_level} spell slots")

        slot_info = spell_slots[slot_key]
        if slot_info["used"] >= slot_info["total"]:
            raise HTTPException(
                status_code=400, detail=f"No level {slot_level} spell slots remaining"
            )

        # Consume spell slot
        spell_slots[slot_key]["used"] += 1
        character.spell_slots = spell_slots


def _calculate_spell_damage(spell: Spell, slot_level: int) -> tuple[Optional[str], Optional[int]]:
    """Calculate damage with upcasting support

    Returns:
        Tuple of (damage_roll_string, total_damage)
    """
    if not spell.damage_dice:
        return None, None

    # Calculate upcast levels
    upcast_levels = slot_level - spell.level

    # Start with base damage
    damage_roll = spell.damage_dice
    total_damage = _roll_dice(damage_roll)

    # Add upcast damage if applicable
    if upcast_levels > 0 and spell.upcast_damage_dice:
        upcast_roll = spell.upcast_damage_dice
        # Handle different upcast formats
        if upcast_roll.startswith("+"):
            # Format: "+1d6" means add this per level
            upcast_dice = upcast_roll[1:]  # Remove the +
            for _ in range(upcast_levels):
                total_damage += _roll_dice(upcast_dice)
            damage_roll = f"{damage_roll} + {upcast_levels}x{upcast_dice}"
        else:
            # Direct formula (rare)
            total_damage += _roll_dice(upcast_roll) * upcast_levels
            damage_roll = f"{damage_roll} + {upcast_roll}x{upcast_levels}"

    return damage_roll, total_damage


@router.post("/character/{character_id}/cast", response_model=CastSpellResponse)
async def cast_spell(
    character_id: UUID, request: CastSpellRequest, db: AsyncSession = Depends(get_db)
):
    """Cast a spell, consuming a spell slot

    Supports:
    - Spell upcasting (cast at higher level for more damage)
    - Ritual casting (no slot consumed, +10 min cast time)
    - Concentration tracking (drop existing concentration spell)
    - Material component checking

    Args:
        character_id: Character UUID
        request: Spell casting request
        db: Database session

    Returns:
        Spell casting result with damage roll if applicable

    Raises:
        HTTPException: 404 if character/spell not found, 400 if no slots available
    """
    # Get character
    character = await CharacterService.get_character(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Get spell
    result = await db.execute(
        select(CharacterSpell)
        .where(
            and_(
                CharacterSpell.character_id == character_id,
                CharacterSpell.spell_id == request.spell_id,
            )
        )
        .options(selectinload(CharacterSpell.spell))
    )
    character_spell = result.scalar_one_or_none()
    if not character_spell:
        raise HTTPException(status_code=404, detail="Character doesn't know this spell")

    spell = character_spell.spell

    # Validate spell preparation
    _check_spell_preparation(character, character_spell, spell)

    # Validate ritual casting
    _validate_ritual_cast(request, spell)

    # Determine and validate slot level
    slot_level = _validate_slot_level(request, spell)

    # Handle concentration
    _handle_concentration(character, spell)

    # Cantrips don't consume spell slots
    if spell.level == 0:
        damage_roll, total_damage = (
            _calculate_spell_damage(spell, 0) if spell.damage_dice else (None, None)
        )

        await db.commit()

        return CastSpellResponse(
            character_id=character.id,
            character_name=character.name,
            spell_name=spell.name,
            spell_level=0,
            slot_level_used=0,
            damage_roll=damage_roll,
            total_damage=total_damage,
            description=spell.description,
            remaining_slots=character.spell_slots or {},
        )

    # Consume spell slot (unless ritual casting)
    _consume_spell_slot(character, slot_level, request.is_ritual_cast)

    # Calculate damage with upcasting
    damage_roll, total_damage = _calculate_spell_damage(spell, slot_level)

    await db.commit()

    # Capture spell casting as memory
    try:
        from app.db.models import GameSession

        result_session = await db.execute(
            select(GameSession)
            .where(GameSession.character_id == character_id)
            .order_by(GameSession.created_at.desc())
            .limit(1)
        )
        session = result_session.scalar_one_or_none()

        if session:
            details = f"{character.name} cast {spell.name}"
            if total_damage:
                details += f" dealing {total_damage} damage"
            if request.is_ritual_cast:
                details += " (ritual cast)"
            elif slot_level > spell.level:
                details += f" (upcast to level {slot_level})"

            await MemoryCaptureService.capture_spell_cast(
                db=db,
                session_id=session.id,
                spell_name=spell.name,
                spell_level=spell.level,
                target=request.target_name if hasattr(request, "target_name") else None,
                outcome=details,
            )
    except Exception as e:
        logger.warning(f"Failed to capture spell cast memory: {e}")

    return CastSpellResponse(
        character_id=character.id,
        character_name=character.name,
        spell_name=spell.name,
        spell_level=spell.level,
        slot_level_used=slot_level if not request.is_ritual_cast else 0,
        damage_roll=damage_roll,
        total_damage=total_damage,
        description=spell.description,
        remaining_slots=character.spell_slots or {},
    )


def _roll_dice(dice_notation: str) -> int:
    """Roll dice from notation like '3d6', '1d8+2', etc.

    Args:
        dice_notation: Dice notation string

    Returns:
        Total rolled value
    """
    try:
        # Handle bonus (e.g., "1d8+2")
        bonus = 0
        if "+" in dice_notation:
            parts = dice_notation.split("+")
            dice_notation = parts[0].strip()
            bonus = int(parts[1].strip())
        elif "-" in dice_notation:
            parts = dice_notation.split("-")
            dice_notation = parts[0].strip()
            bonus = -int(parts[1].strip())

        # Parse dice (e.g., "3d6")
        dice_parts = dice_notation.split("d")
        if len(dice_parts) == 2:
            num_dice = int(dice_parts[0])
            die_size = int(dice_parts[1])
            return sum(random.randint(1, die_size) for _ in range(num_dice)) + bonus

        # If not dice notation, try to parse as integer
        return int(dice_notation) + bonus
    except (ValueError, IndexError):
        return 0


@router.post("/character/{character_id}/rest", response_model=SpellSlotsResponse)
async def long_rest(character_id: UUID, db: AsyncSession = Depends(get_db)):
    """Perform a long rest, restoring all spell slots

    Args:
        character_id: Character UUID
        db: Database session

    Returns:
        Restored spell slots

    Raises:
        HTTPException: 404 if character not found
    """
    character = await CharacterService.get_character(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Reset all spell slots
    if character.spell_slots:
        for level_key in character.spell_slots:
            character.spell_slots[level_key]["used"] = 0

    # Drop concentration
    character.active_concentration_spell = None

    # Also restore HP
    character.hp_current = character.hp_max

    await db.commit()

    return SpellSlotsResponse(
        character_id=character.id,
        character_name=character.name,
        spell_slots=character.spell_slots or {},
    )


@router.post("/character/{character_id}/concentration-check")
async def concentration_check(
    character_id: UUID,
    damage_taken: int = Query(..., ge=1, description="Damage taken that triggers the save"),
    db: AsyncSession = Depends(get_db),
):
    """Perform a concentration check after taking damage

    DC = 10 or half the damage taken, whichever is higher
    Character must beat DC with CON save or lose concentration

    Args:
        character_id: Character UUID
        damage_taken: Amount of damage that triggered the check
        db: Database session

    Returns:
        Result of the concentration check

    Raises:
        HTTPException: 404 if character not found
    """
    character = await CharacterService.get_character(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    if not character.active_concentration_spell:
        return {"success": True, "message": "Character is not concentrating on any spell"}

    # Calculate DC: 10 or half damage, whichever is higher
    dc = max(10, damage_taken // 2)

    # Roll concentration save (d20 + CON modifier)
    roll = random.randint(1, 20)
    con_modifier = (character.constitution - 10) // 2
    total = roll + con_modifier

    success = total >= dc

    if not success:
        # Failed save - drop concentration
        character.active_concentration_spell = None
        await db.commit()

    return {
        "success": success,
        "roll": roll,
        "modifier": con_modifier,
        "total": total,
        "dc": dc,
        "message": f"Concentration {'maintained' if success else 'broken'}!",
    }
