#!/usr/bin/env python3
"""
Database Seeding Script - Master Seeder

Coordinates all database seeding operations:
- Spells from dnd-spells.csv (554 D&D 5e SRD spells)
- (Future: NPCs/Monsters)

Can be run standalone or called from Alembic migrations.

Usage:
    python scripts/seed_database.py
    python scripts/seed_database.py --force  # Force re-seed
"""

import asyncio
import csv
import json
import logging
import sys
import uuid
from argparse import ArgumentParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.db.base import async_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_components(verbal_col, somatic_col, material_col):
    """Parse component flags from CSV"""
    verbal = verbal_col == "1"
    somatic = somatic_col == "1"
    material = "Required" if material_col == "1" else None
    return verbal, somatic, material


def map_classes(classes_str):
    """Map comma-separated class string to JSONB dict"""
    all_cls = [
        "wizard",
        "sorcerer",
        "cleric",
        "druid",
        "bard",
        "warlock",
        "paladin",
        "ranger",
        "artificer",
    ]
    available = [c.strip().lower() for c in classes_str.split(",")]
    return {cls: cls in available for cls in all_cls}


def normalize_casting_time(time_str):
    """Map CSV casting times to DB enum values"""
    mapping = {
        "1 Action": "1 action",
        "1 Bonus Action": "1 bonus action",
        "1 Reaction": "1 reaction",
        "1 Minute": "1 minute",
        "10 Minutes": "10 minutes",
        "1 Hour": "1 hour",
        "8 Hours": "1 hour",  # Fallback
        "12 Hours": "1 hour",  # Fallback
        "24 Hours": "1 hour",  # Fallback
    }
    return mapping.get(time_str, "1 action")


async def seed_spells(force=False):
    """
    Seed spells from dnd-spells.csv

    Args:
        force: If True, delete existing spells and re-seed
    """
    logger.info("=== Seeding Spells ===")

    csv_path = Path(__file__).parent.parent / "data" / "dnd-spells.csv"

    if not csv_path.exists():
        logger.error(f"CSV not found: {csv_path}")
        return False

    logger.info(f"Loading from {csv_path.name}")

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            spells_data = list(csv.DictReader(f))
    except Exception as e:
        logger.error(f"Failed to read CSV: {e}")
        return False

    logger.info(f"Found {len(spells_data)} spells in CSV")

    async with async_session() as db:
        try:
            # Check if spells already exist
            result = await db.execute(text("SELECT COUNT(*) FROM spells"))
            existing_count = result.scalar()

            if existing_count > 0:
                if not force:
                    logger.info(f"✅ Already have {existing_count} spells (use --force to re-seed)")
                    return True
                else:
                    logger.warning(f"Force mode: deleting {existing_count} existing spells")
                    await db.execute(text("DELETE FROM spells"))
                    await db.commit()

            logger.info("Importing spells...")
            imported = 0
            errors = 0

            for idx, row in enumerate(spells_data, 1):
                try:
                    verbal, somatic, material = parse_components(
                        row.get("verbal", "0"),
                        row.get("somatic", "0"),
                        row.get("material", "0"),
                    )

                    # Use material_cost if provided, truncate to 200 chars
                    if row.get("material_cost"):
                        material = row["material_cost"][:200]
                    elif material:
                        material = material[:200]

                    classes_dict = map_classes(row.get("classes", ""))
                    is_conc = "concentration" in row.get("duration", "").lower()

                    await db.execute(
                        text("""
                            INSERT INTO spells (
                                id, name, level, school, casting_time, range, duration,
                                verbal, somatic, material, description, is_concentration,
                                is_ritual, available_to_classes, material_consumed, created_at
                            ) VALUES (
                                :id, :name, :level, :school, :casting_time, :range, :duration,
                                :verbal, :somatic, :material, :description, :is_concentration,
                                :is_ritual, :available_to_classes, :material_consumed, NOW()
                            )
                        """),
                        {
                            "id": uuid.uuid4(),
                            "name": row["name"].strip(),
                            "level": int(row["level"]),
                            "school": row.get("school", "Evocation").strip(),
                            "casting_time": normalize_casting_time(
                                row.get("cast_time", "1 Action")
                            ),
                            "range": row.get("range", "Self").strip(),
                            "duration": row.get("duration", "Instantaneous").strip(),
                            "verbal": verbal,
                            "somatic": somatic,
                            "material": material,
                            "description": " ".join(row.get("description", "").split()),
                            "is_concentration": is_conc,
                            "is_ritual": False,
                            "available_to_classes": json.dumps(classes_dict),
                            "material_consumed": False,
                        },
                    )
                    imported += 1

                    if imported % 100 == 0:
                        logger.info(f"  ... {imported}/{len(spells_data)}")
                        await db.flush()

                except Exception as e:
                    errors += 1
                    logger.warning(f"  ⚠️  Failed to import '{row.get('name', '?')}': {e}")
                    if errors > 10:
                        logger.error("Too many errors, aborting")
                        await db.rollback()
                        return False

            await db.commit()
            logger.info(f"✅ Imported {imported} spells ({errors} errors)")
            return True

        except Exception as e:
            logger.error(f"Database error: {e}")
            await db.rollback()
            return False


async def seed_all(force=False):
    """Run all seeding operations"""
    logger.info("=" * 70)
    logger.info("DATABASE SEEDING")
    logger.info("=" * 70)

    success = True

    # Seed spells
    if not await seed_spells(force=force):
        success = False

    # TODO: Add monster seeding here
    # if not await seed_monsters(force=force):
    #     success = False

    logger.info("=" * 70)
    if success:
        logger.info("✅ Seeding completed successfully")
    else:
        logger.error("❌ Seeding completed with errors")

    return success


def main():
    """CLI entry point"""
    parser = ArgumentParser(description="Seed database with D&D data")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-seed even if data exists",
    )
    args = parser.parse_args()

    result = asyncio.run(seed_all(force=args.force))
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
