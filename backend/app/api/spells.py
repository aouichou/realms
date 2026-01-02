"""Spells API endpoints"""
import random
import uuid
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.db.models import Spell, CharacterSpell, Character, CharacterClass
from app.schemas.spell import (
    SpellCreate,
    SpellResponse,
    SpellListResponse,
    CharacterSpellCreate,
    CharacterSpellResponse,
    PrepareSpellsRequest,
    CastSpellRequest,
    CastSpellResponse,
    SpellSlotsResponse
)
from app.services.character_service import CharacterService

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
    if character_class in [CharacterClass.WIZARD, CharacterClass.CLERIC, CharacterClass.SORCERER]:
        progression = SPELL_SLOTS_BY_LEVEL["full"]
    elif character_class in [CharacterClass.PALADIN, CharacterClass.RANGER]:
        progression = SPELL_SLOTS_BY_LEVEL["half"]
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
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """List all spells with optional filters
    
    Args:
        level: Filter by spell level (0-9)
        school: Filter by school of magic
        character_class: Filter by class (e.g., 'wizard', 'cleric')
        page: Page number
        page_size: Items per page
        db: Database session
        
    Returns:
        Paginated list of spells
    """
    query = select(Spell)
    
    # Apply filters
    if level is not None:
        query = query.where(Spell.level == level)
    if school:
        query = query.where(Spell.school == school)
    if character_class:
        # Filter spells available to this class
        query = query.where(Spell.available_to_classes[character_class.lower()].astext.cast(db.bind.dialect.BOOLEAN) == True)
    
    # Get total count
    count_result = await db.execute(query)
    total = len(count_result.all())
    
    # Apply pagination
    skip = (page - 1) * page_size
    query = query.offset(skip).limit(page_size)
    
    result = await db.execute(query)
    spells = result.scalars().all()
    
    return SpellListResponse(
        spells=[SpellResponse.model_validate(spell) for spell in spells],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{spell_id}", response_model=SpellResponse)
async def get_spell(
    spell_id: UUID,
    db: AsyncSession = Depends(get_db)
):
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
async def create_spell(
    spell_data: SpellCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new spell
    
    Args:
        spell_data: Spell creation data
        db: Database session
        
    Returns:
        Created spell
    """
    spell = Spell(
        id=uuid.uuid4(),
        **spell_data.model_dump()
    )
    
    db.add(spell)
    await db.commit()
    await db.refresh(spell)
    
    return SpellResponse.model_validate(spell)


@router.get("/character/{character_id}/spells", response_model=List[CharacterSpellResponse])
async def get_character_spells(
    character_id: UUID,
    known_only: bool = Query(False, description="Show only known spells"),
    prepared_only: bool = Query(False, description="Show only prepared spells"),
    db: AsyncSession = Depends(get_db)
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
        query = query.where(CharacterSpell.is_known == True)
    if prepared_only:
        query = query.where(CharacterSpell.is_prepared == True)
    
    query = query.options(selectinload(CharacterSpell.spell))
    
    result = await db.execute(query)
    character_spells = result.scalars().all()
    
    return [CharacterSpellResponse.model_validate(cs) for cs in character_spells]


@router.post("/character/{character_id}/spells", response_model=CharacterSpellResponse, status_code=201)
async def add_spell_to_character(
    character_id: UUID,
    spell_data: CharacterSpellCreate,
    db: AsyncSession = Depends(get_db)
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
                CharacterSpell.spell_id == spell_data.spell_id
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
        is_prepared=spell_data.is_prepared
    )
    
    db.add(character_spell)
    await db.commit()
    await db.refresh(character_spell, ["spell"])
    
    return CharacterSpellResponse.model_validate(character_spell)


@router.post("/character/{character_id}/prepare", response_model=List[CharacterSpellResponse])
async def prepare_spells(
    character_id: UUID,
    request: PrepareSpellsRequest,
    db: AsyncSession = Depends(get_db)
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
        select(CharacterSpell)
        .where(CharacterSpell.character_id == character_id)
        .values(is_prepared=False)
    )
    
    # Prepare selected spells
    for spell_id in request.spell_ids:
        result = await db.execute(
            select(CharacterSpell).where(
                and_(
                    CharacterSpell.character_id == character_id,
                    CharacterSpell.spell_id == spell_id
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
            and_(
                CharacterSpell.character_id == character_id,
                CharacterSpell.is_prepared == True
            )
        )
        .options(selectinload(CharacterSpell.spell))
    )
    prepared_spells = result.scalars().all()
    
    return [CharacterSpellResponse.model_validate(cs) for cs in prepared_spells]


@router.get("/character/{character_id}/slots", response_model=SpellSlotsResponse)
async def get_spell_slots(
    character_id: UUID,
    db: AsyncSession = Depends(get_db)
):
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
        spell_slots=character.spell_slots or {}
    )


@router.post("/character/{character_id}/cast", response_model=CastSpellResponse)
async def cast_spell(
    character_id: UUID,
    request: CastSpellRequest,
    db: AsyncSession = Depends(get_db)
):
    """Cast a spell, consuming a spell slot
    
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
                CharacterSpell.spell_id == request.spell_id
            )
        )
        .options(selectinload(CharacterSpell.spell))
    )
    character_spell = result.scalar_one_or_none()
    if not character_spell:
        raise HTTPException(status_code=404, detail="Character doesn't know this spell")
    
    spell = character_spell.spell
    
    # Check if spell needs to be prepared
    if character.character_class in [CharacterClass.WIZARD, CharacterClass.CLERIC]:
        if not character_spell.is_prepared and spell.level > 0:  # Cantrips don't need preparation
            raise HTTPException(status_code=400, detail="Spell not prepared")
    
    # Cantrips don't consume spell slots
    if spell.level == 0:
        damage_roll = None
        total_damage = None
        if spell.damage_dice:
            # Roll damage for cantrip
            damage_roll = spell.damage_dice
            # Simple damage calculation (would be more complex in real implementation)
            dice_parts = damage_roll.split('d')
            if len(dice_parts) == 2:
                num_dice = int(dice_parts[0])
                die_size = int(dice_parts[1])
                total_damage = sum(random.randint(1, die_size) for _ in range(num_dice))
        
        return CastSpellResponse(
            character_id=character.id,
            character_name=character.name,
            spell_name=spell.name,
            spell_level=0,
            slot_level_used=0,
            damage_roll=damage_roll,
            total_damage=total_damage,
            description=spell.description,
            remaining_slots=character.spell_slots or {}
        )
    
    # Check spell slot availability
    spell_slots = character.spell_slots or {}
    slot_key = str(request.spell_level)
    
    if slot_key not in spell_slots:
        raise HTTPException(status_code=400, detail=f"No level {request.spell_level} spell slots")
    
    slot_info = spell_slots[slot_key]
    if slot_info["used"] >= slot_info["total"]:
        raise HTTPException(status_code=400, detail=f"No level {request.spell_level} spell slots remaining")
    
    # Consume spell slot
    spell_slots[slot_key]["used"] += 1
    character.spell_slots = spell_slots
    
    # Roll damage if applicable
    damage_roll = None
    total_damage = None
    if spell.damage_dice:
        damage_roll = spell.damage_dice
        # Simple damage calculation
        dice_parts = damage_roll.replace('+', ' ').split('d')
        if len(dice_parts) == 2:
            num_dice = int(dice_parts[0])
            die_info = dice_parts[1].split()
            die_size = int(die_info[0])
            bonus = int(die_info[1]) if len(die_info) > 1 else 0
            total_damage = sum(random.randint(1, die_size) for _ in range(num_dice)) + bonus
    
    await db.commit()
    
    return CastSpellResponse(
        character_id=character.id,
        character_name=character.name,
        spell_name=spell.name,
        spell_level=spell.level,
        slot_level_used=request.spell_level,
        damage_roll=damage_roll,
        total_damage=total_damage,
        description=spell.description,
        remaining_slots=spell_slots
    )


@router.post("/character/{character_id}/rest", response_model=SpellSlotsResponse)
async def long_rest(
    character_id: UUID,
    db: AsyncSession = Depends(get_db)
):
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
    
    # Also restore HP
    character.hp_current = character.hp_max
    
    await db.commit()
    
    return SpellSlotsResponse(
        character_id=character.id,
        character_name=character.name,
        spell_slots=character.spell_slots or {}
    )
