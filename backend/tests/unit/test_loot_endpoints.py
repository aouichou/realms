"""Tests for loot endpoints (/api/v1/loot)."""

from __future__ import annotations

import pytest
import pytest_asyncio

from app.api.v1.endpoints.loot import get_cr_tier, roll_dice

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


BASE = "/api/v1/loot"


# ===========================================================================
# Pure function tests: get_cr_tier
# ===========================================================================


@pytest.mark.parametrize(
    "cr, expected",
    [
        (0, "0-4"),
        (1, "0-4"),
        (4, "0-4"),
        (5, "5-10"),
        (10, "5-10"),
        (11, "11-16"),
        (16, "11-16"),
        (17, "17+"),
        (20, "17+"),
        (30, "17+"),
    ],
)
def test_get_cr_tier(cr, expected):
    assert get_cr_tier(cr) == expected


# ===========================================================================
# Pure function tests: roll_dice
# ===========================================================================


def test_roll_dice_basic():
    """1d6 => should be between 1 and 6."""
    for _ in range(50):
        result = roll_dice("1d6")
        assert 1 <= result <= 6


def test_roll_dice_multiple():
    """2d6 => should be between 2 and 12."""
    for _ in range(50):
        result = roll_dice("2d6")
        assert 2 <= result <= 12


def test_roll_dice_with_modifier():
    """1d20+5 => should be between 6 and 25."""
    for _ in range(50):
        result = roll_dice("1d20+5")
        assert 6 <= result <= 25


def test_roll_dice_d20():
    for _ in range(50):
        result = roll_dice("1d20")
        assert 1 <= result <= 20


# ===========================================================================
# GET /api/v1/loot/crafting/recipes
# ===========================================================================


async def test_get_recipes_all(client):
    resp = await client.get(f"{BASE}/crafting/recipes")
    assert resp.status_code == 200
    data = resp.json()
    assert "recipes" in data
    assert len(data["recipes"]) > 0
    # Every recipe has required fields
    for recipe in data["recipes"]:
        assert "id" in recipe
        assert "name" in recipe
        assert "required_items" in recipe
        assert "required_skill" in recipe
        assert "dc" in recipe


async def test_get_recipes_filter_by_skill(client):
    resp = await client.get(f"{BASE}/crafting/recipes", params={"skill": "Medicine"})
    assert resp.status_code == 200
    data = resp.json()
    for recipe in data["recipes"]:
        assert recipe["required_skill"].lower() == "medicine"


async def test_get_recipes_filter_no_match(client):
    resp = await client.get(f"{BASE}/crafting/recipes", params={"skill": "Nonexistent"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["recipes"] == []


# ===========================================================================
# POST /api/v1/loot/loot/generate  (generate_loot endpoint)
# ===========================================================================


async def test_generate_loot(client, db_session):
    """Just verify the endpoint returns a valid structure."""
    resp = await client.post(f"{BASE}/loot/generate", json={"cr": 5, "environment": "dungeon"})
    assert resp.status_code == 200
    data = resp.json()
    assert "loot" in data
    assert "total_value" in data
    assert isinstance(data["loot"], list)


async def test_generate_loot_low_cr(client, db_session):
    resp = await client.post(f"{BASE}/loot/generate", json={"cr": 0, "environment": "forest"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["total_value"], (int, float))


async def test_generate_loot_high_cr(client, db_session):
    resp = await client.post(f"{BASE}/loot/generate", json={"cr": 20, "environment": "underdark"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["loot"], list)
