"""Tests for app.utils.starting_equipment – equipment sets for all classes."""

import pytest

from app.db.models import CharacterClass, ItemType
from app.utils.starting_equipment import (
    STARTING_EQUIPMENT,
    StartingEquipmentItem,
    get_starting_equipment,
)

# ── Specific class gear ──────────────────────────────────────────────────


def test_fighter_has_longsword():
    items = get_starting_equipment(CharacterClass.FIGHTER)
    names = [i.name for i in items]
    assert "Longsword" in names


def test_fighter_has_chain_mail():
    items = get_starting_equipment(CharacterClass.FIGHTER)
    names = [i.name for i in items]
    assert "Chain Mail" in names


def test_wizard_has_quarterstaff():
    items = get_starting_equipment(CharacterClass.WIZARD)
    names = [i.name for i in items]
    assert "Quarterstaff" in names


def test_wizard_has_spellbook():
    items = get_starting_equipment(CharacterClass.WIZARD)
    names = [i.name for i in items]
    assert "Spellbook" in names


def test_rogue_has_shortsword():
    items = get_starting_equipment(CharacterClass.ROGUE)
    names = [i.name for i in items]
    assert "Shortsword" in names


def test_rogue_has_thieves_tools():
    items = get_starting_equipment(CharacterClass.ROGUE)
    names = [i.name for i in items]
    assert "Thieves' Tools" in names


def test_cleric_has_holy_symbol():
    items = get_starting_equipment(CharacterClass.CLERIC)
    names = [i.name for i in items]
    assert "Holy Symbol" in names


# ── Parametrised coverage ────────────────────────────────────────────────


@pytest.mark.parametrize("cls", list(CharacterClass))
def test_all_classes_have_equipment(cls):
    items = get_starting_equipment(cls)
    assert len(items) > 0, f"{cls.value} has no starting equipment"


@pytest.mark.parametrize("cls", list(CharacterClass))
def test_all_items_have_valid_type(cls):
    items = get_starting_equipment(cls)
    for item in items:
        assert isinstance(item.item_type, ItemType), (
            f"{item.name} for {cls.value} has invalid item_type: {item.item_type}"
        )


# ── Item properties ──────────────────────────────────────────────────────


def test_equipment_item_properties():
    items = get_starting_equipment(CharacterClass.FIGHTER)
    longsword = next(i for i in items if i.name == "Longsword")
    assert longsword.weight > 0
    assert longsword.value > 0
    assert longsword.equipped is True
    assert isinstance(longsword.properties, dict)
    assert "damage_dice" in longsword.properties


def test_starting_equipment_item_defaults():
    item = StartingEquipmentItem(
        name="Test Item",
        item_type=ItemType.MISC,
        weight=1,
        value=1,
    )
    assert item.equipped is False
    assert item.quantity == 1
    assert item.properties == {}


def test_get_starting_equipment_all_enum_members_covered():
    """Every CharacterClass enum member has an entry in STARTING_EQUIPMENT."""
    for cls in CharacterClass:
        assert cls in STARTING_EQUIPMENT, f"{cls.value} missing from STARTING_EQUIPMENT"
