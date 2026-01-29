"""
Import monsters from JSON into creatures table.
Expands the existing creature database with 11k+ monsters from comprehensive D&D dataset.
"""

import asyncio
import json
import logging
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.models.creature import Creature

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_cr(properties: dict) -> str:
    """Extract Challenge Rating from properties."""
    cr = properties.get("Challenge Rating", "0")
    if isinstance(cr, (int, float)):
        return str(cr)
    return str(cr).strip()


def extract_stats_from_description(description: str) -> dict:
    """Extract creature stats from description text using regex patterns."""
    stats = {}

    # Try to extract AC
    ac_match = re.search(r"(?:AC|Armor Class)[:\s]+(\d+)", description, re.IGNORECASE)
    if ac_match:
        stats["ac"] = int(ac_match.group(1))

    # Try to extract HP
    hp_match = re.search(r"(?:HP|Hit Points)[:\s]+(\d+)", description, re.IGNORECASE)
    if hp_match:
        stats["hp"] = int(hp_match.group(1))

    # Try to extract ability scores
    str_match = re.search(r"STR[:\s]+(\d+)", description, re.IGNORECASE)
    dex_match = re.search(r"DEX[:\s]+(\d+)", description, re.IGNORECASE)
    con_match = re.search(r"CON[:\s]+(\d+)", description, re.IGNORECASE)
    int_match = re.search(r"INT[:\s]+(\d+)", description, re.IGNORECASE)
    wis_match = re.search(r"WIS[:\s]+(\d+)", description, re.IGNORECASE)
    cha_match = re.search(r"CHA[:\s]+(\d+)", description, re.IGNORECASE)

    if str_match:
        stats["strength"] = int(str_match.group(1))
    if dex_match:
        stats["dexterity"] = int(dex_match.group(1))
    if con_match:
        stats["constitution"] = int(con_match.group(1))
    if int_match:
        stats["intelligence"] = int(int_match.group(1))
    if wis_match:
        stats["wisdom"] = int(wis_match.group(1))
    if cha_match:
        stats["charisma"] = int(cha_match.group(1))

    return stats


async def import_monsters():
    """Import monsters from JSON file into creatures database."""
    # Load JSON data
    json_path = Path(__file__).parent.parent / "data" / "monsters.json"

    if not json_path.exists():
        logger.error(f"Monsters JSON file not found: {json_path}")
        return

    logger.info(f"Loading monsters from {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        monsters_data = json.load(f)

    logger.info(f"Loaded {len(monsters_data)} monsters from JSON")

    # Create database engine
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Check existing creatures
        result = await db.execute(select(Creature))
        existing_creatures = {
            creature.name.lower(): creature for creature in result.scalars().all()
        }

        logger.info(f"Found {len(existing_creatures)} existing creatures in database")

        added = 0
        skipped = 0
        errors = 0
        name_counts = {}  # Track duplicate names

        for idx, monster_data in enumerate(monsters_data, 1):
            try:
                base_name = monster_data.get("name", "").strip()

                if not base_name:
                    logger.warning(f"Skipping monster {idx}: No name")
                    skipped += 1
                    continue

                # Handle duplicate names by adding source suffix
                name = base_name
                name_lower = name.lower()

                # If this name has been seen before, add a suffix
                if name_lower in name_counts:
                    name_counts[name_lower] += 1
                    publisher = monster_data.get("publisher", "")
                    book = monster_data.get("book", "")
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
                if name.lower() in existing_creatures:
                    skipped += 1
                    continue

                description = monster_data.get("description", "")
                props = monster_data.get("properties", {})

                # Extract basic info
                size = props.get("Size", "Medium")
                creature_type = props.get("Type", "humanoid").lower()
                alignment = props.get("Alignment", "unaligned")
                cr = parse_cr(props)

                # Try to extract stats from description
                stats = extract_stats_from_description(description)

                # Create creature
                creature = Creature(
                    name=name,
                    size=size,
                    creature_type=creature_type,
                    alignment=alignment,
                    ac=stats.get("ac"),
                    hp=stats.get("hp"),
                    strength=stats.get("strength"),
                    dexterity=stats.get("dexterity"),
                    constitution=stats.get("constitution"),
                    intelligence=stats.get("intelligence"),
                    wisdom=stats.get("wisdom"),
                    charisma=stats.get("charisma"),
                    cr=cr,
                    actions=description[:5000],  # Store full description as actions
                    traits=description[:2000] if len(description) > 5000 else None,
                    source=f"{monster_data.get('publisher', 'Unknown')} - {monster_data.get('book', 'Unknown')}",
                )

                db.add(creature)
                added += 1

                # Add to existing_creatures to catch duplicates in this import
                existing_creatures[name.lower()] = creature

                if added % 1000 == 0:
                    logger.info(f"Progress: {added} monsters added, {skipped} skipped")
                    try:
                        await db.commit()
                    except Exception as e:
                        logger.error(f"Error committing batch at {added} monsters: {e}")
                        await db.rollback()
                        errors += 1000

            except Exception as e:
                logger.error(f"Error importing monster {idx} ({base_name}): {e}")
                errors += 1
                await db.rollback()

        # Final commit
        try:
            await db.commit()
        except Exception as e:
            logger.error(f"Error in final commit: {e}")
            await db.rollback()

        logger.info("\n=== Import Complete ===")
        logger.info(f"Added: {added}")
        logger.info(f"Skipped (duplicates): {skipped}")
        logger.info(f"Errors: {errors}")
        logger.info(f"Total: {len(monsters_data)}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(import_monsters())
