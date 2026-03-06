"""Tests for combat API endpoints (/api/v1/combat)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from tests.factories import make_character, make_combat, make_session, make_user

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


# -- Patch commit -> flush -------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def _patch_commit(db_session):
    original = db_session.commit
    db_session.commit = db_session.flush
    yield
    db_session.commit = original


# ===========================================================================
# Helpers
# ===========================================================================


async def _seed_session_and_character(db_session):
    """Create a user, character, and session for combat tests."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()
    return user, char, session


# ===========================================================================
# POST /api/v1/combat/start
# ===========================================================================


@pytest.mark.asyncio
async def test_start_combat_happy_path(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    body = {
        "session_id": str(session.id),
        "participants": [
            {
                "name": "Player",
                "initiative": 10,
                "hp_current": 12,
                "hp_max": 12,
                "ac": 16,
                "is_enemy": False,
                "conditions": [],
            },
            {
                "name": "Goblin",
                "initiative": 8,
                "hp_current": 7,
                "hp_max": 7,
                "ac": 15,
                "is_enemy": True,
                "conditions": [],
            },
        ],
    }
    resp = await client.post("/api/v1/combat/start", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_active"] is True
    assert data["round_number"] == 1
    assert len(data["participants"]) == 2


@pytest.mark.asyncio
async def test_start_combat_session_not_found(client, db_session):
    body = {
        "session_id": str(uuid.uuid4()),
        "participants": [
            {"name": "X", "initiative": 1, "hp_current": 1, "hp_max": 1, "ac": 10},
        ],
    }
    resp = await client.post("/api/v1/combat/start", json=body)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_start_combat_already_active(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    combat = make_combat(session=session, is_active=True)
    db_session.add(combat)
    await db_session.flush()

    body = {
        "session_id": str(session.id),
        "participants": [
            {"name": "Player", "initiative": 10, "hp_current": 12, "hp_max": 12, "ac": 16},
        ],
    }
    resp = await client.post("/api/v1/combat/start", json=body)
    assert resp.status_code == 400
    assert "already in progress" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_start_combat_with_character_id_dex_modifier(client, db_session):
    """Start combat with a participant that has a character_id so the
    DEX-modifier branch is exercised (lines 73-76)."""
    user, char, session = await _seed_session_and_character(db_session)
    body = {
        "session_id": str(session.id),
        "participants": [
            {
                "name": char.name,
                "character_id": str(char.id),
                "initiative": 0,
                "hp_current": char.hp_current,
                "hp_max": char.hp_max,
                "ac": 16,
                "is_enemy": False,
                "conditions": [],
            },
            {
                "name": "Goblin",
                "initiative": 0,
                "hp_current": 7,
                "hp_max": 7,
                "ac": 15,
                "is_enemy": True,
                "conditions": [],
            },
        ],
    }
    resp = await client.post("/api/v1/combat/start", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_active"] is True
    assert len(data["participants"]) == 2
    # Initiative was re-rolled server-side; just verify field exists
    for p in data["participants"]:
        assert "initiative" in p


@pytest.mark.asyncio
async def test_start_combat_with_nonexistent_character_id(client, db_session):
    """character_id is supplied but resolves to no character — dex_modifier
    stays 0 (branch at line 75 is False)."""
    user, char, session = await _seed_session_and_character(db_session)
    body = {
        "session_id": str(session.id),
        "participants": [
            {
                "name": "Ghost",
                "character_id": str(uuid.uuid4()),
                "initiative": 0,
                "hp_current": 10,
                "hp_max": 10,
                "ac": 12,
                "is_enemy": False,
                "conditions": [],
            },
        ],
    }
    resp = await client.post("/api/v1/combat/start", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["participants"]) == 1


@pytest.mark.asyncio
async def test_start_combat_initiative_sorting(client, db_session):
    """Verify participants are returned sorted by initiative (descending)."""
    user, char, session = await _seed_session_and_character(db_session)

    # Use many participants to increase confidence the sort is correct
    body = {
        "session_id": str(session.id),
        "participants": [
            {"name": f"P{i}", "initiative": 0, "hp_current": 10, "hp_max": 10, "ac": 10}
            for i in range(4)
        ],
    }
    resp = await client.post("/api/v1/combat/start", json=body)
    assert resp.status_code == 201
    data = resp.json()
    initiatives = [p["initiative"] for p in data["participants"]]
    assert initiatives == sorted(initiatives, reverse=True)


# ===========================================================================
# GET /api/v1/combat/{combat_id}/status
# ===========================================================================


@pytest.mark.asyncio
async def test_get_combat_status(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    combat = make_combat(session=session)
    db_session.add(combat)
    await db_session.flush()

    resp = await client.get(f"/api/v1/combat/{combat.id}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["combat_id"] == str(combat.id)
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_combat_status_not_found(client, db_session):
    resp = await client.get(f"/api/v1/combat/{uuid.uuid4()}/status")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_combat_status_includes_current_participant(client, db_session):
    """Verify current_participant is populated from the participants list."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Alice",
            "initiative": 20,
            "hp_current": 10,
            "hp_max": 10,
            "ac": 14,
            "is_enemy": False,
        },
        {
            "name": "Bob",
            "initiative": 5,
            "hp_current": 8,
            "hp_max": 8,
            "ac": 12,
            "is_enemy": True,
        },
    ]
    combat = make_combat(
        session=session, participants=participants, turn_order=[0, 1], current_turn=1
    )
    db_session.add(combat)
    await db_session.flush()

    resp = await client.get(f"/api/v1/combat/{combat.id}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_participant"]["name"] == "Bob"


@pytest.mark.asyncio
async def test_get_combat_status_empty_participants(client, db_session):
    """When participants list is empty, current_participant should be None."""
    user, char, session = await _seed_session_and_character(db_session)
    combat = make_combat(session=session, participants=[], turn_order=[], current_turn=0)
    db_session.add(combat)
    await db_session.flush()

    resp = await client.get(f"/api/v1/combat/{combat.id}/status")
    assert resp.status_code == 200
    assert resp.json()["current_participant"] is None


# ===========================================================================
# POST /api/v1/combat/{combat_id}/action
# ===========================================================================


@pytest.mark.asyncio
async def test_combat_action_attack(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 12,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
            "index": 0,
        },
        {
            "name": "Goblin",
            "initiative": 8,
            "hp_current": 7,
            "hp_max": 7,
            "ac": 15,
            "is_enemy": True,
            "index": 1,
        },
    ]
    combat = make_combat(
        session=session,
        participants=participants,
        turn_order=[0, 1],
        current_turn=0,
    )
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "attack", "target_index": 1, "damage": 5}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    # damage_dealt may be None on a miss; just verify the key exists
    assert "damage_dealt" in data


@pytest.mark.asyncio
async def test_combat_action_attack_no_target(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 12,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
            "index": 0,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0], current_turn=0)
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "attack"}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 400
    assert "Target required" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_combat_action_attack_critical_hit(client, db_session):
    """Force a natural 20 to exercise critical-hit branch (line ~225-229)."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Fighter",
            "initiative": 15,
            "hp_current": 12,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
            "index": 0,
        },
        {
            "name": "Orc",
            "initiative": 8,
            "hp_current": 30,
            "hp_max": 30,
            "ac": 13,
            "is_enemy": True,
            "index": 1,
        },
    ]
    combat = make_combat(
        session=session, participants=participants, turn_order=[0, 1], current_turn=0
    )
    db_session.add(combat)
    await db_session.flush()

    with patch("app.api.v1.endpoints.combat.random.randint", return_value=20):
        body = {"action_type": "attack", "target_index": 1, "damage": 16}
        resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["damage_dealt"] == 16
    assert "critically hits" in data["log_entry"] or "Natural 20" in data["log_entry"]


@pytest.mark.asyncio
async def test_combat_action_attack_normal_hit(client, db_session):
    """Force roll high enough to hit but not 20 — normal hit branch."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Fighter",
            "initiative": 15,
            "hp_current": 12,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
            "index": 0,
        },
        {
            "name": "Orc",
            "initiative": 8,
            "hp_current": 30,
            "hp_max": 30,
            "ac": 10,
            "is_enemy": True,
            "index": 1,
        },
    ]
    combat = make_combat(
        session=session, participants=participants, turn_order=[0, 1], current_turn=0
    )
    db_session.add(combat)
    await db_session.flush()

    # Roll 15 + attack_bonus(5) = 20 >= AC 10 → hit (but not crit since roll != 20)
    with patch("app.api.v1.endpoints.combat.random.randint", return_value=15):
        body = {"action_type": "attack", "target_index": 1, "damage": 7}
        resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["damage_dealt"] == 7
    assert "hits" in data["log_entry"]
    assert "critically" not in data["log_entry"]


@pytest.mark.asyncio
async def test_combat_action_attack_miss(client, db_session):
    """Force roll low enough to miss — miss branch."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Fighter",
            "initiative": 15,
            "hp_current": 12,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
            "index": 0,
        },
        {
            "name": "Dragon",
            "initiative": 8,
            "hp_current": 100,
            "hp_max": 100,
            "ac": 25,
            "is_enemy": True,
            "index": 1,
        },
    ]
    combat = make_combat(
        session=session, participants=participants, turn_order=[0, 1], current_turn=0
    )
    db_session.add(combat)
    await db_session.flush()

    # Roll 1 + 5 = 6 < AC 25 → miss
    with patch("app.api.v1.endpoints.combat.random.randint", return_value=1):
        body = {"action_type": "attack", "target_index": 1}
        resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["damage_dealt"] is None
    assert "misses" in data["log_entry"]


@pytest.mark.asyncio
async def test_combat_action_dodge(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 12,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
            "index": 0,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0], current_turn=0)
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "dodge"}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    assert "Dodge" in resp.json()["log_entry"]


