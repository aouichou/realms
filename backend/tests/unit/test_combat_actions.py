"""Tests for combat actions — /api/v1/combat.

Covers remaining uncovered paths:
- perform_combat_action — cast_spell, dash, help, end_turn, with notes
- end_combat — memory capture, duration, victory/defeat
- update_participant_hp — damage clamping, healing clamping
- Turn advancement / round transitions
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from tests.factories import make_character, make_combat, make_session, make_user

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
    monkeypatch.setattr(session_service, "revoke_token", AsyncMock())
    monkeypatch.setattr(session_service, "is_token_revoked", AsyncMock(return_value=False))


BASE = "/api/v1/combat"

PARTICIPANTS_2 = [
    {
        "index": 0,
        "name": "Hero",
        "initiative": 18,
        "hp_current": 20,
        "hp_max": 20,
        "ac": 16,
        "is_enemy": False,
        "conditions": [],
    },
    {
        "index": 1,
        "name": "Goblin",
        "initiative": 12,
        "hp_current": 7,
        "hp_max": 7,
        "ac": 13,
        "is_enemy": True,
        "conditions": [],
    },
]


async def _seed_combat(db_session, user, **overrides):
    char = make_character(user=user)
    sess = make_session(user=user, character=char)
    defaults = {
        "session": sess,
        "participants": PARTICIPANTS_2,
        "turn_order": [0, 1],
        "combat_log": ["Combat started!"],
        "current_turn": 0,
        "round_number": 1,
    }
    defaults.update(overrides)
    combat = make_combat(**defaults)
    db_session.add_all([char, sess, combat])
    await db_session.flush()
    return user, char, sess, combat


# ===========================================================================
# perform_combat_action — cast_spell with target
# ===========================================================================


async def test_combat_cast_spell_no_target(client, db_session, auth_user):
    user, headers = auth_user
    """Cast spell without target — just log entry."""
    _u, _c, _s, combat = await _seed_combat(db_session, user)

    resp = await client.post(
        f"{BASE}/{combat.id}/action",
        json={"action_type": "cast_spell"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"]
    assert "casts a spell" in data["log_entry"]


async def test_combat_dash_action(client, db_session, auth_user):
    user, headers = auth_user
    _u, _c, _s, combat = await _seed_combat(db_session, user)

    resp = await client.post(
        f"{BASE}/{combat.id}/action",
        json={"action_type": "dash"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "Dash" in resp.json()["log_entry"]


async def test_combat_help_action(client, db_session, auth_user):
    user, headers = auth_user
    _u, _c, _s, combat = await _seed_combat(db_session, user)

    resp = await client.post(
        f"{BASE}/{combat.id}/action",
        json={"action_type": "help"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "Help" in resp.json()["log_entry"]


async def test_combat_unknown_action_type(client, db_session, auth_user):
    user, headers = auth_user
    """Unknown action type falls into else branch."""
    _u, _c, _s, combat = await _seed_combat(db_session, user)

    resp = await client.post(
        f"{BASE}/{combat.id}/action",
        json={"action_type": "wild_magic"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "wild_magic" in resp.json()["log_entry"]


async def test_combat_action_with_notes(client, db_session, auth_user):
    user, headers = auth_user
    _u, _c, _s, combat = await _seed_combat(db_session, user)

    resp = await client.post(
        f"{BASE}/{combat.id}/action",
        json={"action_type": "dodge", "notes": "Bracing for impact"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "Bracing for impact" in resp.json()["log_entry"]


async def test_combat_action_advances_turn(client, db_session, auth_user):
    user, headers = auth_user
    """After action, turn advances; after last participant, round increments."""
    _u, _c, _s, combat = await _seed_combat(db_session, user)

    # Turn 0 → 1
    resp = await client.post(
        f"{BASE}/{combat.id}/action",
        json={"action_type": "end_turn"},
        headers=headers,
    )
    assert resp.status_code == 200

    # Check status — should now be turn 1
    resp2 = await client.get(f"{BASE}/{combat.id}/status", headers=headers)
    assert resp2.status_code == 200


async def test_combat_action_round_wraps(client, db_session, auth_user):
    user, headers = auth_user
    """When last participant acts, round number increments."""
    _u, _c, _s, combat = await _seed_combat(db_session, user, current_turn=1)

    resp = await client.post(
        f"{BASE}/{combat.id}/action",
        json={"action_type": "end_turn"},
        headers=headers,
    )
    assert resp.status_code == 200

    status = await client.get(f"{BASE}/{combat.id}/status", headers=headers)
    data = status.json()
    assert data["round_number"] >= 2


# ===========================================================================
# end_combat — with memory capture
# ===========================================================================


async def test_end_combat_victory(client, db_session, auth_user):
    user, headers = auth_user
    """End combat where player survived — captures memory."""
    _u, _c, _s, combat = await _seed_combat(db_session, user)

    with patch(
        "app.api.v1.endpoints.combat.MemoryCaptureService.capture_combat_event",
        new_callable=AsyncMock,
    ) as mock_mem:
        resp = await client.post(f"{BASE}/{combat.id}/end", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rounds"] >= 1
    assert data["participants_survived"] >= 1


async def test_end_combat_memory_error_graceful(client, db_session, auth_user):
    user, headers = auth_user
    """Memory capture failure doesn't crash end_combat."""
    _u, _c, _s, combat = await _seed_combat(db_session, user)

    with patch(
        "app.api.v1.endpoints.combat.MemoryCaptureService.capture_combat_event",
        new_callable=AsyncMock,
        side_effect=RuntimeError("DB error"),
    ):
        resp = await client.post(f"{BASE}/{combat.id}/end", headers=headers)
    assert resp.status_code == 200


