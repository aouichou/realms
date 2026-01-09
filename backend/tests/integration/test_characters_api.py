"""
Integration Tests - Character API Endpoints
Tests character creation, retrieval, updating, and deletion
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Character, User
from app.main import app


@pytest.fixture
async def auth_headers(test_user: User, test_db: AsyncSession):
    """Get authentication headers for test user"""
    # In real implementation, generate JWT token
    return {"Authorization": f"Bearer test_token_{test_user.id}"}


@pytest.mark.asyncio
class TestCharacterEndpoints:
    """Test character API endpoints"""

    async def test_create_character(self, auth_client: AsyncClient, auth_headers: dict):
        """Test character creation"""
        character_data = {
            "name": "Test Warrior",
            "race": "human",
            "character_class": "fighter",
            "level": 1,
            "strength": 16,
            "dexterity": 14,
            "constitution": 15,
            "intelligence": 10,
            "wisdom": 12,
            "charisma": 8,
        }

        response = await auth_client.post(
            "/api/characters", json=character_data, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Warrior"
        assert data["race"] == "human"
        assert data["character_class"] == "fighter"
        assert "id" in data

    async def test_get_character(
        self, auth_client: AsyncClient, test_character: Character, auth_headers: dict
    ):
        """Test character retrieval"""
        response = await auth_client.get(
            f"/api/characters/{test_character.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_character.id)
        assert data["name"] == test_character.name

    async def test_list_characters(
        self, auth_client: AsyncClient, test_character: Character, auth_headers: dict
    ):
        """Test listing user's characters"""
        response = await auth_client.get("/api/characters", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "characters" in data
        assert len(data["characters"]) > 0
        assert data["characters"][0]["id"] == str(test_character.id)

    async def test_update_character(
        self, auth_client: AsyncClient, test_character: Character, auth_headers: dict
    ):
        """Test character update"""
        update_data = {"name": "Updated Warrior", "level": 2}

        response = await auth_client.patch(
            f"/api/characters/{test_character.id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Warrior"
        assert data["level"] == 2

    async def test_delete_character(
        self, auth_client: AsyncClient, test_character: Character, auth_headers: dict
    ):
        """Test character deletion"""
        response = await auth_client.delete(
            f"/api/characters/{test_character.id}", headers=auth_headers
        )

        assert response.status_code == 204

        # Verify character is deleted
        get_response = await auth_client.get(
            f"/api/characters/{test_character.id}", headers=auth_headers
        )
        assert get_response.status_code == 404

    async def test_unauthorized_access(self, auth_client: AsyncClient, test_character: Character):
        """Test accessing character without authentication"""
        response = await auth_client.get(f"/api/characters/{test_character.id}")

        assert response.status_code == 401
