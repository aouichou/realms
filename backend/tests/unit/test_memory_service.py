"""Tests for MemoryService — memory_service.py

SQLite cannot handle ARRAY / Vector columns used by AdventureMemory, so
tests that persist memories use ``make_memory`` from the factory
(which omits those columns) or mock the DB entirely.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.db.models import AdventureMemory, EventType
from app.services.memory_service import MemoryService
from tests.factories import make_character, make_memory, make_session, make_user

SESSION_ID = uuid.uuid4()


def _patch_embedding():
    mock_svc = MagicMock()
    mock_svc.generate_embedding = AsyncMock(return_value=[0.1] * 1024)
    return patch("app.services.memory_service.get_embedding_service", return_value=mock_svc)


def _patch_embedding_none():
    mock_svc = MagicMock()
    mock_svc.generate_embedding = AsyncMock(return_value=None)
    return patch("app.services.memory_service.get_embedding_service", return_value=mock_svc)


# ---------------------------------------------------------------------------
# store_memory — mock db (SQLite can't handle ARRAY columns)
# ---------------------------------------------------------------------------


class TestStoreMemory:
    async def test_stores_memory(self):
        db = AsyncMock()
        db.refresh = AsyncMock()
        with _patch_embedding():
            await MemoryService.store_memory(
                db=db,
                session_id=SESSION_ID,
                event_type="combat",
                content="Fought a dragon",
                importance=7,
                tags=["boss"],
                npcs_involved=["Dragon"],
                locations=["Mountain"],
                items_involved=["Sword"],
            )
            db.add.assert_called_once()
            db.commit.assert_awaited_once()
            added = db.add.call_args[0][0]
            assert isinstance(added, AdventureMemory)
            assert added.content == "Fought a dragon"
            assert added.importance == 7
            assert added.tags == ["boss"]

    async def test_defaults_empty_lists(self):
        db = AsyncMock()
        db.refresh = AsyncMock()
        with _patch_embedding():
            await MemoryService.store_memory(
                db=db,
                session_id=SESSION_ID,
                event_type="dialogue",
                content="Hello",
            )
            added = db.add.call_args[0][0]
            assert added.tags == []
            assert added.npcs_involved == []
            assert added.locations == []
            assert added.items_involved == []

    async def test_none_embedding_stored(self):
        db = AsyncMock()
        db.refresh = AsyncMock()
        with _patch_embedding_none():
            await MemoryService.store_memory(
                db=db,
                session_id=SESSION_ID,
                event_type="combat",
                content="Test",
            )
            added = db.add.call_args[0][0]
            assert added.embedding is None


# ---------------------------------------------------------------------------
# _text_search_fallback — use db_session + make_memory factory
# ---------------------------------------------------------------------------


def _setup_session(db_session):
    """Helper to create user → character → game session chain."""
    user = make_user()
    char = make_character(user=user)
    sess = make_session(user=user, character=char)
    return user, char, sess


class TestTextSearchFallback:
    async def test_fallback_returns_matching(self, db_session):
        user, char, sess = _setup_session(db_session)
        db_session.add_all([user, char, sess])
        await db_session.flush()

        m1 = make_memory(session=sess, content="Fire dragon attacked the village", importance=8)
        m2 = make_memory(session=sess, content="Chatted with innkeeper", importance=3)
        db_session.add_all([m1, m2])
        await db_session.flush()

        results = await MemoryService._text_search_fallback(
            db=db_session,
            session_id=sess.id,
            query="dragon",
            limit=10,
            min_importance=None,
            event_types=None,
            tags=None,
        )
        assert len(results) >= 1
        assert any("dragon" in m.content.lower() for m in results)

    async def test_fallback_min_importance_filter(self, db_session):
        user, char, sess = _setup_session(db_session)
        db_session.add_all([user, char, sess])
        await db_session.flush()

        db_session.add(make_memory(session=sess, content="A thing happened", importance=2))
        await db_session.flush()

        results = await MemoryService._text_search_fallback(
            db=db_session,
            session_id=sess.id,
            query="thing",
            limit=10,
            min_importance=5,
            event_types=None,
            tags=None,
        )
        assert len(results) == 0

    async def test_fallback_event_type_filter(self, db_session):
        user, char, sess = _setup_session(db_session)
        db_session.add_all([user, char, sess])
        await db_session.flush()

        m1 = make_memory(
            session=sess, content="Fought a goblin", importance=6, event_type=EventType.COMBAT
        )
        m2 = make_memory(
            session=sess, content="Fought in words", importance=6, event_type=EventType.DIALOGUE
        )
        db_session.add_all([m1, m2])
        await db_session.flush()

        results = await MemoryService._text_search_fallback(
            db=db_session,
            session_id=sess.id,
            query="Fought",
            limit=10,
            min_importance=None,
            event_types=["combat"],
            tags=None,
        )
        assert all(r.event_type.value == "combat" for r in results)


# ---------------------------------------------------------------------------
# get_recent_memories
# ---------------------------------------------------------------------------


class TestGetRecentMemories:
    async def test_returns_recent(self, db_session):
        user, char, sess = _setup_session(db_session)
        db_session.add_all([user, char, sess])
        await db_session.flush()

        for i in range(5):
            db_session.add(make_memory(session=sess, content=f"Event {i}", importance=7))
        await db_session.flush()

        memories = await MemoryService.get_recent_memories(
            db=db_session, session_id=sess.id, limit=3, min_importance=5
        )
        assert len(memories) <= 3
        if len(memories) >= 2:
            assert memories[0].timestamp >= memories[1].timestamp

    async def test_filtered_by_importance(self, db_session):
        user, char, sess = _setup_session(db_session)
        db_session.add_all([user, char, sess])
        await db_session.flush()

        db_session.add(make_memory(session=sess, content="Low importance", importance=1))
        await db_session.flush()

        memories = await MemoryService.get_recent_memories(
            db=db_session, session_id=sess.id, limit=10, min_importance=5
        )
        assert all(m.importance >= 5 for m in memories)


# ---------------------------------------------------------------------------
# search_memories — falls back to text search when embedding is None
# ---------------------------------------------------------------------------


class TestSearchMemories:
    async def test_falls_back_on_no_embedding(self, db_session):
        user, char, sess = _setup_session(db_session)
        db_session.add_all([user, char, sess])
        await db_session.flush()

        db_session.add(make_memory(session=sess, content="Dragon fight", importance=8))
        await db_session.flush()

        with _patch_embedding_none():
            results = await MemoryService.search_memories(
                db=db_session,
                session_id=sess.id,
                query="Dragon",
                limit=5,
            )
            assert len(results) >= 1


# ---------------------------------------------------------------------------
# get_context_for_ai
# ---------------------------------------------------------------------------


class TestGetContextForAI:
    async def test_no_memories_returns_default(self, db_session):
        with _patch_embedding_none():
            result = await MemoryService.get_context_for_ai(
                db=db_session,
                session_id=uuid.uuid4(),
                current_situation="What happened?",
            )
            assert "No relevant" in result

    async def test_formats_memories(self, db_session):
        user, char, sess = _setup_session(db_session)
        db_session.add_all([user, char, sess])
        await db_session.flush()

        db_session.add(make_memory(session=sess, content="Battle at the bridge", importance=8))
        await db_session.flush()

        with _patch_embedding_none():
            result = await MemoryService.get_context_for_ai(
                db=db_session,
                session_id=sess.id,
                current_situation="Battle at the bridge",
                max_memories=5,
            )
            assert "Battle at the bridge" in result


# ---------------------------------------------------------------------------
# calculate_importance
# ---------------------------------------------------------------------------


class TestCalculateImportance:
    async def test_base_combat(self):
        score = await MemoryService.calculate_importance("combat", "Simple fight")
        assert score == 7

    async def test_dialogue(self):
        score = await MemoryService.calculate_importance("dialogue", "Hello there")
        assert score == 4

    async def test_modifiers_stack(self):
        score = await MemoryService.calculate_importance(
            "combat",
            "death of the legendary ancient artifact boss",
            is_combat_outcome=True,
            is_major_decision=True,
            involves_boss=True,
        )
        assert score == 10

    async def test_unknown_event_type(self):
        score = await MemoryService.calculate_importance("unknown_type", "nothing")
        assert score == 5

    async def test_clamped_to_min(self):
        score = await MemoryService.calculate_importance("other", "plain text")
        assert 1 <= score <= 10
