"""
Provider selector service with automatic fallback logic.

Manages multiple AI providers, automatically selecting the best available
provider and falling back to alternatives when rate limits or errors occur.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.ai_provider import (
    AIProvider,
    ProviderUnavailableError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class ProviderSelector:
    """
    Selects AI providers based on availability and priority.

    Handles automatic fallback when providers are unavailable or rate-limited.
    """

    def __init__(self):
        """Initialize provider selector."""
        self.providers: List[AIProvider] = []
        self.current_provider: Optional[AIProvider] = None
        self.provider_stats: Dict[str, Dict[str, Any]] = {}

    def register_provider(self, provider: AIProvider):
        """
        Register an AI provider.

        Args:
            provider: Provider instance to register
        """
        self.providers.append(provider)
        # Sort by priority (lower number = higher priority)
        self.providers.sort(key=lambda p: p.priority)

        # Initialize stats
        self.provider_stats[provider.name] = {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "last_used": None,
            "last_error": None,
        }

        logger.info(f"Registered provider: {provider.name} (priority: {provider.priority})")

    async def select_provider(self) -> AIProvider:
        """
        Select the best available provider.

        Returns:
            Selected provider

        Raises:
            ProviderUnavailableError: If no providers are available
        """
        if not self.providers:
            raise ProviderUnavailableError("No AI providers registered")

        # Try providers in priority order
        for provider in self.providers:
            if await provider.is_available():
                if self.current_provider != provider:
                    logger.info(f"Switching to provider: {provider.name}")
                    self.current_provider = provider
                return provider

        # No providers available
        status_info = ", ".join([f"{p.name}: {p._status.value}" for p in self.providers])
        raise ProviderUnavailableError(f"No AI providers available. Status: {status_info}")

    async def generate_narration(
        self, prompt: str, max_tokens: int, temperature: float, **kwargs
    ) -> str:
        """
        Generate narration using the best available provider.

        Automatically tries fallback providers if primary fails.

        Args:
            prompt: The prompt text
            max_tokens: Maximum tokens to generate
            temperature: Temperature for randomness
            **kwargs: Additional parameters

        Returns:
            Generated narration text

        Raises:
            ProviderUnavailableError: If all providers fail
        """
        last_error = None

        # Try each provider in priority order
        for provider in self.providers:
            if not await provider.is_available():
                continue

            try:
                # Track request
                stats = self.provider_stats[provider.name]
                stats["requests"] += 1
                stats["last_used"] = datetime.utcnow()

                # Generate with this provider
                result = await provider.generate_narration(
                    prompt=prompt, max_tokens=max_tokens, temperature=temperature, **kwargs
                )

                # Success!
                stats["successes"] += 1
                logger.info(f"Successfully generated narration with {provider.name}")
                return result

            except RateLimitError as e:
                logger.warning(f"Provider {provider.name} hit rate limit: {e}")
                stats["failures"] += 1
                stats["last_error"] = str(e)
                last_error = e
                # Try next provider

            except ProviderUnavailableError as e:
                logger.error(f"Provider {provider.name} unavailable: {e}")
                stats["failures"] += 1
                stats["last_error"] = str(e)
                last_error = e
                # Try next provider

            except Exception as e:
                logger.error(f"Unexpected error with provider {provider.name}: {e}")
                stats["failures"] += 1
                stats["last_error"] = str(e)
                last_error = e
                # Try next provider

        # All providers failed
        raise ProviderUnavailableError(f"All AI providers failed. Last error: {last_error}")

    async def generate_chat(
        self, messages: List[Dict[str, str]], max_tokens: int, temperature: float, **kwargs
    ) -> str:
        """
        Generate chat response using the best available provider.

        Args:
            messages: Conversation history
            max_tokens: Maximum tokens to generate
            temperature: Temperature for randomness
            **kwargs: Additional parameters

        Returns:
            Generated response text
        """
        last_error = None

        for provider in self.providers:
            if not await provider.is_available():
                continue

            try:
                stats = self.provider_stats[provider.name]
                stats["requests"] += 1
                stats["last_used"] = datetime.utcnow()

                result = await provider.generate_chat(
                    messages=messages, max_tokens=max_tokens, temperature=temperature, **kwargs
                )

                stats["successes"] += 1
                logger.info(f"Successfully generated chat with {provider.name}")
                return result

            except (RateLimitError, ProviderUnavailableError, Exception) as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                stats["failures"] += 1
                stats["last_error"] = str(e)
                last_error = e

        raise ProviderUnavailableError(f"All AI providers failed. Last error: {last_error}")

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get provider usage statistics.

        Returns:
            Dictionary of provider stats
        """
        return self.provider_stats

    def get_current_provider(self) -> Optional[AIProvider]:
        """
        Get the currently selected provider.

        Returns:
            Current provider or None
        """
        return self.current_provider


# Global provider selector instance
provider_selector = ProviderSelector()