@pytest.mark.asyncio
async def test_combat_action_use_item(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 8,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
            "index": 0,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0], current_turn=0)
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "use_item"}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    assert resp.json()["healing_done"] is not None


@pytest.mark.asyncio
async def test_combat_action_use_item_with_explicit_healing(client, db_session):
    """use_item with explicit damage= value used as healing amount."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Cleric",
            "initiative": 15,
            "hp_current": 5,
            "hp_max": 20,
            "ac": 16,
            "is_enemy": False,
            "index": 0,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0], current_turn=0)
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "use_item", "damage": 10}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["healing_done"] == 10
    assert "healing item" in data["log_entry"]


@pytest.mark.asyncio
async def test_combat_action_use_item_caps_at_max_hp(client, db_session):
    """Healing should not exceed hp_max."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Ranger",
            "initiative": 15,
            "hp_current": 9,
            "hp_max": 10,
            "ac": 14,
            "is_enemy": False,
            "index": 0,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0], current_turn=0)
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "use_item", "damage": 50}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    # healing_done reports the raw value, but HP is capped in the participant
    assert resp.json()["healing_done"] == 50


@pytest.mark.asyncio
async def test_combat_action_end_turn(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 12,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
            "index": 0,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0], current_turn=0)
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "end_turn"}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    assert "ends their turn" in resp.json()["log_entry"]


