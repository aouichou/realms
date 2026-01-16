"""
Pydantic models for request/response validation
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class NarrateRequest(BaseModel):
    """Request model for player action narration"""

    action: str = Field(..., description="The player's action to narrate", min_length=1)
    character_context: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional character information (name, class, level, etc.)"
    )
    game_state: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional game state (location, inventory, quest log, etc.)"
    )


class NarrateResponse(BaseModel):
    """Response model for narration"""

    narration: str = Field(..., description="The DM's narration")
    tokens_used: int = Field(..., description="Number of tokens consumed")
