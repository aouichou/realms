"""Tests for companion API endpoints (/api/v1/companions).

Covers all endpoints in ``app/api/v1/endpoints/companions.py``:

- GET  /characters/{character_id}/companions
- GET  /characters/{character_id}/companions/active
- GET  /companions/{companion_id}
- PATCH /companions/{companion_id}/loyalty
- PATCH /companions/{companion_id}/active
- POST  /companions/chat
- GET  /companions/{companion_id}/conversations
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


@pytest.mark.asyncio
async def test_get_character_companions_happy_path(client, db_session, auth_user):
    """Happy path: return companions for a character owned by the user."""
    char, creature, companion, headers = await _seed(db_session, auth_user)

    resp = await client.get(
        f"/api/v1/companions/characters/{char.id}/companions",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    names = [c["name"] for c in data]
    assert companion.name in names


@pytest.mark.asyncio
async def test_get_character_companions_empty(client, db_session, auth_user):
    """Character exists but has no companions — returns empty list."""
    user, headers = auth_user
    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/companions/characters/{char.id}/companions",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_character_companions_wrong_user(client, db_session, auth_user):
    """Cannot access companions of a character belonging to another user."""
    _, headers = auth_user
    # Character owned by a different user
    other_char = make_character()
    db_session.add(other_char)
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/companions/characters/{other_char.id}/companions",
        headers=headers,
    )
    assert resp.status_code == 404


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


@pytest.mark.asyncio
async def test_get_active_companions_happy_path(client, db_session, auth_user):
    """Only active and alive companions are returned."""
    user, headers = auth_user
    creature = make_creature()
    db_session.add(creature)
    await db_session.flush()

    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    # Active and alive
    active_comp = make_companion(
        character=char,
        creature=creature,
        name="Active Companion",
        is_active=True,
        is_alive=True,
    )
    # Inactive
    inactive_comp = make_companion(
        character=char,
        creature=creature,
        name="Inactive Companion",
        is_active=False,
        is_alive=True,
    )
    # Dead
    dead_comp = make_companion(
        character=char,
        creature=creature,
        name="Dead Companion",
        is_active=True,
        is_alive=False,
    )
    db_session.add_all([active_comp, inactive_comp, dead_comp])
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/companions/characters/{char.id}/companions/active",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    names = [c["name"] for c in data]
    assert "Active Companion" in names
    assert "Inactive Companion" not in names
    assert "Dead Companion" not in names


@pytest.mark.asyncio
async def test_get_active_companions_none_active(client, db_session, auth_user):
    """No active companions — returns empty list."""
    user, headers = auth_user
    creature = make_creature()
    db_session.add(creature)
    await db_session.flush()

    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    inactive = make_companion(character=char, creature=creature, is_active=False, is_alive=True)
    db_session.add(inactive)
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/companions/characters/{char.id}/companions/active",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


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


@pytest.mark.asyncio
async def test_get_companion_happy_path(client, db_session, auth_user):
    """Get a specific companion by ID — basic fields."""
    char, creature, companion, headers = await _seed(db_session, auth_user)

    resp = await client.get(
        f"/api/v1/companions/companions/{companion.id}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == companion.name
    assert data["loyalty"] == companion.loyalty
    assert data["hp"] == companion.hp


@pytest.mark.asyncio
async def test_get_companion_with_memory_and_events(client, db_session, auth_user):
    """Companion with conversation_memory and important_events includes them."""
    user, headers = auth_user
    creature = make_creature()
    db_session.add(creature)
    await db_session.flush()

    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    memory = [{"role": "player", "content": "Hello!", "timestamp": "2026-01-01T00:00:00Z"}]
    events = [{"event": "Met in the forest", "timestamp": "2026-01-01T00:00:00Z"}]

    companion = make_companion(
        character=char,
        creature=creature,
        conversation_memory=memory,
        important_events=events,
    )
    db_session.add(companion)
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/companions/companions/{companion.id}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "conversation_memory" in data
    assert data["conversation_memory"] == memory
    assert "important_events" in data
    assert data["important_events"] == events


@pytest.mark.asyncio
async def test_get_companion_wrong_user(client, db_session, auth_user):
    """Cannot get a companion belonging to another user's character."""
    _, headers = auth_user
    creature = make_creature()
    db_session.add(creature)
    await db_session.flush()

    other_char = make_character()  # different user
    db_session.add(other_char)
    await db_session.flush()

    companion = make_companion(character=other_char, creature=creature)
    db_session.add(companion)
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/companions/companions/{companion.id}",
        headers=headers,
    )
    assert resp.status_code == 404


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


