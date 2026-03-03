"""Tests for app.core.security – password hashing, JWT tokens, cookies, revocation."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.security import (
    check_token_revoked,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    set_auth_cookies,
    verify_password,
)

# ── Password hashing ──────────────────────────────────────────────────────


def test_password_hash_and_verify_roundtrip():
    password = "SuperSecret123!"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True


def test_password_hash_different_each_time():
    password = "SamePassword"
    h1 = get_password_hash(password)
    h2 = get_password_hash(password)
    assert h1 != h2  # bcrypt salts each hash differently


def test_verify_wrong_password_returns_false():
    hashed = get_password_hash("correct-password")
    assert verify_password("wrong-password", hashed) is False


# ── Access tokens ──────────────────────────────────────────────────────────


def test_create_access_token_contains_required_fields():
    token = create_access_token({"sub": "user-42"})
    payload = decode_token(token)
    assert "sub" in payload
    assert "exp" in payload
    assert "type" in payload
    assert "jti" in payload
    assert payload["sub"] == "user-42"


def test_access_token_has_type_access():
    token = create_access_token({"sub": "u1"})
    payload = decode_token(token)
    assert payload["type"] == "access"


def test_access_token_custom_expiry():
    token = create_access_token({"sub": "u1"}, expires_delta=timedelta(hours=2))
    payload = decode_token(token)
    # Token should decode fine (not expired) – just verify it parses
    assert payload["sub"] == "u1"


# ── Refresh tokens ─────────────────────────────────────────────────────────


def test_create_refresh_token_has_type_refresh():
    token = create_refresh_token({"sub": "u1"})
    payload = decode_token(token)
    assert payload["type"] == "refresh"
    assert payload["sub"] == "u1"
    assert "jti" in payload


# ── decode_token ───────────────────────────────────────────────────────────


def test_decode_valid_token():
    token = create_access_token({"sub": "user123", "extra": "data"})
    payload = decode_token(token)
    assert payload["sub"] == "user123"
    assert payload["extra"] == "data"


def test_decode_invalid_token_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("not-a-valid-jwt")
    assert exc_info.value.status_code == 401


def test_decode_expired_token_raises_401():
    token = create_access_token({"sub": "test"}, expires_delta=timedelta(minutes=-1))
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401


# ── Cookies ────────────────────────────────────────────────────────────────


def test_set_auth_cookies():
    response = MagicMock()
    set_auth_cookies(response, "access-tok", refresh_token="refresh-tok")
    assert response.set_cookie.call_count == 2
    calls = response.set_cookie.call_args_list
    # First call should set access_token cookie
    assert calls[0].kwargs["key"] == "access_token" or calls[0][1].get("key") == "access_token"


def test_clear_auth_cookies():
    response = MagicMock()
    clear_auth_cookies(response)
    assert response.delete_cookie.call_count == 2


# ── Token revocation ──────────────────────────────────────────────────────


@patch("app.services.redis_service.session_service")
async def test_check_token_revoked_not_revoked(mock_session_svc):
    mock_session_svc.is_token_revoked = AsyncMock(return_value=False)
    result = await check_token_revoked({"jti": "some-jti-value"})
    assert result is False
    mock_session_svc.is_token_revoked.assert_awaited_once_with("some-jti-value")


async def test_check_token_revoked_no_jti():
    result = await check_token_revoked({"sub": "user1"})
    assert result is False
