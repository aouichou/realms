"""Utility functions for D&D 5e rules calculations."""

# ASI levels for each class
ASI_LEVELS = {
    "Barbarian": [4, 8, 12, 16, 19],
    "Bard": [4, 8, 12, 16, 19],
    "Cleric": [4, 8, 12, 16, 19],
    "Druid": [4, 8, 12, 16, 19],
    "Fighter": [4, 6, 8, 12, 14, 16, 19],  # Fighter gets extra ASIs
    "Monk": [4, 8, 12, 16, 19],
    "Paladin": [4, 8, 12, 16, 19],
    "Ranger": [4, 8, 12, 16, 19],
    "Rogue": [4, 8, 10, 12, 16, 19],  # Rogue gets one extra ASI
    "Sorcerer": [4, 8, 12, 16, 19],
    "Warlock": [4, 8, 12, 16, 19],
    "Wizard": [4, 8, 12, 16, 19],
}

# Racial ability score bonuses
RACIAL_BONUSES = {
    "Dragonborn": {"strength": 2, "charisma": 1},
    "Dwarf": {"constitution": 2},  # Base dwarf, subrace adds more
    "Elf": {"dexterity": 2},  # Base elf, subrace adds more
    "Gnome": {"intelligence": 2},  # Base gnome, subrace adds more
    "Half-Elf": {"charisma": 2},  # Plus +1 to two other abilities (user choice)
    "Halfling": {"dexterity": 2},  # Base halfling, subrace adds more
    "Half-Orc": {"strength": 2, "constitution": 1},
    "Human": {
        "strength": 1,
        "dexterity": 1,
        "constitution": 1,
        "intelligence": 1,
        "wisdom": 1,
        "charisma": 1,
    },
    "Tiefling": {"intelligence": 1, "charisma": 2},
}

# Class skill options
CLASS_SKILLS = {
    "Barbarian": {
        "count": 2,
        "choices": [
            "Animal Handling",
            "Athletics",
            "Intimidation",
            "Nature",
            "Perception",
            "Survival",
        ],
    },
    "Bard": {
        "count": 3,
        "choices": "any",  # Bards can choose any 3 skills
    },
    "Cleric": {"count": 2, "choices": ["History", "Insight", "Medicine", "Persuasion", "Religion"]},
    "Druid": {
        "count": 2,
        "choices": [
            "Arcana",
            "Animal Handling",
            "Insight",
            "Medicine",
            "Nature",
            "Perception",
            "Religion",
            "Survival",
        ],
    },
    "Fighter": {
        "count": 2,
        "choices": [
            "Acrobatics",
            "Animal Handling",
            "Athletics",
            "History",
            "Insight",
            "Intimidation",
            "Perception",
            "Survival",
        ],
    },
    "Monk": {
        "count": 2,
        "choices": ["Acrobatics", "Athletics", "History", "Insight", "Religion", "Stealth"],
    },
    "Paladin": {
        "count": 2,
        "choices": ["Athletics", "Insight", "Intimidation", "Medicine", "Persuasion", "Religion"],
    },
    "Ranger": {
        "count": 3,
        "choices": [
            "Animal Handling",
            "Athletics",
            "Insight",
            "Investigation",
            "Nature",
            "Perception",
            "Stealth",
            "Survival",
        ],
    },
    "Rogue": {
        "count": 4,
        "choices": "any",  # Rogues can choose any 4 skills
    },
    "Sorcerer": {
        "count": 2,
        "choices": ["Arcana", "Deception", "Insight", "Intimidation", "Persuasion", "Religion"],
    },
    "Warlock": {
        "count": 2,
        "choices": [
            "Arcana",
            "Deception",
            "History",
            "Intimidation",
            "Investigation",
            "Nature",
            "Religion",
        ],
    },
    "Wizard": {
        "count": 2,
        "choices": ["Arcana", "History", "Insight", "Investigation", "Medicine", "Religion"],
    },
}

# All D&D 5e skills
ALL_SKILLS = [
    "Acrobatics",
    "Animal Handling",
    "Arcana",
    "Athletics",
    "Deception",
    "History",
    "Insight",
    "Intimidation",
    "Investigation",
    "Medicine",
    "Nature",
    "Perception",
    "Performance",
    "Persuasion",
    "Religion",
    "Sleight of Hand",
    "Stealth",
    "Survival",
]


def calculate_asi_count(character_class: str, level: int) -> int:
    """Calculate number of ASIs earned by level.

    Args:
        character_class: Character class name
        level: Character level (1-20)

    Returns:
        Number of ASIs earned (each ASI = 2 points to distribute)
    """
    asi_levels = ASI_LEVELS.get(character_class, ASI_LEVELS["Fighter"])
    return sum(1 for lvl in asi_levels if lvl <= level)


