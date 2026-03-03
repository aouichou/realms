"""Tests for app.utils.dnd_rules — ASI, racial bonuses, skills, proficiency."""

import pytest

from app.utils.dnd_rules import (
    apply_asi_distribution,
    apply_racial_bonuses,
    calculate_asi_count,
    calculate_proficiency_bonus,
    get_skill_choices,
    validate_asi_distribution,
    validate_skill_selection,
)

# ── calculate_asi_count ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "level, expected",
    [
        (1, 0),
        (4, 1),
        (6, 2),
        (8, 3),
        (12, 4),
        (14, 5),
        (16, 6),
        (19, 7),
    ],
    ids=lambda v: f"lvl{v}",
)
def test_asi_count_fighter_extra_asis(level: int, expected: int):
    """Fighter gets extra ASIs at levels 6 and 14."""
    assert calculate_asi_count("Fighter", level) == expected


@pytest.mark.parametrize(
    "level, expected",
    [
        (1, 0),
        (4, 1),
        (8, 2),
        (12, 3),
        (16, 4),
        (19, 5),
    ],
    ids=lambda v: f"lvl{v}",
)
def test_asi_count_standard_class(level: int, expected: int):
    """Wizard (standard ASI schedule) gets ASIs at 4, 8, 12, 16, 19."""
    assert calculate_asi_count("Wizard", level) == expected


def test_asi_count_rogue_extra():
    """Rogue gets an extra ASI at level 10."""
    assert calculate_asi_count("Rogue", 10) == 3  # levels 4, 8, 10


# ── apply_racial_bonuses ─────────────────────────────────────────────────


def test_apply_racial_bonuses_human():
    """Human gets +1 to all ability scores."""
    base = {
        "strength": 10,
        "dexterity": 10,
        "constitution": 10,
        "intelligence": 10,
        "wisdom": 10,
        "charisma": 10,
    }
    result = apply_racial_bonuses(base, "Human")
    for ability in base:
        assert result[ability] == 11


def test_apply_racial_bonuses_dragonborn():
    """Dragonborn gets STR +2, CHA +1."""
    base = {
        "strength": 10,
        "dexterity": 10,
        "constitution": 10,
        "intelligence": 10,
        "wisdom": 10,
        "charisma": 10,
    }
    result = apply_racial_bonuses(base, "Dragonborn")
    assert result["strength"] == 12
    assert result["charisma"] == 11
    # Others unchanged
    assert result["dexterity"] == 10
    assert result["wisdom"] == 10


def test_apply_racial_bonuses_unknown_race():
    """Unknown race applies no bonuses."""
    base = {"strength": 10, "dexterity": 10}
    result = apply_racial_bonuses(base, "Aarakocra")
    assert result == base


# ── apply_asi_distribution ───────────────────────────────────────────────


def test_apply_asi_distribution_basic():
    base = {"strength": 14, "constitution": 12}
    asi = {"4": {"strength": 2}}
    result = apply_asi_distribution(base, asi)
    assert result["strength"] == 16
    assert result["constitution"] == 12


def test_apply_asi_distribution_capped_at_20():
    base = {"strength": 19}
    asi = {"4": {"strength": 2}}
    result = apply_asi_distribution(base, asi)
    assert result["strength"] == 20  # capped


# ── validate_asi_distribution ────────────────────────────────────────────


def test_validate_asi_distribution_valid():
    asi = {"4": {"strength": 1, "constitution": 1}}
    valid, msg = validate_asi_distribution(asi, "Fighter", 4)
    assert valid is True
    assert msg == ""


def test_validate_asi_distribution_invalid_level():
    """Level 5 is not a valid ASI level for Wizard."""
    asi = {"5": {"intelligence": 2}}
    valid, msg = validate_asi_distribution(asi, "Wizard", 5)
    assert valid is False
    assert "not a valid ASI level" in msg


def test_validate_asi_distribution_too_many_points():
    """Exceeding available ASI points."""
    # Fighter level 4 → 1 ASI = 2 points. Providing 2 ASIs → 4 points.
    asi = {
        "4": {"strength": 2},
        "6": {"constitution": 2},
    }
    valid, msg = validate_asi_distribution(asi, "Fighter", 4)
    # Level 6 ASI but character is only level 4
    assert valid is False


def test_validate_asi_distribution_wrong_points_per_level():
    """Each ASI must use exactly 2 points."""
    asi = {"4": {"strength": 1}}  # Only 1 point
    valid, msg = validate_asi_distribution(asi, "Fighter", 4)
    assert valid is False
    assert "exactly 2 points" in msg


def test_validate_asi_distribution_point_value_out_of_range():
    """Each individual ability increase must be +1 or +2."""
    asi = {"4": {"strength": 3}}  # 3 points to one ability
    valid, msg = validate_asi_distribution(asi, "Fighter", 4)
    assert valid is False


# ── get_skill_choices ────────────────────────────────────────────────────


def test_get_skill_choices_bard():
    info = get_skill_choices("Bard")
    assert info["count"] == 3
    assert info["choices"] == "any"


def test_get_skill_choices_fighter():
    info = get_skill_choices("Fighter")
    assert info["count"] == 2
    assert isinstance(info["choices"], list)
    assert "Athletics" in info["choices"]
    assert "Perception" in info["choices"]


# ── validate_skill_selection ─────────────────────────────────────────────


def test_validate_skill_selection_valid():
    valid, msg = validate_skill_selection(["Athletics", "Perception"], "Fighter")
    assert valid is True
    assert msg == ""


def test_validate_skill_selection_wrong_count():
    valid, msg = validate_skill_selection(["Athletics"], "Fighter")
    assert valid is False
    assert "must select 2 skills" in msg


def test_validate_skill_selection_duplicates():
    valid, msg = validate_skill_selection(["Athletics", "Athletics"], "Fighter")
    assert valid is False
    assert "same skill" in msg.lower() or "duplicate" in msg.lower()


def test_validate_skill_selection_invalid_skill():
    valid, msg = validate_skill_selection(["Athletics", "Cooking"], "Fighter")
    assert valid is False
    assert "Invalid skill" in msg


def test_validate_skill_selection_not_available_for_class():
    """Arcana is not available for Fighter."""
    valid, msg = validate_skill_selection(["Athletics", "Arcana"], "Fighter")
    assert valid is False
    assert "not available for Fighter" in msg


# ── calculate_proficiency_bonus (dnd_rules version) ──────────────────────


@pytest.mark.parametrize(
    "level, expected",
    [
        (1, 2),
        (5, 3),
        (9, 4),
        (13, 5),
        (17, 6),
    ],
    ids=lambda v: f"lvl{v}",
)
def test_proficiency_bonus_formula(level: int, expected: int):
    assert calculate_proficiency_bonus(level) == expected
