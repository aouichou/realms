"""Tests for app.services.session_service.GameSessionService."""

from __future__ import annotations

import uuid

import pytest_asyncio

from app.schemas.session import SessionCreate
from app.services.session_service import GameSessionService
from tests.factories import make_character, make_session, make_user


@pytest_asyncio.fixture()
async def db(db_session):
    """Wrap db_session so commit() acts as flush(), preserving the test transaction."""
    original_commit = db_session.commit
    db_session.commit = db_session.flush
    yield db_session
    db_session.commit = original_commit


# ── helpers ────────────────────────────────────────────────────────────────


async def _setup_user_and_character(db):
    """Insert a User + Character and return them."""
    user = make_user()
    char = make_character(user=user)
    db.add_all([user, char])
    await db.flush()
    return user, char


# ── create_session ─────────────────────────────────────────────────────────


async def test_create_session_basic(db):
    user, char = await _setup_user_and_character(db)

    data = SessionCreate(character_id=char.id)
    session = await GameSessionService.create_session(db, user.id, data)

    assert session is not None
    assert session.user_id == user.id
    assert session.character_id == char.id
    assert session.is_active is True


async def test_create_session_deactivates_previous(db):
    """Creating a new session for the same character deactivates the old one."""
    user, char = await _setup_user_and_character(db)

    data = SessionCreate(character_id=char.id)
    first = await GameSessionService.create_session(db, user.id, data)
    assert first.is_active is True

    second = await GameSessionService.create_session(db, user.id, data)
    assert second.is_active is True

    # Re-fetch the first session — it should now be inactive
    refreshed = await GameSessionService.get_session(db, first.id)
    assert refreshed is not None
    assert refreshed.is_active is False


async def test_create_session_with_location(db):
    user, char = await _setup_user_and_character(db)

    data = SessionCreate(character_id=char.id, current_location="Tavern")
    session = await GameSessionService.create_session(db, user.id, data)
    assert session.current_location == "Tavern"


# ── get_session ────────────────────────────────────────────────────────────


async def test_get_session_by_id(db):
    user, char = await _setup_user_and_character(db)

    data = SessionCreate(character_id=char.id)
    created = await GameSessionService.create_session(db, user.id, data)

    fetched = await GameSessionService.get_session(db, created.id)
    assert fetched is not None
    assert fetched.id == created.id


async def test_get_session_nonexistent_returns_none(db):
    result = await GameSessionService.get_session(db, uuid.uuid4())
    assert result is None


# ── get_user_sessions ─────────────────────────────────────────────────────


async def test_get_user_sessions_all(db):
    user, char = await _setup_user_and_character(db)

    s1 = make_session(user=user, character=char, is_active=True)
    s2 = make_session(user=user, character=char, is_active=False)
    db.add_all([s1, s2])
    await db.flush()

    sessions, total = await GameSessionService.get_user_sessions(db, user.id)
    assert total == 2
    assert len(sessions) == 2


async def test_get_user_sessions_active_only(db):
    user, char = await _setup_user_and_character(db)

    s1 = make_session(user=user, character=char, is_active=True)
    s2 = make_session(user=user, character=char, is_active=False)
    db.add_all([s1, s2])
    await db.flush()

    sessions, total = await GameSessionService.get_user_sessions(db, user.id, active_only=True)
    assert total == 1
    assert len(sessions) == 1
    assert sessions[0].is_active is True


# ── get_active_session ─────────────────────────────────────────────────────


async def test_get_active_session(db):
    user, char = await _setup_user_and_character(db)

    s = make_session(user=user, character=char, is_active=True)
    db.add(s)
    await db.flush()

    result = await GameSessionService.get_active_session(db, user.id)
    assert result is not None
    assert result.id == s.id


async def test_get_active_session_none_when_all_inactive(db):
    user, char = await _setup_user_and_character(db)

    s = make_session(user=user, character=char, is_active=False)
    db.add(s)
    await db.flush()

    result = await GameSessionService.get_active_session(db, user.id)
    assert result is None


# ── get_active_session_for_character ───────────────────────────────────────


async def test_get_active_session_for_character(db):
    user, char = await _setup_user_and_character(db)

    s = make_session(user=user, character=char, is_active=True)
    db.add(s)
    await db.flush()

    result = await GameSessionService.get_active_session_for_character(db, char.id)
    assert result is not None
    assert result.character_id == char.id


async def test_get_active_session_for_character_none(db):
    result = await GameSessionService.get_active_session_for_character(db, uuid.uuid4())
    assert result is None


# ── end_session ────────────────────────────────────────────────────────────


async def test_end_session(db):
    user, char = await _setup_user_and_character(db)

    data = SessionCreate(character_id=char.id)
    created = await GameSessionService.create_session(db, user.id, data)
    assert created.is_active is True

    ended = await GameSessionService.end_session(db, created.id)
    assert ended is not None
    assert ended.is_active is False


async def test_end_session_nonexistent_returns_none(db):
    result = await GameSessionService.end_session(db, uuid.uuid4())
    assert result is None


# ── delete_session ─────────────────────────────────────────────────────────


async def test_delete_session(db):
    user, char = await _setup_user_and_character(db)

    data = SessionCreate(character_id=char.id)
    created = await GameSessionService.create_session(db, user.id, data)

    deleted = await GameSessionService.delete_session(db, created.id)
    assert deleted is True

    # Verify it's gone
    fetched = await GameSessionService.get_session(db, created.id)
    assert fetched is None


async def test_delete_session_nonexistent_returns_false(db):
    result = await GameSessionService.delete_session(db, uuid.uuid4())
    assert result is False
