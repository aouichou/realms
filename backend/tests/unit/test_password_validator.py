"""Tests for app.core.password_validator — NIST/OWASP password policy."""

from app.core.password_validator import (
    MAX_LENGTH,
    MIN_CATEGORIES,
    MIN_LENGTH,
    validate_password,
)

# ── valid password ───────────────────────────────────────────────────────


def test_valid_password_returns_empty_list():
    errors = validate_password("Str0ng!Passw0rd#2026")
    assert errors == []


# ── length checks ────────────────────────────────────────────────────────


def test_too_short():
    errors = validate_password("Ab1!")  # 4 chars, far below 12
    assert any("at least" in e and str(MIN_LENGTH) in e for e in errors)


def test_too_long():
    pwd = "Aa1!" + "x" * 200  # well over 128
    errors = validate_password(pwd)
    assert any("exceed" in e.lower() or str(MAX_LENGTH) in e for e in errors)


def test_edge_case_exactly_min_length():
    """A 12-char password meeting all other rules should be valid."""
    pwd = "Abcdef1!ghij"  # exactly 12 chars, 4 categories
    errors = validate_password(pwd)
    # Should NOT have length error
    assert not any("at least" in e for e in errors)


# ── character diversity ──────────────────────────────────────────────────


def test_missing_character_diversity():
    """Only lowercase + digits = 2 categories, need 3."""
    pwd = "abcdefghij12"  # 12 chars, 2 categories
    errors = validate_password(pwd)
    assert any("at least" in e and str(MIN_CATEGORIES) in e for e in errors)


def test_three_categories_is_enough():
    """Lowercase + uppercase + digit = 3 categories — enough."""
    pwd = "Abcdefghij12"  # 12 chars, 3 categories (lower, upper, digit)
    # Filter to only the diversity error
    errors = validate_password(pwd)
    diversity_errors = [e for e in errors if "categories" in e.lower() or "diversity" in e.lower()]
    assert diversity_errors == []


def test_all_four_categories_valid():
    pwd = "Abcdefgh1!jk"  # 12 chars, all 4 categories
    errors = validate_password(pwd)
    diversity_errors = [e for e in errors if "categories" in e.lower()]
    assert diversity_errors == []


# ── common / blocklisted passwords ───────────────────────────────────────


def test_common_password_blocked():
    for common in ("password", "123456"):
        errors = validate_password(common)
        assert any("common" in e.lower() or "guessable" in e.lower() for e in errors)


def test_common_password_with_substitutions():
    """'p@ssw0rd' normalises to 'password' after leet-speak reversal."""
    errors = validate_password("p@ssw0rd")
    # Should trigger either common or "similar to common" error
    assert any("common" in e.lower() or "similar" in e.lower() for e in errors)


# ── keyboard walks ───────────────────────────────────────────────────────


def test_keyboard_walk_blocked():
    errors = validate_password("qwerty")
    assert any("keyboard" in e.lower() for e in errors)


# ── sequential characters ───────────────────────────────────────────────


def test_sequential_chars_detected():
    """Passwords with 3+ sequential chars should be flagged."""
    pwd = "MyP@ssabc9012"  # contains "abc"
    errors = validate_password(pwd)
    assert any("sequential" in e.lower() for e in errors)


# ── repeated characters ─────────────────────────────────────────────────


def test_repeated_chars_detected():
    """3+ identical chars in a row should be flagged."""
    pwd = "MyP@ssaaaxyz1"  # contains "aaa"
    errors = validate_password(pwd)
    assert any("repeated" in e.lower() for e in errors)


# ── username / email checks ─────────────────────────────────────────────


def test_username_in_password():
    errors = validate_password("MyStr0ng!alice99", username="alice")
    assert any("username" in e.lower() for e in errors)


def test_email_local_in_password():
    errors = validate_password("MyStr0ng!bob99!!", email="bob99@example.com")
    assert any("email" in e.lower() for e in errors)


def test_short_username_not_checked():
    """Usernames shorter than 3 chars are ignored (too many false positives)."""
    # "ab" is < 3 chars, so should NOT trigger username-in-password check
    errors = validate_password("Str0ng!Passw0rd#ab", username="ab")
    username_errors = [e for e in errors if "username" in e.lower()]
    assert username_errors == []