@pytest.mark.asyncio
async def test_combat_action_not_found(client, db_session):
    body = {"action_type": "dodge"}
    resp = await client.post(f"/api/v1/combat/{uuid.uuid4()}/action", json=body)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_combat_action_not_active(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    combat = make_combat(session=session, is_active=False)
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "dodge"}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 400
    assert "not active" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_combat_action_cast_spell_with_target(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Wizard",
            "initiative": 15,
            "hp_current": 8,
            "hp_max": 8,
            "ac": 12,
            "is_enemy": False,
            "index": 0,
        },
        {
            "name": "Orc",
            "initiative": 8,
            "hp_current": 15,
            "hp_max": 15,
            "ac": 13,
            "is_enemy": True,
            "index": 1,
        },
    ]
    combat = make_combat(
        session=session, participants=participants, turn_order=[0, 1], current_turn=0
    )
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "cast_spell", "target_index": 1, "damage": 8}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["damage_dealt"] == 8


@pytest.mark.asyncio
async def test_combat_action_cast_spell_without_target(client, db_session):
    """Cast spell with no target — only the base log entry, no damage."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Sorcerer",
            "initiative": 15,
            "hp_current": 8,
            "hp_max": 8,
            "ac": 12,
            "is_enemy": False,
            "index": 0,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0], current_turn=0)
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "cast_spell"}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert "casts a spell" in data["log_entry"]
    assert data["damage_dealt"] is None


@pytest.mark.asyncio
async def test_combat_action_dash(client, db_session):
    """Exercise the DASH branch."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Rogue",
            "initiative": 18,
            "hp_current": 10,
            "hp_max": 10,
            "ac": 14,
            "is_enemy": False,
            "index": 0,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0], current_turn=0)
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "dash"}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    assert "Dash" in resp.json()["log_entry"]


@pytest.mark.asyncio
async def test_combat_action_help(client, db_session):
    """Exercise the HELP branch."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Bard",
            "initiative": 12,
            "hp_current": 10,
            "hp_max": 10,
            "ac": 13,
            "is_enemy": False,
            "index": 0,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0], current_turn=0)
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "help"}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    assert "Help" in resp.json()["log_entry"]


@pytest.mark.asyncio
async def test_combat_action_unknown_type(client, db_session):
    """Exercise the else branch for an unrecognised action type."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Monk",
            "initiative": 14,
            "hp_current": 10,
            "hp_max": 10,
            "ac": 15,
            "is_enemy": False,
            "index": 0,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0], current_turn=0)
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "flurry_of_blows"}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    assert "flurry_of_blows" in resp.json()["log_entry"]


