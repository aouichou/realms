"""Tests for combat API endpoints (/api/v1/combat)."""

from __future__ import annotations

import uuid
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
