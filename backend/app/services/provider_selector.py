"""
Provider selector service with automatic fallback logic.

Manages multiple AI providers, automatically selecting the best available
provider and falling back to alternatives when rate limits or errors occur.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_provider import (
    AIProvider,
    ProviderUnavailableError,
    RateLimitError,
)
from app.services.context_transfer import ContextTransferService

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
        self.last_provider_name: Optional[str] = None
        self.provider_stats: Dict[str, Dict[str, Any]] = {}
        self.context_transfer_service = ContextTransferService()

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
            "switches_to": 0,
            "context_transfers": 0,
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
                # Track provider switch
                if self.current_provider != provider:
                    old_provider = self.current_provider.name if self.current_provider else None
                    logger.info(f"Switching provider: {old_provider} -> {provider.name}")
                    self.last_provider_name = old_provider
                    self.provider_stats[provider.name]["switches_to"] += 1

                self.current_provider = provider
                return provider

        # No providers available
        status_info = ", ".join([f"{p.name}: {p._status.value}" for p in self.providers])
        raise ProviderUnavailableError(f"No AI providers available. Status: {status_info}")

    async def generate_narration(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        db: Optional[AsyncSession] = None,
        session_id: Optional[uuid.UUID] = None,
        character=None,
        **kwargs,
    ) -> str:
        """
        Generate narration using the best available provider.

        Automatically tries fallback providers if primary fails.
        Transfers context when switching providers.

        Args:
            prompt: The prompt text
            max_tokens: Maximum tokens to generate
            temperature: Temperature for randomness
            db: Database session (optional, for context transfer)
            session_id: Game session ID (optional, for context transfer)
            character: Character object (optional, for context transfer)
            **kwargs: Additional parameters

        Returns:
            Generated narration text

        Raises:
            ProviderUnavailableError: If all providers fail
        """
        # Get selected provider
        selected_provider = await self.select_provider()

        # Check if provider switched and context transfer is needed
        context_prefix = ""
        if (
            self.last_provider_name is not None
            and selected_provider.name != self.last_provider_name
            and db is not None
            and session_id is not None
            and character is not None
        ):
            # Provider switched - generate context transfer
            try:
                logger.info(
                    f"Provider switched ({self.last_provider_name} -> {selected_provider.name}), "
                    "generating context transfer..."
                )
                context_summary = await self.context_transfer_service.generate_session_summary(
                    db=db,
                    session_id=session_id,
                    character=character,
                )
                context_prefix = context_summary + "\n\n"
                self.provider_stats[selected_provider.name]["context_transfers"] += 1
                logger.info(f"Context transfer generated ({len(context_prefix)} chars)")
            except Exception as e:
                logger.error(f"Failed to generate context transfer: {e}")
                # Continue without context transfer rather than failing

        # Prepend context if available
        enhanced_prompt = context_prefix + prompt

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
                    prompt=enhanced_prompt, max_tokens=max_tokens, temperature=temperature, **kwargs
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
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        db: Optional[AsyncSession] = None,
        session_id: Optional[uuid.UUID] = None,
        character=None,
        **kwargs,
    ) -> str:
        """
        Generate chat response using the best available provider.

        Transfers context when switching providers.

        Args:
            messages: Conversation history
            max_tokens: Maximum tokens to generate
            temperature: Temperature for randomness
            db: Database session (optional, for context transfer)
            session_id: Game session ID (optional, for context transfer)
            character: Character object (optional, for context transfer)
            **kwargs: Additional parameters

        Returns:
            Generated response text
        """
        # Get selected provider
        selected_provider = await self.select_provider()

        # Check if provider switched and context transfer is needed
        if (
            self.last_provider_name is not None
            and selected_provider.name != self.last_provider_name
            and db is not None
            and session_id is not None
            and character is not None
        ):
            # Provider switched - inject context into messages
            try:
                logger.info(
                    f"Provider switched ({self.last_provider_name} -> {selected_provider.name}), "
                    "generating context transfer..."
                )
                context_summary = await self.context_transfer_service.generate_session_summary(
                    db=db,
                    session_id=session_id,
                    character=character,
                )

                # Inject context as system message if messages exist
                if messages:
                    # Compress conversation history
                    compressed_messages = (
                        await self.context_transfer_service.compress_conversation_history(
                            messages=messages,
                            max_messages=10,
                        )
                    )

                    # Add context transfer message
                    context_msg = {
                        "role": "system",
                        "content": self.context_transfer_service.format_context_transfer(
                            session_summary=context_summary,
                            recent_messages=compressed_messages,
                        ),
                    }

                    # Insert after system message if exists, otherwise prepend
                    if compressed_messages and compressed_messages[0].get("role") == "system":
                        messages = [compressed_messages[0], context_msg] + compressed_messages[1:]
                    else:
                        messages = [context_msg] + compressed_messages

                self.provider_stats[selected_provider.name]["context_transfers"] += 1
                logger.info("Context transfer injected into conversation")
            except Exception as e:
                logger.error(f"Failed to generate context transfer: {e}")
                # Continue without context transfer

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
