"""
D&D 5e Spell Database Seeder

Imports spells from multiple data sources with intelligent duplicate detection
and data merging. Handles various CSV and JSON formats.

Data Sources:
- spells_5e.json: Clean JSON format with class arrays
- dnd-spells.csv: Comprehensive spell list with descriptions
- Class CSVs: Wizard.csv, Bard.csv, etc. (class-specific spell lists)

Usage:
    docker-compose exec backend python scripts/seed_spells.py
"""

import asyncio
import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, Set

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.db.base import async_session
from app.db.models import CastingTime, Spell, SpellSchool

# Valid D&D 5e classes
VALID_CLASSES = {
    "Artificer",
    "Bard",
    "Cleric",
    "Druid",
    "Paladin",
    "Ranger",
    "Sorcerer",
    "Warlock",
    "Wizard",
}

# School abbreviation mappings
SCHOOL_MAPPING = {
    "A": "Abjuration",
    "C": "Conjuration",
    "D": "Divination",
    "E": "Enchantment",
    "EV": "Evocation",
    "I": "Illusion",
    "N": "Necromancy",
    "T": "Transmutation",
}

# Casting time normalization
CASTING_TIME_MAPPING = {
    "1 action": CastingTime.ACTION,
    "1 bonus action": CastingTime.BONUS_ACTION,
    "1 reaction": CastingTime.REACTION,
    "1 minute": CastingTime.MINUTE,
    "10 minutes": CastingTime.TEN_MINUTES,
    "1 hour": CastingTime.HOUR,
    "1 minute (ritual)": CastingTime.RITUAL,
}


class SpellNormalizer:
    """Normalize spell data from various sources"""

    @staticmethod
    def normalize_school(school_str: str) -> SpellSchool:
        """Normalize school to SpellSchool enum"""
        school_str = school_str.strip()
        # Remove 'cantrip' suffix
        school_str = re.sub(r"\s*cantrip\s*$", "", school_str, flags=re.IGNORECASE)
        # Try abbreviation
        if school_str.upper() in SCHOOL_MAPPING:
            school_str = SCHOOL_MAPPING[school_str.upper()]

        # Match to enum
        school_str = school_str.capitalize()
        try:
            return SpellSchool(school_str)
        except ValueError:
            # Default to Evocation if unknown
            print(f"   ⚠️  Unknown school: {school_str}, defaulting to Evocation")
            return SpellSchool.EVOCATION

    @staticmethod
    def normalize_casting_time(time_str: str) -> CastingTime:
        """Normalize casting time to CastingTime enum"""
        time_str = time_str.strip().lower()

        # Try direct match
        for key, value in CASTING_TIME_MAPPING.items():
            if time_str == key.lower():
                return value

        # Try partial matches
        if "reaction" in time_str:
            return CastingTime.REACTION
        if "bonus" in time_str:
            return CastingTime.BONUS_ACTION
        if "hour" in time_str:
            return CastingTime.HOUR
        if "10 min" in time_str or "10min" in time_str:
            return CastingTime.TEN_MINUTES
        if "minute" in time_str:
            return CastingTime.MINUTE

        # Default to 1 action
        return CastingTime.ACTION

    @staticmethod
    def extract_level_from_string(level_str: str) -> int:
        """Extract spell level from strings like 'Evocation cantrip' or '3rd level'"""
        level_str = str(level_str).lower()
        if "cantrip" in level_str:
            return 0
        match = re.search(r"(\d+)", level_str)
        return int(match.group(1)) if match else 0

    @staticmethod
    def extract_classes(class_str: str) -> Set[str]:
        """Extract normalized class names from comma/semicolon-separated string"""
        if not class_str:
            return set()

        classes = set()
        # Split by comma or semicolon
        for cls in re.split(r"[,;]", class_str):
            cls = cls.strip()
            # Remove source info like "(TCE)"
            cls = re.sub(r"\s*\([^)]+\)\s*$", "", cls)
            cls = cls.strip().capitalize()
            if cls in VALID_CLASSES:
                classes.add(cls)

        return classes

    @staticmethod
    def parse_components(components_str: str) -> tuple:
        """Parse component string like 'V, S, M (herbs)' into booleans + material desc"""
        verbal = "V" in components_str
        somatic = "S" in components_str

        material_desc = None
        if "M" in components_str:
            match = re.search(r"\(([^)]+)\)", components_str)
            if match:
                material_desc = match.group(1)

        return verbal, somatic, material_desc

    @staticmethod
    def parse_duration(duration: str) -> tuple:
        """Extract concentration flag from duration"""
        concentration = "concentration" in duration.lower()
        # Clean duration
        duration = re.sub(r"concentration,?\s*", "", duration, flags=re.IGNORECASE).strip()
        return duration, concentration

    @staticmethod
    def clean_description(desc: str) -> str:
        """Remove HTML and normalize whitespace"""
        # Remove <br> tags
        desc = re.sub(r"<br\s*/?>", "\n", desc)
        # Remove other HTML
        desc = re.sub(r"<[^>]+>", "", desc)
        # Normalize whitespace
        desc = re.sub(r"\s+", " ", desc).strip()
        return desc


