"""Character API router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.middleware.auth import get_current_active_user
from app.schemas.character import (
    CharacterCreate,
    CharacterListResponse,
    CharacterResponse,
    CharacterUpdate,
)
from app.schemas.character_stats import CharacterStatsResponse
from app.services.character_service import CharacterService

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.post("", response_model=CharacterResponse, status_code=201)
async def create_character(
    character_data: CharacterCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new D&D character.

    Args:
        character_data: Character creation data
        current_user: Authenticated user (from JWT)
        db: Database session

    Returns:
        Created character
    """
    character = await CharacterService.create_character(db, character_data, current_user.id)
    return character


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a character by ID.

    Args:
        character_id: Character UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Character details

    Raises:
        HTTPException: 404 if character not found
    """
    character = await CharacterService.get_character(db, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.get("", response_model=CharacterListResponse)
async def list_characters(
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """List characters for the authenticated user with pagination.

    Args:
        current_user: Authenticated user
        page: Page number (1-indexed)
        page_size: Number of items per page
        db: Database session

    Returns:
        Paginated list of characters
    """
    skip = (page - 1) * page_size

    # Get characters for the authenticated user
    characters, total = await CharacterService.get_user_characters(
        db, current_user.id, skip=skip, limit=page_size
    )

    return CharacterListResponse(characters=characters, total=total, page=page, page_size=page_size)


@router.patch("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: UUID, character_data: CharacterUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a character.

    Args:
        character_id: Character UUID
        character_data: Character update data
        db: Database session

    Returns:
        Updated character

    Raises:
        HTTPException: 404 if character not found
    """
    character = await CharacterService.update_character(db, character_id, character_data)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.delete("/{character_id}", status_code=204)
async def delete_character(character_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a character.

    Args:
        character_id: Character UUID
        db: Database session

    Raises:
        HTTPException: 404 if character not found
    """
    deleted = await CharacterService.delete_character(db, character_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Character not found")


@router.post("/{character_id}/skills", response_model=CharacterResponse)
async def update_skill_proficiencies(
    character_id: UUID,
    skills: list[str],
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update character's skill proficiencies.

    Args:
        character_id: Character UUID
        skills: List of skill names the character is proficient in
        current_user: Currently authenticated user
        db: Database session

    Returns:
        Updated character data

    Raises:
        HTTPException: 404 if character not found or doesn't belong to user
    """
    from app.schemas.character import CharacterUpdate

    # Verify character exists and belongs to user
    character = await CharacterService.get_character(db, character_id)
    if not character or str(character.user_id) != current_user["sub"]:
        raise HTTPException(status_code=404, detail="Character not found")

    # Update skills
    update_data = CharacterUpdate(skill_proficiencies=skills)
    updated_character = await CharacterService.update_character(db, character_id, update_data)

    if not updated_character:
        raise HTTPException(status_code=404, detail="Character not found")

    return updated_character


@router.post("/{character_id}/background", response_model=CharacterResponse)
async def update_background(
    character_id: UUID,
    background_name: str,
    background_description: str,
    background_skill_proficiencies: list[str],
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update character's background.

    Args:
        character_id: Character UUID
        background_name: Name of the background
        background_description: Description of the background
        background_skill_proficiencies: Skills granted by the background
        current_user: Currently authenticated user
        db: Database session

    Returns:
        Updated character data

    Raises:
        HTTPException: 404 if character not found or doesn't belong to user
    """
    from app.schemas.character import CharacterUpdate

    # Verify character exists and belongs to user
    character = await CharacterService.get_character(db, character_id)
    if not character or str(character.user_id) != current_user["sub"]:
        raise HTTPException(status_code=404, detail="Character not found")

    # Update background
    update_data = CharacterUpdate(
        background_name=background_name,
        background_description=background_description,
        background_skill_proficiencies=background_skill_proficiencies,
    )
    updated_character = await CharacterService.update_character(db, character_id, update_data)

    if not updated_character:
        raise HTTPException(status_code=404, detail="Character not found")

    return updated_character


@router.get("/{character_id}/stats", response_model=CharacterStatsResponse)
async def get_character_stats(character_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get full character statistics including equipment bonuses.

    This endpoint calculates:
    - Ability modifiers
    - Proficiency bonus
    - Armor Class (including equipped armor and shields)
    - Attack bonuses
    - Spell save DC
    - Skill modifiers
    - Saving throw modifiers

    Args:
        character_id: Character UUID
        db: Database session

    Returns:
        Complete character statistics

    Raises:
        HTTPException: 404 if character not found
    """
    stats = await CharacterService.calculate_character_stats(db, character_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Character not found")
    return stats
