"""Tests for adventure API endpoints (/api/v1/adventures)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from tests.factories import make_adventure, make_character, make_user

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
# GET /api/v1/adventures/list
# ===========================================================================


@pytest.mark.asyncio
async def test_list_adventures(client, db_session, auth_headers):
    with patch(
        "app.services.adventure_service.AdventureService.get_available_adventures",
        new_callable=AsyncMock,
        return_value=[
            {
                "id": "goblin_ambush",
                "title": "Goblin Ambush",
                "description": "Goblins attack!",
                "recommended_level": 1,
                "setting": "forest",
            }
        ],
    ):
        resp = await client.get("/api/v1/adventures/list", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["id"] == "goblin_ambush"


# ===========================================================================
# POST /api/v1/adventures/start-preset
# ===========================================================================


@pytest.mark.asyncio
async def test_start_preset_adventure(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    mock_result = {
        "session_id": str(uuid.uuid4()),
        "adventure_id": "goblin_ambush",
        "title": "Goblin Ambush",
        "opening_narration": "You walk into the forest...",
        "setting": "forest",
        "initial_location": "Forest Path",
    }
    with patch(
        "app.services.adventure_service.AdventureService.start_preset_adventure",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = await client.post(
            "/api/v1/adventures/start-preset",
            json={"character_id": str(char.id), "adventure_id": "goblin_ambush"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Goblin Ambush"


@pytest.mark.asyncio
async def test_start_preset_adventure_not_found(client, db_session, auth_headers):
    with patch(
        "app.services.adventure_service.AdventureService.start_preset_adventure",
        new_callable=AsyncMock,
        side_effect=ValueError("Adventure not found"),
    ):
        resp = await client.post(
            "/api/v1/adventures/start-preset",
            json={"character_id": str(uuid.uuid4()), "adventure_id": "nonexistent"},
            headers=auth_headers,
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_start_preset_adventure_server_error(client, db_session, auth_headers):
    with patch(
        "app.services.adventure_service.AdventureService.start_preset_adventure",
        new_callable=AsyncMock,
        side_effect=RuntimeError("DB error"),
    ):
        resp = await client.post(
            "/api/v1/adventures/start-preset",
            json={"character_id": str(uuid.uuid4()), "adventure_id": "test"},
            headers=auth_headers,
        )
    assert resp.status_code == 500


# ===========================================================================
# POST /api/v1/adventures/start-custom
# ===========================================================================


@pytest.mark.asyncio
async def test_start_custom_adventure(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    adventure = make_adventure(character=char)
    db_session.add_all([user, char, adventure])
    await db_session.flush()

    mock_result = {
        "session_id": str(uuid.uuid4()),
        "adventure_id": str(adventure.id),
        "title": adventure.title,
        "opening_narration": "The cursed keep awaits...",
        "setting": adventure.setting,
        "initial_location": "Castle Gate",
    }
    with patch(
        "app.services.adventure_service.AdventureService.start_custom_adventure",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = await client.post(
            "/api/v1/adventures/start-custom",
            json={"character_id": str(char.id), "adventure_id": str(adventure.id)},
            headers=auth_headers,
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_start_custom_adventure_not_found(client, db_session, auth_headers):
    with patch(
        "app.services.adventure_service.AdventureService.start_custom_adventure",
        new_callable=AsyncMock,
        side_effect=ValueError("Adventure not found"),
    ):
        resp = await client.post(
            "/api/v1/adventures/start-custom",
            json={"character_id": str(uuid.uuid4()), "adventure_id": str(uuid.uuid4())},
            headers=auth_headers,
        )
    assert resp.status_code == 404


# ===========================================================================
# GET /api/v1/adventures/{adventure_id}  (get_adventure_details)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_adventure_details(client, db_session, auth_headers):
    mock_adv = AsyncMock()
    mock_adv.id = "goblin_ambush"
    mock_adv.title = "Goblin Ambush"
    mock_adv.description = "test"
    mock_adv.recommended_level = 1
    mock_adv.setting = "forest"
    mock_adv.opening_narration = "You enter..."
    mock_adv.initial_location = "Forest"
    mock_adv.quest_data = {"objectives": ["Survive"], "rewards": {"xp": 100}}

    with patch(
        "app.services.adventure_service.AdventureService.load_adventure",
        new_callable=AsyncMock,
        return_value=mock_adv,
    ):
        resp = await client.get("/api/v1/adventures/goblin_ambush", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Goblin Ambush"


@pytest.mark.asyncio
async def test_get_adventure_details_not_found(client, db_session, auth_headers):
    with patch(
        "app.services.adventure_service.AdventureService.load_adventure",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await client.get("/api/v1/adventures/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


# ===========================================================================
# POST /api/v1/adventures/generate  (generate_custom_adventure)
# ===========================================================================


@pytest.mark.asyncio
async def test_generate_custom_adventure(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    db_session.add_all([user, char])
    await db_session.flush()

    mock_adv = make_adventure(character=char)
    with patch(
        "app.services.adventure_service.AdventureService.generate_custom_adventure",
        new_callable=AsyncMock,
        return_value=mock_adv,
    ):
        resp = await client.post(
            "/api/v1/adventures/generate",
            json={
                "character_id": str(char.id),
                "setting": "haunted_castle",
                "goal": "rescue_mission",
                "tone": "epic_heroic",
            },
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["setting"] == "haunted_castle"


@pytest.mark.asyncio
async def test_generate_custom_adventure_char_not_found(client, db_session, auth_headers):
    with patch(
        "app.services.adventure_service.AdventureService.generate_custom_adventure",
        new_callable=AsyncMock,
        side_effect=ValueError("Character not found"),
    ):
        resp = await client.post(
            "/api/v1/adventures/generate",
            json={
                "character_id": str(uuid.uuid4()),
                "setting": "forest",
                "goal": "explore",
                "tone": "dark",
            },
            headers=auth_headers,
        )
    assert resp.status_code == 404


# ===========================================================================
# GET /api/v1/adventures/custom/character/{character_id}
# ===========================================================================


@pytest.mark.asyncio
async def test_list_character_adventures(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    adv = make_adventure(character=char)
    db_session.add_all([user, char, adv])
    await db_session.flush()

    resp = await client.get(f"/api/v1/adventures/custom/character/{char.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_character_adventures_empty(client, db_session, auth_headers):
    resp = await client.get(f"/api/v1/adventures/custom/character/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


# ===========================================================================
# GET /api/v1/adventures/custom/{adventure_id}
# ===========================================================================


@pytest.mark.asyncio
async def test_get_custom_adventure(client, db_session, auth_headers):
    user = make_user()
    char = make_character(user=user)
    adv = make_adventure(character=char)
    db_session.add_all([user, char, adv])
    await db_session.flush()

    with patch(
        "app.services.adventure_service.AdventureService.get_adventure",
        new_callable=AsyncMock,
        return_value=adv,
    ):
        resp = await client.get(f"/api/v1/adventures/custom/{adv.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == adv.title


@pytest.mark.asyncio
async def test_get_custom_adventure_not_found(client, db_session, auth_headers):
    with patch(
        "app.services.adventure_service.AdventureService.get_adventure",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await client.get(f"/api/v1/adventures/custom/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
