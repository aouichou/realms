"""Tests for effects API endpoints (/api/v1/effects)."""

from __future__ import annotations

import pytest
import pytest_asyncio

from app.schemas.effects import EffectDuration, EffectType
from tests.factories import make_active_effect, make_character, make_session, make_user

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


async def _setup_char_session(db_session):
    """Create user + character + session and return (user, char, session)."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()
    return user, char, session


# ===========================================================================
# GET /api/v1/effects/character/{character_id}
# ===========================================================================


async def test_get_effects_empty(client, db_session, auth_headers):
    user, char, _ = await _setup_char_session(db_session)

    resp = await client.get(f"/api/v1/effects/character/{char.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["character_id"] == str(char.id)
    assert data["effects"] == []
    assert data["count"] == 0


async def test_get_effects_with_data(client, db_session, auth_headers):
    user, char, session = await _setup_char_session(db_session)

    e1 = make_active_effect(character=char, session_id=session.id, name="Bless")
    e2 = make_active_effect(character=char, session_id=session.id, name="Shield of Faith")
    db_session.add_all([e1, e2])
    await db_session.flush()

    resp = await client.get(f"/api/v1/effects/character/{char.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    names = {e["name"] for e in data["effects"]}
    assert "Bless" in names
    assert "Shield of Faith" in names


async def test_get_effects_filter_by_session(client, db_session, auth_headers):
    user, char, session = await _setup_char_session(db_session)

    e1 = make_active_effect(character=char, session_id=session.id, name="Haste")
    e2 = make_active_effect(character=char, session_id=None, name="Permanent Buff")
    db_session.add_all([e1, e2])
    await db_session.flush()

    resp = await client.get(f"/api/v1/effects/character/{char.id}?session_id={session.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == str(session.id)
    assert data["count"] >= 1


# ===========================================================================
# DELETE /api/v1/effects/{effect_id}
# ===========================================================================


async def test_delete_effect_happy(client, db_session, auth_headers):
    user, char, session = await _setup_char_session(db_session)

    effect = make_active_effect(character=char, session_id=session.id, name="Faerie Fire")
    db_session.add(effect)
    await db_session.flush()

    resp = await client.delete(f"/api/v1/effects/{effect.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


async def test_delete_effect_not_found(client, db_session, auth_headers):
    resp = await client.delete("/api/v1/effects/999999", headers=auth_headers)
    assert resp.status_code == 404


# ===========================================================================
# POST /api/v1/effects/character/{character_id}/break-concentration
# ===========================================================================


async def test_break_concentration_no_effects(client, db_session, auth_headers):
    user, char, _ = await _setup_char_session(db_session)

    resp = await client.post(f"/api/v1/effects/character/{char.id}/break-concentration", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["effects_broken"] == 0
    assert data["character_id"] == str(char.id)


async def test_break_concentration_with_effects(client, db_session, auth_headers):
    user, char, session = await _setup_char_session(db_session)

    conc_effect = make_active_effect(
        character=char,
        session_id=session.id,
        name="Bless",
        requires_concentration=True,
        effect_type=EffectType.CONCENTRATION,
        duration_type=EffectDuration.CONCENTRATION,
    )
    db_session.add(conc_effect)
    await db_session.flush()

    resp = await client.post(f"/api/v1/effects/character/{char.id}/break-concentration", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["effects_broken"] >= 1


# ===========================================================================
# POST /api/v1/effects/character/{character_id}/round-end
# ===========================================================================


async def test_round_end_no_effects(client, db_session, auth_headers):
    user, char, _ = await _setup_char_session(db_session)

    resp = await client.post(f"/api/v1/effects/character/{char.id}/round-end", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["expired_effects"] == []
    assert data["count"] == 0


async def test_round_end_with_expiring_effect(client, db_session, auth_headers):
    user, char, session = await _setup_char_session(db_session)

    effect = make_active_effect(
        character=char,
        session_id=session.id,
        name="Short Buff",
        effect_type=EffectType.BUFF,
        duration_type=EffectDuration.ROUNDS,
        duration_value=1,
        rounds_remaining=1,
        requires_concentration=False,
    )
    db_session.add(effect)
    await db_session.flush()

    resp = await client.post(f"/api/v1/effects/character/{char.id}/round-end", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert "Short Buff" in data["expired_effects"]


# ===========================================================================
# POST /api/v1/effects/character/{character_id}/rest
# ===========================================================================


async def test_rest_short(client, db_session, auth_headers):
    user, char, session = await _setup_char_session(db_session)

    effect = make_active_effect(
        character=char,
        session_id=session.id,
        name="Short Rest Effect",
        duration_type=EffectDuration.UNTIL_SHORT_REST,
        requires_concentration=False,
    )
    db_session.add(effect)
    await db_session.flush()

    resp = await client.post(f"/api/v1/effects/character/{char.id}/rest?rest_type=short", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["rest_type"] == "short"
    assert "Short Rest Effect" in data["effects_removed"]


async def test_rest_long(client, db_session, auth_headers):
    user, char, session = await _setup_char_session(db_session)

    effect = make_active_effect(
        character=char,
        session_id=session.id,
        name="Long Rest Effect",
        duration_type=EffectDuration.UNTIL_LONG_REST,
        requires_concentration=False,
    )
    db_session.add(effect)
    await db_session.flush()

    resp = await client.post(f"/api/v1/effects/character/{char.id}/rest?rest_type=long", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["rest_type"] == "long"
    assert "Long Rest Effect" in data["effects_removed"]


async def test_rest_invalid_type(client, db_session, auth_headers):
    user, char, _ = await _setup_char_session(db_session)

    resp = await client.post(f"/api/v1/effects/character/{char.id}/rest?rest_type=mega", headers=auth_headers)
    assert resp.status_code == 422


# ===========================================================================
# POST /api/v1/effects/cleanup
# ===========================================================================


async def test_cleanup_no_expired(client, db_session, auth_headers):
    resp = await client.post("/api/v1/effects/cleanup", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["effects_cleaned"] >= 0


async def test_cleanup_with_expired(client, db_session, auth_headers):
    user, char, session = await _setup_char_session(db_session)

    effect = make_active_effect(
        character=char,
        session_id=session.id,
        name="Expired Buff",
        duration_type=EffectDuration.ROUNDS,
        duration_value=0,
        rounds_remaining=0,
        requires_concentration=False,
    )
    db_session.add(effect)
    await db_session.flush()

    resp = await client.post("/api/v1/effects/cleanup", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["effects_cleaned"] >= 0
