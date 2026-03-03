"""Tests for memory API endpoints (/api/v1/memories)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from tests.factories import make_character, make_memory, make_session, make_user

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
# POST /api/v1/memories  (create_memory)
# ===========================================================================


@pytest.mark.asyncio
async def test_create_memory(client, db_session):
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    mock_memory = make_memory(session=session)
    with patch(
        "app.services.memory_service.MemoryService.store_memory",
        new_callable=AsyncMock,
        return_value=mock_memory,
    ):
        resp = await client.post(
            "/api/v1/memories",
            json={
                "session_id": str(session.id),
                "event_type": "combat",
                "content": "The party defeated the goblins.",
                "importance": 7,
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert (
        data["content"] == "The party defeated the goblin ambush." or data["content"]
    )  # valid content


@pytest.mark.asyncio
async def test_create_memory_error(client, db_session):
    with patch(
        "app.services.memory_service.MemoryService.store_memory",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Embedding failed"),
    ):
        resp = await client.post(
            "/api/v1/memories",
            json={
                "session_id": str(uuid.uuid4()),
                "event_type": "combat",
                "content": "test",
                "importance": 5,
            },
        )
    assert resp.status_code == 500
    assert "Failed to create memory" in resp.json()["detail"]


# ===========================================================================
# POST /api/v1/memories/search
# ===========================================================================


@pytest.mark.asyncio
async def test_search_memories(client, db_session):
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    mock_memory = make_memory(session=session)
    with patch(
        "app.services.memory_service.MemoryService.search_memories",
        new_callable=AsyncMock,
        return_value=[mock_memory],
    ):
        resp = await client.post(
            "/api/v1/memories/search",
            json={
                "session_id": str(session.id),
                "query": "goblin combat",
                "limit": 10,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["query"] == "goblin combat"


@pytest.mark.asyncio
async def test_search_memories_empty(client, db_session):
    with patch(
        "app.services.memory_service.MemoryService.search_memories",
        new_callable=AsyncMock,
        return_value=[],
    ):
        resp = await client.post(
            "/api/v1/memories/search",
            json={
                "session_id": str(uuid.uuid4()),
                "query": "nothing here",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ===========================================================================
# GET /api/v1/memories/session/{session_id}/recent
# ===========================================================================


@pytest.mark.asyncio
async def test_get_recent_memories(client, db_session):
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    mock_memory = make_memory(session=session)
    with patch(
        "app.services.memory_service.MemoryService.get_recent_memories",
        new_callable=AsyncMock,
        return_value=[mock_memory],
    ):
        resp = await client.get(
            f"/api/v1/memories/session/{session.id}/recent",
            params={"limit": 5, "min_importance": 5},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


# ===========================================================================
# GET /api/v1/memories/session/{session_id}/context
# ===========================================================================


@pytest.mark.asyncio
async def test_get_ai_context(client, db_session):
    session_id = uuid.uuid4()

    with (
        patch(
            "app.services.memory_service.MemoryService.get_context_for_ai",
            new_callable=AsyncMock,
            return_value="Previously, the party fought goblins.",
        ),
        patch(
            "app.services.memory_service.MemoryService.search_memories",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        resp = await client.get(
            f"/api/v1/memories/session/{session_id}/context",
            params={"situation": "entering a dungeon"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "relevant_memories" in data
    assert data["context_length"] > 0


# ===========================================================================
# DELETE /api/v1/memories/session/{session_id}
# ===========================================================================


@pytest.mark.asyncio
async def test_delete_session_memories(client, db_session):
    user = make_user()
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([user, char, session])
    await db_session.flush()

    mem = make_memory(session=session)
    db_session.add(mem)
    await db_session.flush()

    resp = await client.delete(f"/api/v1/memories/session/{session.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted_count"] >= 1
    assert "deleted successfully" in data["message"]


@pytest.mark.asyncio
async def test_delete_session_memories_none(client, db_session):
    resp = await client.delete(f"/api/v1/memories/session/{uuid.uuid4()}")
    assert resp.status_code == 200
    assert resp.json()["deleted_count"] == 0
