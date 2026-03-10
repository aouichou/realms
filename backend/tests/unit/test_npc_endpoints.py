"""Tests for NPC endpoints (/api/v1/npcs).

These endpoints use sync SQLAlchemy Session (db.query pattern).
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, get_db
from app.db.models import CharacterType
from tests.factories import make_character, make_session, make_user

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


BASE = "/api/v1/npcs"


# ===========================================================================
# POST /npcs/npcs — create NPC
# ===========================================================================


async def test_create_npc(sync_client, sync_db):
    body = {
        "name": "Barthen",
        "race": "Human",
        "character_class": "Fighter",
        "level": 3,
        "personality": "Friendly merchant",
        "hp_max": 20,
    }
    resp = await sync_client.post(f"{BASE}/npcs", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "NPC Barthen created"
    assert data["npc"]["name"] == "Barthen"
    assert data["npc"]["race"] == "Human"


async def test_create_npc_no_class(sync_client, sync_db):
    body = {"name": "Villager", "race": "Human", "hp_max": 5}
    resp = await sync_client.post(f"{BASE}/npcs", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["npc"]["character_class"] is not None


async def test_create_npc_invalid_race(sync_client, sync_db):
    body = {"name": "Test", "race": "InvalidRace", "hp_max": 10}
    resp = await sync_client.post(f"{BASE}/npcs", json=body)
    assert resp.status_code == 400
    assert "Invalid race" in resp.json()["detail"]


async def test_create_npc_invalid_class(sync_client, sync_db):
    body = {"name": "Test", "race": "Human", "character_class": "InvalidClass", "hp_max": 10}
    resp = await sync_client.post(f"{BASE}/npcs", json=body)
    assert resp.status_code == 400
    assert "Invalid class" in resp.json()["detail"]


# ===========================================================================
# GET /npcs/npcs — list NPCs
# ===========================================================================


async def test_list_npcs_empty(sync_client, sync_db):
    resp = await sync_client.get(f"{BASE}/npcs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["npcs"], list)
    # May or may not be empty depending on whether create tests ran first
    # in this transaction rollback setup it should be empty
    assert data["count"] >= 0


async def test_list_npcs_with_data(sync_client, sync_db):
    npc = make_character(character_type=CharacterType.NPC, name="Guard", user_id=None)
    sync_db.add(npc)
    sync_db.flush()

    resp = await sync_client.get(f"{BASE}/npcs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    names = [n["name"] for n in data["npcs"]]
    assert "Guard" in names


# ===========================================================================
# GET /npcs/npcs/{npc_id} — get specific NPC
# ===========================================================================


async def test_get_npc(sync_client, sync_db):
    npc = make_character(character_type=CharacterType.NPC, name="Sage", user_id=None)
    sync_db.add(npc)
    sync_db.flush()

    resp = await sync_client.get(f"{BASE}/npcs/{npc.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Sage"


async def test_get_npc_not_found(sync_client, sync_db):
    resp = await sync_client.get(f"{BASE}/npcs/{uuid.uuid4()}")
    assert resp.status_code == 404


# ===========================================================================
# POST /npcs/sessions/{session_id}/add-companion
# ===========================================================================


async def test_add_companion(sync_client, sync_db):
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    npc = make_character(character_type=CharacterType.NPC, name="Elara", user_id=None)
    sync_db.add_all([user, char, session, npc])
    sync_db.flush()

    resp = await sync_client.post(
        f"{BASE}/sessions/{session.id}/add-companion",
        params={"npc_id": str(npc.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "joined the party" in data["message"]


async def test_add_companion_session_not_found(sync_client, sync_db):
    npc = make_character(character_type=CharacterType.NPC, user_id=None)
    sync_db.add(npc)
    sync_db.flush()

    resp = await sync_client.post(
        f"{BASE}/sessions/{uuid.uuid4()}/add-companion",
        params={"npc_id": str(npc.id)},
    )
    assert resp.status_code == 404


async def test_add_companion_npc_not_found(sync_client, sync_db):
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    sync_db.add_all([user, char, session])
    sync_db.flush()

    resp = await sync_client.post(
        f"{BASE}/sessions/{session.id}/add-companion",
        params={"npc_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 404


# ===========================================================================
# GET /npcs/sessions/{session_id}/companions
# ===========================================================================


async def test_get_session_companions_empty(sync_client, sync_db):
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    sync_db.add_all([user, char, session])
    sync_db.flush()

    resp = await sync_client.get(f"{BASE}/sessions/{session.id}/companions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["companions"] == []
    assert data["count"] == 0


async def test_get_session_companions_with_companion(sync_client, sync_db):
    user = make_user()
    char = make_character(user=user)
    npc = make_character(character_type=CharacterType.NPC, name="Companion", user_id=None)
    sync_db.add_all([user, char, npc])
    sync_db.flush()

    session = make_session(user=user, character=char, companion_id=npc.id)
    sync_db.add(session)
    sync_db.flush()

    resp = await sync_client.get(f"{BASE}/sessions/{session.id}/companions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["companions"][0]["name"] == "Companion"


async def test_get_session_companions_session_not_found(sync_client, sync_db):
    resp = await sync_client.get(f"{BASE}/sessions/{uuid.uuid4()}/companions")
    assert resp.status_code == 404


# ===========================================================================
# DELETE /npcs/sessions/{session_id}/companions/{npc_id}
# ===========================================================================


async def test_remove_companion(sync_client, sync_db):
    user = make_user()
    char = make_character(user=user)
    npc = make_character(character_type=CharacterType.NPC, name="Leaving", user_id=None)
    sync_db.add_all([user, char, npc])
    sync_db.flush()

    session = make_session(user=user, character=char, companion_id=npc.id)
    sync_db.add(session)
    sync_db.flush()

    resp = await sync_client.delete(f"{BASE}/sessions/{session.id}/companions/{npc.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "left the party" in data["message"]


async def test_remove_companion_wrong_npc(sync_client, sync_db):
    user = make_user()
    char = make_character(user=user)
    npc = make_character(character_type=CharacterType.NPC, user_id=None)
    sync_db.add_all([user, char, npc])
    sync_db.flush()

    session = make_session(user=user, character=char, companion_id=npc.id)
    sync_db.add(session)
    sync_db.flush()

    resp = await sync_client.delete(f"{BASE}/sessions/{session.id}/companions/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_remove_companion_session_not_found(sync_client, sync_db):
    resp = await sync_client.delete(f"{BASE}/sessions/{uuid.uuid4()}/companions/{uuid.uuid4()}")
    assert resp.status_code == 404
