"""
Character stats calculation utilities for D&D 5e.

These helper functions calculate derived stats from base character attributes
to provide the DM with accurate game mechanics information.
"""

from typing import Optional

from app.db.models import Character


def calculate_ability_modifier(ability_score: int) -> int:
    """
    Calculate ability modifier from ability score.

    D&D 5e formula: (ability_score - 10) // 2

    Examples:
        8 -> -1
        10 -> 0
        15 -> +2
        20 -> +5
    """
    return (ability_score - 10) // 2


def calculate_proficiency_bonus(level: int) -> int:
    """
    Calculate proficiency bonus based on character level.

    D&D 5e progression:
        Levels 1-4: +2
        Levels 5-8: +3
        Levels 9-12: +4
        Levels 13-16: +5
        Levels 17-20: +6
    """
    if level >= 17:
        return 6
    elif level >= 13:
        return 5
    elif level >= 9:
        return 4
    elif level >= 5:
        return 3
    else:
        return 2


def calculate_ac(character: Character) -> int:
    """
    Calculate Armor Class (AC).

    Basic calculation: 10 + DEX modifier

    TODO: Add support for:
        - Armor bonuses (leather, chain mail, plate, etc.)
        - Shield bonus (+2)
        - Class features (Barbarian Unarmored Defense, Monk Unarmored Defense, etc.)
        - Magical items
        - Active spells (Mage Armor, Shield of Faith, etc.)

    For now, returns base AC with DEX modifier.
    """
    base_ac = 10
    dex_modifier = calculate_ability_modifier(character.dexterity)

    # TODO: Query character items for armor and shields
    # TODO: Check for active effects that modify AC

    return base_ac + dex_modifier


def calculate_spell_dc(character: Character) -> int:
    """
    Calculate Spell Save DC.

    D&D 5e formula: 8 + proficiency bonus + spellcasting ability modifier

    Spellcasting ability by class:
        - Wizard, Artificer: Intelligence
        - Cleric, Druid, Ranger: Wisdom
        - Bard, Paladin, Sorcerer, Warlock: Charisma
    """
    proficiency = calculate_proficiency_bonus(character.level)

    # Determine spellcasting ability
    spellcasting_classes_int = ["wizard", "artificer"]
    spellcasting_classes_wis = ["cleric", "druid", "ranger"]
    spellcasting_classes_cha = ["bard", "paladin", "sorcerer", "warlock"]

    char_class = character.character_class.value.lower()

    if char_class in spellcasting_classes_int:
        ability_modifier = calculate_ability_modifier(character.intelligence)
    elif char_class in spellcasting_classes_wis:
        ability_modifier = calculate_ability_modifier(character.wisdom)
    elif char_class in spellcasting_classes_cha:
        ability_modifier = calculate_ability_modifier(character.charisma)
    else:
        # Non-spellcaster or unknown class, use highest mental stat
        ability_modifier = max(
            calculate_ability_modifier(character.intelligence),
            calculate_ability_modifier(character.wisdom),
            calculate_ability_modifier(character.charisma),
        )

    return 8 + proficiency + ability_modifier


def calculate_spell_attack_bonus(character: Character) -> int:
    """
    Calculate Spell Attack Bonus.

    D&D 5e formula: proficiency bonus + spellcasting ability modifier

    Uses same spellcasting ability as calculate_spell_dc().
    """
    proficiency = calculate_proficiency_bonus(character.level)

    # Determine spellcasting ability (same logic as spell DC)
    spellcasting_classes_int = ["wizard", "artificer"]
    spellcasting_classes_wis = ["cleric", "druid", "ranger"]
    spellcasting_classes_cha = ["bard", "paladin", "sorcerer", "warlock"]

    char_class = character.character_class.value.lower()

    if char_class in spellcasting_classes_int:
        ability_modifier = calculate_ability_modifier(character.intelligence)
    elif char_class in spellcasting_classes_wis:
        ability_modifier = calculate_ability_modifier(character.wisdom)
    elif char_class in spellcasting_classes_cha:
        ability_modifier = calculate_ability_modifier(character.charisma)
    else:
        # Non-spellcaster or unknown class, use highest mental stat
        ability_modifier = max(
            calculate_ability_modifier(character.intelligence),
            calculate_ability_modifier(character.wisdom),
            calculate_ability_modifier(character.charisma),
        )

    return proficiency + ability_modifier


