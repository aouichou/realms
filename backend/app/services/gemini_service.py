"""
Google Gemini AI service implementation.

Handles API calls to Google's Gemini models, prompt formatting,
and error handling specific to the Gemini API.
"""

import asyncio
import time
from typing import Dict, List

from google import genai
from google.genai.types import GenerateContentConfig

from app.observability.logger import get_logger
from app.observability.metrics import metrics
from app.observability.tracing import get_tracer, trace_llm_call
from app.services.ai_provider import (
    AIProvider,
    ProviderStatus,
    ProviderUnavailableError,
    RateLimitError,
)

logger = get_logger(__name__)


class GeminiService(AIProvider):
    """
    Google Gemini AI provider implementation.

    Supports text generation using Gemini's free tier models
    with generous rate limits.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        priority: int = 1,
        thinking_level: str = "high",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ):
        """
        Initialize Gemini service.

        Args:
            api_key: Google Gemini API key
            model: Model name (e.g., "gemini-3-flash-preview")
            priority: Provider priority (lower = higher priority)
            thinking_level: Thinking level for Gemini 3 models (minimal, low, medium, high)
            max_tokens: Default maximum tokens
            temperature: Default temperature
        """
        super().__init__(name="gemini", priority=priority)
        self.api_key = api_key
        self.model_name = model
        self.thinking_level = thinking_level
        self.default_max_tokens = max_tokens
        self.default_temperature = temperature
        self.client = None

        try:
            # Configure Gemini with API key
            self.client = genai.Client(api_key=self.api_key)
            logger.info(
                f"Gemini service initialized with model {model}, thinking_level={thinking_level}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini service: {e}")
            self.set_status(ProviderStatus.ERROR, str(e))

    async def generate_narration(
        self, prompt: str, max_tokens: int, temperature: float, **kwargs
    ) -> str:
        """
        Generate D&D narration from a prompt.

        Args:
            prompt: The prompt text to generate from
            max_tokens: Maximum tokens to generate
            temperature: Temperature for randomness (0.0-1.0)
            **kwargs: Additional parameters

        Returns:
            Generated narration text

        Raises:
            RateLimitError: If rate limit is exceeded
            ProviderUnavailableError: If service is unavailable
        """
        if not await self.is_available():
            raise ProviderUnavailableError(f"Gemini provider is unavailable: {self._last_error}")

        start_time = time.time()
        
        # Estimate token counts (rough approximation: 1 token ≈ 0.75 words)
        prompt_tokens = int(len(prompt.split()) / 0.75)
        
        # Add LLM tracing like MistralClient
        with trace_llm_call(
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=None,
        ) as span:
            try:
                # Build config with thinking for D&D DMing
                config = GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                )

                # Add thinking config for Gemini 3 models (improves D&D reasoning)
                if "gemini-3" in self.model_name or "gemini-2.5" in self.model_name:
                    from google.genai.types import ThinkingConfig

                    config.thinking_config = ThinkingConfig(thinking_level=self.thinking_level)  # type: ignore

                # Run sync API call in executor
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(  # type: ignore
                        model=self.model_name,
                        contents=prompt,
                        config=config,
                    ),
                )

                # Extract text from response
                text = response.text
                if text is None:
                    raise ProviderUnavailableError("Gemini returned empty response")

                # Calculate completion tokens
                completion_tokens = int(len(text.split()) / 0.75)
                duration = time.time() - start_time

                # Record metrics
                metrics.record_llm_request(
                    model=self.model_name,
                    status="success",
                    duration=duration,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )

                # Add trace attributes
                span.set_attribute("success", True)
                span.set_attribute("response_length", len(text))
                span.set_attribute("llm.prompt_tokens", prompt_tokens)
                span.set_attribute("llm.completion_tokens", completion_tokens)
                span.set_attribute("llm.total_tokens", prompt_tokens + completion_tokens)

                logger.info(f"Gemini generated {len(text)} characters")
                self.set_status(ProviderStatus.AVAILABLE)
                return text

            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e).lower()

                # Record error metrics
                metrics.record_llm_request(
                    model=self.model_name,
                    status="error",
                    duration=duration,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=0,
                )

                # Add error to span
                span.set_attribute("success", False)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.record_exception(e)

                # Check for rate limit errors
                if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
                    logger.warning(f"Gemini rate limit hit: {e}")
                    self.set_status(ProviderStatus.RATE_LIMITED, str(e))
                    raise RateLimitError(f"Gemini rate limit exceeded: {e}", retry_after=60)

                # Check for authentication errors
                if "401" in error_msg or "unauthorized" in error_msg or "api key" in error_msg:
                    logger.error(f"Gemini authentication error: {e}")
                    self.set_status(ProviderStatus.ERROR, str(e))
                    raise ProviderUnavailableError(f"Gemini authentication failed: {e}")

                # Other errors
                logger.error(f"Gemini generation error: {e}")
                self.set_status(ProviderStatus.ERROR, str(e))
                raise ProviderUnavailableError(f"Gemini error: {e}")

    async def generate_chat(
        self, messages: List[Dict[str, str]], max_tokens: int, temperature: float, **kwargs
    ) -> str:
        """
        Generate response from conversation history.

        Gemini doesn't use the same message format as OpenAI,
        so we'll convert the messages to a single prompt.

        Args:
            messages: List of messages with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Temperature for randomness
            **kwargs: Additional parameters

        Returns:
            Generated response text
        """
        # Convert messages to Gemini format
        prompt = self._format_messages_as_prompt(messages)
        return await self.generate_narration(prompt, max_tokens, temperature, **kwargs)

    async def is_available(self) -> bool:
        """
        Check if Gemini is available.

        Returns:
            True if provider can accept requests
        """
        if not self.client or not self.api_key:
            self.set_status(ProviderStatus.UNAVAILABLE, "Client not initialized")
            return False

        # If we're rate limited, check if enough time has passed
        if self._status == ProviderStatus.RATE_LIMITED:
            # For now, assume we need to wait before retrying
            # In production, implement proper backoff logic
            return False

        if self._status == ProviderStatus.ERROR:
            # Don't retry if there's a configuration error
            return False

        return True

    def _format_messages_as_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Convert chat messages to a single prompt for Gemini.

        Gemini works best with a single consolidated prompt rather than
        separate system/user/assistant messages.

        Args:
            messages: List of messages with 'role' and 'content'

        Returns:
            Formatted prompt string
        """
        formatted = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                formatted.append(f"SYSTEM INSTRUCTIONS:\n{content}\n")
            elif role == "user":
                formatted.append(f"USER: {content}")
            elif role == "assistant":
                formatted.append(f"ASSISTANT: {content}")

        return "\n\n".join(formatted)
