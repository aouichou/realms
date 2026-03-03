"""Tests for the models/providers router (/api/models)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


BASE = "/api/models"


# ===========================================================================
# GET /api/models/
# ===========================================================================


async def test_list_all_models(client):
    mock_discovery = MagicMock()
    mock_discovery.get_all_models = AsyncMock(
        return_value={"qwen": ["qwen-turbo", "qwen-plus"], "groq": ["llama3-8b"]}
    )
    with patch("app.routers.models.get_model_discovery_service", return_value=mock_discovery):
        resp = await client.get(f"{BASE}/")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert "qwen" in data["providers"]
        assert "groq" in data["providers"]


async def test_list_all_models_error(client):
    mock_discovery = MagicMock()
    mock_discovery.get_all_models = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("app.routers.models.get_model_discovery_service", return_value=mock_discovery):
        resp = await client.get(f"{BASE}/")
        assert resp.status_code == 500


# ===========================================================================
# GET /api/models/{provider_name}
# ===========================================================================


async def test_list_provider_models(client):
    mock_discovery = MagicMock()
    mock_discovery.discover_models = AsyncMock(return_value=["qwen-turbo", "qwen-plus"])

    mock_provider = MagicMock()
    mock_provider.name = "qwen"
    mock_provider.get_model = MagicMock(return_value="qwen-turbo")

    with (
        patch("app.routers.models.get_model_discovery_service", return_value=mock_discovery),
        patch("app.routers.models.provider_selector") as mock_selector,
    ):
        mock_selector.providers = [mock_provider]
        resp = await client.get(f"{BASE}/qwen")
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "qwen"
        assert "qwen-turbo" in data["models"]
        assert data["current_model"] == "qwen-turbo"


async def test_list_provider_models_unknown(client):
    mock_discovery = MagicMock()
    mock_discovery.discover_models = AsyncMock(return_value=[])
    with (
        patch("app.routers.models.get_model_discovery_service", return_value=mock_discovery),
        patch("app.routers.models.provider_selector") as mock_selector,
    ):
        mock_selector.providers = []
        resp = await client.get(f"{BASE}/unknown_provider")
        assert resp.status_code == 200
        data = resp.json()
        assert data["models"] == []
        assert data["current_model"] == "unknown"


# ===========================================================================
# POST /api/models/switch
# ===========================================================================


async def test_switch_model_success(client):
    mock_provider = MagicMock()
    mock_provider.name = "qwen"
    mock_provider.set_model = MagicMock()
    mock_provider.get_available_models = AsyncMock(return_value=["qwen-turbo", "qwen-plus"])

    with patch("app.routers.models.provider_selector") as mock_selector:
        mock_selector.providers = [mock_provider]
        resp = await client.post(f"{BASE}/switch", json={"provider": "qwen", "model": "qwen-plus"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        mock_provider.set_model.assert_called_once_with("qwen-plus")


async def test_switch_model_provider_not_found(client):
    with patch("app.routers.models.provider_selector") as mock_selector:
        mock_selector.providers = []
        resp = await client.post(f"{BASE}/switch", json={"provider": "nonexistent", "model": "m1"})
        assert resp.status_code == 404


async def test_switch_model_not_switchable(client):
    mock_provider = MagicMock(spec=[])  # no set_model
    mock_provider.name = "groq"

    with patch("app.routers.models.provider_selector") as mock_selector:
        mock_selector.providers = [mock_provider]
        resp = await client.post(f"{BASE}/switch", json={"provider": "groq", "model": "m1"})
        assert resp.status_code == 400


async def test_switch_model_invalid_model(client):
    mock_provider = MagicMock()
    mock_provider.name = "qwen"
    mock_provider.get_available_models = AsyncMock(return_value=["qwen-turbo"])

    with patch("app.routers.models.provider_selector") as mock_selector:
        mock_selector.providers = [mock_provider]
        resp = await client.post(
            f"{BASE}/switch", json={"provider": "qwen", "model": "nonexistent-model"}
        )
        assert resp.status_code == 400


# ===========================================================================
# GET /api/models/providers/status
# ===========================================================================


async def test_providers_status(client):
    mock_discovery = MagicMock()
    mock_discovery.discover_models = AsyncMock(return_value=["model-a"])

    mock_provider = MagicMock()
    mock_provider.name = "qwen"
    mock_provider.get_model = MagicMock(return_value="qwen-turbo")

    status_data = {
        "providers": [
            {
                "name": "qwen",
                "priority": 1,
                "status": "available",
                "last_error": None,
                "stats": {"requests": 10},
            }
        ]
    }

    with (
        patch("app.routers.models.get_model_discovery_service", return_value=mock_discovery),
        patch(
            "app.routers.models.get_provider_status",
            new_callable=AsyncMock,
            return_value=status_data,
        ),
        patch("app.routers.models.provider_selector") as mock_selector,
    ):
        mock_selector.providers = [mock_provider]
        resp = await client.get(f"{BASE}/providers/status")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "qwen"
        assert data[0]["status"] == "available"


# ===========================================================================
# POST /api/models/discovery/refresh
# ===========================================================================


async def test_refresh_discovery_all(client):
    mock_discovery = MagicMock()
    mock_discovery.clear_cache = MagicMock()

    with patch("app.routers.models.get_model_discovery_service", return_value=mock_discovery):
        resp = await client.post(f"{BASE}/discovery/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        mock_discovery.clear_cache.assert_called_once_with(None)


async def test_refresh_discovery_specific_provider(client):
    mock_discovery = MagicMock()
    mock_discovery.clear_cache = MagicMock()

    with patch("app.routers.models.get_model_discovery_service", return_value=mock_discovery):
        resp = await client.post(f"{BASE}/discovery/refresh", params={"provider_name": "groq"})
        assert resp.status_code == 200
        mock_discovery.clear_cache.assert_called_once_with("groq")
