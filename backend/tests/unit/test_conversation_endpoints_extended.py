"""Extended tests for conversation endpoints (/api/v1/conversations).

Complements test_conversation_endpoints.py with coverage for:
- POST /conversations/start — start a new conversation
- POST /conversations/action — player action / DM response
- GET  /conversations/{session_id} — redis source
- GET  /conversations/{session_id}/recent — edge cases
- Error paths, pagination
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from tests.factories import make_character, make_message, make_session, make_user

# -- Strip problematic middleware ------------------------------------------


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
    monkeypatch.setattr(session_service, "get_conversation_history", AsyncMock(return_value=[]))
    monkeypatch.setattr(session_service, "update_session_state", AsyncMock(return_value={}))
    monkeypatch.setattr(session_service, "refresh_ttl", AsyncMock())
    monkeypatch.setattr(session_service, "delete_session_state", AsyncMock())
    monkeypatch.setattr(session_service, "revoke_token", AsyncMock())
    monkeypatch.setattr(session_service, "is_token_revoked", AsyncMock(return_value=False))
    monkeypatch.setattr(session_service, "add_message_to_history", AsyncMock())
    monkeypatch.setattr(session_service, "clear_conversation_history", AsyncMock())


BASE = "/api/v1/conversations"


async def _create_session_in_db(db_session, **session_kw):
    """Helper: create user + character + game session."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char, **session_kw)
    db_session.add_all([user, char, session])
    await db_session.flush()
    return user, char, session


# ===========================================================================
# POST /conversations/start
# ===========================================================================


async def test_start_conversation_happy(client, db_session):
    """Start a new conversation for a fresh session."""
    _user, char, session = await _create_session_in_db(db_session)

    resp = await client.post(f"{BASE}/start", json={"session_id": str(session.id)})
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert char.name in data["response"]


async def test_start_conversation_already_has_messages(client, db_session):
    """Starting a conversation with existing messages should fail."""
    _user, _char, session = await _create_session_in_db(db_session)

    msg = make_message(session=session, role="assistant", content="Previous message")
    db_session.add(msg)
    await db_session.flush()

    resp = await client.post(f"{BASE}/start", json={"session_id": str(session.id)})
    assert resp.status_code == 400
    assert "already has messages" in resp.json()["detail"]


async def test_start_conversation_session_not_found(client, db_session):
    """Non-existent session should return 404."""
    random_id = str(uuid.uuid4())
    resp = await client.post(f"{BASE}/start", json={"session_id": random_id})
    assert resp.status_code == 404


async def test_start_conversation_french(client, db_session):
    """French language opening narration."""
    _user, char, session = await _create_session_in_db(db_session)

    with patch("app.i18n.get_language", return_value="fr"):
        resp = await client.post(f"{BASE}/start", json={"session_id": str(session.id)})
        assert resp.status_code == 200
        data = resp.json()
        assert "Bienvenue" in data["response"]


# ===========================================================================
# POST /conversations/action  —  main DM endpoint
# ===========================================================================


async def test_action_character_not_found(client, db_session):
    """Action with non-existent character should 404."""
    _user, _char, session = await _create_session_in_db(db_session)

    body = {
        "session_id": str(session.id),
        "character_id": str(uuid.uuid4()),
        "action": "I look around.",
    }
    resp = await client.post(f"{BASE}/action", json=body)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Character not found"


