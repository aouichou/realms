"""Tests for spell casting logic — /api/v1/spells.

Covers the big uncovered helper functions and the cast_spell endpoint:
- _roll_dice, _calculate_spell_damage, _consume_spell_slot
- _check_spell_preparation, _validate_ritual_cast, _validate_slot_level
- _handle_concentration
- cast_spell endpoint (cantrips, ritual, upcasting, no slots)
- long_rest endpoint
- concentration_check endpoint
- get_spell_slots endpoint
- prepare_spells endpoint
- add_spell_to_character duplicate check
- get_character_spells filters
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.db.models import CharacterClass
from tests.factories import (
    make_character,
    make_character_spell,
    make_spell,
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
    monkeypatch.setattr(session_service, "revoke_token", AsyncMock())
    monkeypatch.setattr(session_service, "is_token_revoked", AsyncMock(return_value=False))


BASE = "/api/v1/spells"


# ── helpers ────────────────────────────────────────────────────────────────


async def _setup_caster(db_session, cls=CharacterClass.WIZARD, level=5, slots=None):
    """Create a user, wizard character, spell, and character_spell."""
    user = make_user()
    if slots is None:
        slots = {"1": {"total": 4, "used": 0}, "2": {"total": 3, "used": 0}}
    char = make_character(
        user=user,
        character_class=cls,
        level=level,
        spell_slots=slots,
    )
    spell = make_spell(
        name="Magic Missile",
        level=1,
        damage_dice="3d4+3",
        is_concentration=False,
        is_ritual=False,
    )
    cs = make_character_spell(character=char, spell=spell, is_known=True, is_prepared=True)
    db_session.add_all([user, char, spell, cs])
    await db_session.flush()
    return user, char, spell, cs


# ===========================================================================
# Unit tests for helper functions (direct import, not HTTP)
# ===========================================================================


class TestRollDice:
    """Test the _roll_dice helper."""

    def test_simple_dice(self):
        from app.api.v1.endpoints.spells import _roll_dice

        result = _roll_dice("1d6")
        assert 1 <= result <= 6

    def test_multiple_dice(self):
        from app.api.v1.endpoints.spells import _roll_dice

        result = _roll_dice("3d6")
        assert 3 <= result <= 18

    def test_dice_with_positive_bonus(self):
        from app.api.v1.endpoints.spells import _roll_dice

        result = _roll_dice("1d4+2")
        assert 3 <= result <= 6

    def test_dice_with_negative_bonus(self):
        from app.api.v1.endpoints.spells import _roll_dice

        result = _roll_dice("1d8-1")
        assert 0 <= result <= 7

    def test_invalid_notation(self):
        from app.api.v1.endpoints.spells import _roll_dice

        result = _roll_dice("invalid")
        assert result == 0

    def test_plain_integer(self):
        from app.api.v1.endpoints.spells import _roll_dice

        result = _roll_dice("5")
        assert result == 5


class TestCalculateSpellDamage:
    """Test _calculate_spell_damage."""

    def test_no_damage_dice(self):
        from app.api.v1.endpoints.spells import _calculate_spell_damage

        spell = MagicMock(damage_dice=None)
        roll, total = _calculate_spell_damage(spell, 1)
        assert roll is None
        assert total is None

    def test_base_damage(self):
        from app.api.v1.endpoints.spells import _calculate_spell_damage

        spell = MagicMock(damage_dice="3d4+3", level=1, upcast_damage_dice=None)
        roll, total = _calculate_spell_damage(spell, 1)
        assert roll is not None
        assert total >= 6  # 3*1 + 3

    def test_upcast_with_plus_format(self):
        from app.api.v1.endpoints.spells import _calculate_spell_damage

        spell = MagicMock(damage_dice="1d10", level=1, upcast_damage_dice="+1d10")
        roll, total = _calculate_spell_damage(spell, 3)  # +2 levels
        assert total is not None
        assert total >= 3  # 1 + 1 + 1

    def test_upcast_without_plus(self):
        from app.api.v1.endpoints.spells import _calculate_spell_damage

        spell = MagicMock(damage_dice="1d6", level=1, upcast_damage_dice="1d6")
        roll, total = _calculate_spell_damage(spell, 2)  # +1 level
        assert total is not None


class TestConsumeSpellSlot:
    """Test _consume_spell_slot."""

    def test_consume_success(self):
        from app.api.v1.endpoints.spells import _consume_spell_slot

        char = MagicMock(spell_slots={"1": {"total": 2, "used": 0}})
        _consume_spell_slot(char, 1, False)
        assert char.spell_slots["1"]["used"] == 1

    def test_consume_ritual_no_slot_used(self):
        from app.api.v1.endpoints.spells import _consume_spell_slot

        char = MagicMock(spell_slots={"1": {"total": 2, "used": 0}})
        _consume_spell_slot(char, 1, True)
        assert char.spell_slots["1"]["used"] == 0

    def test_consume_no_slots_available(self):
        from fastapi import HTTPException

        from app.api.v1.endpoints.spells import _consume_spell_slot

        char = MagicMock(spell_slots={"1": {"total": 2, "used": 2}})
        with pytest.raises(HTTPException) as exc_info:
            _consume_spell_slot(char, 1, False)
        assert exc_info.value.status_code == 400

    def test_consume_no_slot_key(self):
        from fastapi import HTTPException

        from app.api.v1.endpoints.spells import _consume_spell_slot

        char = MagicMock(spell_slots={})
        with pytest.raises(HTTPException) as exc_info:
            _consume_spell_slot(char, 3, False)
        assert exc_info.value.status_code == 400


class TestCheckSpellPreparation:
    """Test _check_spell_preparation."""

    def test_prepared_caster_unprepared_spell(self):
        from fastapi import HTTPException

        from app.api.v1.endpoints.spells import _check_spell_preparation

        char = MagicMock(character_class=CharacterClass.WIZARD)
        cs = MagicMock(is_prepared=False)
        spell = MagicMock(level=1)
        with pytest.raises(HTTPException) as exc_info:
            _check_spell_preparation(char, cs, spell)
        assert exc_info.value.status_code == 400

    def test_prepared_caster_cantrip_passes(self):
        from app.api.v1.endpoints.spells import _check_spell_preparation

        char = MagicMock(character_class=CharacterClass.WIZARD)
        cs = MagicMock(is_prepared=False)
        spell = MagicMock(level=0)
        # Should not raise
        _check_spell_preparation(char, cs, spell)

    def test_non_prepared_caster_passes(self):
        from app.api.v1.endpoints.spells import _check_spell_preparation

        char = MagicMock(character_class=CharacterClass.SORCERER)
        cs = MagicMock(is_prepared=False)
        spell = MagicMock(level=2)
        # Sorcerer is not a prepared caster → should not raise
        _check_spell_preparation(char, cs, spell)


class TestValidateRitualCast:
    """Test _validate_ritual_cast."""

    def test_ritual_cast_non_ritual_spell(self):
        from fastapi import HTTPException

        from app.api.v1.endpoints.spells import _validate_ritual_cast

        request = MagicMock(is_ritual_cast=True)
        spell = MagicMock(is_ritual=False)
        with pytest.raises(HTTPException):
            _validate_ritual_cast(request, spell)

    def test_ritual_cast_ritual_spell(self):
        from app.api.v1.endpoints.spells import _validate_ritual_cast

        request = MagicMock(is_ritual_cast=True)
        spell = MagicMock(is_ritual=True)
        _validate_ritual_cast(request, spell)  # no raise


class TestValidateSlotLevel:
    """Test _validate_slot_level."""

    def test_slot_level_too_low(self):
        from fastapi import HTTPException

        from app.api.v1.endpoints.spells import _validate_slot_level

        request = MagicMock(slot_level=1)
        spell = MagicMock(level=3)
        with pytest.raises(HTTPException):
            _validate_slot_level(request, spell)

    def test_slot_level_none_defaults_to_spell_level(self):
        from app.api.v1.endpoints.spells import _validate_slot_level

        request = MagicMock(slot_level=None)
        spell = MagicMock(level=2)
        result = _validate_slot_level(request, spell)
        assert result == 2


class TestHandleConcentration:
    """Test _handle_concentration."""

    def test_concentration_spell_sets_active(self):
        from app.api.v1.endpoints.spells import _handle_concentration

        spell_id = uuid.uuid4()
        char = MagicMock(active_concentration_spell=None)
        spell = MagicMock(is_concentration=True, id=spell_id)
        _handle_concentration(char, spell)
        assert char.active_concentration_spell == spell_id

    def test_non_concentration_no_change(self):
        from app.api.v1.endpoints.spells import _handle_concentration

        char = MagicMock(active_concentration_spell=None)
        spell = MagicMock(is_concentration=False)
        _handle_concentration(char, spell)
        assert char.active_concentration_spell is None


# ===========================================================================
# get_spell_slots_for_class
# ===========================================================================


class TestGetSpellSlotsForClass:
    def test_full_caster(self):
        from app.api.v1.endpoints.spells import get_spell_slots_for_class

        slots = get_spell_slots_for_class(CharacterClass.WIZARD, 1)
        assert "1" in slots
        assert slots["1"]["total"] == 2

    def test_half_caster(self):
        from app.api.v1.endpoints.spells import get_spell_slots_for_class

        slots = get_spell_slots_for_class(CharacterClass.PALADIN, 2)
        assert "1" in slots

    def test_non_caster(self):
        from app.api.v1.endpoints.spells import get_spell_slots_for_class

        slots = get_spell_slots_for_class(CharacterClass.FIGHTER, 5)
        assert slots == {}

    def test_warlock(self):
        from app.api.v1.endpoints.spells import get_spell_slots_for_class

        slots = get_spell_slots_for_class(CharacterClass.WARLOCK, 1)
        # Warlock progression dict may be empty
        assert isinstance(slots, dict)


# ===========================================================================
# Endpoint tests — cast_spell
# ===========================================================================


async def test_cast_spell_basic(client, db_session, auth_headers):
    """Cast a level 1 spell using a level 1 slot."""
    _u, char, spell, _cs = await _setup_caster(db_session)

    with (
        patch(
            "app.api.v1.endpoints.spells.MemoryCaptureService.capture_spell_cast",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.spells.spell_creates_effect",
            return_value=False,
        ),
    ):
        resp = await client.post(
            f"{BASE}/character/{char.id}/cast",
            json={
                "spell_id": str(spell.id),
                "spell_level": 1,
            },
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["spell_name"] == "Magic Missile"
    assert data["slot_level_used"] == 1


async def test_cast_spell_upcast(client, db_session, auth_headers):
    """Cast a level 1 spell at level 2 slot (upcasting)."""
    _u, char, spell, _cs = await _setup_caster(db_session)

    with (
        patch(
            "app.api.v1.endpoints.spells.MemoryCaptureService.capture_spell_cast",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.spells.spell_creates_effect",
            return_value=False,
        ),
    ):
        resp = await client.post(
            f"{BASE}/character/{char.id}/cast",
            json={
                "spell_id": str(spell.id),
                "spell_level": 1,
                "slot_level": 2,
            },
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["slot_level_used"] == 2


async def test_cast_spell_cantrip(client, db_session, auth_headers):
    """Casting a cantrip (level 0) doesn't consume a slot."""
    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.WIZARD,
        level=1,
        spell_slots={"1": {"total": 2, "used": 0}},
    )
    cantrip = make_spell(name="Fire Bolt", level=0, damage_dice="1d10")
    cs = make_character_spell(character=char, spell=cantrip, is_known=True, is_prepared=True)
    db_session.add_all([user, char, cantrip, cs])
    await db_session.flush()

    resp = await client.post(
        f"{BASE}/character/{char.id}/cast",
        json={
            "spell_id": str(cantrip.id),
            "spell_level": 0,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["slot_level_used"] == 0


async def test_cast_spell_ritual(client, db_session, auth_headers):
    """Ritual casting doesn't consume a slot."""
    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.WIZARD,
        level=3,
        spell_slots={"1": {"total": 4, "used": 0}},
    )
    spell = make_spell(name="Detect Magic", level=1, is_ritual=True, damage_dice=None)
    cs = make_character_spell(character=char, spell=spell, is_known=True, is_prepared=True)
    db_session.add_all([user, char, spell, cs])
    await db_session.flush()

    with (
        patch(
            "app.api.v1.endpoints.spells.MemoryCaptureService.capture_spell_cast",
            new_callable=AsyncMock,
        ),
        patch(
            "app.api.v1.endpoints.spells.spell_creates_effect",
            return_value=False,
        ),
    ):
        resp = await client.post(
            f"{BASE}/character/{char.id}/cast",
            json={
                "spell_id": str(spell.id),
                "spell_level": 1,
                "is_ritual_cast": True,
            },
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["slot_level_used"] == 0  # Ritual = no slot consumed


async def test_cast_spell_character_not_found(client, db_session, auth_headers):
    """Casting with non-existent character returns 404."""
    resp = await client.post(
        f"{BASE}/character/{uuid.uuid4()}/cast",
        json={"spell_id": str(uuid.uuid4()), "spell_level": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_cast_spell_unknown_spell(client, db_session, auth_headers):
    """Casting a spell the character doesn't know returns 404."""
    user = make_user()
    char = make_character(user=user, character_class=CharacterClass.WIZARD, level=1)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(
        f"{BASE}/character/{char.id}/cast",
        json={"spell_id": str(uuid.uuid4()), "spell_level": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_cast_spell_not_ritual_fails(client, db_session, auth_headers):
    """Attempting ritual cast on non-ritual spell returns 400."""
    _u, char, spell, _cs = await _setup_caster(db_session)

    resp = await client.post(
        f"{BASE}/character/{char.id}/cast",
        json={
            "spell_id": str(spell.id),
            "spell_level": 1,
            "is_ritual_cast": True,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400


async def test_cast_spell_no_slots_remaining(client, db_session, auth_headers):
    """Casting when all slots used returns 400."""
    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.WIZARD,
        level=1,
        spell_slots={"1": {"total": 2, "used": 2}},
    )
    spell = make_spell(name="Shield", level=1)
    cs = make_character_spell(character=char, spell=spell, is_known=True, is_prepared=True)
    db_session.add_all([user, char, spell, cs])
    await db_session.flush()

    resp = await client.post(
        f"{BASE}/character/{char.id}/cast",
        json={"spell_id": str(spell.id), "spell_level": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 400


# ===========================================================================
# long_rest endpoint
# ===========================================================================


async def test_long_rest_restores_slots(client, db_session, auth_headers):
    """Long rest resets all used spell slots and HP."""
    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.WIZARD,
        level=3,
        hp_current=5,
        hp_max=20,
        spell_slots={"1": {"total": 4, "used": 3}, "2": {"total": 2, "used": 1}},
    )
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(f"{BASE}/character/{char.id}/rest", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["spell_slots"]["1"]["used"] == 0
    assert data["spell_slots"]["2"]["used"] == 0


async def test_long_rest_character_not_found(client, db_session, auth_headers):
    resp = await client.post(f"{BASE}/character/{uuid.uuid4()}/rest", headers=auth_headers)
    assert resp.status_code == 404


# ===========================================================================
# concentration_check endpoint
# ===========================================================================


async def test_concentration_check_not_concentrating(client, db_session, auth_headers):
    """Character not concentrating → success."""
    user = make_user()
    char = make_character(user=user, active_concentration_spell=None)
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(f"{BASE}/character/{char.id}/concentration-check?damage_taken=10", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


async def test_concentration_check_character_not_found(client, db_session, auth_headers):
    resp = await client.post(f"{BASE}/character/{uuid.uuid4()}/concentration-check?damage_taken=5", headers=auth_headers)
    assert resp.status_code == 404


async def test_concentration_check_with_active_spell(client, db_session, auth_headers):
    """Character concentrating on a spell — roll outcome."""
    user = make_user()
    spell_id = uuid.uuid4()
    char = make_character(
        user=user,
        active_concentration_spell=spell_id,
        constitution=10,
    )
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.post(f"{BASE}/character/{char.id}/concentration-check?damage_taken=5", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "roll" in data
    assert "dc" in data
    assert data["dc"] == 10  # max(10, 5//2=2) = 10


# ===========================================================================
# get_spell_slots endpoint
# ===========================================================================


async def test_get_spell_slots(client, db_session, auth_headers):
    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.WIZARD,
        level=1,
        spell_slots={"1": {"total": 2, "used": 0}},
    )
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.get(f"{BASE}/character/{char.id}/slots", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["character_id"] == str(char.id)


async def test_get_spell_slots_initializes_empty(client, db_session, auth_headers):
    """If spell_slots is empty, endpoint initializes them."""
    user = make_user()
    char = make_character(
        user=user,
        character_class=CharacterClass.WIZARD,
        level=1,
        spell_slots={},
    )
    db_session.add_all([user, char])
    await db_session.flush()

    resp = await client.get(f"{BASE}/character/{char.id}/slots", headers=auth_headers)
    assert resp.status_code == 200


async def test_get_spell_slots_not_found(client, db_session, auth_headers):
    resp = await client.get(f"{BASE}/character/{uuid.uuid4()}/slots", headers=auth_headers)
    assert resp.status_code == 404


# ===========================================================================
# prepare_spells endpoint
# ===========================================================================


async def test_prepare_spells(client, db_session, auth_headers):
    _u, char, spell, cs = await _setup_caster(db_session)

    resp = await client.post(
        f"{BASE}/character/{char.id}/prepare",
        json={"spell_ids": [str(spell.id)]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


async def test_prepare_spells_character_not_found(client, db_session, auth_headers):
    resp = await client.post(
        f"{BASE}/character/{uuid.uuid4()}/prepare",
        json={"spell_ids": [str(uuid.uuid4())]},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ===========================================================================
# add_spell_to_character duplicate
# ===========================================================================


async def test_add_spell_duplicate(client, db_session, auth_headers):
    """Adding the same spell twice returns 400."""
    _u, char, spell, _cs = await _setup_caster(db_session)

    resp = await client.post(
        f"{BASE}/character/{char.id}/spells",
        json={"spell_id": str(spell.id)},
        headers=auth_headers,
    )
    assert resp.status_code == 400


# ===========================================================================
# get_character_spells with filters
# ===========================================================================


async def test_get_character_spells_known_only(client, db_session, auth_headers):
    _u, char, spell, _cs = await _setup_caster(db_session)

    resp = await client.get(f"{BASE}/character/{char.id}/spells?known_only=true", headers=auth_headers)
    assert resp.status_code == 200


async def test_get_character_spells_prepared_only(client, db_session, auth_headers):
    _u, char, spell, _cs = await _setup_caster(db_session)

    resp = await client.get(f"{BASE}/character/{char.id}/spells?prepared_only=true", headers=auth_headers)
    assert resp.status_code == 200


async def test_get_character_spells_not_found(client, db_session, auth_headers):
    resp = await client.get(f"{BASE}/character/{uuid.uuid4()}/spells", headers=auth_headers)
    assert resp.status_code == 404
