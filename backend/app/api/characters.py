"""Character API router."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
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
    user_id: Optional[UUID] = None,  # TODO: Replace with auth user from JWT
    db: AsyncSession = Depends(get_db)
):
    """Create a new D&D character.
    
    Args:
        character_data: Character creation data
        user_id: User ID (from authentication)
        db: Database session
        
    Returns:
        Created character
    """
    character = await CharacterService.create_character(db, character_data, user_id)
    return character


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a character by ID.
    
    Args:
        character_id: Character UUID
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
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """List characters with pagination.
    
    Args:
        user_id: Optional user ID filter
        page: Page number (1-indexed)
        page_size: Number of items per page
        db: Database session
        
    Returns:
        Paginated list of characters
    """
    skip = (page - 1) * page_size
    
    if user_id:
        characters, total = await CharacterService.get_user_characters(
            db, user_id, skip=skip, limit=page_size
        )
    else:
        # TODO: For now, return empty if no user_id
        # Later, implement admin endpoint to list all characters
        characters, total = [], 0
    
    return CharacterListResponse(
        characters=characters,
        total=total,
        page=page,
        page_size=page_size
    )


@router.patch("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: UUID,
    character_data: CharacterUpdate,
    db: AsyncSession = Depends(get_db)
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
async def delete_character(
    character_id: UUID,
    db: AsyncSession = Depends(get_db)
):
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


@router.get("/{character_id}/stats", response_model=CharacterStatsResponse)
async def get_character_stats(
    character_id: UUID,
    db: AsyncSession = Depends(get_db)
):
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
