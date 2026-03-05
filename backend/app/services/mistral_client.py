"""
Mistral AI API Client
Handles communication with Mistral AI API with streaming support, rate limiting, and error handling
"""

import asyncio
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Sequence

from mistralai import Mistral
from mistralai.models import ChatCompletionResponse

from app.config import settings
from app.observability.logger import get_logger
from app.observability.metrics import metrics
from app.observability.tracing import trace_llm_call

logger = get_logger(__name__)


class MistralAPIError(Exception):
    """Base exception for Mistral API errors"""

    pass


class RateLimitError(MistralAPIError):
    """Raised when rate limit is exceeded"""

    pass


class MistralClient:
    """
    Mistral AI API client with rate limiting, streaming support, and error handling
    """

    def __init__(self):
        """Initialize Mistral client with configuration"""
        self.client = Mistral(api_key=settings.mistral_api_key)
        self.model = settings.mistral_model
        self.max_tokens = settings.mistral_max_tokens
        self.temperature = settings.mistral_temperature

        # Rate limiting
        self.rate_limit = settings.rate_limit_per_second
        self.last_request_time = 0.0
        self.request_lock = asyncio.Lock()

        logger.info("Initialized Mistral client with model: %s", self.model)

    async def _wait_for_rate_limit(self):
        """
        Enforce rate limiting by waiting if necessary
        Thread-safe using asyncio.Lock
        """
        async with self.request_lock:
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            min_interval = 1.0 / self.rate_limit

            if time_since_last_request < min_interval:
                wait_time = min_interval - time_since_last_request
                logger.debug("Rate limiting: waiting %.2fs", wait_time)
                await asyncio.sleep(wait_time)

            self.last_request_time = time.time()

    async def chat_completion(
        self,
        messages: Sequence[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> ChatCompletionResponse:
        """
        Send a chat completion request to Mistral API

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature (defaults to configured temperature)
            max_tokens: Maximum tokens to generate (defaults to configured max_tokens)
            stream: Whether to stream the response

        Returns:
            ChatCompletionResponse from Mistral API

        Raises:
            RateLimitError: If rate limit is exceeded
            MistralAPIError: For other API errors
        """
        await self._wait_for_rate_limit()

        start_time = time.time()
        model_name = model or self.model

        try:
            logger.info(
                "Sending LLM request",
                extra={"extra_data": {"model": model_name, "messages_count": len(messages)}},
            )

            # Trace LLM call
            with trace_llm_call(model_name) as span:
                response = await asyncio.to_thread(
                    self.client.chat.complete,
                    model=model_name,
                    messages=list(messages),  # type: ignore[arg-type]
                    temperature=temperature or self.temperature,
                    max_tokens=max_tokens or self.max_tokens,
                    stream=stream,
                )

                if not stream and response.usage:
                    # Update span with token counts
                    span.set_usage(
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    )

                    # Record metrics
                    duration = time.time() - start_time
                    metrics.record_llm_request(
                        model=model_name,
                        status="success",
                        duration=duration,
                        prompt_tokens=response.usage.prompt_tokens or 0,
                        completion_tokens=response.usage.completion_tokens or 0,
                    )

                    logger.info(
                        "LLM request completed",
                        extra={
                            "extra_data": {
                                "model": model_name,
                                "tokens": response.usage.total_tokens,
                                "duration": duration,
                            }
                        },
                    )

            return response

        except Exception as e:
            error_msg = str(e).lower()
            duration = time.time() - start_time

            # Record error metrics
            metrics.record_llm_request(
                model=model_name,
                status="error",
                duration=duration,
                prompt_tokens=0,
                completion_tokens=0,
            )

            if "rate limit" in error_msg or "429" in error_msg:
                logger.error(
                    "LLM rate limit exceeded",
                    extra={"extra_data": {"model": model_name, "error": str(e)}},
                )
                raise RateLimitError("Rate limit exceeded. Please try again later.") from e

            logger.error(
                "LLM API error",
                extra={"extra_data": {"model": model_name, "error": str(e)}},
                exc_info=True,
            )
            raise MistralAPIError(f"Failed to get completion from Mistral: {e}") from e

    async def chat_completion_stream(
        self,
        messages: Sequence[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion responses from Mistral API

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature (defaults to configured temperature)
            max_tokens: Maximum tokens to generate (defaults to configured max_tokens)

        Yields:
            Content chunks as they arrive from the API

        Raises:
            RateLimitError: If rate limit is exceeded
            MistralAPIError: For other API errors
        """
        await self._wait_for_rate_limit()

        try:
            logger.debug("Starting streaming chat completion: %d messages", len(messages))

            # Get streaming response
            stream = await asyncio.to_thread(
                self.client.chat.stream,
                model=model or self.model,
                messages=list(messages),  # type: ignore[arg-type]
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )

            # Yield chunks as they arrive
            token_count = 0
            for chunk in stream:
                if chunk.data.choices and len(chunk.data.choices) > 0:
                    delta = chunk.data.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        token_count += 1
                        # Ensure content is a string
                        content = delta.content
                        if isinstance(content, str):
                            yield content
                        else:
                            yield str(content)

            logger.debug("Streaming completed: ~%d tokens", token_count)

        except Exception as e:
            error_msg = str(e).lower()

            if "rate limit" in error_msg or "429" in error_msg:
                logger.error("Rate limit exceeded during streaming: %s", e)
                raise RateLimitError("Rate limit exceeded. Please try again later.") from e

            logger.error("Mistral API streaming error: %s", e)
            raise MistralAPIError(f"Failed to stream completion from Mistral: {e}") from e

    def get_token_count(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate token count for a list of messages
        This is a rough estimation - actual count may vary

        Args:
            messages: List of message dictionaries

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        estimated_tokens = total_chars // 4
        return estimated_tokens

    def get_available_models(self) -> List[str]:
        """
        Get list of available Mistral models

        Returns:
            List of model names
        """
        # Based on Mistral AI documentation (as of Dec 2025)
        return [
            "mistral-small-latest",
            "mistral-medium-latest",
            "mistral-large-latest",
            "open-mistral-7b",
            "open-mixtral-8x7b",
            "open-mixtral-8x22b",
        ]

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about current model configuration

        Returns:
            Dictionary with model configuration
        """
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "rate_limit": f"{self.rate_limit} req/sec",
        }


# Global client instance
_mistral_client: Optional[MistralClient] = None


def get_mistral_client() -> MistralClient:
    """
    Get or create the global Mistral client instance

    Returns:
        MistralClient instance
    """
    global _mistral_client
    if _mistral_client is None:
        _mistral_client = MistralClient()
    return _mistral_client
