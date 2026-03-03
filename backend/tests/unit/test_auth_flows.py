"""Tests for auth flow coverage — /api/v1/auth.

Covers:
- Guest account creation
- Claim guest account
- Token refresh
- Logout
- Token status
- Forgot / reset password
- get_current_user (/me)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.core.security import create_access_token, create_refresh_token
from tests.factories import make_user

# ── autouse fixtures ─────────────────────────────────────────────────────


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


@pytest_asyncio.fixture(autouse=True)
async def _patch_commit(db_session):
    original = db_session.commit
    db_session.commit = db_session.flush
    yield
    db_session.commit = original


@pytest.fixture(autouse=True)
def _mock_session_service(monkeypatch):
    from app.services.redis_service import session_service

    monkeypatch.setattr(session_service, "connect", AsyncMock())
    monkeypatch.setattr(session_service, "create_session_state", AsyncMock(return_value={}))
    monkeypatch.setattr(session_service, "get_session_state", AsyncMock(return_value=None))
    monkeypatch.setattr(session_service, "update_session_state", AsyncMock(return_value=True))
    monkeypatch.setattr(session_service, "revoke_token", AsyncMock())
    monkeypatch.setattr(session_service, "is_token_revoked", AsyncMock(return_value=False))
    monkeypatch.setattr(session_service, "delete_session_state", AsyncMock(return_value=True))


BASE = "/api/v1/auth"


# ===========================================================================
# POST /auth/guest — create guest account
# ===========================================================================


async def test_create_guest(client, db_session):
    """Create a guest account successfully."""
    with patch(
        "app.api.v1.endpoints.auth.create_guest_user",
        new_callable=AsyncMock,
    ) as mock_create:
        guest = make_user(is_guest=True, guest_token="test-guest-token-123")
        mock_create.return_value = guest

        resp = await client.post(f"{BASE}/guest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["guest_token"] == "test-guest-token-123"


async def test_create_guest_no_token(client, db_session):
    """Guest creation fails if guest_token is None."""
    with patch(
        "app.api.v1.endpoints.auth.create_guest_user",
        new_callable=AsyncMock,
    ) as mock_create:
        guest = make_user(is_guest=True, guest_token=None)
        mock_create.return_value = guest

        resp = await client.post(f"{BASE}/guest")
    assert resp.status_code == 500


# ===========================================================================
# POST /auth/claim-guest
# ===========================================================================


async def test_claim_guest_account(client, db_session):
    """Claiming a guest account with valid token."""
    with patch(
        "app.api.v1.endpoints.auth.claim_guest_account",
        new_callable=AsyncMock,
    ) as mock_claim:
        user = make_user(is_guest=False, email=None)
        mock_claim.return_value = user

        resp = await client.post(
            f"{BASE}/claim-guest",
            json={
                "guest_token": "test-token",
                "email": "test@example.com",
                "username": "newuser",
                "password": "Str0ngP@ssword!X9",
            },
        )
    assert resp.status_code == 200


# ===========================================================================
# POST /auth/refresh
# ===========================================================================


async def test_refresh_no_cookie(client, db_session):
    """No refresh token cookie returns 401."""
    resp = await client.post(f"{BASE}/refresh")
    assert resp.status_code == 401


async def test_refresh_valid_token(client, db_session):
    """Valid refresh token returns new tokens."""
    user = make_user()
    db_session.add(user)
    await db_session.flush()

    refresh = create_refresh_token(data={"sub": str(user.id)})
    resp = await client.post(
        f"{BASE}/refresh",
        cookies={"refresh_token": refresh},
    )
    assert resp.status_code == 200


async def test_refresh_revoked_token(client, db_session, monkeypatch):
    """Revoked refresh token returns 401."""

    user = make_user()
    db_session.add(user)
    await db_session.flush()

    refresh = create_refresh_token(data={"sub": str(user.id)})

    # Mock check_token_revoked to return True
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.check_token_revoked",
        AsyncMock(return_value=True),
    )

    resp = await client.post(
        f"{BASE}/refresh",
        cookies={"refresh_token": refresh},
    )
    assert resp.status_code == 401


# ===========================================================================
# POST /auth/logout
# ===========================================================================


async def test_logout(client, db_session):
    """Logout clears cookies."""
    resp = await client.post(f"{BASE}/logout")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Successfully logged out"


async def test_logout_with_refresh_cookie(client, db_session):
    """Logout with a refresh cookie revokes the token."""
    user = make_user()
    db_session.add(user)
    await db_session.flush()

    refresh = create_refresh_token(data={"sub": str(user.id)})
    resp = await client.post(
        f"{BASE}/logout",
        cookies={"refresh_token": refresh},
    )
    assert resp.status_code == 200


# ===========================================================================
# GET /auth/token-status
# ===========================================================================


async def test_token_status_no_token(client, db_session):
    """No access token cookie returns unauthenticated."""
    resp = await client.get(f"{BASE}/token-status")
    assert resp.status_code == 401
    data = resp.json()
    assert data["authenticated"] is False


async def test_token_status_valid(client, db_session):
    """Valid access token returns expiry info."""
    user = make_user()
    db_session.add(user)
    await db_session.flush()

    token = create_access_token(data={"sub": str(user.id)})
    resp = await client.get(
        f"{BASE}/token-status",
        cookies={"access_token": token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is True
    assert "expires_in_seconds" in data


async def test_token_status_invalid_token(client, db_session):
    """Invalid access token returns unauthenticated."""
    resp = await client.get(
        f"{BASE}/token-status",
        cookies={"access_token": "invalid-jwt-token"},
    )
    assert resp.status_code == 401


# ===========================================================================
# GET /auth/me
# ===========================================================================


async def test_get_me(client, db_session, auth_user):
    """Get current user info."""
    user, headers = auth_user
    resp = await client.get(f"{BASE}/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == user.username


async def test_get_me_unauthenticated(client, db_session):
    """Unauthenticated request to /me returns 401."""
    resp = await client.get(f"{BASE}/me")
    assert resp.status_code in (401, 403)


# ===========================================================================
# POST /auth/forgot-password
# ===========================================================================


async def test_forgot_password_always_succeeds(client, db_session):
    """Forgot password always returns success (anti-enumeration)."""
    with patch(
        "app.api.v1.endpoints.auth.session_service",
    ) as mock_ss:
        mock_ss.redis = None  # no Redis

        resp = await client.post(
            f"{BASE}/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
    assert resp.status_code == 200


# ===========================================================================
# POST /auth/reset-password
# ===========================================================================


async def test_reset_password_no_redis(client, db_session, monkeypatch):
    """Reset password with no Redis returns 503."""
    from app.services.redis_service import session_service

    monkeypatch.setattr(session_service, "_redis", None)

    resp = await client.post(
        f"{BASE}/reset-password",
        json={"token": "fake-token", "password": "NewSecureP@ss1!"},
    )
    assert resp.status_code == 503


async def test_reset_password_invalid_token(client, db_session, monkeypatch):
    """Reset password with invalid/expired token."""
    from app.services.redis_service import session_service

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    monkeypatch.setattr(session_service, "_redis", mock_redis)

    resp = await client.post(
        f"{BASE}/reset-password",
        json={"token": "expired-token", "password": "NewSecureP@ss1!"},
    )
    assert resp.status_code == 400


# ===========================================================================
# POST /auth/register — validation
# ===========================================================================


async def test_register_weak_password(client, db_session):
    """Registration with weak password fails validation."""
    resp = await client.post(
        f"{BASE}/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "short",
        },
    )
    assert resp.status_code == 422


async def test_register_success(client, db_session):
    """Successful registration."""
    with patch(
        "app.api.v1.endpoints.auth.register_user",
        new_callable=AsyncMock,
    ) as mock_reg:
        user = make_user(email=None, username="newuser123")
        mock_reg.return_value = user

        resp = await client.post(
            f"{BASE}/register",
            json={
                "username": "newuser123",
                "email": "new@example.com",
                "password": "Str0ngP@ssword!X9",
            },
        )
    assert resp.status_code == 200


# ===========================================================================
# POST /auth/login
# ===========================================================================


async def test_login_success(client, db_session):
    """Successful login."""
    with patch(
        "app.api.v1.endpoints.auth.authenticate_user",
        new_callable=AsyncMock,
    ) as mock_auth:
        user = make_user(email=None)
        mock_auth.return_value = user

        resp = await client.post(
            f"{BASE}/login",
            json={"email": "test@example.com", "password": "TestPassword123!"},
        )
    assert resp.status_code == 200
