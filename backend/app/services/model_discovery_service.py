"""
Model Discovery Service

Discovers available models from AI providers via their APIs.
Provides fallback hardcoded lists when discovery fails or is unavailable.
"""

import asyncio
from typing import Dict, List, Optional

import httpx
from openai import AsyncOpenAI

from app.config import settings
from app.observability.logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# HARDCODED FALLBACK MODEL LISTS
# =============================================================================
# These are used when API discovery fails or is unavailable
# Last updated: 2025-01-08

FALLBACK_MODELS: Dict[str, List[str]] = {
    "qwen": [
        "qwen-max",
        "qwen-max-longcontext",
        "qwen-plus",
        "qwen-turbo",
        "qwen-long",
        "qwen-vl-max",
        "qwen-vl-plus",
    ],
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "llama3-70b-8192",
        "llama3-8b-8192",
        "mixtral-8x7b-32768",
        "gemma-7b-it",
        "gemma2-9b-it",
    ],
    "cerebras": [
        "llama-3.3-70b",
        "llama3.1-70b",
        "llama3.1-8b",
        "qwen-3-32b",
        "gpt-oss-120b",
        "zai-glm-4.7",
    ],
    "together": [
        "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
        "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "Qwen/Qwen3-235B-A22B-Instruct-2507-tput",
        "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        "mistralai/Mistral-Small-24B-Instruct-2501",
        "openai/gpt-oss-120b",
    ],
    "sambanova": [
        "Meta-Llama-3.1-8B-Instruct",
        "Meta-Llama-3.1-70B-Instruct",
        "Meta-Llama-3.1-405B-Instruct",
        "Meta-Llama-3.3-70B-Instruct",
        "DeepSeek-V3.2",
        "Qwen-QwQ-32B-Preview",
    ],
}