async def test_action_happy_path(client, db_session):
    """Happy path for player action → DM response."""
    _user, char, session = await _create_session_in_db(db_session)

    mock_dm = AsyncMock()
    mock_dm.narrate = AsyncMock(
        return_value={
            "narration": "You see a dark corridor ahead.",
            "tokens_used": 42,
        }
    )

    mock_image_svc = MagicMock()
    mock_image_svc.is_significant_scene = MagicMock(return_value=(False, 0.0, None))

    with (
        patch("app.api.v1.endpoints.conversations.DMEngine", return_value=mock_dm),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=mock_image_svc,
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=(None, None, None, None),
        ),
        patch("app.api.v1.endpoints.conversations.MemoryCaptureService") as mock_mem,
        patch("app.services.memory_service.MemoryService") as mock_mem_svc_cls,
    ):
        mock_mem.capture_combat_event = AsyncMock()
        mock_mem.capture_dialogue = AsyncMock()
        mock_mem_svc_inst = MagicMock()
        mock_mem_svc_inst.store_memory = AsyncMock()
        mock_mem_svc_inst.get_context_for_ai = AsyncMock(return_value=None)
        mock_mem_svc_cls.return_value = mock_mem_svc_inst

        body = {
            "session_id": str(session.id),
            "character_id": str(char.id),
            "action": "I open the door.",
        }
        resp = await client.post(f"{BASE}/action", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "You see a dark corridor ahead."
        assert data["tokens_used"] == 42


async def test_action_with_roll_result(client, db_session):
    """When the player provides a roll result, it should be formatted into the action."""
    _user, char, session = await _create_session_in_db(db_session)

    mock_dm = AsyncMock()
    mock_dm.narrate = AsyncMock(
        return_value={
            "narration": "The lock clicks open.",
            "tokens_used": 30,
        }
    )

    mock_image_svc = MagicMock()
    mock_image_svc.is_significant_scene = MagicMock(return_value=(False, 0.0, None))

    with (
        patch("app.api.v1.endpoints.conversations.DMEngine", return_value=mock_dm),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=mock_image_svc,
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=(None, None, None, None),
        ),
        patch("app.api.v1.endpoints.conversations.MemoryCaptureService") as mock_mem,
        patch("app.services.memory_service.MemoryService") as mock_mem_svc_cls,
    ):
        mock_mem.capture_combat_event = AsyncMock()
        mock_mem.capture_dialogue = AsyncMock()
        mock_mem_svc_inst = MagicMock()
        mock_mem_svc_inst.store_memory = AsyncMock()
        mock_mem_svc_inst.get_context_for_ai = AsyncMock(return_value=None)
        mock_mem_svc_cls.return_value = mock_mem_svc_inst

        body = {
            "session_id": str(session.id),
            "character_id": str(char.id),
            "action": "I pick the lock.",
            "roll_result": {
                "type": "check",
                "total": 18,
                "roll": 15,
                "modifier": 3,
                "success": True,
            },
        }
        resp = await client.post(f"{BASE}/action", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data


async def test_action_empty_narration_fallback(client, db_session):
    """If DM engine returns empty narration, a fallback should be used."""
    _user, char, session = await _create_session_in_db(db_session)

    mock_dm = AsyncMock()
    mock_dm.narrate = AsyncMock(
        return_value={
            "narration": "",
            "tokens_used": 0,
        }
    )

    mock_image_svc = MagicMock()
    mock_image_svc.is_significant_scene = MagicMock(return_value=(False, 0.0, None))

    with (
        patch("app.api.v1.endpoints.conversations.DMEngine", return_value=mock_dm),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=mock_image_svc,
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=(None, None, None, None),
        ),
        patch("app.api.v1.endpoints.conversations.MemoryCaptureService") as mock_mem,
        patch("app.services.memory_service.MemoryService") as mock_mem_svc_cls,
    ):
        mock_mem.capture_combat_event = AsyncMock()
        mock_mem.capture_dialogue = AsyncMock()
        mock_mem_svc_inst = MagicMock()
        mock_mem_svc_inst.store_memory = AsyncMock()
        mock_mem_svc_inst.get_context_for_ai = AsyncMock(return_value=None)
        mock_mem_svc_cls.return_value = mock_mem_svc_inst

        body = {
            "session_id": str(session.id),
            "character_id": str(char.id),
            "action": "I wait.",
        }
        resp = await client.post(f"{BASE}/action", json=body)
        assert resp.status_code == 200
        data = resp.json()
        # Fallback narration
        assert len(data["response"]) > 0


