"""Dice rolling API endpoints."""
from fastapi import APIRouter, HTTPException

from app.schemas.dice import DiceRollRequest, DiceRollResponse, DiceRollResult
from app.services.dice_service import DiceService

router = APIRouter(prefix="/api/dice", tags=["dice"])


@router.post("/roll", response_model=DiceRollResponse)
async def roll_dice(request: DiceRollRequest) -> DiceRollResponse:
    """Roll dice according to D&D notation.
    
    Args:
        request: Dice roll request with notation and roll type
        
    Returns:
        Dice roll response with results and breakdown
        
    Raises:
        HTTPException: If dice notation is invalid
    """
    try:
        rolls, modifier, total = DiceService.roll_dice(
            request.dice,
            request.roll_type
        )
        
        breakdown = DiceService.format_breakdown(
            request.dice,
            rolls,
            modifier,
            total
        )
        
        return DiceRollResponse(
            notation=request.dice,
            roll_type=request.roll_type,
            individual_rolls=rolls,
            modifier=modifier,
            total=total,
            reason=request.reason,
            breakdown=breakdown
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
