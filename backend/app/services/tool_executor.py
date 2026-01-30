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
        elif tool_name == "introduce_companion":
            return await _execute_introduce_companion(tool_arguments, character, db)
        elif tool_name == "companion_suggest_action":
            return await _execute_companion_suggest_action(tool_arguments, character, db)
        elif tool_name == "companion_share_knowledge":
            return await _execute_companion_share_knowledge(tool_arguments, character, db)
        elif tool_name == "give_item":
            return await _execute_give_item(tool_arguments, character, db)
        elif tool_name == "search_items":
            return await _execute_search_items(tool_arguments, db)
        elif tool_name == "search_monsters":
            return await _execute_search_monsters(tool_arguments, db)
        elif tool_name == "search_spells":
            return await _execute_search_spells(tool_arguments, db)
        elif tool_name == "search_memories":
            return await _execute_search_memories(tool_arguments, character, db)
        elif tool_name == "get_monster_loot":
            return await _execute_get_monster_loot(tool_arguments, db)
        elif tool_name == "generate_treasure_hoard":
            return await _execute_generate_treasure_hoard(tool_arguments, db)
        elif tool_name == "list_available_tools":
            return await _execute_list_available_tools(tool_arguments)
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


async def _execute_introduce_companion(
    args: dict[str, Any],
    character: Character,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Introduce a new AI-driven companion NPC.
    Links to creature stats and generates avatar.
    """
    from sqlalchemy import func, select

    from app.db.models.companion import Companion
    from app.db.models.creature import Creature

    name = args.get("name", "Unknown Companion")
    creature_name = args.get("creature_name", "Guard")
    personality = args.get("personality", "Friendly and helpful")
    goals = args.get("goals")
    relationship_status = args.get("relationship_status", "just_met")
    background = args.get("background", "")

    logger.info(f"Creating companion '{name}' based on creature '{creature_name}'")

    # Step 1: Look up creature stats
    query = select(Creature).where(func.lower(Creature.name) == func.lower(creature_name))
    result = await db.execute(query)
    creature = result.scalar_one_or_none()

    # Try fuzzy match if exact fails
    if not creature:
        query = select(Creature).where(
            func.lower(Creature.name).contains(func.lower(creature_name))
        )
        result = await db.execute(query.limit(1))
        creature = result.scalar_one_or_none()

    if not creature:
        logger.error(f"Creature '{creature_name}' not found for companion creation")
        return {
            "success": False,
            "error": f"Creature '{creature_name}' not found in database",
            "message": f"Cannot create companion: creature '{creature_name}' does not exist. Try a different creature name.",
        }

    # Step 2: Create companion with stats from creature
    companion = Companion(
        character_id=character.id,
        creature_id=creature.id,
        name=name,
        creature_name=creature.name,
        personality=personality,
        goals=goals,
        background=background,
        relationship_status=relationship_status,
        loyalty=50,  # Start at neutral
        # Copy combat stats from creature
        hp=creature.hp or 10,
        max_hp=creature.hp or 10,
        ac=creature.ac or 10,
        # Copy ability scores
        strength=creature.strength,
        dexterity=creature.dexterity,
        constitution=creature.constitution,
        intelligence=creature.intelligence,
        wisdom=creature.wisdom,
        charisma=creature.charisma,
        # Copy additional data
        actions=creature.actions if hasattr(creature, "actions") else None,
        special_traits=creature.traits if hasattr(creature, "traits") else None,
        speed=creature.speed,
        # State
        is_active=True,
        is_alive=True,
        death_save_successes=0,
        death_save_failures=0,
    )

    # Step 3: Generate companion avatar
    try:
        from app.services.image_service import ImageService

        image_service = ImageService()

        # Create avatar prompt
        avatar_prompt = f"Fantasy character portrait: {name}, a {creature.name}. "
        avatar_prompt += f"Personality: {personality}. "
        if background:
            avatar_prompt += f"Background: {background}. "
        avatar_prompt += "Style: D&D character art, detailed, fantasy illustration, hero portrait."

        logger.info(f"Generating avatar for companion '{name}'")
        image_url = await image_service.generate_image(
            prompt=avatar_prompt,
            character_id=character.id,
            image_type="companion_avatar",
        )

        if image_url:
            companion.avatar_url = image_url
            logger.info(f"Avatar generated successfully: {image_url}")
    except Exception as e:
        logger.warning(f"Failed to generate companion avatar: {e}")
        # Continue without avatar - not a critical failure

    # Step 4: Save to database
    db.add(companion)
    await db.flush()
    await db.commit()
    await db.refresh(companion)

    logger.info(
        f"Companion created: {companion.name} (ID: {companion.id}, Creature: {creature.name}, HP: {companion.hp}, AC: {companion.ac})"
    )

    return {
        "success": True,
        "companion": companion.to_dict(),
        "message": f"{name} joins the party as a companion! (Based on {creature.name}: HP {companion.hp}, AC {companion.ac})",
    }


async def _execute_list_available_tools(
    args: dict[str, Any],
) -> dict[str, Any]:
    """
    List all available DM tools with descriptions.
    Helps DM remember what actions are available.
    """
    from app.dm_tools import GAME_MASTER_TOOLS

    tools_list = []

    for tool in GAME_MASTER_TOOLS:
        if tool.get("type") == "function" and "function" in tool:
            func_info = tool["function"]
            tools_list.append(
                {
                    "name": func_info.get("name"),
                    "description": func_info.get("description"),
                    "parameters": list(
                        func_info.get("parameters", {}).get("properties", {}).keys()
                    ),
                }
            )

    logger.info(f"Listing {len(tools_list)} available tools")

    # Format as readable text
    tool_descriptions = []
    for tool in tools_list:
        params_str = ", ".join(tool["parameters"]) if tool["parameters"] else "none"
        tool_descriptions.append(
            f"• **{tool['name']}**: {tool['description']} (Parameters: {params_str})"
        )

    formatted_list = "\n".join(tool_descriptions)

    return {
        "success": True,
        "tools": tools_list,
        "message": f"Available DM Tools ({len(tools_list)} total):\n\n{formatted_list}",
    }


async def _execute_companion_suggest_action(
    args: dict[str, Any],
    character: Character,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Allow a companion to suggest a tactical action to the player.
    """
    from sqlalchemy import select

    from app.db.models.companion import Companion

    companion_name = args.get("companion_name")
    suggestion = args.get("suggestion")
    reason = args.get("reason", "")
    urgency = args.get("urgency", "moderate")

    if not companion_name or not suggestion:
        return {
            "success": False,
            "error": "companion_name and suggestion are required",
        }

    # Verify companion exists and belongs to character
    result = await db.execute(
        select(Companion).where(
            Companion.character_id == character.id, Companion.name == companion_name
        )
    )
    companion = result.scalar_one_or_none()

    if not companion:
        return {
            "success": False,
            "error": f"Companion {companion_name} not found for this character",
        }

    logger.info(f"Companion {companion_name} suggesting action (urgency: {urgency}): {suggestion}")

    # Format the suggestion with urgency styling
    urgency_emojis = {
        "low": "💡",
        "moderate": "⚔️",
        "high": "⚠️",
        "critical": "🚨",
    }

    emoji = urgency_emojis.get(urgency, "💡")
    reason_text = f" ({reason})" if reason else ""

    return {
        "success": True,
        "companion_name": companion_name,
        "suggestion": suggestion,
        "urgency": urgency,
        "message": f"{emoji} **{companion_name}'s Suggestion:** {suggestion}{reason_text}",
    }


async def _execute_companion_share_knowledge(
    args: dict[str, Any],
    character: Character,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Allow a companion to share knowledge or lore with the player.
    """
    from sqlalchemy import select

    from app.db.models.companion import Companion

    companion_name = args.get("companion_name")
    topic = args.get("topic")
    information = args.get("information")
    source = args.get("source", "")
    reliability = args.get("reliability", "confident")

    if not companion_name or not topic or not information:
        return {
            "success": False,
            "error": "companion_name, topic, and information are required",
        }

    # Verify companion exists and belongs to character
    result = await db.execute(
        select(Companion).where(
            Companion.character_id == character.id, Companion.name == companion_name
        )
    )
    companion = result.scalar_one_or_none()

    if not companion:
        return {
            "success": False,
            "error": f"Companion {companion_name} not found for this character",
        }

    logger.info(f"Companion {companion_name} sharing knowledge about {topic}")

    # Format the knowledge with reliability indicator
    reliability_indicators = {
        "certain": "✓ (Certain)",
        "confident": "➜ (Confident)",
        "uncertain": "? (Uncertain)",
        "rumor": "~ (Rumor)",
    }

    indicator = reliability_indicators.get(reliability, "➜")
    source_text = f" (Source: {source})" if source else ""

    return {
        "success": True,
        "companion_name": companion_name,
        "topic": topic,
        "information": information,
        "reliability": reliability,
        "message": f"📚 **{companion_name}'s Knowledge about {topic}:** {indicator}\n\n{information}{source_text}",
    }


async def _execute_give_item(
    args: dict[str, Any],
    character: Character,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Give an item from the catalog to the player's inventory.
    """
    from sqlalchemy import func, select

    from app.db.models.item import Item
    from app.db.models.item_catalog import ItemCatalog

    item_name = args.get("item_name")
    quantity = args.get("quantity", 1)
    reason = args.get("reason", "")

    if not item_name:
        return {
            "success": False,
            "error": "item_name is required",
        }

    # Look up item in catalog (fuzzy match)
    query = select(ItemCatalog).where(func.lower(ItemCatalog.name) == func.lower(item_name))
    result = await db.execute(query)
    catalog_item = result.scalar_one_or_none()

    # Try fuzzy match if exact match fails
    if not catalog_item:
        query = select(ItemCatalog).where(
            func.lower(ItemCatalog.name).contains(func.lower(item_name))
        )
        result = await db.execute(query.limit(1))
        catalog_item = result.scalar_one_or_none()

    if not catalog_item:
        return {
            "success": False,
            "error": f"Item '{item_name}' not found in catalog. Use search_items to find available items.",
        }

    # Create item in player's inventory
    new_item = Item(
        character_id=character.id,
        name=catalog_item.name,
        category=catalog_item.category,
        quantity=quantity,
        equipped=False,
        properties=catalog_item.properties or {},
        description=catalog_item.description,
    )

    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)

    logger.info(f"Gave {quantity}x {catalog_item.name} to character {character.id}")

    reason_text = f" ({reason})" if reason else ""
    item_desc = (
        catalog_item.description[:100] + "..."
        if catalog_item.description and len(catalog_item.description) > 100
        else catalog_item.description or ""
    )

    return {
        "success": True,
        "item": {
            "name": catalog_item.name,
            "category": catalog_item.category,
            "quantity": quantity,
            "description": item_desc,
        },
        "message": f"✨ **Item Given:** {quantity}x {catalog_item.name}{reason_text}\n{item_desc}",
    }


async def _execute_search_items(
    args: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Search the item catalog for DM reference.
    Supports both exact matching and semantic search (RL-144).
    """
    from sqlalchemy import func, or_, select

    from app.db.models.item_catalog import ItemCatalog

    query_text = args.get("query")
    category = args.get("category")
    rarity = args.get("rarity")
    limit = args.get("limit", 10)
    use_semantic = args.get("semantic", False)

    if not query_text:
        return {
            "success": False,
            "error": "query is required",
        }

    # RL-144: Use semantic search if requested
    if use_semantic:
        from app.services.semantic_search_service import get_semantic_search_service

        logger.info(f"RL-144: Using semantic search for items: '{query_text}'")
        semantic_service = get_semantic_search_service()

        results = await semantic_service.search_items(
            query=query_text,
            db=db,
            limit=limit,
            category=category,
            rarity=rarity,
        )

        if not results:
            return {
                "success": True,
                "items": [],
                "message": f"No items found matching '{query_text}' (semantic search)",
            }

        # Format message
        message_lines = [f"🔍 **Found {len(results)} item(s) matching '{query_text}' (semantic):**\n"]
        for item in results[:5]:
            message_lines.append(
                f"• **{item['name']}** ({item['category']}, {item['rarity']}) - similarity: {item['similarity']}"
            )
        if len(results) > 5:
            message_lines.append(f"... and {len(results) - 5} more")

        return {
            "success": True,
            "items": results,
            "total": len(results),
            "message": "\n".join(message_lines),
            "search_type": "semantic",
        }

    # Original exact matching logic

    # Build query
    stmt = select(ItemCatalog)

    # Search by name or description
    search_term = f"%{query_text.lower()}%"
    stmt = stmt.where(
        or_(
            func.lower(ItemCatalog.name).like(search_term),
            func.lower(ItemCatalog.description).like(search_term),
        )
    )

    # Apply filters
    if category:
        stmt = stmt.where(func.lower(ItemCatalog.category) == func.lower(category))

    if rarity:
        stmt = stmt.where(func.lower(ItemCatalog.rarity).like(f"%{rarity.lower()}%"))

    # Execute query with limit
    stmt = stmt.limit(min(limit, 50)).order_by(ItemCatalog.name)
    result = await db.execute(stmt)
    items = result.scalars().all()

    if not items:
        return {
            "success": True,
            "items": [],
            "message": f"No items found matching '{query_text}'",
        }

    # Format results
    item_list = []
    for item in items:
        item_info = {
            "name": item.name,
            "category": item.category,
            "rarity": item.rarity,
        }

        # Add relevant stats based on category
        if item.is_weapon():
            item_info["damage"] = (
                f"{item.damage_dice} {item.damage_type}" if item.damage_dice else "N/A"
            )
            if item.attack_bonus:
                item_info["attack_bonus"] = f"+{item.attack_bonus}"

        if item.is_armor():
            if item.ac_base:
                item_info["ac"] = item.ac_base
            elif item.ac_bonus:
                item_info["ac_bonus"] = f"+{item.ac_bonus}"

        # Add description (truncated)
        if item.description:
            item_info["description"] = (
                item.description[:150] + "..." if len(item.description) > 150 else item.description
            )

        item_list.append(item_info)

    logger.info(f"Search '{query_text}' returned {len(items)} items")

    # Format message
    message_lines = [f"🔍 **Found {len(items)} item(s) matching '{query_text}':**\n"]
    for item_info in item_list[:5]:  # Show first 5 in message
        message_lines.append(
            f"• **{item_info['name']}** ({item_info['category']}, {item_info['rarity']})"
        )

    if len(items) > 5:
        message_lines.append(f"... and {len(items) - 5} more")

    return {
        "success": True,
        "items": item_list,
        "total": len(items),
        "message": "\n".join(message_lines),
        "search_type": "exact",
    }


async def _execute_search_monsters(
    args: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Search the creature database for DM reference (RL-144).
    Supports both exact matching and semantic search.
    """
    from sqlalchemy import func, or_, select

    from app.db.models.creature import Creature

    query_text = args.get("query")
    creature_type = args.get("creature_type")
    limit = args.get("limit", 10)
    use_semantic = args.get("semantic", False)

    if not query_text:
        return {
            "success": False,
            "error": "query is required",
        }

    # RL-144: Use semantic search if requested
    if use_semantic:
        from app.services.semantic_search_service import get_semantic_search_service

        logger.info(f"RL-144: Using semantic search for monsters: '{query_text}'")
        semantic_service = get_semantic_search_service()

        results = await semantic_service.search_monsters(
            query=query_text,
            db=db,
            limit=limit,
            creature_type=creature_type,
        )

        if not results:
            return {
                "success": True,
                "creatures": [],
                "message": f"No creatures found matching '{query_text}' (semantic search)",
            }

        # Format message
        message_lines = [f"🐉 **Found {len(results)} creature(s) matching '{query_text}' (semantic):**\n"]
        for creature in results[:5]:
            message_lines.append(
                f"• **{creature['name']}** ({creature['creature_type']}, CR {creature['cr']}) - AC {creature['ac']}, HP {creature['hp']} - similarity: {creature['similarity']}"
            )
        if len(results) > 5:
            message_lines.append(f"... and {len(results) - 5} more")

        return {
            "success": True,
            "creatures": results,
            "total": len(results),
            "message": "\n".join(message_lines),
            "search_type": "semantic",
        }

    # Exact matching logic
    stmt = select(Creature)

    # Search by name or type
    search_term = f"%{query_text.lower()}%"
    stmt = stmt.where(
        or_(
            func.lower(Creature.name).like(search_term),
            func.lower(Creature.creature_type).like(search_term),
        )
    )

    # Apply filters
    if creature_type:
        stmt = stmt.where(
            func.lower(Creature.creature_type).contains(func.lower(creature_type))
        )

    # Execute query with limit
    stmt = stmt.limit(min(limit, 50)).order_by(Creature.name)
    result = await db.execute(stmt)
    creatures = result.scalars().all()

    if not creatures:
        return {
            "success": True,
            "creatures": [],
            "message": f"No creatures found matching '{query_text}'",
        }

    # Format results
    creature_list = []
    for creature in creatures:
        creature_info = {
            "name": creature.name,
            "creature_type": creature.creature_type,
            "size": creature.size,
            "cr": creature.cr,
            "ac": creature.ac,
            "hp": creature.hp,
            "alignment": creature.alignment,
        }
        creature_list.append(creature_info)

    logger.info(f"Search '{query_text}' returned {len(creatures)} creatures")

    # Format message
    message_lines = [f"🐉 **Found {len(creatures)} creature(s) matching '{query_text}':**\n"]
    for creature_info in creature_list[:5]:
        message_lines.append(
            f"• **{creature_info['name']}** ({creature_info['creature_type']}, CR {creature_info['cr']}) - AC {creature_info['ac']}, HP {creature_info['hp']}"
        )
    if len(creatures) > 5:
        message_lines.append(f"... and {len(creatures) - 5} more")

    return {
        "success": True,
        "creatures": creature_list,
        "total": len(creatures),
        "message": "\n".join(message_lines),
        "search_type": "exact",
    }


async def _execute_search_spells(
    args: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Search the spell database for DM reference (RL-144).
    Supports both exact matching and semantic search.
    """
    from sqlalchemy import func, or_, select

    from app.db.models.spell import Spell

    query_text = args.get("query")
    spell_level = args.get("spell_level")
    school = args.get("school")
    limit = args.get("limit", 10)
    use_semantic = args.get("semantic", False)

    if not query_text:
        return {
            "success": False,
            "error": "query is required",
        }

    # RL-144: Use semantic search if requested
    if use_semantic:
        from app.services.semantic_search_service import get_semantic_search_service

        logger.info(f"RL-144: Using semantic search for spells: '{query_text}'")
        semantic_service = get_semantic_search_service()

        results = await semantic_service.search_spells(
            query=query_text,
            db=db,
            limit=limit,
            spell_level=spell_level,
            school=school,
        )

        if not results:
            return {
                "success": True,
                "spells": [],
                "message": f"No spells found matching '{query_text}' (semantic search)",
            }

        # Format message
        message_lines = [f"✨ **Found {len(results)} spell(s) matching '{query_text}' (semantic):**\n"]
        for spell in results[:5]:
            level_text = "Cantrip" if spell['level'] == 0 else f"Level {spell['level']}"
            message_lines.append(
                f"• **{spell['name']}** ({level_text}, {spell['school']}) - {spell['casting_time']}, {spell['range']} - similarity: {spell['similarity']}"
            )
        if len(results) > 5:
            message_lines.append(f"... and {len(results) - 5} more")

        return {
            "success": True,
            "spells": results,
            "total": len(results),
            "message": "\n".join(message_lines),
            "search_type": "semantic",
        }

    # Exact matching logic
    stmt = select(Spell)

    # Search by name or description
    search_term = f"%{query_text.lower()}%"
    stmt = stmt.where(
        or_(
            func.lower(Spell.name).like(search_term),
            func.lower(Spell.description).like(search_term),
        )
    )

    # Apply filters
    if spell_level is not None:
        stmt = stmt.where(Spell.level == spell_level)
    if school:
        stmt = stmt.where(func.lower(Spell.school) == func.lower(school))

    # Execute query with limit
    stmt = stmt.limit(min(limit, 50)).order_by(Spell.level, Spell.name)
    result = await db.execute(stmt)
    spells = result.scalars().all()

    if not spells:
        return {
            "success": True,
            "spells": [],
            "message": f"No spells found matching '{query_text}'",
        }

    # Format results
    spell_list = []
    for spell in spells:
        spell_info = {
            "name": spell.name,
            "level": spell.level,
            "school": str(spell.school),
            "casting_time": str(spell.casting_time),
            "range": spell.range,
            "duration": spell.duration,
            "description": spell.description[:150] + "..."
            if len(spell.description) > 150
            else spell.description,
            "damage_type": spell.damage_type,
            "is_concentration": spell.is_concentration,
        }
        spell_list.append(spell_info)

    logger.info(f"Search '{query_text}' returned {len(spells)} spells")

    # Format message
    message_lines = [f"✨ **Found {len(spells)} spell(s) matching '{query_text}':**\n"]
    for spell_info in spell_list[:5]:
        level_text = "Cantrip" if spell_info['level'] == 0 else f"Level {spell_info['level']}"
        message_lines.append(
            f"• **{spell_info['name']}** ({level_text}, {spell_info['school']}) - {spell_info['casting_time']}, {spell_info['range']}"
        )
    if len(spells) > 5:
        message_lines.append(f"... and {len(spells) - 5} more")

    return {
        "success": True,
        "spells": spell_list,
        "total": len(spells),
        "message": "\n".join(message_lines),
        "search_type": "exact",
    }


async def _execute_search_memories(
    args: dict[str, Any],
    character: Character,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Search adventure memories using vector similarity.
    Enables DM to recall past events semantically.

    REFACTORED: Now uses centralized SemanticSearchService (RL-144)
    """
    from app.services.semantic_search_service import get_semantic_search_service

    query_text = args.get("query")
    limit = args.get("limit", 5)

    if not query_text:
        return {"success": False, "error": "query is required"}

    try:
        # Use centralized semantic search service
        semantic_service = get_semantic_search_service()

        memory_list = await semantic_service.search_memories(
            query=query_text,
            db=db,
            character_id=character.id,
            limit=limit,
        )

        if not memory_list:
            return {
                "success": True,
                "memories": [],
                "message": f"No memories found for '{query_text}'",
            }

        logger.info(f"Memory search '{query_text}' returned {len(memory_list)} results")

        # Format message
        message_lines = [f"🧠 **Found {len(memory_list)} memory(ies) for '{query_text}':**\n"]
        for i, mem in enumerate(memory_list[:3], 1):
            message_lines.append(f"{i}. {mem['content']}")

        if len(memory_list) > 3:
            message_lines.append(f"... and {len(memory_list) - 3} more")

        return {
            "success": True,
            "memories": memory_list,
            "total": len(memory_list),
            "message": "\n".join(message_lines),
        }

    except Exception as e:
        logger.error(f"Error searching memories: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to search memories: {str(e)}",
        }


async def _execute_get_monster_loot(
    args: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Get appropriate loot for defeating a monster.
    Uses ContentLinker to generate loot based on monster CR.
    RL-145: Content Cross-Reference System
    """
    from app.services.content_linker import get_content_linker

    monster_name = args.get("monster_name")
    quantity = args.get("quantity", 3)

    if not monster_name:
        return {"success": False, "error": "monster_name is required"}

    try:
        content_linker = get_content_linker()
        items = await content_linker.get_monster_equipment(
            monster_name=monster_name,
            db=db,
            limit=quantity,
        )

        if not items:
            return {
                "success": True,
                "items": [],
                "message": f"⚔️ No loot found for '{monster_name}'. Try searching for the monster first.",
            }

        logger.info(f"RL-145: Generated {len(items)} loot items for {monster_name}")

        # Format message
        message_lines = [f"⚔️ **Loot from {monster_name}:**\n"]
        for i, item in enumerate(items[:5], 1):
            damage = f" ({item['damage_dice']} {item['damage_type']})" if item.get('damage_dice') else ""
            ac = f" (AC {item['ac_base']})" if item.get('ac_base') else ""
            ac_bonus = f" (+{item['ac_bonus']} AC)" if item.get('ac_bonus') else ""

            message_lines.append(
                f"{i}. **{item['name']}** ({item['rarity']})" + damage + ac + ac_bonus
            )

        if len(items) > 5:
            message_lines.append(f"... and {len(items) - 5} more items")

        return {
            "success": True,
            "items": items,
            "total": len(items),
            "message": "\n".join(message_lines),
        }

    except Exception as e:
        logger.error(f"RL-145: Error getting monster loot: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to get monster loot: {str(e)}",
        }


async def _execute_generate_treasure_hoard(
    args: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Generate random treasure hoard based on encounter CR.
    Uses ContentLinker to generate appropriate loot for encounter difficulty.
    RL-145: Content Cross-Reference System
    """
    from app.services.content_linker import get_content_linker

    challenge_rating = args.get("challenge_rating")
    num_items = args.get("num_items", 5)
    include_consumables = args.get("include_consumables", True)

    if challenge_rating is None:
        return {"success": False, "error": "challenge_rating is required"}

    try:
        cr = float(challenge_rating)
        content_linker = get_content_linker()

        items = await content_linker.generate_loot_table(
            encounter_cr=cr,
            db=db,
            num_items=num_items,
            include_consumables=include_consumables,
        )

        if not items:
            return {
                "success": True,
                "items": [],
                "message": f"💎 No treasure found for CR {cr} encounter.",
            }

        logger.info(f"RL-145: Generated {len(items)} treasure items for CR {cr}")

        # Determine rarity descriptor
        if cr <= 4:
            descriptor = "common"
        elif cr <= 10:
            descriptor = "uncommon"
        elif cr <= 16:
            descriptor = "rare"
        elif cr <= 20:
            descriptor = "very rare"
        else:
            descriptor = "legendary"

        # Format message
        message_lines = [f"💎 **Treasure Hoard (CR {cr} - {descriptor}):**\n"]
        for i, item in enumerate(items, 1):
            value = f" ({item['value_gp']} gp)" if item.get('value_gp') else ""
            message_lines.append(
                f"{i}. **{item['name']}** ({item['rarity']})" + value
            )

        return {
            "success": True,
            "items": items,
            "total": len(items),
            "challenge_rating": cr,
            "rarity_level": descriptor,
            "message": "\n".join(message_lines),
        }

    except ValueError:
        return {
            "success": False,
            "error": f"Invalid challenge_rating: {challenge_rating}. Must be a number.",
        }
    except Exception as e:
        logger.error(f"RL-145: Error generating treasure hoard: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to generate treasure hoard: {str(e)}",
        }
