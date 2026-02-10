"""
Qwen (Alibaba Cloud DashScope) Provider
Implements AIProvider interface for Alibaba Cloud Qwen models via OpenAI-compatible API
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


class QwenProvider(AIProvider):
    """Qwen (Alibaba Cloud DashScope) provider implementation"""

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.6,
        priority: int = 1,
    ):
        super().__init__(name="qwen", priority=priority)
        # DashScope OpenAI-compatible endpoint
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )
        self.model = model
        self.default_max_tokens = max_tokens
        self.default_temperature = temperature

        logger.info(f"Initialized Qwen provider with model: {model}")

    async def generate_narration(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> str:
        """
        Generate narration using Qwen

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
                **kwargs,  # Pass through tools, functions, etc.
            )

            content = response.choices[0].message.content
            if not content:
                raise ProviderUnavailableError("Qwen returned empty response")

            self.set_status(ProviderStatus.AVAILABLE)
            return content

        except OpenAIRateLimitError as e:
            logger.warning(f"Qwen rate limit exceeded: {e}")
            self.set_status(ProviderStatus.RATE_LIMITED, str(e))
            # Extract retry_after from headers if available
            retry_after = getattr(e, "retry_after", None)
            raise RateLimitError(str(e), retry_after=retry_after)

        except APIError as e:
            logger.error(f"Qwen API error: {e}")
            self.set_status(ProviderStatus.ERROR, str(e))
            raise ProviderUnavailableError(f"Qwen API error: {e}")

        except Exception as e:
            logger.error(f"Unexpected Qwen error: {e}")
            self.set_status(ProviderStatus.ERROR, str(e))
            raise ProviderUnavailableError(f"Qwen error: {e}")

    async def is_available(self) -> bool:
        """
        Check if Qwen is currently available

        Returns:
            True if provider can accept requests
        """
        # Provider is available if not in error or rate-limited state
        return self._status in [ProviderStatus.AVAILABLE, ProviderStatus.UNAVAILABLE]
