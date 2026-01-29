"""
Import spells from JSON into spells table.
Expands the existing spell database with 5k+ spells from comprehensive D&D dataset.
"""

import asyncio
import json
import logging
import re
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.models.enums import CastingTime, SpellSchool
from app.db.models.spell import Spell

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_spell_level(properties: dict) -> int:
    """Extract spell level from properties."""
    level = properties.get("Level", 0)
    if isinstance(level, int):
        return level
    try:
        return int(level)
    except (ValueError, TypeError):
        return 0


def parse_school(properties: dict) -> SpellSchool:
    """Parse spell school from properties."""
    school = properties.get("School", "evocation").lower()

    # Map to SpellSchool enum
    school_map = {
        "abjuration": SpellSchool.ABJURATION,
        "conjuration": SpellSchool.CONJURATION,
        "divination": SpellSchool.DIVINATION,
        "enchantment": SpellSchool.ENCHANTMENT,
        "evocation": SpellSchool.EVOCATION,
        "illusion": SpellSchool.ILLUSION,
        "necromancy": SpellSchool.NECROMANCY,
        "transmutation": SpellSchool.TRANSMUTATION,
    }

    return school_map.get(school, SpellSchool.EVOCATION)


def parse_casting_time(properties: dict) -> CastingTime:
    """Parse casting time from properties."""
    casting = properties.get("Casting Time", "1 action").lower()

    # Map to CastingTime enum
    if "bonus action" in casting:
        return CastingTime.BONUS_ACTION
    elif "reaction" in casting:
        return CastingTime.REACTION
    elif "minute" in casting:
        if "10" in casting:
            return CastingTime.TEN_MINUTES
        return CastingTime.MINUTE
    elif "hour" in casting:
        return CastingTime.HOUR
    else:
        return CastingTime.ACTION


def parse_components(properties: dict) -> tuple[bool, bool, str | None]:
    """Parse spell components (V, S, M) from properties."""
    components = properties.get("Components", "")

    verbal = "V" in components
    somatic = "S" in components
    material = None

    # Extract material components
    if "M" in components:
        # Try to find material description in parentheses
        mat_match = re.search(r"M\s*\(([^)]+)\)", components)
        if mat_match:
            material = mat_match.group(1)[:200]  # Limit to 200 chars
        else:
            material = "Material component required"

    return verbal, somatic, material


def extract_damage_info(description: str, properties: dict) -> tuple[str | None, str | None]:
    """Extract damage dice and type from description."""
    damage_type = properties.get("Damage Type", "").lower()
    if not damage_type:
        damage_type = None

    # Try to find damage dice in description
    damage_dice = None
    dice_match = re.search(r"(\d+d\d+(?:\s*\+\s*\d+)?)", description)
    if dice_match:
        damage_dice = dice_match.group(1).replace(" ", "")

    return damage_dice, damage_type


def parse_range(properties: dict) -> str:
    """Parse spell range from properties."""
    range_val = properties.get("data-RangeAoe", properties.get("Range", "Self"))
    return str(range_val)[:50]


def parse_duration(description: str, properties: dict) -> str:
    """Parse spell duration from description."""
    # Try to extract duration from description
    duration_match = re.search(r"Duration[:\s]+([^.\n]+)", description, re.IGNORECASE)
    if duration_match:
        return duration_match.group(1).strip()[:50]
    return "Instantaneous"


async def import_spells():
    """Import spells from JSON file into spells database."""
    # Load JSON data
    json_path = Path(__file__).parent.parent / "data" / "spells.json"

    if not json_path.exists():
        logger.error(f"Spells JSON file not found: {json_path}")
        return

    logger.info(f"Loading spells from {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        spells_data = json.load(f)

    logger.info(f"Loaded {len(spells_data)} spells from JSON")

    # Create database engine
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Check existing spells
        result = await db.execute(select(Spell))
        existing_spells = {spell.name.lower(): spell for spell in result.scalars().all()}

        logger.info(f"Found {len(existing_spells)} existing spells in database")

        added = 0
        skipped = 0
        errors = 0
        name_counts = {}  # Track duplicate names

        for idx, spell_data in enumerate(spells_data, 1):
            try:
                base_name = spell_data.get("name", "").strip()

                if not base_name:
                    logger.warning(f"Skipping spell {idx}: No name")
                    skipped += 1
                    continue

                # Handle duplicate names by adding source suffix
                name = base_name
                name_lower = name.lower()

                # If this name has been seen before, add a suffix
                if name_lower in name_counts:
                    name_counts[name_lower] += 1
                    publisher = spell_data.get("publisher", "")
                    book = spell_data.get("book", "")
                    suffix = (
                        f" ({publisher[:15]})"
                        if publisher
                        else f" ({book[:15]})"
                        if book
                        else f" (v{name_counts[name_lower]})"
                    )
                    name = f"{base_name}{suffix}"
                else:
                    name_counts[name_lower] = 1

                # Skip if already in database
                if name.lower() in existing_spells:
                    skipped += 1
                    continue

                description = spell_data.get("description", "")
                props = spell_data.get("properties", {})

                # Parse spell properties
                level = parse_spell_level(props)
                school = parse_school(props)
                casting_time = parse_casting_time(props)
                verbal, somatic, material = parse_components(props)
                damage_dice, damage_type = extract_damage_info(description, props)
                range_val = parse_range(props)
                duration = parse_duration(description, props)

                # Check for concentration and ritual
                is_concentration = "concentration" in description.lower()
                is_ritual = (
                    "ritual" in description.lower()
                    or "ritual" in props.get("Casting Time", "").lower()
                )

                # Create spell
                spell = Spell(
                    id=uuid.uuid4(),
                    name=name[:100],
                    level=level,
                    school=school,
                    casting_time=casting_time,
                    range=range_val,
                    duration=duration,
                    verbal=verbal,
                    somatic=somatic,
                    material=material,
                    description=description[:5000],  # Limit to 5000 chars
                    is_concentration=is_concentration,
                    is_ritual=is_ritual,
                    damage_dice=damage_dice,
                    damage_type=damage_type,
                )

                db.add(spell)
                added += 1

                # Add to existing_spells to catch duplicates in this import
                existing_spells[name.lower()] = spell

                if added % 1000 == 0:
                    logger.info(f"Progress: {added} spells added, {skipped} skipped")
                    try:
                        await db.commit()
                    except Exception as e:
                        logger.error(f"Error committing batch at {added} spells: {e}")
                        await db.rollback()
                        errors += 1000

            except Exception as e:
                logger.error(f"Error importing spell {idx} ({base_name}): {e}")
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
        logger.info(f"Total: {len(spells_data)}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(import_spells())
