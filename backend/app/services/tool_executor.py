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
        elif tool_name == "roll_for_npc":
            return await _execute_roll_for_npc(tool_arguments, db)
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
    Uses fuzzy matching to find creatures by name.
    """
    from sqlalchemy import func, select

    from app.db.models.creature import Creature

    creature_name = args.get("creature_name", "Unknown")
    creature_type = args.get("creature_type")

    logger.info(f"Looking up creature: '{creature_name}' (type: {creature_type})")

    # Try exact match first
    query = select(Creature).where(func.lower(Creature.name) == func.lower(creature_name))

    if creature_type:
        query = query.where(Creature.creature_type == creature_type.lower())

    result = await db.execute(query)
    creature = result.scalar_one_or_none()

    # If no exact match, try fuzzy match (contains)
    if not creature:
        query = select(Creature).where(
            func.lower(Creature.name).contains(func.lower(creature_name))
        )
        if creature_type:
            query = query.where(Creature.creature_type == creature_type.lower())

        result = await db.execute(query.limit(1))
        creature = result.scalar_one_or_none()

    if not creature:
        logger.warning(f"Creature '{creature_name}' not found in database")
        return {
            "success": False,
            "error": f"Creature '{creature_name}' not found in database",
            "message": f"Could not find '{creature_name}'. Try a more specific name or check spelling.",
        }

    # Return formatted stat block
    stat_block = creature.get_stat_block()

    logger.info(f"Successfully retrieved stats for '{creature.name}' (CR {creature.cr})")

    return {
        "success": True,
        "creature_name": creature.name,
        "stat_block": stat_block,
        "creature_data": creature.to_dict(),
        "message": f"Retrieved stats for {creature.name} (CR {creature.cr})",
    }


async def _execute_roll_for_npc(
    args: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Execute dice roll for NPC/monster.
    Shows transparency in combat by displaying actual roll results.
    """
    from app.services.dice_service import DiceService

    npc_name = args.get("npc_name", "Unknown NPC")
    roll_type = args.get("roll_type", "attack")
    dice_expression = args.get("dice_expression", "d20")
    target_name = args.get("target_name")
    context = args.get("context", "")

    logger.info(f"Rolling {dice_expression} for {npc_name} ({roll_type})")

    try:
        # Parse and roll the dice
        dice_service = DiceService()
        count, sides, modifier = dice_service.parse_dice_notation(dice_expression)

        # Roll all dice
        rolls = []
        for _ in range(count):
            roll = await dice_service.roll_die(sides)
            rolls.append(roll)

        # Calculate total
        dice_total = sum(rolls)
        final_total = dice_total + modifier

        # Format roll breakdown
        breakdown_parts = []
        if len(rolls) > 1:
            breakdown_parts.append(f"{len(rolls)}d{sides}: {rolls} = {dice_total}")
        else:
            breakdown_parts.append(f"d{sides}: {rolls[0]}")

        if modifier != 0:
            sign = "+" if modifier > 0 else ""
            breakdown_parts.append(f"{sign}{modifier}")

        breakdown = " ".join(breakdown_parts)

        # Create result message
        result_msg = f"{npc_name} rolled {final_total}"
        if context:
            result_msg += f" ({context})"
        if target_name:
            result_msg += f" vs {target_name}"

        logger.info(f"NPC roll result: {result_msg} [{breakdown}]")

        return {
            "success": True,
            "npc_name": npc_name,
            "roll_type": roll_type,
            "result": final_total,
            "breakdown": breakdown,
            "rolls": rolls,
            "modifier": modifier,
            "target_name": target_name,
            "context": context,
            "message": result_msg,
        }

    except ValueError as e:
        logger.error(f"Invalid dice expression '{dice_expression}': {e}")
        return {
            "success": False,
            "error": f"Invalid dice notation: {dice_expression}",
            "message": f"Could not parse dice expression '{dice_expression}'. Use format like 'd20+5' or '2d6+3'",
        }
    except Exception as e:
        logger.error(f"Error rolling for NPC: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to roll dice for {npc_name}",
        }
