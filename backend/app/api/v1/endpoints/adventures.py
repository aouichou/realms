"""API endpoints for preset and custom adventures"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.observability.tracing import trace_async
from app.services.adventure_service import AdventureService

router = APIRouter(prefix="/adventures", tags=["adventures"])


class StartPresetAdventureRequest(BaseModel):
    """Request to start a preset adventure"""

    character_id: UUID
    adventure_id: str


class StartCustomAdventureRequest(BaseModel):
    """Request to start a custom adventure"""

    character_id: UUID
    adventure_id: UUID


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
    quest_id: Optional[str] = None
    adventure_id: str
    title: str
    opening_narration: str
    setting: str
    initial_location: str
    combat_encounter_data: Optional[Dict[str, Any]] = None
    npcs: Optional[List[Dict[str, Any]]] = None
    initial_location: str


@router.get("/list", response_model=List[AdventureInfo])
@trace_async("adventures.list")
async def list_adventures(db: AsyncSession = Depends(get_db)):
    """Get list of all available preset adventures"""
    service = AdventureService(db)
    adventures = await service.get_available_adventures()
    return adventures


@router.post("/start-preset", response_model=StartedAdventureResponse)
@trace_async("adventures.start_preset")
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


@router.post("/start-custom", response_model=StartedAdventureResponse)
@trace_async("adventures.start_custom")
async def start_custom_adventure(
    request: StartCustomAdventureRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a custom AI-generated adventure for a character.
    Creates a game session and returns opening narration based on the adventure's first scene.
    """
    service = AdventureService(db)

    try:
        result = await service.start_custom_adventure(
            character_id=request.character_id,
            adventure_id=request.adventure_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start custom adventure: {str(e)}")


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


# Custom Adventure Generation Endpoints


class CustomAdventureRequest(BaseModel):
    """Request to generate a custom adventure"""

    character_id: UUID
    setting: str
    goal: str
    tone: str


class CustomAdventureResponse(BaseModel):
    """Response with generated custom adventure"""

    id: UUID
    character_id: UUID
    setting: str
    goal: str
    tone: str
    title: str
    description: str
    scenes: Any  # JSONB field from database
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/generate", response_model=CustomAdventureResponse)
async def generate_custom_adventure(
    request: CustomAdventureRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a custom adventure using AI based on player choices.
    Uses a 3-question questionnaire (setting, goal, tone) to create unique adventures.
    """
    service = AdventureService(db)

    try:
        adventure = await service.generate_custom_adventure(
            character_id=request.character_id,
            setting=request.setting,
            goal=request.goal,
            tone=request.tone,
        )

        return CustomAdventureResponse(
            id=adventure.id,
            character_id=adventure.character_id,
            setting=adventure.setting,
            goal=adventure.goal,
            tone=adventure.tone,
            title=adventure.title,
            description=adventure.description,
            scenes=adventure.scenes,
            is_completed=adventure.is_completed,
            created_at=adventure.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate adventure: {str(e)}")


@router.get("/custom/character/{character_id}", response_model=List[CustomAdventureResponse])
async def list_character_adventures(
    character_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all custom adventures for a character"""
    from sqlalchemy import select

    from app.db.models import Adventure

    result = await db.execute(
        select(Adventure)
        .where(Adventure.character_id == character_id)
        .order_by(Adventure.created_at.desc())
    )
    adventures = result.scalars().all()

    return [
        CustomAdventureResponse(
            id=adv.id,
            character_id=adv.character_id,
            setting=adv.setting,
            goal=adv.goal,
            tone=adv.tone,
            title=adv.title,
            description=adv.description,
            scenes=adv.scenes,
            is_completed=adv.is_completed,
            created_at=adv.created_at,
        )
        for adv in adventures
    ]


@router.get("/custom/{adventure_id}", response_model=CustomAdventureResponse)
async def get_custom_adventure(
    adventure_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a generated custom adventure by ID"""
    service = AdventureService(db)
    adventure = await service.get_adventure(adventure_id)

    if not adventure:
        raise HTTPException(status_code=404, detail=f"Adventure {adventure_id} not found")

    return CustomAdventureResponse(
        id=adventure.id,
        character_id=adventure.character_id,
        setting=adventure.setting,
        goal=adventure.goal,
        tone=adventure.tone,
        title=adventure.title,
        description=adventure.description,
        scenes=adventure.scenes,
        is_completed=adventure.is_completed,
        created_at=adventure.created_at,
    )
