"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class HealthCheckResponse(BaseModel):
    """Health check response model"""
    status: str = Field(description="Service status")
    app_name: str = Field(description="Application name")
    version: str = Field(description="Application version")
    environment: str = Field(description="Environment")
    timestamp: datetime = Field(description="Current timestamp")


class NarrateRequest(BaseModel):
    """Request model for player action narration"""
    action: str = Field(..., description="The player's action to narrate", min_length=1)
    character_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional character information (name, class, level, etc.)"
    )
    game_state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional game state (location, inventory, quest log, etc.)"
    )


class NarrateResponse(BaseModel):
    """Response model for narration"""
    narration: str = Field(..., description="The DM's narration")
    tokens_used: int = Field(..., description="Number of tokens consumed")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
