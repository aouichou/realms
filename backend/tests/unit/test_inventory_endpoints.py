"""Tests for inventory API endpoints (/api/v1/characters/{id}/inventory)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from tests.factories import make_character, make_item, make_session, make_user

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


# -- helpers ---------------------------------------------------------------

BASE = "/api/v1/characters"


def _inv_url(char_id, suffix=""):
    return f"{BASE}/{char_id}/inventory{suffix}"


# ===========================================================================
# POST /api/v1/characters/{character_id}/inventory/add
# ===========================================================================


async def test_add_item_happy(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    body = {
        "name": "Healing Potion",
        "item_type": "consumable",
        "weight": 0.5,
        "value": 50,
        "quantity": 2,
    }
    resp = await client.post(_inv_url(char.id, "/add"), json=body, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Healing Potion"
    assert data["item_type"] == "consumable"
    assert data["quantity"] == 2
    assert data["equipped"] is False


async def test_add_item_with_properties(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    body = {
        "name": "Flame Tongue",
        "item_type": "weapon",
        "weight": 3.0,
        "value": 5000,
        "properties": {"damage": "2d6", "damage_type": "fire"},
    }
    resp = await client.post(_inv_url(char.id, "/add"), json=body, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["properties"]["damage"] == "2d6"


async def test_add_item_character_not_found(client, db_session, auth_headers):
    body = {
        "name": "Ghost Sword",
        "item_type": "weapon",
        "weight": 3,
        "value": 10,
    }
    resp = await client.post(_inv_url(uuid.uuid4(), "/add"), json=body, headers=auth_headers)
    assert resp.status_code == 404


async def test_add_item_exceeds_weight_capacity(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user, carrying_capacity=10)
    db_session.add_all([user, char])
    await db_session.flush()

    body = {
        "name": "Boulder",
        "item_type": "misc",
        "weight": 20,
        "value": 0,
        "quantity": 1,
    }
    resp = await client.post(_inv_url(char.id, "/add"), json=body, headers=auth_headers)
    assert resp.status_code == 400
    assert "capacity" in resp.json()["detail"].lower()


async def test_add_item_exceeds_weight_with_existing_items(client, db_session, auth_headers):
    """Adding new item when existing items already consume most capacity."""
    user = make_user()
    char = make_character(user=user, carrying_capacity=15)
    existing = make_item(character=char, weight=10.0, quantity=1)
    db_session.add_all([user, char, existing])
    await db_session.flush()

    body = {
        "name": "Heavy Shield",
        "item_type": "armor",
        "weight": 6.0,
        "value": 10,
        "quantity": 1,
    }
    resp = await client.post(_inv_url(char.id, "/add"), json=body, headers=auth_headers)
    assert resp.status_code == 400
    assert "capacity" in resp.json()["detail"].lower()


async def test_add_item_equipped_true(client, db_session, auth_headers):
    """Add an item that is immediately equipped."""
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    body = {
        "name": "Shield",
        "item_type": "armor",
        "weight": 6.0,
        "value": 10,
        "equipped": True,
    }
    resp = await client.post(_inv_url(char.id, "/add"), json=body, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["equipped"] is True


async def test_add_item_memory_capture_with_session(client, db_session, auth_headers):
    """When a GameSession exists for the character, memory capture is invoked."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char, is_active=True)
    db_session.add_all([user, char, session])
    await db_session.flush()

    with patch(
        "app.api.v1.endpoints.inventory.MemoryCaptureService.capture_loot",
        new_callable=AsyncMock,
    ) as mock_loot:
        body = {
            "name": "Golden Ring",
            "item_type": "misc",
            "weight": 0.1,
            "value": 100,
            "quantity": 1,
        }
        resp = await client.post(_inv_url(char.id, "/add"), json=body, headers=auth_headers)
        assert resp.status_code == 201
        mock_loot.assert_awaited_once()
        call_kwargs = mock_loot.call_args
        assert (
            "Golden Ring" in call_kwargs.kwargs.get("items", call_kwargs[1].get("items", [""]))[0]
        )


