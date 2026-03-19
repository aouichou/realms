"""
Mistral AI Provider
Implements AIProvider interface for Mistral AI API
"""

import asyncio
import time
from typing import AsyncGenerator, Dict, List

from mistralai.client import Mistral
from mistralai.client.models import ChatCompletionResponse

from app.observability.logger import get_logger
from app.observability.metrics import metrics
from app.observability.tracing import trace_llm_call
from app.services.ai_provider import AIProvider, ProviderStatus
from app.utils.content_extractor import extract_text_content

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
        self._last_usage: dict | None = None  # Token usage from last API call

        logger.info(f"Initialized Mistral provider with model: {model}")

    def get_last_usage(self) -> dict | None:
        """
        Get token usage from the last API call.

        Returns:
            Dict with prompt_tokens, completion_tokens, total_tokens, or None
        """
        return self._last_usage

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
        await self._wait_for_rate_limit()

        model = kwargs.get("model", self.model)
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        messages = [{"role": "user", "content": prompt}]

        start_time = time.time()
        try:
            with trace_llm_call(model=model, vendor="mistral", operation="narration") as llm_span:
                response: ChatCompletionResponse = await asyncio.to_thread(
                    self.client.chat.complete,
                    model=model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                # Record token usage on the tracing span
                if response.usage:
                    llm_span.set_usage(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    )
                    self._last_usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }
                else:
                    self._last_usage = None

            duration = time.time() - start_time
            prompt_t = (
                int(getattr(response.usage, "prompt_tokens", 0) or 0) if response.usage else 0
            )
            completion_t = (
                int(getattr(response.usage, "completion_tokens", 0) or 0) if response.usage else 0
            )
            metrics.record_llm_request(
                model=model,
                status="success",
                duration=duration,
                prompt_tokens=prompt_t,
                completion_tokens=completion_t,
            )
            self.set_status(ProviderStatus.AVAILABLE)

            content = response.choices[0].message.content
            # v2: content can be str or List[ContentChunk]
            text = extract_text_content(content)
            if not text:
                raise ValueError("Empty response from Mistral API")

            return text

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Mistral generation error: {error_msg}")
            metrics.record_llm_request(model=model, status="error", duration=duration)

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
        await self._wait_for_rate_limit()

        model = kwargs.get("model", self.model)
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        start_time = time.time()
        try:
            with trace_llm_call(model=model, vendor="mistral", operation="chat") as llm_span:
                response: ChatCompletionResponse = await asyncio.to_thread(
                    self.client.chat.complete,
                    model=model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                # Record token usage on the tracing span
                if response.usage:
                    llm_span.set_usage(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    )
                    self._last_usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }
                else:
                    self._last_usage = None

            duration = time.time() - start_time
            prompt_t = (
                int(getattr(response.usage, "prompt_tokens", 0) or 0) if response.usage else 0
            )
            completion_t = (
                int(getattr(response.usage, "completion_tokens", 0) or 0) if response.usage else 0
            )
            metrics.record_llm_request(
                model=model,
                status="success",
                duration=duration,
                prompt_tokens=prompt_t,
                completion_tokens=completion_t,
            )
            self.set_status(ProviderStatus.AVAILABLE)

            content = response.choices[0].message.content
            # v2: content can be str or List[ContentChunk]
            text = extract_text_content(content)
            if not text:
                raise ValueError("Empty response from Mistral API")

            return text

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Mistral chat error: {error_msg}")
            metrics.record_llm_request(model=model, status="error", duration=duration)

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

        If rate-limited or in error, automatically becomes available after cooldown.
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

        # Auto-recover from ERROR after a cooldown (e.g. transient 401/500)
        if self._status == ProviderStatus.ERROR:
            error_cooldown = 120.0  # 2 minutes
            if self._error_at > 0:
                elapsed = time.time() - self._error_at
                if elapsed >= error_cooldown:
                    logger.info(
                        f"Mistral error cooldown elapsed ({elapsed:.1f}s), "
                        "marking as available for retry"
                    )
                    self.set_status(ProviderStatus.AVAILABLE)
                    return True
                else:
                    remaining = error_cooldown - elapsed
                    logger.debug(f"Mistral still in error cooldown ({remaining:.1f}s remaining)")
                    return False
            return False

        return self._status == ProviderStatus.AVAILABLE

    async def generate_chat_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response token-by-token using Mistral streaming API.

        Args:
            messages: List of chat messages with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature

        Yields:
            Text chunks as they arrive from the API
        """
        await self._wait_for_rate_limit()

        model = kwargs.get("model", self.model)
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        start_time = time.time()
        try:
            with trace_llm_call(model=model, vendor="mistral", operation="chat_stream") as llm_span:
                stream = self.client.chat.stream(
                    model=model,
                    messages=messages,  # type: ignore[arg-type]
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                for event in stream:
                    chunk = event.data
                    # Extract text content from delta
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        # v2: content can be str or List[ContentChunk]
                        yield extract_text_content(content)

                    # Last chunk may contain usage stats
                    if chunk.usage:
                        llm_span.set_usage(
                            prompt_tokens=chunk.usage.prompt_tokens,
                            completion_tokens=chunk.usage.completion_tokens,
                            total_tokens=chunk.usage.total_tokens,
                        )
                        self._last_usage = {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens,
                        }

            duration = time.time() - start_time
            usage = self._last_usage or {}
            metrics.record_llm_request(
                model=model,
                status="success",
                duration=duration,
                prompt_tokens=usage.get("prompt_tokens", 0) or 0,
                completion_tokens=usage.get("completion_tokens", 0) or 0,
            )
            self.set_status(ProviderStatus.AVAILABLE)

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Mistral stream error: {error_msg}")
            metrics.record_llm_request(model=model, status="error", duration=duration)

            if (
                "rate_limit" in error_msg.lower()
                or "429" in error_msg
                or "status 429" in error_msg.lower()
            ):
                self.set_status(ProviderStatus.RATE_LIMITED, error_msg)
                self.rate_limited_at = time.time()
                from app.services.ai_provider import RateLimitError

                raise RateLimitError(
                    f"Mistral rate limit exceeded: {error_msg}",
                    retry_after=self.rate_limit_cooldown,
                )

            self.set_status(ProviderStatus.ERROR, error_msg)
            from app.services.ai_provider import ProviderUnavailableError

            raise ProviderUnavailableError(f"Mistral provider error: {error_msg}")
