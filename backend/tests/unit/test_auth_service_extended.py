"""Extended tests for app.services.auth_service — register, login, guest, lockout."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.core.pii_encryption import create_blind_index, encrypt_pii
from app.core.security import get_password_hash
from app.services.auth_service import (
    _check_lockout,
    _clear_failed_attempts,
    _get_failed_attempts,
    _record_failed_attempt,
    authenticate_user,
    claim_guest_account,
    create_guest_user,
    get_user_by_id,
    register_user,
)
from tests.factories import make_user

# ── Patch commit → flush so service code doesn't break the test txn ──────


@pytest_asyncio.fixture(autouse=True)
async def _patch_commit(db_session):
    original = db_session.commit
    db_session.commit = db_session.flush
    yield
    db_session.commit = original


# ── helpers ───────────────────────────────────────────────────────────────


def _make_mock_redis():
    """Create a mock redis object with the methods used by auth_service."""
    redis = AsyncMock()
    redis.zremrangebyscore = AsyncMock(return_value=0)
    redis.zcard = AsyncMock(return_value=0)
    redis.zadd = AsyncMock()
    redis.expire = AsyncMock()
    redis.setex = AsyncMock()
    redis.ttl = AsyncMock(return_value=-2)  # key doesn't exist
    redis.delete = AsyncMock()
    return redis


# ── _get_failed_attempts ──────────────────────────────────────────────────


async def test_get_failed_attempts_no_redis():
    """Should raise 503 when redis is None — fail closed."""
    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = None
        with pytest.raises(HTTPException) as exc_info:
            await _get_failed_attempts("test@example.com")
        assert exc_info.value.status_code == 503


async def test_get_failed_attempts_with_redis():
    """Should call zremrangebyscore and zcard."""
    redis = _make_mock_redis()
    redis.zcard.return_value = 3
    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = redis
        result = await _get_failed_attempts("test@example.com")
    assert result == 3
    redis.zremrangebyscore.assert_called_once()
    redis.zcard.assert_called_once()


# ── _record_failed_attempt ────────────────────────────────────────────────


async def test_record_failed_attempt_no_redis():
    """Should raise 503 when redis is None — fail closed."""
    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = None
        with pytest.raises(HTTPException) as exc_info:
            await _record_failed_attempt("x@y.com")
        assert exc_info.value.status_code == 503


async def test_record_failed_attempt_below_threshold():
    """Under 5 attempts — no lockout."""
    redis = _make_mock_redis()
    redis.zcard.return_value = 2
    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = redis
        remaining, lockout = await _record_failed_attempt("x@y.com")
    assert lockout == 0
    assert remaining == 3  # 5 - 2


async def test_record_failed_attempt_triggers_lockout():
    """At 5 attempts — triggers 15 minute lockout."""
    redis = _make_mock_redis()
    redis.zcard.return_value = 5
    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = redis
        remaining, lockout = await _record_failed_attempt("x@y.com")
    assert lockout == 15 * 60
    redis.setex.assert_called_once()


async def test_record_failed_attempt_10_triggers_30min():
    """At 10 attempts — triggers 30 minute lockout."""
    redis = _make_mock_redis()
    redis.zcard.return_value = 10
    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = redis
        remaining, lockout = await _record_failed_attempt("x@y.com")
    assert lockout == 30 * 60


async def test_record_failed_attempt_15_triggers_60min():
    """At 15 attempts — triggers 60 minute lockout."""
    redis = _make_mock_redis()
    redis.zcard.return_value = 15
    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = redis
        remaining, lockout = await _record_failed_attempt("x@y.com")
    assert lockout == 60 * 60


# ── _check_lockout ────────────────────────────────────────────────────────


async def test_check_lockout_no_redis():
    """Should raise 503 when redis is None — fail closed."""
    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = None
        with pytest.raises(HTTPException) as exc_info:
            await _check_lockout("x@y.com")
        assert exc_info.value.status_code == 503


async def test_check_lockout_not_locked():
    """TTL ≤ 0 means not locked."""
    redis = _make_mock_redis()
    redis.ttl.return_value = -2
    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = redis
        locked, ttl = await _check_lockout("x@y.com")
    assert locked is False


async def test_check_lockout_locked():
    """Positive TTL means locked."""
    redis = _make_mock_redis()
    redis.ttl.return_value = 600
    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = redis
        locked, ttl = await _check_lockout("x@y.com")
    assert locked is True
    assert ttl == 600


# ── _clear_failed_attempts ────────────────────────────────────────────────


async def test_clear_failed_attempts_no_redis():
    """Should return immediately when redis is None."""
    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = None
        await _clear_failed_attempts("x@y.com")  # no error


async def test_clear_failed_attempts_with_redis():
    redis = _make_mock_redis()
    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = redis
        await _clear_failed_attempts("x@y.com")
    assert redis.delete.call_count == 2  # failed + locked keys


# ── create_guest_user ─────────────────────────────────────────────────────


async def test_create_guest_user(db_session):
    """Should create a guest user with a token and Guest_ prefix."""
    user = await create_guest_user(db_session)
    assert user.is_guest is True
    assert user.username.startswith("Guest_")
    assert user.guest_token is not None
    assert len(user.guest_token) > 0
    assert user.id is not None


# ── register_user ─────────────────────────────────────────────────────────


async def test_register_user_success(db_session):
    """Happy path — new user created."""
    user = await register_user(db_session, "alice@example.com", "alice", "SecurePass1!")
    assert user.username == "alice"
    assert user.is_guest is False
    assert user.password_hash is not None
    assert user.email_blind_index is not None


async def test_register_user_duplicate_email(db_session):
    """Should raise 400 for duplicate email."""
    await register_user(db_session, "dup@example.com", "user1", "SecurePass1!")
    with pytest.raises(HTTPException) as exc:
        await register_user(db_session, "dup@example.com", "user2", "SecurePass2!")
    assert exc.value.status_code == 400
    assert "already registered" in exc.value.detail.lower()


async def test_register_user_duplicate_username(db_session):
    """Should raise 400 for duplicate username."""
    await register_user(db_session, "a@a.com", "samename", "SecurePass1!")
    with pytest.raises(HTTPException) as exc:
        await register_user(db_session, "b@b.com", "samename", "SecurePass2!")
    assert exc.value.status_code == 400
    assert "already taken" in exc.value.detail.lower()


# ── authenticate_user ─────────────────────────────────────────────────────


async def test_authenticate_user_success(db_session):
    """Valid credentials should return the user."""
    email = "auth@example.com"
    password = "MyPassword123!"
    user = await register_user(db_session, email, "authuser", password)

    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = _make_mock_redis()
        result = await authenticate_user(db_session, email, password)

    assert result.id == user.id


async def test_authenticate_user_wrong_password(db_session):
    """Wrong password should raise 401."""
    email = "wrongpw@example.com"
    await register_user(db_session, email, "wrongpw_user", "Correct123!")

    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = _make_mock_redis()
        with pytest.raises(HTTPException) as exc:
            await authenticate_user(db_session, email, "Wrong123!")
    assert exc.value.status_code == 401


async def test_authenticate_user_nonexistent_email(db_session):
    """Non-existent email should raise 401 (no enumeration)."""
    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = _make_mock_redis()
        with pytest.raises(HTTPException) as exc:
            await authenticate_user(db_session, "nobody@example.com", "pass")
    assert exc.value.status_code == 401


async def test_authenticate_user_locked_out(db_session):
    """Locked-out user should get 423."""
    email = "locked@example.com"
    await register_user(db_session, email, "locked_user", "SomePass123!")

    redis = _make_mock_redis()
    redis.ttl.return_value = 300  # locked for 5 min

    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = redis
        with pytest.raises(HTTPException) as exc:
            await authenticate_user(db_session, email, "SomePass123!")
    assert exc.value.status_code == 423
    assert "AccountLocked" in str(exc.value.detail)


async def test_authenticate_user_records_failure_and_warns(db_session):
    """Wrong password with remaining <= 2 should include warning."""
    email = "warn@example.com"
    await register_user(db_session, email, "warn_user", "Correct123!")

    redis = _make_mock_redis()
    redis.ttl.return_value = -2  # not locked
    redis.zcard.return_value = 4  # 4 attempts → remaining = 1

    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = redis
        with pytest.raises(HTTPException) as exc:
            await authenticate_user(db_session, email, "Wrong123!")
    assert exc.value.status_code == 401
    detail = exc.value.detail
    assert "warning" in detail or "remaining_attempts" in detail


async def test_authenticate_user_triggers_lockout_on_failure(db_session):
    """5th failed attempt should trigger lockout and raise 423."""
    email = "lockout@example.com"
    await register_user(db_session, email, "lockout_user", "Correct123!")

    redis = _make_mock_redis()
    redis.ttl.return_value = -2  # not locked yet
    redis.zcard.return_value = 5  # hits first lockout threshold

    with patch("app.services.auth_service.session_service") as mock_ss:
        mock_ss.redis = redis
        with pytest.raises(HTTPException) as exc:
            await authenticate_user(db_session, email, "Wrong123!")
    assert exc.value.status_code == 423


# ── claim_guest_account ───────────────────────────────────────────────────


async def test_claim_guest_account_success(db_session):
    """Guest should be converted to registered user."""
    guest = await create_guest_user(db_session)
    token = guest.guest_token

    result = await claim_guest_account(
        db_session, token, "claimed@example.com", "ClaimedUser", "NewPass123!"
    )
    assert result.is_guest is False
    assert result.username == "ClaimedUser"
    assert result.guest_token is None
    assert result.email_blind_index is not None


async def test_claim_guest_account_not_found(db_session):
    """Invalid guest token should raise 404."""
    with pytest.raises(HTTPException) as exc:
        await claim_guest_account(db_session, "invalid-token", "x@x.com", "user", "pass")
    assert exc.value.status_code == 404


async def test_claim_guest_account_email_taken(db_session):
    """Should raise 400 if email is already registered."""
    await register_user(db_session, "taken@example.com", "taken_user", "Pass123!")

    guest = await create_guest_user(db_session)
    with pytest.raises(HTTPException) as exc:
        await claim_guest_account(
            db_session, guest.guest_token, "taken@example.com", "newname", "Pass123!"
        )
    assert exc.value.status_code == 400


# ── get_user_by_id ────────────────────────────────────────────────────────


async def test_get_user_by_id_found(db_session):
    user = make_user()
    db_session.add(user)
    await db_session.flush()

    result = await get_user_by_id(db_session, str(user.id))
    assert result is not None
    assert result.id == user.id


async def test_get_user_by_id_not_found(db_session):
    result = await get_user_by_id(db_session, str(uuid.uuid4()))
    assert result is None
