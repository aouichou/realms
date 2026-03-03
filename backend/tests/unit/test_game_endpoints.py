"""Tests for game save/load API endpoints (/api/v1/game)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from tests.factories import make_character, make_session

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
# POST /api/v1/game/save
# ===========================================================================


@pytest.mark.asyncio
async def test_save_game(client, db_session, auth_user):
    user, headers = auth_user
    char = make_character(user=user)
    session = make_session(user=user, character=char)
    db_session.add_all([char, session])
    await db_session.flush()

    mock_save_data = {
        "session_id": str(session.id),
        "character_id": str(char.id),
        "save_name": "My Save",
        "saved_at": "2026-01-01T00:00:00Z",
    }
    with patch(
        "app.services.save_service.SaveService.save_game",
        new_callable=AsyncMock,
        return_value=mock_save_data,
    ):
        resp = await client.post(
            "/api/v1/game/save",
            json={"session_id": str(session.id), "save_name": "My Save"},
            headers=headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["save_data"]["save_name"] == "My Save"


@pytest.mark.asyncio
async def test_save_game_conflict(client, db_session, auth_user):
    user, headers = auth_user

    with patch(
        "app.services.save_service.SaveService.save_game",
        new_callable=AsyncMock,
        side_effect=ValueError("Save 'My Save' already exists"),
    ):
        resp = await client.post(
            "/api/v1/game/save",
            json={"session_id": str(uuid.uuid4()), "save_name": "My Save"},
            headers=headers,
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_save_game_no_auth(client, db_session):
    resp = await client.post(
        "/api/v1/game/save",
        json={"session_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


# ===========================================================================
# GET /api/v1/game/load/{session_id}
# ===========================================================================


@pytest.mark.asyncio
async def test_load_game_found(client, db_session, auth_user):
    user, headers = auth_user
    session_id = uuid.uuid4()

    mock_save = {"session_id": str(session_id), "character_id": str(uuid.uuid4())}
    with patch(
        "app.services.save_service.SaveService.load_game",
        new_callable=AsyncMock,
        return_value=mock_save,
    ):
        resp = await client.get(f"/api/v1/game/load/{session_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is True
    assert data["save_data"] is not None


@pytest.mark.asyncio
async def test_load_game_not_found(client, db_session, auth_user):
    user, headers = auth_user

    with patch(
        "app.services.save_service.SaveService.load_game",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await client.get(f"/api/v1/game/load/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False
    assert data["save_data"] is None


@pytest.mark.asyncio
async def test_load_game_no_auth(client, db_session):
    resp = await client.get(f"/api/v1/game/load/{uuid.uuid4()}")
    assert resp.status_code == 401


# ===========================================================================
# GET /api/v1/game/saves
# ===========================================================================


@pytest.mark.asyncio
async def test_list_saves(client, db_session, auth_user):
    user, headers = auth_user

    mock_saves = [
        {"session_id": str(uuid.uuid4()), "save_name": "Save 1"},
        {"session_id": str(uuid.uuid4()), "save_name": "Save 2"},
    ]
    with patch(
        "app.services.save_service.SaveService.list_saves",
        new_callable=AsyncMock,
        return_value=mock_saves,
    ):
        resp = await client.get("/api/v1/game/saves", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_saves_empty(client, db_session, auth_user):
    user, headers = auth_user

    with patch(
        "app.services.save_service.SaveService.list_saves",
        new_callable=AsyncMock,
        return_value=[],
    ):
        resp = await client.get("/api/v1/game/saves", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_saves_no_auth(client, db_session):
    resp = await client.get("/api/v1/game/saves")
    assert resp.status_code == 401


# ===========================================================================
# DELETE /api/v1/game/save/{session_id}
# ===========================================================================


@pytest.mark.asyncio
async def test_delete_save(client, db_session, auth_user):
    user, headers = auth_user

    with patch(
        "app.services.save_service.SaveService.delete_save",
        new_callable=AsyncMock,
        return_value=True,
    ):
        resp = await client.delete(f"/api/v1/game/save/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_delete_save_not_found(client, db_session, auth_user):
    user, headers = auth_user

    with patch(
        "app.services.save_service.SaveService.delete_save",
        new_callable=AsyncMock,
        return_value=False,
    ):
        resp = await client.delete(f"/api/v1/game/save/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_save_no_auth(client, db_session):
    resp = await client.delete(f"/api/v1/game/save/{uuid.uuid4()}")
    assert resp.status_code == 401
