"""
Groq Provider
Implements AIProvider interface for Groq API (OpenAI-compatible)
Ultra-fast inference with generous free tier (14,400 req/day)
"""

import time
from typing import Any, Dict, List

from openai import APIError, AsyncOpenAI
from openai import RateLimitError as OpenAIRateLimitError

from app.observability.logger import get_logger
from app.observability.metrics import metrics
from app.services.ai_provider import (
    AIProvider,
    ProviderStatus,
    ProviderUnavailableError,
    RateLimitError,
)

logger = get_logger(__name__)


class GroqProvider(AIProvider):
    """Groq provider implementation (OpenAI-compatible)"""

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        priority: int = 3,
    ):
        super().__init__(name="groq", priority=priority)
        # Groq uses OpenAI-compatible API
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model = model
        self.default_max_tokens = max_tokens
        self.default_temperature = temperature

        logger.info(f"Initialized Groq provider with model: {model}")

    async def generate_narration(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> str:
        """
        Generate narration using Groq

        Args:
            prompt: The narration prompt
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature
            **kwargs: Additional arguments

        Returns:
            Generated narration text

        Raises:
            ProviderUnavailableError: If the API is unavailable
            RateLimitError: If rate limit is exceeded (14,400 req/day)
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
        start_time = time.time()
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
                raise ProviderUnavailableError("Groq returned empty response")

            duration = time.time() - start_time
            prompt_t = (
                int(getattr(response.usage, "prompt_tokens", 0) or 0) if response.usage else 0
            )
            completion_t = (
                int(getattr(response.usage, "completion_tokens", 0) or 0) if response.usage else 0
            )
            metrics.record_llm_request(
                model=self.model,
                status="success",
                duration=duration,
                prompt_tokens=prompt_t,
                completion_tokens=completion_t,
            )
            self.set_status(ProviderStatus.AVAILABLE)
            return content

        except OpenAIRateLimitError as e:
            duration = time.time() - start_time
            metrics.record_llm_request(model=self.model, status="error", duration=duration)
            logger.warning(f"Groq rate limit exceeded: {e}")
            self.set_status(ProviderStatus.RATE_LIMITED, str(e))
            # Groq has daily limits (14,400 req/day)
            retry_after = getattr(e, "retry_after", None) or 3600  # Default 1 hour
            raise RateLimitError(str(e), retry_after=retry_after)

        except APIError as e:
            duration = time.time() - start_time
            metrics.record_llm_request(model=self.model, status="error", duration=duration)
            logger.error(f"Groq API error: {e}")
            self.set_status(ProviderStatus.ERROR, str(e))
            raise ProviderUnavailableError(f"Groq provider error: {str(e)}")

        except Exception as e:
            duration = time.time() - start_time
            metrics.record_llm_request(model=self.model, status="error", duration=duration)
            logger.error(f"Unexpected Groq error: {e}")
            self.set_status(ProviderStatus.ERROR, str(e))
            raise ProviderUnavailableError(f"Groq provider error: {str(e)}")

    async def is_available(self) -> bool:
        """
        Check if Groq is currently available

        Returns:
            True if provider can accept requests
        """
        # Provider is available if not in error or rate-limited state
        return self._status in [ProviderStatus.AVAILABLE, ProviderStatus.UNAVAILABLE]
