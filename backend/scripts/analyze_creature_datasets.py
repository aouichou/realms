#!/usr/bin/env python3
"""
Analyze creature CSV datasets to understand structure, quality, and gaps.
"""

import re
from collections import Counter, defaultdict
from pathlib import Path

# Monster CSV files
MONSTER_FILES = [
    "HotDQ.csv",
    "Lost Mine of Phandelver.csv",
    "Monsters_shadowfell.csv",
    "Out_of_the_Abyss.csv",
    "POTA.csv",
    "Ragnarok.csv",
    "RiseOfTiamat.csv",
    "Underdark (Black).csv",
    "Unique Monsters.csv",
    "DDEP4 Reclamation of Phlan - Tier 2.csv",
]

# Field indices based on CSV structure
FIELD_NAMES = [
    "name",
    "size_type",
    "alignment",
    "ac",
    "armor_type",
    "hp",
    "hit_dice",
    "speed",
    "str",
    "dex",
    "con",
    "int",
    "wis",
    "cha",
    "saving_throws",
    "skills",
    "damage_resistances",
    "damage_immunities",
    "condition_immunities",
    "senses",
    "languages",
    "cr",
    "xp",
    "description",
    "actions",
    "legendary_actions",
    "special_traits",
]


def parse_creature_line(line: str) -> dict:
    """Parse a single CSV line into creature data."""
    fields = line.strip().split(";")

    # Ensure we have at least the core fields
    while len(fields) < len(FIELD_NAMES):
        fields.append("")

    creature = {}
    for i, field_name in enumerate(FIELD_NAMES):
        creature[field_name] = fields[i].strip() if i < len(fields) else ""

    return creature


