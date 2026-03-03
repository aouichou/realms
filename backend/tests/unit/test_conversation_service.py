"""Tests for app.services.conversation_service.ConversationService."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest_asyncio

from app.schemas.message import MessageCreate
from app.services.conversation_service import ConversationService
from tests.factories import make_character, make_message, make_session, make_user


@pytest_asyncio.fixture()
async def db(db_session):
    """Wrap db_session so commit() acts as flush(), preserving the test transaction."""
    original_commit = db_session.commit
    db_session.commit = db_session.flush
    yield db_session
    db_session.commit = original_commit


# ── helpers ────────────────────────────────────────────────────────────────


async def _setup_session(db):
    """Create User → Character → GameSession in the DB and return them."""
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db.add_all([user, char, session])
    await db.flush()
    return user, char, session


# ── create_message ─────────────────────────────────────────────────────────


async def test_create_message(db):
    user, char, session = await _setup_session(db)

    data = MessageCreate(
        session_id=session.id,
        role="user",
        content="I open the door.",
        tokens_used=12,
    )
    msg = await ConversationService.create_message(db, data)

    assert msg is not None
    assert msg.session_id == session.id
    assert msg.role == "user"
    assert msg.content == "I open the door."
    assert msg.tokens_used == 12


async def test_create_message_without_tokens(db):
    user, char, session = await _setup_session(db)

    data = MessageCreate(
        session_id=session.id,
        role="assistant",
        content="You see a dark corridor.",
    )
    msg = await ConversationService.create_message(db, data)

    assert msg is not None
    assert msg.tokens_used is None


# ── get_session_messages ───────────────────────────────────────────────────


async def test_get_session_messages_empty(db):
    user, char, session = await _setup_session(db)

    messages, total = await ConversationService.get_session_messages(db, session.id)
    assert messages == []
    assert total == 0


async def test_get_session_messages_returns_chronological(db):
    """Messages are returned oldest-first (chronological)."""
    user, char, session = await _setup_session(db)

    now = datetime.now(timezone.utc)
    m1 = make_message(session=session, content="First", created_at=now - timedelta(seconds=2))
    m2 = make_message(session=session, content="Second", created_at=now - timedelta(seconds=1))
    m3 = make_message(session=session, content="Third", created_at=now)
    db.add_all([m1, m2, m3])
    await db.flush()

    messages, total = await ConversationService.get_session_messages(db, session.id)
    assert total == 3
    assert len(messages) == 3
    assert messages[0].content == "First"
    assert messages[1].content == "Second"
    assert messages[2].content == "Third"


async def test_get_session_messages_pagination(db):
    """Limit and offset reduce the result set."""
    user, char, session = await _setup_session(db)

    now = datetime.now(timezone.utc)
    for i in range(5):
        m = make_message(
            session=session,
            content=f"Msg {i}",
            created_at=now + timedelta(seconds=i),
        )
        db.add(m)
    await db.flush()

    messages, total = await ConversationService.get_session_messages(
        db, session.id, limit=2, offset=0
    )
    assert total == 5
    assert len(messages) == 2


async def test_get_session_messages_different_sessions(db):
    """Messages from other sessions are not returned."""
    user, char, session = await _setup_session(db)
    other_session = make_session(user=user, character=char)
    db.add(other_session)
    await db.flush()

    m1 = make_message(session=session, content="Mine")
    m2 = make_message(session=other_session, content="Other")
    db.add_all([m1, m2])
    await db.flush()

    messages, total = await ConversationService.get_session_messages(db, session.id)
    assert total == 1
    assert messages[0].content == "Mine"


# ── get_recent_messages ────────────────────────────────────────────────────


async def test_get_recent_messages(db):
    """count=3 returns the 3 most recent messages in chronological order."""
    user, char, session = await _setup_session(db)

    now = datetime.now(timezone.utc)
    for i in range(5):
        m = make_message(
            session=session,
            content=f"Msg {i}",
            created_at=now + timedelta(seconds=i),
        )
        db.add(m)
    await db.flush()

    recent = await ConversationService.get_recent_messages(db, session.id, count=3)
    assert len(recent) == 3
    # Should be chronological: Msg 2, Msg 3, Msg 4
    assert recent[0].content == "Msg 2"
    assert recent[1].content == "Msg 3"
    assert recent[2].content == "Msg 4"


async def test_get_recent_messages_fewer_than_count(db):
    """If fewer messages exist than count, return all of them."""
    user, char, session = await _setup_session(db)

    m = make_message(session=session, content="Only one")
    db.add(m)
    await db.flush()

    recent = await ConversationService.get_recent_messages(db, session.id, count=10)
    assert len(recent) == 1


# ── get_total_tokens ───────────────────────────────────────────────────────


async def test_get_total_tokens(db):
    """Sum of tokens_used across messages."""
    user, char, session = await _setup_session(db)

    m1 = make_message(session=session, tokens_used=10)
    m2 = make_message(session=session, tokens_used=20)
    m3 = make_message(session=session, tokens_used=30)
    db.add_all([m1, m2, m3])
    await db.flush()

    total = await ConversationService.get_total_tokens(db, session.id)
    assert total == 60


async def test_get_total_tokens_empty_session(db):
    user, char, session = await _setup_session(db)

    total = await ConversationService.get_total_tokens(db, session.id)
    assert total == 0


async def test_get_total_tokens_with_nulls(db):
    """Messages with tokens_used=None are ignored in the sum."""
    user, char, session = await _setup_session(db)

    m1 = make_message(session=session, tokens_used=10)
    m2 = make_message(session=session, tokens_used=None)
    db.add_all([m1, m2])
    await db.flush()

    total = await ConversationService.get_total_tokens(db, session.id)
    assert total == 10


# ── delete_session_messages ────────────────────────────────────────────────


async def test_delete_session_messages(db):
    """Deletes all messages and returns the count."""
    user, char, session = await _setup_session(db)

    for _ in range(3):
        db.add(make_message(session=session))
    await db.flush()

    deleted_count = await ConversationService.delete_session_messages(db, session.id)
    assert deleted_count == 3

    # Verify they're gone
    remaining, total = await ConversationService.get_session_messages(db, session.id)
    assert total == 0
    assert remaining == []


async def test_delete_session_messages_empty(db):
    user, char, session = await _setup_session(db)

    deleted_count = await ConversationService.delete_session_messages(db, session.id)
    assert deleted_count == 0
