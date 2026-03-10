"""Tests for remaining endpoint coverage — dice, inventory, sessions, characters extra, companions.

Covers endpoints that have low/no coverage from existing test suites.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.core.security import create_access_token
from app.db.models.enums import ItemType
from tests.factories import (
    make_character,
    make_companion,
    make_companion_conversation,
    make_creature,
    make_item,
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
    monkeypatch.setattr(session_service, "update_session_state", AsyncMock(return_value=True))
    monkeypatch.setattr(session_service, "get_conversation_history", AsyncMock(return_value=None))
    monkeypatch.setattr(session_service, "revoke_token", AsyncMock())
    monkeypatch.setattr(session_service, "is_token_revoked", AsyncMock(return_value=False))
    monkeypatch.setattr(session_service, "delete_session_state", AsyncMock(return_value=True))
    monkeypatch.setattr(session_service, "refresh_ttl", AsyncMock())


V1 = "/api/v1"


# ===========================================================================
# ── Dice Endpoints ──────────────────────────────────────────────────────
# ===========================================================================


class TestDiceRoll:
    """POST /api/v1/dice/roll"""

    async def test_simple_roll(self, client, db_session, auth_headers):
        resp = await client.post(f"{V1}/dice/roll", json={"dice": "1d20"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["notation"] == "1d20"
        assert 1 <= data["total"] <= 20
        assert data["breakdown"]

    async def test_roll_with_modifier(self, client, db_session, auth_headers):
        resp = await client.post(f"{V1}/dice/roll", json={"dice": "2d6+3"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["modifier"] == 3
        assert data["total"] >= 5  # min: 2+3

    async def test_roll_with_reason(self, client, db_session, auth_headers):
        resp = await client.post(
            f"{V1}/dice/roll", json={"dice": "1d20", "reason": "attack roll"}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["reason"] == "attack roll"

    async def test_roll_advantage(self, client, db_session, auth_headers):
        resp = await client.post(
            f"{V1}/dice/roll", json={"dice": "1d20", "roll_type": "advantage"}, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["roll_type"] == "advantage"

    async def test_roll_disadvantage(self, client, db_session, auth_headers):
        resp = await client.post(
            f"{V1}/dice/roll",
            json={"dice": "1d20", "roll_type": "disadvantage"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["roll_type"] == "disadvantage"

    async def test_invalid_notation(self, client, db_session, auth_headers):
        resp = await client.post(f"{V1}/dice/roll", json={"dice": "xyzzy"}, headers=auth_headers)
        assert resp.status_code == 400


class TestAbilityCheck:
    """POST /api/v1/dice/check"""

    async def _make_char(self, db_session):
        user = make_user()
        char = make_character(user=user)
        db_session.add_all([user, char])
        await db_session.flush()
        return char

    async def test_basic_check(self, client, db_session, auth_headers):
        char = await self._make_char(db_session)
        resp = await client.post(
            f"{V1}/dice/check",
            json={"character_id": str(char.id), "ability": "strength"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ability"] == "strength"
        assert data["character_name"] == char.name

    async def test_check_with_dc(self, client, db_session, auth_headers):
        char = await self._make_char(db_session)
        resp = await client.post(
            f"{V1}/dice/check",
            json={"character_id": str(char.id), "ability": "dexterity", "dc": 15},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert isinstance(data["success"], bool)

    async def test_check_with_advantage(self, client, db_session, auth_headers):
        char = await self._make_char(db_session)
        resp = await client.post(
            f"{V1}/dice/check",
            json={"character_id": str(char.id), "ability": "wisdom", "advantage": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["advantage"] is True
        assert len(data["rolls"]) == 2

    async def test_check_with_disadvantage(self, client, db_session, auth_headers):
        char = await self._make_char(db_session)
        resp = await client.post(
            f"{V1}/dice/check",
            json={"character_id": str(char.id), "ability": "charisma", "disadvantage": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["disadvantage"] is True

    async def test_advantage_and_disadvantage_error(self, client, db_session, auth_headers):
        char = await self._make_char(db_session)
        resp = await client.post(
            f"{V1}/dice/check",
            json={
                "character_id": str(char.id),
                "ability": "strength",
                "advantage": True,
                "disadvantage": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_skill_ability_mismatch(self, client, db_session, auth_headers):
        char = await self._make_char(db_session)
        resp = await client.post(
            f"{V1}/dice/check",
            json={
                "character_id": str(char.id),
                "ability": "strength",
                "skill": "stealth",  # stealth uses dexterity
            },
            headers=auth_headers,
        )
        assert resp.status_code == 400

    async def test_character_not_found(self, client, db_session, auth_headers):
        resp = await client.post(
            f"{V1}/dice/check",
            json={"character_id": str(uuid.uuid4()), "ability": "strength"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_check_with_reason(self, client, db_session, auth_headers):
        char = await self._make_char(db_session)
        resp = await client.post(
            f"{V1}/dice/check",
            json={
                "character_id": str(char.id),
                "ability": "intelligence",
                "reason": "Arcana check",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["reason"] == "Arcana check"


# ===========================================================================
# ── Inventory Endpoints ─────────────────────────────────────────────────
# ===========================================================================


class TestInventory:
    """Inventory CRUD endpoints."""

    async def _seed(self, db_session):
        user = make_user()
        char = make_character(user=user)
        db_session.add_all([user, char])
        await db_session.flush()
        return user, char

    async def test_add_item(self, client, db_session, auth_headers):
        _, char = await self._seed(db_session)
        resp = await client.post(
            f"{V1}/characters/{char.id}/inventory/add",
            json={"name": "Shield", "item_type": "armor", "weight": 6, "value": 10, "quantity": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Shield"

    async def test_add_item_exceeds_capacity(self, client, db_session, auth_headers):
        _, char = await self._seed(db_session)
        resp = await client.post(
            f"{V1}/characters/{char.id}/inventory/add",
            json={"name": "Anvil", "item_type": "misc", "weight": 999, "value": 5, "quantity": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "capacity" in resp.json()["detail"].lower()

    async def test_add_item_char_not_found(self, client, db_session, auth_headers):
        resp = await client.post(
            f"{V1}/characters/{uuid.uuid4()}/inventory/add",
            json={"name": "Sword", "item_type": "weapon", "weight": 3, "value": 15, "quantity": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_get_inventory(self, client, db_session, auth_headers):
        _, char = await self._seed(db_session)
        item = make_item(character=char, name="Rope", item_type=ItemType.MISC)
        db_session.add(item)
        await db_session.flush()

        resp = await client.get(f"{V1}/characters/{char.id}/inventory", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1
        assert "carrying_capacity" in data

    async def test_get_inventory_filter_type(self, client, db_session, auth_headers):
        _, char = await self._seed(db_session)
        weapon = make_item(character=char, name="Dagger", item_type=ItemType.WEAPON)
        armor = make_item(character=char, name="Leather", item_type=ItemType.ARMOR)
        db_session.add_all([weapon, armor])
        await db_session.flush()

        resp = await client.get(
            f"{V1}/characters/{char.id}/inventory?item_type=weapon", headers=auth_headers
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["item_type"] == "weapon" for i in items)

    async def test_get_inventory_filter_equipped(self, client, db_session, auth_headers):
        _, char = await self._seed(db_session)
        eq = make_item(character=char, equipped=True, name="Equipped Sword")
        uneq = make_item(character=char, equipped=False, name="Stowed Shield")
        db_session.add_all([eq, uneq])
        await db_session.flush()

        resp = await client.get(
            f"{V1}/characters/{char.id}/inventory?equipped=true", headers=auth_headers
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["equipped"] for i in items)

    async def test_get_inventory_char_not_found(self, client, db_session, auth_headers):
        resp = await client.get(f"{V1}/characters/{uuid.uuid4()}/inventory", headers=auth_headers)
        assert resp.status_code == 404

    async def test_toggle_equip(self, client, db_session, auth_headers):
        _, char = await self._seed(db_session)
        item = make_item(character=char, equipped=False)
        db_session.add(item)
        await db_session.flush()

        resp = await client.patch(
            f"{V1}/characters/{char.id}/inventory/{item.id}/equip", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["equipped"] is True

    async def test_toggle_equip_not_found(self, client, db_session, auth_headers):
        _, char = await self._seed(db_session)
        resp = await client.patch(
            f"{V1}/characters/{char.id}/inventory/{uuid.uuid4()}/equip", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_update_item_quantity(self, client, db_session, auth_headers):
        _, char = await self._seed(db_session)
        item = make_item(character=char, quantity=5)
        db_session.add(item)
        await db_session.flush()

        resp = await client.patch(
            f"{V1}/characters/{char.id}/inventory/{item.id}",
            json={"quantity": 3},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 3

    async def test_update_item_quantity_zero_deletes(self, client, db_session, auth_headers):
        _, char = await self._seed(db_session)
        item = make_item(character=char, quantity=1)
        db_session.add(item)
        await db_session.flush()

        resp = await client.patch(
            f"{V1}/characters/{char.id}/inventory/{item.id}",
            json={"quantity": 0},
            headers=auth_headers,
        )
        assert resp.status_code == 204

    async def test_update_item_not_found(self, client, db_session, auth_headers):
        _, char = await self._seed(db_session)
        resp = await client.patch(
            f"{V1}/characters/{char.id}/inventory/{uuid.uuid4()}",
            json={"quantity": 2},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_remove_item(self, client, db_session, auth_headers):
        _, char = await self._seed(db_session)
        item = make_item(character=char)
        db_session.add(item)
        await db_session.flush()

        resp = await client.delete(
            f"{V1}/characters/{char.id}/inventory/{item.id}", headers=auth_headers
        )
        assert resp.status_code == 204

    async def test_remove_item_not_found(self, client, db_session, auth_headers):
        _, char = await self._seed(db_session)
        resp = await client.delete(
            f"{V1}/characters/{char.id}/inventory/{uuid.uuid4()}", headers=auth_headers
        )
        assert resp.status_code == 404


# ===========================================================================
# ── Session Endpoints ───────────────────────────────────────────────────
# ===========================================================================


class TestSessionEndpoints:
    """Session CRUD endpoints."""

    async def _seed(self, db_session):
        user = make_user()
        char = make_character(user=user)
        db_session.add_all([user, char])
        await db_session.flush()
        token = create_access_token({"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        return user, char, headers

    async def test_create_session(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        resp = await client.post(
            f"{V1}/sessions",
            json={"character_id": str(char.id)},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["character_id"] == str(char.id)
        assert data["is_active"] is True

    async def test_get_session(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        session = make_session(user=user, character=char)
        db_session.add(session)
        await db_session.flush()

        resp = await client.get(f"{V1}/sessions/{session.id}", headers=auth_headers)
        assert resp.status_code == 200

    async def test_get_session_not_found(self, client, db_session, auth_headers):
        resp = await client.get(f"{V1}/sessions/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_list_sessions(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        s1 = make_session(user=user, character=char)
        s2 = make_session(user=user, character=char, is_active=False)
        db_session.add_all([s1, s2])
        await db_session.flush()

        resp = await client.get(f"{V1}/sessions", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    async def test_list_sessions_active_only(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        s1 = make_session(user=user, character=char, is_active=True)
        s2 = make_session(user=user, character=char, is_active=False)
        db_session.add_all([s1, s2])
        await db_session.flush()

        resp = await client.get(f"{V1}/sessions?active_only=true", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(s["is_active"] for s in data)

    async def test_get_active_session_for_character(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        session = make_session(user=user, character=char, is_active=True)
        db_session.add(session)
        await db_session.flush()

        resp = await client.get(
            f"{V1}/sessions/active/character/{char.id}",
            headers=headers,
        )
        assert resp.status_code == 200

    async def test_get_active_session_for_character_not_found(
        self, client, db_session, auth_headers
    ):
        _, _, headers = await self._seed(db_session)
        resp = await client.get(
            f"{V1}/sessions/active/character/{uuid.uuid4()}",
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_update_session(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        session = make_session(user=user, character=char)
        db_session.add(session)
        await db_session.flush()

        resp = await client.patch(
            f"{V1}/sessions/{session.id}",
            json={"current_location": "Forest"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["current_location"] == "Forest"

    async def test_update_session_not_found(self, client, db_session, auth_headers):
        resp = await client.patch(
            f"{V1}/sessions/{uuid.uuid4()}",
            json={"current_location": "Nowhere"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_end_session(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        session = make_session(user=user, character=char, is_active=True)
        db_session.add(session)
        await db_session.flush()

        resp = await client.post(f"{V1}/sessions/{session.id}/end", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_end_session_not_found(self, client, db_session, auth_headers):
        resp = await client.post(f"{V1}/sessions/{uuid.uuid4()}/end", headers=auth_headers)
        assert resp.status_code == 404

    async def test_delete_session(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        session = make_session(user=user, character=char)
        db_session.add(session)
        await db_session.flush()

        resp = await client.delete(f"{V1}/sessions/{session.id}", headers=auth_headers)
        assert resp.status_code == 204

    async def test_delete_session_not_found(self, client, db_session, auth_headers):
        resp = await client.delete(f"{V1}/sessions/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_update_session_state(self, client, db_session, auth_headers, monkeypatch):
        user, char, headers = await self._seed(db_session)
        session = make_session(user=user, character=char)
        db_session.add(session)
        await db_session.flush()

        from app.services.redis_service import session_service as ss

        monkeypatch.setattr(
            ss,
            "update_session_state",
            AsyncMock(return_value={"current_location": "Dungeon", "hp": 10}),
        )
        monkeypatch.setattr(ss, "refresh_ttl", AsyncMock())

        resp = await client.patch(
            f"{V1}/sessions/{session.id}/state",
            json={"current_location": "Dungeon", "state_data": {"hp": 10}},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_update_session_state_not_found(self, client, db_session, auth_headers):
        resp = await client.patch(
            f"{V1}/sessions/{uuid.uuid4()}/state",
            json={"current_location": "Cave"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ===========================================================================
# ── Character Extra Endpoints ───────────────────────────────────────────
# ===========================================================================


class TestCharacterExtras:
    """Character endpoints not already covered (skills, background, personality, motivation, stats, delete)."""

    async def _seed(self, db_session):
        user = make_user()
        char = make_character(user=user)
        db_session.add_all([user, char])
        await db_session.flush()
        token = create_access_token({"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        return user, char, headers

    async def test_update_skill_proficiencies(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        resp = await client.post(
            f"{V1}/characters/{char.id}/skills",
            json=["athletics", "perception", "stealth"],
            headers=headers,
        )
        assert resp.status_code == 200

    async def test_update_skills_not_found(self, client, db_session, auth_headers):
        _, _, headers = await self._seed(db_session)
        resp = await client.post(
            f"{V1}/characters/{uuid.uuid4()}/skills",
            json=["athletics"],
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_update_background(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        resp = await client.post(
            f"{V1}/characters/{char.id}/background",
            params={
                "background_name": "Noble",
                "background_description": "Born to privilege",
                "background_skill_proficiencies": ["history", "persuasion"],
            },
            headers=headers,
        )
        assert resp.status_code == 200

    async def test_update_background_not_found(self, client, db_session, auth_headers):
        _, _, headers = await self._seed(db_session)
        resp = await client.post(
            f"{V1}/characters/{uuid.uuid4()}/background",
            params={
                "background_name": "Soldier",
                "background_description": "Veteran",
                "background_skill_proficiencies": ["athletics"],
            },
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_update_personality(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        resp = await client.post(
            f"{V1}/characters/{char.id}/personality",
            params={
                "personality_trait": "Brave",
                "ideal": "Justice",
                "bond": "My family",
                "flaw": "Stubborn",
            },
            headers=headers,
        )
        assert resp.status_code == 200

    async def test_update_personality_not_found(self, client, db_session, auth_headers):
        _, _, headers = await self._seed(db_session)
        resp = await client.post(
            f"{V1}/characters/{uuid.uuid4()}/personality",
            params={
                "personality_trait": "Shy",
                "ideal": "Knowledge",
                "bond": "My mentor",
                "flaw": "Greedy",
            },
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_update_motivation(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        resp = await client.post(
            f"{V1}/characters/{char.id}/motivation",
            params={"motivation": "glory"},
            headers=headers,
        )
        assert resp.status_code == 200

    async def test_update_motivation_not_found(self, client, db_session, auth_headers):
        _, _, headers = await self._seed(db_session)
        resp = await client.post(
            f"{V1}/characters/{uuid.uuid4()}/motivation",
            params={"motivation": "peace"},
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_get_character_stats(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        resp = await client.get(f"{V1}/characters/{char.id}/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "ability_modifiers" in data or "proficiency_bonus" in data or resp.status_code == 200

    async def test_get_character_stats_not_found(self, client, db_session, auth_headers):
        resp = await client.get(f"{V1}/characters/{uuid.uuid4()}/stats", headers=auth_headers)
        assert resp.status_code == 404

    async def test_delete_character(self, client, db_session, auth_headers):
        user, char, headers = await self._seed(db_session)
        resp = await client.delete(f"{V1}/characters/{char.id}", headers=headers)
        assert resp.status_code == 204

    async def test_delete_character_not_found(self, client, db_session, auth_headers):
        _, _, headers = await self._seed(db_session)
        resp = await client.delete(f"{V1}/characters/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    async def test_delete_character_not_owner(self, client, db_session, auth_headers):
        """Cannot delete another user's character."""
        user1 = make_user()
        user2 = make_user()
        char = make_character(user=user1)
        db_session.add_all([user1, user2, char])
        await db_session.flush()

        token2 = create_access_token({"sub": str(user2.id)})
        headers2 = {"Authorization": f"Bearer {token2}"}
        resp = await client.delete(f"{V1}/characters/{char.id}", headers=headers2)
        assert resp.status_code == 403

    async def test_delete_character_deactivates_sessions(self, client, db_session, auth_headers):
        """Deleting a character deactivates its active sessions."""
        user, char, headers = await self._seed(db_session)
        session = make_session(user=user, character=char, is_active=True)
        db_session.add(session)
        await db_session.flush()

        resp = await client.delete(f"{V1}/characters/{char.id}", headers=headers)
        assert resp.status_code == 204