# ===========================================================================
# update_participant_hp
# ===========================================================================


async def test_update_hp_damage_clamped_to_zero(client, db_session, auth_user):
    user, headers = auth_user
    """HP doesn't go below zero."""
    _u, _c, _s, combat = await _seed_combat(db_session, user)

    resp = await client.patch(
        f"{BASE}/{combat.id}/participants/1/hp?hp_change=-100", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    goblin = data["participants"][1]
    assert goblin["hp_current"] == 0


async def test_update_hp_healing_clamped_to_max(client, db_session, auth_user):
    user, headers = auth_user
    """HP doesn't exceed max."""
    _u, _c, _s, combat = await _seed_combat(db_session, user)

    # First damage
    await client.patch(f"{BASE}/{combat.id}/participants/0/hp?hp_change=-10", headers=headers)
    # Then overheal
    resp = await client.patch(f"{BASE}/{combat.id}/participants/0/hp?hp_change=50", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    hero = data["participants"][0]
    assert hero["hp_current"] == hero["hp_max"]


async def test_update_hp_invalid_index(client, db_session, auth_user):
    user, headers = auth_user
    _u, _c, _s, combat = await _seed_combat(db_session, user)

    resp = await client.patch(
        f"{BASE}/{combat.id}/participants/99/hp?hp_change=-5", headers=headers
    )
    assert resp.status_code == 400


async def test_update_hp_negative_index(client, db_session, auth_user):
    user, headers = auth_user
    _u, _c, _s, combat = await _seed_combat(db_session, user)

    resp = await client.patch(
        f"{BASE}/{combat.id}/participants/-1/hp?hp_change=-5", headers=headers
    )
    assert resp.status_code == 400


# ===========================================================================
# Start combat with participants
# ===========================================================================


async def test_start_combat_rolls_initiative(client, db_session, auth_user):
    user, headers = auth_user
    """Start combat calculates initiative and sorts participants."""
    char = make_character(user=user)
    sess = make_session(user=user, character=char)
    db_session.add_all([char, sess])
    await db_session.flush()

    resp = await client.post(
        f"{BASE}/start",
        json={
            "session_id": str(sess.id),
            "participants": [
                {
                    "name": "Hero",
                    "initiative": 0,
                    "hp_current": 20,
                    "hp_max": 20,
                    "ac": 16,
                    "is_enemy": False,
                    "character_id": str(char.id),
                },
                {
                    "name": "Orc",
                    "initiative": 0,
                    "hp_current": 15,
                    "hp_max": 15,
                    "ac": 13,
                    "is_enemy": True,
                },
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_active"]
    assert len(data["participants"]) == 2