def analyze_datasets():
    """Comprehensive dataset analysis."""

    from scripts.data_utils import get_data_dir

    data_dir = get_data_dir()

    all_creatures = []
    creature_names = []
    file_stats = {}

    print("=" * 80)
    print("CREATURE DATASET ANALYSIS")
    print("=" * 80)
    print()

    # Read all datasets
    for filename in MONSTER_FILES:
        filepath = data_dir / filename

        if not filepath.exists():
            print(f"⚠️  {filename}: FILE NOT FOUND")
            continue

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = [line for line in f.readlines() if line.strip()]
        except Exception as e:
            print(f"❌ {filename}: ERROR reading file - {e}")
            continue

        creature_count = len(lines)
        file_stats[filename] = creature_count

        for line in lines:
            creature = parse_creature_line(line)
            creature["source_file"] = filename
            all_creatures.append(creature)
            creature_names.append(creature["name"])

        print(f"✅ {filename}: {creature_count} creatures")

    print()
    print(f"TOTAL: {len(all_creatures)} creatures across {len(MONSTER_FILES)} files")
    print()

    # Duplicate analysis
    print("=" * 80)
    print("DUPLICATE ANALYSIS")
    print("=" * 80)
    print()

    name_counts = Counter(creature_names)
    duplicates = {name: count for name, count in name_counts.items() if count > 1}

    if duplicates:
        print(f"Found {len(duplicates)} creatures appearing in multiple files:")
        print()
        for name, count in sorted(duplicates.items(), key=lambda x: -x[1])[:20]:
            print(f"  - {name}: {count} occurrences")
            sources = [c["source_file"] for c in all_creatures if c["name"] == name]
            print(f"    Sources: {', '.join(set(sources))}")

        if len(duplicates) > 20:
            print(f"  ... and {len(duplicates) - 20} more")
    else:
        print("No duplicates found.")

    print()
    unique_count = len(set(creature_names))
    print(f"UNIQUE creatures: {unique_count}")
    print(f"DUPLICATE entries: {len(all_creatures) - unique_count}")
    print()

    # Data quality analysis
    print("=" * 80)
    print("DATA QUALITY ANALYSIS")
    print("=" * 80)
    print()

    missing_fields = defaultdict(int)
    field_patterns = defaultdict(set)

    for creature in all_creatures:
        for field in FIELD_NAMES:
            value = creature.get(field, "")

            # Check for missing data
            if not value or value == "":
                missing_fields[field] += 1
            else:
                # Collect patterns for fields
                field_patterns[field].add(value[:100])  # Sample first 100 chars

    print("Missing/Empty Fields:")
    print()
    for field, count in sorted(missing_fields.items(), key=lambda x: -x[1]):
        percentage = (count / len(all_creatures)) * 100
        if percentage > 5:  # Only show fields missing in >5% of entries
            print(f"  - {field}: {count}/{len(all_creatures)} ({percentage:.1f}%)")

    print()

    # Challenge Rating distribution
    print("=" * 80)
    print("CHALLENGE RATING DISTRIBUTION")
    print("=" * 80)
    print()

    cr_counts = Counter([c["cr"] for c in all_creatures if c["cr"]])
    print("Top 20 CRs:")
    for cr, count in cr_counts.most_common(20):
        print(f"  CR {cr}: {count} creatures")

    print()

    # Creature type distribution
    print("=" * 80)
    print("CREATURE TYPE DISTRIBUTION")
    print("=" * 80)
    print()

    # Extract type from "size_type" field (e.g., "Medium humanoid")
    type_pattern = re.compile(r"(Tiny|Small|Medium|Large|Huge|Gargantuan)\s+(\w+)")
    type_counts = Counter()

    for creature in all_creatures:
        size_type = creature.get("size_type", "")
        match = type_pattern.search(size_type)
        if match:
            creature_type = match.group(2)
            type_counts[creature_type] += 1

    print("Creature Types:")
    for creature_type, count in type_counts.most_common():
        print(f"  - {creature_type}: {count}")

    print()

    # HTML formatting check
    print("=" * 80)
    print("HTML FORMATTING ANALYSIS")
    print("=" * 80)
    print()

    html_tags = defaultdict(int)

    for creature in all_creatures:
        for field in ["actions", "special_traits", "legendary_actions", "description"]:
            content = creature.get(field, "")
            if "<br>" in content:
                html_tags["<br>"] += 1
            if "<b>" in content or "<i>" in content:
                html_tags["<b>/<i>"] += 1

    print("HTML tags found in text fields:")
    for tag, count in html_tags.items():
        print(f"  - {tag}: {count} occurrences")

    print()

    # Data gap recommendations
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()

    print("ISSUES TO ADDRESS:")
    print()

    if duplicates:
        print(f"1. DUPLICATES: {len(duplicates)} creatures appear in multiple files")
        print("   → Implement deduplication strategy (prefer most complete entry)")
        print()

    if missing_fields:
        print("2. MISSING DATA:")
        for field, count in sorted(missing_fields.items(), key=lambda x: -x[1])[:5]:
            percentage = (count / len(all_creatures)) * 100
            if percentage > 10:
                print(f"   - {field}: {percentage:.1f}% empty")
        print(
            "   → Some fields are acceptable (e.g., legendary_actions for non-legendary creatures)"
        )
        print("   → Critical fields like name, cr, hp, abilities should not be empty")
        print()

    if html_tags:
        print("3. HTML FORMATTING:")
        print("   → Strip HTML tags (<br>, <b>, <i>) during import")
        print("   → Convert to plain text or Markdown")
        print()

    print("4. monsters.csv and Underdark Encounters v1.5.csv:")
    print("   → These files have 0 newlines (single-line dumps)")
    print("   → Need special parsing logic to handle them")
    print()

    print("DATABASE SCHEMA RECOMMENDATIONS:")
    print()
    print("- Primary table: creatures")
    print("  * Indexed fields: name, cr, creature_type, alignment")
    print("  * Full-text search: name, description, actions")
    print("  * JSONB fields: speed (variants), saves, skills, resistances, immunities")
    print()
    print("- Unique key: (name, cr) for deduplication")
    print("- Source tracking: source_file field for provenance")
    print()

    return {
        "total_creatures": len(all_creatures),
        "unique_creatures": unique_count,
        "duplicates": len(duplicates),
        "file_stats": file_stats,
    }


if __name__ == "__main__":
    analyze_datasets()
