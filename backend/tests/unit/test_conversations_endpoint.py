"""Comprehensive tests for conversation API endpoints (/api/v1/conversations).

Covers all endpoint functions, error paths and edge cases to maximise
coverage of ``app/api/v1/endpoints/conversations.py``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from tests.factories import (
    make_character,
    make_character_quest,
    make_companion,
    make_message,
    make_quest,
    make_session,
    make_user,
)

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
    original_commit = db_session.commit
    original_rollback = db_session.rollback
    db_session.commit = db_session.flush

    async def _noop_rollback():
        pass

    db_session.rollback = _noop_rollback
    yield
    db_session.commit = original_commit
    db_session.rollback = original_rollback


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


async def _create_full_context(db_session, *, with_quest=False, with_companion=False):
    """Create user, character, session and optionally quest/companion.

    Returns (session, character, user) tuple.
    """
    user = make_user()
    char = make_character(user=user, spell_slots={"1": 2, "2": 1})
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    if with_quest:
        from app.db.models.enums import QuestState

        quest = make_quest(state=QuestState.IN_PROGRESS)
        cq = make_character_quest(character=char, quest=quest)
        db_session.add_all([quest, cq])
        await db_session.flush()

    if with_companion:
        from app.db.models import Creature

        # Create a minimal creature for the FK
        creature = Creature(
            id=99999,
            name="Test Elf Scout",
            creature_type="humanoid",
            cr="0.5",
            hp=16,
            ac=13,
        )
        db_session.add(creature)
        await db_session.flush()

        comp = make_companion(
            character=char,
            creature=creature,
            is_active=True,
            is_alive=True,
        )
        db_session.add(comp)
        await db_session.flush()

    return session, char, user


# ===========================================================================
# POST /api/v1/conversations/messages
# ===========================================================================


class TestCreateMessage:
    async def test_happy_path(self, client, db_session, auth_headers):
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

    async def test_without_redis(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        body = {
            "session_id": str(session.id),
            "role": "assistant",
            "content": "The door creaks open.",
        }
        resp = await client.post(
            f"{BASE}/messages", json=body, params={"save_to_redis": False}, headers=auth_headers
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "assistant"

    async def test_empty_content_rejected(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        body = {"session_id": str(session.id), "role": "user", "content": ""}
        resp = await client.post(f"{BASE}/messages", json=body, headers=auth_headers)
        assert resp.status_code == 422

    async def test_minimal_fields(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        body = {"session_id": str(session.id), "role": "user", "content": "Look."}
        resp = await client.post(f"{BASE}/messages", json=body, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["tokens_used"] is None

    async def test_companion_message(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        companion_id = str(uuid.uuid4())
        body = {
            "session_id": str(session.id),
            "role": "companion",
            "content": "I'll guard the rear!",
            "companion_id": companion_id,
        }
        resp = await client.post(f"{BASE}/messages", json=body, headers=auth_headers)
        assert resp.status_code == 201
        # companion_id is accepted but not stored by create_message service
        assert resp.json()["companion_id"] is None


# ===========================================================================
# POST /api/v1/conversations/start
# ===========================================================================


class TestStartConversation:
    async def test_happy_path_english(self, client, db_session, auth_headers):
        session, char, _ = await _create_full_context(db_session)

        with patch("app.i18n.get_language", return_value="en"):
            resp = await client.post(
                f"{BASE}/start", json={"session_id": str(session.id)}, headers=auth_headers
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "Welcome" in data["response"]
        assert char.name in data["response"]
        assert data["tokens_used"] == 0
        assert data["roll_request"] is None

    async def test_happy_path_french(self, client, db_session, auth_headers):
        session, char, _ = await _create_full_context(db_session)

        with patch("app.i18n.get_language", return_value="fr"):
            resp = await client.post(
                f"{BASE}/start", json={"session_id": str(session.id)}, headers=auth_headers
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "Bienvenue" in data["response"]
        assert char.name in data["response"]

    async def test_session_already_has_messages(self, client, db_session, auth_headers):
        session, _, _ = await _create_full_context(db_session)
        msg = make_message(session=session, content="Old message")
        db_session.add(msg)
        await db_session.flush()

        resp = await client.post(
            f"{BASE}/start", json={"session_id": str(session.id)}, headers=auth_headers
        )
        assert resp.status_code == 400
        assert "already has messages" in resp.json()["detail"]

    async def test_session_not_found(self, client, db_session, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"{BASE}/start", json={"session_id": fake_id}, headers=auth_headers
        )
        assert resp.status_code == 404
        assert "Session not found" in resp.json()["detail"]

    async def test_character_not_found(self, client, db_session, auth_headers):
        """Session exists but its character_id points to nothing."""
        user = make_user()
        # Create session with a nonexistent character_id
        fake_char_id = uuid.uuid4()
        session = make_session(user=user, character=make_character(user=user))
        # Override character_id to a non-existent one after creation
        session.character_id = fake_char_id
        db_session.add_all([user, session])
        await db_session.flush()

        resp = await client.post(
            f"{BASE}/start", json={"session_id": str(session.id)}, headers=auth_headers
        )
        assert resp.status_code == 404
        assert "Character not found" in resp.json()["detail"]

    async def test_uses_current_location(self, client, db_session, auth_headers):
        session, char, _ = await _create_full_context(db_session)
        session.current_location = "The Dragon's Lair"
        await db_session.flush()

        with patch("app.i18n.get_language", return_value="en"):
            resp = await client.post(
                f"{BASE}/start", json={"session_id": str(session.id)}, headers=auth_headers
            )

        assert resp.status_code == 200
        assert "The Dragon's Lair" in resp.json()["response"]

    async def test_default_location_english(self, client, db_session, auth_headers):
        session, char, _ = await _create_full_context(db_session)
        session.current_location = None
        await db_session.flush()

        with patch("app.i18n.get_language", return_value="en"):
            resp = await client.post(
                f"{BASE}/start", json={"session_id": str(session.id)}, headers=auth_headers
            )

        assert resp.status_code == 200
        assert "the beginning of your journey" in resp.json()["response"]

    async def test_default_location_french(self, client, db_session, auth_headers):
        session, char, _ = await _create_full_context(db_session)
        session.current_location = None
        await db_session.flush()

        with patch("app.i18n.get_language", return_value="fr"):
            resp = await client.post(
                f"{BASE}/start", json={"session_id": str(session.id)}, headers=auth_headers
            )

        assert resp.status_code == 200
        assert "le début de votre voyage" in resp.json()["response"]


# ===========================================================================
# POST /api/v1/conversations/action  (heavily mocked)
# ===========================================================================


def _build_action_body(session_id, character_id, action="I look around", roll_result=None):
    body = {
        "character_id": str(character_id),
        "session_id": str(session_id),
        "action": action,
    }
    if roll_result is not None:
        body["roll_result"] = roll_result
    return body


def _mock_dm_narrate(narration="The room is dark and cold.", tokens_used=42, **extra):
    """Return a coroutine-producing mock for DMEngine.narrate."""
    result = {
        "narration": narration,
        "tokens_used": tokens_used,
        **extra,
    }
    mock = AsyncMock(return_value=result)
    return mock


class TestSendPlayerAction:
    """Tests for POST /action – the most complex endpoint."""

    # ── Helpers / fixtures ────────────────────────────────────────────

    @pytest.fixture(autouse=True)
    def _mock_external_services(self, monkeypatch):
        """Patch heavy external dependencies for *every* action test."""
        # DMEngine.narrate
        self._dm_narrate = _mock_dm_narrate()
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            self._dm_narrate,
        )

        # Image detection – never significant by default
        mock_img_service = MagicMock()
        mock_img_service.is_significant_scene.return_value = (False, 0.0, None)
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            lambda: mock_img_service,
        )
        self._mock_img_service = mock_img_service

        # Summarization – never summarise by default
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.SummarizationService.should_summarize",
            lambda count, threshold=10: False,
        )

        # detect_spell_cast – no spell by default
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            AsyncMock(return_value=(None, None, None, None)),
        )

        # detect_roll_request_from_narration – nothing
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.detect_roll_request_from_narration",
            lambda text: None,
        )

        # MemoryCaptureService – no-ops
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            AsyncMock(),
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            AsyncMock(),
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_summary",
            AsyncMock(),
        )

        # MemoryService – no-ops
        mock_memory_svc = AsyncMock()
        mock_memory_svc.get_context_for_ai = AsyncMock(return_value=None)
        mock_memory_svc.store_memory = AsyncMock()
        monkeypatch.setattr(
            "app.services.memory_service.MemoryService.get_context_for_ai",
            mock_memory_svc.get_context_for_ai,
        )
        monkeypatch.setattr(
            "app.services.memory_service.MemoryService.store_memory",
            mock_memory_svc.store_memory,
        )
        self._mock_memory_svc = mock_memory_svc

        # Context window manager – never over limit
        mock_ctx = MagicMock()
        mock_ctx.get_context_stats.return_value = {
            "total_tokens": 100,
            "max_tokens": 4000,
            "usage_percent": 2.5,
            "message_count": 3,
            "is_over_limit": False,
        }
        mock_ctx.prune_messages.return_value = ([], 0)
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.get_context_manager",
            lambda: mock_ctx,
        )
        self._mock_ctx = mock_ctx

        # build_character_stats_context – simple dict
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.build_character_stats_context",
            lambda char: {"str": 16},
        )

        # RollParser – no roll tags by default
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.RollParser.has_roll_tags",
            lambda text: False,
        )

        # Companion service stuff
        monkeypatch.setattr(
            "app.services.provider_selector.provider_selector.get_current_provider",
            MagicMock(return_value=None),
        )

    # ── Basic happy-path tests ────────────────────────────────────────

    async def test_action_happy_path(self, client, db_session, auth_headers):
        session, char, _ = await _create_full_context(db_session)
        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "The room is dark and cold."
        assert data["tokens_used"] == 42

    async def test_action_character_not_found(self, client, db_session, auth_headers):
        session, _, _ = await _create_full_context(db_session)
        body = _build_action_body(session.id, uuid.uuid4())
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 404
        assert "Character not found" in resp.json()["detail"]

    async def test_action_without_session_id(self, client, db_session, auth_headers):
        """When session_id is None, conversation history is skipped."""
        _, char, _ = await _create_full_context(db_session)
        body = {
            "character_id": str(char.id),
            "action": "I look around",
        }
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    # ── Roll result in action ─────────────────────────────────────────

    async def test_action_with_roll_result(self, client, db_session, auth_headers):
        session, char, _ = await _create_full_context(db_session)
        roll = {"type": "check", "total": 18, "roll": 15, "modifier": 3, "success": True}
        body = _build_action_body(session.id, char.id, action="I sneak past", roll_result=roll)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        # DMEngine.narrate should have been called with the augmented action text
        call_kwargs = self._dm_narrate.call_args
        user_action_arg = call_kwargs.kwargs.get(
            "user_action", call_kwargs[1].get("user_action", "")
        )
        assert "ROLL RESULT" in user_action_arg

    async def test_action_with_roll_result_no_success(self, client, db_session, auth_headers):
        session, char, _ = await _create_full_context(db_session)
        roll = {"type": "attack", "total": 7, "roll": 5, "modifier": 2}
        body = _build_action_body(session.id, char.id, action="I swing", roll_result=roll)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    # ── Summarization path ────────────────────────────────────────────

    async def test_action_with_summarization(self, client, db_session, auth_headers, monkeypatch):
        session, char, _ = await _create_full_context(db_session)
        # Add many messages to trigger summarization
        for i in range(12):
            db_session.add(make_message(session=session, content=f"Msg {i}"))
        await db_session.flush()

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.SummarizationService.should_summarize",
            lambda count, threshold=10: True,
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.SummarizationService.get_summarized_context",
            AsyncMock(
                return_value=("Summary of events so far.", [{"role": "user", "content": "hi"}])
            ),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    async def test_action_summarization_failure_fallback(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)
        for i in range(12):
            db_session.add(make_message(session=session, content=f"Msg {i}"))
        await db_session.flush()

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.SummarizationService.should_summarize",
            lambda count, threshold=10: True,
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.SummarizationService.get_summarized_context",
            AsyncMock(side_effect=RuntimeError("Summarization failed")),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        # Should still succeed using fallback
        assert resp.status_code == 200

    async def test_action_summary_memory_capture_failure(
        self, client, db_session, auth_headers, monkeypatch
    ):
        """MemoryCaptureService.capture_summary failure is swallowed."""
        session, char, _ = await _create_full_context(db_session)
        for i in range(12):
            db_session.add(make_message(session=session, content=f"Msg {i}"))
        await db_session.flush()

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.SummarizationService.should_summarize",
            lambda count, threshold=10: True,
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.SummarizationService.get_summarized_context",
            AsyncMock(return_value=("Summary.", [{"role": "user", "content": "hi"}])),
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_summary",
            AsyncMock(side_effect=RuntimeError("memory error")),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    # ── Memory context ────────────────────────────────────────────────

    async def test_action_with_memory_context(self, client, db_session, auth_headers, monkeypatch):
        session, char, _ = await _create_full_context(db_session)
        monkeypatch.setattr(
            "app.services.memory_service.MemoryService.get_context_for_ai",
            AsyncMock(return_value="You met a goblin earlier."),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    async def test_action_memory_fetch_failure(self, client, db_session, auth_headers, monkeypatch):
        session, char, _ = await _create_full_context(db_session)
        monkeypatch.setattr(
            "app.services.memory_service.MemoryService.get_context_for_ai",
            AsyncMock(side_effect=RuntimeError("Redis down")),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        # Memory fetch failure is non-fatal
        assert resp.status_code == 200

    # ── Context window pruning ────────────────────────────────────────

    async def test_action_context_over_limit_prunes(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        mock_ctx = MagicMock()
        mock_ctx.get_context_stats.return_value = {
            "total_tokens": 5000,
            "max_tokens": 4000,
            "usage_percent": 125.0,
            "message_count": 20,
            "is_over_limit": True,
        }
        mock_ctx.prune_messages.return_value = ([{"role": "user", "content": "hi"}], 1000)
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.get_context_manager",
            lambda: mock_ctx,
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        mock_ctx.prune_messages.assert_called_once()

    # ── Empty narration safety check ──────────────────────────────────

    async def test_action_empty_narration_fallback(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(narration=""),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        assert "magical energies" in resp.json()["response"]

    async def test_action_whitespace_narration_fallback(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(narration="   "),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        assert "magical energies" in resp.json()["response"]

    # ── Spell detection ───────────────────────────────────────────────

    async def test_action_spell_cast_detected(self, client, db_session, auth_headers, monkeypatch):
        session, char, _ = await _create_full_context(db_session)
        char.spell_slots = {"1": 2}
        await db_session.flush()

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            AsyncMock(return_value=("Magic Missile", 1, None, None)),
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            MagicMock(return_value=(True, None)),
        )

        body = _build_action_body(session.id, char.id, action="I cast magic missile!")
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    async def test_action_spell_cast_cantrip(self, client, db_session, auth_headers, monkeypatch):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            AsyncMock(return_value=("Fire Bolt", 0, None, None)),
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            MagicMock(return_value=(True, None)),
        )

        body = _build_action_body(session.id, char.id, action="I cast fire bolt!")
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    async def test_action_spell_slot_warning(self, client, db_session, auth_headers, monkeypatch):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            AsyncMock(return_value=("Shield", 1, "No slots remaining!", None)),
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            MagicMock(return_value=(False, "No level 1 slots remaining")),
        )

        body = _build_action_body(session.id, char.id, action="I cast shield")
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["warnings"] is not None
        assert len(data["warnings"]) > 0

    async def test_action_spell_suggestion(self, client, db_session, auth_headers, monkeypatch):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            AsyncMock(return_value=(None, None, None, "Did you mean 'Magic Missile'?")),
        )

        body = _build_action_body(session.id, char.id, action="I cast magic missle")
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["warnings"] is not None
        assert "Did you mean" in data["warnings"][0]

    async def test_action_spell_detection_failure(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            AsyncMock(side_effect=RuntimeError("Spell DB error")),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        # Spell detection failure is non-fatal
        assert resp.status_code == 200

    # ── Roll tag parsing ──────────────────────────────────────────────

    async def test_action_with_roll_tags_player_roll(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        narration = "[ROLL:check STR DC15] You try to lift the boulder."
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(narration=narration),
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.RollParser.has_roll_tags",
            lambda text: True,
        )

        # Mock parse_narration to return a player roll request
        mock_roll_req = MagicMock()
        mock_roll_req.is_player_roll = True
        mock_roll_req.roll_type = MagicMock(value="check")
        mock_roll_req.dice_notation = "1d20"
        mock_roll_req.ability = MagicMock(value="STR")
        mock_roll_req.skill = None
        mock_roll_req.dc = 15
        mock_roll_req.advantage = False
        mock_roll_req.disadvantage = False
        mock_roll_req.description = "Lift the boulder"

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.RollParser.parse_narration",
            lambda text: ("You try to lift the boulder.", [mock_roll_req]),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["roll_request"] is not None
        assert data["roll_request"]["type"] == "check"

    async def test_action_with_roll_tags_npc_roll(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        narration = "[ROLL:NPC attack] The goblin attacks!"
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(narration=narration),
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.RollParser.has_roll_tags",
            lambda text: True,
        )

        mock_roll_req = MagicMock()
        mock_roll_req.is_player_roll = False
        mock_roll_req.roll_type = MagicMock(value="attack")
        mock_roll_req.dice_notation = "1d20+3"
        mock_roll_req.ability = MagicMock(value="STR")
        mock_roll_req.dc = None
        mock_roll_req.advantage = False
        mock_roll_req.disadvantage = False
        mock_roll_req.description = "Goblin attacks"

        mock_roll_result = MagicMock()
        mock_roll_result.notation = "1d20+3"
        mock_roll_result.rolls = [14]
        mock_roll_result.modifier = 3
        mock_roll_result.total = 17
        mock_roll_result.dc = None
        mock_roll_result.success = None
        mock_roll_result.advantage = False
        mock_roll_result.disadvantage = False
        mock_roll_result.is_critical = False
        mock_roll_result.is_critical_fail = False

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.RollParser.parse_narration",
            lambda text: ("The goblin attacks!", [mock_roll_req]),
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.RollExecutor.execute_roll",
            MagicMock(return_value=mock_roll_result),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["rolls"] is not None
        assert data["rolls"][0]["total"] == 17

    async def test_action_npc_roll_execution_failure(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(narration="Roll tags here."),
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.RollParser.has_roll_tags",
            lambda text: True,
        )

        mock_roll_req = MagicMock()
        mock_roll_req.is_player_roll = False
        mock_roll_req.roll_type = MagicMock(value="attack")
        mock_roll_req.dice_notation = "1d20+3"
        mock_roll_req.ability = MagicMock(value="STR")
        mock_roll_req.dc = None
        mock_roll_req.advantage = False
        mock_roll_req.disadvantage = False
        mock_roll_req.description = "Goblin attacks"

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.RollParser.parse_narration",
            lambda text: ("Roll tags here.", [mock_roll_req]),
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.RollExecutor.execute_roll",
            MagicMock(side_effect=RuntimeError("Bad dice")),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        # NPC roll failure is non-fatal
        assert resp.status_code == 200

    # ── Natural language roll detection ───────────────────────────────

    async def test_action_natural_language_roll_detected(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.detect_roll_request_from_narration",
            lambda text: {
                "roll_type": "check",
                "ability": "DEX",
                "skill": "stealth",
                "dc": 14,
                "detected_text": "Make a stealth check",
            },
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["roll_request"] is not None
        assert data["roll_request"]["type"] == "check"
        assert data["roll_request"]["skill"] == "stealth"

    async def test_action_nl_roll_skipped_when_responding_to_roll(
        self, client, db_session, auth_headers, monkeypatch
    ):
        """When player is submitting a roll result, NL detection is skipped."""
        session, char, _ = await _create_full_context(db_session)

        # The detect function should NOT be called when roll_result is provided
        detect_mock = MagicMock(return_value={"roll_type": "check", "detected_text": "check"})
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.detect_roll_request_from_narration",
            detect_mock,
        )

        roll = {"type": "check", "total": 15, "roll": 12, "modifier": 3, "success": True}
        body = _build_action_body(session.id, char.id, action="I sneak past", roll_result=roll)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        # detect_roll_request_from_narration should NOT be called
        detect_mock.assert_not_called()

    async def test_action_nl_roll_skipped_for_i_rolled(
        self, client, db_session, auth_headers, monkeypatch
    ):
        """NL detection skipped when action starts with 'I rolled'."""
        session, char, _ = await _create_full_context(db_session)

        detect_mock = MagicMock(return_value=None)
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.detect_roll_request_from_narration",
            detect_mock,
        )

        body = _build_action_body(session.id, char.id, action="I rolled a 15")
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        detect_mock.assert_not_called()

    # ── Tool-based roll request format ────────────────────────────────

    async def test_action_tool_roll_request_ability_check(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(
                narration="The DM asks for a check.",
                roll_request={
                    "type": "ability_check",
                    "ability_or_skill": "perception",
                    "dc": 12,
                    "advantage": False,
                    "disadvantage": False,
                    "description": "Perception check",
                },
            ),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["roll_request"] is not None
        assert data["roll_request"]["type"] == "check"
        assert data["roll_request"]["skill"] == "perception"
        assert data["roll_request"]["dc"] == 12

    async def test_action_tool_roll_request_saving_throw(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(
                narration="Make a save!",
                roll_request={
                    "type": "saving_throw",
                    "ability_or_skill": "DEX",
                    "dc": 15,
                    "advantage": False,
                    "disadvantage": False,
                    "description": "Dexterity saving throw",
                },
            ),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["roll_request"]["type"] == "save"
        assert data["roll_request"]["ability"] == "DEX"

    async def test_action_tool_roll_request_attack(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(
                narration="Attack!",
                roll_request={
                    "type": "attack",
                    "ability_or_skill": "melee",
                    "dc": None,
                    "advantage": True,
                    "disadvantage": False,
                    "description": "Melee attack",
                },
            ),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["roll_request"]["type"] == "attack"
        assert data["roll_request"]["advantage"] is True

    # ── Image generation ──────────────────────────────────────────────

    async def test_action_significant_scene_generates_image(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        self._mock_img_service.is_significant_scene.return_value = (True, 0.85, "combat")

        mock_image_svc = MagicMock()
        mock_image_svc.generate_scene_image = AsyncMock(
            return_value="https://img.example.com/scene.png"
        )

        body = _build_action_body(session.id, char.id)

        # Patch the locally-imported image_service inside the endpoint function
        with patch.dict(
            "sys.modules",
            {"app.services.image_service": MagicMock(image_service=mock_image_svc)},
        ):
            resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)

        assert resp.status_code == 200

    async def test_action_image_detection_failure(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        self._mock_img_service.is_significant_scene.side_effect = RuntimeError("Model not loaded")

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        # Image detection failure is non-fatal
        assert resp.status_code == 200

    async def test_action_image_generation_failure(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        self._mock_img_service.is_significant_scene.return_value = (True, 0.9, "discovery")

        mock_image_svc = MagicMock()
        mock_image_svc.generate_scene_image = AsyncMock(side_effect=RuntimeError("API error"))

        with patch.dict(
            "sys.modules", {"app.services.image_service": MagicMock(image_service=mock_image_svc)}
        ):
            body = _build_action_body(session.id, char.id)
            resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)

        assert resp.status_code == 200

    # ── Memory capture events ─────────────────────────────────────────

    async def test_action_combat_memory_capture(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(narration="The Goblin attacks! You strike with your sword and hit!"),
        )

        body = _build_action_body(session.id, char.id, action="I attack the goblin")
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    async def test_action_combat_memory_victory(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(narration="Victory! The dragon is defeated and you won the battle!"),
        )

        body = _build_action_body(session.id, char.id, action="I attack the dragon")
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    async def test_action_combat_memory_defeat(self, client, db_session, auth_headers, monkeypatch):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(narration="You have fallen in defeat. Death claims you."),
        )

        body = _build_action_body(session.id, char.id, action="I attack the orc")
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    async def test_action_combat_memory_flee(self, client, db_session, auth_headers, monkeypatch):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(narration="You flee from combat and retreat to safety."),
        )

        body = _build_action_body(session.id, char.id, action="I flee from the battle")
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    async def test_action_dialogue_memory_capture(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        # Narration with NPC dialogue (Name: dialogue format)
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(
                narration='Gandalf: "You shall not pass!" The wizard raises his staff.'
            ),
        )

        body = _build_action_body(session.id, char.id, action="I talk to the wizard")
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    async def test_action_discovery_memory_capture(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(
                narration="You discover a hidden passage behind the bookshelf. You notice ancient runes carved into the wall."
            ),
        )

        body = _build_action_body(session.id, char.id, action="I search the room carefully")
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    async def test_action_generic_interaction_memory(
        self, client, db_session, auth_headers, monkeypatch
    ):
        """Substantial narration without combat/dialogue/discovery keywords => generic interaction."""
        session, char, _ = await _create_full_context(db_session)

        # Long narration without combat/dialogue/discovery keywords
        long_narration = "The wind howls through the empty streets. " * 10
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(narration=long_narration),
        )

        body = _build_action_body(session.id, char.id, action="I walk forward")
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    async def test_action_memory_capture_failure(
        self, client, db_session, auth_headers, monkeypatch
    ):
        """Event memory capture failures are swallowed."""
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(narration="You attack fiercely! Combat ensues!"),
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            AsyncMock(side_effect=RuntimeError("DB error")),
        )

        body = _build_action_body(session.id, char.id, action="I attack")
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    # ── Active quest in context ───────────────────────────────────────

    async def test_action_with_active_quest(self, client, db_session, auth_headers):
        session, char, _ = await _create_full_context(db_session, with_quest=True)

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    # ── Character with background/personality fields ──────────────────

    async def test_action_character_with_full_context(self, client, db_session, auth_headers):
        session, char, _ = await _create_full_context(db_session)
        char.background = "Noble"
        char.personality = "Brave and bold"
        char.background_name = "Noble"
        char.background_description = "You grew up in a castle"
        char.personality_trait = "I'm always polite"
        char.ideal = "Justice"
        char.bond = "My sword"
        char.flaw = "Reckless"
        await db_session.flush()

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    # ── Combined summary + memory context ─────────────────────────────

    async def test_action_combined_context(self, client, db_session, auth_headers, monkeypatch):
        session, char, _ = await _create_full_context(db_session)
        for i in range(12):
            db_session.add(make_message(session=session, content=f"Msg {i}"))
        await db_session.flush()

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.SummarizationService.should_summarize",
            lambda count, threshold=10: True,
        )
        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.SummarizationService.get_summarized_context",
            AsyncMock(return_value=("Summary.", [{"role": "user", "content": "hi"}])),
        )
        monkeypatch.setattr(
            "app.services.memory_service.MemoryService.get_context_for_ai",
            AsyncMock(return_value="Memory context here."),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200

    # ── Companion responses ───────────────────────────────────────────

    async def test_action_companion_responds(self, client, db_session, auth_headers, monkeypatch):
        session, char, _ = await _create_full_context(db_session, with_companion=True)

        mock_provider = MagicMock()
        monkeypatch.setattr(
            "app.services.provider_selector.provider_selector.get_current_provider",
            MagicMock(return_value=mock_provider),
        )

        mock_companion_svc = MagicMock()
        mock_companion_svc.should_companion_respond = AsyncMock(return_value=True)
        mock_companion_svc.generate_companion_response = AsyncMock(return_value="I'll help!")

        with patch(
            "app.services.companion_service.CompanionService",
            return_value=mock_companion_svc,
        ):
            body = _build_action_body(session.id, char.id)
            resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["companion_speech"] == "I'll help!"
        assert data["companion_responses"] is not None

    async def test_action_companion_chooses_not_to_respond(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session, with_companion=True)

        mock_provider = MagicMock()
        monkeypatch.setattr(
            "app.services.provider_selector.provider_selector.get_current_provider",
            MagicMock(return_value=mock_provider),
        )

        mock_companion_svc = MagicMock()
        mock_companion_svc.should_companion_respond = AsyncMock(return_value=False)

        with patch(
            "app.services.companion_service.CompanionService",
            return_value=mock_companion_svc,
        ):
            body = _build_action_body(session.id, char.id)
            resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json()["companion_speech"] is None

    async def test_action_companion_error_non_fatal(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session, with_companion=True)

        mock_provider = MagicMock()
        monkeypatch.setattr(
            "app.services.provider_selector.provider_selector.get_current_provider",
            MagicMock(return_value=mock_provider),
        )

        mock_companion_svc = MagicMock()
        mock_companion_svc.should_companion_respond = AsyncMock(
            side_effect=RuntimeError("AI broken")
        )

        with patch(
            "app.services.companion_service.CompanionService",
            return_value=mock_companion_svc,
        ):
            body = _build_action_body(session.id, char.id)
            resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)

        assert resp.status_code == 200

    async def test_action_no_ai_provider_skips_companions(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session, with_companion=True)

        # Provider returns None
        monkeypatch.setattr(
            "app.services.provider_selector.provider_selector.get_current_provider",
            MagicMock(return_value=None),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["companion_speech"] is None

    # ── quest_complete_id and tool_calls_made ─────────────────────────

    async def test_action_quest_complete(self, client, db_session, auth_headers, monkeypatch):
        session, char, _ = await _create_full_context(db_session)
        quest_id = str(uuid.uuid4())

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(quest_complete_id=quest_id),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["quest_complete_id"] == quest_id

    async def test_action_tool_calls_and_character_updates(
        self, client, db_session, auth_headers, monkeypatch
    ):
        session, char, _ = await _create_full_context(db_session)

        monkeypatch.setattr(
            "app.api.v1.endpoints.conversations.DMEngine.narrate",
            _mock_dm_narrate(
                tool_calls_made=[{"tool": "damage", "args": {"amount": 5}}],
                character_updates={"hp_current": 7},
            ),
        )

        body = _build_action_body(session.id, char.id)
        resp = await client.post(f"{BASE}/action", json=body, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tool_calls_made"] is not None
        assert data["character_updates"] is not None


# ===========================================================================
# GET /api/v1/conversations/{session_id}
# ===========================================================================


class TestGetConversationHistory:
    async def test_from_database_empty(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        resp = await client.get(
            f"{BASE}/{session.id}", params={"source": "database"}, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == str(session.id)
        assert data["messages"] == []
        assert data["total_messages"] == 0

    async def test_from_database_with_messages(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        db_session.add(make_message(session=session, role="user", content="Hello!"))
        db_session.add(make_message(session=session, role="assistant", content="Welcome!"))
        await db_session.flush()

        resp = await client.get(
            f"{BASE}/{session.id}", params={"source": "database"}, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_messages"] == 2
        assert len(data["messages"]) == 2

    async def test_from_redis_empty(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        resp = await client.get(
            f"{BASE}/{session.id}", params={"source": "redis"}, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == str(session.id)
        assert data["messages"] == []
        assert data["total_messages"] == 0

    async def test_from_redis_with_messages(self, client, db_session, auth_headers, monkeypatch):
        from app.services.redis_service import session_service

        session = await _create_session_in_db(db_session)

        redis_msgs = [
            {
                "role": "user",
                "content": "Hello from Redis",
                "tokens_used": 5,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "role": "assistant",
                "content": "Redis response",
                "tokens_used": 10,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]
        monkeypatch.setattr(
            session_service, "get_conversation_history", AsyncMock(return_value=redis_msgs)
        )

        resp = await client.get(
            f"{BASE}/{session.id}", params={"source": "redis"}, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_messages"] == 2
        assert data["messages"][0]["content"] == "Hello from Redis"

    async def test_pagination_params(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        for i in range(5):
            db_session.add(make_message(session=session, content=f"Msg {i}"))
        await db_session.flush()

        resp = await client.get(
            f"{BASE}/{session.id}",
            params={"source": "database", "limit": 2, "offset": 0},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["messages"]) <= 2

    async def test_default_source_is_database(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        resp = await client.get(f"{BASE}/{session.id}", headers=auth_headers)
        assert resp.status_code == 200


# ===========================================================================
# GET /api/v1/conversations/{session_id}/recent
# ===========================================================================


class TestGetRecentMessages:
    async def test_empty(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        resp = await client.get(
            f"{BASE}/{session.id}/recent", params={"count": 5}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_with_data(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        for i in range(5):
            db_session.add(make_message(session=session, content=f"Msg {i}"))
        await db_session.flush()

        resp = await client.get(
            f"{BASE}/{session.id}/recent", params={"count": 3}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert len(resp.json()) <= 3

    async def test_default_count(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        resp = await client.get(f"{BASE}/{session.id}/recent", headers=auth_headers)
        assert resp.status_code == 200


# ===========================================================================
# DELETE /api/v1/conversations/{session_id}
# ===========================================================================


class TestDeleteConversationHistory:
    async def test_with_messages(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        db_session.add(make_message(session=session))
        await db_session.flush()

        resp = await client.delete(f"{BASE}/{session.id}", headers=auth_headers)
        assert resp.status_code == 204

    async def test_empty_session(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        resp = await client.delete(f"{BASE}/{session.id}", headers=auth_headers)
        assert resp.status_code == 204

    async def test_without_redis(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        resp = await client.delete(
            f"{BASE}/{session.id}", params={"include_redis": False}, headers=auth_headers
        )
        assert resp.status_code == 204

    async def test_with_redis(self, client, db_session, auth_headers):
        session = await _create_session_in_db(db_session)
        resp = await client.delete(
            f"{BASE}/{session.id}", params={"include_redis": True}, headers=auth_headers
        )
        assert resp.status_code == 204
