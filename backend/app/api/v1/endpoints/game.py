"""Save/Load API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.middleware.auth import get_current_active_user
from app.services.save_service import SaveService

router = APIRouter(prefix="/game", tags=["game"])


class SaveRequest(BaseModel):
    """Request to save game"""

    session_id: UUID
    save_name: str | None = None


class SaveResponse(BaseModel):
    """Response for save operation"""

    success: bool
    save_data: dict


class LoadResponse(BaseModel):
    """Response for load operation"""

    found: bool
    save_data: dict | None


@router.post("/save", response_model=SaveResponse)
async def save_game(
    request: SaveRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Save current game state

    Args:
        request: Save request with session_id
        current_user: Authenticated user
        db: Database session

    Returns:
        Save confirmation with data
    """
    save_data = await SaveService.save_game(db, request.session_id, request.save_name)

    return SaveResponse(success=True, save_data=save_data)


@router.get("/load/{session_id}", response_model=LoadResponse)
async def load_game(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Load saved game state

    Args:
        session_id: Session ID to load
        current_user: Authenticated user
        db: Database session

    Returns:
        Saved game data or None
    """
    save_data = await SaveService.load_game(db, session_id)

    return LoadResponse(found=save_data is not None, save_data=save_data)


@router.get("/saves", response_model=list[dict])
async def list_saves(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
):
    """List all saves for authenticated user

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        List of saves
    """
    return await SaveService.list_saves(db, current_user.id)
