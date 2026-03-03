"""Tests for app.utils.currency — D&D 5e currency operations."""

import pytest

from app.utils.currency import (
    CP_PER_GP,
    CP_PER_SP,
    SP_PER_GP,
    Currency,
    add_currency,
    convert_to_gold,
    format_price,
    subtract_currency,
)
from tests.factories import make_character

# ── Currency.to_copper ────────────────────────────────────────────────────


def test_currency_to_copper():
    assert Currency(gold=1, silver=2, copper=3).to_copper() == 123
    assert Currency(gold=0, silver=0, copper=0).to_copper() == 0
    assert Currency(gold=5, silver=0, copper=0).to_copper() == 500
    assert Currency(gold=0, silver=0, copper=7).to_copper() == 7


# ── Currency.to_gold_fractional ───────────────────────────────────────────


def test_currency_to_gold_fractional():
    assert Currency(gold=1, silver=5, copper=0).to_gold_fractional() == 1.5
    assert Currency(gold=0, silver=0, copper=50).to_gold_fractional() == 0.5
    assert Currency(gold=0, silver=0, copper=0).to_gold_fractional() == 0.0


# ── Currency.from_copper ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "copper_in, expected_g, expected_s, expected_c",
    [
        (0, 0, 0, 0),
        (1, 0, 0, 1),
        (99, 0, 9, 9),
        (100, 1, 0, 0),
        (255, 2, 5, 5),
    ],
    ids=["0cp", "1cp", "99cp", "100cp", "255cp"],
)
def test_currency_from_copper(copper_in: int, expected_g: int, expected_s: int, expected_c: int):
    c = Currency.from_copper(copper_in)
    assert c.gold == expected_g
    assert c.silver == expected_s
    assert c.copper == expected_c


# ── Currency.from_gold (fractional) ──────────────────────────────────────


def test_currency_from_gold_fractional():
    c = Currency.from_gold(1.5)
    assert c.gold == 1
    assert c.silver == 5
    assert c.copper == 0

    c2 = Currency.from_gold(0.05)
    assert c2.gold == 0
    assert c2.silver == 0
    assert c2.copper == 5


# ── Currency arithmetic ──────────────────────────────────────────────────


def test_currency_addition():
    a = Currency(gold=1, silver=5, copper=3)
    b = Currency(gold=0, silver=7, copper=8)
    result = a + b
    # 153 + 78 = 231 cp → 2 gp, 3 sp, 1 cp
    assert result.gold == 2
    assert result.silver == 3
    assert result.copper == 1


def test_currency_subtraction():
    a = Currency(gold=2, silver=0, copper=0)
    b = Currency(gold=0, silver=5, copper=0)
    result = a - b
    # 200 − 50 = 150 cp → 1 gp, 5 sp, 0 cp
    assert result.gold == 1
    assert result.silver == 5
    assert result.copper == 0


def test_currency_subtraction_clamps_to_zero():
    a = Currency(gold=0, silver=1, copper=0)
    b = Currency(gold=5, silver=0, copper=0)
    result = a - b
    assert result.to_copper() == 0


# ── Currency.__str__ ─────────────────────────────────────────────────────


def test_currency_str_formatting():
    assert str(Currency(gold=5, silver=3, copper=1)) == "5 gp, 3 sp, 1 cp"
    assert str(Currency(gold=1, silver=0, copper=0)) == "1 gp"
    assert str(Currency(gold=0, silver=0, copper=5)) == "5 cp"


def test_currency_str_zero():
    assert str(Currency(gold=0, silver=0, copper=0)) == "0 cp"


# ── add_currency ─────────────────────────────────────────────────────────


def test_add_currency_to_character():
    char = make_character(gold=5, silver=3, copper=2)
    result = add_currency(char, gold=2, silver=8, copper=9)

    # 532 + 289 = 821 → 8 gp, 2 sp, 1 cp
    assert char.gold == 8
    assert char.silver == 2
    assert char.copper == 1
    assert result.gold == 8


# ── subtract_currency ────────────────────────────────────────────────────


def test_subtract_currency_success():
    char = make_character(gold=10, silver=0, copper=0)
    success, result = subtract_currency(char, gold=3, silver=5, copper=0)

    assert success is True
    # 1000 − 350 = 650 → 6 gp, 5 sp, 0 cp
    assert char.gold == 6
    assert char.silver == 5
    assert char.copper == 0


def test_subtract_currency_insufficient_funds():
    char = make_character(gold=1, silver=0, copper=0)
    success, result = subtract_currency(char, gold=5, silver=0, copper=0)

    assert success is False
    # Character's currency unchanged
    assert char.gold == 1
    assert char.silver == 0
    assert char.copper == 0


# ── format_price ─────────────────────────────────────────────────────────


def test_format_price():
    assert format_price(gold=5, silver=3) == "5 gp, 3 sp"
    assert format_price(copper=15) == "15 cp"
    assert format_price() == "0 cp"


# ── convert_to_gold ──────────────────────────────────────────────────────


def test_convert_to_gold():
    assert convert_to_gold(silver=10) == 1
    assert convert_to_gold(copper=100) == 1
    assert convert_to_gold(silver=5, copper=50) == 1
    assert convert_to_gold(silver=3, copper=0) == 0  # 30cp < 100cp


# ── Constants ─────────────────────────────────────────────────────────────


def test_constants():
    assert CP_PER_SP == 10
    assert CP_PER_GP == 100
    assert SP_PER_GP == 10
