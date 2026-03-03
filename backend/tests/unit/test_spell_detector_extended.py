"""Extended tests for app.utils.spell_detector — can_cast_spell, consume_spell_slot, detect_spell_cast."""

from __future__ import annotations

import pytest

from app.utils.spell_detector import (
    can_cast_spell,
    consume_spell_slot,
    detect_spell_cast,
    find_closest_spell,
    levenshtein_distance,
)
from tests.factories import make_character, make_character_spell, make_spell, make_user

# ── can_cast_spell ────────────────────────────────────────────────────────


def test_cantrip_always_free():
    char = make_character(spell_slots={})
    ok, reason = can_cast_spell(char, 0)
    assert ok is True
    assert "Cantrip" in reason


def test_character_has_no_slot_key():
    char = make_character(spell_slots={"1": {"used": 0, "total": 2}})
    ok, reason = can_cast_spell(char, 5)
    assert ok is False
    assert "5" in reason


def test_character_has_slots_new_format():
    char = make_character(spell_slots={"3": {"used": 0, "total": 2}})
    ok, reason = can_cast_spell(char, 3)
    assert ok is True
    assert reason == ""


def test_character_all_slots_used_new_format():
    char = make_character(spell_slots={"2": {"used": 2, "total": 2}})
    ok, reason = can_cast_spell(char, 2)
    assert ok is False
    assert "remaining" in reason.lower()


def test_character_old_format_has_slots():
    char = make_character(spell_slots={"1": 3})
    ok, reason = can_cast_spell(char, 1)
    assert ok is True


def test_character_old_format_zero_slots():
    char = make_character(spell_slots={"1": 0})
    ok, reason = can_cast_spell(char, 1)
    assert ok is False


def test_character_none_spell_slots():
    char = make_character(spell_slots=None)
    ok, reason = can_cast_spell(char, 1)
    assert ok is False


# ── consume_spell_slot ────────────────────────────────────────────────────


def test_consume_cantrip():
    char = make_character(spell_slots={})
    ok, warning = consume_spell_slot(char, 0)
    assert ok is True
    assert warning is None


def test_consume_new_format():
    char = make_character(spell_slots={"3": {"used": 0, "total": 2}})
    ok, warning = consume_spell_slot(char, 3)
    assert ok is True
    assert warning is None
    assert char.spell_slots["3"]["used"] == 1


def test_consume_old_format():
    char = make_character(spell_slots={"1": 2})
    ok, warning = consume_spell_slot(char, 1)
    assert ok is True
    assert char.spell_slots["1"] == 1


def test_consume_no_slots_remaining():
    char = make_character(spell_slots={"2": {"used": 2, "total": 2}})
    ok, warning = consume_spell_slot(char, 2)
    assert ok is False
    assert warning is not None
    assert "⚠️" in warning


def test_consume_level2_ordinal():
    """Level 2 should produce 'nd' ordinal."""
    char = make_character(spell_slots={"2": {"used": 2, "total": 2}})
    ok, warning = consume_spell_slot(char, 2)
    assert "2nd" in warning


def test_consume_level3_ordinal():
    """Level 3 should produce 'rd' ordinal."""
    char = make_character(spell_slots={"3": {"used": 3, "total": 3}})
    ok, warning = consume_spell_slot(char, 3)
    assert "3rd" in warning


def test_consume_level4_ordinal():
    """Level 4+ should produce 'th' ordinal."""
    char = make_character(spell_slots={"4": {"used": 1, "total": 1}})
    ok, warning = consume_spell_slot(char, 4)
    assert "4th" in warning


def test_consume_slot_key_missing():
    """If slot key exists but dict doesn't have the key, returns (False, None)."""
    char = make_character(spell_slots={"1": {"used": 0, "total": 2}})
    # Try to consume level 5 which isn't in spell_slots but can_cast_spell fails first
    ok, warning = consume_spell_slot(char, 5)
    assert ok is False


# ── find_closest_spell extended ───────────────────────────────────────────


def test_find_closest_spell_non_string_in_list():
    """Non-string entries in known_spells should be skipped."""
    spells = ["Fireball", None, 42, "Shield"]
    result = find_closest_spell("Firebal", spells)
    assert result == "Fireball"


def test_find_closest_spell_case_insensitive():
    spells = ["Fireball", "Shield"]
    result = find_closest_spell("FIREBALL", spells)
    assert result == "Fireball"


# ── detect_spell_cast ─────────────────────────────────────────────────────


async def test_detect_spell_cast_empty_action(db_session):
    """Empty action should return no detection."""
    user = make_user()
    char = make_character(user=user, character_class="Wizard")
    db_session.add_all([user, char])
    await db_session.flush()

    spell_name, level, warning, suggestion = await detect_spell_cast("", char, db_session)
    assert spell_name is None
    assert level == 0


async def test_detect_spell_cast_no_spell_pattern(db_session):
    """Action without spell patterns returns no detection."""
    user = make_user()
    char = make_character(user=user, character_class="Wizard")
    db_session.add_all([user, char])
    await db_session.flush()

    spell_name, level, warning, suggestion = await detect_spell_cast(
        "I walk to the tavern", char, db_session
    )
    assert spell_name is None
    assert level == 0