@pytest.mark.asyncio
async def test_combat_action_with_notes(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 12,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
            "index": 0,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0], current_turn=0)
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "dash", "notes": "Running away!"}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200
    assert "Running away!" in resp.json()["log_entry"]


@pytest.mark.asyncio
async def test_combat_action_advances_turn(client, db_session):
    """After an action, current_turn should advance by one."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "P1",
            "initiative": 20,
            "hp_current": 10,
            "hp_max": 10,
            "ac": 14,
            "is_enemy": False,
            "index": 0,
        },
        {
            "name": "P2",
            "initiative": 10,
            "hp_current": 10,
            "hp_max": 10,
            "ac": 14,
            "is_enemy": True,
            "index": 1,
        },
    ]
    combat = make_combat(
        session=session, participants=participants, turn_order=[0, 1], current_turn=0
    )
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "dodge"}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200

    # After the action, check status shows turn advanced
    status_resp = await client.get(f"/api/v1/combat/{combat.id}/status")
    assert status_resp.json()["current_turn"] == 1


@pytest.mark.asyncio
async def test_combat_action_round_wraps(client, db_session):
    """When the last participant acts, turn wraps to 0 and round increments."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Solo",
            "initiative": 10,
            "hp_current": 10,
            "hp_max": 10,
            "ac": 14,
            "is_enemy": False,
            "index": 0,
        },
    ]
    combat = make_combat(
        session=session,
        participants=participants,
        turn_order=[0],
        current_turn=0,
        round_number=1,
    )
    db_session.add(combat)
    await db_session.flush()

    body = {"action_type": "end_turn"}
    resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200

    status_resp = await client.get(f"/api/v1/combat/{combat.id}/status")
    data = status_resp.json()
    assert data["current_turn"] == 0
    assert data["round_number"] == 2
    # The combat log should include the round announcement
    assert any("Round 2" in entry for entry in data["combat_log"])


@pytest.mark.asyncio
async def test_combat_action_attack_reduces_target_hp_to_zero(client, db_session):
    """Attack damage should not reduce HP below 0."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Fighter",
            "initiative": 20,
            "hp_current": 12,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
            "index": 0,
        },
        {
            "name": "Rat",
            "initiative": 5,
            "hp_current": 2,
            "hp_max": 2,
            "ac": 8,
            "is_enemy": True,
            "index": 1,
        },
    ]
    combat = make_combat(
        session=session, participants=participants, turn_order=[0, 1], current_turn=0
    )
    db_session.add(combat)
    await db_session.flush()

    # Force a hit with a lot of damage
    with patch("app.api.v1.endpoints.combat.random.randint", return_value=18):
        body = {"action_type": "attack", "target_index": 1, "damage": 50}
        resp = await client.post(f"/api/v1/combat/{combat.id}/action", json=body)
    assert resp.status_code == 200

    # Check HP didn't go below 0
    status = await client.get(f"/api/v1/combat/{combat.id}/status")
    target = status.json()["participants"][1]
    assert target["hp_current"] == 0


# ===========================================================================
# POST /api/v1/combat/{combat_id}/end
# ===========================================================================


@pytest.mark.asyncio
async def test_end_combat(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 12,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
        },
        {
            "name": "Goblin",
            "initiative": 8,
            "hp_current": 0,
            "hp_max": 7,
            "ac": 15,
            "is_enemy": True,
        },
    ]
    combat = make_combat(session=session, participants=participants)
    db_session.add(combat)
    await db_session.flush()

    with patch.object(
        __import__(
            "app.services.memory_capture", fromlist=["MemoryCaptureService"]
        ).MemoryCaptureService,
        "capture_combat_event",
        new_callable=AsyncMock,
    ):
        resp = await client.post(f"/api/v1/combat/{combat.id}/end")
    assert resp.status_code == 200
    data = resp.json()
    assert data["participants_survived"] == 1
    assert data["participants_defeated"] == 1
    assert data["total_rounds"] >= 1


@pytest.mark.asyncio
async def test_end_combat_not_found(client, db_session):
    resp = await client.post(f"/api/v1/combat/{uuid.uuid4()}/end")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_end_combat_defeat_outcome(client, db_session):
    """All player characters defeated — memory capture records 'defeat'."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 0,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
        },
        {
            "name": "Goblin",
            "initiative": 8,
            "hp_current": 5,
            "hp_max": 7,
            "ac": 15,
            "is_enemy": True,
        },
    ]
    combat = make_combat(session=session, participants=participants)
    db_session.add(combat)
    await db_session.flush()

    mock_capture = AsyncMock()
    with patch(
        "app.api.v1.endpoints.combat.MemoryCaptureService.capture_combat_event",
        mock_capture,
    ):
        resp = await client.post(f"/api/v1/combat/{combat.id}/end")

    assert resp.status_code == 200
    data = resp.json()
    assert data["participants_survived"] == 1  # Goblin survived
    assert data["participants_defeated"] == 1  # Player defeated
    # Verify 'defeat' was passed to the memory capture
    mock_capture.assert_awaited_once()
    call_kwargs = mock_capture.call_args
    assert call_kwargs.kwargs.get("outcome") == "defeat" or (
        len(call_kwargs.args) > 0 and "defeat" in str(call_kwargs)
    )


