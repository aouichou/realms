"""API endpoints for preset adventures"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.services.adventure_service import AdventureService

router = APIRouter(prefix="/api/adventures", tags=["adventures"])


class StartPresetAdventureRequest(BaseModel):
    """Request to start a preset adventure"""

    character_id: UUID
    adventure_id: str


class AdventureInfo(BaseModel):
    """Information about a preset adventure"""

    id: str
    title: str
    description: str
    recommended_level: int
    setting: str


class StartedAdventureResponse(BaseModel):
    """Response after starting an adventure"""

    session_id: str
    quest_id: str
    adventure_id: str
    title: str
    opening_narration: str
    setting: str
    initial_location: str


@router.get("/list", response_model=List[AdventureInfo])
async def list_adventures(db: AsyncSession = Depends(get_db)):
    """Get list of all available preset adventures"""
    service = AdventureService(db)
    adventures = await service.get_available_adventures()
    return adventures


@router.post("/start-preset", response_model=StartedAdventureResponse)
async def start_preset_adventure(
    request: StartPresetAdventureRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a preset adventure for a character.
    Creates a quest, game session, and returns opening narration.
    """
    service = AdventureService(db)

    try:
        result = await service.start_preset_adventure(
            character_id=request.character_id,
            adventure_id=request.adventure_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start adventure: {str(e)}")


@router.get("/{adventure_id}")
async def get_adventure_details(
    adventure_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a specific adventure"""
    service = AdventureService(db)
    adventure = await service.load_adventure(adventure_id)

    if not adventure:
        raise HTTPException(status_code=404, detail=f"Adventure {adventure_id} not found")

    return {
        "id": adventure.id,
        "title": adventure.title,
        "description": adventure.description,
        "recommended_level": adventure.recommended_level,
        "setting": adventure.setting,
        "opening_narration": adventure.opening_narration,
        "initial_location": adventure.initial_location,
        "quest_objectives": adventure.quest_data["objectives"],
        "rewards": adventure.quest_data["rewards"],
    }
