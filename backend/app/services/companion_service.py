"""
Companion AI service for generating companion NPC responses.
Uses Google Gemini to provide distinct personality from DM.
"""

import logging
import random
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.character import Character
from app.db.models.companion import Companion
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class CompanionService:
    """
    AI service for companion NPCs.

    Handles companion personality, decision-making, and responses
    using Google Gemini (separate from DM's Mistral).
    """

    def __init__(self, gemini_service: GeminiService):
        """
        Initialize companion AI service.

        Args:
            gemini_service: Configured GeminiService instance
        """
        self.gemini_service = gemini_service
        logger.info("CompanionService initialized with Google Gemini")

    async def generate_companion_response(
        self,
        companion: Companion,
        player_action: str,
        dm_narration: str,
        recent_context: list[dict[str, Any]],
        character: Character,
    ) -> str:
        """
        Generate companion's response to current situation.

        Args:
            companion: Companion model instance
            player_action: Player's recent action/message
            dm_narration: DM's recent narration
            recent_context: Recent conversation messages for context
            character: Player character for relationship context

        Returns:
            Companion's response as text
        """
        logger.info(f"Generating response for companion '{companion.name}'")

        # Build companion personality prompt
        prompt = self._build_companion_prompt(
            companion=companion,
            player_action=player_action,
            dm_narration=dm_narration,
            recent_context=recent_context,
            character=character,
        )

        try:
            # Generate response using Gemini
            response = await self.gemini_service.generate_narration(
                prompt=prompt,
                max_tokens=500,
                temperature=0.8,
            )

            # Add to companion's conversation memory
            companion.add_conversation_memory("dm", dm_narration)
            companion.add_conversation_memory("player", player_action)
            companion.add_conversation_memory("companion", response)

            logger.info(f"Companion '{companion.name}' responded: {response[:100]}...")
            return response

        except Exception as e:
            logger.error(f"Failed to generate companion response: {e}")
            return self._get_fallback_response(companion)

    def _build_companion_prompt(
        self,
        companion: Companion,
        player_action: str,
        dm_narration: str,
        recent_context: list[dict[str, Any]],
        character: Character,
    ) -> str:
        """Build the prompt for companion AI."""
        str_mod = companion.get_stat_modifier(companion.strength)
        dex_mod = companion.get_stat_modifier(companion.dexterity)
        int_mod = companion.get_stat_modifier(companion.intelligence)
        wis_mod = companion.get_stat_modifier(companion.wisdom)
        cha_mod = companion.get_stat_modifier(companion.charisma)

        abilities_desc = []
        if str_mod >= 3:
            abilities_desc.append("very strong")
        if dex_mod >= 3:
            abilities_desc.append("very agile")
        if int_mod >= 3:
            abilities_desc.append("highly intelligent")
        if wis_mod >= 3:
            abilities_desc.append("very wise")
        if cha_mod >= 3:
            abilities_desc.append("very charismatic")

        abilities_text = ", ".join(abilities_desc) if abilities_desc else "of average abilities"

        context_text = ""
        if recent_context:
            recent_messages = recent_context[-10:]
            context_lines = []
            for msg in recent_messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:200]
                if role == "assistant":
                    context_lines.append(f"DM: {content}")
                elif role == "user":
                    context_lines.append(f"{character.name}: {content}")
            context_text = "\n".join(context_lines)

        prompt = f"""You are {companion.name}, a {companion.creature_name} companion.

**YOUR PERSONALITY:**
{companion.personality}

**YOUR GOALS:**
{companion.goals or "To assist your companion on their journey"}

**YOUR BACKGROUND:**
{companion.background or f"A {companion.creature_name} who has joined the party"}

**YOUR ABILITIES:**
You are {abilities_text}.
- Current HP: {companion.hp}/{companion.max_hp}
- Armor Class: {companion.ac}

**YOUR RELATIONSHIP WITH {character.name}:**
Status: {companion.relationship_status.replace("_", " ").title()}
Loyalty: {companion.loyalty}/100

**RECENT CONVERSATION:**
{context_text if context_text else "(No recent context)"}

**CURRENT SITUATION:**
DM narration: {dm_narration}

{character.name}'s action: {player_action}

**YOUR RESPONSE:**
Respond in character as {companion.name}. Your response should:
- Reflect your personality ({companion.personality})
- Consider your relationship with {character.name} (currently {companion.relationship_status})
- Be aware of your current state (HP: {companion.hp}/{companion.max_hp})
- Stay true to your goals: {companion.goals or "helping your companion"}
- Be 1-3 sentences, natural and conversational
- DO NOT narrate the scene - only speak as yourself
- DO NOT speak for {character.name} or describe their actions

Speak now as {companion.name}:"""

        return prompt

    def _get_fallback_response(self, companion: Companion) -> str:
        """Generate a fallback response if AI generation fails."""
        personality_lower = companion.personality.lower()

        if "brave" in personality_lower or "bold" in personality_lower:
            return f"{companion.name} nods firmly, ready for whatever comes next."
        elif "cautious" in personality_lower or "careful" in personality_lower:
            return f"{companion.name} looks around warily, staying alert."
        elif "friendly" in personality_lower or "loyal" in personality_lower:
            return f"{companion.name} stays close, offering a reassuring presence."
        elif "curious" in personality_lower:
            return f"{companion.name} watches with keen interest."
        else:
            return f"{companion.name} remains at your side."

    async def should_companion_respond(
        self,
        companion: Companion,
        player_action: str,
        dm_narration: str,
        combat_active: bool = False,
    ) -> bool:
        """Determine if companion should speak in current situation."""
        companion_name_lower = companion.name.lower()
        player_action_lower = player_action.lower()
        dm_narration_lower = dm_narration.lower()

        if combat_active and f"{companion_name_lower}'s turn" in dm_narration_lower:
            return True

        if companion_name_lower in player_action_lower:
            return True

        opinion_keywords = [
            "what do you think",
            "your opinion",
            "companion",
            "what should we",
            "any ideas",
        ]
        if any(keyword in player_action_lower for keyword in opinion_keywords):
            return True

        if companion_name_lower in dm_narration_lower:
            return True

        if random.random() < 0.1:
            return True

        return False

    async def update_companion_loyalty(
        self,
        companion: Companion,
        event_description: str,
        loyalty_change: int,
        db: AsyncSession,
    ) -> None:
        """Update companion loyalty based on player actions."""
        old_loyalty = companion.loyalty
        companion.loyalty = max(0, min(100, companion.loyalty + loyalty_change))

        if companion.loyalty >= 80:
            companion.relationship_status = "trusted"
        elif companion.loyalty >= 60:
            companion.relationship_status = "friend"
        elif companion.loyalty >= 40:
            companion.relationship_status = "ally"
        elif companion.loyalty >= 20:
            companion.relationship_status = "suspicious"
        else:
            companion.relationship_status = "just_met"

        companion.add_important_event(
            f"Loyalty changed from {old_loyalty} to {companion.loyalty}: {event_description}"
        )

        await db.commit()

        logger.info(
            f"Companion '{companion.name}' loyalty: {old_loyalty} -> {companion.loyalty} ({companion.relationship_status})"
        )
