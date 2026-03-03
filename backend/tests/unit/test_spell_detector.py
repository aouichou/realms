"""Tests for app.utils.spell_detector – Levenshtein distance and fuzzy spell matching."""

from app.utils.spell_detector import find_closest_spell, levenshtein_distance

# ── levenshtein_distance ──────────────────────────────────────────────────


def test_levenshtein_identical_strings():
    assert levenshtein_distance("Fireball", "Fireball") == 0


def test_levenshtein_single_insert():
    # "cat" → "cats" requires one insertion
    assert levenshtein_distance("cat", "cats") == 1


def test_levenshtein_single_delete():
    # "cats" → "cat" requires one deletion
    assert levenshtein_distance("cats", "cat") == 1


def test_levenshtein_single_substitution():
    # "cat" → "bat" requires one substitution
    assert levenshtein_distance("cat", "bat") == 1


def test_levenshtein_completely_different():
    d = levenshtein_distance("abc", "xyz")
    assert d == 3


def test_levenshtein_empty_string():
    assert levenshtein_distance("", "hello") == 5
    assert levenshtein_distance("hello", "") == 5
    assert levenshtein_distance("", "") == 0


# ── find_closest_spell ───────────────────────────────────────────────────


def test_find_closest_spell_exact_match():
    spells = ["Fireball", "Magic Missile", "Shield"]
    assert find_closest_spell("Fireball", spells) == "Fireball"


def test_find_closest_spell_one_typo():
    spells = ["Fireball", "Magic Missile", "Shield"]
    result = find_closest_spell("Firebll", spells)
    assert result == "Fireball"


def test_find_closest_spell_too_different():
    spells = ["Fireball", "Magic Missile", "Shield"]
    result = find_closest_spell("Earthquake", spells, max_distance=2)
    assert result is None


def test_find_closest_spell_empty_list():
    result = find_closest_spell("Fireball", [])
    assert result is None