class ModelDiscoveryService:
    """
    Service for discovering available models from AI providers.

    Supports dynamic discovery via API endpoints for:
    - Groq (OpenAI-compatible)
    - Cerebras (OpenAI-compatible)
    - Together.ai
    - Sambanova (OpenAI-compatible)

    Falls back to hardcoded lists when discovery fails or for:
    - Qwen/DashScope (no models endpoint)
    """

    def __init__(self):
        """Initialize model discovery service."""
        self._cache: Dict[str, List[str]] = {}
        logger.info("ModelDiscoveryService initialized")

    async def discover_models(self, provider_name: str) -> List[str]:
        """
        Discover available models for a given provider.

        Args:
            provider_name: Name of the provider ("qwen", "groq", "cerebras", etc.)

        Returns:
            List of available model identifiers

        Note:
            Uses cached results if available from previous discovery.
            Falls back to hardcoded lists on failure.
        """
        provider_name = provider_name.lower()

        # Check cache first
        if provider_name in self._cache:
            logger.debug(f"Returning cached models for {provider_name}")
            return self._cache[provider_name]

        # Try dynamic discovery
        try:
            if provider_name == "qwen":
                # Qwen/DashScope doesn't expose models endpoint - use fallback
                models = FALLBACK_MODELS.get("qwen", [])
                logger.info(f"Using hardcoded models for Qwen: {len(models)} models")

            elif provider_name == "groq":
                models = await self._discover_groq_models()

            elif provider_name == "cerebras":
                models = await self._discover_cerebras_models()

            elif provider_name == "together":
                models = await self._discover_together_models()

            elif provider_name == "sambanova":
                models = await self._discover_sambanova_models()

            else:
                logger.warning(f"Unknown provider: {provider_name}")
                models = FALLBACK_MODELS.get(provider_name, [])

            # Cache successful discovery
            if models:
                self._cache[provider_name] = models
                logger.info(f"Discovered {len(models)} models for {provider_name}")
            else:
                # Empty result - use fallback
                models = FALLBACK_MODELS.get(provider_name, [])
                logger.warning(f"No models discovered for {provider_name}, using fallback")

            return models

        except Exception as e:
            logger.error(f"Error discovering models for {provider_name}: {e}")
            # Return fallback on any error
            return FALLBACK_MODELS.get(provider_name, [])

    async def _discover_groq_models(self) -> List[str]:
        """
        Discover Groq models via OpenAI-compatible endpoint.

        Returns:
            List of model IDs
        """
        try:
            client = AsyncOpenAI(
                api_key=settings.groq_api_key or "dummy-key-for-list",
                base_url="https://api.groq.com/openai/v1",
            )

            response = await client.models.list()
            models = [model.id for model in response.data if hasattr(model, "id")]

            logger.info(f"Groq API returned {len(models)} models")
            return models

        except Exception as e:
            logger.warning(f"Groq model discovery failed: {e}")
            return []

    async def _discover_cerebras_models(self) -> List[str]:
        """
        Discover Cerebras models via public API endpoint.

        Returns:
            List of model IDs

        Note:
            Uses public endpoint which doesn't require authentication
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use public endpoint (no auth required)
                response = await client.get("https://api.cerebras.ai/public/v1/models")
                response.raise_for_status()

                data = response.json()
                models = [model["id"] for model in data.get("data", []) if "id" in model]

                logger.info(f"Cerebras API returned {len(models)} models")
                return models

        except Exception as e:
            logger.warning(f"Cerebras model discovery failed: {e}")
            return []

    async def _discover_together_models(self) -> List[str]:
        """
        Discover Together.ai models via API endpoint.

        Returns:
            List of model IDs
        """
        try:
            headers = {}
            if settings.together_api_key:
                headers["Authorization"] = f"Bearer {settings.together_api_key}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://api.together.xyz/v1/models", headers=headers)
                response.raise_for_status()

                data = response.json()
                # Together.ai returns models with various types - filter for chat models
                all_models = data.get("models", data.get("data", []))
                models = [
                    model["id"]
                    for model in all_models
                    if isinstance(model, dict)
                    and "id" in model
                    and model.get("type") in ["chat", None]
                ]

                logger.info(f"Together.ai API returned {len(models)} models")
                return models

        except Exception as e:
            logger.warning(f"Together.ai model discovery failed: {e}")
            return []

    async def _discover_sambanova_models(self) -> List[str]:
        """
        Discover Sambanova models via OpenAI-compatible endpoint.

        Returns:
            List of model IDs
        """
        try:
            client = AsyncOpenAI(
                api_key=settings.sambanova_api_key or "dummy-key-for-list",
                base_url=settings.sambanova_base_url or "https://api.sambanova.ai/v1",
            )

            response = await client.models.list()
            models = [model.id for model in response.data if hasattr(model, "id")]

            logger.info(f"Sambanova API returned {len(models)} models")
            return models

        except Exception as e:
            logger.warning(f"Sambanova model discovery failed: {e}")
            return []

    async def get_all_models(self) -> Dict[str, List[str]]:
        """
        Discover models for all providers concurrently.

        Returns:
            Dictionary mapping provider names to model lists
        """
        providers = ["qwen", "groq", "cerebras", "together", "sambanova"]

        tasks = [self.discover_models(provider) for provider in providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_models = {}
        for provider, result in zip(providers, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to discover models for {provider}: {result}")
                all_models[provider] = FALLBACK_MODELS.get(provider, [])
            else:
                all_models[provider] = result

        return all_models

    def get_fallback_models(self, provider_name: str) -> List[str]:
        """
        Get hardcoded fallback models for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            List of fallback model identifiers
        """
        return FALLBACK_MODELS.get(provider_name.lower(), [])

    def clear_cache(self, provider_name: Optional[str] = None):
        """
        Clear cached models.

        Args:
            provider_name: Specific provider to clear, or None for all
        """
        if provider_name:
            self._cache.pop(provider_name.lower(), None)
            logger.info(f"Cleared cache for {provider_name}")
        else:
            self._cache.clear()
            logger.info("Cleared all model cache")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_model_discovery_service: Optional[ModelDiscoveryService] = None


def get_model_discovery_service() -> ModelDiscoveryService:
    """
    Get or create the model discovery service singleton.

    Returns:
        ModelDiscoveryService instance
    """
    global _model_discovery_service
    if _model_discovery_service is None:
        _model_discovery_service = ModelDiscoveryService()
    return _model_discovery_service
