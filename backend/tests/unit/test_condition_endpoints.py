"""Tests for condition endpoints (/api/v1/conditions).

The endpoints declare `character_id: int` path params but the Character model
uses UUID ids. Happy-path business logic is therefore tested by calling the
endpoint functions **directly** (bypassing FastAPI routing), and HTTP-level
tests exercise error/static paths.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.endpoints.conditions import (
    CONDITION_EFFECTS,
    AddConditionRequest,
    add_condition,
    get_conditions,
    remove_condition,
)
from app.db.base import Base, get_db
from app.db.models import ConditionType
from tests.factories import make_character, make_condition, make_user

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
    from app.db.models import User
    from app.main import app
    from app.middleware.auth import get_current_active_user

    def _get_sync_db():
        yield sync_db

    auth_user = User(
        id=uuid.uuid4(),
        username=f"syncuser_{uuid.uuid4().hex[:8]}",
        password_hash="hashed",
        is_guest=False,
        is_active=True,
    )
    sync_db.add(auth_user)
    sync_db.flush()

    async def _mock_auth():
        return auth_user

    app.dependency_overrides[get_db] = _get_sync_db
    app.dependency_overrides[get_current_active_user] = _mock_auth
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


BASE = "/api/v1/conditions"


# ===========================================================================
# CONDITION_EFFECTS data
# ===========================================================================


def test_condition_effects_has_all_standard_conditions():
    expected = {ct.value for ct in ConditionType}
    actual = set(CONDITION_EFFECTS.keys())
    assert expected == actual


def test_condition_effects_structure():
    for name, info in CONDITION_EFFECTS.items():
        assert "description" in info
        assert "effects" in info
        assert isinstance(info["effects"], list)
        assert len(info["description"]) > 0


# ===========================================================================
# GET /conditions/effects (static, no path param issue)
# ===========================================================================


async def test_get_condition_effects_via_http(sync_client):
    resp = await sync_client.get(f"{BASE}/conditions/effects")
    assert resp.status_code == 200
    data = resp.json()
    assert "conditions" in data
    assert "Blinded" in data["conditions"]
    assert "Poisoned" in data["conditions"]
    assert "effects" in data["conditions"]["Blinded"]


# ===========================================================================
# Direct function tests — add_condition
# ===========================================================================


async def test_add_condition_happy_path(sync_db):
    user = make_user()
    char = make_character(user=user)
    sync_db.add_all([user, char])
    sync_db.flush()

    req = AddConditionRequest(condition="Poisoned", duration=5, source="Trap")
    result = await add_condition(character_id=char.id, request=req, db=sync_db)

    assert result["message"] == "Condition Poisoned applied"
    assert result["condition"].condition == "Poisoned"
    assert result["condition"].duration == 5
    assert result["condition"].source == "Trap"
    assert "effects" in result
    assert len(result["effects"]) > 0


async def test_add_condition_character_not_found(sync_db):
    req = AddConditionRequest(condition="Poisoned")
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await add_condition(character_id=uuid.uuid4(), request=req, db=sync_db)
    assert exc_info.value.status_code == 404


async def test_add_condition_invalid_condition(sync_db):
    user = make_user()
    char = make_character(user=user)
    sync_db.add_all([user, char])
    sync_db.flush()

    req = AddConditionRequest(condition="Flying")
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await add_condition(character_id=char.id, request=req, db=sync_db)
    assert exc_info.value.status_code == 400
    assert "Invalid condition" in exc_info.value.detail


async def test_add_condition_duplicate_updates_duration(sync_db):
    user = make_user()
    char = make_character(user=user)
    sync_db.add_all([user, char])
    sync_db.flush()

    req1 = AddConditionRequest(condition="Blinded", duration=3, source="Spell A")
    await add_condition(character_id=char.id, request=req1, db=sync_db)

    # Re-apply with longer duration
    req2 = AddConditionRequest(condition="Blinded", duration=10, source="Spell B")
    result = await add_condition(character_id=char.id, request=req2, db=sync_db)

    assert result["message"] == "Condition Blinded updated"
    assert result["condition"].duration == 10


async def test_add_condition_duplicate_shorter_duration_no_update(sync_db):
    user = make_user()
    char = make_character(user=user)
    sync_db.add_all([user, char])
    sync_db.flush()

    req1 = AddConditionRequest(condition="Stunned", duration=10, source="Blow")
    await add_condition(character_id=char.id, request=req1, db=sync_db)

    # Re-apply with shorter duration — should not decrease
    req2 = AddConditionRequest(condition="Stunned", duration=2)
    result = await add_condition(character_id=char.id, request=req2, db=sync_db)

    assert result["condition"].duration == 10  # kept original


# ===========================================================================
# Direct function tests — remove_condition
# ===========================================================================


async def test_remove_condition_happy_path(sync_db):
    user = make_user()
    char = make_character(user=user)
    cond = make_condition(character=char, condition=ConditionType.PRONE)
    sync_db.add_all([user, char, cond])
    sync_db.flush()

    result = await remove_condition(character_id=char.id, condition_id=str(cond.id), db=sync_db)
    assert result["message"] == "Condition Prone removed"


async def test_remove_condition_character_not_found(sync_db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await remove_condition(
            character_id=uuid.uuid4(), condition_id=str(uuid.uuid4()), db=sync_db
        )
    assert exc_info.value.status_code == 404


async def test_remove_condition_condition_not_found(sync_db):
    user = make_user()
    char = make_character(user=user)
    sync_db.add_all([user, char])
    sync_db.flush()

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await remove_condition(character_id=char.id, condition_id=str(uuid.uuid4()), db=sync_db)
    assert exc_info.value.status_code == 404


# ===========================================================================
# Direct function tests — get_conditions
# ===========================================================================


async def test_get_conditions_empty(sync_db):
    user = make_user()
    char = make_character(user=user)
    sync_db.add_all([user, char])
    sync_db.flush()

    result = await get_conditions(character_id=char.id, db=sync_db)
    assert result["count"] == 0
    assert result["conditions"] == []


async def test_get_conditions_with_data(sync_db):
    user = make_user()
    char = make_character(user=user)
    cond1 = make_condition(character=char, condition=ConditionType.POISONED)
    cond2 = make_condition(character=char, condition=ConditionType.BLINDED)
    sync_db.add_all([user, char, cond1, cond2])
    sync_db.flush()

    result = await get_conditions(character_id=char.id, db=sync_db)
    assert result["count"] == 2
    condition_names = {c["condition"] for c in result["conditions"]}
    assert "Poisoned" in condition_names
    assert "Blinded" in condition_names
    # Verify each condition has effects/description from the lookup
    for c in result["conditions"]:
        assert "effects" in c
        assert "description" in c


async def test_get_conditions_character_not_found(sync_db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_conditions(character_id=uuid.uuid4(), db=sync_db)
    assert exc_info.value.status_code == 404


# ===========================================================================
# HTTP-level error tests (for routing validation)
# ===========================================================================


async def test_add_condition_via_http_returns_404_for_unknown_int(sync_client):
    """character_id: int means int path params work but return 404 since no UUID matches."""
    resp = await sync_client.post(
        f"{BASE}/characters/99999/conditions",
        json={"condition": "Poisoned", "duration": 5},
    )
    assert resp.status_code == 404
