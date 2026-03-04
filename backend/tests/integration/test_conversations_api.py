"""
Integration Tests - Conversation & DM Narration
Tests conversation history, DM narration, and game flow
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.db.models import Character, GameSession


@pytest.mark.asyncio
class TestConversationEndpoints:
    """Test conversation and DM narration endpoints"""

    @pytest.fixture
    async def test_session(self, test_db, test_character):
        """Create test session"""
        session = GameSession(id=uuid4(), character_id=test_character.id, is_active=True)
        test_db.add(session)
        await test_db.commit()
        await test_db.refresh(session)
        return session

    async def test_create_message(self, auth_client: AsyncClient, test_session, auth_headers):
        """Test creating a conversation message"""
        message_data = {
            "session_id": str(test_session.id),
            "role": "user",
            "content": "I look around the tavern.",
        }

        response = await auth_client.post(
            "/api/conversations/messages", json=message_data, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "user"
        assert data["content"] == "I look around the tavern."

    async def test_player_action(
        self, auth_client: AsyncClient, test_character, test_session, auth_headers
    ):
        """Test player action with DM narration"""
        action_data = {
            "character_id": str(test_character.id),
            "session_id": str(test_session.id),
            "action": "I draw my sword and approach the mysterious figure.",
        }

        response = await auth_client.post(
            "/api/conversations/action", json=action_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data  # DM narration
        assert "tokens_used" in data
        # May include roll_request, companion_speech, scene_image_url

    async def test_get_conversation_history(
        self, auth_client: AsyncClient, test_session, auth_headers
    ):
        """Test retrieving conversation history"""
        response = await auth_client.get(
            f"/api/conversations/{test_session.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "session_id" in data
        assert data["session_id"] == str(test_session.id)

    async def test_conversation_pagination(
        self, auth_client: AsyncClient, test_session, auth_headers
    ):
        """Test conversation history pagination"""
        response = await auth_client.get(
            f"/api/conversations/{test_session.id}?limit=10&offset=0", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) <= 10

    async def test_delete_conversation(self, auth_client: AsyncClient, test_session, auth_headers):
        """Test deleting conversation history"""
        response = await auth_client.delete(
            f"/api/conversations/{test_session.id}", headers=auth_headers
        )

        assert response.status_code == 204

        # Verify conversation is deleted
        get_response = await auth_client.get(
            f"/api/conversations/{test_session.id}", headers=auth_headers
        )
        assert get_response.json()["total_messages"] == 0
