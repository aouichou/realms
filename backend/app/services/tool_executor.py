"""
Tool execution service for Mistral DM tool calling.
Executes game mechanics functions requested by the DM.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.db.models.character import Character

logger = logging.getLogger(__name__)


async def execute_tool(
    tool_name: str,
    tool_arguments: dict[str, Any],
    character: Character,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Execute a game mechanic tool and return the result.

    Args:
        tool_name: Name of the tool to execute
        tool_arguments: Arguments passed by Mistral DM
        character: Character model instance
        db: Database session

    Returns:
        Dictionary with execution result and any state changes
    """
    logger.info(f"Executing tool: {tool_name} with args: {tool_arguments}")

    try:
        if tool_name == "request_player_roll":
            return await _execute_request_player_roll(tool_arguments, character)
        elif tool_name == "update_character_hp":
            return await _execute_update_character_hp(tool_arguments, character, db)
        elif tool_name == "consume_spell_slot":
            return await _execute_consume_spell_slot(tool_arguments, character, db)
        elif tool_name == "get_creature_stats":
            return await _execute_get_creature_stats(tool_arguments, db)
        else:
            logger.error(f"Unknown tool: {tool_name}")
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
            }
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
        }


async def _execute_request_player_roll(
    args: dict[str, Any],
    character: Character,
) -> dict[str, Any]:
    """
    Request a roll from the player.
    This doesn't modify state, just returns roll parameters.
    """
    roll_type = args.get("roll_type")
    ability_or_skill = args.get("ability_or_skill")
    dc = args.get("dc")
    advantage = args.get("advantage", False)
    disadvantage = args.get("disadvantage", False)
    description = args.get("description", "")

    logger.info(
        f"Roll requested: {roll_type} for {ability_or_skill} "
        f"(DC {dc}, adv={advantage}, dis={disadvantage})"
    )

    return {
        "success": True,
        "roll_request": {
            "type": roll_type,
            "ability_or_skill": ability_or_skill,
            "dc": dc,
            "advantage": advantage,
            "disadvantage": disadvantage,
            "description": description,
        },
        "message": f"Requesting {roll_type} roll for {ability_or_skill}"
        + (f" (DC {dc})" if dc else ""),
    }


async def _execute_update_character_hp(
    args: dict[str, Any],
    character: Character,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Update character's HP (damage or healing).
    Negative amount = damage, positive = healing.
    """
    amount = args.get("amount", 0)
    damage_type = args.get("damage_type")
    reason = args.get("reason", "")

    old_hp = character.current_hp
    character.current_hp = max(0, min(character.max_hp, character.current_hp + amount))
    new_hp = character.current_hp

    # Persist changes
    flag_modified(character, "current_hp")
    await db.flush()
    await db.commit()

    hp_change = new_hp - old_hp

    logger.info(
        f"HP updated for {character.name}: {old_hp} -> {new_hp} "
        f"(change: {hp_change}, reason: {reason})"
    )

    return {
        "success": True,
        "character_update": {
            "hp": {
                "old": old_hp,
                "new": new_hp,
                "change": hp_change,
            }
        },
        "message": f"HP changed from {old_hp} to {new_hp}" + (f" ({reason})" if reason else ""),
        "damage_type": damage_type,
    }


async def _execute_consume_spell_slot(
    args: dict[str, Any],
    character: Character,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Consume a spell slot when DM detects spell casting.
    """
    spell_level = args.get("spell_level")
    spell_name = args.get("spell_name", "Unknown Spell")

    if not spell_level or spell_level < 1 or spell_level > 9:
        return {
            "success": False,
            "error": f"Invalid spell level: {spell_level}",
        }

    # Check if spell slots exist and have remaining slots
    spell_slots = character.spell_slots or {}
    slot_key = f"level_{spell_level}"

    if slot_key not in spell_slots:
        return {
            "success": False,
            "error": f"Character has no level {spell_level} spell slots",
            "warning": f"⚠️ {character.name} doesn't have level {spell_level} spell slots",
        }

    slots_remaining = spell_slots[slot_key].get("remaining", 0)

    if slots_remaining <= 0:
        return {
            "success": False,
            "warning": f"⚠️ No level {spell_level} spell slots remaining",
        }

    # Consume the slot
    spell_slots[slot_key]["remaining"] = slots_remaining - 1
    character.spell_slots = spell_slots
    flag_modified(character, "spell_slots")
    await db.flush()
    await db.commit()

    logger.info(
        f"Spell slot consumed: {character.name} cast {spell_name} "
        f"(Level {spell_level}, {slots_remaining - 1} remaining)"
    )

    return {
        "success": True,
        "character_update": {
            "spell_slots": {
                "level": spell_level,
                "remaining": slots_remaining - 1,
            }
        },
        "message": f"Consumed level {spell_level} spell slot for {spell_name} ({slots_remaining - 1} remaining)",
    }


async def _execute_get_creature_stats(
    args: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Retrieve creature stats from database.
    Note: This requires RL-130 (creature dataset) to be implemented.
    For now, returns a placeholder.
    """
    creature_name = args.get("creature_name", "Unknown")
    creature_type = args.get("creature_type", "monster")

    # TODO: RL-130 - Implement creature database lookup
    # For now, return placeholder stats
    logger.warning(
        f"get_creature_stats called for '{creature_name}' but RL-130 not yet implemented. "
        "Returning placeholder stats."
    )

    # Placeholder goblin stats as example
    placeholder_stats = {
        "name": creature_name,
        "type": creature_type,
        "ac": 15,
        "hp": 7,
        "speed": 30,
        "str": 8,
        "dex": 14,
        "con": 10,
        "int": 10,
        "wis": 8,
        "cha": 8,
        "cr": "1/4",
        "note": "Placeholder stats - RL-130 creature database not yet implemented",
    }

    return {
        "success": True,
        "creature_stats": placeholder_stats,
        "message": f"Retrieved stats for {creature_name} (placeholder until RL-130)",
        "warning": "⚠️ Using placeholder stats - creature database not yet implemented (RL-130)",
    }
