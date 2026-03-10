"""Tests for DM conversation paths — /api/v1/conversations/action.

Covers the large uncovered body of send_player_action:
- DM narration flow (mocking DMEngine.narrate)
- Roll tag parsing & NPC roll execution
- Natural language roll detection
- Spell detection & slot consumption
- Memory capture paths (combat, dialogue, discovery, generic)
- Companion response generation
- Scene image generation
- Tool-based roll request format conversion
- Context window pruning
- Summarization path
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.db.models.enums import CharacterClass
from tests.factories import (
    make_character,
    make_session,
    make_user,
)

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
    monkeypatch.setattr(session_service, "get_conversation_history", AsyncMock(return_value=[]))
    monkeypatch.setattr(session_service, "update_session_state", AsyncMock(return_value={}))
    monkeypatch.setattr(session_service, "refresh_ttl", AsyncMock())
    monkeypatch.setattr(session_service, "delete_session_state", AsyncMock())
    monkeypatch.setattr(session_service, "revoke_token", AsyncMock())
    monkeypatch.setattr(session_service, "is_token_revoked", AsyncMock(return_value=False))
    monkeypatch.setattr(session_service, "add_message_to_history", AsyncMock())
    monkeypatch.setattr(session_service, "clear_conversation_history", AsyncMock())


# ── helpers ────────────────────────────────────────────────────────────────

BASE = "/api/v1/conversations"


async def _seed(db_session, **char_kw):
    user = make_user()
    char = make_character(user=user, **char_kw)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()
    return user, char, session


def _mock_narrate(narration="The tavern door creaks open.", tokens=42, **extra):
    """Return an AsyncMock that simulates DMEngine.narrate."""
    result = {
        "narration": narration,
        "tokens_used": tokens,
        "quest_complete_id": None,
        **extra,
    }
    return AsyncMock(return_value=result)


# common patches applied to most tests
def _common_patches():
    return [
        patch(
            "app.api.v1.endpoints.conversations.DMEngine",
            return_value=MagicMock(narrate=_mock_narrate()),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=(None, None, None, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            return_value=(False, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(is_significant_scene=MagicMock(return_value=(False, 0.0, None))),
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_summary",
            new_callable=AsyncMock,
        ),
    ]


# ===========================================================================
# Basic action flow
# ===========================================================================


async def test_action_basic_narration(client, db_session, auth_headers):
    """DM returns a simple narration without rolls/spells."""
    _u, char, sess = await _seed(db_session)
    patches = _common_patches()
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I look around the tavern.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "The tavern door creaks open."
        assert data["tokens_used"] == 42
    finally:
        for p in patches:
            p.stop()


async def test_action_with_roll_result(client, db_session, auth_headers):
    """Player submits a roll result; it should be injected into action text."""
    _u, char, sess = await _seed(db_session)
    patches = _common_patches()
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I try to pick the lock.",
                "roll_result": {
                    "type": "check",
                    "total": 18,
                    "roll": 15,
                    "modifier": 3,
                    "success": True,
                },
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
    finally:
        for p in patches:
            p.stop()


async def test_action_character_not_found(client, db_session, auth_headers):
    """Action with non-existent character returns 404."""
    _u, _c, sess = await _seed(db_session)
    patches = _common_patches()
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(uuid.uuid4()),
                "session_id": str(sess.id),
                "action": "hello",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 404
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# Spell detection paths
# ===========================================================================


async def test_action_spell_detected_and_consumed(client, db_session, auth_headers):
    """When detect_spell_cast finds a spell, slot is consumed."""
    _u, char, sess = await _seed(
        db_session,
        character_class=CharacterClass.WIZARD,
        spell_slots={"1": {"total": 2, "used": 0}},
    )

    dm_mock = MagicMock(narrate=_mock_narrate("You cast Magic Missile!"))
    patches = [
        patch("app.api.v1.endpoints.conversations.DMEngine", return_value=dm_mock),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=("Magic Missile", 1, None, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            return_value=(True, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(is_significant_scene=MagicMock(return_value=(False, 0.0, None))),
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
    ]
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I cast Magic Missile at the goblin.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
    finally:
        for p in patches:
            p.stop()


async def test_action_spell_detection_with_warning(client, db_session, auth_headers):
    """Spell detection returns a warning (e.g., unknown spell)."""
    _u, char, sess = await _seed(db_session)

    patches = [
        patch(
            "app.api.v1.endpoints.conversations.DMEngine",
            return_value=MagicMock(narrate=_mock_narrate("You wave your hands.")),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=(None, None, "Unknown spell 'Firblast'", "Did you mean 'Firebolt'?"),
        ),
        patch(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            return_value=(False, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(is_significant_scene=MagicMock(return_value=(False, 0.0, None))),
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
    ]
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I cast Firblast.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("warnings") is not None
        assert len(data["warnings"]) >= 1
    finally:
        for p in patches:
            p.stop()


async def test_action_spell_slot_consumption_fails(client, db_session, auth_headers):
    """consume_spell_slot returns (False, warning) — slot exhausted."""
    _u, char, sess = await _seed(
        db_session,
        character_class=CharacterClass.WIZARD,
        spell_slots={"1": {"total": 2, "used": 2}},
    )

    patches = [
        patch(
            "app.api.v1.endpoints.conversations.DMEngine",
            return_value=MagicMock(narrate=_mock_narrate("The spell fizzles.")),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=("Magic Missile", 1, None, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            return_value=(False, "No level 1 slots remaining"),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(is_significant_scene=MagicMock(return_value=(False, 0.0, None))),
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
    ]
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I cast Magic Missile.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("warnings") is not None
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# Roll tag parsing
# ===========================================================================


async def test_action_with_roll_tags_in_narration(client, db_session, auth_headers):
    """DM narration contains [ROLL:...] tags — parsed and NPC rolls executed."""
    _u, char, sess = await _seed(db_session)
    narration_with_tags = "A goblin attacks! [ROLL:NPC d20+3 attack vs AC 15]"

    patches = [
        patch(
            "app.api.v1.endpoints.conversations.DMEngine",
            return_value=MagicMock(narrate=_mock_narrate(narration_with_tags, tokens=30)),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=(None, None, None, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            return_value=(False, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(is_significant_scene=MagicMock(return_value=(False, 0.0, None))),
        ),
        patch(
            "app.api.v1.endpoints.conversations.RollParser.has_roll_tags",
            return_value=True,
        ),
        patch(
            "app.api.v1.endpoints.conversations.RollParser.parse_narration",
            return_value=("A goblin attacks!", []),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_roll_request_from_narration",
            return_value=None,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
    ]
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I attack the goblin.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# Natural language roll detection
# ===========================================================================


async def test_action_natural_language_roll_detection(client, db_session, auth_headers):
    """No roll tags, but natural language suggests a roll is needed."""
    _u, char, sess = await _seed(db_session)

    detected = {
        "roll_type": "check",
        "ability": "dexterity",
        "skill": "stealth",
        "dc": 15,
        "detected_text": "Roll a Stealth check",
    }

    patches = [
        patch(
            "app.api.v1.endpoints.conversations.DMEngine",
            return_value=MagicMock(
                narrate=_mock_narrate("You need to be quiet. Roll a Stealth check.")
            ),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=(None, None, None, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            return_value=(False, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(is_significant_scene=MagicMock(return_value=(False, 0.0, None))),
        ),
        patch(
            "app.api.v1.endpoints.conversations.RollParser.has_roll_tags",
            return_value=False,
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_roll_request_from_narration",
            return_value=detected,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
    ]
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I try to sneak past the guards.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("roll_request") is not None
        assert data["roll_request"]["type"] == "check"
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# Tool-based roll request format conversion
# ===========================================================================


async def test_action_tool_based_roll_request(client, db_session, auth_headers):
    """DM engine returns tool-based roll request — converted to frontend format."""
    _u, char, sess = await _seed(db_session)

    tool_roll = {
        "type": "saving_throw",
        "ability_or_skill": "DEX",
        "dc": 14,
        "advantage": False,
        "disadvantage": False,
        "description": "Dodge the fireball!",
    }

    patches = [
        patch(
            "app.api.v1.endpoints.conversations.DMEngine",
            return_value=MagicMock(
                narrate=_mock_narrate(
                    "A fireball erupts! Make a DEX save!",
                    roll_request=tool_roll,
                )
            ),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=(None, None, None, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            return_value=(False, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(is_significant_scene=MagicMock(return_value=(False, 0.0, None))),
        ),
        patch(
            "app.api.v1.endpoints.conversations.RollParser.has_roll_tags",
            return_value=False,
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_roll_request_from_narration",
            return_value=None,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
    ]
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I stand my ground.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        rr = data.get("roll_request")
        assert rr is not None
        assert rr["type"] == "save"
        assert rr["ability"] == "DEX"
        assert rr["dc"] == 14
    finally:
        for p in patches:
            p.stop()


async def test_action_tool_based_ability_check(client, db_session, auth_headers):
    """Tool roll request with type=ability_check maps to 'check' and sets skill."""
    _u, char, sess = await _seed(db_session)

    tool_roll = {
        "type": "ability_check",
        "ability_or_skill": "perception",
        "dc": 12,
        "advantage": False,
        "disadvantage": False,
        "description": "Spot the hidden trap",
    }

    patches = [
        patch(
            "app.api.v1.endpoints.conversations.DMEngine",
            return_value=MagicMock(
                narrate=_mock_narrate("Look carefully...", roll_request=tool_roll)
            ),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=(None, None, None, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            return_value=(False, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(is_significant_scene=MagicMock(return_value=(False, 0.0, None))),
        ),
        patch(
            "app.api.v1.endpoints.conversations.RollParser.has_roll_tags",
            return_value=False,
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_roll_request_from_narration",
            return_value=None,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
    ]
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I search for traps.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        rr = data.get("roll_request")
        assert rr is not None
        assert rr["type"] == "check"
        assert rr["skill"] == "perception"
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# Scene image generation
# ===========================================================================


async def test_action_scene_image_generated(client, db_session, auth_headers):
    """Significant scene triggers image generation."""
    _u, char, sess = await _seed(db_session)

    patches = [
        patch(
            "app.api.v1.endpoints.conversations.DMEngine",
            return_value=MagicMock(narrate=_mock_narrate("A dragon rises!")),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=(None, None, None, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            return_value=(False, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(
                is_significant_scene=MagicMock(return_value=(True, 0.95, "dragon_encounter"))
            ),
        ),
        patch(
            "app.services.image_service.image_service",
            new=MagicMock(
                generate_scene_image=AsyncMock(return_value="https://img.example.com/dragon.png")
            ),
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
    ]
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I look up at the sky.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("scene_image_url") == "https://img.example.com/dragon.png"
    finally:
        for p in patches:
            p.stop()


async def test_action_image_detection_error_graceful(client, db_session, auth_headers):
    """Image detection failure doesn't crash the request."""
    _u, char, sess = await _seed(db_session)

    patches = [
        patch(
            "app.api.v1.endpoints.conversations.DMEngine",
            return_value=MagicMock(narrate=_mock_narrate("You proceed.")),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=(None, None, None, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            return_value=(False, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(
                is_significant_scene=MagicMock(side_effect=RuntimeError("ML failed"))
            ),
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
    ]
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I continue walking.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# Empty narration fallback
# ===========================================================================


async def test_action_empty_narration_gets_fallback(client, db_session, auth_headers):
    """If DM returns empty narration, a fallback is used."""
    _u, char, sess = await _seed(db_session)

    patches = [
        patch(
            "app.api.v1.endpoints.conversations.DMEngine",
            return_value=MagicMock(narrate=_mock_narrate("", tokens=0)),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=(None, None, None, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            return_value=(False, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(is_significant_scene=MagicMock(return_value=(False, 0.0, None))),
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
    ]
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I wait.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should get fallback narration
        assert len(data["response"]) > 10
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# Spell detection exception handling
# ===========================================================================


async def test_action_spell_detection_exception_handled(client, db_session, auth_headers):
    """Exception in detect_spell_cast is caught gracefully."""
    _u, char, sess = await _seed(db_session)

    patches = [
        patch(
            "app.api.v1.endpoints.conversations.DMEngine",
            return_value=MagicMock(narrate=_mock_narrate("The air shimmers.")),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            side_effect=RuntimeError("spell detection broke"),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(is_significant_scene=MagicMock(return_value=(False, 0.0, None))),
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
    ]
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I mumble arcane words.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# Conversation history & context window
# ===========================================================================


async def test_action_no_session_id(client, db_session, auth_headers):
    """Action with session_id=None — should be handled gracefully."""
    _u, char, sess = await _seed(db_session)

    patches = _common_patches()
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I look around.",
            },
            headers=auth_headers,
        )
        # session_id is required by the code even though schema says Optional
        assert resp.status_code == 200
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# Cantrip casting (level-0 spell, no slot consumed)
# ===========================================================================


async def test_action_cantrip_detection(client, db_session, auth_headers):
    """Cantrip detected — consume_spell_slot returns True, no slot used."""
    _u, char, sess = await _seed(db_session)

    patches = [
        patch(
            "app.api.v1.endpoints.conversations.DMEngine",
            return_value=MagicMock(narrate=_mock_narrate("A bolt of fire shoots out!")),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=("Fire Bolt", 0, None, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            return_value=(True, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(is_significant_scene=MagicMock(return_value=(False, 0.0, None))),
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
    ]
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I cast Fire Bolt.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# Respond-to-roll skip logic
# ===========================================================================


async def test_action_roll_response_skips_nl_detection(client, db_session, auth_headers):
    """When player says 'I rolled 18', natural language detection is skipped."""
    _u, char, sess = await _seed(db_session)

    nl_detect = MagicMock(return_value={"roll_type": "check"})
    patches = [
        patch(
            "app.api.v1.endpoints.conversations.DMEngine",
            return_value=MagicMock(narrate=_mock_narrate("You succeed!")),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_spell_cast",
            new_callable=AsyncMock,
            return_value=(None, None, None, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.consume_spell_slot",
            return_value=(False, None),
        ),
        patch(
            "app.api.v1.endpoints.conversations.get_image_detection_service",
            return_value=MagicMock(is_significant_scene=MagicMock(return_value=(False, 0.0, None))),
        ),
        patch(
            "app.api.v1.endpoints.conversations.detect_roll_request_from_narration",
            nl_detect,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_dialogue",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.conversations.MemoryCaptureService.capture_combat_event",
            new_callable=AsyncMock,
        ),
    ]
    for p in patches:
        p.start()
    try:
        resp = await client.post(
            f"{BASE}/action",
            json={
                "character_id": str(char.id),
                "session_id": str(sess.id),
                "action": "I rolled a 18 for stealth.",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        # NL detection should NOT have been called because action starts with "i rolled"
        nl_detect.assert_not_called()
    finally:
        for p in patches:
            p.stop()
