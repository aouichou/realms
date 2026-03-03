"""Tests for item catalog API endpoints (/api/v1/items)."""

from __future__ import annotations

import pytest
import pytest_asyncio

from tests.factories import make_item_catalog_entry

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
# GET /api/v1/items/search
# ===========================================================================


@pytest.mark.asyncio
async def test_search_items_empty(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get("/api/v1/items/search", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_search_items_with_query(client, db_session, auth_user):
    _, headers = auth_user
    item = make_item_catalog_entry(name="Longsword", description="A versatile weapon")
    db_session.add(item)
    await db_session.flush()

    resp = await client.get(
        "/api/v1/items/search",
        params={"query": "Longsword"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(i["name"] == "Longsword" for i in data["items"])


@pytest.mark.asyncio
async def test_search_items_by_category(client, db_session, auth_user):
    _, headers = auth_user
    item = make_item_catalog_entry(name="Chain Mail", category="armor", description="Heavy armor")
    db_session.add(item)
    await db_session.flush()

    resp = await client.get(
        "/api/v1/items/search",
        params={"category": "armor"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_search_items_by_rarity(client, db_session, auth_user):
    _, headers = auth_user
    item = make_item_catalog_entry(
        name="Flame Tongue", rarity="rare", description="A magical sword"
    )
    db_session.add(item)
    await db_session.flush()

    resp = await client.get(
        "/api/v1/items/search",
        params={"rarity": "rare"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_search_items_pagination(client, db_session, auth_user):
    _, headers = auth_user
    for i in range(5):
        item = make_item_catalog_entry(name=f"Item {i}", description=f"Desc {i}")
        db_session.add(item)
    await db_session.flush()

    resp = await client.get(
        "/api/v1/items/search",
        params={"limit": 2, "offset": 0},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 2
    assert data["total"] >= 5


@pytest.mark.asyncio
async def test_search_items_no_auth(client, db_session):
    resp = await client.get("/api/v1/items/search")
    assert resp.status_code == 401


# ===========================================================================
# GET /api/v1/items/categories
# ===========================================================================


@pytest.mark.asyncio
async def test_list_categories(client, db_session, auth_user):
    _, headers = auth_user
    item = make_item_catalog_entry(name="Dagger Cat", category="weapon", description="A dagger")
    db_session.add(item)
    await db_session.flush()

    resp = await client.get("/api/v1/items/categories", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data


# ===========================================================================
# GET /api/v1/items/random
# ===========================================================================


@pytest.mark.asyncio
async def test_random_item(client, db_session, auth_user):
    _, headers = auth_user
    item = make_item_catalog_entry(name="Potion of Healing R", description="Heals 2d4+2")
    db_session.add(item)
    await db_session.flush()

    resp = await client.get("/api/v1/items/random", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "item" in data


@pytest.mark.asyncio
async def test_random_item_with_filter(client, db_session, auth_user):
    _, headers = auth_user
    item = make_item_catalog_entry(
        name="Rare Amulet", category="wondrous_item", rarity="rare", description="A rare amulet"
    )
    db_session.add(item)
    await db_session.flush()

    resp = await client.get(
        "/api/v1/items/random",
        params={"category": "wondrous_item"},
        headers=headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_random_item_no_match(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get(
        "/api/v1/items/random",
        params={"category": "nonexistent_category"},
        headers=headers,
    )
    assert resp.status_code == 404


# ===========================================================================
# GET /api/v1/items/{item_id}
# ===========================================================================


@pytest.mark.asyncio
async def test_get_item_by_id(client, db_session, auth_user):
    _, headers = auth_user
    item = make_item_catalog_entry(name="Shield ID", description="A shield")
    db_session.add(item)
    await db_session.flush()

    resp = await client.get(f"/api/v1/items/{item.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["item"]["name"] == "Shield ID"


@pytest.mark.asyncio
async def test_get_item_by_id_not_found(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get("/api/v1/items/99999", headers=headers)
    assert resp.status_code == 404


# ===========================================================================
# GET /api/v1/items/name/{item_name}
# ===========================================================================


@pytest.mark.asyncio
async def test_get_item_by_name_exact(client, db_session, auth_user):
    _, headers = auth_user
    item = make_item_catalog_entry(name="Wand of Fireballs", description="A powerful wand")
    db_session.add(item)
    await db_session.flush()

    resp = await client.get("/api/v1/items/name/Wand of Fireballs", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["item"]["name"] == "Wand of Fireballs"


@pytest.mark.asyncio
async def test_get_item_by_name_fuzzy(client, db_session, auth_user):
    _, headers = auth_user
    item = make_item_catalog_entry(name="Boots of Speed", description="Magical boots")
    db_session.add(item)
    await db_session.flush()

    resp = await client.get("/api/v1/items/name/Boots", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_item_by_name_not_found(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get("/api/v1/items/name/NonexistentItem12345", headers=headers)
    assert resp.status_code == 404