async def test_add_item_memory_capture_failure_still_succeeds(client, db_session, auth_headers):
    """If memory capture raises, the item is still created successfully."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char, is_active=True)
    db_session.add_all([user, char, session])
    await db_session.flush()

    with patch(
        "app.api.v1.endpoints.inventory.MemoryCaptureService.capture_loot",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Redis down"),
    ):
        body = {
            "name": "Broken Amulet",
            "item_type": "misc",
            "weight": 0.2,
            "value": 5,
            "quantity": 1,
        }
        resp = await client.post(_inv_url(char.id, "/add"), json=body, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "Broken Amulet"


# ===========================================================================
# GET /api/v1/characters/{character_id}/inventory
# ===========================================================================


async def test_get_inventory_empty(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.get(_inv_url(char.id), headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["current_weight"] == 0
    assert data["carrying_capacity"] == char.carrying_capacity


async def test_get_inventory_with_items(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    i1 = make_item(character=char, name="Longsword", weight=3.0, quantity=1)
    i2 = make_item(character=char, name="Shield", item_type="armor", weight=6.0, quantity=1)
    db_session.add_all([user, char, i1, i2])
    await db_session.flush()

    resp = await client.get(_inv_url(char.id), headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["current_weight"] == 9.0


async def test_get_inventory_filter_by_type(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    i1 = make_item(character=char, name="Longsword", item_type="weapon")
    i2 = make_item(character=char, name="Chain Mail", item_type="armor")
    db_session.add_all([user, char, i1, i2])
    await db_session.flush()

    resp = await client.get(_inv_url(char.id) + "?item_type=weapon", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["item_type"] == "weapon"


async def test_get_inventory_filter_by_equipped(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    i1 = make_item(character=char, name="Equipped Sword", equipped=True)
    i2 = make_item(character=char, name="Stashed Dagger", equipped=False)
    db_session.add_all([user, char, i1, i2])
    await db_session.flush()

    resp = await client.get(_inv_url(char.id) + "?equipped=true", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Equipped Sword"


async def test_get_inventory_character_not_found(client, db_session, auth_headers):
    resp = await client.get(_inv_url(uuid.uuid4()), headers=auth_headers)
    assert resp.status_code == 404


async def test_get_inventory_weight_percentage(client, db_session, auth_headers):
    """Verify weight_percentage is calculated correctly."""
    user = make_user()
    char = make_character(user=user, carrying_capacity=100)
    item = make_item(character=char, weight=25.0, quantity=2)  # 50 lbs total
    db_session.add_all([user, char, item])
    await db_session.flush()

    resp = await client.get(_inv_url(char.id), headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_weight"] == 50.0
    assert data["weight_percentage"] == pytest.approx(50.0)


async def test_get_inventory_filter_by_type_and_equipped(client, db_session, auth_headers):
    """Combine both item_type and equipped filters."""
    user = make_user()
    char = make_character(user=user)
    i1 = make_item(character=char, name="Equipped Sword", item_type="weapon", equipped=True)
    i2 = make_item(character=char, name="Stashed Sword", item_type="weapon", equipped=False)
    i3 = make_item(character=char, name="Worn Armor", item_type="armor", equipped=True)
    db_session.add_all([user, char, i1, i2, i3])
    await db_session.flush()

    resp = await client.get(_inv_url(char.id) + "?item_type=weapon&equipped=true", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Equipped Sword"


# ===========================================================================
# PATCH /api/v1/characters/{char}/inventory/{item}/equip
# ===========================================================================


async def test_toggle_equip_on(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    item = make_item(character=char, equipped=False)
    db_session.add_all([user, char, item])
    await db_session.flush()

    resp = await client.patch(_inv_url(char.id, f"/{item.id}/equip"), headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["equipped"] is True


async def test_toggle_equip_off(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    item = make_item(character=char, equipped=True)
    db_session.add_all([user, char, item])
    await db_session.flush()

    resp = await client.patch(_inv_url(char.id, f"/{item.id}/equip"), headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["equipped"] is False


async def test_toggle_equip_not_found(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.patch(_inv_url(char.id, f"/{uuid.uuid4()}/equip"), headers=auth_headers)
    assert resp.status_code == 404


async def test_toggle_equip_wrong_character(client, db_session, auth_headers):
    """Item belongs to char1 but request uses char2's ID → 404."""
    user = make_user()
    char1 = make_character(user=user)
    char2 = make_character(user=user)
    item = make_item(character=char1, equipped=False)
    db_session.add_all([user, char1, char2, item])
    await db_session.flush()

    resp = await client.patch(_inv_url(char2.id, f"/{item.id}/equip"), headers=auth_headers)
    assert resp.status_code == 404


