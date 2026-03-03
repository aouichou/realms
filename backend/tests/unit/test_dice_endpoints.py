"""Tests for dice API endpoints (/api/v1/dice)."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from tests.factories import make_character, make_user

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
    original = db_session.commit
    db_session.commit = db_session.flush
    yield
    db_session.commit = original


# ===========================================================================
# POST /api/v1/dice/roll  (no auth)
# ===========================================================================


async def test_roll_d20(client, db_session):
    resp = await client.post("/api/v1/dice/roll", json={"dice": "d20"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["notation"] == "d20"
    assert data["roll_type"] == "normal"
    assert 1 <= data["total"] <= 20
    assert len(data["individual_rolls"]) >= 1
    assert data["individual_rolls"][0]["die_type"] == "d20"
    assert "breakdown" in data


async def test_roll_2d6_plus_3(client, db_session):
    resp = await client.post("/api/v1/dice/roll", json={"dice": "2d6+3"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["notation"] == "2d6+3"
    assert data["modifier"] == 3
    # 2d6 has range 2-12, plus modifier 3 -> 5-15
    assert 5 <= data["total"] <= 15
    assert len(data["individual_rolls"]) == 2


async def test_roll_3d8_minus_2(client, db_session):
    resp = await client.post("/api/v1/dice/roll", json={"dice": "3d8-2"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["notation"] == "3d8-2"
    assert data["modifier"] == -2


async def test_roll_4d6(client, db_session):
    resp = await client.post("/api/v1/dice/roll", json={"dice": "4d6"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["individual_rolls"]) == 4
    for roll in data["individual_rolls"]:
        assert 1 <= roll["roll"] <= 6


async def test_roll_advantage(client, db_session):
    resp = await client.post(
        "/api/v1/dice/roll",
        json={"dice": "d20", "roll_type": "advantage"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["roll_type"] == "advantage"
    # Advantage rolls 2d20
    assert len(data["individual_rolls"]) == 2
    # One of them should be marked as dropped
    dropped = [r for r in data["individual_rolls"] if r["dropped"]]
    kept = [r for r in data["individual_rolls"] if not r["dropped"]]
    assert len(dropped) == 1
    assert len(kept) == 1
    # The kept roll should be >= the dropped (advantage takes higher)
    assert kept[0]["roll"] >= dropped[0]["roll"]


async def test_roll_disadvantage(client, db_session):
    resp = await client.post(
        "/api/v1/dice/roll",
        json={"dice": "d20", "roll_type": "disadvantage"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["roll_type"] == "disadvantage"
    assert len(data["individual_rolls"]) == 2
    dropped = [r for r in data["individual_rolls"] if r["dropped"]]
    kept = [r for r in data["individual_rolls"] if not r["dropped"]]
    assert len(dropped) == 1
    assert len(kept) == 1
    # The kept roll should be <= the dropped (disadvantage takes lower)
    assert kept[0]["roll"] <= dropped[0]["roll"]


async def test_roll_with_reason(client, db_session):
    resp = await client.post(
        "/api/v1/dice/roll",
        json={"dice": "d20", "reason": "Initiative check"},
    )
    assert resp.status_code == 200
    assert resp.json()["reason"] == "Initiative check"


async def test_roll_invalid_notation(client, db_session):
    resp = await client.post("/api/v1/dice/roll", json={"dice": "banana"})
    assert resp.status_code == 400


# ===========================================================================
# POST /api/v1/dice/check  (no auth, needs character in DB)
# ===========================================================================


async def test_ability_check_strength(client, db_session):
    user = make_user()
    char = make_character(user=user, strength=16)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        "/api/v1/dice/check",
        json={"character_id": str(char.id), "ability": "strength"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["character_id"] == str(char.id)
    assert data["ability"] == "strength"
    assert data["ability_score"] == 16
    assert data["ability_modifier"] == 3  # (16-10)//2
    assert data["dc"] is None
    assert data["success"] is None


async def test_ability_check_with_dc(client, db_session):
    user = make_user()
    char = make_character(user=user, strength=10)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        "/api/v1/dice/check",
        json={"character_id": str(char.id), "ability": "strength", "dc": 10},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["dc"] == 10
    assert data["success"] is not None  # True or False based on roll


async def test_ability_check_with_advantage(client, db_session):
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        "/api/v1/dice/check",
        json={
            "character_id": str(char.id),
            "ability": "dexterity",
            "advantage": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["advantage"] is True
    assert len(data["rolls"]) == 2


async def test_ability_check_advantage_and_disadvantage_400(client, db_session):
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        "/api/v1/dice/check",
        json={
            "character_id": str(char.id),
            "ability": "wisdom",
            "advantage": True,
            "disadvantage": True,
        },
    )
    assert resp.status_code == 400


async def test_ability_check_character_not_found(client, db_session):
    resp = await client.post(
        "/api/v1/dice/check",
        json={"character_id": str(uuid.uuid4()), "ability": "strength"},
    )
    assert resp.status_code == 404


async def test_ability_check_skill_mismatch(client, db_session):
    """Athletics uses strength; sending it with charisma should 400."""
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        "/api/v1/dice/check",
        json={
            "character_id": str(char.id),
            "ability": "charisma",
            "skill": "athletics",
        },
    )
    assert resp.status_code == 400


async def test_ability_check_with_matching_skill(client, db_session):
    """Athletics matches strength -- should succeed."""
    user = make_user()
    char = make_character(user=user, strength=14)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        "/api/v1/dice/check",
        json={
            "character_id": str(char.id),
            "ability": "strength",
            "skill": "athletics",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["skill"] == "athletics"
    assert data["ability"] == "strength"
