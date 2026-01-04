"""Character API router."""
from typing import Optional
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
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db)
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
