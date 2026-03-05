"""
NPC and companion management API endpoints
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Character, CharacterClass, CharacterRace, CharacterType, GameSession

router = APIRouter(prefix="/npcs", tags=["npcs"])


class NPCCreate(BaseModel):
    name: str
    race: str
    character_class: Optional[str] = None
    level: int = 1
    personality: Optional[str] = None
    background: Optional[str] = None
    # Stats
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    # Combat stats
    hp_max: int = 10
    armor_class: int = 10


class NPCResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    race: str
    character_class: Optional[str]
    level: int
    personality: Optional[str]
    background: Optional[str]
    hp_current: int
    hp_max: int


@router.post("/npcs")
async def create_npc(npc: NPCCreate, db: Session = Depends(get_db)):
    """
    Create a new NPC (companion, quest giver, or merchant)
    """
    # Validate race
    try:
        race_enum = CharacterRace(npc.race)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid race: {npc.race}. Must be one of: {', '.join([r.value for r in CharacterRace])}",
        )

    # Validate class if provided
    class_enum = None
    if npc.character_class:
        try:
            class_enum = CharacterClass(npc.character_class)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid class: {npc.character_class}. Must be one of: {', '.join([c.value for c in CharacterClass])}",
            )
    else:
        # Default to Commoner (use Fighter as placeholder)
        class_enum = CharacterClass.FIGHTER

    # Create NPC character
    character = Character(
        user_id=None,  # NPCs don't belong to users
        name=npc.name,
        character_type=CharacterType.NPC,
        character_class=class_enum,
        race=race_enum,
        level=npc.level,
        hp_current=npc.hp_max,
        hp_max=npc.hp_max,
        strength=npc.strength,
        dexterity=npc.dexterity,
        constitution=npc.constitution,
        intelligence=npc.intelligence,
        wisdom=npc.wisdom,
        charisma=npc.charisma,
        carrying_capacity=npc.strength * 15,
        personality=npc.personality,
        background=npc.background,
    )

    db.add(character)
    db.commit()
    db.refresh(character)

    return {
        "message": f"NPC {character.name} created",
        "npc": NPCResponse(
            id=str(character.id),
            name=character.name,
            race=character.race.value,
            character_class=character.character_class.value if character.character_class else None,
            level=character.level,
            personality=character.personality,
            background=character.background,
            hp_current=character.hp_current,
            hp_max=character.hp_max,
        ),
    }


@router.get("/npcs")
async def list_npcs(session_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    List all NPCs, optionally filtered by session
    For now, returns all NPCs since we don't have session-NPC relationships yet
    """
    npcs = db.query(Character).filter(Character.character_type == CharacterType.NPC).all()

    npc_list = [
        NPCResponse(
            id=str(npc.id),
            name=npc.name,
            race=npc.race.value,
            character_class=npc.character_class.value if npc.character_class else None,
            level=npc.level,
            personality=npc.personality,
            background=npc.background,
            hp_current=npc.hp_current,
            hp_max=npc.hp_max,
        )
        for npc in npcs
    ]

    return {"npcs": npc_list, "count": len(npc_list)}


@router.get("/npcs/{npc_id}")
async def get_npc(npc_id: str, db: Session = Depends(get_db)):
    """
    Get details of a specific NPC
    """
    npc = (
        db.query(Character)
        .filter(Character.id == npc_id, Character.character_type == CharacterType.NPC)
        .first()
    )

    if not npc:
        raise HTTPException(status_code=404, detail="NPC not found")

    return NPCResponse(
        id=str(npc.id),
        name=npc.name,
        race=npc.race.value,
        character_class=npc.character_class.value if npc.character_class else None,
        level=npc.level,
        personality=npc.personality,
        background=npc.background,
        hp_current=npc.hp_current,
        hp_max=npc.hp_max,
    )


@router.post("/sessions/{session_id}/add-companion")
async def add_companion(session_id: str, npc_id: str, db: Session = Depends(get_db)):
    """
    Add an NPC as a companion to a session
    Updates the session's companion_id
    """
    session = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    npc = (
        db.query(Character)
        .filter(Character.id == npc_id, Character.character_type == CharacterType.NPC)
        .first()
    )

    if not npc:
        raise HTTPException(status_code=404, detail="NPC not found")

    # Set as companion
    session.companion_id = npc.id
    db.commit()

    return {
        "message": f"{npc.name} has joined the party!",
        "session_id": str(session.id),
        "companion": NPCResponse(
            id=str(npc.id),
            name=npc.name,
            race=npc.race.value,
            character_class=npc.character_class.value if npc.character_class else None,
            level=npc.level,
            personality=npc.personality,
            background=npc.background,
            hp_current=npc.hp_current,
            hp_max=npc.hp_max,
        ),
    }


@router.get("/sessions/{session_id}/companions")
async def get_session_companions(session_id: str, db: Session = Depends(get_db)):
    """
    Get all companions for a session
    Currently only supports one companion per session
    """
    session = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    companions = []
    if session.companion_id:
        companion = db.query(Character).filter(Character.id == session.companion_id).first()
        if companion:
            companions.append(
                NPCResponse(
                    id=str(companion.id),
                    name=companion.name,
                    race=companion.race.value,
                    character_class=(
                        companion.character_class.value if companion.character_class else None
                    ),
                    level=companion.level,
                    personality=companion.personality,
                    background=companion.background,
                    hp_current=companion.hp_current,
                    hp_max=companion.hp_max,
                )
            )

    return {"session_id": str(session.id), "companions": companions, "count": len(companions)}


@router.delete("/sessions/{session_id}/companions/{npc_id}")
async def remove_companion(session_id: str, npc_id: str, db: Session = Depends(get_db)):
    """
    Remove a companion from a session
    """
    session = db.query(GameSession).filter(GameSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if str(session.companion_id) != npc_id:
        raise HTTPException(status_code=404, detail="NPC is not a companion in this session")

    npc_name = "Companion"
    if session.companion_id:
        companion = db.query(Character).filter(Character.id == session.companion_id).first()
        if companion:
            npc_name = companion.name

    session.companion_id = None
    db.commit()

    return {"message": f"{npc_name} has left the party", "session_id": str(session.id)}