# ===========================================================================
# PATCH /api/v1/characters/{char}/inventory/{item}
# ===========================================================================


async def test_update_item_quantity(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    item = make_item(character=char, quantity=3)
    db_session.add_all([user, char, item])
    await db_session.flush()

    resp = await client.patch(_inv_url(char.id, f"/{item.id}"), json={"quantity": 5}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 5


async def test_update_item_properties(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    item = make_item(character=char)
    db_session.add_all([user, char, item])
    await db_session.flush()

    new_props = {"damage": "2d6", "magic": True}
    resp = await client.patch(_inv_url(char.id, f"/{item.id}"), json={"properties": new_props}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["properties"]["magic"] is True


async def test_update_item_quantity_zero_deletes(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    item = make_item(character=char, quantity=1)
    db_session.add_all([user, char, item])
    await db_session.flush()

    resp = await client.patch(_inv_url(char.id, f"/{item.id}"), json={"quantity": 0}, headers=auth_headers)
    assert resp.status_code == 204


async def test_update_item_not_found(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.patch(_inv_url(char.id, f"/{uuid.uuid4()}"), json={"quantity": 1}, headers=auth_headers)
    assert resp.status_code == 404


async def test_update_item_equipped_field(client, db_session, auth_headers):
    """Update only the equipped field via PATCH."""
    user = make_user()
    char = make_character(user=user)
    item = make_item(character=char, equipped=False)
    db_session.add_all([user, char, item])
    await db_session.flush()

    resp = await client.patch(_inv_url(char.id, f"/{item.id}"), json={"equipped": True}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["equipped"] is True


async def test_update_item_multiple_fields(client, db_session, auth_headers):
    """Update quantity, equipped, and properties in one request."""
    user = make_user()
    char = make_character(user=user)
    item = make_item(character=char, quantity=1, equipped=False)
    db_session.add_all([user, char, item])
    await db_session.flush()

    body = {"quantity": 3, "equipped": True, "properties": {"enchanted": True}}
    resp = await client.patch(_inv_url(char.id, f"/{item.id}"), json=body, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["quantity"] == 3
    assert data["equipped"] is True
    assert data["properties"]["enchanted"] is True


async def test_update_item_negative_quantity_rejected(client, db_session, auth_headers):
    """Negative quantity is rejected by schema validation (quantity >= 0)."""
    user = make_user()
    char = make_character(user=user)
    item = make_item(character=char, quantity=2)
    db_session.add_all([user, char, item])
    await db_session.flush()

    resp = await client.patch(_inv_url(char.id, f"/{item.id}"), json={"quantity": -1}, headers=auth_headers)
    assert resp.status_code == 422


# ===========================================================================
# DELETE /api/v1/characters/{char}/inventory/{item}
# ===========================================================================


async def test_delete_item_happy(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    item = make_item(character=char, name="ToRemove")
    db_session.add_all([user, char, item])
    await db_session.flush()

    resp = await client.delete(_inv_url(char.id, f"/{item.id}"), headers=auth_headers)
    assert resp.status_code == 204


async def test_delete_item_not_found(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.delete(_inv_url(char.id, f"/{uuid.uuid4()}"), headers=auth_headers)
    assert resp.status_code == 404


async def test_add_multiple_items_weight_tracking(client, db_session, auth_headers):
    """Add two items and confirm total weight is tracked correctly."""
    user = make_user()
    char = make_character(user=user, carrying_capacity=100)
    db_session.add_all([user, char])
    await db_session.flush()

    await client.post(
        _inv_url(char.id, "/add"),
        json={"name": "Sword", "item_type": "weapon", "weight": 3.0, "value": 15},
        headers=auth_headers,
    )
    await client.post(
        _inv_url(char.id, "/add"),
        json={"name": "Shield", "item_type": "armor", "weight": 6.0, "value": 10},
        headers=auth_headers,
    )

    resp = await client.get(_inv_url(char.id), headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["current_weight"] == 9.0


async def test_delete_item_wrong_character(client, db_session, auth_headers):
    """Deleting an item that belongs to another character returns 404."""
    user = make_user()
    char1 = make_character(user=user)
    char2 = make_character(user=user)
    item = make_item(character=char1)
    db_session.add_all([user, char1, char2, item])
    await db_session.flush()

    resp = await client.delete(_inv_url(char2.id, f"/{item.id}"), headers=auth_headers)
    assert resp.status_code == 404
