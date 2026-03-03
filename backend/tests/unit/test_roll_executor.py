"""Tests for app.services.roll_executor – dice rolling, modifiers, advantage."""

from unittest.mock import patch

from app.services.roll_executor import DiceRollResult, RollExecutor
from app.services.roll_parser import Ability, RollType
from tests.factories import make_character, make_user

# ── _parse_notation ──────────────────────────────────────────────────────


def test_parse_notation_simple():
    dice_parts, modifier = RollExecutor._parse_notation("d20")
    assert len(dice_parts) == 1
    assert dice_parts[0]["count"] == 1
    assert dice_parts[0]["sides"] == 20
    assert dice_parts[0]["drop_lowest"] == 0
    assert dice_parts[0]["drop_highest"] == 0
    assert modifier == 0


def test_parse_notation_with_modifier():
    dice_parts, modifier = RollExecutor._parse_notation("d20+5")
    assert dice_parts[0]["count"] == 1
    assert dice_parts[0]["sides"] == 20
    assert modifier == 5


def test_parse_notation_multiple_dice():
    dice_parts, modifier = RollExecutor._parse_notation("2d6+1d4+3")
    assert len(dice_parts) == 2
    assert dice_parts[0]["count"] == 2
    assert dice_parts[0]["sides"] == 6
    assert dice_parts[1]["count"] == 1
    assert dice_parts[1]["sides"] == 4
    assert modifier == 3


def test_parse_notation_drop_lowest():
    dice_parts, modifier = RollExecutor._parse_notation("4d6dl1")
    assert len(dice_parts) == 1
    assert dice_parts[0]["count"] == 4
    assert dice_parts[0]["sides"] == 6
    assert dice_parts[0]["drop_lowest"] == 1


# ── execute_roll ─────────────────────────────────────────────────────────


@patch("app.services.roll_executor.random.randint", return_value=15)
def test_execute_roll_basic(mock_randint):
    result = RollExecutor.execute_roll("d20+3", RollType.ATTACK)
    assert result.total == 15 + 3
    assert result.rolls == [15]
    assert result.modifier == 3


@patch("app.services.roll_executor.random.randint", return_value=15)
def test_execute_roll_with_dc_success(mock_randint):
    result = RollExecutor.execute_roll("d20+2", RollType.CHECK, dc=15)
    # total = 15 + 2 = 17 >= 15
    assert result.success is True
    assert result.dc == 15


@patch("app.services.roll_executor.random.randint", return_value=5)
def test_execute_roll_with_dc_failure(mock_randint):
    result = RollExecutor.execute_roll("d20+2", RollType.CHECK, dc=15)
    # total = 5 + 2 = 7 < 15
    assert result.success is False


@patch("app.services.roll_executor.random.randint", return_value=10)
def test_execute_roll_with_character_ability_modifier(mock_randint):
    user = make_user()
    char = make_character(user=user, strength=16)  # mod = (16-10)//2 = +3
    result = RollExecutor.execute_roll(
        "d20", RollType.CHECK, character=char, ability=Ability.STRENGTH
    )
    # total = 10 (roll) + 0 (notation mod) + 3 (ability mod) = 13
    assert result.total == 13


@patch("app.services.roll_executor.random.randint", side_effect=[8, 15])
def test_execute_roll_advantage(mock_randint):
    result = RollExecutor.execute_roll("d20", RollType.ATTACK, advantage=True)
    # Advantage takes max(8, 15) = 15
    assert result.rolls == [15]
    assert result.advantage is True


@patch("app.services.roll_executor.random.randint", side_effect=[15, 8])
def test_execute_roll_disadvantage(mock_randint):
    result = RollExecutor.execute_roll("d20", RollType.ATTACK, disadvantage=True)
    # Disadvantage takes min(15, 8) = 8
    assert result.rolls == [8]
    assert result.disadvantage is True


# ── DiceRollResult properties ────────────────────────────────────────────


def test_dice_roll_result_is_critical():
    result = DiceRollResult(notation="d20+5", rolls=[20], modifier=5, total=25)
    assert result.is_critical is True


def test_dice_roll_result_is_critical_fail():
    result = DiceRollResult(notation="d20+3", rolls=[1], modifier=3, total=4)
    assert result.is_critical_fail is True


def test_dice_roll_result_dice_total_property():
    result = DiceRollResult(notation="2d6+3", rolls=[4, 5], modifier=3, total=12)
    assert result.dice_total == 9  # 4 + 5
