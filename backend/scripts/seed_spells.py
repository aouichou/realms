#!/usr/bin/env python3
"""
Spell Database Seeding Script

Seeds the spells table from dnd-spells.csv (554 D&D 5e SRD spells).
Automatically skips if spells already exist.

Usage:
    python scripts/seed_spells.py
"""

import asyncio
import csv
import json
import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.db.base import async_session

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def parse_components(v, s, m):
    verbal = v == "1"
    somatic = s == "1"
    material = "Required" if m == "1" else None
    return verbal, somatic, material


def map_classes(classes_str):
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
    avail = [c.strip().lower() for c in classes_str.split(",")]
    return {cls: cls in avail for cls in all_cls}


def normalize_casting_time(time_str):
    """Map CSV casting times to DB enum values"""
    mapping = {
        "1 Action": "1 action",
        "1 Bonus Action": "1 bonus action",
        "1 Reaction": "1 reaction",
        "1 Minute": "1 minute",
        "10 Minutes": "10 minutes",
        "1 Hour": "1 hour",
        "8 Hours": "1 hour",
        "12 Hours": "1 hour",
        "24 Hours": "1 hour",
    }
    return mapping.get(time_str, "1 action")


async def main():
    csv_path = Path("/app/data/dnd-spells.csv")

    if not csv_path.exists():
        print(f"❌ CSV not found")
        return

    print(f"📖 Loading spells...")

    with open(csv_path, "r", encoding="utf-8") as f:
        spells = list(csv.DictReader(f))

    print(f"   Found {len(spells)} spells")

    async with async_session() as db:
        result = await db.execute(text("SELECT COUNT(*) FROM spells"))
        existing = result.scalar()

        if existing > 0:
            print(f"✅ Already have {existing} spells")
            return

        print("🔄 Importing...")
        imported = 0

        for row in spells:
            verbal, somatic, material = parse_components(
                row.get("verbal", "0"), row.get("somatic", "0"), row.get("material", "0")
            )
            if row.get("material_cost"):
                material = row["material_cost"][:200]  # Truncate to fit DB constraint
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
                    "casting_time": normalize_casting_time(row.get("cast_time", "1 Action")),
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

            if imported % 200 == 0:
                print(f"   ... {imported}")
                await db.flush()

        await db.commit()
        print(f"✅ Imported {imported} spells!")


if __name__ == "__main__":
    asyncio.run(main())
