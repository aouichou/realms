"""Dice rolling schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DiceType(str, Enum):
    """Standard D&D dice types."""

    D4 = "d4"
    D6 = "d6"
    D8 = "d8"
    D10 = "d10"
    D12 = "d12"
    D20 = "d20"
    D100 = "d100"


class RollType(str, Enum):
    """Roll type modifiers."""

    NORMAL = "normal"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"


class DiceRollRequest(BaseModel):
    """Request for rolling dice."""

    dice: str = Field(..., description="Dice notation (e.g., '2d6+3', 'd20', '3d8-2')")
    roll_type: RollType = Field(RollType.NORMAL, description="Normal, advantage, or disadvantage")
    reason: Optional[str] = Field(None, max_length=255, description="Reason for the roll")


class DiceRollResult(BaseModel):
    """Individual die roll result."""

    die_type: str
    roll: int
    dropped: bool = False  # For advantage/disadvantage


class DiceRollResponse(BaseModel):
    """Response from dice roll."""

    notation: str = Field(..., description="Original dice notation")
    roll_type: str
    individual_rolls: list[DiceRollResult]
    modifier: int = 0
    total: int
    reason: Optional[str] = None
    breakdown: str = Field(..., description="Human-readable breakdown")
