"""
Tool definitions for Mistral DM to call game mechanics functions.
Showcases Mistral's advanced function calling capabilities.
"""

from typing import Any

# Tool definitions in Mistral API format
GAME_MASTER_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "request_player_roll",
            "description": "Request a dice roll from the player for ability checks, saving throws, or attacks. Use this when the player attempts an action with uncertain outcome.",
            "parameters": {
                "type": "object",
                "properties": {
                    "roll_type": {
                        "type": "string",
                        "enum": ["ability_check", "saving_throw", "attack", "damage"],
                        "description": "Type of roll needed: ability_check for skill checks, saving_throw for saves against spells/effects, attack for combat, damage for damage rolls",
                    },
                    "ability_or_skill": {
                        "type": "string",
                        "description": "Ability score (STR, DEX, CON, INT, WIS, CHA) or skill name (Stealth, Perception, Athletics, etc.)",
                    },
                    "dc": {
                        "type": "integer",
                        "description": "Difficulty Class (5=very easy, 10=easy, 15=moderate, 20=hard, 25=very hard, 30=nearly impossible)",
                    },
                    "advantage": {
                        "type": "boolean",
                        "description": "Roll with advantage (roll twice, take higher). Use when player has favorable conditions.",
                    },
                    "disadvantage": {
                        "type": "boolean",
                        "description": "Roll with disadvantage (roll twice, take lower). Use when player has unfavorable conditions.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what the roll is for (e.g., 'sneaking past guards', 'resisting poison')",
                    },
                },
                "required": ["roll_type", "ability_or_skill"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_character_hp",
            "description": "Change character's hit points due to damage or healing. Use this when combat damage occurs or healing is applied.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "integer",
                        "description": "HP change amount. Negative for damage (e.g., -5 for 5 damage), positive for healing (e.g., +8 for 8 HP restored)",
                    },
                    "damage_type": {
                        "type": "string",
                        "description": "Type of damage: fire, cold, lightning, acid, poison, necrotic, radiant, slashing, piercing, bludgeoning, force, psychic, thunder",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Narrative reason for HP change (e.g., 'goblin scimitar strike', 'healing potion', 'fall damage')",
                    },
                },
                "required": ["amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consume_spell_slot",
            "description": "Consume a spell slot when the DM determines a player is casting a spell. Use this ONLY if spell slot auto-detection fails.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spell_level": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 9,
                        "description": "Spell slot level to consume (1-9). Do not use for cantrips (level 0).",
                    },
                    "spell_name": {
                        "type": "string",
                        "description": "Name of the spell being cast",
                    },
                },
                "required": ["spell_level", "spell_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_creature_stats",
            "description": "Retrieve stat block for an NPC, monster, or companion to use in encounters. Use this when you need accurate stats for combat or interactions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "creature_name": {
                        "type": "string",
                        "description": "Name of creature (e.g., 'Goblin', 'Bandit', 'Wolf', 'Guard')",
                    },
                    "creature_type": {
                        "type": "string",
                        "enum": ["monster", "npc", "companion"],
                        "description": "Type of creature: monster for beasts/enemies, npc for humanoid characters, companion for allied creatures",
                    },
                },
                "required": ["creature_name"],
            },
        },
    },
]
