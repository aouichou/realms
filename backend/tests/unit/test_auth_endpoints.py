"""Tests for authentication API endpoints (/api/v1/auth)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

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
    # redis property used for lockout checks — return None so it fails open
    monkeypatch.setattr(type(session_service), "redis", property(lambda self: None), raising=False)


# -- helpers ---------------------------------------------------------------

BASE = "/api/v1/auth"
STRONG_PASSWORD = "MyS3cure!Pass42"
STRONG_PASSWORD_2 = "An0ther$ecure99"


# ===========================================================================
# POST /api/v1/auth/register
# ===========================================================================


async def test_register_happy_path(client):
    body = {
        "username": "herouser",
        "email": "hero@example.com",
        "password": STRONG_PASSWORD,
    }
    resp = await client.post(f"{BASE}/register", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "herouser"
    assert data["user"]["email"] == "hero@example.com"
    assert data["user"]["is_guest"] is False


async def test_register_returns_user_data(client):
    body = {
        "username": "datauser",
        "email": "data@example.com",
        "password": STRONG_PASSWORD,
    }
    resp = await client.post(f"{BASE}/register", json=body)
    assert resp.status_code == 200
    data = resp.json()
    user = data["user"]
    assert "id" in user
    assert "created_at" in user
    # Validate it's a valid UUID
    uuid.UUID(user["id"])


async def test_register_duplicate_email(client):
    body = {
        "username": "first_user",
        "email": "dupe@example.com",
        "password": STRONG_PASSWORD,
    }
    resp1 = await client.post(f"{BASE}/register", json=body)
    assert resp1.status_code == 200

    body2 = {
        "username": "second_user",
        "email": "dupe@example.com",
        "password": STRONG_PASSWORD_2,
    }
    resp2 = await client.post(f"{BASE}/register", json=body2)
    assert resp2.status_code == 400
    assert "email" in resp2.json()["detail"].lower()


async def test_register_duplicate_username(client):
    body = {
        "username": "samename",
        "email": "unique1@example.com",
        "password": STRONG_PASSWORD,
    }
    resp1 = await client.post(f"{BASE}/register", json=body)
    assert resp1.status_code == 200

    body2 = {
        "username": "samename",
        "email": "unique2@example.com",
        "password": STRONG_PASSWORD_2,
    }
    resp2 = await client.post(f"{BASE}/register", json=body2)
    assert resp2.status_code == 400
    assert "username" in resp2.json()["detail"].lower()


async def test_register_weak_password_too_short(client):
    body = {
        "username": "shortpw",
        "email": "short@example.com",
        "password": "Ab1!",  # too short
    }
    resp = await client.post(f"{BASE}/register", json=body)
    assert resp.status_code == 422  # validation error


async def test_register_weak_password_common(client):
    body = {
        "username": "commonpw",
        "email": "common@example.com",
        "password": "password1234",  # too common / weak
    }
    resp = await client.post(f"{BASE}/register", json=body)
    assert resp.status_code == 422


# ===========================================================================
# POST /api/v1/auth/login
# ===========================================================================


async def test_login_happy_path(client):
    # Register first
    reg_body = {
        "username": "loginuser",
        "email": "login@example.com",
        "password": STRONG_PASSWORD,
    }
    reg = await client.post(f"{BASE}/register", json=reg_body)
    assert reg.status_code == 200

    # Now login
    login_body = {
        "email": "login@example.com",
        "password": STRONG_PASSWORD,
    }
    resp = await client.post(f"{BASE}/login", json=login_body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@example.com"


async def test_login_wrong_password(client):
    # Register first
    reg_body = {
        "username": "wrongpwuser",
        "email": "wrongpw@example.com",
        "password": STRONG_PASSWORD,
    }
    reg = await client.post(f"{BASE}/register", json=reg_body)
    assert reg.status_code == 200

    login_body = {
        "email": "wrongpw@example.com",
        "password": "TotallyWr0ng!Pass",
    }
    resp = await client.post(f"{BASE}/login", json=login_body)
    assert resp.status_code == 401


async def test_login_nonexistent_email(client):
    login_body = {
        "email": "nobody@example.com",
        "password": STRONG_PASSWORD,
    }
    resp = await client.post(f"{BASE}/login", json=login_body)
    assert resp.status_code == 401


# ===========================================================================
# POST /api/v1/auth/guest
# ===========================================================================


async def test_guest_creation(client):
    resp = await client.post(f"{BASE}/guest")
    assert resp.status_code == 200
    data = resp.json()
    assert "guest_token" in data
    assert data["user"]["is_guest"] is True
    assert data["user"]["username"].startswith("Guest_")


# ===========================================================================
# POST /api/v1/auth/claim-guest
# ===========================================================================


async def test_claim_guest_happy_path(client):
    # Create guest
    guest_resp = await client.post(f"{BASE}/guest")
    assert guest_resp.status_code == 200
    guest_token = guest_resp.json()["guest_token"]

    # Claim it
    claim_body = {
        "guest_token": guest_token,
        "email": "claimed@example.com",
        "username": "claimeduser",
        "password": STRONG_PASSWORD,
    }
    resp = await client.post(f"{BASE}/claim-guest", json=claim_body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["is_guest"] is False
    assert data["user"]["username"] == "claimeduser"
    assert data["user"]["email"] == "claimed@example.com"


async def test_claim_guest_nonexistent_token(client):
    claim_body = {
        "guest_token": "nonexistent_token_xyz",
        "email": "claim@example.com",
        "username": "claimuser",
        "password": STRONG_PASSWORD,
    }
    resp = await client.post(f"{BASE}/claim-guest", json=claim_body)
    assert resp.status_code == 404


async def test_claim_guest_email_taken(client):
    # Register a real user with this email
    reg_body = {
        "username": "emailowner",
        "email": "taken@example.com",
        "password": STRONG_PASSWORD,
    }
    reg = await client.post(f"{BASE}/register", json=reg_body)
    assert reg.status_code == 200

    # Create guest
    guest_resp = await client.post(f"{BASE}/guest")
    guest_token = guest_resp.json()["guest_token"]

    # Try to claim with taken email
    claim_body = {
        "guest_token": guest_token,
        "email": "taken@example.com",
        "username": "newname",
        "password": STRONG_PASSWORD_2,
    }
    resp = await client.post(f"{BASE}/claim-guest", json=claim_body)
    assert resp.status_code == 400
    assert "email" in resp.json()["detail"].lower()


# ===========================================================================
# POST /api/v1/auth/logout
# ===========================================================================


async def test_logout(client):
    resp = await client.post(f"{BASE}/logout")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Successfully logged out"


async def test_logout_without_cookie(client):
    """Logout should always return 200 even without a refresh token cookie."""
    resp = await client.post(f"{BASE}/logout")
    assert resp.status_code == 200