class SpellImporter:
    """Import spells from various data sources"""

    def __init__(self, db):
        self.db = db
        self.normalizer = SpellNormalizer()
        self.spell_cache: Dict[str, Spell] = {}  # name -> spell
        self.stats = {"processed": 0, "imported": 0, "duplicates": 0, "merged": 0, "errors": 0}

    async def load_existing_spells(self):
        """Load existing spells from database"""
        result = await self.db.execute(select(Spell))
        spells = result.scalars().all()
        self.spell_cache = {spell.name: spell for spell in spells}
        print(f"📚 Loaded {len(self.spell_cache)} existing spells")

    def get_or_create_spell(self, name: str) -> tuple:
        """Get existing or create new spell. Returns (spell, is_new)"""
        name = name.strip()
        if name in self.spell_cache:
            return self.spell_cache[name], False

        spell = Spell(name=name)
        self.spell_cache[name] = spell
        return spell, True

    async def import_from_json(self, file_path: Path):
        """Import from spells_5e.json"""
        print(f"\n🔮 Importing from {file_path.name}...")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        spells = data.get("spells", [])

        for spell_data in spells:
            try:
                self.stats["processed"] += 1
                name = spell_data.get("name", "").strip()
                if not name:
                    continue

                spell, is_new = self.get_or_create_spell(name)

                # Update fields
                spell.level = spell_data.get("level", 0)
                spell.school = self.normalizer.normalize_school(
                    spell_data.get("school", "Evocation")
                )
                spell.casting_time = self.normalizer.normalize_casting_time(
                    spell_data.get("casting_time", "1 action")
                )
                spell.range = spell_data.get("range", "Self")

                # Duration and concentration
                duration = spell_data.get("duration", "Instantaneous")
                spell.duration, spell.is_concentration = self.normalizer.parse_duration(duration)

                # Components
                components = spell_data.get("components", [])
                spell.verbal = "V" in components
                spell.somatic = "S" in components
                if "M" in components:
                    mat_desc = spell_data.get("material", "Material components")
                    # Truncate to 200 chars to fit database schema
                    spell.material = mat_desc[:200] if mat_desc else None

                # Description
                spell.description = self.normalizer.clean_description(
                    spell_data.get("description", "")
                )
                spell.is_ritual = spell_data.get("ritual", False)

                # Classes
                classes = spell_data.get("classes", [])
                if classes:
                    spell.available_to_classes = {
                        cls.lower(): True for cls in classes if cls in VALID_CLASSES
                    }

                if is_new:
                    self.db.add(spell)
                    self.stats["imported"] += 1
                else:
                    self.stats["merged"] += 1

            except Exception as e:
                print(f"   ⚠️  Error: {e}")
                self.stats["errors"] += 1

    async def import_from_csv(self, file_path: Path):
        """Import from dnd-spells.csv"""
        print(f"\n🔮 Importing from {file_path.name}...")

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    self.stats["processed"] += 1
                    name = row.get("name", "").strip()
                    if not name:
                        continue

                    spell, is_new = self.get_or_create_spell(name)

                    # Only update if not already set
                    if not spell.level:
                        spell.level = int(row.get("level", 0))

                    if not spell.school:
                        spell.school = self.normalizer.normalize_school(
                            row.get("school", "Evocation")
                        )

                    if not spell.casting_time:
                        spell.casting_time = self.normalizer.normalize_casting_time(
                            row.get("cast_time", "1 action")
                        )

                    if not spell.range:
                        spell.range = row.get("range", "Self")

                    if not spell.duration:
                        spell.duration = row.get("duration", "Instantaneous")

                    # Components
                    if not spell.verbal and not spell.somatic and not spell.material:
                        spell.verbal = bool(int(row.get("verbal", 0)))
                        spell.somatic = bool(int(row.get("somatic", 0)))
                        if bool(int(row.get("material", 0))):
                            mat_desc = row.get("material_cost", "Material components")
                            spell.material = mat_desc[:200] if mat_desc else None

                    # Description (prefer longer one)
                    csv_desc = self.normalizer.clean_description(row.get("description", ""))
                    if not spell.description or len(csv_desc) > len(spell.description):
                        spell.description = csv_desc

                    # Classes
                    classes_str = row.get("classes", "")
                    classes = self.normalizer.extract_classes(classes_str)
                    if classes:
                        if not spell.available_to_classes:
                            spell.available_to_classes = {}
                        for cls in classes:
                            spell.available_to_classes[cls.lower()] = True

                    if is_new:
                        self.db.add(spell)
                        self.stats["imported"] += 1
                    else:
                        self.stats["merged"] += 1

                except Exception as e:
                    print(f"   ⚠️  Error: {e}")
                    self.stats["errors"] += 1

    async def import_from_class_csv(self, file_path: Path, class_name: str):
        """Import from class-specific CSV"""
        print(f"\n🔮 Importing {class_name} spells from {file_path.name}...")

        with open(file_path, "r", encoding="utf-8") as f:
            # Handle BOM
            content = f.read()
            if content.startswith("\ufeff"):
                content = content[1:]

            lines = content.splitlines()
            reader = csv.reader(lines, delimiter=";")

            for row in reader:
                try:
                    if len(row) < 3:
                        continue

                    self.stats["processed"] += 1

                    name = row[1].strip() if len(row) > 1 else ""
                    if not name:
                        continue

                    spell, is_new = self.get_or_create_spell(name)

                    # Add class
                    if not spell.available_to_classes:
                        spell.available_to_classes = {}
                    spell.available_to_classes[class_name.lower()] = True

                    # Update fields if not set
                    if len(row) >= 3:
                        school_str = row[2].strip()
                        if not spell.school:
                            spell.level = self.normalizer.extract_level_from_string(school_str)
                            spell.school = self.normalizer.normalize_school(school_str)

                    if len(row) >= 4 and not spell.casting_time:
                        spell.casting_time = self.normalizer.normalize_casting_time(row[3].strip())

                    if len(row) >= 5 and not spell.range:
                        spell.range = row[4].strip()

                    if len(row) >= 6:
                        components = row[5].strip()
                        if not spell.verbal and not spell.somatic:
                            v, s, mat = self.normalizer.parse_components(components)
                            spell.verbal = v
                            spell.somatic = s
                            if mat:
                                spell.material = mat[:200] if mat else None

                    if len(row) >= 7 and not spell.duration:
                        dur, conc = self.normalizer.parse_duration(row[6].strip())
                        spell.duration = dur
                        spell.is_concentration = conc

                    if len(row) >= 8:
                        desc = self.normalizer.clean_description(row[7])
                        if not spell.description or len(desc) > len(spell.description):
                            spell.description = desc

                    if is_new:
                        self.db.add(spell)
                        self.stats["imported"] += 1
                    else:
                        self.stats["merged"] += 1

                except Exception as e:
                    print(f"   ⚠️  Error: {e}")
                    self.stats["errors"] += 1

    def print_stats(self):
        """Print import statistics"""
        print("\n" + "=" * 60)
        print("📊 IMPORT STATISTICS")
        print("=" * 60)
        print(f"  Total Processed:   {self.stats['processed']}")
        print(f"  ✅ Newly Imported:  {self.stats['imported']}")
        print(f"  🔄 Merged/Updated:  {self.stats['merged']}")
        print(f"  ⏭️  Skipped (Dupes):  {self.stats['duplicates']}")
        print(f"  ❌ Errors:          {self.stats['errors']}")
        print("=" * 60)
        print(f"  📚 Total Unique Spells: {len(self.spell_cache)}")
        print("=" * 60)


