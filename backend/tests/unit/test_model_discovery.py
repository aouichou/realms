"""Tests for app.services.model_discovery_service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.services.model_discovery_service import (
    FALLBACK_MODELS,
    ModelDiscoveryService,
)

# ---------------------------------------------------------------------------
# discover_models — caching & fallback
# ---------------------------------------------------------------------------


class TestDiscoverModels:
    async def test_returns_cached(self):
        svc = ModelDiscoveryService()
        svc._cache["groq"] = ["cached-model"]
        result = await svc.discover_models("groq")
        assert result == ["cached-model"]

    async def test_qwen_uses_fallback(self):
        svc = ModelDiscoveryService()
        result = await svc.discover_models("qwen")
        assert result == FALLBACK_MODELS["qwen"]
        assert "qwen" in svc._cache

    async def test_unknown_provider_uses_fallback(self):
        svc = ModelDiscoveryService()
        result = await svc.discover_models("nonexistent")
        assert result == []

    @patch.object(ModelDiscoveryService, "_discover_groq_models", new_callable=AsyncMock)
    async def test_groq_discovery(self, mock_discover):
        mock_discover.return_value = ["llama-70b", "llama-8b"]
        svc = ModelDiscoveryService()
        result = await svc.discover_models("groq")
        assert result == ["llama-70b", "llama-8b"]
        assert svc._cache["groq"] == ["llama-70b", "llama-8b"]

    @patch.object(ModelDiscoveryService, "_discover_groq_models", new_callable=AsyncMock)
    async def test_groq_empty_falls_back(self, mock_discover):
        mock_discover.return_value = []
        svc = ModelDiscoveryService()
        result = await svc.discover_models("groq")
        assert result == FALLBACK_MODELS["groq"]

    @patch.object(ModelDiscoveryService, "_discover_cerebras_models", new_callable=AsyncMock)
    async def test_cerebras_discovery(self, mock_discover):
        mock_discover.return_value = ["llama-3.3-70b"]
        svc = ModelDiscoveryService()
        result = await svc.discover_models("cerebras")
        assert result == ["llama-3.3-70b"]

    @patch.object(ModelDiscoveryService, "_discover_together_models", new_callable=AsyncMock)
    async def test_together_discovery(self, mock_discover):
        mock_discover.return_value = ["model-a"]
        svc = ModelDiscoveryService()
        result = await svc.discover_models("together")
        assert result == ["model-a"]

    @patch.object(ModelDiscoveryService, "_discover_sambanova_models", new_callable=AsyncMock)
    async def test_sambanova_discovery(self, mock_discover):
        mock_discover.return_value = ["meta-llama"]
        svc = ModelDiscoveryService()
        result = await svc.discover_models("sambanova")
        assert result == ["meta-llama"]

    @patch.object(ModelDiscoveryService, "_discover_groq_models", new_callable=AsyncMock)
    async def test_exception_returns_fallback(self, mock_discover):
        mock_discover.side_effect = RuntimeError("network error")
        svc = ModelDiscoveryService()
        result = await svc.discover_models("groq")
        assert result == FALLBACK_MODELS["groq"]

    async def test_case_insensitive(self):
        svc = ModelDiscoveryService()
        result = await svc.discover_models("QWEN")
        assert result == FALLBACK_MODELS["qwen"]


# ---------------------------------------------------------------------------
# API discovery helpers (mocked HTTP)
# ---------------------------------------------------------------------------


class TestDiscoveryHelpers:
    @patch("app.services.model_discovery_service.AsyncOpenAI")
    async def test_discover_groq_models(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_model = MagicMock()
        mock_model.id = "llama3-70b-8192"
        mock_client.models.list = AsyncMock(return_value=MagicMock(data=[mock_model]))
        mock_openai_cls.return_value = mock_client

        svc = ModelDiscoveryService()
        result = await svc._discover_groq_models()
        assert result == ["llama3-70b-8192"]

    @patch("app.services.model_discovery_service.AsyncOpenAI")
    async def test_discover_groq_exception(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_client.models.list = AsyncMock(side_effect=Exception("fail"))
        mock_openai_cls.return_value = mock_client

        svc = ModelDiscoveryService()
        result = await svc._discover_groq_models()
        assert result == []

    @patch("app.services.model_discovery_service.httpx.AsyncClient")
    async def test_discover_cerebras_models(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"data": [{"id": "llama-3.3-70b"}]}
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        svc = ModelDiscoveryService()
        result = await svc._discover_cerebras_models()
        assert "llama-3.3-70b" in result

    @patch("app.services.model_discovery_service.httpx.AsyncClient")
    async def test_discover_together_models(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"data": [{"id": "model-x", "type": "chat"}]}
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        svc = ModelDiscoveryService()
        result = await svc._discover_together_models()
        assert "model-x" in result


# ---------------------------------------------------------------------------
# get_all_models
# ---------------------------------------------------------------------------


class TestGetAllModels:
    @patch.object(ModelDiscoveryService, "discover_models", new_callable=AsyncMock)
    async def test_get_all_models(self, mock_discover):
        mock_discover.return_value = ["m1"]
        svc = ModelDiscoveryService()
        result = await svc.get_all_models()
        assert "qwen" in result
        assert "groq" in result
        assert all(v == ["m1"] for v in result.values())

    @patch.object(ModelDiscoveryService, "discover_models", new_callable=AsyncMock)
    async def test_exception_falls_back(self, mock_discover):
        mock_discover.side_effect = RuntimeError("oops")
        svc = ModelDiscoveryService()
        result = await svc.get_all_models()
        # Should have fallback models for each provider
        for provider in ["qwen", "groq", "cerebras", "together", "sambanova"]:
            assert provider in result


# ---------------------------------------------------------------------------
# get_fallback_models / clear_cache
# ---------------------------------------------------------------------------


class TestFallbackAndCache:
    def test_get_fallback_models(self):
        svc = ModelDiscoveryService()
        assert svc.get_fallback_models("groq") == FALLBACK_MODELS["groq"]
        assert svc.get_fallback_models("CEREBRAS") == FALLBACK_MODELS["cerebras"]
        assert svc.get_fallback_models("unknown") == []

    def test_clear_cache_specific(self):
        svc = ModelDiscoveryService()
        svc._cache["groq"] = ["x"]
        svc._cache["qwen"] = ["y"]
        svc.clear_cache("groq")
        assert "groq" not in svc._cache
        assert "qwen" in svc._cache

    def test_clear_cache_all(self):
        svc = ModelDiscoveryService()
        svc._cache["groq"] = ["x"]
        svc._cache["qwen"] = ["y"]
        svc.clear_cache()
        assert svc._cache == {}
