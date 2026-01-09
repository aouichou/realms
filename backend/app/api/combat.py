"""Combat encounter API endpoints"""

import random
import uuid
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import CombatEncounter, GameSession
from app.schemas.combat import (
    CombatActionRequest,
    CombatActionResponse,
    CombatActionType,
    CombatStatusResponse,
    EndCombatResponse,
    StartCombatRequest,
)
from app.services.character_service import CharacterService
from app.services.memory_capture import MemoryCaptureService
from app.utils.logger import logger

router = APIRouter(prefix="/api/combat", tags=["combat"])


@router.post("/start", response_model=CombatStatusResponse, status_code=201)
async def start_combat(request: StartCombatRequest, db: AsyncSession = Depends(get_db)):
    """Start a new combat encounter

    Rolls initiative for all participants and sorts turn order.
    Initiative = 1d20 + DEX modifier

    Args:
        request: Combat start request with participants
        db: Database session

    Returns:
        Initial combat status

    Raises:
        HTTPException: 404 if session not found, 400 if combat already active
    """
    # Check session exists
    result = await db.execute(select(GameSession).where(GameSession.id == request.session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if there's already an active combat
    existing = await db.execute(
        select(CombatEncounter).where(
            and_(
                CombatEncounter.session_id == request.session_id,
                CombatEncounter.is_active.is_(True),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Combat already in progress for this session")

    # Roll initiative for each participant
    participants_with_initiative = []
    for i, participant in enumerate(request.participants):
        # Get DEX modifier if we have character_id
        dex_modifier = 0
        if participant.character_id:
            character = await CharacterService.get_character(db, participant.character_id)
            if character:
                dex_modifier = CharacterService.calculate_ability_modifier(character.dexterity)

        # Roll initiative (1d20 + DEX modifier)
        initiative_roll = random.randint(1, 20) + dex_modifier

        participants_with_initiative.append(
            {
                "index": i,
                "character_id": str(participant.character_id) if participant.character_id else None,
                "name": participant.name,
                "initiative": initiative_roll,
                "hp_current": participant.hp_current,
                "hp_max": participant.hp_max,
                "ac": participant.ac,
                "is_enemy": participant.is_enemy,
                "conditions": participant.conditions,
            }
        )

    # Sort by initiative (highest first)
    participants_with_initiative.sort(key=lambda x: x["initiative"], reverse=True)
    turn_order = [p["index"] for p in participants_with_initiative]

    # Create combat encounter
    combat = CombatEncounter(
        id=uuid.uuid4(),
        session_id=request.session_id,
        is_active=True,
        current_turn=0,
        round_number=1,
        participants=participants_with_initiative,
        turn_order=turn_order,
        combat_log=["Combat started! Initiative rolled."],
    )

    db.add(combat)
    await db.commit()
    await db.refresh(combat)

    return CombatStatusResponse(
        combat_id=combat.id,
        session_id=combat.session_id,
        is_active=combat.is_active,
        current_turn=combat.current_turn,
        round_number=combat.round_number,
        participants=list(combat.participants),
        turn_order=combat.turn_order,
        combat_log=combat.combat_log,
        current_participant=combat.participants[combat.current_turn]
        if combat.participants
        else None,
    )


@router.get("/{combat_id}/status", response_model=CombatStatusResponse)
async def get_combat_status(combat_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get current combat status

    Args:
        combat_id: Combat encounter UUID
        db: Database session

    Returns:
        Current combat status

    Raises:
        HTTPException: 404 if combat not found
    """
    result = await db.execute(select(CombatEncounter).where(CombatEncounter.id == combat_id))
    combat = result.scalar_one_or_none()

    if not combat:
        raise HTTPException(status_code=404, detail="Combat encounter not found")

    return CombatStatusResponse(
        combat_id=combat.id,
        session_id=combat.session_id,
        is_active=combat.is_active,
        current_turn=combat.current_turn,
        round_number=combat.round_number,
        participants=list(combat.participants),
        turn_order=combat.turn_order,
        combat_log=combat.combat_log,
        current_participant=combat.participants[combat.current_turn]
        if combat.participants
        else None,
    )


@router.post("/{combat_id}/action", response_model=CombatActionResponse)
async def perform_combat_action(
    combat_id: UUID, action: CombatActionRequest, db: AsyncSession = Depends(get_db)
):
    """Perform a combat action

    Args:
        combat_id: Combat encounter UUID
        action: Action to perform
        db: Database session

    Returns:
        Action result

    Raises:
        HTTPException: 404 if combat not found, 400 if combat not active
    """
    result = await db.execute(select(CombatEncounter).where(CombatEncounter.id == combat_id))
    combat = result.scalar_one_or_none()

    if not combat:
        raise HTTPException(status_code=404, detail="Combat encounter not found")

    if not combat.is_active:
        raise HTTPException(status_code=400, detail="Combat is not active")

    current_participant = combat.participants[combat.current_turn]
    log_entry = ""
    damage_dealt = None
    healing_done = None

    if action.action_type == CombatActionType.ATTACK:
        if action.target_index is None:
            raise HTTPException(status_code=400, detail="Target required for attack")

        target = combat.participants[action.target_index]

        # Simple attack: 1d20 + proficiency + ability modifier
        attack_roll = random.randint(1, 20)
        proficiency = 2  # Simplified
        attack_bonus = proficiency + 3  # Simplified
        total_attack = attack_roll + attack_bonus

        if attack_roll == 20:  # Critical hit
            damage = action.damage or random.randint(2, 12) * 2  # Double dice
            target["hp_current"] = max(0, target["hp_current"] - damage)
            damage_dealt = damage
            log_entry = f"{current_participant['name']} critically hits {target['name']} for {damage} damage! (Natural 20)"
        elif total_attack >= target["ac"]:  # Hit
            damage = action.damage or random.randint(1, 8) + 3
            target["hp_current"] = max(0, target["hp_current"] - damage)
            damage_dealt = damage
            log_entry = f"{current_participant['name']} hits {target['name']} for {damage} damage! (rolled {attack_roll}+{attack_bonus}={total_attack} vs AC {target['ac']})"
        else:  # Miss
            log_entry = f"{current_participant['name']} misses {target['name']}. (rolled {attack_roll}+{attack_bonus}={total_attack} vs AC {target['ac']})"

        combat.participants[action.target_index] = target

    elif action.action_type == CombatActionType.CAST_SPELL:
        log_entry = f"{current_participant['name']} casts a spell!"
        if action.target_index is not None:
            target = combat.participants[action.target_index]
            damage = action.damage or random.randint(2, 12)
            target["hp_current"] = max(0, target["hp_current"] - damage)
            damage_dealt = damage
            combat.participants[action.target_index] = target
            log_entry += f" {target['name']} takes {damage} damage!"

    elif action.action_type == CombatActionType.USE_ITEM:
        healing = action.damage or random.randint(2, 8) + 2
        current_participant["hp_current"] = min(
            current_participant["hp_max"], current_participant["hp_current"] + healing
        )
        healing_done = healing
        combat.participants[combat.current_turn] = current_participant
        log_entry = f"{current_participant['name']} uses a healing item and restores {healing} HP!"

    elif action.action_type == CombatActionType.DODGE:
        log_entry = f"{current_participant['name']} takes the Dodge action."

    elif action.action_type == CombatActionType.DASH:
        log_entry = f"{current_participant['name']} takes the Dash action (double movement)."

    elif action.action_type == CombatActionType.HELP:
        log_entry = f"{current_participant['name']} takes the Help action."

    elif action.action_type == CombatActionType.END_TURN:
        log_entry = f"{current_participant['name']} ends their turn."

    else:
        log_entry = f"{current_participant['name']} performs {action.action_type}."

    if action.notes:
        log_entry += f" {action.notes}"

    # Add to combat log
    combat.combat_log.append(log_entry)

    # Advance turn
    combat.current_turn += 1
    if combat.current_turn >= len(combat.participants):
        combat.current_turn = 0
        combat.round_number += 1
        combat.combat_log.append(f"--- Round {combat.round_number} begins ---")

    await db.commit()

    return CombatActionResponse(
        success=True,
        message="Action performed successfully",
        damage_dealt=damage_dealt,
        healing_done=healing_done,
        log_entry=log_entry,
    )


@router.post("/{combat_id}/end", response_model=EndCombatResponse)
async def end_combat(combat_id: UUID, db: AsyncSession = Depends(get_db)):
    """End a combat encounter

    Args:
        combat_id: Combat encounter UUID
        db: Database session

    Returns:
        Combat summary

    Raises:
        HTTPException: 404 if combat not found
    """
    result = await db.execute(select(CombatEncounter).where(CombatEncounter.id == combat_id))
    combat = result.scalar_one_or_none()

    if not combat:
        raise HTTPException(status_code=404, detail="Combat encounter not found")

    # Mark as ended
    combat.is_active = False
    ended_at = datetime.utcnow()
    combat.ended_at = ended_at

    # Calculate stats
    survived = sum(1 for p in combat.participants if p["hp_current"] > 0)
    defeated = len(combat.participants) - survived

    duration_seconds: float | None = None
    if combat.started_at is not None:
        duration_seconds = (ended_at - combat.started_at).total_seconds()

    combat.combat_log.append(f"Combat ended after {combat.round_number} rounds!")

    await db.commit()

    # Capture combat memory
    try:
        combatant_names = [p["name"] for p in combat.participants]
        player_survived = any(
            p["hp_current"] > 0 for p in combat.participants if not p.get("is_enemy", False)
        )
        outcome = "victory" if player_survived else "defeat"
        
        # Build combat summary
        details = f"Combat lasted {combat.round_number} rounds. "
        details += f"{survived} survived, {defeated} defeated. "
        details += "\n".join(combat.combat_log[-10:])  # Last 10 log entries
        
        await MemoryCaptureService.capture_combat_event(
            db=db,
            session_id=combat.session_id,
            combatant_names=combatant_names,
            outcome=outcome,
            details=details,
        )
        logger.info(f"Captured combat memory for session {combat.session_id}")
    except Exception as e:
        logger.warning(f"Failed to capture combat memory: {e}")

    return EndCombatResponse(
        combat_id=combat.id,
        total_rounds=combat.round_number,
        duration_seconds=duration_seconds,
        participants_survived=survived,
        participants_defeated=defeated,
        combat_log=combat.combat_log,
    )


@router.patch(
    "/{combat_id}/participants/{participant_index}/hp", response_model=CombatStatusResponse
)
async def update_participant_hp(
    combat_id: UUID, participant_index: int, hp_change: int, db: AsyncSession = Depends(get_db)
):
    """Update a participant's HP (damage or healing)

    Args:
        combat_id: Combat encounter UUID
        participant_index: Index of participant in list
        hp_change: HP change (negative for damage, positive for healing)
        db: Database session

    Returns:
        Updated combat status

    Raises:
        HTTPException: 404 if combat not found, 400 if invalid index
    """
    result = await db.execute(select(CombatEncounter).where(CombatEncounter.id == combat_id))
    combat = result.scalar_one_or_none()

    if not combat:
        raise HTTPException(status_code=404, detail="Combat encounter not found")

    if participant_index < 0 or participant_index >= len(combat.participants):
        raise HTTPException(status_code=400, detail="Invalid participant index")

    participant = combat.participants[participant_index]
    old_hp = participant["hp_current"]
    participant["hp_current"] = max(
        0, min(participant["hp_max"], participant["hp_current"] + hp_change)
    )
    new_hp = participant["hp_current"]

    combat.participants[participant_index] = participant

    if hp_change < 0:
        combat.combat_log.append(
            f"{participant['name']} takes {abs(hp_change)} damage! ({old_hp} → {new_hp} HP)"
        )
    else:
        combat.combat_log.append(
            f"{participant['name']} is healed for {hp_change} HP! ({old_hp} → {new_hp} HP)"
        )

    await db.commit()

    return CombatStatusResponse(
        combat_id=combat.id,
        session_id=combat.session_id,
        is_active=combat.is_active,
        current_turn=combat.current_turn,
        round_number=combat.round_number,
        participants=list(combat.participants),
        turn_order=combat.turn_order,
        combat_log=combat.combat_log,
        current_participant=combat.participants[combat.current_turn]
        if combat.participants
        else None,
    )
