"""Tests for app.utils.character_stats — pure D&D 5e stat calculations."""

import pytest

from app.db.models.enums import CharacterClass
from app.utils.character_stats import (
    build_character_stats_context,
    calculate_ability_modifier,
    calculate_ac,
    calculate_proficiency_bonus,
    calculate_spell_attack_bonus,
    calculate_spell_dc,
    format_ability_modifier,
    format_spell_slots,
)
from tests.factories import make_character

# ── calculate_ability_modifier ────────────────────────────────────────────


@pytest.mark.parametrize(
    "score, expected",
    [
        (1, -5),
        (8, -1),
        (10, 0),
        (11, 0),
        (12, 1),
        (15, 2),
        (20, 5),
        (30, 10),
    ],
    ids=lambda v: str(v),
)
def test_ability_modifier_boundary_values(score: int, expected: int):
    assert calculate_ability_modifier(score) == expected


# ── calculate_proficiency_bonus ───────────────────────────────────────────


@pytest.mark.parametrize(
    "level, expected",
    [
        (1, 2),
        (2, 2),
        (3, 2),
        (4, 2),
        (5, 3),
        (6, 3),
        (7, 3),
        (8, 3),
        (9, 4),
        (10, 4),
        (11, 4),
        (12, 4),
        (13, 5),
        (14, 5),
        (15, 5),
        (16, 5),
        (17, 6),
        (18, 6),
        (19, 6),
        (20, 6),
    ],
    ids=lambda v: f"lvl{v}",
)
def test_proficiency_bonus_per_level(level: int, expected: int):
    assert calculate_proficiency_bonus(level) == expected


# ── calculate_ac ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "dex, expected_ac",
    [
        (8, 9),  # 10 + (-1)
        (10, 10),  # 10 + 0
        (14, 12),  # 10 + 2
        (16, 13),  # 10 + 3
        (20, 15),  # 10 + 5
    ],
    ids=lambda v: str(v),
)
def test_ac_with_various_dex_scores(dex: int, expected_ac: int):
    char = make_character(dexterity=dex)
    assert calculate_ac(char) == expected_ac


# ── calculate_spell_dc ───────────────────────────────────────────────────


def test_spell_dc_for_intelligence_casters():
    """Wizard uses INT for spell DC: 8 + prof + INT mod."""
    char = make_character(
        character_class=CharacterClass.WIZARD,
        level=5,  # prof = +3
        intelligence=16,  # mod = +3
    )
    # 8 + 3 + 3 = 14
    assert calculate_spell_dc(char) == 14


@pytest.mark.parametrize(
    "cls",
    [CharacterClass.CLERIC, CharacterClass.DRUID, CharacterClass.RANGER],
    ids=lambda c: c.value,
)
def test_spell_dc_for_wisdom_casters(cls: CharacterClass):
    """Cleric, Druid, Ranger use WIS for spell DC."""
    char = make_character(
        character_class=cls,
        level=1,  # prof = +2
        wisdom=16,  # mod = +3
    )
    # 8 + 2 + 3 = 13
    assert calculate_spell_dc(char) == 13


@pytest.mark.parametrize(
    "cls",
    [
        CharacterClass.BARD,
        CharacterClass.PALADIN,
        CharacterClass.SORCERER,
        CharacterClass.WARLOCK,
    ],
    ids=lambda c: c.value,
)
def test_spell_dc_for_charisma_casters(cls: CharacterClass):
    """Bard, Paladin, Sorcerer, Warlock use CHA for spell DC."""
    char = make_character(
        character_class=cls,
        level=9,  # prof = +4
        charisma=18,  # mod = +4
    )
    # 8 + 4 + 4 = 16
    assert calculate_spell_dc(char) == 16


def test_spell_dc_for_non_spellcaster():
    """Fighter falls back to max(INT, WIS, CHA) modifier."""
    char = make_character(
        character_class=CharacterClass.FIGHTER,
        level=1,  # prof = +2
        intelligence=10,  # mod = 0
        wisdom=14,  # mod = +2  ← highest
        charisma=8,  # mod = -1
    )
    # 8 + 2 + 2 = 12
    assert calculate_spell_dc(char) == 12


# ── calculate_spell_attack_bonus ──────────────────────────────────────────


def test_spell_attack_bonus_wizard():
    char = make_character(
        character_class=CharacterClass.WIZARD,
        level=5,  # prof = +3
        intelligence=18,  # mod = +4
    )
    # 3 + 4 = 7
    assert calculate_spell_attack_bonus(char) == 7


def test_spell_attack_bonus_cleric():
    char = make_character(
        character_class=CharacterClass.CLERIC,
        level=1,  # prof = +2
        wisdom=16,  # mod = +3
    )
    # 2 + 3 = 5
    assert calculate_spell_attack_bonus(char) == 5


# ── format_spell_slots ───────────────────────────────────────────────────


def test_format_spell_slots_empty():
    assert "No spell slots" in format_spell_slots(None)
    assert "No spell slots" in format_spell_slots({})


def test_format_spell_slots_normal():
    slots = {"1": {"total": 4, "used": 2}}
    result = format_spell_slots(slots)
    assert "Level 1: 2/4" in result


def test_format_spell_slots_multiple_levels():
    slots = {
        "1": {"total": 4, "used": 1},
        "2": {"total": 3, "used": 0},
        "3": {"total": 2, "used": 2},
    }
    result = format_spell_slots(slots)
    assert "Level 1: 3/4" in result
    assert "Level 2: 3/3" in result
    assert "Level 3: 0/2" in result


# ── format_ability_modifier ──────────────────────────────────────────────


def test_format_ability_modifier_negative():
    assert format_ability_modifier(-1) == "-1"
    assert format_ability_modifier(-3) == "-3"


def test_format_ability_modifier_zero():
    assert format_ability_modifier(0) == "+0"


def test_format_ability_modifier_positive():
    assert format_ability_modifier(3) == "+3"
    assert format_ability_modifier(5) == "+5"


# ── build_character_stats_context ────────────────────────────────────────


def test_build_character_stats_context_contains_key_info():
    char = make_character(
        name="Gandalf",
        character_class=CharacterClass.WIZARD,
        level=10,
        strength=10,
        dexterity=14,
        constitution=12,
        intelligence=20,
        wisdom=16,
        charisma=11,
        hp_current=48,
        hp_max=62,
        spell_slots={"1": {"total": 4, "used": 0}},
    )
    ctx = build_character_stats_context(char)

    # Core info present
    assert "Gandalf" in ctx
    assert "Wizard" in ctx
    assert "Level 10" in ctx

    # Combat stats
    assert "AC" in ctx
    assert "48/62" in ctx  # HP
    assert "+4" in ctx  # proficiency bonus at level 10

    # Ability modifiers — INT 20 → +5
    assert "+5" in ctx

    # Spell slots
    assert "Level 1: 4/4" in ctx
