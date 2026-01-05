"""AI Companion API endpoints"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.middleware.auth import get_current_active_user
from app.services.companion_service import CompanionService

router = APIRouter(prefix="/api/companion", tags=["companion"])


class CompanionSpeechRequest(BaseModel):
    """Request model for companion speech generation"""

    personality: str
    companion_name: str
    companion_race: str
    companion_class: str
    trigger: str
    context: Dict[str, Any]
    user_message: Optional[str] = None


class CompanionSpeechResponse(BaseModel):
    """Response model for companion speech"""

    speech: str
    personality: str
    trigger: str


@router.post("/speech", response_model=CompanionSpeechResponse)
async def generate_companion_speech(
    request: CompanionSpeechRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI companion speech based on personality and context

    Args:
        request: Speech generation request with personality, context, trigger
        current_user: Authenticated user
        db: Database session

    Returns:
        Generated companion speech

    Raises:
        HTTPException: 400 if personality invalid
    """
    # Validate personality
    valid_personalities = ["helpful", "brave", "cautious", "sarcastic", "mysterious", "scholarly"]
    if request.personality not in valid_personalities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid personality. Must be one of: {', '.join(valid_personalities)}",
        )

    # Generate speech
    speech = await CompanionService.generate_companion_speech(
        personality=request.personality,
        companion_name=request.companion_name,
        companion_race=request.companion_race,
        companion_class=request.companion_class,
        trigger=request.trigger,
        context=request.context,
        user_message=request.user_message,
    )

    return CompanionSpeechResponse(
        speech=speech, personality=request.personality, trigger=request.trigger
    )


@router.get("/personalities")
async def list_personalities():
    """List available companion personalities with their triggers

    Returns:
        Dict of personalities with their trigger events
    """
    from app.services.companion_service import COMPANION_PERSONALITIES

    return {
        personality: {"triggers": data["triggers"], "description": personality.capitalize()}
        for personality, data in COMPANION_PERSONALITIES.items()
    }