@pytest.mark.asyncio
async def test_update_loyalty_happy_path(client, db_session, auth_user):
    """Successfully update companion loyalty."""
    char, creature, companion, headers = await _seed(db_session, auth_user)

    with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
        mock_provider = MagicMock()
        mock_ps.get_current_provider.return_value = mock_provider
        with patch("app.api.v1.endpoints.companions.CompanionService") as mock_service_cls:
            mock_service_instance = MagicMock()
            mock_service_instance.update_companion_loyalty = AsyncMock()
            mock_service_cls.return_value = mock_service_instance

            resp = await client.patch(
                f"/api/v1/companions/companions/{companion.id}/loyalty",
                params={"loyalty_change": 10, "event_description": "Saved a villager"},
                headers=headers,
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == companion.name


@pytest.mark.asyncio
async def test_update_loyalty_no_ai_provider(client, db_session, auth_user):
    """503 when no AI provider is available."""
    char, creature, companion, headers = await _seed(db_session, auth_user)

    with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
        mock_ps.get_current_provider.return_value = None
        resp = await client.patch(
            f"/api/v1/companions/companions/{companion.id}/loyalty",
            params={"loyalty_change": 5, "event_description": "test event"},
            headers=headers,
        )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_update_loyalty_wrong_user(client, db_session, auth_user):
    """Cannot update loyalty on another user's companion."""
    _, headers = auth_user
    creature = make_creature()
    db_session.add(creature)
    await db_session.flush()

    other_char = make_character()
    db_session.add(other_char)
    await db_session.flush()

    companion = make_companion(character=other_char, creature=creature)
    db_session.add(companion)
    await db_session.flush()

    with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
        mock_ps.get_current_provider.return_value = MagicMock()
        resp = await client.patch(
            f"/api/v1/companions/companions/{companion.id}/loyalty",
            params={"loyalty_change": 5, "event_description": "test"},
            headers=headers,
        )
    assert resp.status_code == 404


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


@pytest.mark.asyncio
async def test_toggle_companion_active_happy_path(client, db_session, auth_user):
    """Successfully toggle companion active state to False."""
    char, creature, companion, headers = await _seed(db_session, auth_user)

    resp = await client.patch(
        f"/api/v1/companions/companions/{companion.id}/active",
        params={"is_active": False},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_toggle_companion_active_to_true(client, db_session, auth_user):
    """Toggle companion from inactive to active."""
    user, headers = auth_user
    creature = make_creature()
    db_session.add(creature)
    await db_session.flush()

    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    companion = make_companion(character=char, creature=creature, is_active=False)
    db_session.add(companion)
    await db_session.flush()

    resp = await client.patch(
        f"/api/v1/companions/companions/{companion.id}/active",
        params={"is_active": True},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_toggle_companion_active_wrong_user(client, db_session, auth_user):
    """Cannot toggle active on another user's companion."""
    _, headers = auth_user
    creature = make_creature()
    db_session.add(creature)
    await db_session.flush()

    other_char = make_character()
    db_session.add(other_char)
    await db_session.flush()

    companion = make_companion(character=other_char, creature=creature)
    db_session.add(companion)
    await db_session.flush()

    resp = await client.patch(
        f"/api/v1/companions/companions/{companion.id}/active",
        params={"is_active": False},
        headers=headers,
    )
    assert resp.status_code == 404


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
async def test_chat_share_with_dm_persists_messages(client, db_session, auth_user):
    """When share_with_dm=True, messages are persisted and retrievable."""
    char, _, companion, headers = await _seed(db_session, auth_user)

    with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
        mock_ps.get_current_provider.return_value = MagicMock()
        with patch(
            "app.services.companion_service.CompanionService.generate_companion_response",
            new_callable=AsyncMock,
            return_value="I remember this.",
        ):
            resp = await client.post(
                "/api/v1/companions/companions/chat",
                json={
                    "companion_id": str(companion.id),
                    "message": "Remember this",
                    "share_with_dm": True,
                },
                headers=headers,
            )
    assert resp.status_code == 200
    data = resp.json()
    # Both IDs should be valid UUIDs (persisted)
    assert data["message_id"] is not None
    assert data["companion_message_id"] is not None

    # Verify they appear in conversations
    conv_resp = await client.get(
        f"/api/v1/companions/companions/{companion.id}/conversations",
        params={"shared_only": True},
        headers=headers,
    )
    assert conv_resp.status_code == 200
    messages = conv_resp.json()
    assert len(messages) >= 2


@pytest.mark.asyncio
async def test_chat_with_existing_conversation_memory(client, db_session, auth_user):
    """Chat when companion already has conversation_memory — covers context building."""
    user, headers = auth_user
    creature = make_creature()
    db_session.add(creature)
    await db_session.flush()

    char = make_character(user=user)
    db_session.add(char)
    await db_session.flush()

    memory = [
        {"role": "player", "content": "Who are you?", "timestamp": "2026-01-01T00:00:00Z"},
        {"role": "companion", "content": "I am Elara.", "timestamp": "2026-01-01T00:01:00Z"},
        {"role": "player", "content": "Where from?", "timestamp": "2026-01-01T00:02:00Z"},
        {
            "role": "companion",
            "content": "The northern forests.",
            "timestamp": "2026-01-01T00:03:00Z",
        },
    ]
    companion = make_companion(character=char, creature=creature, conversation_memory=memory)
    db_session.add(companion)
    await db_session.flush()

    with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
        mock_ps.get_current_provider.return_value = MagicMock()
        with patch(
            "app.services.companion_service.CompanionService.generate_companion_response",
            new_callable=AsyncMock,
            return_value="I recall our conversation.",
        ):
            resp = await client.post(
                "/api/v1/companions/companions/chat",
                json={
                    "companion_id": str(companion.id),
                    "message": "Do you remember me?",
                    "share_with_dm": False,
                },
                headers=headers,
            )
    assert resp.status_code == 200
    assert resp.json()["companion_response"] == "I recall our conversation."


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


@pytest.mark.asyncio
async def test_chat_wrong_user(client, db_session, auth_user):
    """Cannot chat with a companion belonging to another user."""
    _, headers = auth_user
    creature = make_creature()
    db_session.add(creature)
    await db_session.flush()

    other_char = make_character()
    db_session.add(other_char)
    await db_session.flush()

    companion = make_companion(character=other_char, creature=creature)
    db_session.add(companion)
    await db_session.flush()

    with patch("app.api.v1.endpoints.companions.provider_selector") as mock_ps:
        mock_ps.get_current_provider.return_value = MagicMock()
        resp = await client.post(
            "/api/v1/companions/companions/chat",
            json={
                "companion_id": str(companion.id),
                "message": "Hello?",
                "share_with_dm": False,
            },
            headers=headers,
        )
    assert resp.status_code == 404


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
async def test_get_conversations_all(client, db_session, auth_user):
    """shared_only=False returns both shared and private messages."""
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
        params={"shared_only": False},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    shared_flags = {msg["shared_with_dm"] for msg in data}
    assert True in shared_flags
    assert False in shared_flags


@pytest.mark.asyncio
async def test_get_conversations_not_found(client, db_session, auth_user):
    _, headers = auth_user
    resp = await client.get(
        f"/api/v1/companions/companions/{uuid.uuid4()}/conversations",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_conversations_empty(client, db_session, auth_user):
    """Companion exists but has no conversations — returns empty list."""
    char, _, companion, headers = await _seed(db_session, auth_user)

    resp = await client.get(
        f"/api/v1/companions/companions/{companion.id}/conversations",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_conversations_wrong_user(client, db_session, auth_user):
    """Cannot view conversations of another user's companion."""
    _, headers = auth_user
    creature = make_creature()
    db_session.add(creature)
    await db_session.flush()

    other_char = make_character()
    db_session.add(other_char)
    await db_session.flush()

    companion = make_companion(character=other_char, creature=creature)
    db_session.add(companion)
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/companions/companions/{companion.id}/conversations",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_conversations_message_fields(client, db_session, auth_user):
    """Verify all expected fields are present in conversation messages."""
    char, _, companion, headers = await _seed(db_session, auth_user)

    conv = make_companion_conversation(
        companion=companion,
        character=char,
        shared_with_dm=True,
        role="player",
        message="Test message",
    )
    db_session.add(conv)
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/companions/companions/{companion.id}/conversations",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    msg = data[0]
    assert "id" in msg
    assert "companion_id" in msg
    assert "character_id" in msg
    assert "role" in msg
    assert msg["role"] == "player"
    assert "message" in msg
    assert msg["message"] == "Test message"
    assert "shared_with_dm" in msg
    assert "created_at" in msg
