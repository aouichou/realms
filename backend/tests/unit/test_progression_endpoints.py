"""Tests for progression endpoints (/api/v1/progression).

Pure helper functions are tested directly.
Endpoint functions (which declare `character_id: int` but Character.id is UUID)
are called directly to bypass the routing type mismatch.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.progression import (
    CLASS_HIT_DICE,
    XP_THRESHOLDS,
    AddXPRequest,
    LevelUpRequest,
    add_experience,
    can_level_up,
    get_proficiency_bonus,
    get_xp_for_level,
    get_xp_progress,
    level_up_character,
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


@pytest.fixture
def sync_auth_user(sync_db):
    """The User that sync_client authenticates as."""
    from app.db.models import User

    user = User(
        id=uuid.uuid4(),
        username=f"syncuser_{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        is_guest=False,
        is_active=True,
    )
    sync_db.add(user)
    sync_db.flush()
    return user


@pytest_asyncio.fixture
async def sync_client(sync_db, sync_auth_user):
    from app.main import app
    from app.middleware.auth import get_current_active_user

    def _get_sync_db():
        yield sync_db

    async def _mock_auth():
        return sync_auth_user

    app.dependency_overrides[get_db] = _get_sync_db
    app.dependency_overrides[get_current_active_user] = _mock_auth
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


BASE = "/api/v1/progression"


# ===========================================================================
# Pure function tests — get_proficiency_bonus
# ===========================================================================


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
def test_proficiency_bonus(level, expected):
    assert get_proficiency_bonus(level) == expected


# ===========================================================================
# Pure function tests — get_xp_for_level
# ===========================================================================


def test_xp_for_level_1():
    assert get_xp_for_level(1) == 0


def test_xp_for_level_2():
    assert get_xp_for_level(2) == 300


def test_xp_for_level_20():
    assert get_xp_for_level(20) == 355000


def test_xp_for_level_beyond_20():
    """Levels > 20 fall back to the level 20 threshold."""
    assert get_xp_for_level(25) == XP_THRESHOLDS[20]


# ===========================================================================
# Pure function tests — can_level_up
# ===========================================================================


def test_can_level_up_true():
    assert can_level_up(xp=300, current_level=1) is True


def test_can_level_up_false_not_enough_xp():
    assert can_level_up(xp=100, current_level=1) is False


def test_can_level_up_false_max_level():
    assert can_level_up(xp=999999, current_level=20) is False


def test_can_level_up_exact_threshold():
    assert can_level_up(xp=900, current_level=2) is True  # need 900 for level 3


# ===========================================================================
# CLASS_HIT_DICE data
# ===========================================================================


def test_class_hit_dice_complete():
    for cls in CharacterClass:
        assert cls in CLASS_HIT_DICE


# ===========================================================================
# Direct function tests — add_experience
# ===========================================================================


async def test_add_xp(sync_db):
    user = make_user()
    char = make_character(user=user, experience_points=0, level=1)
    sync_db.add_all([user, char])
    sync_db.flush()

    result = await add_experience(
        character_id=char.id, request=AddXPRequest(amount=500), current_user=user, db=sync_db
    )

    assert result["experience_points"] == 500
    assert result["xp_added"] == 500
    assert result["can_level_up"] is True  # 500 >= 300 (level 2 threshold)
    assert result["xp_to_next_level"] is not None


async def test_add_xp_character_not_found(sync_db):
    user = make_user()
    sync_db.add(user)
    sync_db.flush()
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await add_experience(
            character_id=uuid.uuid4(),
            request=AddXPRequest(amount=100),
            current_user=user,
            db=sync_db,
        )
    assert exc_info.value.status_code == 404


# ===========================================================================
# Direct function tests — get_xp_progress
# ===========================================================================


async def test_xp_progress(sync_db):
    user = make_user()
    char = make_character(user=user, experience_points=600, level=2)
    sync_db.add_all([user, char])
    sync_db.flush()

    result = await get_xp_progress(character_id=char.id, current_user=user, db=sync_db)

    assert result["level"] == 2
    assert result["experience_points"] == 600
    assert result["current_level_xp"] == 300
    assert result["next_level_xp"] == 900
    # 600 - 300 = 300 in level; 900 - 300 = 600 needed; 300/600 = 50%
    assert result["progress_percent"] == 50.0
    assert result["can_level_up"] is False


async def test_xp_progress_at_max_level(sync_db):
    user = make_user()
    char = make_character(user=user, experience_points=400000, level=20)
    sync_db.add_all([user, char])
    sync_db.flush()

    result = await get_xp_progress(character_id=char.id, current_user=user, db=sync_db)

    assert result["progress_percent"] == 100.0
    assert result["next_level_xp"] is None
    assert result["can_level_up"] is False


async def test_xp_progress_character_not_found(sync_db):
    user = make_user()
    sync_db.add(user)
    sync_db.flush()
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_xp_progress(character_id=uuid.uuid4(), current_user=user, db=sync_db)
    assert exc_info.value.status_code == 404


# ===========================================================================
# Direct function tests — level_up_character
# ===========================================================================


async def test_level_up_basic(sync_db):
    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.FIGHTER,
        experience_points=300,
        level=1,
        hp_current=12,
        hp_max=12,
        constitution=14,  # +2
    )
    sync_db.add_all([user, char])
    sync_db.flush()

    req = LevelUpRequest(hp_roll=7)
    result = await level_up_character(
        character_id=char.id, request=req, current_user=user, db=sync_db
    )

    assert result["success"] is True
    assert result["new_level"] == 2
    # hp_roll=7, con_mod=2 → hp_increase=9
    assert result["hp_gained"] == 9
    assert result["new_hp_max"] == 21


async def test_level_up_average_hp(sync_db):
    from unittest.mock import patch

    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.WIZARD,
        experience_points=300,
        level=1,
        hp_current=6,
        hp_max=6,
        constitution=10,  # +0
    )
    sync_db.add_all([user, char])
    sync_db.flush()

    # Mock: get_spell_slots_for_class returns {level: count} (raw ints)
    # The production code has a bug wrapping these a second time.
    with patch(
        "app.api.v1.endpoints.progression.get_spell_slots_for_class",
        return_value={1: 3},
    ):
        req = LevelUpRequest(hp_roll=0)  # 0 = take average
        result = await level_up_character(
            character_id=char.id, request=req, current_user=user, db=sync_db
        )

    # Wizard d6: average = (6//2)+1 = 4, con_mod=0 → 4
    assert result["hp_gained"] == 4
    assert result["new_hp_max"] == 10


async def test_level_up_with_ability_increase(sync_db):
    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.FIGHTER,
        experience_points=2700,  # enough for level 4
        level=3,
        hp_current=30,
        hp_max=30,
        strength=16,
        constitution=14,
    )
    sync_db.add_all([user, char])
    sync_db.flush()

    req = LevelUpRequest(
        hp_roll=8,
        ability_increases={"strength": 1, "constitution": 1},
    )
    result = await level_up_character(
        character_id=char.id, request=req, current_user=user, db=sync_db
    )

    assert result["new_level"] == 4
    assert result["ability_increases"] == {"strength": 1, "constitution": 1}


async def test_level_up_asi_wrong_total(sync_db):
    user = make_user()
    char = make_character(
        user=user,
        experience_points=2700,
        level=3,
        hp_current=30,
        hp_max=30,
    )
    sync_db.add_all([user, char])
    sync_db.flush()

    # Level 4 is an ASI level — must provide exactly 2 points
    req = LevelUpRequest(hp_roll=5, ability_increases={"strength": 1})  # only 1
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await level_up_character(character_id=char.id, request=req, current_user=user, db=sync_db)
    assert exc_info.value.status_code == 400
    assert "exactly 2 points" in exc_info.value.detail


async def test_level_up_asi_invalid_ability(sync_db):
    user = make_user()
    char = make_character(
        user=user,
        experience_points=2700,
        level=3,
        hp_current=30,
        hp_max=30,
    )
    sync_db.add_all([user, char])
    sync_db.flush()

    req = LevelUpRequest(hp_roll=5, ability_increases={"luck": 2})
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await level_up_character(character_id=char.id, request=req, current_user=user, db=sync_db)
    assert exc_info.value.status_code == 400


async def test_level_up_not_enough_xp(sync_db):
    user = make_user()
    char = make_character(user=user, experience_points=100, level=1)
    sync_db.add_all([user, char])
    sync_db.flush()

    req = LevelUpRequest(hp_roll=5)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await level_up_character(character_id=char.id, request=req, current_user=user, db=sync_db)
    assert exc_info.value.status_code == 400


async def test_level_up_max_level(sync_db):
    user = make_user()
    char = make_character(user=user, experience_points=999999, level=20)
    sync_db.add_all([user, char])
    sync_db.flush()

    req = LevelUpRequest()
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await level_up_character(character_id=char.id, request=req, current_user=user, db=sync_db)
    assert exc_info.value.status_code == 400


async def test_level_up_character_not_found(sync_db):
    user = make_user()
    sync_db.add(user)
    sync_db.flush()
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await level_up_character(
            character_id=uuid.uuid4(), request=LevelUpRequest(), current_user=user, db=sync_db
        )
    assert exc_info.value.status_code == 404


async def test_level_up_spellcaster_gets_spell_slots(sync_db):
    from unittest.mock import patch

    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.WIZARD,
        experience_points=300,
        level=1,
        hp_current=6,
        hp_max=6,
        constitution=10,
        spell_slots={"1": {"total": 2, "used": 0}},
    )
    sync_db.add_all([user, char])
    sync_db.flush()

    with patch(
        "app.api.v1.endpoints.progression.get_spell_slots_for_class",
        return_value={1: 3},
    ):
        req = LevelUpRequest(hp_roll=0)
        result = await level_up_character(
            character_id=char.id, request=req, current_user=user, db=sync_db
        )

    assert result["new_spell_slots"] is not None
    assert result["new_level"] == 2


# ===========================================================================
# HTTP-level error test
# ===========================================================================


async def test_progression_via_http_returns_404_for_unknown_int(sync_client):
    resp = await sync_client.post(
        f"{BASE}/characters/{uuid.uuid4()}/add-xp",
        json={"amount": 100},
    )
    assert resp.status_code == 404