async def import_all_spells():
    """Main import function"""
    print("🧙 Starting D&D 5e Spell Import...")
    print("=" * 60)

    data_dir = Path(__file__).parent.parent / "data"

    async with async_session() as db:
        try:
            importer = SpellImporter(db)

            # Load existing
            await importer.load_existing_spells()

            # Import JSON
            json_file = data_dir / "spells_5e.json"
            if json_file.exists():
                await importer.import_from_json(json_file)
                await db.commit()

            # Import CSV
            csv_file = data_dir / "dnd-spells.csv"
            if csv_file.exists():
                await importer.import_from_csv(csv_file)
                await db.commit()

            # Import class CSVs
            class_files = {
                "Artificer": "Artificer.csv",
                "Bard": "Bard.csv",
                "Cleric": "Cleric.csv",
                "Druid": "Druid.csv",
                "Paladin": "Paladin.csv",
                "Ranger": "Ranger.csv",
                "Sorcerer": "Sorcerer.csv",
                "Warlock": "Warlock.csv",
                "Wizard": "Wizard.csv",
            }

            for class_name, filename in class_files.items():
                class_file = data_dir / filename
                if class_file.exists():
                    await importer.import_from_class_csv(class_file, class_name)
                    await db.commit()

            # Final commit
            await db.commit()

            # Stats
            importer.print_stats()

            print("\n✨ Spell import completed successfully!")

        except Exception as e:
            await db.rollback()
            print(f"\n❌ Import failed: {e}")
            import traceback

            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(import_all_spells())