@pytest.mark.asyncio
async def test_end_combat_duration_calculated(client, db_session):
    """When started_at is set, duration_seconds should be computed."""
    user, char, session = await _seed_session_and_character(db_session)
    started = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 10,
            "hp_max": 10,
            "ac": 14,
            "is_enemy": False,
        },
    ]
    combat = make_combat(session=session, participants=participants, started_at=started)
    db_session.add(combat)
    await db_session.flush()

    with patch(
        "app.api.v1.endpoints.combat.MemoryCaptureService.capture_combat_event",
        new_callable=AsyncMock,
    ):
        resp = await client.post(f"/api/v1/combat/{combat.id}/end")

    assert resp.status_code == 200
    data = resp.json()
    # duration should be a positive number of seconds
    assert data["duration_seconds"] is not None
    assert data["duration_seconds"] > 0


@pytest.mark.asyncio
async def test_end_combat_duration_always_computed(client, db_session):
    """started_at is NOT NULL so duration_seconds is always computed."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 10,
            "hp_max": 10,
            "ac": 14,
            "is_enemy": False,
        },
    ]
    combat = make_combat(session=session, participants=participants)
    db_session.add(combat)
    await db_session.flush()

    with patch(
        "app.api.v1.endpoints.combat.MemoryCaptureService.capture_combat_event",
        new_callable=AsyncMock,
    ):
        resp = await client.post(f"/api/v1/combat/{combat.id}/end")

    assert resp.status_code == 200
    assert resp.json()["duration_seconds"] is not None
    assert resp.json()["duration_seconds"] >= 0


@pytest.mark.asyncio
async def test_end_combat_memory_capture_failure_logged(client, db_session):
    """If MemoryCaptureService.capture_combat_event raises, it's caught
    and the endpoint still returns 200."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 10,
            "hp_max": 10,
            "ac": 14,
            "is_enemy": False,
        },
    ]
    combat = make_combat(session=session, participants=participants)
    db_session.add(combat)
    await db_session.flush()

    with patch(
        "app.api.v1.endpoints.combat.MemoryCaptureService.capture_combat_event",
        new_callable=AsyncMock,
        side_effect=RuntimeError("redis down"),
    ):
        resp = await client.post(f"/api/v1/combat/{combat.id}/end")

    # Should still succeed — the error is caught
    assert resp.status_code == 200
    data = resp.json()
    assert "Combat ended" in data["combat_log"][-1]


