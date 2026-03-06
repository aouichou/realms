"""Tests for dice API endpoints (/api/v1/dice)."""

from __future__ import annotations

import uuid
from unittest.mock import patch

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


# ---------------------------------------------------------------------------
# NEW TESTS — targeting missed lines 83-145
# ---------------------------------------------------------------------------


async def test_ability_check_with_disadvantage(client, db_session):
    """Disadvantage rolls 2d20 and takes the lower."""
    user = make_user()
    char = make_character(user=user, dexterity=14)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        "/api/v1/dice/check",
        json={
            "character_id": str(char.id),
            "ability": "dexterity",
            "disadvantage": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["disadvantage"] is True
    assert data["advantage"] is False
    assert len(data["rolls"]) == 2
    # The used roll should be the minimum of the two
    assert data["roll"] == min(data["rolls"])


async def test_ability_check_all_abilities(client, db_session):
    """Exercise every ability score lookup (lines 90-97)."""
    user = make_user()
    char = make_character(
        user=user,
        strength=18,
        dexterity=14,
        constitution=16,
        intelligence=12,
        wisdom=10,
        charisma=8,
    )
    db_session.add_all([user, char])
    await db_session.flush()

    expected = {
        "strength": (18, 4),
        "dexterity": (14, 2),
        "constitution": (16, 3),
        "intelligence": (12, 1),
        "wisdom": (10, 0),
        "charisma": (8, -1),
    }
    for ability, (score, modifier) in expected.items():
        resp = await client.post(
            "/api/v1/dice/check",
            json={"character_id": str(char.id), "ability": ability},
        )
        assert resp.status_code == 200, f"Failed for {ability}"
        data = resp.json()
        assert data["ability_score"] == score, f"Wrong score for {ability}"
        assert data["ability_modifier"] == modifier, f"Wrong modifier for {ability}"


async def test_ability_check_with_reason(client, db_session):
    """Verify the reason field is echoed back."""
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        "/api/v1/dice/check",
        json={
            "character_id": str(char.id),
            "ability": "wisdom",
            "reason": "Checking for traps",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["reason"] == "Checking for traps"


async def test_ability_check_dc_success_deterministic(client, db_session):
    """Patch random to guarantee success against DC."""
    user = make_user()
    char = make_character(user=user, strength=20)  # modifier = +5
    db_session.add_all([user, char])
    await db_session.flush()

    with patch("app.api.v1.endpoints.dice.random.randint", return_value=15):
        resp = await client.post(
            "/api/v1/dice/check",
            json={"character_id": str(char.id), "ability": "strength", "dc": 15},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["roll"] == 15
    assert data["total"] == 20  # 15 + 5
    assert data["dc"] == 15
    assert data["success"] is True


async def test_ability_check_dc_failure_deterministic(client, db_session):
    """Patch random to guarantee failure against DC."""
    user = make_user()
    char = make_character(user=user, strength=8)  # modifier = -1
    db_session.add_all([user, char])
    await db_session.flush()

    with patch("app.api.v1.endpoints.dice.random.randint", return_value=5):
        resp = await client.post(
            "/api/v1/dice/check",
            json={"character_id": str(char.id), "ability": "strength", "dc": 10},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["roll"] == 5
    assert data["total"] == 4  # 5 + (-1)
    assert data["dc"] == 10
    assert data["success"] is False


async def test_ability_check_advantage_deterministic(client, db_session):
    """Patch random to verify advantage takes the higher roll."""
    user = make_user()
    char = make_character(user=user, dexterity=10)  # modifier = 0
    db_session.add_all([user, char])
    await db_session.flush()

    with patch("app.api.v1.endpoints.dice.random.randint", side_effect=[7, 15]):
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
    assert data["rolls"] == [7, 15]
    assert data["roll"] == 15  # advantage takes max
    assert data["total"] == 15


async def test_ability_check_disadvantage_deterministic(client, db_session):
    """Patch random to verify disadvantage takes the lower roll."""
    user = make_user()
    char = make_character(user=user, wisdom=10)  # modifier = 0
    db_session.add_all([user, char])
    await db_session.flush()

    with patch("app.api.v1.endpoints.dice.random.randint", side_effect=[18, 4]):
        resp = await client.post(
            "/api/v1/dice/check",
            json={
                "character_id": str(char.id),
                "ability": "wisdom",
                "disadvantage": True,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rolls"] == [18, 4]
    assert data["roll"] == 4  # disadvantage takes min
    assert data["total"] == 4


async def test_ability_check_breakdown_format(client, db_session):
    """Verify breakdown string includes roll, modifier, and total."""
    user = make_user()
    char = make_character(user=user, charisma=16)  # modifier = +3
    db_session.add_all([user, char])
    await db_session.flush()

    with patch("app.api.v1.endpoints.dice.random.randint", return_value=12):
        resp = await client.post(
            "/api/v1/dice/check",
            json={"character_id": str(char.id), "ability": "charisma"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "1d20(12)" in data["breakdown"]
    assert "+3" in data["breakdown"]
    assert "CHA" in data["breakdown"]
    assert "= 15" in data["breakdown"]


async def test_ability_check_negative_modifier_breakdown(client, db_session):
    """Verify breakdown shows negative modifier correctly."""
    user = make_user()
    char = make_character(user=user, intelligence=6)  # modifier = -2
    db_session.add_all([user, char])
    await db_session.flush()

    with patch("app.api.v1.endpoints.dice.random.randint", return_value=10):
        resp = await client.post(
            "/api/v1/dice/check",
            json={"character_id": str(char.id), "ability": "intelligence"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ability_modifier"] == -2
    assert data["total"] == 8  # 10 + (-2)
    assert "-2" in data["breakdown"]
    assert "INT" in data["breakdown"]


async def test_ability_check_zero_modifier(client, db_session):
    """Ability score of 10/11 gives +0 modifier — breakdown should not show modifier."""
    user = make_user()
    char = make_character(user=user, constitution=10)  # modifier = 0
    db_session.add_all([user, char])
    await db_session.flush()

    with patch("app.api.v1.endpoints.dice.random.randint", return_value=14):
        resp = await client.post(
            "/api/v1/dice/check",
            json={"character_id": str(char.id), "ability": "constitution"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ability_modifier"] == 0
    assert data["total"] == 14
    # With zero modifier, breakdown should just have roll and total
    assert "1d20(14)" in data["breakdown"]
    assert "= 14" in data["breakdown"]


async def test_ability_check_proficiency_bonus_returned(client, db_session):
    """Verify proficiency_bonus field is calculated from level."""
    user = make_user()
    char = make_character(user=user, level=5, strength=10)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        "/api/v1/dice/check",
        json={"character_id": str(char.id), "ability": "strength"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["proficiency_bonus"] == 3  # level 5 → +3
    assert data["is_proficient"] is False  # always False for now


async def test_ability_check_character_name_returned(client, db_session):
    """Verify character_name is populated in the response."""
    user = make_user()
    char = make_character(user=user, name="Gandalf the Grey", wisdom=18)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        "/api/v1/dice/check",
        json={"character_id": str(char.id), "ability": "wisdom"},
    )
    assert resp.status_code == 200
    assert resp.json()["character_name"] == "Gandalf the Grey"


async def test_ability_check_skill_perception_wisdom(client, db_session):
    """Perception uses wisdom — should succeed with correct ability."""
    user = make_user()
    char = make_character(user=user, wisdom=16)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        "/api/v1/dice/check",
        json={
            "character_id": str(char.id),
            "ability": "wisdom",
            "skill": "perception",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["skill"] == "perception"
    assert data["ability"] == "wisdom"
    assert data["ability_modifier"] == 3


async def test_ability_check_skill_stealth_wrong_ability(client, db_session):
    """Stealth uses dexterity — sending with strength should 400."""
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        "/api/v1/dice/check",
        json={
            "character_id": str(char.id),
            "ability": "strength",
            "skill": "stealth",
        },
    )
    assert resp.status_code == 400
    assert "dexterity" in resp.json()["detail"].lower()
