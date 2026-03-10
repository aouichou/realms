"""Quest tracking and management API"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import (
    Character,
    CharacterQuest,
    ItemType,
    Quest,
    QuestObjective,
    QuestState,
    User,
)
from app.middleware.auth import get_current_active_user

router = APIRouter(prefix="/quests", tags=["quests"])


# Pydantic schemas
class QuestObjectiveInput(BaseModel):
    """Quest objective input"""

    description: str = Field(..., min_length=1, max_length=500)
    order: int = Field(..., ge=0)


class QuestRewards(BaseModel):
    """Quest rewards"""

    xp: int = Field(default=0, ge=0)
    gold: int = Field(default=0, ge=0)
    items: list[str] = Field(default_factory=list)


class CreateQuestRequest(BaseModel):
    """Create quest request"""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=2000)
    quest_giver_id: Optional[UUID] = None
    rewards: QuestRewards
    objectives: list[QuestObjectiveInput] = Field(..., min_length=1)


class QuestObjectiveResponse(BaseModel):
    """Quest objective response"""

    id: UUID
    description: str
    order: int
    is_completed: bool


class QuestResponse(BaseModel):
    """Quest response"""

    id: UUID
    title: str
    description: str
    state: QuestState
    quest_giver_id: Optional[UUID]
    quest_giver_name: Optional[str]
    rewards: dict
    objectives: list[QuestObjectiveResponse]
    progress: str  # e.g., "2/5 objectives"
    created_at: datetime
    updated_at: datetime


class AcceptQuestRequest(BaseModel):
    """Accept quest request"""

    character_id: UUID


@router.post("", response_model=QuestResponse)
def create_quest(
    request: CreateQuestRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new quest with objectives"""
    # Verify quest giver exists if provided
    if request.quest_giver_id:
        quest_giver = db.query(Character).filter(Character.id == request.quest_giver_id).first()
        if not quest_giver:
            raise HTTPException(status_code=404, detail="Quest giver not found")
        if quest_giver.type != "NPC":
            raise HTTPException(status_code=400, detail="Quest giver must be an NPC")

    # Create quest
    quest = Quest(
        title=request.title,
        description=request.description,
        quest_giver_id=request.quest_giver_id,
        rewards=request.rewards.model_dump(),
        state=QuestState.NOT_STARTED,
    )
    db.add(quest)
    db.flush()  # Get quest ID

    # Create objectives
    for obj_input in request.objectives:
        objective = QuestObjective(
            quest_id=quest.id,
            description=obj_input.description,
            order=obj_input.order,
            is_completed=False,
        )
        db.add(objective)

    db.commit()
    db.refresh(quest)

    # Build response
    quest_giver_name = None
    if quest.quest_giver_id:
        giver = db.query(Character).filter(Character.id == quest.quest_giver_id).first()
        quest_giver_name = giver.name if giver else None

    objectives = (
        db.query(QuestObjective)
        .filter(QuestObjective.quest_id == quest.id)
        .order_by(QuestObjective.order)
        .all()
    )

    completed_count = sum(1 for obj in objectives if obj.is_completed)
    total_count = len(objectives)

    return QuestResponse(
        id=quest.id,
        title=quest.title,
        description=quest.description,
        state=quest.state,
        quest_giver_id=quest.quest_giver_id,
        quest_giver_name=quest_giver_name,
        rewards=quest.rewards,
        objectives=[
            QuestObjectiveResponse(
                id=obj.id,
                description=obj.description,
                order=obj.order,
                is_completed=obj.is_completed,
            )
            for obj in objectives
        ],
        progress=f"{completed_count}/{total_count} objectives",
        created_at=quest.created_at,
        updated_at=quest.updated_at,
    )


