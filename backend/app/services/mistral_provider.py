"""
Mistral AI Provider
Implements AIProvider interface for Mistral AI API
"""

import asyncio
import time
from typing import Dict, List

from mistralai import Mistral
from mistralai.models import ChatCompletionResponse

from app.observability.logger import get_logger
from app.observability.metrics import metrics
from app.observability.tracing import (
    trace_llm_call,  # noqa: F401 - TODO: Implement in tracing ticket
)
from app.services.ai_provider import AIProvider, ProviderStatus

logger = get_logger(__name__)


class MistralProvider(AIProvider):
    """Mistral AI provider implementation"""

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        rate_limit: float = 1.0,
        priority: int = 2,
        rate_limit_cooldown: int = 60,  # Seconds to wait after rate limit
    ):
        super().__init__(name="mistral", priority=priority)
        self.client = Mistral(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.rate_limit = rate_limit
        self.rate_limit_cooldown = rate_limit_cooldown
        self.last_request_time = 0.0
        self.rate_limited_at = 0.0  # Timestamp when rate limit occurred
        self.request_lock = asyncio.Lock()

        logger.info(f"Initialized Mistral provider with model: {model}")

    async def _wait_for_rate_limit(self):
        """Enforce rate limiting"""
        async with self.request_lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            min_interval = 1.0 / self.rate_limit

            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                await asyncio.sleep(wait_time)

            self.last_request_time = time.time()

    async def generate_narration(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> str:
        """
        Generate narration using Mistral AI

        Args:
            prompt: The narration prompt
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature
            **kwargs: Additional arguments (model override, etc.)

        Returns:
            Generated narration text

        Raises:
            ProviderUnavailableError: If the API is unavailable
            RateLimitError: If rate limit is exceeded
        """
        # TODO: Add tracing with trace_llm_call context manager in observability ticket
        await self._wait_for_rate_limit()

        model = kwargs.get("model", self.model)
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        messages = [{"role": "user", "content": prompt}]

        try:
            response: ChatCompletionResponse = await asyncio.to_thread(
                self.client.chat.complete,
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )

            metrics.record_llm_request(model=model, status="success", duration=0.0)
            self.set_status(ProviderStatus.AVAILABLE)

            content = response.choices[0].message.content
            if not content or isinstance(content, list):
                raise ValueError("Empty or invalid response from Mistral API")

            return content

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Mistral generation error: {error_msg}")
            metrics.record_llm_request(model=model, status="error", duration=0.0)

            # Check for rate limit (429 status or rate_limit in message)
            if (
                "rate_limit" in error_msg.lower()
                or "429" in error_msg
                or "status 429" in error_msg.lower()
            ):
                self.set_status(ProviderStatus.RATE_LIMITED, error_msg)
                self.rate_limited_at = time.time()  # Record when rate limit occurred
                from app.services.ai_provider import RateLimitError

                logger.warning(
                    f"Mistral rate limited - will switch to fallback provider for {self.rate_limit_cooldown}s"
                )
                raise RateLimitError(
                    f"Mistral rate limit exceeded: {error_msg}",
                    retry_after=self.rate_limit_cooldown,
                )

            self.set_status(ProviderStatus.ERROR, error_msg)
            from app.services.ai_provider import ProviderUnavailableError

            raise ProviderUnavailableError(f"Mistral provider error: {error_msg}")

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> str:
        """
        Generate chat response using Mistral AI

        Args:
            messages: List of chat messages with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature
            **kwargs: Additional arguments

        Returns:
            Generated chat response
        """
        # TODO: Add tracing with trace_llm_call context manager in observability ticket
        await self._wait_for_rate_limit()

        model = kwargs.get("model", self.model)
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        try:
            response: ChatCompletionResponse = await asyncio.to_thread(
                self.client.chat.complete,
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )

            metrics.record_llm_request(model=model, status="success", duration=0.0)
            self.set_status(ProviderStatus.AVAILABLE)

            content = response.choices[0].message.content
            if not content or isinstance(content, list):
                raise ValueError("Empty or invalid response from Mistral API")

            return content

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Mistral chat error: {error_msg}")
            metrics.record_llm_request(model=model, status="error", duration=0.0)

            # Check for rate limit (429 status or rate_limit in message)
            if (
                "rate_limit" in error_msg.lower()
                or "429" in error_msg
                or "status 429" in error_msg.lower()
            ):
                self.set_status(ProviderStatus.RATE_LIMITED, error_msg)
                self.rate_limited_at = time.time()  # Record when rate limit occurred
                from app.services.ai_provider import RateLimitError

                logger.warning(
                    f"Mistral rate limited - will switch to fallback provider for {self.rate_limit_cooldown}s"
                )
                raise RateLimitError(
                    f"Mistral rate limit exceeded: {error_msg}",
                    retry_after=self.rate_limit_cooldown,
                )

            self.set_status(ProviderStatus.ERROR, error_msg)
            from app.services.ai_provider import ProviderUnavailableError

            raise ProviderUnavailableError(f"Mistral provider error: {error_msg}")

    async def is_available(self) -> bool:
        """
        Check if Mistral provider is available.

        If rate-limited, automatically becomes available after cooldown period.
        """
        # If rate limited, check if cooldown period has elapsed
        if self._status == ProviderStatus.RATE_LIMITED:
            if self.rate_limited_at > 0:
                elapsed = time.time() - self.rate_limited_at
                if elapsed >= self.rate_limit_cooldown:
                    logger.info(
                        f"Mistral cooldown period elapsed ({elapsed:.1f}s), marking as available"
                    )
                    self.set_status(ProviderStatus.AVAILABLE)
                    self.rate_limited_at = 0.0
                    return True
                else:
                    remaining = self.rate_limit_cooldown - elapsed
                    logger.debug(f"Mistral still in cooldown ({remaining:.1f}s remaining)")
                    return False
            return False

        # Rate-limited providers should be unavailable to trigger fallback
        return self._status == ProviderStatus.AVAILABLE
