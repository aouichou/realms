"""AI Companion Service with personality-based responses"""

import os
from typing import Any, Dict, Optional

from mistralai import Mistral

# Initialize Mistral client
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None

# Companion Personality Prompts
COMPANION_PERSONALITIES = {
    "helpful": {
        "system_prompt": """You are {name}, a helpful {race} {companion_class} companion in a D&D adventure.

Your personality: HELPFUL
- Always suggest optimal strategies
- Warn of dangers before they become critical
- Offer tactical advice in combat
- Explain game mechanics when useful
- Prioritize party survival

Current situation:
- Player HP: {player_hp}/{player_max_hp}
- Your HP: {companion_hp}/{companion_max_hp}
- In combat: {in_combat}
- Location: {location}

Respond in-character with helpful tactical advice.
Keep responses under 50 words unless providing crucial information.""",
        "triggers": ["combat_start", "player_low_hp", "exploration", "puzzle"],
    },
    "brave": {
        "system_prompt": """You are {name}, a brave {race} {companion_class} companion in a D&D adventure.

Your personality: BRAVE
- Encourage heroic actions
- Never suggest retreat
- Celebrate combat victories
- Mock cowardice (playfully)
- Take risks

Current situation:
- Player HP: {player_hp}/{player_max_hp}
- Your HP: {companion_hp}/{companion_max_hp}
- In combat: {in_combat}
- Enemies: {enemies}

Respond with bravery and encourage bold action.
Keep responses under 40 words.""",
        "triggers": ["combat_start", "victory", "boss_encounter"],
    },
    "cautious": {
        "system_prompt": """You are {name}, a cautious {race} {companion_class} companion in a D&D adventure.

Your personality: CAUTIOUS
- Prioritize survival over glory
- Suggest retreat when outmatched
- Warn about traps and dangers
- Conserve resources
- Plan before acting

Current situation:
- Player HP: {player_hp}/{player_max_hp} {hp_warning}
- Enemies: {enemies} {enemy_warning}
- Location: {location}

Respond with caution and concern for safety.""",
        "triggers": ["player_low_hp", "outnumbered", "exploration", "trap"],
    },
    "sarcastic": {
        "system_prompt": """You are {name}, a sarcastic {race} {companion_class} companion in a D&D adventure.

Your personality: SARCASTIC
- Make witty comments about situations
- Use humor to lighten mood
- Tease player (playfully)
- Still provide useful info, but sarcastically

Current situation: {situation}

Respond with sarcasm and wit. Keep it fun, not mean.
Keep responses under 35 words.""",
        "triggers": ["combat_start", "player_action", "npc_interaction"],
    },
    "mysterious": {
        "system_prompt": """You are {name}, a mysterious {race} {companion_class} companion in a D&D adventure.

Your personality: MYSTERIOUS
- Speak in cryptic hints
- Reference hidden knowledge
- Have a secret agenda (don't reveal fully)
- Know more than you say

Current situation: {situation}

Respond mysteriously. Hint at deeper knowledge.
Keep responses under 40 words.""",
        "triggers": ["exploration", "lore_discovery", "magic_item"],
    },
    "scholarly": {
        "system_prompt": """You are {name}, a scholarly {race} {companion_class} companion in a D&D adventure.

Your personality: SCHOLARLY
- Provide lore and history
- Identify monsters with detail
- Explain magic and artifacts
- Reference books and studies

Current situation: {situation}

Respond with academic knowledge and explanations.
Keep responses under 50 words.""",
        "triggers": ["monster_encounter", "magic_item", "lore_discovery", "puzzle"],
    },
}


class CompanionService:
    """Service for generating AI companion responses"""

    @staticmethod
    def get_personality_triggers(personality: str) -> list[str]:
        """Get list of triggers for a personality"""
        return COMPANION_PERSONALITIES.get(personality, {}).get("triggers", [])

    @staticmethod
    def _format_prompt(
        personality: str,
        companion_name: str,
        companion_race: str,
        companion_class: str,
        context: Dict[str, Any],
    ) -> str:
        """Format system prompt with context"""
        prompt_template = COMPANION_PERSONALITIES.get(personality, {}).get(
            "system_prompt", COMPANION_PERSONALITIES["helpful"]["system_prompt"]
        )

        # Prepare context values with defaults
        player_hp = context.get("player_hp", 50)
        player_max_hp = context.get("player_max_hp", 50)
        companion_hp = context.get("companion_hp", 40)
        companion_max_hp = context.get("companion_max_hp", 40)
        in_combat = context.get("in_combat", False)
        location = context.get("location", "Unknown")
        enemies = context.get("enemies", "None")
        enemy_count = context.get("enemy_count", 0)
        situation = context.get("situation", "Adventure continues")

        # Calculate warnings
        hp_warning = "(LOW!)" if player_hp < player_max_hp * 0.3 else ""
        enemy_warning = "(OUTNUMBERED!)" if enemy_count > 2 else ""

        # Format the prompt
        return prompt_template.format(
            name=companion_name,
            race=companion_race,
            companion_class=companion_class,
            player_hp=player_hp,
            player_max_hp=player_max_hp,
            companion_hp=companion_hp,
            companion_max_hp=companion_max_hp,
            in_combat=in_combat,
            location=location,
            enemies=enemies,
            enemy_count=enemy_count,
            situation=situation,
            hp_warning=hp_warning,
            enemy_warning=enemy_warning,
        )

    @staticmethod
    async def generate_companion_speech(
        personality: str,
        companion_name: str,
        companion_race: str,
        companion_class: str,
        trigger: str,
        context: Dict[str, Any],
        user_message: Optional[str] = None,
    ) -> str:
        """Generate companion speech using Mistral AI

        Args:
            personality: Companion personality type (helpful, brave, cautious, etc.)
            companion_name: Name of the companion
            companion_race: Race of the companion
            companion_class: Class of the companion
            trigger: Event that triggered the speech (combat_start, player_low_hp, etc.)
            context: Dict with game state (hp, enemies, location, etc.)
            user_message: Optional message from player to respond to

        Returns:
            str: Generated companion speech
        """
        if not client:
            # Fallback responses if no API key
            fallback = {
                "helpful": "Let me help you with that. Stay safe out there!",
                "brave": "We can handle this! To victory!",
                "cautious": "Perhaps we should proceed carefully...",
                "sarcastic": f"Oh great, another {trigger.replace('_', ' ')}...",
                "mysterious": "I sense something... unusual here.",
                "scholarly": "Interesting. According to my studies, this is quite rare.",
            }
            return fallback.get(personality, "...")

        # Format system prompt
        system_prompt = CompanionService._format_prompt(
            personality, companion_name, companion_race, companion_class, context
        )

        # Prepare user message
        if user_message:
            message = f"Trigger: {trigger}\nPlayer says: {user_message}"
        else:
            message = f"Trigger: {trigger}\nRespond to this situation in character."

        try:
            # Call Mistral API
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                max_tokens=100,
                temperature=0.8,
            )

            content = response.choices[0].message.content
            if isinstance(content, str):
                return content.strip()
            return str(content).strip() if content else "..."

        except Exception as e:
            print(f"Error generating companion speech: {e}")
            # Return personality-appropriate fallback
            fallback = {
                "helpful": "I'm here to help. What do you need?",
                "brave": "Let's face this together!",
                "cautious": "We should be careful here.",
                "sarcastic": "Well, this should be interesting...",
                "mysterious": "The path ahead is unclear...",
                "scholarly": "Fascinating. Let me think on this.",
            }
            return fallback.get(personality, "...")