@router.post("/{quest_id}/accept", response_model=dict)
def accept_quest(
    quest_id: UUID,
    request: AcceptQuestRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Accept a quest for a character"""
    # Verify quest exists
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    # Verify character exists
    character = db.query(Character).filter(Character.id == request.character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Check if already accepted
    existing = (
        db.query(CharacterQuest)
        .filter(
            CharacterQuest.character_id == request.character_id, CharacterQuest.quest_id == quest_id
        )
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail="Quest already accepted by this character")

    # Accept quest
    character_quest = CharacterQuest(character_id=request.character_id, quest_id=quest_id)
    db.add(character_quest)

    # Update quest state to in_progress if not started
    if quest.state == QuestState.NOT_STARTED:
        quest.state = QuestState.IN_PROGRESS

    db.commit()

    return {"message": "Quest accepted", "quest_id": quest_id, "character_id": request.character_id}


@router.get("/character/{character_id}", response_model=list[QuestResponse])
def get_character_quests(
    character_id: UUID,
    state: Optional[QuestState] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all quests for a character, optionally filtered by state"""
    # Verify character exists
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Query character quests
    query = (
        db.query(Quest)
        .join(CharacterQuest, CharacterQuest.quest_id == Quest.id)
        .filter(CharacterQuest.character_id == character_id)
    )

    if state:
        query = query.filter(Quest.state == state)

    quests = query.order_by(Quest.created_at.desc()).all()

    # Build responses
    responses = []
    for quest in quests:
        quest_giver_name = None
        if quest.quest_giver_id:
            giver = db.query(Character).filter(Character.id == quest.quest_giver_id).first()
            quest_giver_name = giver.name if giver else None

        objectives = (
            db.query(QuestObjective)
            .filter(QuestObjective.quest_id == quest.id)
            .order_by(QuestObjective.order)
            .all()
        )

        completed_count = sum(1 for obj in objectives if obj.is_completed)
        total_count = len(objectives)

        responses.append(
            QuestResponse(
                id=quest.id,
                title=quest.title,
                description=quest.description,
                state=quest.state,
                quest_giver_id=quest.quest_giver_id,
                quest_giver_name=quest_giver_name,
                rewards=quest.rewards,
                objectives=[
                    QuestObjectiveResponse(
                        id=obj.id,
                        description=obj.description,
                        order=obj.order,
                        is_completed=obj.is_completed,
                    )
                    for obj in objectives
                ],
                progress=f"{completed_count}/{total_count} objectives",
                created_at=quest.created_at,
                updated_at=quest.updated_at,
            )
        )

    return responses


@router.patch("/{quest_id}/objectives/{objective_id}/complete", response_model=dict)
def complete_objective(
    quest_id: UUID,
    objective_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark a quest objective as complete"""
    # Verify quest exists
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    # Verify objective exists and belongs to quest
    objective = (
        db.query(QuestObjective)
        .filter(QuestObjective.id == objective_id, QuestObjective.quest_id == quest_id)
        .first()
    )

    if not objective:
        raise HTTPException(status_code=404, detail="Objective not found")

    if objective.is_completed:
        raise HTTPException(status_code=400, detail="Objective already completed")

    # Mark objective complete
    objective.is_completed = True

    # Check if all objectives are complete
    all_objectives = db.query(QuestObjective).filter(QuestObjective.quest_id == quest_id).all()

    all_complete = all(obj.is_completed for obj in all_objectives)

    db.commit()

    return {
        "message": "Objective completed",
        "objective_id": objective_id,
        "all_objectives_complete": all_complete,
    }


@router.post("/{quest_id}/complete", response_model=dict)
def complete_quest(
    quest_id: UUID,
    character_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark quest as complete and grant rewards"""
    # Verify quest exists
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    # Verify character has quest
    character_quest = (
        db.query(CharacterQuest)
        .filter(CharacterQuest.quest_id == quest_id, CharacterQuest.character_id == character_id)
        .first()
    )

    if not character_quest:
        raise HTTPException(status_code=404, detail="Character does not have this quest")

    # Verify character exists
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Check if already completed
    if quest.state == QuestState.COMPLETED:
        raise HTTPException(status_code=400, detail="Quest already completed")

    # Grant rewards
    rewards = quest.rewards
    rewards_granted = []

    # XP reward
    if rewards.get("xp", 0) > 0:
        character.experience_points += rewards["xp"]
        rewards_granted.append(f"{rewards['xp']} XP")

    # Gold reward
    if rewards.get("gold", 0) > 0:
        # Add gold directly to character
        character.gold += rewards["gold"]
        rewards_granted.append(f"{rewards['gold']} gold")

    # Item rewards
    if rewards.get("items"):
        from app.db.models import Item

        for item_name in rewards["items"]:
            item = Item(
                character_id=character_id,
                name=item_name,
                item_type=ItemType.QUEST,
                quantity=1,
                weight=0.0,
                value=0,
                properties={"description": f"Reward from quest: {quest.title}"},
            )
            db.add(item)
            rewards_granted.append(item_name)

    # Mark quest complete
    quest.state = QuestState.COMPLETED

    db.commit()

    return {"message": "Quest completed!", "quest_id": quest_id, "rewards_granted": rewards_granted}


@router.post("/{quest_id}/fail", response_model=dict)
def fail_quest(
    quest_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark quest as failed"""
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    if quest.state in [QuestState.COMPLETED, QuestState.FAILED]:
        raise HTTPException(status_code=400, detail=f"Quest already {quest.state.value}")

    quest.state = QuestState.FAILED
    db.commit()

    return {"message": "Quest failed", "quest_id": quest_id}
