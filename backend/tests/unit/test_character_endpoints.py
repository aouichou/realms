"""Tests for character API endpoints (/api/v1/characters)."""

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
# POST /api/v1/characters  (requires auth)
# ===========================================================================


async def test_create_character_happy_path(client, db_session, auth_user):
    user, headers = auth_user
    body = {"name": "Gandalf", "character_class": "Wizard", "race": "Human"}
    resp = await client.post("/api/v1/characters", headers=headers, json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Gandalf"
    assert data["character_class"] == "Wizard"
    assert data["race"] == "Human"
    assert data["level"] == 1
    assert "id" in data


async def test_create_character_with_ability_scores(client, db_session, auth_user):
    user, headers = auth_user
    body = {
        "name": "Strongman",
        "character_class": "Fighter",
        "race": "Dwarf",
        "ability_scores": {
            "strength": 18,
            "dexterity": 12,
            "constitution": 16,
            "intelligence": 8,
            "wisdom": 10,
            "charisma": 10,
        },
    }
    resp = await client.post("/api/v1/characters", headers=headers, json=body)
    assert resp.status_code == 201
    data = resp.json()
    # Racial bonuses applied: Dwarf gets +2 CON (16 → 18)
    assert data["strength"] == 18
    assert data["constitution"] == 18


async def test_create_character_with_level(client, db_session, auth_user):
    user, headers = auth_user
    body = {"name": "Veteran", "character_class": "Paladin", "race": "Human", "level": 5}
    resp = await client.post("/api/v1/characters", headers=headers, json=body)
    assert resp.status_code == 201
    assert resp.json()["level"] == 5


async def test_create_character_with_background_fields(client, db_session, auth_user):
    user, headers = auth_user
    body = {
        "name": "Lorekeeper",
        "character_class": "Cleric",
        "race": "Elf",
        "background": "A scholar who seeks ancient tomes.",
        "personality": "Curious and studious.",
    }
    resp = await client.post("/api/v1/characters", headers=headers, json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Lorekeeper"
    assert data["character_class"] == "Cleric"
    assert data["race"] == "Elf"


async def test_create_character_invalid_class(client, db_session, auth_user):
    _, headers = auth_user
    body = {"name": "Bad", "character_class": "Ninja", "race": "Human"}
    resp = await client.post("/api/v1/characters", headers=headers, json=body)
    assert resp.status_code == 422


async def test_create_character_invalid_race(client, db_session, auth_user):
    _, headers = auth_user
    body = {"name": "Bad", "character_class": "Fighter", "race": "Vulcan"}
    resp = await client.post("/api/v1/characters", headers=headers, json=body)
    assert resp.status_code == 422


async def test_create_character_missing_name(client, db_session, auth_user):
    _, headers = auth_user
    body = {"character_class": "Fighter", "race": "Human"}
    resp = await client.post("/api/v1/characters", headers=headers, json=body)
    assert resp.status_code == 422


async def test_create_character_missing_class(client, db_session, auth_user):
    _, headers = auth_user
    body = {"name": "NoClass", "race": "Human"}
    resp = await client.post("/api/v1/characters", headers=headers, json=body)
    assert resp.status_code == 422


async def test_create_character_missing_race(client, db_session, auth_user):
    _, headers = auth_user
    body = {"name": "NoRace", "character_class": "Fighter"}
    resp = await client.post("/api/v1/characters", headers=headers, json=body)
    assert resp.status_code == 422


async def test_create_character_no_auth(client, db_session):
    body = {"name": "Ghost", "character_class": "Rogue", "race": "Halfling"}
    resp = await client.post("/api/v1/characters", json=body)
    assert resp.status_code == 401


# ===========================================================================
# GET /api/v1/characters/{character_id}  (requires auth)
# ===========================================================================


async def test_get_character_happy_path(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user, name="Lookup")
    db_session.add(char)
    await db_session.flush()

    resp = await client.get(f"/api/v1/characters/{char.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(char.id)
    assert data["name"] == "Lookup"


async def test_get_character_not_found(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get(f"/api/v1/characters/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


async def test_get_character_no_auth(client, db_session):
    resp = await client.get(f"/api/v1/characters/{uuid.uuid4()}")
    assert resp.status_code == 401


# ===========================================================================
# GET /api/v1/characters  (requires auth)
# ===========================================================================


async def test_list_characters_empty(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get("/api/v1/characters", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["characters"] == []
    assert data["total"] == 0


async def test_list_characters_with_data(client, db_session, auth_user):
    user, headers = auth_user
    c1 = make_character(user=user, name="Alpha")
    c2 = make_character(user=user, name="Beta")
    db_session.add_all([c1, c2])
    await db_session.flush()

    resp = await client.get("/api/v1/characters", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["characters"]) == 2


async def test_list_characters_pagination_page1(client, db_session, auth_user):
    user, headers = auth_user
    chars = [make_character(user=user, name=f"Char{i}") for i in range(3)]
    db_session.add_all(chars)
    await db_session.flush()

    resp = await client.get("/api/v1/characters?page=1&page_size=2", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["characters"]) == 2
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2


async def test_list_characters_pagination_page2(client, db_session, auth_user):
    user, headers = auth_user
    chars = [make_character(user=user, name=f"Char{i}") for i in range(3)]
    db_session.add_all(chars)
    await db_session.flush()

    resp = await client.get("/api/v1/characters?page=2&page_size=2", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["characters"]) == 1
    assert data["total"] == 3
    assert data["page"] == 2


async def test_list_characters_no_auth(client, db_session):
    resp = await client.get("/api/v1/characters")
    assert resp.status_code == 401


# ===========================================================================
# PATCH /api/v1/characters/{character_id}  (NO auth!)
# ===========================================================================


async def test_update_character_name(client, db_session, auth_user):
    user, _ = auth_user
    char = make_character(user=user, name="OldName")
    db_session.add(char)
    await db_session.flush()

    resp = await client.patch(f"/api/v1/characters/{char.id}", json={"name": "NewName"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "NewName"


async def test_update_character_hp(client, db_session, auth_user):
    user, _ = auth_user
    char = make_character(user=user, hp_current=12, hp_max=12)
    db_session.add(char)
    await db_session.flush()

    resp = await client.patch(f"/api/v1/characters/{char.id}", json={"hp_current": 8})
    assert resp.status_code == 200
    assert resp.json()["hp_current"] == 8


async def test_update_character_personality_trait(client, db_session, auth_user):
    user, _ = auth_user
    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    resp = await client.patch(
        f"/api/v1/characters/{char.id}",
        json={"personality_trait": "Always cheerful"},
    )
    assert resp.status_code == 200
    assert resp.json()["personality_trait"] == "Always cheerful"


async def test_update_character_multiple_fields(client, db_session, auth_user):
    user, _ = auth_user
    char = make_character(user=user, name="Multi")
    db_session.add(char)
    await db_session.flush()

    resp = await client.patch(
        f"/api/v1/characters/{char.id}",
        json={"name": "Updated", "hp_current": 5, "motivation": "revenge"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated"
    assert data["hp_current"] == 5
    assert data["motivation"] == "revenge"


async def test_update_character_not_found(client, db_session):
    resp = await client.patch(f"/api/v1/characters/{uuid.uuid4()}", json={"name": "Ghost"})
    assert resp.status_code == 404


# ===========================================================================
# DELETE /api/v1/characters/{character_id}  (requires auth)
# ===========================================================================


async def test_delete_character_happy_path(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user, name="ToDelete")
    db_session.add(char)
    await db_session.flush()

    resp = await client.delete(f"/api/v1/characters/{char.id}", headers=headers)
    assert resp.status_code == 204


async def test_delete_character_not_found(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.delete(f"/api/v1/characters/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


async def test_delete_character_wrong_owner(client, db_session, auth_user):
    _, headers = auth_user
    other_user = make_user()
    db_session.add(other_user)
    await db_session.flush()

    char = make_character(user=other_user, name="NotMine")
    db_session.add(char)
    await db_session.flush()

    resp = await client.delete(f"/api/v1/characters/{char.id}", headers=headers)
    assert resp.status_code == 403


async def test_delete_character_no_auth(client, db_session):
    user = make_user()
    db_session.add(user)
    await db_session.flush()
    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    resp = await client.delete(f"/api/v1/characters/{char.id}")
    assert resp.status_code == 401


# ===========================================================================
# POST /api/v1/characters/{character_id}/skills  (requires auth)
# ===========================================================================


async def test_update_skills_happy_path(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user, name="Skilled")
    db_session.add(char)
    await db_session.flush()

    resp = await client.post(
        f"/api/v1/characters/{char.id}/skills",
        headers=headers,
        json=["athletics", "perception"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "athletics" in data["skill_proficiencies"]
    assert "perception" in data["skill_proficiencies"]


async def test_update_skills_not_found(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.post(
        f"/api/v1/characters/{uuid.uuid4()}/skills",
        headers=headers,
        json=["athletics"],
    )
    assert resp.status_code == 404


async def test_update_skills_no_auth(client, db_session):
    resp = await client.post(
        f"/api/v1/characters/{uuid.uuid4()}/skills",
        json=["athletics"],
    )
    assert resp.status_code == 401


# ===========================================================================
# GET /api/v1/characters/{character_id}/stats  (NO auth!)
# ===========================================================================


async def test_get_stats_happy_path(client, db_session, auth_user):
    user, _ = auth_user
    char = make_character(user=user, name="Statsy")
    db_session.add(char)
    await db_session.flush()

    resp = await client.get(f"/api/v1/characters/{char.id}/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "strength" in data
    assert "armor_class" in data
    assert "proficiency_bonus" in data
    assert "skills" in data
    assert "saving_throws" in data


async def test_get_stats_not_found(client, db_session):
    resp = await client.get(f"/api/v1/characters/{uuid.uuid4()}/stats")
    assert resp.status_code == 404
