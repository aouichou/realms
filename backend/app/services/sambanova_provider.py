"""
Sambanova Provider
Implements AIProvider interface for Sambanova API (OpenAI-compatible)
Unlimited inference with rate limits
"""

from typing import Any, Dict, List

from openai import APIError, AsyncOpenAI
from openai import RateLimitError as OpenAIRateLimitError

from app.observability.logger import get_logger
from app.services.ai_provider import (
    AIProvider,
    ProviderStatus,
    ProviderUnavailableError,
    RateLimitError,
)

logger = get_logger(__name__)


class SambanovaProvider(AIProvider):
    """Sambanova provider implementation (OpenAI-compatible)"""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.sambanova.ai/v1",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        priority: int = 3,
    ):
        super().__init__(name="sambanova", priority=priority)
        # Sambanova uses OpenAI-compatible API
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model
        self.default_max_tokens = max_tokens
        self.default_temperature = temperature

        logger.info(f"Initialized Sambanova provider with model: {model}")

    async def generate_narration(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> str:
        """
        Generate narration using Sambanova

        Args:
            prompt: The narration prompt
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature
            **kwargs: Additional arguments

        Returns:
            Generated narration text

        Raises:
            ProviderUnavailableError: If the API is unavailable
            RateLimitError: If rate limit is exceeded
        """
        messages = [{"role": "user", "content": prompt}]
        return await self.generate_chat(messages, max_tokens, temperature, **kwargs)

    async def generate_chat(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> str:
        """
        Generate response from conversation history

        Args:
            messages: List of messages with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature
            **kwargs: Additional arguments

        Returns:
            Generated response text

        Raises:
            ProviderUnavailableError: If the API is unavailable
            RateLimitError: If rate limit is exceeded
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=max_tokens or self.default_max_tokens,
                temperature=temperature or self.default_temperature,
                **kwargs,  # Pass through tools, functions, etc.
            )

            content = response.choices[0].message.content
            if not content:
                raise ProviderUnavailableError("Sambanova returned empty response")

            self.set_status(ProviderStatus.AVAILABLE)
            return content

        except OpenAIRateLimitError as e:
            logger.warning(f"Sambanova rate limit exceeded: {e}")
            self.set_status(ProviderStatus.RATE_LIMITED, str(e))
            retry_after = getattr(e, "retry_after", None) or 60  # Default 1 minute
            raise RateLimitError(str(e), retry_after=retry_after)

        except APIError as e:
            logger.error(f"Sambanova API error: {e}")
            self.set_status(ProviderStatus.ERROR, str(e))
            raise ProviderUnavailableError(f"Sambanova provider error: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected Sambanova error: {e}")
            self.set_status(ProviderStatus.ERROR, str(e))
            raise ProviderUnavailableError(f"Sambanova provider error: {str(e)}")

    async def is_available(self) -> bool:
        """
        Check if Sambanova is currently available

        Returns:
            True if provider can accept requests
        """
        # Provider is available if not in error or rate-limited state
        return self._status in [ProviderStatus.AVAILABLE, ProviderStatus.UNAVAILABLE]
