"""Tests for app.services.character_service.CharacterService."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from app.db.models import Character, Item
from app.schemas.character import CharacterCreate, CharacterUpdate
from app.services.character_service import CharacterService
from tests.factories import make_character, make_user


@pytest_asyncio.fixture()
async def db(db_session):
    """Wrap db_session so commit() acts as flush(), preserving the test transaction."""
    original_commit = db_session.commit
    db_session.commit = db_session.flush
    yield db_session
    db_session.commit = original_commit


# ── calculate_hp_max ───────────────────────────────────────────────────────


async def test_calculate_hp_max_barbarian_level_1():
    """Barbarian with CON 14 (mod +2): hit_die 12 + 2 = 14."""
    hp = CharacterService.calculate_hp_max("Barbarian", constitution=14, level=1)
    assert hp == 14


async def test_calculate_hp_max_wizard_level_1():
    """Wizard with CON 10 (mod 0): hit_die 6 + 0 = 6."""
    hp = CharacterService.calculate_hp_max("Wizard", constitution=10, level=1)
    assert hp == 6


async def test_calculate_hp_max_fighter_level_5():
    """Fighter CON 14, level 5: level1=10+2=12, levels 2-5=4*(6+2)=32, total=44."""
    hp = CharacterService.calculate_hp_max("Fighter", constitution=14, level=5)
    assert hp == 44


async def test_calculate_hp_max_unknown_class():
    """Unknown class defaults to hit_die=8."""
    hp = CharacterService.calculate_hp_max("Artificer", constitution=10, level=1)
    assert hp == 8


async def test_calculate_hp_max_paladin_level_1():
    """Paladin with CON 12 (mod +1): 10+1 = 11."""
    hp = CharacterService.calculate_hp_max("Paladin", constitution=12, level=1)
    assert hp == 11


async def test_calculate_hp_max_rogue_level_3():
    """Rogue CON 16 (mod +3), level 3: level1=8+3=11, levels 2-3=2*(5+3)=16, total=27."""
    hp = CharacterService.calculate_hp_max("Rogue", constitution=16, level=3)
    assert hp == 27


async def test_calculate_hp_max_sorcerer_level_1():
    """Sorcerer hit_die=6, CON 8 (mod -1): 6 + (-1) = 5."""
    hp = CharacterService.calculate_hp_max("Sorcerer", constitution=8, level=1)
    assert hp == 5


# ── create_character ───────────────────────────────────────────────────────


async def test_create_character_basic(db):
    """create_character returns a Character persisted in the DB."""
    user = make_user()
    db.add(user)
    await db.flush()

    data = CharacterCreate(
        name="Aragorn",
        character_class="Fighter",
        race="Human",
        strength=15,
        dexterity=13,
        constitution=14,
        intelligence=10,
        wisdom=12,
        charisma=8,
    )
    result = await CharacterService.create_character(db, data, user_id=user.id)

    assert isinstance(result, Character)
    assert result.name == "Aragorn"
    assert result.character_class == "Fighter"
    assert result.user_id == user.id


async def test_create_character_has_starting_equipment(db):
    """Fighter should receive starting equipment items."""
    user = make_user()
    db.add(user)
    await db.flush()

    data = CharacterCreate(
        name="Conan",
        character_class="Fighter",
        race="Human",
        strength=16,
        dexterity=12,
        constitution=14,
        intelligence=10,
        wisdom=10,
        charisma=10,
    )
    char = await CharacterService.create_character(db, data, user_id=user.id)

    from sqlalchemy import select

    result = await db.execute(select(Item).where(Item.character_id == char.id))
    items = result.scalars().all()
    assert len(items) > 0, "Fighter should have starting equipment"


async def test_create_character_applies_racial_bonuses(db):
    """Human gets +1 to all stats."""
    user = make_user()
    db.add(user)
    await db.flush()

    data = CharacterCreate(
        name="Humantest",
        character_class="Fighter",
        race="Human",
        strength=10,
        dexterity=10,
        constitution=10,
        intelligence=10,
        wisdom=10,
        charisma=10,
    )
    char = await CharacterService.create_character(db, data, user_id=user.id)

    # Humans get +1 to all ability scores
    assert char.strength == 11
    assert char.dexterity == 11
    assert char.constitution == 11
    assert char.intelligence == 11
    assert char.wisdom == 11
    assert char.charisma == 11


async def test_create_character_default_scores(db):
    """Omitted scores default to 10 (before racial bonuses)."""
    user = make_user()
    db.add(user)
    await db.flush()

    data = CharacterCreate(
        name="DefaultStats",
        character_class="Wizard",
        race="Elf",
    )
    char = await CharacterService.create_character(db, data, user_id=user.id)
    assert isinstance(char, Character)
    assert char.name == "DefaultStats"


# ── get_character ──────────────────────────────────────────────────────────


async def test_get_character_returns_none_for_nonexistent(db):
    result = await CharacterService.get_character(db, uuid.uuid4())
    assert result is None


async def test_get_character_excludes_soft_deleted(db):
    """Characters with deleted_at set should not be returned."""
    user = make_user()
    char = make_character(user=user, deleted_at=datetime.now(timezone.utc))
    db.add_all([user, char])
    await db.flush()

    result = await CharacterService.get_character(db, char.id)
    assert result is None


async def test_get_character_returns_existing(db):
    user = make_user()
    char = make_character(user=user)
    db.add_all([user, char])
    await db.flush()

    result = await CharacterService.get_character(db, char.id)
    assert result is not None
    assert result.id == char.id


# ── get_user_characters ───────────────────────────────────────────────────


async def test_get_user_characters(db):
    """Returns all non-deleted characters for a user plus a total count."""
    user = make_user()
    c1 = make_character(user=user, name="Hero A")
    c2 = make_character(user=user, name="Hero B")
    db.add_all([user, c1, c2])
    await db.flush()

    chars, total = await CharacterService.get_user_characters(db, user.id)
    assert total == 2
    assert len(chars) == 2
    names = {c.name for c in chars}
    assert names == {"Hero A", "Hero B"}


async def test_get_user_characters_excludes_deleted(db):
    user = make_user()
    c1 = make_character(user=user, name="Alive")
    c2 = make_character(user=user, name="Dead", deleted_at=datetime.now(timezone.utc))
    db.add_all([user, c1, c2])
    await db.flush()

    chars, total = await CharacterService.get_user_characters(db, user.id)
    assert total == 1
    assert chars[0].name == "Alive"


# ── update_character ──────────────────────────────────────────────────────


async def test_update_character_name(db):
    user = make_user()
    char = make_character(user=user, name="OldName")
    db.add_all([user, char])
    await db.flush()

    updated = await CharacterService.update_character(db, char.id, CharacterUpdate(name="NewName"))
    assert updated is not None
    assert updated.name == "NewName"


async def test_update_character_nonexistent_returns_none(db):
    result = await CharacterService.update_character(db, uuid.uuid4(), CharacterUpdate(name="Nope"))
    assert result is None


async def test_update_character_partial(db):
    """Only specified fields are changed; others are untouched."""
    user = make_user()
    char = make_character(user=user, name="Keep", hp_current=10)
    db.add_all([user, char])
    await db.flush()

    updated = await CharacterService.update_character(db, char.id, CharacterUpdate(hp_current=5))
    assert updated.name == "Keep"
    assert updated.hp_current == 5


# ── delete_character ──────────────────────────────────────────────────────


async def test_delete_character_sets_deleted_at(db):
    user = make_user()
    char = make_character(user=user)
    db.add_all([user, char])
    await db.flush()

    result = await CharacterService.delete_character(db, char.id)
    assert result is True

    # Should no longer appear via get_character
    fetched = await CharacterService.get_character(db, char.id)
    assert fetched is None


async def test_delete_character_nonexistent_returns_false(db):
    result = await CharacterService.delete_character(db, uuid.uuid4())
    assert result is False


# ── calculate_ability_modifier ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "score,expected",
    [
        (8, -1),
        (10, 0),
        (14, 2),
        (20, 5),
        (1, -5),
        (15, 2),
    ],
)
async def test_ability_modifier_calculation(score, expected):
    assert CharacterService.calculate_ability_modifier(score) == expected


# ── calculate_proficiency_bonus ────────────────────────────────────────────


@pytest.mark.parametrize(
    "level,expected",
    [
        (1, 2),
        (4, 2),
        (5, 3),
        (8, 3),
        (9, 4),
        (12, 4),
        (13, 5),
        (16, 5),
        (17, 6),
        (20, 6),
    ],
)
async def test_proficiency_bonus(level, expected):
    assert CharacterService.calculate_proficiency_bonus(level) == expected
