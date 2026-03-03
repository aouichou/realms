"""Tests for rest endpoints (/api/v1/rest).

The endpoints declare `character_id: int` but Character.id is UUID.
Happy-path tests call endpoint functions directly; HTTP tests cover error paths.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.rest import (
    CLASS_HIT_DICE,
    RestRequest,
    get_rest_status,
    take_rest,
)
from app.db.base import Base, get_db
from app.db.models import CharacterClass
from tests.factories import make_character, make_user

# ---------------------------------------------------------------------------
# Sync engine/session fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _sync_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def sync_db(_sync_engine):
    connection = _sync_engine.connect()
    transaction = connection.begin()
    SyncSession = sessionmaker(bind=connection, expire_on_commit=False)
    session = SyncSession()
    original_commit = session.commit
    session.commit = session.flush
    yield session
    session.commit = original_commit
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def _strip_middleware():
    from app.main import app
    from app.middleware.csrf import CSRFProtectionMiddleware
    from app.middleware.https import HTTPSEnforcementMiddleware
    from app.middleware.rate_limit import RateLimitMiddleware

    original = app.user_middleware[:]
    app.user_middleware = [
        m
        for m in app.user_middleware
        if m.cls not in (CSRFProtectionMiddleware, RateLimitMiddleware, HTTPSEnforcementMiddleware)
    ]
    app.middleware_stack = app.build_middleware_stack()
    yield
    app.user_middleware = original
    app.middleware_stack = app.build_middleware_stack()


@pytest_asyncio.fixture
async def sync_client(sync_db):
    from app.main import app

    def _get_sync_db():
        yield sync_db

    app.dependency_overrides[get_db] = _get_sync_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


BASE = "/api/v1/rest"


# ===========================================================================
# CLASS_HIT_DICE data
# ===========================================================================


def test_class_hit_dice_has_all_classes():
    for cls in CharacterClass:
        assert cls in CLASS_HIT_DICE, f"Missing hit die for {cls.value}"


def test_barbarian_has_d12():
    assert CLASS_HIT_DICE[CharacterClass.BARBARIAN] == 12


def test_wizard_has_d6():
    assert CLASS_HIT_DICE[CharacterClass.WIZARD] == 6


def test_fighter_has_d10():
    assert CLASS_HIT_DICE[CharacterClass.FIGHTER] == 10


# ===========================================================================
# Direct function tests — take_rest (short)
# ===========================================================================


async def test_short_rest_with_hit_dice(sync_db):
    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.FIGHTER,
        hp_current=5,
        hp_max=20,
        constitution=14,  # +2 modifier
    )
    sync_db.add_all([user, char])
    sync_db.flush()

    req = RestRequest(rest_type="short", hit_dice_spent=[6])
    result = await take_rest(character_id=char.id, request=req, db=sync_db)

    assert result["rest_type"] == "short"
    assert result["hit_dice_spent"] == 1
    # roll 6 + con_mod 2 = 8 HP recovered, 5 + 8 = 13
    assert result["hp_recovered"] == 8
    assert result["current_hp"] == 13
    assert result["max_hp"] == 20


async def test_short_rest_no_dice(sync_db):
    user = make_user()
    char = make_character(user=user, hp_current=5, hp_max=20)
    sync_db.add_all([user, char])
    sync_db.flush()

    req = RestRequest(rest_type="short", hit_dice_spent=[])
    result = await take_rest(character_id=char.id, request=req, db=sync_db)

    assert result["hp_recovered"] == 0
    assert result["current_hp"] == 5


async def test_short_rest_caps_at_max_hp(sync_db):
    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.FIGHTER,
        hp_current=18,
        hp_max=20,
        constitution=10,  # +0 modifier
    )
    sync_db.add_all([user, char])
    sync_db.flush()

    # Roll max d10 = 10 → would bring to 28, capped at 20
    req = RestRequest(rest_type="short", hit_dice_spent=[10])
    result = await take_rest(character_id=char.id, request=req, db=sync_db)

    assert result["current_hp"] == 20
    assert result["hp_recovered"] == 2


async def test_short_rest_invalid_roll(sync_db):
    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.FIGHTER,
        hp_current=5,
        hp_max=20,
    )
    sync_db.add_all([user, char])
    sync_db.flush()

    # Fighter has d10 — roll of 11 is invalid
    req = RestRequest(rest_type="short", hit_dice_spent=[11])
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await take_rest(character_id=char.id, request=req, db=sync_db)
    assert exc_info.value.status_code == 400
    assert "Invalid hit die roll" in exc_info.value.detail


async def test_short_rest_minimum_1_hp_per_die(sync_db):
    """Even with negative CON modifier, minimum 1 HP per die."""
    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.WIZARD,
        hp_current=3,
        hp_max=10,
        constitution=6,  # -2 modifier
    )
    sync_db.add_all([user, char])
    sync_db.flush()

    # Roll 1 + con_mod(-2) = -1 → clamped to 1
    req = RestRequest(rest_type="short", hit_dice_spent=[1])
    result = await take_rest(character_id=char.id, request=req, db=sync_db)

    assert result["hp_recovered"] == 1
    assert result["current_hp"] == 4


# ===========================================================================
# Direct function tests — take_rest (long)
# ===========================================================================


async def test_long_rest_restores_full_hp(sync_db):
    user = make_user()
    char = make_character(user=user, hp_current=3, hp_max=20)
    sync_db.add_all([user, char])
    sync_db.flush()

    req = RestRequest(rest_type="long")
    result = await take_rest(character_id=char.id, request=req, db=sync_db)

    assert result["rest_type"] == "long"
    assert result["hp_recovered"] == 17
    assert result["current_hp"] == 20


async def test_long_rest_restores_spell_slots(sync_db):
    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.WIZARD,
        hp_current=8,
        hp_max=8,
        spell_slots={
            "1": {"total": 4, "used": 3},
            "2": {"total": 2, "used": 2},
        },
    )
    sync_db.add_all([user, char])
    sync_db.flush()

    req = RestRequest(rest_type="long")
    result = await take_rest(character_id=char.id, request=req, db=sync_db)

    assert result["spell_slots_restored"] is True


async def test_long_rest_no_spell_slots(sync_db):
    user = make_user()
    char = make_character(user=user, hp_current=10, hp_max=10, spell_slots={})
    sync_db.add_all([user, char])
    sync_db.flush()

    req = RestRequest(rest_type="long")
    result = await take_rest(character_id=char.id, request=req, db=sync_db)

    assert result["spell_slots_restored"] is False


# ===========================================================================
# Direct function tests — take_rest (invalid)
# ===========================================================================


async def test_invalid_rest_type(sync_db):
    user = make_user()
    char = make_character(user=user)
    sync_db.add_all([user, char])
    sync_db.flush()

    req = RestRequest(rest_type="nap")
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await take_rest(character_id=char.id, request=req, db=sync_db)
    assert exc_info.value.status_code == 400
    assert "Invalid rest type" in exc_info.value.detail


async def test_rest_character_not_found(sync_db):
    req = RestRequest(rest_type="short")
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await take_rest(character_id=uuid.uuid4(), request=req, db=sync_db)
    assert exc_info.value.status_code == 404


# ===========================================================================
# Direct function tests — get_rest_status
# ===========================================================================


async def test_rest_status(sync_db):
    user = make_user()
    char = make_character(user=user, hp_current=8, hp_max=20, level=3)
    sync_db.add_all([user, char])
    sync_db.flush()

    result = await get_rest_status(character_id=char.id, db=sync_db)

    assert result["current_hp"] == 8
    assert result["max_hp"] == 20
    assert result["hp_percent"] == 40.0
    assert result["hit_die_type"] == "d10"  # Fighter default
    assert result["available_hit_dice"] == 3
    assert result["needs_rest"] is True


async def test_rest_status_full_hp(sync_db):
    user = make_user()
    char = make_character(user=user, hp_current=20, hp_max=20, spell_slots={})
    sync_db.add_all([user, char])
    sync_db.flush()

    result = await get_rest_status(character_id=char.id, db=sync_db)

    assert result["needs_rest"] is False


async def test_rest_status_with_spell_slots(sync_db):
    user = make_user()
    char = make_character(
        user=user,
        hp_current=10,
        hp_max=10,
        spell_slots={"1": {"total": 3, "used": 1}},
    )
    sync_db.add_all([user, char])
    sync_db.flush()

    result = await get_rest_status(character_id=char.id, db=sync_db)

    assert "1" in result["spell_slots"]
    assert result["spell_slots"]["1"]["remaining"] == 2
    assert result["needs_rest"] is True  # has used spell slots


async def test_rest_status_character_not_found(sync_db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_rest_status(character_id=uuid.uuid4(), db=sync_db)
    assert exc_info.value.status_code == 404


# ===========================================================================
# HTTP-level error test
# ===========================================================================


async def test_rest_via_http_returns_404_for_unknown_int(sync_client):
    resp = await sync_client.post(
        f"{BASE}/characters/99999/rest",
        json={"rest_type": "short", "hit_dice_spent": []},
    )
    assert resp.status_code == 404
