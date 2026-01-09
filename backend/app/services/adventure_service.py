"""Service for managing preset and custom adventures"""

import json
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.preset_adventures import PresetAdventure, get_preset_adventure, list_preset_adventures
from app.db.models import Adventure, Character, GameSession, Quest, QuestObjective, QuestState
from app.observability.logger import get_logger
from app.services.dm_engine import DMEngine
from app.services.mistral_client import get_mistral_client

logger = get_logger(__name__)


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

    # Custom Adventure Generation
    # Setting descriptions
    SETTINGS = {
        "haunted_castle": "a cursed fortress filled with undead and dark magic",
        "ancient_ruins": "forgotten temples and lost civilizations",
        "dark_forest": "twisted woods teeming with monsters and ancient spirits",
        "underground_dungeon": "dangerous caverns and hidden chambers",
        "pirate_port": "treacherous waters and lawless harbors",
        "desert_oasis": "harsh sands and ancient desert secrets",
        "mountain_peak": "treacherous heights and legendary summits",
        "mystical_academy": "a school of sorcery with magical mysteries",
    }

    # Goal descriptions
    GOALS = {
        "rescue_mission": "rescue someone important from imminent danger",
        "find_artifact": "locate a powerful magical artifact",
        "defeat_villain": "stop an evil force threatening the realm",
        "solve_mystery": "uncover the truth behind strange supernatural events",
        "treasure_hunt": "find legendary riches and ancient fortune",
        "diplomatic_mission": "negotiate peace or forge crucial alliances",
        "exploration": "discover uncharted territories and hidden places",
        "survival": "endure and overcome overwhelming odds",
    }

    # Tone descriptions
    TONES = {
        "epic_heroic": "epic and heroic with grand stakes and legendary heroes",
        "dark_gritty": "dark and gritty with mature themes and moral ambiguity",
        "lighthearted": "lighthearted and humorous with fun adventures",
        "horror": "horror-themed with terrifying encounters and dread",
        "mystery": "mystery-focused with intrigue and investigation",
    }

    async def generate_custom_adventure(
        self,
        character_id: UUID,
        setting: str,
        goal: str,
        tone: str,
    ) -> Adventure:
        """
        Generate a custom adventure using AI based on player choices.

        Args:
            character_id: ID of the character
            setting: Adventure setting ID
            goal: Adventure goal ID
            tone: Adventure tone ID

        Returns:
            Adventure object with generated scenes
        """
        # Get the character
        result = await self.db.execute(select(Character).where(Character.id == character_id))
        character = result.scalar_one_or_none()
        if not character:
            raise ValueError(f"Character {character_id} not found")

        # Get descriptions
        setting_desc = self.SETTINGS.get(setting, "an unknown location")
        goal_desc = self.GOALS.get(goal, "complete an objective")
        tone_desc = self.TONES.get(tone, "balanced")

        # Build AI prompt
        prompt = self._build_adventure_prompt(setting_desc, goal_desc, tone_desc, character.level)

        try:
            # Call Mistral API
            client = get_mistral_client()
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert D&D Dungeon Master who creates engaging, balanced adventures.",
                },
                {"role": "user", "content": prompt},
            ]

            response = await client.chat_completion(
                messages=messages, temperature=0.8, max_tokens=2000
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from AI")

            # Parse the AI response
            adventure_data = self._parse_adventure_response(str(content), setting, goal, tone)

            # Create Adventure in database
            adventure = Adventure(
                character_id=character_id,
                setting=setting,
                goal=goal,
                tone=tone,
                title=adventure_data["title"],
                description=adventure_data["description"],
                scenes=adventure_data["scenes"],
                is_completed=False,
            )
            self.db.add(adventure)
            await self.db.commit()
            await self.db.refresh(adventure)

            logger.info(f"Generated adventure: {adventure.title} for character {character_id}")
            return adventure

        except Exception as e:
            logger.error(f"Error generating adventure: {e}")
            raise

    def _build_adventure_prompt(self, setting: str, goal: str, tone: str, level: int) -> str:
        """Build the prompt for adventure generation"""
        return f"""Create a D&D 5e adventure with the following parameters:

**Setting**: {setting}
**Goal**: {goal}
**Tone**: {tone}
**Character Level**: {level}

Generate a complete adventure with:
1. **Title**: A compelling adventure title
2. **Description**: A 2-3 paragraph overview
3. **Scenes**: 3-5 structured scenes with:
   - Scene number and title
   - Scene description (2-3 sentences)
   - Encounters (2-3 combat/skill challenges)
   - NPCs (name, race, role, personality)
   - Loot (items, gold)

Format your response as JSON:
{{
  "title": "Adventure Title",
  "description": "Full adventure description",
  "scenes": [
    {{
      "scene_number": 1,
      "title": "Scene Title",
      "description": "Scene description",
      "encounters": ["Encounter 1", "Encounter 2"],
      "npcs": [
        {{
          "name": "NPC Name",
          "race": "NPC Race",
          "role": "NPC Role",
          "personality": "Brief personality"
        }}
      ],
      "loot": [
        {{
          "item": "Item Name",
          "description": "Item description",
          "value": 100
        }}
      ]
    }}
  ]
}}

Make encounters appropriate for level {level} characters. Include specific D&D 5e creatures, DCs, and mechanics.
"""

    def _parse_adventure_response(
        self, response: str, setting: str, goal: str, tone: str
    ) -> Dict[str, Any]:
        """
        Parse the AI response into structured adventure data.

        Args:
            response: Raw AI response
            setting: Setting ID
            goal: Goal ID
            tone: Tone ID

        Returns:
            Structured adventure dictionary
        """
        try:
            # Try to extract JSON from the response
            # AI might wrap it in markdown code blocks
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()

            # Parse JSON
            data = json.loads(json_str)

            # Validate required fields
            if "title" not in data or "description" not in data or "scenes" not in data:
                raise ValueError("Missing required fields in adventure data")

            # Ensure proper structure
            adventure = {
                "title": data["title"],
                "description": data["description"],
                "scenes": [],
            }

            # Process each scene
            for scene in data.get("scenes", []):
                processed_scene = {
                    "scene_number": scene.get("scene_number", 1),
                    "title": scene.get("title", "Untitled Scene"),
                    "description": scene.get("description", ""),
                    "encounters": scene.get("encounters", []),
                    "npcs": scene.get("npcs", []),
                    "loot": scene.get("loot", []),
                }
                adventure["scenes"].append(processed_scene)

            return adventure

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse adventure JSON: {e}")
            logger.error(f"Response was: {response}")
            # Return a fallback adventure
            return self._create_fallback_adventure(setting, goal, tone)
        except Exception as e:
            logger.error(f"Error parsing adventure: {e}")
            return self._create_fallback_adventure(setting, goal, tone)

    def _create_fallback_adventure(self, setting: str, goal: str, tone: str) -> Dict[str, Any]:
        """Create a basic fallback adventure if AI generation fails"""
        setting_name = setting.replace("_", " ").title()
        goal_name = goal.replace("_", " ").title()

        return {
            "title": f"The {setting_name} Quest",
            "description": f"A {tone.replace('_', ' ')} adventure to {goal_name.lower()} in {setting_name.lower()}. Your journey begins now.",
            "scenes": [
                {
                    "scene_number": 1,
                    "title": "The Beginning",
                    "description": "Your adventure starts here.",
                    "encounters": ["Initial Challenge"],
                    "npcs": [
                        {
                            "name": "Guide",
                            "race": "Human",
                            "role": "Quest Giver",
                            "personality": "Helpful",
                        }
                    ],
                    "loot": [
                        {
                            "item": "Starting Equipment",
                            "description": "Basic gear",
                            "value": 10,
                        }
                    ],
                },
                {
                    "scene_number": 2,
                    "title": "The Challenge",
                    "description": "Face the main obstacle.",
                    "encounters": ["Primary Conflict"],
                    "npcs": [],
                    "loot": [{"item": "Reward", "description": "Quest reward", "value": 100}],
                },
                {
                    "scene_number": 3,
                    "title": "The Resolution",
                    "description": "Complete your goal.",
                    "encounters": ["Final Confrontation"],
                    "npcs": [],
                    "loot": [{"item": "Treasure", "description": "Final treasure", "value": 200}],
                },
            ],
        }

    async def get_adventure(self, adventure_id: UUID) -> Adventure | None:
        """Get a custom adventure by ID"""
        result = await self.db.execute(select(Adventure).where(Adventure.id == adventure_id))
        return result.scalar_one_or_none()

    async def start_custom_adventure(
        self, character_id: UUID, adventure_id: UUID
    ) -> Dict[str, Any]:
        """
        Start a custom AI-generated adventure for a character.
        Creates a game session and returns opening narration based on the first scene.
        """
        # Get the custom adventure
        adventure = await self.get_adventure(adventure_id)
        if not adventure:
            raise ValueError(f"Adventure {adventure_id} not found")

        # Verify adventure belongs to this character
        if adventure.character_id != character_id:
            raise ValueError("Adventure does not belong to this character")

        # Get the character
        result = await self.db.execute(select(Character).where(Character.id == character_id))
        character = result.scalar_one_or_none()
        if not character:
            raise ValueError(f"Character {character_id} not found")

        # Get the first scene for opening narration
        scenes = adventure.scenes
        first_scene = scenes[0] if scenes and len(scenes) > 0 else None

        # Create opening narration from first scene or use default
        if first_scene:
            opening_narration = (
                f"**{adventure.title}**\n\n"
                f"{adventure.description}\n\n"
                f"**Scene 1: {first_scene.get('title', 'The Beginning')}**\n\n"
                f"{first_scene.get('description', 'Your adventure begins...')}"
            )
            initial_location = first_scene.get("title", "Starting Location")
        else:
            opening_narration = (
                f"**{adventure.title}**\n\n{adventure.description}\n\nYour adventure begins!"
            )
            initial_location = "Starting Location"

        # Create a new game session
        session = GameSession(
            character_id=character_id,
            current_location=initial_location,
            is_active=True,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        # Return adventure info with opening narration
        return {
            "session_id": str(session.id),
            "quest_id": None,  # Custom adventures don't have preset quests
            "adventure_id": str(adventure.id),
            "title": adventure.title,
            "opening_narration": opening_narration,
            "setting": adventure.setting,
            "initial_location": initial_location,
        }
