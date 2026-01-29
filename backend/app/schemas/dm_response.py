"""Schema for DM responses with roll requests"""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class RollRequest(BaseModel):
    """Roll request from DM"""

    type: str  # "check", "attack", "save", "initiative", "custom"
    ability: Optional[str] = None  # "STR", "DEX", etc.
    skill: Optional[str] = None  # "stealth", "perception", etc.
    dc: Optional[int] = None
    dice: Optional[str] = None  # For custom rolls
    target: Optional[str] = None  # For attacks
    reason: Optional[str] = None
    advantage: Optional[bool] = None
    disadvantage: Optional[bool] = None
    description: Optional[str] = None


class PlayerActionRequest(BaseModel):
    """Request for player action with DM response"""

    character_id: UUID
    session_id: Optional[str] = None
    action: str
    roll_result: Optional[dict] = None  # If responding to a roll request


class DMResponse(BaseModel):
    """DM response with optional roll request and quest completion"""

    response: str
    roll_request: Optional[RollRequest] = None
    roll_requests: Optional[list[RollRequest]] = None
    quest_complete_id: Optional[str] = None  # UUID of completed quest
    scene_image_url: Optional[str] = None
    tokens_used: int
    rolls: Optional[list[dict[str, Any]]] = None  # Executed dice rolls
    companion_speech: Optional[str] = None  # AI companion contextual response (legacy)
    companion_responses: Optional[list[dict[str, Any]]] = (
        None  # RL-131: Companion responses with full data
    )
    warnings: Optional[list[str]] = None  # Spell detection warnings and suggestions
    tool_calls_made: Optional[list[dict[str, Any]]] = None  # RL-129: Mistral tool calls
    character_updates: Optional[dict[str, Any]] = None  # RL-129: Character state changes from tools
