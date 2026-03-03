"""Tests for auth middleware functions."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.security import create_access_token
from app.middleware.auth import (
    get_current_registered_user,
    get_current_user,
    get_optional_user,
    get_token_from_request,
)
from tests.factories import make_user

# ---------------------------------------------------------------------------
# get_token_from_request
# ---------------------------------------------------------------------------


class TestGetTokenFromRequest:
    def test_prefers_cookie_over_bearer(self):
        request = MagicMock()
        creds = MagicMock()
        creds.credentials = "bearer-token"
        result = get_token_from_request(
            request, credentials=creds, access_token_cookie="cookie-token"
        )
        assert result == "cookie-token"

    def test_falls_back_to_bearer(self):
        request = MagicMock()
        creds = MagicMock()
        creds.credentials = "bearer-token"
        result = get_token_from_request(request, credentials=creds, access_token_cookie=None)
        assert result == "bearer-token"

    def test_returns_none_if_neither(self):
        request = MagicMock()
        result = get_token_from_request(request, credentials=None, access_token_cookie=None)
        assert result is None

    def test_cookie_only(self):
        request = MagicMock()
        result = get_token_from_request(
            request, credentials=None, access_token_cookie="my-cookie-token"
        )
        assert result == "my-cookie-token"


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    async def test_raises_401_no_token(self):
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(db=db, token=None)
        assert exc_info.value.status_code == 401

    async def test_raises_401_invalid_jwt(self):
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(db=db, token="not-a-valid-jwt")
        assert exc_info.value.status_code == 401

    async def test_raises_401_user_not_found(self):
        user_id = str(uuid.uuid4())
        token = create_access_token({"sub": user_id})

        db = AsyncMock()
        with patch("app.middleware.auth.get_user_by_id", new_callable=AsyncMock, return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(db=db, token=token)
            assert exc_info.value.status_code == 401
            assert "not found" in exc_info.value.detail.lower()

    async def test_returns_user_with_valid_token(self):
        user = make_user()
        token = create_access_token({"sub": str(user.id)})

        db = AsyncMock()
        with patch(
            "app.middleware.auth.get_user_by_id",
            new_callable=AsyncMock,
            return_value=user,
        ):
            result = await get_current_user(db=db, token=token)
            assert result.id == user.id

    async def test_raises_401_missing_sub_claim(self):
        token = create_access_token({"data": "no-sub"})
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(db=db, token=token)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_current_registered_user
# ---------------------------------------------------------------------------


class TestGetCurrentRegisteredUser:
    async def test_raises_403_for_guest(self):
        user = make_user(is_guest=True)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_registered_user(current_user=user)
        assert exc_info.value.status_code == 403

    async def test_allows_non_guest(self):
        user = make_user(is_guest=False)
        result = await get_current_registered_user(current_user=user)
        assert result.id == user.id


# ---------------------------------------------------------------------------
# get_optional_user
# ---------------------------------------------------------------------------


class TestGetOptionalUser:
    async def test_returns_none_no_credentials(self):
        db = AsyncMock()
        result = await get_optional_user(credentials=None, db=db)
        assert result is None

    async def test_returns_none_on_invalid_token(self):
        creds = MagicMock()
        creds.credentials = "bad-token"
        db = AsyncMock()
        result = await get_optional_user(credentials=creds, db=db)
        assert result is None

    async def test_returns_user_on_valid_token(self):
        user = make_user()
        token = create_access_token({"sub": str(user.id)})
        creds = MagicMock()
        creds.credentials = token
        db = AsyncMock()

        with patch(
            "app.middleware.auth.get_user_by_id",
            new_callable=AsyncMock,
            return_value=user,
        ):
            result = await get_optional_user(credentials=creds, db=db)
            assert result is not None
            assert result.id == user.id
