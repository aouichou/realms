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
from app.observability.tracing import trace_llm_call
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
    ):
        super().__init__(name="mistral", priority=priority)
        self.client = Mistral(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.rate_limit = rate_limit
        self.last_request_time = 0.0
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

    @trace_llm_call
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
        await self._wait_for_rate_limit()

        model = kwargs.get("model", self.model)
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        messages = [{"role": "user", "content": prompt}]

        try:
            response: ChatCompletionResponse = await asyncio.to_thread(
                self.client.chat.complete,
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            metrics.increment("mistral.requests.success")
            self._update_status(ProviderStatus.AVAILABLE)

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from Mistral API")

            return content

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Mistral generation error: {error_msg}")
            metrics.increment("mistral.requests.error")

            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                self._update_status(ProviderStatus.RATE_LIMITED, error_msg)
                from app.services.ai_provider import RateLimitError

                raise RateLimitError(f"Mistral rate limit exceeded: {error_msg}")

            self._update_status(ProviderStatus.ERROR, error_msg)
            from app.services.ai_provider import ProviderUnavailableError

            raise ProviderUnavailableError(f"Mistral provider error: {error_msg}")

    @trace_llm_call
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
        await self._wait_for_rate_limit()

        model = kwargs.get("model", self.model)
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        try:
            response: ChatCompletionResponse = await asyncio.to_thread(
                self.client.chat.complete,
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            metrics.increment("mistral.requests.success")
            self._update_status(ProviderStatus.AVAILABLE)

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from Mistral API")

            return content

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Mistral chat error: {error_msg}")
            metrics.increment("mistral.requests.error")

            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                self._update_status(ProviderStatus.RATE_LIMITED, error_msg)
                from app.services.ai_provider import RateLimitError

                raise RateLimitError(f"Mistral rate limit exceeded: {error_msg}")

            self._update_status(ProviderStatus.ERROR, error_msg)
            from app.services.ai_provider import ProviderUnavailableError

            raise ProviderUnavailableError(f"Mistral provider error: {error_msg}")

    async def is_available(self) -> bool:
        """Check if Mistral provider is available"""
        return self.status == ProviderStatus.AVAILABLE or self.status == ProviderStatus.ERROR
