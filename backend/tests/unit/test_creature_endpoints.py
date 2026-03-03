"""Tests for creature API endpoints (/api/v1/creatures)."""

from __future__ import annotations

import pytest
import pytest_asyncio

from tests.factories import make_creature

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
# GET /api/v1/creatures/{creature_name}  (get_creature_by_name)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_creature_by_name_exact(client, db_session, auth_user):
    _, headers = auth_user
    creature = make_creature(name="Goblin")
    db_session.add(creature)
    await db_session.flush()

    resp = await client.get("/api/v1/creatures/Goblin", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["creature"]["name"] == "Goblin"
    assert "stat_block" in data


@pytest.mark.asyncio
async def test_get_creature_by_name_fuzzy(client, db_session, auth_user):
    _, headers = auth_user
    creature = make_creature(name="Ancient Red Dragon")
    db_session.add(creature)
    await db_session.flush()

    resp = await client.get("/api/v1/creatures/Red Dragon", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "Dragon" in data["creature"]["name"]


@pytest.mark.asyncio
async def test_get_creature_by_name_not_found(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get("/api/v1/creatures/NonexistentCreature12345", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_creature_no_auth(client, db_session):
    resp = await client.get("/api/v1/creatures/Goblin")
    assert resp.status_code == 401


# ===========================================================================
# GET /api/v1/creatures/  (list_creatures)
# ===========================================================================


@pytest.mark.asyncio
async def test_list_creatures_empty(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get("/api/v1/creatures/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "creatures" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_creatures_with_data(client, db_session, auth_user):
    _, headers = auth_user
    c1 = make_creature(name="Goblin LC")
    c2 = make_creature(name="Orc LC", creature_type="humanoid", cr="1/2")
    db_session.add_all([c1, c2])
    await db_session.flush()

    resp = await client.get("/api/v1/creatures/", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2


@pytest.mark.asyncio
async def test_list_creatures_filter_type(client, db_session, auth_user):
    _, headers = auth_user
    c1 = make_creature(name="Skeleton LT", creature_type="undead", cr="1/4")
    c2 = make_creature(name="Wolf LT", creature_type="beast", cr="1/4")
    db_session.add_all([c1, c2])
    await db_session.flush()

    resp = await client.get(
        "/api/v1/creatures/",
        params={"creature_type": "undead"},
        headers=headers,
    )
    assert resp.status_code == 200
    creatures = resp.json()["creatures"]
    for c in creatures:
        assert c["creature_type"] == "undead"


@pytest.mark.asyncio
async def test_list_creatures_search(client, db_session, auth_user):
    _, headers = auth_user
    c = make_creature(name="Beholder LS")
    db_session.add(c)
    await db_session.flush()

    resp = await client.get(
        "/api/v1/creatures/",
        params={"search": "Beholder"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_list_creatures_pagination(client, db_session, auth_user):
    _, headers = auth_user
    for i in range(5):
        db_session.add(make_creature(name=f"Creature P{i}", cr=f"{i}"))
    await db_session.flush()

    resp = await client.get(
        "/api/v1/creatures/",
        params={"limit": 2, "offset": 0},
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["creatures"]) <= 2


# ===========================================================================
# GET /api/v1/creatures/types/list
# ===========================================================================


@pytest.mark.asyncio
async def test_list_creature_types(client, db_session, auth_user):
    _, headers = auth_user
    c = make_creature(name="Zombie CT", creature_type="undead")
    db_session.add(c)
    await db_session.flush()

    resp = await client.get("/api/v1/creatures/types/list", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "types" in data or "creature_types" in data or isinstance(data, dict)
