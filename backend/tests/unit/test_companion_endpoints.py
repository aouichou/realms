"""Tests for companion API endpoints (/api/v1/companions).

NOTE: Several companion endpoints declare path parameters as ``int``
(character_id, companion_id) even though the underlying DB model uses
UUID primary keys.  Those endpoints will always return 404 since an int
can never match a UUID column.  We test the 404/422/401 error paths for
them and full happy-path tests for the endpoints that accept UUID
(chat via request body, conversations via UUID path param).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from tests.factories import (
    make_character,
    make_companion,
    make_companion_conversation,
    make_creature,
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
# Helpers
# ===========================================================================


async def _seed(db_session, auth_user):
    """Create character, creature, and companion owned by auth_user."""
    user, headers = auth_user
    creature = make_creature()
    db_session.add(creature)
    await db_session.flush()

    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    companion = make_companion(character=char, creature=creature)
    db_session.add(companion)
    await db_session.flush()

    return char, creature, companion, headers


# ===========================================================================
# GET /api/v1/companions/characters/{character_id}/companions
# (path param is UUID)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_character_companions_rejects_uuid(client, db_session, auth_user):
    """UUID path param now accepted; non-existent character returns 404."""
    _, headers = auth_user
    resp = await client.get(
        f"/api/v1/companions/characters/{uuid.uuid4()}/companions",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_character_companions_not_found(client, db_session, auth_user):
    """Invalid non-UUID string returns 422."""
    _, headers = auth_user
    resp = await client.get(
        "/api/v1/companions/characters/not-a-uuid/companions",
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_character_companions_no_auth(client, db_session):
    resp = await client.get("/api/v1/companions/characters/1/companions")
    assert resp.status_code == 401


# ===========================================================================
# GET /api/v1/companions/characters/{character_id}/companions/active
# ===========================================================================


@pytest.mark.asyncio
async def test_get_active_companions_rejects_uuid(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get(
        f"/api/v1/companions/characters/{uuid.uuid4()}/companions/active",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_active_companions_not_found(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get(
        "/api/v1/companions/characters/not-a-uuid/companions/active",
        headers=headers,
    )
    assert resp.status_code == 422


# ===========================================================================
# GET /api/v1/companions/companions/{companion_id}
# ===========================================================================


@pytest.mark.asyncio
async def test_get_companion_rejects_uuid(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get(
        f"/api/v1/companions/companions/{uuid.uuid4()}",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_companion_not_found(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get(
        "/api/v1/companions/companions/not-a-uuid",
        headers=headers,
    )
    assert resp.status_code == 422


# ===========================================================================
# PATCH /api/v1/companions/companions/{companion_id}/loyalty
# ===========================================================================


@pytest.mark.asyncio
async def test_update_loyalty_rejects_uuid(client, db_session, auth_user):
    _, headers = auth_user
    with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
        mock_ps.get_current_provider.return_value = MagicMock()
        resp = await client.patch(
            f"/api/v1/companions/companions/{uuid.uuid4()}/loyalty",
            params={"loyalty_change": 5, "event_description": "test"},
            headers=headers,
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_loyalty_not_found(client, db_session, auth_user):
    _, headers = auth_user
    with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
        mock_ps.get_current_provider.return_value = MagicMock()
        resp = await client.patch(
            "/api/v1/companions/companions/not-a-uuid/loyalty",
            params={"loyalty_change": 5, "event_description": "test"},
            headers=headers,
        )
    assert resp.status_code == 422


# ===========================================================================
# PATCH /api/v1/companions/companions/{companion_id}/active
# ===========================================================================


@pytest.mark.asyncio
async def test_toggle_companion_active_rejects_uuid(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.patch(
        f"/api/v1/companions/companions/{uuid.uuid4()}/active",
        params={"is_active": True},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_toggle_companion_active_not_found(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.patch(
        "/api/v1/companions/companions/not-a-uuid/active",
        params={"is_active": True},
        headers=headers,
    )
    assert resp.status_code == 422


# ===========================================================================
# POST /api/v1/companions/companions/chat  (companion_id from body as UUID)
# ===========================================================================


@pytest.mark.asyncio
async def test_chat_with_companion(client, db_session, auth_user):
    char, _, companion, headers = await _seed(db_session, auth_user)

    with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
        mock_provider = MagicMock()
        mock_ps.get_current_provider.return_value = mock_provider
        with patch(
            "app.services.companion_service.CompanionService.generate_companion_response",
            new_callable=AsyncMock,
            return_value="I am ready to help!",
        ):
            resp = await client.post(
                "/api/v1/companions/companions/chat",
                json={
                    "companion_id": str(companion.id),
                    "message": "Hello companion!",
                    "share_with_dm": False,
                },
                headers=headers,
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["companion_response"] == "I am ready to help!"


@pytest.mark.asyncio
async def test_chat_share_with_dm(client, db_session, auth_user):
    char, _, companion, headers = await _seed(db_session, auth_user)

    with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
        mock_ps.get_current_provider.return_value = MagicMock()
        with patch(
            "app.services.companion_service.CompanionService.generate_companion_response",
            new_callable=AsyncMock,
            return_value="Shared response!",
        ):
            resp = await client.post(
                "/api/v1/companions/companions/chat",
                json={
                    "companion_id": str(companion.id),
                    "message": "Let's talk",
                    "share_with_dm": True,
                },
                headers=headers,
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["companion_response"] == "Shared response!"


@pytest.mark.asyncio
async def test_chat_companion_not_found(client, db_session, auth_user):
    _, headers = auth_user

    with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
        mock_ps.get_current_provider.return_value = MagicMock()
        resp = await client.post(
            "/api/v1/companions/companions/chat",
            json={
                "companion_id": str(uuid.uuid4()),
                "message": "Hello?",
                "share_with_dm": False,
            },
            headers=headers,
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_chat_no_ai_provider(client, db_session, auth_user):
    char, _, companion, headers = await _seed(db_session, auth_user)

    with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
        mock_ps.get_current_provider.return_value = None
        resp = await client.post(
            "/api/v1/companions/companions/chat",
            json={
                "companion_id": str(companion.id),
                "message": "Hello?",
                "share_with_dm": False,
            },
            headers=headers,
        )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_chat_ai_error(client, db_session, auth_user):
    char, _, companion, headers = await _seed(db_session, auth_user)

    with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
        mock_ps.get_current_provider.return_value = MagicMock()
        with patch(
            "app.services.companion_service.CompanionService.generate_companion_response",
            new_callable=AsyncMock,
            side_effect=RuntimeError("AI model error"),
        ):
            resp = await client.post(
                "/api/v1/companions/companions/chat",
                json={
                    "companion_id": str(companion.id),
                    "message": "Hello?",
                    "share_with_dm": False,
                },
                headers=headers,
            )
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_chat_no_auth(client, db_session):
    resp = await client.post(
        "/api/v1/companions/companions/chat",
        json={
            "companion_id": str(uuid.uuid4()),
            "message": "Hello?",
            "share_with_dm": False,
        },
    )
    assert resp.status_code == 401


# ===========================================================================
# GET /api/v1/companions/companions/{id}/conversations  (UUID path param)
# ===========================================================================


@pytest.mark.asyncio
async def test_get_companion_conversations(client, db_session, auth_user):
    char, _, companion, headers = await _seed(db_session, auth_user)

    conv = make_companion_conversation(companion=companion, character=char, shared_with_dm=True)
    db_session.add(conv)
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/companions/companions/{companion.id}/conversations",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_conversations_shared_only(client, db_session, auth_user):
    char, _, companion, headers = await _seed(db_session, auth_user)

    shared = make_companion_conversation(
        companion=companion, character=char, shared_with_dm=True, message="shared msg"
    )
    private = make_companion_conversation(
        companion=companion, character=char, shared_with_dm=False, message="private msg"
    )
    db_session.add_all([shared, private])
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/companions/companions/{companion.id}/conversations",
        params={"shared_only": True},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    for msg in data:
        assert msg["shared_with_dm"] is True


@pytest.mark.asyncio
async def test_get_conversations_not_found(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get(
        f"/api/v1/companions/companions/{uuid.uuid4()}/conversations",
        headers=headers,
    )
    assert resp.status_code == 404