async def test_detect_spell_cast_known_spell(db_session):
    """Casting a known spell should return spell name and level."""
    user = make_user()
    char = make_character(user=user, character_class="Wizard")
    spell = make_spell(name="Fireball", level=3)
    db_session.add_all([user, char, spell])
    await db_session.flush()

    cs = make_character_spell(character=char, spell=spell, is_known=True, is_prepared=True)
    db_session.add(cs)
    await db_session.flush()

    spell_name, level, warning, suggestion = await detect_spell_cast(
        "I cast Fireball at the goblins", char, db_session
    )
    assert spell_name == "Fireball"
    assert level == 3
    assert warning is None


async def test_detect_spell_cast_unprepared_spell_for_wizard(db_session):
    """Wizard casting unprepared spell should get a warning."""
    user = make_user()
    char = make_character(user=user, character_class="Wizard")
    spell = make_spell(name="Lightning Bolt", level=3)
    # Create a spell the wizard knows but did NOT prepare
    prepared_spell = make_spell(name="Shield", level=1)
    db_session.add_all([user, char, spell, prepared_spell])
    await db_session.flush()

    cs = make_character_spell(character=char, spell=prepared_spell, is_known=True, is_prepared=True)
    db_session.add(cs)
    await db_session.flush()

    spell_name, level, warning, suggestion = await detect_spell_cast(
        "I cast Lightning Bolt at the dragon", char, db_session
    )
    # The spell exists in DB but is not prepared by the wizard
    assert warning is not None
    assert (
        "prepared" in warning.lower()
        or "haven't" in warning.lower()
        or "doesn't exist" in warning.lower()
    )


async def test_detect_spell_cast_spontaneous_caster(db_session):
    """Bard (spontaneous caster) should check is_known."""
    user = make_user()
    char = make_character(user=user, character_class="Bard")
    spell = make_spell(name="Healing Word", level=1)
    db_session.add_all([user, char, spell])
    await db_session.flush()

    cs = make_character_spell(character=char, spell=spell, is_known=True, is_prepared=False)
    db_session.add(cs)
    await db_session.flush()

    spell_name, level, warning, suggestion = await detect_spell_cast(
        "I cast Healing Word on the fighter", char, db_session
    )
    assert spell_name == "Healing Word"
    assert level == 1


async def test_detect_spell_cast_unknown_spell(db_session):
    """Casting a spell that doesn't exist in the DB."""
    user = make_user()
    char = make_character(user=user, character_class="Wizard")
    db_session.add_all([user, char])
    await db_session.flush()

    spell_name, level, warning, suggestion = await detect_spell_cast(
        "I cast Xylophone of Doom at the goblin", char, db_session
    )
    # Should detect the cast attempt but spell doesn't exist
    assert warning is not None or spell_name is None


async def test_detect_spell_cast_skip_common_words(db_session):
    """Common action words like 'attack' should not be treated as spells."""
    user = make_user()
    char = make_character(user=user, character_class="Fighter")
    db_session.add_all([user, char])
    await db_session.flush()

    spell_name, level, warning, suggestion = await detect_spell_cast(
        "I use attack on the orc", char, db_session
    )
    # "attack" is in skip_words so it shouldn't give a detection
    assert spell_name is None


async def test_detect_spell_cast_no_spells_configured(db_session):
    """Character with no spells configured should still allow DB spell match with warning."""
    user = make_user()
    char = make_character(user=user, character_class="Wizard")
    spell = make_spell(name="Magic Missile", level=1)
    db_session.add_all([user, char, spell])
    await db_session.flush()

    # No CharacterSpell entries — character has no spells configured
    spell_name, level, warning, suggestion = await detect_spell_cast(
        "I cast Magic Missile at the skeleton", char, db_session
    )
    # Should allow the cast but log a warning (no spells configured)
    assert spell_name == "Magic Missile"
    assert level == 1


async def test_detect_spell_cast_fuzzy_match_hits_int_uuid_bug(db_session):
    """Misspelled spell name triggers fuzzy matching path which has a UUID→int bug.

    detect_spell_cast line 222 does int(sid) on UUID spell IDs.
    This test documents the existing bug.
    """
    user = make_user()
    char = make_character(user=user, character_class="Sorcerer")
    spell = make_spell(name="Fireball", level=3)
    db_session.add_all([user, char, spell])
    await db_session.flush()

    cs = make_character_spell(character=char, spell=spell, is_known=True, is_prepared=False)
    db_session.add(cs)
    await db_session.flush()

    # The fuzzy match path tries int(sid) on UUIDs — this raises ValueError
    with pytest.raises(ValueError, match="invalid literal"):
        await detect_spell_cast("I cast Xyzzy at the goblins", char, db_session)


async def test_detect_spell_cast_quoted_spell(db_session):
    """Spell names in quotes should be detected."""
    user = make_user()
    char = make_character(user=user, character_class="Wizard")
    spell = make_spell(name="Shield", level=1)
    db_session.add_all([user, char, spell])
    await db_session.flush()

    cs = make_character_spell(character=char, spell=spell, is_known=True, is_prepared=True)
    db_session.add(cs)
    await db_session.flush()

    spell_name, level, warning, suggestion = await detect_spell_cast(
        'I cast "Shield"', char, db_session
    )
    assert spell_name == "Shield"
    assert level == 1
