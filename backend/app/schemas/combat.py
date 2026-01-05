"""Combat encounter schemas"""

from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CombatParticipant(BaseModel):
    """A participant in combat"""

    character_id: Optional[UUID] = None
    name: str
    initiative: int
    hp_current: int
    hp_max: int
    ac: int
    is_enemy: bool = False
    conditions: List[str] = []


class StartCombatRequest(BaseModel):
    """Request to start a combat encounter"""

    session_id: UUID
    participants: List[CombatParticipant]


class CombatActionType(str):
    """Types of combat actions"""

    ATTACK = "attack"
    CAST_SPELL = "cast_spell"
    USE_ITEM = "use_item"
    DASH = "dash"
    DODGE = "dodge"
    HELP = "help"
    HIDE = "hide"
    READY = "ready"
    END_TURN = "end_turn"


class CombatActionRequest(BaseModel):
    """Request to perform a combat action"""

    action_type: str = Field(..., description="Type of action")
    target_index: Optional[int] = Field(None, description="Index of target in participants list")
    spell_id: Optional[UUID] = Field(None, description="Spell ID if casting")
    item_id: Optional[UUID] = Field(None, description="Item ID if using item")
    damage: Optional[int] = Field(None, description="Manual damage override")
    notes: Optional[str] = Field(None, description="Additional notes about the action")


class CombatActionResponse(BaseModel):
    """Response from a combat action"""

    success: bool
    message: str
    damage_dealt: Optional[int] = None
    healing_done: Optional[int] = None
    log_entry: str


class CombatStatusResponse(BaseModel):
    """Current combat status"""

    combat_id: UUID
    session_id: UUID
    is_active: bool
    current_turn: int
    round_number: int
    participants: List[Dict]
    turn_order: List[int]
    combat_log: List[str]
    current_participant: Optional[Dict] = None


class EndCombatResponse(BaseModel):
    """Response when combat ends"""

    combat_id: UUID
    total_rounds: int
    duration_seconds: Optional[float] = None
    participants_survived: int
    participants_defeated: int
    combat_log: List[str]