# ===========================================================================
# GET /conversations/{session_id} — redis source
# ===========================================================================


async def test_get_history_redis_source(client, db_session, monkeypatch):
    """Reading from redis source should use session_service."""
    from app.services.redis_service import session_service

    _user, _char, session = await _create_session_in_db(db_session)

    fake_messages = [
        {"role": "user", "content": "Hello", "tokens_used": 5, "timestamp": "2026-01-01T00:00:00"},
        {
            "role": "assistant",
            "content": "Hi!",
            "tokens_used": 3,
            "timestamp": "2026-01-01T00:00:01",
        },
    ]
    monkeypatch.setattr(
        session_service, "get_conversation_history", AsyncMock(return_value=fake_messages)
    )

    resp = await client.get(f"{BASE}/{session.id}", params={"source": "redis"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_messages"] == 2
    assert data["messages"][0]["role"] == "user"


async def test_get_history_with_pagination(client, db_session):
    """Pagination params on database source."""
    _user, _char, session = await _create_session_in_db(db_session)

    for i in range(5):
        db_session.add(make_message(session=session, content=f"msg {i}"))
    await db_session.flush()

    resp = await client.get(
        f"{BASE}/{session.id}", params={"limit": 2, "offset": 0, "source": "database"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_messages"] == 5
    assert len(data["messages"]) == 2


# ===========================================================================
# GET /conversations/{session_id}/recent — edge cases
# ===========================================================================


async def test_get_recent_messages_large_count(client, db_session):
    """Requesting more messages than exist should just return all."""
    _user, _char, session = await _create_session_in_db(db_session)
    db_session.add(make_message(session=session, content="Only one"))
    await db_session.flush()

    resp = await client.get(f"{BASE}/{session.id}/recent", params={"count": 100})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


# ===========================================================================
# DELETE /conversations/{session_id} — with redis
# ===========================================================================


async def test_delete_conversation_with_redis(client, db_session, monkeypatch):
    from app.services.redis_service import session_service

    _user, _char, session = await _create_session_in_db(db_session)

    mock_clear = AsyncMock()
    monkeypatch.setattr(session_service, "clear_conversation_history", mock_clear)

    resp = await client.delete(f"{BASE}/{session.id}", params={"include_redis": True})
    assert resp.status_code == 204
    mock_clear.assert_awaited_once()


async def test_delete_conversation_without_redis(client, db_session, monkeypatch):
    from app.services.redis_service import session_service

    _user, _char, session = await _create_session_in_db(db_session)

    mock_clear = AsyncMock()
    monkeypatch.setattr(session_service, "clear_conversation_history", mock_clear)

    resp = await client.delete(f"{BASE}/{session.id}", params={"include_redis": False})
    assert resp.status_code == 204
    mock_clear.assert_not_awaited()


# ===========================================================================
# POST /conversations/messages — token tracking
# ===========================================================================


async def test_create_message_with_scene_image(client, db_session):
    _user, _char, session = await _create_session_in_db(db_session)

    body = {
        "session_id": str(session.id),
        "role": "assistant",
        "content": "A dragon appears before you!",
        "tokens_used": 25,
        "scene_image_url": "https://example.com/dragon.png",
    }
    resp = await client.post(f"{BASE}/messages", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["scene_image_url"] == "https://example.com/dragon.png"


# ===========================================================================
# GET /api/v1/random/status — random pool status
# ===========================================================================


async def test_random_pool_status(client):
    """Cover the remaining path for random_status.py."""
    mock_status = {
        "enabled": False,
        "api_available": False,
        "pool_size": 0,
        "min_threshold": 100,
        "is_refilling": False,
        "source": "pseudo-random",
    }
    with patch("app.api.v1.endpoints.random_status.random_pool") as mock_pool:
        mock_pool.get_pool_status = AsyncMock(return_value=mock_status)
        resp = await client.get("/api/v1/random/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "pseudo-random"
        assert data["enabled"] is False
