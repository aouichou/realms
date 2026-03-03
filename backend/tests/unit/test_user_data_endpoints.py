"""Tests for user data / GDPR endpoints (/api/v1/user)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from tests.factories import make_character, make_session

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


# -- Mock Redis session_service (some auth middleware may touch it) ---------


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

BASE = "/api/v1/user"


# ===========================================================================
# GET /api/v1/user/export
# ===========================================================================


async def test_export_requires_auth(client):
    resp = await client.get(f"{BASE}/export")
    assert resp.status_code == 401


async def test_export_empty_data(client, auth_user):
    user, headers = auth_user

    resp = await client.get(f"{BASE}/export", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["personal_data"]["id"] == str(user.id)
    assert data["personal_data"]["username"] == user.username
    assert data["characters"] == []
    assert data["game_sessions"] == []
    assert "export_date" in data


async def test_export_with_characters(client, db_session, auth_user):
    user, headers = auth_user

    char = make_character(user=user, name="Gandalf")
    db_session.add(char)
    await db_session.flush()

    resp = await client.get(f"{BASE}/export", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["characters"]) == 1
    assert data["characters"][0]["name"] == "Gandalf"


async def test_export_with_sessions(client, db_session, auth_user):
    user, headers = auth_user

    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([char, session])
    await db_session.flush()

    resp = await client.get(f"{BASE}/export", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["game_sessions"]) == 1
    assert data["game_sessions"][0]["id"] == str(session.id)


# ===========================================================================
# DELETE /api/v1/user/account
# ===========================================================================


async def test_delete_account_requires_auth(client):
    resp = await client.delete(f"{BASE}/account")
    assert resp.status_code == 401


async def test_delete_account_happy(client, db_session, auth_user):
    user, headers = auth_user

    resp = await client.delete(f"{BASE}/account", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "successfully" in data["message"].lower()

    # Verify the user was anonymized
    await db_session.refresh(user)
    assert user.username.startswith("deleted_user_")
    assert user.is_active is False
    assert user.password_hash is None


async def test_delete_account_preserves_characters(client, db_session, auth_user):
    user, headers = auth_user

    char = make_character(user=user, name="PreservedHero")
    db_session.add(char)
    await db_session.flush()

    resp = await client.delete(f"{BASE}/account", headers=headers)
    assert resp.status_code == 200

    # Character should still exist
    await db_session.refresh(char)
    assert char.name == "PreservedHero"
