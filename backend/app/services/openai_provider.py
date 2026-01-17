"""
OpenAI Provider
Implements AIProvider interface for OpenAI API
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


class OpenAIProvider(AIProvider):
    """OpenAI provider implementation"""

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        priority: int = 3,
    ):
        super().__init__(name="openai", priority=priority)
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.default_max_tokens = max_tokens
        self.default_temperature = temperature

        logger.info(f"Initialized OpenAI provider with model: {model}")

    async def generate_narration(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> str:
        """
        Generate narration using OpenAI

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
        return await self.generate_chat(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

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
            )

            content = response.choices[0].message.content
            if not content:
                raise ProviderUnavailableError("OpenAI returned empty response")

            self.set_status(ProviderStatus.AVAILABLE)
            return content

        except OpenAIRateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded: {e}")
            self.set_status(ProviderStatus.RATE_LIMITED, str(e))
            # Extract retry_after from headers if available
            retry_after = getattr(e, "retry_after", None)
            raise RateLimitError(str(e), retry_after=retry_after)

        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            self.set_status(ProviderStatus.ERROR, str(e))
            raise ProviderUnavailableError(f"OpenAI API error: {e}")

        except Exception as e:
            logger.error(f"Unexpected OpenAI error: {e}")
            self.set_status(ProviderStatus.ERROR, str(e))
            raise ProviderUnavailableError(f"OpenAI error: {e}")

    async def is_available(self) -> bool:
        """
        Check if OpenAI is currently available

        Returns:
            True if provider can accept requests
        """
        # Provider is available if not in error or rate-limited state
        return self._status in [ProviderStatus.AVAILABLE, ProviderStatus.UNAVAILABLE]