def apply_racial_bonuses(base_scores: dict, race: str) -> dict:
    """Apply racial ability score bonuses to base scores.

    Args:
        base_scores: Dictionary of base ability scores from point buy
        race: Character race

    Returns:
        Dictionary with racial bonuses applied
    """
    bonuses = RACIAL_BONUSES.get(race, {})
    result = base_scores.copy()

    for ability, bonus in bonuses.items():
        result[ability] = result.get(ability, 10) + bonus

    return result


def apply_asi_distribution(base_scores: dict, asi_distribution: dict, max_score: int = 20) -> dict:
    """Apply ASI distribution to ability scores.

    Args:
        base_scores: Dictionary of ability scores (after racial bonuses)
        asi_distribution: Dictionary mapping levels to ability increases
                         e.g., {"4": {"strength": 2}, "8": {"dexterity": 1, "constitution": 1}}
        max_score: Maximum allowed ability score (default 20)

    Returns:
        Dictionary with ASIs applied
    """
    result = base_scores.copy()

    for level, increases in asi_distribution.items():
        for ability, points in increases.items():
            current = result.get(ability, 10)
            new_score = min(current + points, max_score)
            result[ability] = new_score

    return result


def validate_asi_distribution(
    asi_distribution: dict, character_class: str, level: int
) -> tuple[bool, str]:
    """Validate ASI distribution for a character.

    Args:
        asi_distribution: Dictionary mapping levels to ability increases
        character_class: Character class
        level: Character level

    Returns:
        Tuple of (is_valid, error_message)
    """
    asi_count = calculate_asi_count(character_class, level)
    total_points_allowed = asi_count * 2

    total_points_used = 0
    for level_str, increases in asi_distribution.items():
        asi_level = int(level_str)

        # Check if ASI level is valid for this class
        if asi_level not in ASI_LEVELS.get(character_class, []):
            return False, f"Level {asi_level} is not a valid ASI level for {character_class}"

        # Check if ASI level is within character level
        if asi_level > level:
            return False, f"Cannot apply ASI from level {asi_level} (character is level {level})"

        # Count points used at this level
        level_points = sum(increases.values())

        # Each ASI grants 2 points (either +2 to one or +1 to two)
        if level_points != 2:
            return (
                False,
                f"Each ASI must use exactly 2 points (level {asi_level} uses {level_points})",
            )

        # Check that no single ability gets more than +2 at once
        for ability, points in increases.items():
            if points > 2 or points < 1:
                return (
                    False,
                    f"Each ability increase must be +1 or +2 (got {points} for {ability} at level {asi_level})",
                )

        total_points_used += level_points

    if total_points_used > total_points_allowed:
        return (
            False,
            f"Used {total_points_used} ASI points but only {total_points_allowed} are available",
        )

    return True, ""


def get_skill_choices(character_class: str) -> dict:
    """Get skill selection options for a class.

    Args:
        character_class: Character class name

    Returns:
        Dictionary with 'count' and 'choices' keys
    """
    return CLASS_SKILLS.get(character_class, {"count": 2, "choices": []})


def validate_skill_selection(skills: list, character_class: str) -> tuple[bool, str]:
    """Validate skill selection for a character.

    Args:
        skills: List of selected skill names
        character_class: Character class

    Returns:
        Tuple of (is_valid, error_message)
    """
    class_skills = CLASS_SKILLS.get(character_class)
    if not class_skills:
        return False, f"Unknown character class: {character_class}"

    required_count = class_skills["count"]
    allowed_choices = class_skills["choices"]

    # Check count
    if len(skills) != required_count:
        return False, f"{character_class} must select {required_count} skills (got {len(skills)})"

    # Check for duplicates
    if len(skills) != len(set(skills)):
        return False, "Cannot select the same skill multiple times"

    # Check if all skills are valid
    for skill in skills:
        if skill not in ALL_SKILLS:
            return False, f"Invalid skill: {skill}"

    # Check if skills are allowed for this class
    if allowed_choices != "any":
        for skill in skills:
            if skill not in allowed_choices:
                return False, f"{skill} is not available for {character_class}"

    return True, ""


def calculate_proficiency_bonus(level: int) -> int:
    """Calculate proficiency bonus for character level.

    Args:
        level: Character level (1-20)

    Returns:
        Proficiency bonus (+2 to +6)
    """
    return 2 + ((level - 1) // 4)
