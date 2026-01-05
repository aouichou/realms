"""Service for managing preset adventures"""

from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.preset_adventures import PresetAdventure, get_preset_adventure, list_preset_adventures
from app.db.models import Character, GameSession, Quest, QuestObjective, QuestState
from app.services.dm_engine import DMEngine


class AdventureService:
    """Service for loading and starting preset adventures"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dm_engine = DMEngine()

    async def get_available_adventures(self) -> List[Dict[str, Any]]:
        """Get list of all available preset adventures"""
        return list_preset_adventures()

    async def load_adventure(self, adventure_id: str) -> PresetAdventure | None:
        """Load a preset adventure by ID"""
        return get_preset_adventure(adventure_id)

    async def start_preset_adventure(self, character_id: UUID, adventure_id: str) -> Dict[str, Any]:
        """
        Start a preset adventure for a character.
        Creates a quest, game session, and returns the opening narration.
        """
        # Load the preset adventure
        adventure = get_preset_adventure(adventure_id)
        if not adventure:
            raise ValueError(f"Adventure {adventure_id} not found")

        # Get the character
        result = await self.db.execute(select(Character).where(Character.id == character_id))
        character = result.scalar_one_or_none()
        if not character:
            raise ValueError(f"Character {character_id} not found")

        # Create a new game session
        session = GameSession(
            character_id=character_id,
            setting=adventure.setting,
            initial_location=adventure.initial_location,
            is_active=True,
            chat_history=[],
        )
        self.db.add(session)
        await self.db.flush()

        # Create the quest
        quest = Quest(
            title=adventure.quest_data["title"],
            description=adventure.quest_data["description"],
            quest_giver_id=None,  # System-generated quest
            state=QuestState.NOT_STARTED,
            rewards=adventure.quest_data["rewards"],
        )
        self.db.add(quest)
        await self.db.flush()

        # Create quest objectives
        for obj_data in adventure.quest_data["objectives"]:
            objective = QuestObjective(
                quest_id=quest.id,
                description=obj_data["description"],
                order=obj_data["order"],
                is_completed=False,
            )
            self.db.add(objective)

        await self.db.commit()
        await self.db.refresh(session)
        await self.db.refresh(quest)

        # Return adventure info with opening narration
        return {
            "session_id": str(session.id),
            "quest_id": str(quest.id),
            "adventure_id": adventure.id,
            "title": adventure.title,
            "opening_narration": adventure.opening_narration,
            "setting": adventure.setting,
            "initial_location": adventure.initial_location,
            "combat_encounter_data": adventure.combat_encounter,
            "npcs": adventure.npcs,
        }

    async def get_adventure_context(self, session_id: UUID) -> Dict[str, Any]:
        """
        Get adventure context for an active session.
        Used by DM Engine for contextual narration.
        """
        # Get session
        result = await self.db.execute(select(GameSession).where(GameSession.id == session_id))
        session = result.scalar_one_or_none()

        if not session:
            return {}

        # Get character
        result = await self.db.execute(
            select(Character).where(Character.id == session.character_id)
        )
        character = result.scalar_one_or_none()

        # Get active quest for this character (if any)
        result = await self.db.execute(
            select(Quest)
            .join(Quest.character_quests)
            .where(
                Quest.character_quests.any(character_id=session.character_id),
                Quest.state.in_([QuestState.NOT_STARTED, QuestState.IN_PROGRESS]),
            )
        )
        active_quest = result.scalar_one_or_none()

        context = {
            "session_id": str(session.id),
            "setting": session.setting,
            "location": session.initial_location,
            "character_name": character.name if character else "Unknown",
            "character_class": character.character_class.value if character else "Unknown",
            "character_level": character.level if character else 1,
        }

        if active_quest:
            context["active_quest"] = {
                "title": active_quest.title,
                "description": active_quest.description,
                "state": active_quest.state.value,
            }

        return context
