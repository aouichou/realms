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
    {
        "type": "function",
        "function": {
            "name": "roll_for_npc",
            "description": "Roll dice for an NPC, monster, or enemy. Use this for ALL NPC/monster rolls: attacks, saves, ability checks, damage, or initiative. NEVER state roll results narratively - always use this tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "npc_name": {
                        "type": "string",
                        "description": "Name of NPC/monster rolling (e.g., 'Goblin', 'Guard', 'Bandit Captain')",
                    },
                    "roll_type": {
                        "type": "string",
                        "enum": ["attack", "damage", "saving_throw", "ability_check", "initiative"],
                        "description": "Type of roll: attack for attack rolls, damage for damage dice, saving_throw for saves, ability_check for skill/ability checks, initiative for combat order",
                    },
                    "dice_expression": {
                        "type": "string",
                        "description": "Dice notation (e.g., 'd20+5' for attack, '2d6+3' for damage, 'd20' for initiative)",
                    },
                    "target_name": {
                        "type": "string",
                        "description": "Optional: Name of target for attacks (e.g., 'the player', 'Theron')",
                    },
                    "context": {
                        "type": "string",
                        "description": "Brief context for the roll (e.g., 'scimitar attack', 'Dexterity saving throw', 'Stealth check')",
                    },
                },
                "required": ["npc_name", "roll_type", "dice_expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "introduce_companion",
            "description": "Introduce a new AI-driven companion NPC that will travel with the player. Use this when organically introducing allies, guides, or story-relevant NPCs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Unique name for the companion (e.g., 'Elara Swiftwind', 'Grimtooth', 'Seraphina')",
                    },
                    "creature_name": {
                        "type": "string",
                        "description": "Base creature type from creatures database (e.g., 'Elf Scout', 'Dwarf Warrior', 'Guard'). Stats will be copied from this creature.",
                    },
                    "personality": {
                        "type": "string",
                        "description": "Core personality traits (e.g., 'brave, loyal, curious, witty', 'gruff, protective, honor-bound')",
                    },
                    "goals": {
                        "type": "string",
                        "description": "Companion's personal goals or motivations (e.g., 'Find her missing brother', 'Redeem his tarnished honor', 'Protect ancient knowledge')",
                    },
                    "relationship_status": {
                        "type": "string",
                        "enum": ["just_met", "ally", "friend", "trusted", "suspicious"],
                        "description": "Initial relationship with player: just_met for first encounter, ally for cooperative, friend for warm, trusted for deep bond, suspicious for uneasy alliance",
                    },
                    "background": {
                        "type": "string",
                        "description": "Brief backstory for companion (e.g., 'Former royal guard exiled for speaking truth', 'Ranger searching the wilds for her captured sibling')",
                    },
                },
                "required": ["name", "creature_name", "personality"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "companion_suggest_action",
            "description": "Allow a companion to suggest tactical options or courses of action to the player. Use this when a companion would naturally offer strategic advice based on their personality and knowledge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "companion_name": {
                        "type": "string",
                        "description": "Name of the companion making the suggestion",
                    },
                    "suggestion": {
                        "type": "string",
                        "description": "The tactical suggestion or advice being offered (e.g., 'I could flank from the left while you distract them', 'We should investigate that suspicious shrine')",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why the companion is suggesting this (e.g., 'based on my scouting experience', 'I sense something magical here')",
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "moderate", "high", "critical"],
                        "description": "How urgent the suggestion is: low for general advice, moderate for tactical suggestions, high for important warnings, critical for immediate danger",
                    },
                },
                "required": ["companion_name", "suggestion"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "companion_share_knowledge",
            "description": "Allow a companion to share lore, information, or knowledge with the player. Use this when a companion would know relevant information about locations, creatures, history, or magic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "companion_name": {
                        "type": "string",
                        "description": "Name of the companion sharing knowledge",
                    },
                    "topic": {
                        "type": "string",
                        "description": "What the knowledge is about (e.g., 'ancient ruins', 'goblin tactics', 'local legends', 'magical artifacts')",
                    },
                    "information": {
                        "type": "string",
                        "description": "The actual information or lore being shared. Should be 2-4 sentences of useful knowledge.",
                    },
                    "source": {
                        "type": "string",
                        "description": "How the companion knows this (e.g., 'from my military training', 'tales from my village', 'I read about this in the archives')",
                    },
                    "reliability": {
                        "type": "string",
                        "enum": ["certain", "confident", "uncertain", "rumor"],
                        "description": "How reliable the information is: certain for facts, confident for likely true, uncertain for educated guess, rumor for hearsay",
                    },
                },
                "required": ["companion_name", "topic", "information"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "give_item",
            "description": "Give an item from the catalog to the player's character inventory. Use this when the DM awards loot, quest rewards, or the player purchases/finds items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {
                        "type": "string",
                        "description": "Name of the item to give (e.g., 'Longsword', 'Healing Potion', 'Chain Mail')",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of items to give (default: 1). Use for stackable items like potions, arrows, gold pieces.",
                        "minimum": 1,
                        "default": 1,
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why the item is being given (e.g., 'found in treasure chest', 'quest reward from mayor', 'purchased from blacksmith')",
                    },
                },
                "required": ["item_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_items",
            "description": "Search the item catalog (14,351 items) for DM reference. Use this to look up item stats, costs, and properties. Supports both exact name matching and semantic search for natural language queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term. For exact matching: 'longsword', 'healing potion'. For semantic search: 'healing magic', 'fire weapons', 'protective gear'",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["weapon", "armor", "shield", "potion", "scroll", "wondrous_item", "general"],
                        "description": "Filter by item category",
                    },
                    "rarity": {
                        "type": "string",
                        "enum": ["common", "uncommon", "rare", "very rare", "legendary", "artifact"],
                        "description": "Filter by rarity for magic items",
                    },
                    "semantic": {
                        "type": "boolean",
                        "description": "Use semantic search for natural language queries (e.g., 'healing magic'). Default: false for exact matching.",
                        "default": False,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10, max: 50)",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_monsters",
            "description": "Search the creature database (11,172 monsters) for DM reference. Returns stat blocks for combat encounters. Supports semantic search for natural language queries like 'undead creatures' or 'fire breathing'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term. For exact: 'goblin', 'ancient red dragon'. For semantic: 'undead creatures', 'flying enemies', 'weak monsters'",
                    },
                    "creature_type": {
                        "type": "string",
                        "description": "Filter by type: undead, dragon, humanoid, beast, fiend, celestial, elemental, fey, construct, monstrosity, aberration, giant, ooze, plant",
                    },
                    "semantic": {
                        "type": "boolean",
                        "description": "Use semantic search for natural language queries. Default: false for exact matching.",
                        "default": False,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10, max: 50)",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_spells",
            "description": "Search the spell database (4,759 spells) for DM reference. Useful for spell effects, casting requirements, and damage calculations. Supports semantic search for natural language queries like 'fire damage spells'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term. For exact: 'fireball', 'cure wounds'. For semantic: 'fire damage', 'healing spells', 'protective magic'",
                    },
                    "spell_level": {
                        "type": "integer",
                        "description": "Filter by spell level (0 for cantrips, 1-9 for leveled spells)",
                        "minimum": 0,
                        "maximum": 9,
                    },
                    "school": {
                        "type": "string",
                        "enum": ["abjuration", "conjuration", "divination", "enchantment", "evocation", "illusion", "necromancy", "transmutation"],
                        "description": "Filter by spell school",
                    },
                    "semantic": {
                        "type": "boolean",
                        "description": "Use semantic search for natural language queries. Default: false for exact matching.",
                        "default": False,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10, max: 50)",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memories",
            "description": "Search past adventure memories to recall events, NPCs, locations, or plot points. Use when you need to remember something from earlier in the adventure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for (e.g., 'dragon encounter', 'tavern keeper', 'magical artifact')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default: 5, max: 10)",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_available_tools",
            "description": "Get a list of all available DM tools. Use when you need a reminder of what actions you can take.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_monster_loot",
            "description": "Get appropriate loot for defeating a monster. Returns equipment based on monster CR (Challenge Rating). Higher CR monsters drop better loot. Use after combat victories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "monster_name": {
                        "type": "string",
                        "description": "Name of the monster (e.g., 'Goblin', 'Ancient Red Dragon', 'Lich')",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of loot items to generate (default: 3, max: 10)",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 3,
                    },
                },
                "required": ["monster_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_treasure_hoard",
            "description": "Generate random treasure hoard for encounter CR. Creates thematically appropriate loot based on encounter difficulty. CR 0-4: common, CR 5-10: uncommon, CR 11-16: rare, CR 17-20: very rare, CR 21+: legendary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "challenge_rating": {
                        "type": "number",
                        "description": "Challenge Rating of the encounter (e.g., 5 for moderate, 10 for deadly, 20 for epic)",
                    },
                    "num_items": {
                        "type": "integer",
                        "description": "Number of items in the hoard (default: 5, max: 10)",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                    },
                    "include_consumables": {
                        "type": "boolean",
                        "description": "Include potions and scrolls in the hoard (default: true)",
                        "default": True,
                    },
                },
                "required": ["challenge_rating"],
            },
        },
    },
]
