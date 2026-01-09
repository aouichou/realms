"""
DM (Dungeon Master) Engine
Handles D&D narrative generation with focused storytelling in multiple languages
"""

from datetime import datetime
from typing import AsyncGenerator, Dict, List, Optional

from app.i18n import translate
from app.services.mistral_client import MistralAPIError, get_mistral_client
from app.utils.logger import logger


class DMEngine:
    """
    Dungeon Master Engine for D&D narrative generation
    Provides focused storytelling without conversational meta-commentary
    Supports English and French narration
    """

    # System prompt templates by language
    SYSTEM_PROMPTS = {
        "en": """You are an expert Dungeon Master running a D&D 5th edition adventure.

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
- Lists of possible actions

DICE ROLLS - IMPORTANT:
When player actions require dice rolls, embed roll tags in your narration using these EXACT formats:

Attack Rolls:
- [ROLL:attack:d20+5] for attack with modifier
- Example: "You swing your sword [ROLL:attack:d20+4] at the goblin."

Saving Throws:
- [ROLL:save:dex:DC15] for DEX save vs DC 15
- [ROLL:save:wis:DC13] for WIS save vs DC 13
- Example: "A burst of flame erupts! [ROLL:save:dex:DC15]"

Ability Checks:
- [ROLL:check:perception:DC12] for Perception check
- [ROLL:check:stealth:DC10] for Stealth check
- Example: "You try to spot traps [ROLL:check:perception:DC15]."

Damage Rolls:
- [ROLL:damage:2d6+3] after successful attacks
- Example: "Your blade strikes true! [ROLL:damage:1d8+3]"

Initiative:
- [ROLL:initiative:d20+2] when combat begins

The rolls execute automatically and results are injected back. DO NOT wait or ask - just continue narration. Keep roll tags natural in the story flow.

SPELL SLOTS - RESOURCE MANAGEMENT:
You will receive the character's current spell slots in the context. BE AWARE of spell resource management:

When character info includes spell_slots:
- Track which spell levels are available
- Mention when running low: "You feel your magical reserves waning" (1-2 slots left)
- Subtly encourage resource management: "This might be your last big spell"
- Never allow impossible casts - if no slots, narrate failure: "You reach for the magic, but nothing comes"
- Remind of rest benefits: "A short rest would restore some power" (for warlocks) or "Only a long rest can restore your full might"

Spell Slot Awareness Examples:
- "You have 2 level-3 slots remaining - use them wisely"
- "Your last level-1 slot flickers as you cast"
- "The magic flows freely - you're still fresh with 4 slots at each level"
- If out of slots: "You try to weave the spell, but your magical energy is spent. You'll need rest."

Always respect D&D 5e spell slot rules. Don't let players cast without resources.

QUEST COMPLETION:
When the player has completed all objectives of their current quest, recognize this moment and celebrate their success.
Include this EXACT tag to trigger reward distribution:
[QUEST_COMPLETE: quest_id="<quest_id>"]

You will be told the quest_id in the character context. After completing a quest, narrate the victory and what comes next.""",
        "fr": """Vous êtes un Maître du Donjon expert menant une aventure de D&D 5ème édition.

INSTRUCTIONS CRITIQUES:
- Racontez l'histoire directement sans méta-commentaires ni options
- Ne dites jamais "Voulez-vous...", "Je peux...", "Faites-moi savoir si..."
- Concentrez-vous sur les descriptions vives, les actions des personnages et les conséquences
- Incluez des détails sensoriels (vues, sons, odeurs)
- Réagissez aux actions du joueur avec des conséquences narratives immédiates
- Lorsque le combat se produit, décrivez-le de manière cinématographique
- Maintenez la cohérence avec les règles et la tradition de D&D 5e
- Gardez les réponses concentrées et immersives (100-200 mots typiquement)

STYLE NARRATIF:
- Présent, deuxième personne ("Vous voyez...", "Vous ressentez...")
- Montrez, ne dites pas - utilisez des images vives
- Créez de la tension et de l'atmosphère
- Équilibrez description et action
- Terminez par une situation claire nécessitant une réponse du joueur

N'INCLUEZ JAMAIS:
- Options à choix multiples ou suggestions
- Questions sur ce que le joueur veut
- Explications de ce que vous pouvez faire en tant que MJ
- Briser le quatrième mur
- Listes d'actions possibles

JETS DE DÉS - IMPORTANT:
Lorsque les actions du joueur nécessitent des jets de dés, intégrez des balises de jet dans votre narration en utilisant ces formats EXACTS:

Jets d'attaque:
- [ROLL:attack:d20+5] pour attaque avec modificateur
- Exemple: "Vous balancez votre épée [ROLL:attack:d20+4] contre le gobelin."

Jets de sauvegarde:
- [ROLL:save:dex:DC15] pour jet de DEX contre DD 15
- [ROLL:save:wis:DC13] for jet de SAG contre DD 13
- Exemple: "Une explosion de flammes éclate! [ROLL:save:dex:DC15]"

Tests de caractéristique:
- [ROLL:check:perception:DC12] pour test de Perception
- [ROLL:check:stealth:DC10] pour test de Discrétion
- Exemple: "Vous essayez de repérer des pièges [ROLL:check:perception:DC15]."

Jets de dégâts:
- [ROLL:damage:2d6+3] après attaques réussies
- Exemple: "Votre lame frappe juste! [ROLL:damage:1d8+3]"

Initiative:
- [ROLL:initiative:d20+2] quand le combat commence

Les jets s'exécutent automatiquement et les résultats sont réinjectés. N'attendez PAS - continuez simplement la narration.

EMPLACEMENTS DE SORTS - GESTION DES RESSOURCES:
Vous recevrez les emplacements de sorts actuels du personnage. SOYEZ CONSCIENT de la gestion des ressources magiques:

Lorsque les informations du personnage incluent spell_slots:
- Suivez quels niveaux de sorts sont disponibles
- Mentionnez quand les ressources s'épuisent: "Vous sentez vos réserves magiques s'amenuiser" (1-2 emplacements restants)
- Encouragez subtilement la gestion: "Ce pourrait être votre dernier grand sort"
- N'autorisez jamais de lancers impossibles - sans emplacement, racontez l'échec: "Vous cherchez la magie, mais rien ne vient"
- Rappelez les avantages du repos: "Un repos court restaurerait un peu de pouvoir" (pour les occultistes) ou "Seul un repos long peut restaurer toute votre puissance"

Exemples de conscience des emplacements:
- "Il vous reste 2 emplacements de niveau 3 - utilisez-les judicieusement"
- "Votre dernier emplacement de niveau 1 vacille alors que vous lancez"
- "La magie coule librement - vous êtes encore frais avec 4 emplacements à chaque niveau"
- Si plus d'emplacements: "Vous essayez de tisser le sort, mais votre énergie magique est épuisée. Vous aurez besoin de repos."

Respectez toujours les règles d'emplacements de sorts de D&D 5e.

ACHÈVEMENT DE QUÊTE:
Lorsque le joueur a terminé tous les objectifs de sa quête actuelle, reconnaissez ce moment et célébrez son succès.
Incluez cette balise EXACTE pour déclencher la distribution des récompenses:
[QUEST_COMPLETE: quest_id="<quest_id>"]

L'identifiant de quête vous sera fourni dans le contexte du personnage. Après avoir terminé une quête, racontez la victoire et ce qui vient ensuite.""",
    }

    def __init__(self):
        """Initialize DM Engine"""
        self.mistral_client = get_mistral_client()
        logger.info("DM Engine initialized with multilingual support")

    def get_system_prompt(self, language: str = "en") -> str:
        """
        Get system prompt in the specified language

        Args:
            language: Language code ("en" or "fr")

        Returns:
            System prompt in the requested language
        """
        return self.SYSTEM_PROMPTS.get(language, self.SYSTEM_PROMPTS["en"])

    @staticmethod
    def extract_roll_request(response_text: str) -> tuple[str, Optional[Dict]]:
        """Extract roll request from DM response if present.

        Returns:
            Tuple of (cleaned_text, roll_request_dict or None)
        """
        import re

        pattern = r"\[ROLL_REQUEST:\s*([^\]]+)\]"
        match = re.search(pattern, response_text)

        if not match:
            return response_text, None

        # Extract the roll request parameters
        params_str = match.group(1)
        roll_request = {}

        # Parse key="value" or key=value patterns
        param_pattern = r'(\w+)="?([^,"\\]]+)"?'
        for param_match in re.finditer(param_pattern, params_str):
            key = param_match.group(1).strip()
            value = param_match.group(2).strip()

            # Convert numeric values
            if value.isdigit():
                value = int(value)

            roll_request[key] = value

        # Remove the roll request tag from the narrative
        cleaned_text = re.sub(pattern, "", response_text).strip()

        return cleaned_text, roll_request

    @staticmethod
    def extract_quest_complete(response_text: str) -> tuple[str, Optional[str]]:
        """Extract quest complete notification from DM response if present.

        Returns:
            Tuple of (cleaned_text, quest_id or None)
        """
        import re

        pattern = r'\[QUEST_COMPLETE:\s*quest_id="?([^"\\]]+)"?\]'
        match = re.search(pattern, response_text)

        if not match:
            return response_text, None

        quest_id = match.group(1).strip()

        # Remove the quest complete tag from the narrative
        cleaned_text = re.sub(pattern, "", response_text).strip()

        return cleaned_text, quest_id

    def detect_scene_change(self, response_text: str, user_action: Optional[str] = None) -> bool:
        """
        Detect if the narration describes a new scene that should trigger image generation

        Triggers on:
        - Location changes ("you enter", "you arrive", "you see")
        - Combat initiation ("combat begins", "initiative", "attacks")
        - NPC introductions ("appears", "steps forward", "emerges")
        - Major events ("door opens", "treasure", "dragon")

        Args:
            response_text: The DM narration
            user_action: Optional player action that triggered this narration

        Returns:
            True if scene change detected, False otherwise
        """
        # Normalize text for matching
        text_lower = response_text.lower()

        # Location change triggers
        location_triggers = [
            "you enter",
            "you arrive",
            "you reach",
            "you find yourself",
            "before you stands",
            "you see a",
            "stretches before you",
            "you come to",
            "the path leads to",
        ]

        # Combat triggers
        combat_triggers = [
            "roll initiative",
            "[ROLL:initiative",
            "combat begins",
            "attacks you",
            "draws their weapon",
            "hostile",
            "ambush",
            "leaps at you",
        ]

        # NPC/Creature appearance triggers
        appearance_triggers = [
            "appears before",
            "steps forward",
            "emerges from",
            "a figure",
            "someone",
            "creature",
            "dragon",
            "beast",
            "approaches you",
        ]

        # Major event triggers
        event_triggers = [
            "door opens",
            "gate swings",
            "treasure chest",
            "altar glows",
            "portal",
            "magical",
            "discovery",
            "reveals",
        ]

        # Check all trigger categories
        all_triggers = location_triggers + combat_triggers + appearance_triggers + event_triggers

        for trigger in all_triggers:
            if trigger in text_lower:
                logger.info(f"Scene change detected: trigger='{trigger}'")
                return True

        return False

    def extract_scene_description(
        self, response_text: str, character_context: Optional[Dict] = None
    ) -> str:
        """
        Extract a concise scene description for image generation

        Takes the first 2-3 sentences or first paragraph of narration
        and formats it for image generation

        Args:
            response_text: The full DM narration
            character_context: Character info to include in description

        Returns:
            Formatted scene description (100-200 chars ideal)
        """
        # Remove roll tags and quest tags
        clean_text = re.sub(r"\[ROLL:[^\]]+\]", "", response_text)
        clean_text = re.sub(r"\[QUEST_COMPLETE:[^\]]+\]", "", clean_text)
        clean_text = clean_text.strip()

        # Take first 2-3 sentences or up to first paragraph break
        sentences = clean_text.split(". ")
        if len(sentences) >= 3:
            description = ". ".join(sentences[:3]) + "."
        else:
            description = clean_text

        # Limit to reasonable length for image prompts
        if len(description) > 300:
            description = description[:297] + "..."

        # Add character context if available for better image consistency
        if character_context:
            char_class = character_context.get("class", "")
            char_race = character_context.get("race", "")
            if char_class and char_race:
                # Prepend character description
                char_desc = f"A {char_race} {char_class}. "
                description = char_desc + description

        return description

    def _build_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        character_context: Optional[Dict] = None,
        game_state: Optional[Dict] = None,
        memory_context: Optional[str] = None,
        language: str = "en",
    ) -> List[Dict[str, str]]:
        """
        Build message list for Mistral API with context

        Args:
            user_message: Current player action/message
            conversation_history: Previous messages
            character_context: Character information
            game_state: Current game state (location, inventory, etc.)
            memory_context: Relevant past memories from vector search
            language: Language for system prompt ("en" or "fr")

        Returns:
            List of formatted messages
        """
        # Use language-specific system prompt
        messages = [{"role": "system", "content": self.get_system_prompt(language)}]

        # Add character context if available
        if character_context:
            context_msg = self._format_character_context(character_context)
            messages.append({"role": "system", "content": context_msg})

        # Add game state if available
        if game_state:
            state_msg = self._format_game_state(game_state)
            messages.append({"role": "system", "content": state_msg})

        # Add memory context if available (RAG pattern)
        if memory_context:
            memory_msg = f"RELEVANT PAST EVENTS:\n{memory_context}"
            messages.append({"role": "system", "content": memory_msg})

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
        memory_context: Optional[str] = None,
        language: str = "en",
    ) -> Dict:
        """
        Generate DM narration in response to player action

        Args:
            user_action: What the player wants to do
            conversation_history: Previous conversation
            character_context: Character information
            game_state: Current game state
            memory_context: Relevant past memories from vector search
            language: Language for narration ("en" or "fr")

        Returns:
            Dictionary with response and metadata

        Raises:
            MistralAPIError: If API call fails
        """
        try:
            messages = self._build_messages(
                user_action,
                conversation_history,
                character_context,
                game_state,
                memory_context,
                language,
            )

            logger.debug(f"Generating narration for action: {user_action[:50]}...")

            response = await self.mistral_client.chat_completion(messages)

            narration_content = response.choices[0].message.content
            narration = str(narration_content) if narration_content else ""
            tokens_used = response.usage.total_tokens

            # Extract roll request if present
            cleaned_narration, roll_request = self.extract_roll_request(narration)

            # Extract quest complete if present
            cleaned_narration, quest_complete_id = self.extract_quest_complete(cleaned_narration)

            logger.info(f"Narration generated: {tokens_used} tokens")
            if roll_request:
                logger.info(f"Roll request detected: {roll_request}")
            if quest_complete_id:
                logger.info(f"Quest completion detected: {quest_complete_id}")

            return {
                "narration": cleaned_narration,
                "roll_request": roll_request,
                "quest_complete_id": quest_complete_id,
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
        memory_context: Optional[str] = None,
        language: str = "en",
    ) -> AsyncGenerator[str, None]:
        """
        Stream DM narration in real-time

        Args:
            user_action: What the player wants to do
            conversation_history: Previous conversation
            character_context: Character information
            game_state: Current game state
            memory_context: Relevant past memories from vector search
            language: Language for narration ("en" or "fr")

        Yields:
            Narration text chunks

        Raises:
            MistralAPIError: If API call fails
        """
        try:
            messages = self._build_messages(
                user_action,
                conversation_history,
                character_context,
                game_state,
                memory_context,
                language,
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
