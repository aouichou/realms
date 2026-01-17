"""Save/Load API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.middleware.auth import get_current_active_user
from app.observability.tracing import trace_async
from app.services.save_service import SaveService

router = APIRouter(prefix="/game", tags=["game"])


class SaveRequest(BaseModel):
    """Request to save game"""

    session_id: UUID
    save_name: str | None = None
    overwrite: bool = False


class SaveResponse(BaseModel):
    """Response for save operation"""

    success: bool
    save_data: dict


class LoadResponse(BaseModel):
    """Response for load operation"""

    found: bool
    save_data: dict | None


@router.post("/save", response_model=SaveResponse)
@trace_async("game.save")
async def save_game(
    request: SaveRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Save current game state

    Args:
        request: Save request with session_id, save_name, and overwrite flag
        current_user: Authenticated user
        db: Database session

    Returns:
        Save confirmation with data

    Raises:
        HTTPException: 409 if save name already exists and overwrite is False
    """
    try:
        save_data = await SaveService.save_game(
            db, request.session_id, request.save_name, request.overwrite
        )
        return SaveResponse(success=True, save_data=save_data)
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise


@router.get("/load/{session_id}", response_model=LoadResponse)
@trace_async("game.load")
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
@trace_async("game.list_saves")
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