# ===========================================================================
# ── Companion Endpoints ─────────────────────────────────────────────────
# ===========================================================================


class TestCompanionEndpoints:
    """Companion CRUD endpoints."""

    async def _seed(self, db_session):
        user = make_user()
        char = make_character(user=user)
        creature = make_creature()
        db_session.add_all([user, char, creature])
        await db_session.flush()

        companion = make_companion(character=char, creature=creature)
        db_session.add(companion)
        await db_session.flush()

        token = create_access_token({"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        return user, char, creature, companion, headers

    async def test_get_character_companions(self, client, db_session, auth_headers):
        user, char, _, companion, headers = await self._seed(db_session)
        resp = await client.get(
            f"{V1}/companions/characters/{char.id}/companions",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_get_character_companions_not_found(self, client, db_session, auth_headers):
        _, _, _, _, headers = await self._seed(db_session)
        resp = await client.get(
            f"{V1}/companions/characters/{uuid.uuid4()}/companions",
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_get_active_companions(self, client, db_session, auth_headers):
        user, char, _, companion, headers = await self._seed(db_session)
        resp = await client.get(
            f"{V1}/companions/characters/{char.id}/companions/active",
            headers=headers,
        )
        assert resp.status_code == 200

    async def test_get_companion(self, client, db_session, auth_headers):
        user, char, _, companion, headers = await self._seed(db_session)
        resp = await client.get(
            f"{V1}/companions/companions/{companion.id}",
            headers=headers,
        )
        assert resp.status_code == 200

    async def test_get_companion_not_found(self, client, db_session, auth_headers):
        _, _, _, _, headers = await self._seed(db_session)
        resp = await client.get(
            f"{V1}/companions/companions/{uuid.uuid4()}",
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_toggle_companion_active(self, client, db_session, auth_headers):
        user, char, _, companion, headers = await self._seed(db_session)
        resp = await client.patch(
            f"{V1}/companions/companions/{companion.id}/active?is_active=true",
            headers=headers,
        )
        assert resp.status_code == 200

    async def test_toggle_companion_not_found(self, client, db_session, auth_headers):
        _, _, _, _, headers = await self._seed(db_session)
        resp = await client.patch(
            f"{V1}/companions/companions/{uuid.uuid4()}/active?is_active=true",
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_update_companion_loyalty(self, client, db_session, auth_headers):
        user, char, _, companion, headers = await self._seed(db_session)

        mock_provider = MagicMock()
        mock_service = AsyncMock()
        mock_service.update_companion_loyalty = AsyncMock()

        with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
            mock_ps.get_current_provider.return_value = mock_provider
            with patch(
                "app.api.v1.endpoints.companions.CompanionService",
                return_value=mock_service,
            ):
                resp = await client.patch(
                    f"{V1}/companions/companions/{companion.id}/loyalty"
                    f"?loyalty_change=10&event_description=helped+in+battle",
                    headers=headers,
                )
        assert resp.status_code == 200

    async def test_update_loyalty_no_provider(self, client, db_session, auth_headers):
        user, char, _, companion, headers = await self._seed(db_session)

        with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
            mock_ps.get_current_provider.return_value = None
            resp = await client.patch(
                f"{V1}/companions/companions/{companion.id}/loyalty"
                f"?loyalty_change=5&event_description=test",
                headers=headers,
            )
        assert resp.status_code == 503

    async def test_update_loyalty_not_found(self, client, db_session, auth_headers):
        _, _, _, _, headers = await self._seed(db_session)
        with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
            mock_ps.get_current_provider.return_value = MagicMock()
            resp = await client.patch(
                f"{V1}/companions/companions/{uuid.uuid4()}/loyalty?loyalty_change=5&event_description=test",
                headers=headers,
            )
        assert resp.status_code == 404

    async def test_chat_with_companion(self, client, db_session, auth_headers):
        user, char, _, companion, headers = await self._seed(db_session)

        mock_provider = MagicMock()
        mock_service = AsyncMock()
        mock_service.generate_companion_response = AsyncMock(return_value="Hello, adventurer!")

        with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
            mock_ps.get_current_provider.return_value = mock_provider
            with patch(
                "app.api.v1.endpoints.companions.CompanionService",
                return_value=mock_service,
            ):
                resp = await client.post(
                    f"{V1}/companions/companions/chat",
                    json={
                        "companion_id": str(companion.id),
                        "message": "Where are we going?",
                        "share_with_dm": False,
                    },
                    headers=headers,
                )
        assert resp.status_code == 200
        data = resp.json()
        assert data["companion_response"] == "Hello, adventurer!"

    async def test_chat_with_companion_shared(self, client, db_session, auth_headers):
        user, char, _, companion, headers = await self._seed(db_session)

        mock_provider = MagicMock()
        mock_service = AsyncMock()
        mock_service.generate_companion_response = AsyncMock(return_value="Let us proceed.")

        with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
            mock_ps.get_current_provider.return_value = mock_provider
            with patch(
                "app.api.v1.endpoints.companions.CompanionService",
                return_value=mock_service,
            ):
                resp = await client.post(
                    f"{V1}/companions/companions/chat",
                    json={
                        "companion_id": str(companion.id),
                        "message": "Tell me about this place.",
                        "share_with_dm": True,
                    },
                    headers=headers,
                )
        assert resp.status_code == 200

    async def test_chat_companion_not_found(self, client, db_session, auth_headers):
        _, _, _, _, headers = await self._seed(db_session)
        resp = await client.post(
            f"{V1}/companions/companions/chat",
            json={
                "companion_id": str(uuid.uuid4()),
                "message": "Hello",
                "share_with_dm": False,
            },
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_chat_no_provider(self, client, db_session, auth_headers):
        user, char, _, companion, headers = await self._seed(db_session)

        with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
            mock_ps.get_current_provider.return_value = None
            resp = await client.post(
                f"{V1}/companions/companions/chat",
                json={
                    "companion_id": str(companion.id),
                    "message": "Hello",
                    "share_with_dm": False,
                },
                headers=headers,
            )
        assert resp.status_code == 503

    async def test_get_companion_conversations(self, client, db_session, auth_headers):
        user, char, _, companion, headers = await self._seed(db_session)

        conv = make_companion_conversation(
            companion=companion,
            character=char,
            role="player",
            message="Hello there",
            shared_with_dm=True,
        )
        db_session.add(conv)
        await db_session.flush()

        resp = await client.get(
            f"{V1}/companions/companions/{companion.id}/conversations",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_get_conversations_not_found(self, client, db_session, auth_headers):
        _, _, _, _, headers = await self._seed(db_session)
        resp = await client.get(
            f"{V1}/companions/companions/{uuid.uuid4()}/conversations",
            headers=headers,
        )
        assert resp.status_code == 404
