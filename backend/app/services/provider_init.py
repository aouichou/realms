"""
AI Provider initialization and management.

Initializes and registers all configured AI providers at application startup.
"""

from typing import Optional

from app.config import settings
from app.observability.logger import get_logger
from app.services.ai_provider import AIProvider
from app.services.cerebras_provider import CerebrasProvider
from app.services.groq_provider import GroqProvider
from app.services.mistral_provider import MistralProvider
from app.services.provider_selector import provider_selector
from app.services.qwen_provider import QwenProvider
from app.services.sambanova_provider import SambanovaProvider
from app.services.together_provider import TogetherProvider

logger = get_logger(__name__)


async def initialize_providers():
    """
    Initialize and register all configured AI providers.

    Providers are registered in priority order based on configuration.
    """
    logger.info("Initializing AI providers...")

    # Log Mistral toggle state for visibility
    if settings.mistral_enabled:
        logger.info("🎯 DEMO MODE: Mistral enabled at priority 1 (preserving quota for recruiters)")
    else:
        logger.info(
            "🧪 TESTING MODE: Mistral deprioritized to priority 99 (emergency fallback only)"
        )

    providers_config = settings.ai_providers_config
    initialized_count = 0

    # Register providers in priority order
    for provider_name in sorted(
        providers_config.keys(), key=lambda k: providers_config[k]["priority"]
    ):
        config = providers_config[provider_name]

        if not config["enabled"]:
            logger.info(f"Provider {provider_name} is disabled (no API key)")
            continue

        try:
            provider = await create_provider(provider_name, config)
            if provider:
                provider_selector.register_provider(provider)
                initialized_count += 1
                logger.info(
                    f"✓ Registered {provider_name} (priority: {config['priority']}, model: {config['model']})"
                )
        except Exception as e:
            logger.error(f"Failed to initialize {provider_name}: {e}")

    if initialized_count == 0:
        logger.error("❌ No AI providers were initialized!")
        logger.error("Please check your API keys in the .env file")
    else:
        logger.info(f"✓ Successfully initialized {initialized_count} AI provider(s)")

    return initialized_count


async def create_provider(name: str, config: dict) -> Optional[AIProvider]:
    """
    Create a provider instance based on configuration.

    Args:
        name: Provider name ("gemini", "mistral", etc.)
        config: Provider configuration dict

    Returns:
        Provider instance or None if creation fails
    """
    try:
        if name == "qwen":
            return QwenProvider(
                api_key=config["api_key"],
                model=config["model"],
                max_tokens=config.get("max_tokens", 2048),
                temperature=config.get("temperature", 0.7),
                priority=config["priority"],
            )
        elif name == "mistral":
            return MistralProvider(
                api_key=config["api_key"],
                model=config["model"],
                max_tokens=config.get("max_tokens", 2048),
                temperature=config.get("temperature", 0.7),
                rate_limit=config.get("rate_limit", 1.0),
                priority=config["priority"],
                rate_limit_cooldown=config.get("rate_limit_cooldown", 60),  # Default 60s cooldown
            )
        elif name == "groq":
            return GroqProvider(
                api_key=config["api_key"],
                model=config["model"],
                max_tokens=config.get("max_tokens", 2048),
                temperature=config.get("temperature", 0.7),
                priority=config["priority"],
            )
        elif name == "cerebras":
            return CerebrasProvider(
                api_key=config["api_key"],
                model=config["model"],
                base_url=config.get("base_url", "https://api.cerebras.ai/v1"),
                max_tokens=config.get("max_tokens", 2048),
                temperature=config.get("temperature", 0.7),
                priority=config["priority"],
            )
        elif name == "together":
            return TogetherProvider(
                api_key=config["api_key"],
                model=config["model"],
                base_url=config.get("base_url", "https://api.together.xyz/v1"),
                max_tokens=config.get("max_tokens", 2048),
                temperature=config.get("temperature", 0.7),
                priority=config["priority"],
            )
        elif name == "sambanova":
            return SambanovaProvider(
                api_key=config["api_key"],
                model=config["model"],
                base_url=config.get("base_url", "https://api.sambanova.ai/v1"),
                max_tokens=config.get("max_tokens", 2048),
                temperature=config.get("temperature", 0.7),
                priority=config["priority"],
            )
        else:
            logger.warning(f"Unknown provider: {name}")
            return None

    except Exception as e:
        logger.error(f"Error creating {name} provider: {e}")
        return None


async def get_provider_status() -> dict:
    """
    Get status of all registered providers.

    Returns:
        Dictionary with provider statuses and stats
    """
    stats = provider_selector.get_stats()
    current = provider_selector.get_current_provider()

    return {
        "current_provider": current.name if current else None,
        "providers": [
            {
                "name": p.name,
                "priority": p.priority,
                "status": p._status.value,
                "last_error": p.get_last_error(),
                "stats": stats.get(p.name, {}),
            }
            for p in provider_selector.providers
        ],
    }
