"""Tests for spells API endpoints (/api/v1/spells)."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from tests.factories import (
    make_character,
    make_character_spell,
    make_spell,
    make_user,
)

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
# GET /api/v1/spells  (list_spells)
# ===========================================================================


@pytest.mark.asyncio
async def test_list_spells_empty(client, db_session, auth_headers):
    resp = await client.get("/api/v1/spells", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "spells" in data
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_spells_with_data(client, db_session, auth_headers):
    sp = make_spell(name="Fireball", level=3)
    db_session.add(sp)
    await db_session.flush()

    resp = await client.get("/api/v1/spells", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_spells_filter_level(client, db_session, auth_headers):
    sp1 = make_spell(name="Magic Missile", level=1)
    sp2 = make_spell(name="Fireball", level=3)
    db_session.add_all([sp1, sp2])
    await db_session.flush()

    resp = await client.get("/api/v1/spells", params={"level": 1}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    names = [s["name"] for s in data["spells"]]
    assert "Magic Missile" in names
    assert "Fireball" not in names


@pytest.mark.asyncio
async def test_list_spells_filter_concentration(client, db_session, auth_headers):
    sp = make_spell(name="Haste", level=3, is_concentration=True)
    db_session.add(sp)
    await db_session.flush()

    resp = await client.get("/api/v1/spells", params={"concentration": True}, headers=auth_headers)
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()["spells"]]
    assert "Haste" in names


@pytest.mark.asyncio
async def test_list_spells_search(client, db_session, auth_headers):
    sp = make_spell(name="Lightning Bolt", level=3, description="A bolt of lightning")
    db_session.add(sp)
    await db_session.flush()

    resp = await client.get("/api/v1/spells", params={"search": "Lightning"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


# ===========================================================================
# GET /api/v1/spells/{spell_id}
# ===========================================================================


@pytest.mark.asyncio
async def test_get_spell(client, db_session, auth_headers):
    sp = make_spell(name="Shield")
    db_session.add(sp)
    await db_session.flush()

    resp = await client.get(f"/api/v1/spells/{sp.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Shield"


@pytest.mark.asyncio
async def test_get_spell_not_found(client, db_session, auth_headers):
    resp = await client.get(f"/api/v1/spells/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ===========================================================================
# POST /api/v1/spells  (create_spell)
# ===========================================================================


@pytest.mark.asyncio
async def test_create_spell(client, db_session, auth_headers):
    body = {
        "name": "Ice Storm",
        "level": 4,
        "school": "Evocation",
        "casting_time": "1 action",
        "range": "300 feet",
        "duration": "Instantaneous",
        "description": "Bludgeoning and cold damage rain down.",
        "verbal": True,
        "somatic": True,
    }
    resp = await client.post("/api/v1/spells", json=body, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Ice Storm"
    assert data["level"] == 4


# ===========================================================================
# GET /api/v1/spells/character/{character_id}/spells  (get_character_spells)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_character_spells(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    sp = make_spell(name="Cure Wounds")
    db_session.add_all([user, char, sp])
    await db_session.flush()

    cs = make_character_spell(character=char, spell=sp, is_known=True)
    db_session.add(cs)
    await db_session.flush()

    resp = await client.get(f"/api/v1/spells/character/{char.id}/spells", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_character_spells_not_found(client, db_session, auth_headers):
    resp = await client.get(f"/api/v1/spells/character/{uuid.uuid4()}/spells", headers=auth_headers)
    assert resp.status_code == 404


# ===========================================================================
# POST /api/v1/spells/character/{character_id}/spells  (add_spell_to_character)
# ===========================================================================


@pytest.mark.asyncio
async def test_add_spell_to_character(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    sp = make_spell(name="Detect Magic")
    db_session.add_all([user, char, sp])
    await db_session.flush()

    body = {"spell_id": str(sp.id), "is_known": True, "is_prepared": False}
    resp = await client.post(f"/api/v1/spells/character/{char.id}/spells", json=body, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["spell_id"] == str(sp.id)


@pytest.mark.asyncio
async def test_add_spell_to_character_char_not_found(client, db_session, auth_headers):
    body = {"spell_id": str(uuid.uuid4()), "is_known": True}
    resp = await client.post(f"/api/v1/spells/character/{uuid.uuid4()}/spells", json=body, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_spell_to_character_spell_not_found(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    body = {"spell_id": str(uuid.uuid4()), "is_known": True}
    resp = await client.post(f"/api/v1/spells/character/{char.id}/spells", json=body, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_spell_duplicate(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    sp = make_spell(name="Bless")
    db_session.add_all([user, char, sp])
    await db_session.flush()

    cs = make_character_spell(character=char, spell=sp)
    db_session.add(cs)
    await db_session.flush()

    body = {"spell_id": str(sp.id), "is_known": True}
    resp = await client.post(f"/api/v1/spells/character/{char.id}/spells", json=body, headers=auth_headers)
    assert resp.status_code == 400
    assert "already has" in resp.json()["detail"]


# ===========================================================================
# POST /api/v1/spells/character/{character_id}/prepare
# ===========================================================================


@pytest.mark.asyncio
async def test_prepare_spells(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    sp = make_spell(name="Healing Word")
    db_session.add_all([user, char, sp])
    await db_session.flush()

    cs = make_character_spell(character=char, spell=sp, is_known=True)
    db_session.add(cs)
    await db_session.flush()

    body = {"spell_ids": [str(sp.id)]}
    resp = await client.post(f"/api/v1/spells/character/{char.id}/prepare", json=body, headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_prepare_spells_char_not_found(client, db_session, auth_headers):
    body = {"spell_ids": [str(uuid.uuid4())]}
    resp = await client.post(f"/api/v1/spells/character/{uuid.uuid4()}/prepare", json=body, headers=auth_headers)
    assert resp.status_code == 404


# ===========================================================================
# GET /api/v1/spells/character/{character_id}/slots
# ===========================================================================


@pytest.mark.asyncio
async def test_get_spell_slots(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user, character_class="Wizard", level=3)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.get(f"/api/v1/spells/character/{char.id}/slots", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["character_id"] == str(char.id)
    assert "spell_slots" in data


@pytest.mark.asyncio
async def test_get_spell_slots_not_found(client, db_session, auth_headers):
    resp = await client.get(f"/api/v1/spells/character/{uuid.uuid4()}/slots", headers=auth_headers)
    assert resp.status_code == 404


# ===========================================================================
# POST /api/v1/spells/character/{character_id}/cast
# ===========================================================================


@pytest.mark.asyncio
async def test_cast_cantrip(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user, character_class="Wizard", level=1)
    cantrip = make_spell(name="Fire Bolt", level=0, damage_dice="1d10", damage_type="fire")
    db_session.add_all([user, char, cantrip])
    await db_session.flush()

    cs = make_character_spell(character=char, spell=cantrip, is_known=True)
    db_session.add(cs)
    await db_session.flush()

    body = {"spell_id": str(cantrip.id), "spell_level": 0}
    resp = await client.post(f"/api/v1/spells/character/{char.id}/cast", json=body, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["slot_level_used"] == 0
    assert data["spell_name"] == "Fire Bolt"


@pytest.mark.asyncio
async def test_cast_spell_no_slots(client, db_session, auth_headers):
    user = make_user()
    char = make_character(
        user=user,
        character_class="Fighter",
        level=1,
        spell_slots={},
    )
    sp = make_spell(name="Cure Wounds LVL", level=1)
    db_session.add_all([user, char, sp])
    await db_session.flush()

    cs = make_character_spell(character=char, spell=sp, is_known=True, is_prepared=True)
    db_session.add(cs)
    await db_session.flush()

    body = {"spell_id": str(sp.id), "spell_level": 1}
    resp = await client.post(f"/api/v1/spells/character/{char.id}/cast", json=body, headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_cast_spell_char_not_found(client, db_session, auth_headers):
    body = {"spell_id": str(uuid.uuid4()), "spell_level": 1}
    resp = await client.post(f"/api/v1/spells/character/{uuid.uuid4()}/cast", json=body, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cast_spell_not_known(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user, character_class="Wizard", level=1)
    db_session.add_all([user, char])
    await db_session.flush()

    body = {"spell_id": str(uuid.uuid4()), "spell_level": 1}
    resp = await client.post(f"/api/v1/spells/character/{char.id}/cast", json=body, headers=auth_headers)
    assert resp.status_code == 404
    assert "doesn't know" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_cast_ritual_non_ritual_spell(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user, character_class="Wizard", level=1)
    sp = make_spell(name="Magic Missile R", level=1, is_ritual=False)
    db_session.add_all([user, char, sp])
    await db_session.flush()

    cs = make_character_spell(character=char, spell=sp, is_known=True, is_prepared=True)
    db_session.add(cs)
    await db_session.flush()

    body = {"spell_id": str(sp.id), "spell_level": 1, "is_ritual_cast": True}
    resp = await client.post(f"/api/v1/spells/character/{char.id}/cast", json=body, headers=auth_headers)
    assert resp.status_code == 400
    assert "ritual" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cast_spell_slot_too_low(client, db_session, auth_headers):
    user = make_user()
    char = make_character(
        user=user,
        character_class="Wizard",
        level=5,
        spell_slots={
            "1": {"total": 4, "used": 0},
            "2": {"total": 3, "used": 0},
            "3": {"total": 2, "used": 0},
        },
    )
    sp = make_spell(name="Fireball SL", level=3)
    db_session.add_all([user, char, sp])
    await db_session.flush()

    cs = make_character_spell(character=char, spell=sp, is_known=True, is_prepared=True)
    db_session.add(cs)
    await db_session.flush()

    body = {"spell_id": str(sp.id), "spell_level": 3, "slot_level": 1}
    resp = await client.post(f"/api/v1/spells/character/{char.id}/cast", json=body, headers=auth_headers)
    assert resp.status_code == 400
    assert "Cannot cast" in resp.json()["detail"]


# ===========================================================================
# POST /api/v1/spells/character/{character_id}/rest (long_rest)
# ===========================================================================


@pytest.mark.asyncio
async def test_long_rest(client, db_session, auth_headers):
    user = make_user()
    char = make_character(
        user=user,
        character_class="Wizard",
        level=3,
        hp_current=5,
        hp_max=12,
        spell_slots={"1": {"total": 4, "used": 3}, "2": {"total": 2, "used": 2}},
    )
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(f"/api/v1/spells/character/{char.id}/rest", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    # All slots should be restored
    for lvl, slots in data["spell_slots"].items():
        assert slots["used"] == 0


@pytest.mark.asyncio
async def test_long_rest_not_found(client, db_session, auth_headers):
    resp = await client.post(f"/api/v1/spells/character/{uuid.uuid4()}/rest", headers=auth_headers)
    assert resp.status_code == 404


# ===========================================================================
# POST /api/v1/spells/character/{character_id}/concentration-check
# ===========================================================================


@pytest.mark.asyncio
async def test_concentration_check_no_concentration(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user, active_concentration_spell=None)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        f"/api/v1/spells/character/{char.id}/concentration-check",
        params={"damage_taken": 10},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "not concentrating" in data["message"]


@pytest.mark.asyncio
async def test_concentration_check_with_concentration(client, db_session, auth_headers):
    user = make_user()
    sp = make_spell(name="Haste CC", level=3, is_concentration=True)
    char = make_character(user=user, constitution=16, active_concentration_spell=sp.id)
    db_session.add_all([user, char, sp])
    await db_session.flush()

    resp = await client.post(
        f"/api/v1/spells/character/{char.id}/concentration-check",
        params={"damage_taken": 10},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "dc" in data
    assert data["dc"] == 10  # max(10, 10//2) = 10


@pytest.mark.asyncio
async def test_concentration_check_not_found(client, db_session, auth_headers):
    resp = await client.post(
        f"/api/v1/spells/character/{uuid.uuid4()}/concentration-check",
        params={"damage_taken": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 404
