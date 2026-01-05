"""
DM (Dungeon Master) Engine
Handles D&D narrative generation with focused storytelling
"""

from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional

from app.services.mistral_client import MistralAPIError, get_mistral_client
from app.utils.logger import logger


class DMEngine:
    """
    Dungeon Master Engine for D&D narrative generation
    Provides focused storytelling without conversational meta-commentary
    """

    # System prompt for focused D&D narration
    SYSTEM_PROMPT = """You are an expert Dungeon Master running a D&D 5th edition adventure.

CRITICAL INSTRUCTIONS:
- Narrate the story directly without meta-commentary or options
- Never say things like "Would you like...", "I can...", "Let me know if..."
- Focus on vivid descriptions, character actions, and consequences
- Include sensory details (sights, sounds, smells)
- React to player actions with immediate narrative consequences
- When combat occurs, describe it cinematically
- Maintain consistency with D&D 5e rules and lore
- Keep responses focused and immersive (100-200 words typically)

STORYTELLING STYLE:
- Present tense, second person ("You see...", "You feel...")
- Show, don't tell - use vivid imagery
- Create tension and atmosphere
- Balance description with action
- End with a clear situation requiring player response

NEVER include:
- Multiple choice options or suggestions
- Questions about what the player wants
- Explanations of what you can do as a DM
- Breaking the fourth wall
- Lists of possible actions"""

    def __init__(self):
        """Initialize DM Engine"""
        self.mistral_client = get_mistral_client()
        logger.info("DM Engine initialized")

    def _build_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        character_context: Optional[Dict] = None,
        game_state: Optional[Dict] = None,
    ) -> List[Dict[str, str]]:
        """
        Build message list for Mistral API with context

        Args:
            user_message: Current player action/message
            conversation_history: Previous messages
            character_context: Character information
            game_state: Current game state (location, inventory, etc.)

        Returns:
            List of formatted messages
        """
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

        # Add character context if available
        if character_context:
            context_msg = self._format_character_context(character_context)
            messages.append({"role": "system", "content": context_msg})

        # Add game state if available
        if game_state:
            state_msg = self._format_game_state(game_state)
            messages.append({"role": "system", "content": state_msg})

        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    def _format_character_context(self, character: Dict) -> str:
        """Format character information for context"""
        parts = ["CHARACTER CONTEXT:"]

        if character.get("name"):
            parts.append(f"Name: {character['name']}")
        if character.get("race"):
            parts.append(f"Race: {character['race']}")
        if character.get("class"):
            parts.append(f"Class: {character['class']}")
        if character.get("level"):
            parts.append(f"Level: {character['level']}")
        if character.get("background"):
            parts.append(f"Background: {character['background']}")

        return "\n".join(parts)

    def _format_game_state(self, state: Dict) -> str:
        """Format game state for context"""
        parts = ["CURRENT GAME STATE:"]

        if state.get("location"):
            parts.append(f"Location: {state['location']}")
        if state.get("time_of_day"):
            parts.append(f"Time: {state['time_of_day']}")
        if state.get("weather"):
            parts.append(f"Weather: {state['weather']}")
        if state.get("party_members"):
            parts.append(f"Party: {', '.join(state['party_members'])}")
        if state.get("active_quest"):
            parts.append(f"Quest: {state['active_quest']}")

        return "\n".join(parts)

    async def narrate(
        self,
        user_action: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        character_context: Optional[Dict] = None,
        game_state: Optional[Dict] = None,
    ) -> Dict:
        """
        Generate DM narration in response to player action

        Args:
            user_action: What the player wants to do
            conversation_history: Previous conversation
            character_context: Character information
            game_state: Current game state

        Returns:
            Dictionary with response and metadata

        Raises:
            MistralAPIError: If API call fails
        """
        try:
            messages = self._build_messages(
                user_action, conversation_history, character_context, game_state
            )

            logger.debug(f"Generating narration for action: {user_action[:50]}...")

            response = await self.mistral_client.chat_completion(messages)

            narration = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            logger.info(f"Narration generated: {tokens_used} tokens")

            return {
                "narration": narration,
                "tokens_used": tokens_used,
                "timestamp": datetime.now(),
                "model": self.mistral_client.model,
            }

        except MistralAPIError as e:
            logger.error(f"Failed to generate narration: {e}")
            raise

    async def narrate_stream(
        self,
        user_action: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        character_context: Optional[Dict] = None,
        game_state: Optional[Dict] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream DM narration in real-time

        Args:
            user_action: What the player wants to do
            conversation_history: Previous conversation
            character_context: Character information
            game_state: Current game state

        Yields:
            Narration text chunks

        Raises:
            MistralAPIError: If API call fails
        """
        try:
            messages = self._build_messages(
                user_action, conversation_history, character_context, game_state
            )

            logger.debug(f"Streaming narration for action: {user_action[:50]}...")

            async for chunk in self.mistral_client.chat_completion_stream(messages):
                yield chunk

            logger.info("Narration streaming completed")

        except MistralAPIError as e:
            logger.error(f"Failed to stream narration: {e}")
            raise

    async def start_adventure(
        self, setting: str = "classic fantasy dungeon", character_context: Optional[Dict] = None
    ) -> Dict:
        """
        Generate opening narration for a new adventure

        Args:
            setting: Adventure setting/theme
            character_context: Character information

        Returns:
            Dictionary with opening narration
        """
        opening_prompt = f"""Begin an exciting {setting} adventure.
Set the scene with vivid description and present an immediate hook or challenge.
The adventure should feel dangerous, mysterious, and full of possibility."""

        return await self.narrate(opening_prompt, character_context=character_context)

    async def start_adventure_stream(
        self, setting: str = "classic fantasy dungeon", character_context: Optional[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream opening narration for a new adventure

        Args:
            setting: Adventure setting/theme
            character_context: Character information

        Yields:
            Opening narration chunks
        """
        opening_prompt = f"""Begin an exciting {setting} adventure.
Set the scene with vivid description and present an immediate hook or challenge.
The adventure should feel dangerous, mysterious, and full of possibility."""

        async for chunk in self.narrate_stream(opening_prompt, character_context=character_context):
            yield chunk


# Global DM Engine instance
_dm_engine: Optional[DMEngine] = None


def get_dm_engine() -> DMEngine:
    """
    Get or create the global DM Engine instance

    Returns:
        DMEngine instance
    """
    global _dm_engine
    if _dm_engine is None:
        _dm_engine = DMEngine()
    return _dm_engine
