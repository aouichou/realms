#!/usr/bin/env python3
"""
Import creatures from creatures_master.csv into the database.
Run this after migrating the database to populate creature data.

Usage:
    python scripts/import_creatures.py
"""

import asyncio
import csv
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import async_session
from app.db.models.creature import Creature


def parse_speed(speed_walk: str, speed_fly: str, speed_swim: str) -> dict:
    """
    Parse speed fields into JSONB format.
    Handles "N/S" (Not Specified) values.
    """
    speed = {}

    if speed_walk and speed_walk.strip() and speed_walk != "N/S":
        speed["walk"] = speed_walk.strip()

    if speed_fly and speed_fly.strip() and speed_fly != "N/S":
        speed["fly"] = speed_fly.strip()

    if speed_swim and speed_swim.strip() and speed_swim != "N/S":
        speed["swim"] = speed_swim.strip()

    return speed if speed else None


def clean_field(value: str) -> str | None:
    """
    Clean CSV field value.
    - Remove extra whitespace
    - Convert "NONE", "N/S", "DNE" to None
    - Return None for empty strings
    """
    if not value:
        return None

    value = value.strip()

    if value.upper() in ["NONE", "N/S", "DNE", ""]:
        return None

    return value


def parse_integer(value: str) -> int | None:
    """Parse integer from string, handling None/empty values."""
    value = clean_field(value)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


async def import_creatures(csv_path: Path, session: AsyncSession):
    """
    Import creatures from CSV file into database.
    """
    print(f"Reading creatures from {csv_path}...")

    creatures_imported = 0
    creatures_skipped = 0
    errors = []

    with open(csv_path, "r", encoding="utf-8-sig") as f:  # utf-8-sig removes BOM
        # CSV is semicolon-delimited, has header row
        reader = csv.DictReader(f, delimiter=";")

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is line 1)
            try:
                # Strip whitespace from keys and values
                row = {k.strip(): v for k, v in row.items()}

                # Extract and clean fields
                name = clean_field(row.get("name"))

                if not name:
                    print(f"⚠️  Row {row_num}: Skipping creature with no name")
                    creatures_skipped += 1
                    continue

                # Check if creature already exists
                result = await session.execute(select(Creature).where(Creature.name == name))
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"⏭️  Row {row_num}: '{name}' already exists, skipping")
                    creatures_skipped += 1
                    continue

                # Parse speed into JSONB
                speed = parse_speed(
                    row.get("speed_walk", ""), row.get("speed_fly", ""), row.get("speed_swim", "")
                )

                # Create creature instance
                creature = Creature(
                    name=name,
                    size=clean_field(row.get("size")),
                    creature_type=clean_field(
                        row.get("creature_type ")
                    ),  # Note trailing space in CSV!
                    alignment=clean_field(row.get("Alignment")),
                    ac=parse_integer(row.get("Ac ")),  # Note trailing space
                    armor_type=clean_field(row.get("armor_type ")),
                    hp=parse_integer(row.get("Hp ")),
                    hit_dice=clean_field(row.get("hit_dice ")),
                    speed=speed,
                    strength=parse_integer(row.get("Str ")),
                    dexterity=parse_integer(row.get("Dex ")),
                    constitution=parse_integer(row.get("Con ")),
                    intelligence=parse_integer(row.get("Int ")),
                    wisdom=parse_integer(row.get("Wis ")),
                    charisma=parse_integer(row.get("Cha ")),
                    saving_throws=clean_field(row.get("saving_throws ")),
                    skills=clean_field(row.get("Skills ")),
                    damage_resistances=clean_field(row.get("damage_resistances ")),
                    damage_immunities=clean_field(row.get("damage_immunities ")),
                    condition_immunities=clean_field(row.get("condition_immunities ")),
                    senses=clean_field(row.get("Senses ")),
                    languages=clean_field(row.get("Languages ")),
                    cr=clean_field(row.get("CR")),
                    xp=clean_field(row.get("XP_or_treasure_reference (X or X,Y)")),
                    actions=clean_field(row.get("Actions ")),
                    legendary_actions=clean_field(row.get("legendary_actions ")),
                    traits=clean_field(row.get("traits_feats_reactions ")),
                    dc=parse_integer(row.get("DC")),
                    source=clean_field(row.get("Source")),
                )

                session.add(creature)
                creatures_imported += 1

                if creatures_imported % 50 == 0:
                    await session.commit()
                    print(f"✅ Imported {creatures_imported} creatures so far...")

            except Exception as e:
                error_msg = f"Row {row_num} ('{row.get('name', 'UNKNOWN')}'): {str(e)}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")
                continue

    # Final commit
    await session.commit()

    # Print summary
    print("\n" + "=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)
    print(f"✅ Creatures imported: {creatures_imported}")
    print(f"⏭️  Creatures skipped: {creatures_skipped}")
    print(f"❌ Errors: {len(errors)}")

    if errors:
        print("\nERROR DETAILS:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")

    print("=" * 60)

    return creatures_imported, creatures_skipped, errors


async def main():
    """Main import function."""
    csv_path = Path(__file__).parent.parent / "data" / "creatures_master.csv"

    if not csv_path.exists():
        print(f"❌ Error: {csv_path} not found!")
        print("Please ensure creatures_master.csv exists in backend/data/")
        sys.exit(1)

    print("🎲 Realms Creature Import Tool")
    print("=" * 60)

    async with async_session() as session:
        imported, skipped, errors = await import_creatures(csv_path, session)

    if errors:
        print("\n⚠️  Import completed with errors. Review the error log above.")
        sys.exit(1)
    else:
        print("\n🎉 Import completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