def format_spell_slots(spell_slots: Optional[dict]) -> str:
    """
    Format spell slots for display.

    Args:
        spell_slots: Dict with format {"1": {"total": 4, "used": 2}, "2": {...}, ...}

    Returns:
        Formatted string like "Level 1: 2/4, Level 2: 3/3, Level 3: 0/2"
        or "No spell slots" if character is not a spellcaster.
    """
    if not spell_slots:
        return "No spell slots (non-spellcaster or cantrips only)"

    formatted_slots = []

    # Sort by spell level (1-9)
    for level in sorted([int(k) for k in spell_slots.keys() if k.isdigit()]):
        slot_info = spell_slots.get(str(level), {})
        total = slot_info.get("total", 0)
        used = slot_info.get("used", 0)
        remaining = total - used

        if total > 0:
            formatted_slots.append(f"Level {level}: {remaining}/{total}")

    return ", ".join(formatted_slots) if formatted_slots else "No spell slots available"


def format_ability_modifier(modifier: int) -> str:
    """
    Format ability modifier with proper sign.

    Examples:
        -1 -> "-1"
        0 -> "+0"
        +3 -> "+3"
    """
    if modifier >= 0:
        return f"+{modifier}"
    return str(modifier)


def build_character_stats_context(character: Character) -> str:
    """
    Build complete character stats context for DM.

    This provides all the information the DM needs to make
    informed game mechanic decisions.

    Args:
        character: Character instance

    Returns:
        Formatted stats context string
    """
    ac = calculate_ac(character)
    spell_dc = calculate_spell_dc(character)
    spell_attack = calculate_spell_attack_bonus(character)
    proficiency = calculate_proficiency_bonus(character.level)

    # Calculate all ability modifiers
    str_mod = calculate_ability_modifier(character.strength)
    dex_mod = calculate_ability_modifier(character.dexterity)
    con_mod = calculate_ability_modifier(character.constitution)
    int_mod = calculate_ability_modifier(character.intelligence)
    wis_mod = calculate_ability_modifier(character.wisdom)
    cha_mod = calculate_ability_modifier(character.charisma)

    stats_context = f"""
[CHARACTER STATS - Use these for accurate game mechanics]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name: {character.name}
Class: {character.character_class.value} (Level {character.level})
Race: {character.race.value}

COMBAT STATS:
• Armor Class (AC): {ac}
• Hit Points: {character.hp_current}/{character.hp_max}
• Proficiency Bonus: +{proficiency}

SPELLCASTING:
• Spell Save DC: {spell_dc}
• Spell Attack Bonus: +{spell_attack}
• Spell Slots: {format_spell_slots(character.spell_slots)}

ABILITY SCORES & MODIFIERS:
• STR: {character.strength} ({format_ability_modifier(str_mod)})
• DEX: {character.dexterity} ({format_ability_modifier(dex_mod)})
• CON: {character.constitution} ({format_ability_modifier(con_mod)})
• INT: {character.intelligence} ({format_ability_modifier(int_mod)})
• WIS: {character.wisdom} ({format_ability_modifier(wis_mod)})
• CHA: {character.charisma} ({format_ability_modifier(cha_mod)})

IMPORTANT RULES:
- When enemies attack, compare their roll + attack bonus to AC
- When player casts spell requiring save, enemies roll vs Spell Save DC
- When player uses ability/skill, add ability modifier + proficiency (if proficient)
- Spell slots are consumed when casting leveled spells (not cantrips)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".strip()

    return stats_context
