"""
Integration Tests - Authentication Endpoints
Tests user registration, login, and token management
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthEndpoints:
    """Test authentication API endpoints"""

    async def test_register_user(self, auth_client: AsyncClient):
        """Test user registration"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
        }

        response = await auth_client.post("/api/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "id" in data
        assert "password" not in data

    async def test_register_duplicate_username(self, auth_client: AsyncClient, test_user):
        """Test registering with duplicate username"""
        user_data = {
            "username": test_user.username,
            "email": "different@example.com",
            "password": "SecurePassword123!",
        }

        response = await auth_client.post("/api/auth/register", json=user_data)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    async def test_login_success(self, auth_client: AsyncClient, test_user):
        """Test successful login"""
        login_data = {"username": test_user.username, "password": "test_password"}

        response = await auth_client.post("/api/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, auth_client: AsyncClient):
        """Test login with invalid credentials"""
        login_data = {"username": "nonexistent", "password": "wrong_password"}

        response = await auth_client.post("/api/auth/login", json=login_data)

        assert response.status_code == 401

    async def test_refresh_token(self, auth_client: AsyncClient, test_user):
        """Test token refresh"""
        # First login to get tokens
        login_data = {"username": test_user.username, "password": "test_password"}
        login_response = await auth_client.post("/api/auth/login", json=login_data)
        refresh_token = login_response.json()["refresh_token"]

        # Refresh the token
        refresh_data = {"refresh_token": refresh_token}
        response = await auth_client.post("/api/auth/refresh", json=refresh_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_guest_mode(self, auth_client: AsyncClient):
        """Test guest user creation"""
        response = await auth_client.post("/api/auth/guest")

        assert response.status_code == 201
        data = response.json()
        assert "guest_" in data["username"]
        assert data["is_guest"] is True
        assert "access_token" in data
