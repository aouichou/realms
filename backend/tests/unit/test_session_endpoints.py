"""Tests for session API endpoints (/api/v1/sessions)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from tests.factories import make_character, make_session, make_user

# -- Strip problematic middleware (CSRF, rate-limit, HTTPS) for tests ------


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


# -- Patch commit -> flush so endpoint code doesn't break the test txn -----


@pytest_asyncio.fixture(autouse=True)
async def _patch_commit(db_session):
    original = db_session.commit
    db_session.commit = db_session.flush
    yield
    db_session.commit = original


# -- Mock Redis session_service --------------------------------------------


@pytest.fixture(autouse=True)
def _mock_session_service(monkeypatch):
    from app.services.redis_service import session_service

    monkeypatch.setattr(session_service, "connect", AsyncMock())
    monkeypatch.setattr(session_service, "create_session_state", AsyncMock(return_value={}))
    monkeypatch.setattr(session_service, "get_session_state", AsyncMock(return_value=None))
    monkeypatch.setattr(session_service, "get_conversation_history", AsyncMock(return_value=[]))
    monkeypatch.setattr(session_service, "update_session_state", AsyncMock(return_value={}))
    monkeypatch.setattr(session_service, "refresh_ttl", AsyncMock())
    monkeypatch.setattr(session_service, "delete_session_state", AsyncMock())
    monkeypatch.setattr(session_service, "revoke_token", AsyncMock())
    monkeypatch.setattr(session_service, "is_token_revoked", AsyncMock(return_value=False))
    monkeypatch.setattr(session_service, "add_message_to_history", AsyncMock())
    monkeypatch.setattr(session_service, "clear_conversation_history", AsyncMock())


# -- helpers ---------------------------------------------------------------

BASE = "/api/v1/sessions"


# ===========================================================================
# POST /api/v1/sessions
# ===========================================================================


async def test_create_session_happy(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    body = {"character_id": str(char.id)}
    resp = await client.post(BASE, json=body, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["character_id"] == str(char.id)
    assert data["is_active"] is True
    assert data["user_id"] == str(user.id)


async def test_create_session_with_location(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    body = {"character_id": str(char.id), "current_location": "Dragon's Lair"}
    resp = await client.post(BASE, json=body, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["current_location"] == "Dragon's Lair"


# ===========================================================================
# GET /api/v1/sessions/{session_id}
# ===========================================================================


async def test_get_session_happy(client, db_session):
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    resp = await client.get(f"{BASE}/{session.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(session.id)
    assert data["character_id"] == str(char.id)


async def test_get_session_not_found(client):
    fake_id = uuid.uuid4()
    resp = await client.get(f"{BASE}/{fake_id}")
    assert resp.status_code == 404


async def test_get_session_without_state(client, db_session):
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    resp = await client.get(f"{BASE}/{session.id}", params={"include_state": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] is None
    assert data["conversation_history"] is None


# ===========================================================================
# GET /api/v1/sessions
# ===========================================================================


async def test_list_sessions(client, db_session):
    user = make_user()
    char = make_character(user=user)
    s1 = make_session(user=user, character=char)
    s2 = make_session(user=user, character=char, is_active=False)
    db_session.add_all([user, char, s1, s2])
    await db_session.flush()

    resp = await client.get(BASE, params={"user_id": str(user.id)})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


async def test_list_sessions_active_only(client, db_session):
    user = make_user()
    char = make_character(user=user)
    s1 = make_session(user=user, character=char, is_active=True)
    s2 = make_session(user=user, character=char, is_active=False)
    db_session.add_all([user, char, s1, s2])
    await db_session.flush()

    resp = await client.get(BASE, params={"user_id": str(user.id), "active_only": True})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["is_active"] is True


# ===========================================================================
# PATCH /api/v1/sessions/{session_id}
# ===========================================================================


async def test_update_session(client, db_session):
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    body = {"current_location": "Dungeon Entrance"}
    resp = await client.patch(f"{BASE}/{session.id}", json=body)
    assert resp.status_code == 200
    assert resp.json()["current_location"] == "Dungeon Entrance"


async def test_update_session_not_found(client):
    fake_id = uuid.uuid4()
    body = {"current_location": "Nowhere"}
    resp = await client.patch(f"{BASE}/{fake_id}", json=body)
    assert resp.status_code == 404


# ===========================================================================
# POST /api/v1/sessions/{session_id}/end
# ===========================================================================


async def test_end_session_happy(client, db_session):
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char, is_active=True)
    db_session.add_all([user, char, session])
    await db_session.flush()

    resp = await client.post(f"{BASE}/{session.id}/end")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_end_session_not_found(client):
    fake_id = uuid.uuid4()
    resp = await client.post(f"{BASE}/{fake_id}/end")
    assert resp.status_code == 404


# ===========================================================================
# DELETE /api/v1/sessions/{session_id}
# ===========================================================================


async def test_delete_session_happy(client, db_session):
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    resp = await client.delete(f"{BASE}/{session.id}")
    assert resp.status_code == 204


async def test_delete_session_not_found(client):
    fake_id = uuid.uuid4()
    resp = await client.delete(f"{BASE}/{fake_id}")
    assert resp.status_code == 404


# ===========================================================================
# GET /api/v1/sessions/active/character/{character_id}
# ===========================================================================


async def test_get_active_session_for_character_not_found(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    resp = await client.get(f"{BASE}/active/character/{char.id}", headers=headers)
    assert resp.status_code == 404


async def test_get_active_session_for_character_happy(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user)
    session = make_session(user=user, character=char, is_active=True)
    db_session.add_all([char, session])
    await db_session.flush()

    resp = await client.get(f"{BASE}/active/character/{char.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["character_id"] == str(char.id)
    assert data["is_active"] is True
