"""Tests for app.services.effects_service.EffectsService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest_asyncio

from app.schemas.effects import ActiveEffect, EffectDuration, EffectType
from tests.factories import make_active_effect, make_character, make_user

# Mock OpenTelemetry tracing before importing EffectsService
mock_tracer = MagicMock()
mock_span = MagicMock()
mock_span.__enter__ = MagicMock(return_value=mock_span)
mock_span.__exit__ = MagicMock(return_value=False)
mock_tracer.start_as_current_span.return_value = mock_span

with patch("app.services.effects_service.get_tracer", return_value=mock_tracer):
    with patch("app.services.effects_service.trace_async", lambda name: lambda f: f):
        from app.services.effects_service import EffectsService


@pytest_asyncio.fixture()
async def db(db_session):
    """Wrap db_session so commit() acts as flush(), preserving the test transaction."""
    original_commit = db_session.commit
    db_session.commit = db_session.flush
    yield db_session
    db_session.commit = original_commit


# ── helpers ────────────────────────────────────────────────────────────────


async def _setup_character(db):
    """Insert User + Character and return them."""
    user = make_user()
    char = make_character(user=user)
    db.add_all([user, char])
    await db.flush()
    return user, char


# ── apply_effect ───────────────────────────────────────────────────────────


async def test_apply_basic_buff(db):
    user, char = await _setup_character(db)

    effect = await EffectsService.apply_effect(
        db,
        character_id=char.id,
        name="Shield of Faith",
        effect_type=EffectType.BUFF,
        duration_type=EffectDuration.ROUNDS,
        duration_value=10,
        bonus_value=2,
    )

    assert isinstance(effect, ActiveEffect)
    assert effect.name == "Shield of Faith"
    assert effect.effect_type == EffectType.BUFF
    assert effect.is_active is True
    assert effect.rounds_remaining == 10
    assert effect.bonus_value == 2


async def test_apply_concentration_breaks_previous(db):
    """Applying a concentration effect breaks any existing concentration."""
    user, char = await _setup_character(db)

    first = await EffectsService.apply_effect(
        db,
        character_id=char.id,
        name="Bless",
        effect_type=EffectType.CONCENTRATION,
        duration_type=EffectDuration.CONCENTRATION,
        requires_concentration=True,
    )
    assert first.is_active is True

    second = await EffectsService.apply_effect(
        db,
        character_id=char.id,
        name="Haste",
        effect_type=EffectType.CONCENTRATION,
        duration_type=EffectDuration.CONCENTRATION,
        requires_concentration=True,
    )
    assert second.is_active is True

    # Re-fetch first — concentration should be broken
    await db.refresh(first)
    assert first.is_active is False


async def test_apply_non_stacking_refreshes_existing(db):
    """Re-applying a non-stacking effect refreshes duration instead of creating a new one."""
    user, char = await _setup_character(db)

    first = await EffectsService.apply_effect(
        db,
        character_id=char.id,
        name="Bless",
        effect_type=EffectType.BUFF,
        duration_type=EffectDuration.ROUNDS,
        duration_value=5,
        stacks=False,
    )
    first_id = first.id

    # Apply again with longer duration
    refreshed = await EffectsService.apply_effect(
        db,
        character_id=char.id,
        name="Bless",
        effect_type=EffectType.BUFF,
        duration_type=EffectDuration.ROUNDS,
        duration_value=10,
        stacks=False,
    )

    # Same row, updated duration
    assert refreshed.id == first_id
    assert refreshed.rounds_remaining == 10


async def test_apply_stacking_creates_new(db):
    """Stacking effects create separate instances."""
    user, char = await _setup_character(db)

    first = await EffectsService.apply_effect(
        db,
        character_id=char.id,
        name="Bardic Inspiration",
        effect_type=EffectType.INSPIRATION,
        duration_type=EffectDuration.ROUNDS,
        duration_value=5,
        stacks=True,
    )

    second = await EffectsService.apply_effect(
        db,
        character_id=char.id,
        name="Bardic Inspiration",
        effect_type=EffectType.INSPIRATION,
        duration_type=EffectDuration.ROUNDS,
        duration_value=5,
        stacks=True,
    )

    assert first.id != second.id


# ── get_active_effects ─────────────────────────────────────────────────────


async def test_get_active_effects(db):
    user, char = await _setup_character(db)

    e1 = make_active_effect(character=char, name="Bless", is_active=True)
    e2 = make_active_effect(character=char, name="Shield", is_active=True)
    e3 = make_active_effect(character=char, name="Expired", is_active=False)
    db.add_all([e1, e2, e3])
    await db.flush()

    effects = await EffectsService.get_active_effects(db, char.id)
    names = {e.name for e in effects}
    assert "Bless" in names
    assert "Shield" in names
    assert "Expired" not in names


async def test_get_active_effects_empty(db):
    user, char = await _setup_character(db)

    effects = await EffectsService.get_active_effects(db, char.id)
    assert effects == []


# ── remove_effect ──────────────────────────────────────────────────────────


async def test_remove_effect(db):
    user, char = await _setup_character(db)

    effect = make_active_effect(character=char, name="RemoveMe")
    db.add(effect)
    await db.flush()

    result = await EffectsService.remove_effect(db, effect.id)
    assert result is True

    # Verify deactivated
    await db.refresh(effect)
    assert effect.is_active is False


async def test_remove_effect_nonexistent(db):
    result = await EffectsService.remove_effect(db, 999999)
    assert result is False


# ── break_concentration ────────────────────────────────────────────────────


async def test_break_concentration(db):
    user, char = await _setup_character(db)

    c1 = make_active_effect(
        character=char, name="Bless", requires_concentration=True, is_active=True
    )
    c2 = make_active_effect(
        character=char, name="Haste", requires_concentration=True, is_active=True
    )
    non_conc = make_active_effect(
        character=char, name="Shield", requires_concentration=False, is_active=True
    )
    db.add_all([c1, c2, non_conc])
    await db.flush()

    count = await EffectsService.break_concentration(db, char.id)
    assert count == 2

    await db.refresh(c1)
    await db.refresh(c2)
    await db.refresh(non_conc)
    assert c1.is_active is False
    assert c2.is_active is False
    assert non_conc.is_active is True  # Non-concentration unaffected


async def test_break_concentration_none_active(db):
    user, char = await _setup_character(db)

    count = await EffectsService.break_concentration(db, char.id)
    assert count == 0


# ── process_round_end ──────────────────────────────────────────────────────


async def test_process_round_end_decrements(db):
    """Round-based effects have rounds_remaining decremented by 1."""
    user, char = await _setup_character(db)

    effect = make_active_effect(
        character=char,
        name="Bless",
        duration_type=EffectDuration.ROUNDS,
        rounds_remaining=5,
        is_active=True,
    )
    db.add(effect)
    await db.flush()

    expired = await EffectsService.process_round_end(db, char.id)
    assert expired == []

    await db.refresh(effect)
    assert effect.rounds_remaining == 4
    assert effect.is_active is True


async def test_process_round_end_expires_at_zero(db):
    """Effect with rounds_remaining=1 expires after processing."""
    user, char = await _setup_character(db)

    effect = make_active_effect(
        character=char,
        name="Shield",
        duration_type=EffectDuration.ROUNDS,
        rounds_remaining=1,
        is_active=True,
    )
    db.add(effect)
    await db.flush()

    expired = await EffectsService.process_round_end(db, char.id)
    assert "Shield" in expired

    await db.refresh(effect)
    assert effect.is_active is False
    assert effect.rounds_remaining == 0


# ── process_rest ───────────────────────────────────────────────────────────


async def test_process_rest_short_rest(db):
    """Short rest removes only UNTIL_SHORT_REST effects."""
    user, char = await _setup_character(db)

    short = make_active_effect(
        character=char,
        name="Second Wind",
        duration_type=EffectDuration.UNTIL_SHORT_REST,
        is_active=True,
    )
    long_only = make_active_effect(
        character=char,
        name="Rage",
        duration_type=EffectDuration.UNTIL_LONG_REST,
        is_active=True,
    )
    db.add_all([short, long_only])
    await db.flush()

    removed = await EffectsService.process_rest(db, char.id, is_long_rest=False)
    assert "Second Wind" in removed
    assert "Rage" not in removed

    await db.refresh(short)
    await db.refresh(long_only)
    assert short.is_active is False
    assert long_only.is_active is True


async def test_process_rest_long_rest(db):
    """Long rest removes everything except PERMANENT effects."""
    user, char = await _setup_character(db)

    temp = make_active_effect(
        character=char,
        name="Rage",
        duration_type=EffectDuration.UNTIL_LONG_REST,
        is_active=True,
    )
    perm = make_active_effect(
        character=char,
        name="Darkvision",
        duration_type=EffectDuration.PERMANENT,
        is_active=True,
    )
    short_eff = make_active_effect(
        character=char,
        name="Inspiration",
        duration_type=EffectDuration.UNTIL_SHORT_REST,
        is_active=True,
    )
    db.add_all([temp, perm, short_eff])
    await db.flush()

    removed = await EffectsService.process_rest(db, char.id, is_long_rest=True)
    assert "Rage" in removed
    assert "Inspiration" in removed
    assert "Darkvision" not in removed

    await db.refresh(perm)
    assert perm.is_active is True