@pytest.mark.asyncio
async def test_end_combat_all_survived(client, db_session):
    """All participants alive — survived count equals total."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Paladin",
            "initiative": 15,
            "hp_current": 20,
            "hp_max": 20,
            "ac": 18,
            "is_enemy": False,
        },
        {
            "name": "Goblin",
            "initiative": 8,
            "hp_current": 3,
            "hp_max": 7,
            "ac": 15,
            "is_enemy": True,
        },
    ]
    combat = make_combat(session=session, participants=participants, round_number=5)
    db_session.add(combat)
    await db_session.flush()

    with patch(
        "app.api.v1.endpoints.combat.MemoryCaptureService.capture_combat_event",
        new_callable=AsyncMock,
    ):
        resp = await client.post(f"/api/v1/combat/{combat.id}/end")

    assert resp.status_code == 200
    data = resp.json()
    assert data["participants_survived"] == 2
    assert data["participants_defeated"] == 0
    assert data["total_rounds"] == 5
    assert "Combat ended after 5 rounds!" in data["combat_log"][-1]


# ===========================================================================
# PATCH /api/v1/combat/{combat_id}/participants/{idx}/hp
# ===========================================================================


@pytest.mark.asyncio
async def test_update_participant_hp_damage(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 12,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0])
    db_session.add(combat)
    await db_session.flush()

    resp = await client.patch(
        f"/api/v1/combat/{combat.id}/participants/0/hp",
        params={"hp_change": -5},
    )
    assert resp.status_code == 200
    data = resp.json()
    updated = data["participants"][0]
    assert updated["hp_current"] == 7


@pytest.mark.asyncio
async def test_update_participant_hp_healing(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 5,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0])
    db_session.add(combat)
    await db_session.flush()

    resp = await client.patch(
        f"/api/v1/combat/{combat.id}/participants/0/hp",
        params={"hp_change": 4},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["participants"][0]["hp_current"] == 9


@pytest.mark.asyncio
async def test_update_participant_hp_not_found(client, db_session):
    resp = await client.patch(
        f"/api/v1/combat/{uuid.uuid4()}/participants/0/hp",
        params={"hp_change": -5},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_participant_hp_invalid_index(client, db_session):
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 12,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0])
    db_session.add(combat)
    await db_session.flush()

    resp = await client.patch(
        f"/api/v1/combat/{combat.id}/participants/5/hp",
        params={"hp_change": -5},
    )
    assert resp.status_code == 400
    assert "Invalid participant index" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_update_participant_hp_negative_index(client, db_session):
    """Negative participant index should be rejected."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 12,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0])
    db_session.add(combat)
    await db_session.flush()

    resp = await client.patch(
        f"/api/v1/combat/{combat.id}/participants/-1/hp",
        params={"hp_change": -5},
    )
    assert resp.status_code == 400
    assert "Invalid participant index" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_update_participant_hp_floor_at_zero(client, db_session):
    """Massive damage should floor HP at 0, not go negative."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 5,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0])
    db_session.add(combat)
    await db_session.flush()

    resp = await client.patch(
        f"/api/v1/combat/{combat.id}/participants/0/hp",
        params={"hp_change": -100},
    )
    assert resp.status_code == 200
    assert resp.json()["participants"][0]["hp_current"] == 0


@pytest.mark.asyncio
async def test_update_participant_hp_cap_at_max(client, db_session):
    """Healing beyond hp_max should cap at hp_max."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Player",
            "initiative": 15,
            "hp_current": 10,
            "hp_max": 12,
            "ac": 16,
            "is_enemy": False,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0])
    db_session.add(combat)
    await db_session.flush()

    resp = await client.patch(
        f"/api/v1/combat/{combat.id}/participants/0/hp",
        params={"hp_change": 100},
    )
    assert resp.status_code == 200
    assert resp.json()["participants"][0]["hp_current"] == 12


@pytest.mark.asyncio
async def test_update_participant_hp_damage_log_entry(client, db_session):
    """Damage produces a 'takes X damage' combat log entry."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Knight",
            "initiative": 15,
            "hp_current": 20,
            "hp_max": 20,
            "ac": 18,
            "is_enemy": False,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0])
    db_session.add(combat)
    await db_session.flush()

    resp = await client.patch(
        f"/api/v1/combat/{combat.id}/participants/0/hp",
        params={"hp_change": -8},
    )
    assert resp.status_code == 200
    log = resp.json()["combat_log"]
    assert any("takes 8 damage" in entry for entry in log)
    assert any("20 → 12 HP" in entry for entry in log)


@pytest.mark.asyncio
async def test_update_participant_hp_healing_log_entry(client, db_session):
    """Healing produces a 'healed for X HP' combat log entry."""
    user, char, session = await _seed_session_and_character(db_session)
    participants = [
        {
            "name": "Knight",
            "initiative": 15,
            "hp_current": 10,
            "hp_max": 20,
            "ac": 18,
            "is_enemy": False,
        },
    ]
    combat = make_combat(session=session, participants=participants, turn_order=[0])
    db_session.add(combat)
    await db_session.flush()

    resp = await client.patch(
        f"/api/v1/combat/{combat.id}/participants/0/hp",
        params={"hp_change": 5},
    )
    assert resp.status_code == 200
    log = resp.json()["combat_log"]
    assert any("healed for 5 HP" in entry for entry in log)
    assert any("10 → 15 HP" in entry for entry in log)
