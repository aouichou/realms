"""
Import items from JSON dataset into item_catalog table.
Processes 15k+ D&D 5e items from comprehensive JSON file.
"""

import asyncio
import json
import logging
import re
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.models.item_catalog import ItemCatalog
from scripts.data_utils import get_data_path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_item_properties(item_data: dict) -> tuple[dict, dict]:
    """
    Parse item properties from JSON data.
    Returns (properties, requirements) dictionaries.
    """
    properties = {}
    requirements = {}

    props = item_data.get("properties", {})

    # Extract common properties
    if "Item Type" in props:
        item_type = props["Item Type"]
        properties["item_type_detailed"] = item_type

    if "Item Rarity" in props:
        properties["rarity_source"] = props["Item Rarity"]

    # Parse weapon properties
    if "Damage" in props:
        properties["damage"] = props["Damage"]

    if "Properties" in props:
        # Properties might be a string like "Finesse, Light, Thrown (range 20/60)"
        prop_str = props["Properties"]
        if isinstance(prop_str, str):
            # Parse thrown range
            thrown_match = re.search(r"Thrown.*?\(range (\d+)/(\d+)\)", prop_str, re.IGNORECASE)
            if thrown_match:
                properties["thrown"] = {
                    "normal": int(thrown_match.group(1)),
                    "long": int(thrown_match.group(2)),
                }

            # Parse other properties
            prop_list = [p.strip().lower() for p in prop_str.split(",")]
            for prop in [
                "finesse",
                "light",
                "heavy",
                "reach",
                "versatile",
                "loading",
                "ammunition",
            ]:
                if any(prop in p for p in prop_list):
                    properties[prop] = True

    # Parse armor properties
    if "Armor Class (AC)" in props:
        properties["ac_details"] = props["Armor Class (AC)"]

    # Store all original properties
    properties["raw"] = props

    return properties, requirements


def extract_damage_info(description: str, name: str) -> tuple[str | None, str | None]:
    """
    Extract damage dice and type from description.
    Returns (damage_dice, damage_type)
    """
    # Common damage dice patterns
    dice_pattern = r"(\d+d\d+(?:\s*\+\s*\d+)?)"
    damage_types = [
        "slashing",
        "piercing",
        "bludgeoning",
        "fire",
        "cold",
        "lightning",
        "thunder",
        "acid",
        "poison",
        "necrotic",
        "radiant",
        "force",
        "psychic",
    ]

    damage_dice = None
    damage_type = None

    # Try to find damage dice
    dice_match = re.search(dice_pattern, description)
    if dice_match:
        damage_dice = dice_match.group(1).replace(" ", "")

    # Try to find damage type
    desc_lower = description.lower()
    for dtype in damage_types:
        if dtype in desc_lower:
            damage_type = dtype
            break

    return damage_dice, damage_type


def extract_ac_info(description: str, name: str, props: dict) -> tuple[int | None, int | None]:
    """
    Extract AC base and bonus from description.
    Returns (ac_base, ac_bonus)
    """
    ac_base = None
    ac_bonus = None

    # Check for "+X Armor" pattern (magic armor)
    magic_armor_match = re.search(r"\+(\d+)\s+Armor", name, re.IGNORECASE)
    if magic_armor_match:
        ac_bonus = int(magic_armor_match.group(1))

    # Check for shield
    if "shield" in name.lower():
        # Most shields give +2 AC
        shield_match = re.search(r"\+(\d+)", name)
        if shield_match:
            ac_bonus = int(shield_match.group(1))
        else:
            ac_bonus = 2  # Default shield bonus

    # Check for armor AC in description
    ac_match = re.search(r"(?:AC|Armor Class)(?:\s+is)?\s+(\d+)", description, re.IGNORECASE)
    if ac_match:
        ac_base = int(ac_match.group(1))

    return ac_base, ac_bonus


def categorize_item(name: str, props: dict, description: str) -> tuple[str, str]:
    """
    Determine item category and type.
    Returns (category, item_type)
    """
    item_type_raw = props.get("Item Type", "").lower()
    name_lower = name.lower()

    # Weapons
    if "weapon" in item_type_raw or any(
        w in name_lower for w in ["sword", "axe", "mace", "dagger", "bow", "crossbow", "spear"]
    ):
        if "ranged" in item_type_raw:
            return "weapon", "ranged_weapon"
        elif "melee" in item_type_raw:
            return "weapon", "melee_weapon"
        else:
            return "weapon", "weapon"

    # Armor
    if "armor" in item_type_raw or any(
        a in name_lower for a in ["mail", "plate", "leather", "hide"]
    ):
        if "light" in description.lower():
            return "armor", "light_armor"
        elif "medium" in description.lower():
            return "armor", "medium_armor"
        elif "heavy" in description.lower():
            return "armor", "heavy_armor"
        else:
            return "armor", "armor"

    # Shield
    if "shield" in name_lower:
        return "shield", "shield"

    # Potions
    if "potion" in name_lower:
        return "potion", "potion"

    # Scrolls
    if "scroll" in name_lower:
        return "scroll", "scroll"

    # Wands/Rods/Staves
    if any(w in name_lower for w in ["wand", "rod", "staff", "orb"]):
        return "wondrous_item", "magical_focus"

    # Rings and Amulets
    if any(w in name_lower for w in ["ring", "amulet", "necklace", "bracelet"]):
        return "wondrous_item", "wearable"

    # Default
    return "item", "adventuring_gear"


