"""Tests for RedisSessionService — redis_service.py"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

from app.services.redis_service import RedisSessionService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SESSION_ID = uuid.uuid4()
CHARACTER_ID = uuid.uuid4()


def _make_service(connected: bool = True) -> tuple[RedisSessionService, AsyncMock]:
    """Create a RedisSessionService with a mock Redis client.

    Returns (service, mock_redis).
    """
    svc = RedisSessionService()
    mock_redis = AsyncMock()
    if connected:
        svc._redis = mock_redis
    return svc, mock_redis


# ---------------------------------------------------------------------------
# connect / disconnect
# ---------------------------------------------------------------------------


class TestConnectDisconnect:
    async def test_connect_creates_client(self):
        svc = RedisSessionService()
        assert svc._redis is None
        with patch("app.services.redis_service.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client
            await svc.connect()
            assert svc._redis is mock_client
            mock_from_url.assert_called_once()

    async def test_connect_idempotent(self):
        svc, mock_redis = _make_service(connected=True)
        with patch("app.services.redis_service.redis.from_url") as mock_from_url:
            await svc.connect()
            mock_from_url.assert_not_called()

    async def test_disconnect(self):
        svc, mock_redis = _make_service()
        await svc.disconnect()
        mock_redis.close.assert_awaited_once()
        assert svc._redis is None

    async def test_disconnect_when_not_connected(self):
        svc = RedisSessionService()
        await svc.disconnect()  # Should not error


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------


class TestKeyHelpers:
    def test_state_key(self):
        svc = RedisSessionService()
        key = svc._get_state_key(SESSION_ID)
        assert str(SESSION_ID) in key
        assert key.startswith(svc.SESSION_STATE_PREFIX)

    def test_history_key(self):
        svc = RedisSessionService()
        key = svc._get_history_key(SESSION_ID)
        assert str(SESSION_ID) in key
        assert key.startswith(svc.SESSION_HISTORY_PREFIX)


# ---------------------------------------------------------------------------
# create_session_state
# ---------------------------------------------------------------------------


class TestCreateSessionState:
    async def test_creates_state(self):
        svc, mock_redis = _make_service()
        state = await svc.create_session_state(
            session_id=SESSION_ID,
            character_id=CHARACTER_ID,
            current_location="Tavern",
        )
        assert state["session_id"] == str(SESSION_ID)
        assert state["character_id"] == str(CHARACTER_ID)
        assert state["current_location"] == "Tavern"
        mock_redis.setex.assert_awaited_once()

    async def test_creates_state_with_companion(self):
        svc, mock_redis = _make_service()
        companion_id = uuid.uuid4()
        state = await svc.create_session_state(
            session_id=SESSION_ID,
            character_id=CHARACTER_ID,
            companion_id=companion_id,
        )
        assert state["companion_id"] == str(companion_id)

    async def test_creates_state_with_initial_state(self):
        svc, mock_redis = _make_service()
        state = await svc.create_session_state(
            session_id=SESSION_ID,
            character_id=CHARACTER_ID,
            initial_state={"hp": 20},
        )
        assert state["state"] == {"hp": 20}

    async def test_create_no_redis(self):
        svc = RedisSessionService()
        svc._redis = None
        with patch.object(svc, "connect", new_callable=AsyncMock):
            state = await svc.create_session_state(
                session_id=SESSION_ID,
                character_id=CHARACTER_ID,
            )
        assert state["session_id"] == str(SESSION_ID)


# ---------------------------------------------------------------------------
# get_session_state
# ---------------------------------------------------------------------------


class TestGetSessionState:
    async def test_returns_state(self):
        svc, mock_redis = _make_service()
        expected = {"session_id": str(SESSION_ID), "state": {}}
        mock_redis.get.return_value = json.dumps(expected)

        result = await svc.get_session_state(SESSION_ID)
        assert result == expected

    async def test_returns_none_when_missing(self):
        svc, mock_redis = _make_service()
        mock_redis.get.return_value = None

        result = await svc.get_session_state(SESSION_ID)
        assert result is None


# ---------------------------------------------------------------------------
# update_session_state
# ---------------------------------------------------------------------------


class TestUpdateSessionState:
    async def test_updates_location(self):
        svc, mock_redis = _make_service()
        existing = {
            "session_id": str(SESSION_ID),
            "current_location": "Tavern",
            "state": {},
            "last_updated": "old",
        }
        mock_redis.get.return_value = json.dumps(existing)

        result = await svc.update_session_state(SESSION_ID, current_location="Forest")
        assert result["current_location"] == "Forest"
        mock_redis.setex.assert_awaited()

    async def test_merges_state_updates(self):
        svc, mock_redis = _make_service()
        existing = {
            "session_id": str(SESSION_ID),
            "current_location": "Tavern",
            "state": {"hp": 20},
            "last_updated": "old",
        }
        mock_redis.get.return_value = json.dumps(existing)

        result = await svc.update_session_state(SESSION_ID, state_updates={"gold": 100})
        assert result["state"]["hp"] == 20
        assert result["state"]["gold"] == 100

    async def test_returns_none_when_no_session(self):
        svc, mock_redis = _make_service()
        mock_redis.get.return_value = None

        result = await svc.update_session_state(SESSION_ID)
        assert result is None


# ---------------------------------------------------------------------------
# delete_session_state
# ---------------------------------------------------------------------------


class TestDeleteSessionState:
    async def test_deletes(self):
        svc, mock_redis = _make_service()
        mock_redis.delete.return_value = 2  # state + history deleted

        result = await svc.delete_session_state(SESSION_ID)
        assert result is True
        mock_redis.delete.assert_awaited_once()

    async def test_returns_false_not_found(self):
        svc, mock_redis = _make_service()
        mock_redis.delete.return_value = 0

        result = await svc.delete_session_state(SESSION_ID)
        assert result is False

    async def test_returns_false_no_redis(self):
        svc = RedisSessionService()
        svc._redis = None
        with patch.object(svc, "connect", new_callable=AsyncMock):
            result = await svc.delete_session_state(SESSION_ID)
        assert result is False


# ---------------------------------------------------------------------------
# add_message_to_history
# ---------------------------------------------------------------------------


class TestAddMessageToHistory:
    async def test_adds_message(self):
        svc, mock_redis = _make_service()
        mock_redis.rpush.return_value = 1

        length = await svc.add_message_to_history(SESSION_ID, role="user", content="Hello")
        assert length == 1
        mock_redis.rpush.assert_awaited_once()
        # First message → expire is called
        mock_redis.expire.assert_awaited_once()

    async def test_no_expire_on_subsequent(self):
        svc, mock_redis = _make_service()
        mock_redis.rpush.return_value = 5  # not the first message

        length = await svc.add_message_to_history(SESSION_ID, role="assistant", content="Hi")
        assert length == 5
        mock_redis.expire.assert_not_awaited()

    async def test_returns_zero_no_redis(self):
        svc = RedisSessionService()
        svc._redis = None
        with patch.object(svc, "connect", new_callable=AsyncMock):
            length = await svc.add_message_to_history(SESSION_ID, role="user", content="Hi")
        assert length == 0


# ---------------------------------------------------------------------------
# get_conversation_history
# ---------------------------------------------------------------------------


class TestGetConversationHistory:
    async def test_returns_messages(self):
        svc, mock_redis = _make_service()
        msgs = [
            json.dumps({"role": "user", "content": "Hello"}),
            json.dumps({"role": "assistant", "content": "Hi"}),
        ]
        mock_redis.lrange.return_value = msgs

        result = await svc.get_conversation_history(SESSION_ID)
        assert len(result) == 2
        # Reversed (newest first)
        assert result[0]["role"] == "assistant"

    async def test_empty_when_no_redis(self):
        svc = RedisSessionService()
        svc._redis = None
        with patch.object(svc, "connect", new_callable=AsyncMock):
            result = await svc.get_conversation_history(SESSION_ID)
        assert result == []


# ---------------------------------------------------------------------------
# clear_conversation_history
# ---------------------------------------------------------------------------


class TestClearConversationHistory:
    async def test_clears(self):
        svc, mock_redis = _make_service()
        mock_redis.delete.return_value = 1

        result = await svc.clear_conversation_history(SESSION_ID)
        assert result is True

    async def test_returns_false_not_found(self):
        svc, mock_redis = _make_service()
        mock_redis.delete.return_value = 0

        result = await svc.clear_conversation_history(SESSION_ID)
        assert result is False

    async def test_returns_false_no_redis(self):
        svc = RedisSessionService()
        svc._redis = None
        with patch.object(svc, "connect", new_callable=AsyncMock):
            result = await svc.clear_conversation_history(SESSION_ID)
        assert result is False


# ---------------------------------------------------------------------------
# refresh_ttl
# ---------------------------------------------------------------------------


class TestRefreshTTL:
    async def test_refreshes(self):
        svc, mock_redis = _make_service()
        mock_redis.expire.return_value = 1

        result = await svc.refresh_ttl(SESSION_ID)
        assert result is True
        assert mock_redis.expire.await_count == 2  # state + history

    async def test_returns_false_not_found(self):
        svc, mock_redis = _make_service()
        mock_redis.expire.return_value = 0

        result = await svc.refresh_ttl(SESSION_ID)
        assert result is False

    async def test_returns_false_no_redis(self):
        svc = RedisSessionService()
        svc._redis = None
        with patch.object(svc, "connect", new_callable=AsyncMock):
            result = await svc.refresh_ttl(SESSION_ID)
        assert result is False


# ---------------------------------------------------------------------------
# Guest token management
# ---------------------------------------------------------------------------


class TestGuestTokens:
    async def test_store_guest_token(self):
        svc, mock_redis = _make_service()
        await svc.store_guest_token("token123", "user-abc")
        mock_redis.setex.assert_awaited_once()

    async def test_get_guest_user_id(self):
        svc, mock_redis = _make_service()
        mock_redis.get.return_value = "user-abc"
        result = await svc.get_guest_user_id("token123")
        assert result == "user-abc"

    async def test_get_guest_user_id_no_redis(self):
        svc = RedisSessionService()
        svc._redis = None
        with patch.object(svc, "connect", new_callable=AsyncMock):
            result = await svc.get_guest_user_id("token123")
        assert result is None

    async def test_delete_guest_token(self):
        svc, mock_redis = _make_service()
        await svc.delete_guest_token("token123")
        mock_redis.delete.assert_awaited_once()

    async def test_store_no_redis(self):
        svc = RedisSessionService()
        svc._redis = None
        with patch.object(svc, "connect", new_callable=AsyncMock):
            await svc.store_guest_token("t", "u")  # should not raise

    async def test_delete_no_redis(self):
        svc = RedisSessionService()
        svc._redis = None
        with patch.object(svc, "connect", new_callable=AsyncMock):
            await svc.delete_guest_token("t")  # should not raise


# ---------------------------------------------------------------------------
# Token revocation
# ---------------------------------------------------------------------------


class TestTokenRevocation:
    async def test_revoke_token(self):
        svc, mock_redis = _make_service()
        await svc.revoke_token("jti-123", expires_in=3600)
        mock_redis.setex.assert_awaited_once()
        args = mock_redis.setex.call_args
        assert "jti-123" in args[0][0]

    async def test_is_token_revoked_true(self):
        svc, mock_redis = _make_service()
        mock_redis.exists.return_value = 1
        result = await svc.is_token_revoked("jti-123")
        assert result is True

    async def test_is_token_revoked_false(self):
        svc, mock_redis = _make_service()
        mock_redis.exists.return_value = 0
        result = await svc.is_token_revoked("jti-123")
        assert result is False

    async def test_is_token_revoked_no_redis(self):
        svc = RedisSessionService()
        svc._redis = None
        with patch.object(svc, "connect", new_callable=AsyncMock):
            result = await svc.is_token_revoked("jti-123")
        assert result is False

    async def test_revoke_no_redis(self):
        svc = RedisSessionService()
        svc._redis = None
        with patch.object(svc, "connect", new_callable=AsyncMock):
            await svc.revoke_token("jti", 100)  # should not raise


# ---------------------------------------------------------------------------
# redis property
# ---------------------------------------------------------------------------


class TestRedisProperty:
    def test_returns_none_initially(self):
        svc = RedisSessionService()
        assert svc.redis is None

    def test_returns_client_when_set(self):
        svc, mock_redis = _make_service()
        assert svc.redis is mock_redis
