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


async def test_create_session_with_companion(client, db_session, auth_user):
    """Create a session that includes a companion_id."""
    user, headers = auth_user
    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    companion_id = uuid.uuid4()
    body = {
        "character_id": str(char.id),
        "companion_id": str(companion_id),
    }
    resp = await client.post(BASE, json=body, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["companion_id"] == str(companion_id)


async def test_create_session_redis_state_creation(client, db_session, auth_user, monkeypatch):
    """Verify that Redis create_session_state is called during creation."""
    from app.services.redis_service import session_service

    mock_create = AsyncMock(return_value={})
    monkeypatch.setattr(session_service, "create_session_state", mock_create)

    user, headers = auth_user
    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    body = {"character_id": str(char.id), "current_location": "Forest"}
    resp = await client.post(BASE, json=body, headers=headers)
    assert resp.status_code == 201
    mock_create.assert_awaited_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["character_id"] == char.id
    assert call_kwargs["current_location"] == "Forest"


# ===========================================================================
# GET /api/v1/sessions/{session_id}
# ===========================================================================


async def test_get_session_happy(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([char, session])
    await db_session.flush()

    resp = await client.get(f"{BASE}/{session.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(session.id)
    assert data["character_id"] == str(char.id)


async def test_get_session_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"{BASE}/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_get_session_without_state(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([char, session])
    await db_session.flush()

    resp = await client.get(f"{BASE}/{session.id}", params={"include_state": False}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] is None
    assert data["conversation_history"] is None


async def test_get_session_with_redis_state(client, db_session, auth_user, monkeypatch):
    """When Redis returns state data, it should be included in the response."""
    user, headers = auth_user
    from app.services.redis_service import session_service

    redis_state = {"state": {"hp": 20, "location": "Cave"}}
    conversation = [{"role": "user", "content": "I look around"}]
    monkeypatch.setattr(session_service, "get_session_state", AsyncMock(return_value=redis_state))
    monkeypatch.setattr(
        session_service, "get_conversation_history", AsyncMock(return_value=conversation)
    )

    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([char, session])
    await db_session.flush()

    resp = await client.get(f"{BASE}/{session.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == {"hp": 20, "location": "Cave"}
    assert data["conversation_history"] == conversation


# ===========================================================================
# GET /api/v1/sessions
# ===========================================================================


async def test_list_sessions(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user)
    s1 = make_session(user=user, character=char)
    s2 = make_session(user=user, character=char, is_active=False)
    db_session.add_all([char, s1, s2])
    await db_session.flush()

    resp = await client.get(BASE, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


async def test_list_sessions_active_only(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user)
    s1 = make_session(user=user, character=char, is_active=True)
    s2 = make_session(user=user, character=char, is_active=False)
    db_session.add_all([char, s1, s2])
    await db_session.flush()

    resp = await client.get(BASE, params={"active_only": True}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["is_active"] is True


async def test_list_sessions_pagination(client, db_session, auth_user):
    """Verify skip and limit parameters work correctly."""
    user, headers = auth_user
    char = make_character(user=user)
    sessions = [make_session(user=user, character=char) for _ in range(5)]
    db_session.add_all([char, *sessions])
    await db_session.flush()

    # Get first page (2 items)
    resp = await client.get(BASE, params={"skip": 0, "limit": 2}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    # Get second page
    resp2 = await client.get(BASE, params={"skip": 2, "limit": 2}, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2) == 2

    # Ensure no overlap
    ids_page1 = {d["id"] for d in data}
    ids_page2 = {d["id"] for d in data2}
    assert ids_page1.isdisjoint(ids_page2)


# ===========================================================================
# GET /api/v1/sessions/active/current
# ===========================================================================


async def test_get_active_session_happy(client, db_session, auth_user):
    """Get the user's currently active session."""
    user, headers = auth_user
    char = make_character(user=user)
    session = make_session(user=user, character=char, is_active=True)
    db_session.add_all([char, session])
    await db_session.flush()

    resp = await client.get(f"{BASE}/active/current", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(session.id)
    assert data["is_active"] is True


async def test_get_active_session_not_found(client, db_session, auth_user):
    """No active session for user → 404."""
    user, headers = auth_user
    char = make_character(user=user)
    session = make_session(user=user, character=char, is_active=False)
    db_session.add_all([char, session])
    await db_session.flush()

    resp = await client.get(f"{BASE}/active/current", headers=headers)
    assert resp.status_code == 404


async def test_get_active_session_with_redis_state(client, db_session, auth_user, monkeypatch):
    """Active session endpoint includes Redis state."""
    from app.services.redis_service import session_service

    redis_state = {"state": {"turn": 3}}
    conversation = [{"role": "assistant", "content": "You see a dark cave."}]
    monkeypatch.setattr(session_service, "get_session_state", AsyncMock(return_value=redis_state))
    monkeypatch.setattr(
        session_service, "get_conversation_history", AsyncMock(return_value=conversation)
    )

    user, headers = auth_user
    char = make_character(user=user)
    session = make_session(user=user, character=char, is_active=True)
    db_session.add_all([char, session])
    await db_session.flush()

    resp = await client.get(f"{BASE}/active/current", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == {"turn": 3}
    assert len(data["conversation_history"]) == 1


# ===========================================================================
# PATCH /api/v1/sessions/{session_id}
# ===========================================================================


async def test_update_session(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([char, session])
    await db_session.flush()

    body = {"current_location": "Dungeon Entrance"}
    resp = await client.patch(f"{BASE}/{session.id}", json=body, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["current_location"] == "Dungeon Entrance"


async def test_update_session_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    body = {"current_location": "Nowhere"}
    resp = await client.patch(f"{BASE}/{fake_id}", json=body, headers=auth_headers)
    assert resp.status_code == 404


async def test_update_session_is_active(client, db_session, auth_user):
    """Update is_active field via PATCH."""
    user, headers = auth_user
    char = make_character(user=user)
    session = make_session(user=user, character=char, is_active=True)
    db_session.add_all([char, session])
    await db_session.flush()

    body = {"is_active": False}
    resp = await client.patch(f"{BASE}/{session.id}", json=body, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


# ===========================================================================
# PATCH /api/v1/sessions/{session_id}/state
# ===========================================================================


async def test_update_session_state_happy(client, db_session, auth_user, monkeypatch):
    """Update session state in Redis."""
    user, headers = auth_user
    from app.services.redis_service import session_service

    updated_state = {"state": {"hp": 15, "location": "Dungeon"}}
    monkeypatch.setattr(
        session_service, "update_session_state", AsyncMock(return_value=updated_state)
    )
    mock_refresh = AsyncMock()
    monkeypatch.setattr(session_service, "refresh_ttl", mock_refresh)

    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([char, session])
    await db_session.flush()

    body = {"current_location": "Dungeon", "state_data": {"hp": 15}}
    resp = await client.patch(f"{BASE}/{session.id}/state", json=body, headers=headers)
    assert resp.status_code == 200
    mock_refresh.assert_awaited_once_with(session.id)


async def test_update_session_state_session_not_found(client, db_session, auth_headers):
    """Session doesn't exist in DB → 404."""
    fake_id = uuid.uuid4()
    body = {"current_location": "Nowhere"}
    resp = await client.patch(f"{BASE}/{fake_id}/state", json=body, headers=auth_headers)
    assert resp.status_code == 404


async def test_update_session_state_redis_not_found(client, db_session, auth_user, monkeypatch):
    """Session exists in DB but not in Redis → 404."""
    user, headers = auth_user
    from app.services.redis_service import session_service

    monkeypatch.setattr(session_service, "update_session_state", AsyncMock(return_value=None))

    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([char, session])
    await db_session.flush()

    body = {"state_data": {"hp": 10}}
    resp = await client.patch(f"{BASE}/{session.id}/state", json=body, headers=headers)
    assert resp.status_code == 404
    assert "Redis" in resp.json()["detail"]


async def test_update_session_state_location_only(client, db_session, auth_user, monkeypatch):
    """Update only the location, no state_data."""
    user, headers = auth_user
    from app.services.redis_service import session_service

    updated_state = {"state": {"location": "Forest"}}
    monkeypatch.setattr(
        session_service, "update_session_state", AsyncMock(return_value=updated_state)
    )
    monkeypatch.setattr(session_service, "refresh_ttl", AsyncMock())

    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([char, session])
    await db_session.flush()

    body = {"current_location": "Forest"}
    resp = await client.patch(f"{BASE}/{session.id}/state", json=body, headers=headers)
    assert resp.status_code == 200


# ===========================================================================
# POST /api/v1/sessions/{session_id}/end
# ===========================================================================


async def test_end_session_happy(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user)
    session = make_session(user=user, character=char, is_active=True)
    db_session.add_all([char, session])
    await db_session.flush()

    resp = await client.post(f"{BASE}/{session.id}/end", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_end_session_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.post(f"{BASE}/{fake_id}/end", headers=auth_headers)
    assert resp.status_code == 404


# ===========================================================================
# DELETE /api/v1/sessions/{session_id}
# ===========================================================================


async def test_delete_session_happy(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([char, session])
    await db_session.flush()

    resp = await client.delete(f"{BASE}/{session.id}", headers=headers)
    assert resp.status_code == 204


async def test_delete_session_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.delete(f"{BASE}/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_delete_session_cleans_redis(client, db_session, auth_user, monkeypatch):
    """Verify that Redis delete_session_state is called during deletion."""
    user, headers = auth_user
    from app.services.redis_service import session_service

    mock_delete = AsyncMock()
    monkeypatch.setattr(session_service, "delete_session_state", mock_delete)

    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([char, session])
    await db_session.flush()

    resp = await client.delete(f"{BASE}/{session.id}", headers=headers)
    assert resp.status_code == 204
    mock_delete.assert_awaited_once_with(session.id)


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