async def import_items():
    """Import items from JSON file into database."""
    # Load JSON data
    try:
        json_path = get_data_path("items.json")
    except FileNotFoundError as e:
        logger.error(str(e))
        return

    logger.info(f"Loading items from {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        items_data = json.load(f)

    logger.info(f"Loaded {len(items_data)} items from JSON")

    # Create database engine
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Check existing items
        result = await db.execute(select(ItemCatalog))
        existing_items = {item.name.lower(): item for item in result.scalars().all()}

        logger.info(f"Found {len(existing_items)} existing items in database")

        added = 0
        skipped = 0
        errors = 0
        name_counts = {}  # Track duplicate names

        for idx, item_data in enumerate(items_data, 1):
            try:
                base_name = item_data.get("name", "").strip()

                if not base_name:
                    logger.warning(f"Skipping item {idx}: No name")
                    skipped += 1
                    continue

                # Handle duplicate names by adding source suffix
                name = base_name
                name_lower = name.lower()

                # If this name has been seen before, add a suffix
                if name_lower in name_counts:
                    name_counts[name_lower] += 1
                    # Add book/publisher suffix to make it unique
                    publisher = item_data.get("publisher", "")
                    book = item_data.get("book", "")
                    suffix = (
                        f" ({publisher[:20]})"
                        if publisher
                        else f" ({book[:20]})"
                        if book
                        else f" (variant {name_counts[name_lower]})"
                    )
                    name = f"{base_name}{suffix}"
                else:
                    name_counts[name_lower] = 1

                # Skip if already in database
                if name.lower() in existing_items:
                    skipped += 1
                    continue

                description = item_data.get("description", "")
                props = item_data.get("properties", {})

                # Categorize
                category, item_type = categorize_item(name, props, description)

                # Extract rarity
                rarity = props.get("Item Rarity", "common").lower()

                # Extract damage info for weapons
                damage_dice, damage_type = extract_damage_info(description, name)

                # Extract AC info for armor/shields
                ac_base, ac_bonus = extract_ac_info(description, name, props)

                # Extract attack/damage bonus from name (e.g., "+1 Longsword")
                attack_bonus = 0
                damage_bonus = 0
                magic_bonus_match = re.search(r"\+(\d+)", name)
                if magic_bonus_match and category in ("weapon", "armor"):
                    bonus = int(magic_bonus_match.group(1))
                    if category == "weapon":
                        attack_bonus = bonus
                        damage_bonus = bonus
                    elif category == "armor":
                        if ac_bonus is None:
                            ac_bonus = bonus

                # Parse properties
                properties, requirements = parse_item_properties(item_data)

                # Create item
                item = ItemCatalog(
                    name=name,
                    description=description[:2000],  # Truncate long descriptions
                    category=category,
                    item_type=item_type,
                    rarity=rarity,
                    ac_base=ac_base,
                    ac_bonus=ac_bonus,
                    damage_dice=damage_dice,
                    damage_type=damage_type,
                    attack_bonus=attack_bonus,
                    damage_bonus=damage_bonus,
                    properties=properties,
                    requirements=requirements,
                    cost_gp=0,  # Would need separate pricing data
                    weight_lbs=0.0,  # Would need separate weight data
                    publisher=item_data.get("publisher"),
                    book=item_data.get("book"),
                    expansion=props.get("Expansion"),
                    properties_raw=props,
                )

                db.add(item)
                added += 1

                # Add name to existing_items to catch duplicates in this import
                existing_items[name.lower()] = item

                if added % 1000 == 0:
                    logger.info(f"Progress: {added} items added, {skipped} skipped")
                    try:
                        await db.commit()
                    except Exception as e:
                        logger.error(f"Error committing batch at {added} items: {e}")
                        await db.rollback()
                        errors += 1000  # Assume all items in batch failed

            except Exception as e:
                logger.error(f"Error importing item {idx} ({base_name}): {e}")
                errors += 1
                await db.rollback()  # Roll back individual item error

        # Final commit
        try:
            await db.commit()
        except Exception as e:
            logger.error(f"Error in final commit: {e}")
            await db.rollback()

        logger.info(f"\n=== Import Complete ===")
        logger.info(f"Added: {added}")
        logger.info(f"Skipped (duplicates): {skipped}")
        logger.info(f"Errors: {errors}")
        logger.info(f"Total: {len(items_data)}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(import_items())
