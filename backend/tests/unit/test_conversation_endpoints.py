"""Tests for conversation API endpoints (/api/v1/conversations)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from tests.factories import make_character, make_message, make_session, make_user

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

BASE = "/api/v1/conversations"


async def _create_session_in_db(db_session):
    """Helper: create a user + character + game session and return the session."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()
    return session


# ===========================================================================
# POST /api/v1/conversations/messages
# ===========================================================================


async def test_create_message_happy(client, db_session, auth_headers):
    session = await _create_session_in_db(db_session)

    body = {
        "session_id": str(session.id),
        "role": "user",
        "content": "I open the door carefully.",
        "tokens_used": 15,
    }
    resp = await client.post(f"{BASE}/messages", json=body, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "user"
    assert data["content"] == "I open the door carefully."
    assert data["tokens_used"] == 15
    assert data["session_id"] == str(session.id)


async def test_create_message_without_redis(client, db_session, auth_headers):
    session = await _create_session_in_db(db_session)

    body = {
        "session_id": str(session.id),
        "role": "assistant",
        "content": "The door creaks open revealing a dark corridor.",
    }
    resp = await client.post(f"{BASE}/messages", json=body, params={"save_to_redis": False}, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "assistant"


async def test_create_message_minimal(client, db_session, auth_headers):
    session = await _create_session_in_db(db_session)

    body = {
        "session_id": str(session.id),
        "role": "user",
        "content": "Look around.",
    }
    resp = await client.post(f"{BASE}/messages", json=body, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["tokens_used"] is None  # optional field


async def test_create_message_empty_content(client, db_session, auth_headers):
    session = await _create_session_in_db(db_session)

    body = {
        "session_id": str(session.id),
        "role": "user",
        "content": "",  # min_length=1 should reject this
    }
    resp = await client.post(f"{BASE}/messages", json=body, headers=auth_headers)
    assert resp.status_code == 422


# ===========================================================================
# GET /api/v1/conversations/{session_id}
# ===========================================================================


async def test_get_conversation_history_empty(client, db_session, auth_headers):
    session = await _create_session_in_db(db_session)

    resp = await client.get(f"{BASE}/{session.id}", params={"source": "database"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == str(session.id)
    assert data["messages"] == []
    assert data["total_messages"] == 0


async def test_get_conversation_history_with_messages(client, db_session, auth_headers):
    session = await _create_session_in_db(db_session)

    msg1 = make_message(session=session, role="user", content="Hello!")
    msg2 = make_message(session=session, role="assistant", content="Greetings, adventurer!")
    db_session.add_all([msg1, msg2])
    await db_session.flush()

    resp = await client.get(f"{BASE}/{session.id}", params={"source": "database"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_messages"] == 2
    assert len(data["messages"]) == 2


# ===========================================================================
# GET /api/v1/conversations/{session_id}/recent
# ===========================================================================


async def test_get_recent_messages_empty(client, db_session, auth_headers):
    session = await _create_session_in_db(db_session)

    resp = await client.get(f"{BASE}/{session.id}/recent", params={"count": 5}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data == []


async def test_get_recent_messages_with_data(client, db_session, auth_headers):
    session = await _create_session_in_db(db_session)

    for i in range(5):
        msg = make_message(session=session, content=f"Message {i}")
        db_session.add(msg)
    await db_session.flush()

    resp = await client.get(f"{BASE}/{session.id}/recent", params={"count": 3}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) <= 3


# ===========================================================================
# DELETE /api/v1/conversations/{session_id}
# ===========================================================================


async def test_delete_conversation_history(client, db_session, auth_headers):
    session = await _create_session_in_db(db_session)

    msg = make_message(session=session)
    db_session.add(msg)
    await db_session.flush()

    resp = await client.delete(f"{BASE}/{session.id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_delete_conversation_history_empty(client, db_session, auth_headers):
    """Deleting an empty conversation should still succeed (204)."""
    session = await _create_session_in_db(db_session)

    resp = await client.delete(f"{BASE}/{session.id}", headers=auth_headers)
    assert resp.status_code == 204
