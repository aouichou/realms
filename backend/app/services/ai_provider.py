"""
Abstract base class for AI provider implementations.

This module defines the interface that all AI providers must implement,
enabling hot-swapping between different AI services (Mistral, Gemini, OpenAI, etc.)
while maintaining consistent behavior.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional


class ProviderStatus(Enum):
    """Provider availability status."""

    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class AIProvider(ABC):
    """
    Abstract base class for AI providers.

    All AI provider implementations must inherit from this class
    and implement the required methods.
    """

    def __init__(self, name: str, priority: int):
        """
        Initialize AI provider.

        Args:
            name: Provider name (e.g., "mistral", "gemini")
            priority: Priority order (lower = higher priority)
        """
        self.name = name
        self.priority = priority
        self._status = ProviderStatus.AVAILABLE
        self._last_error: Optional[str] = None

    @abstractmethod
    async def generate_narration(
        self, prompt: str, max_tokens: int, temperature: float, **kwargs
    ) -> str:
        """
        Generate narration from a prompt.

        Args:
            prompt: The prompt text to generate from
            max_tokens: Maximum tokens to generate
            temperature: Temperature for randomness (0.0-1.0)
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated narration text

        Raises:
            ProviderUnavailableError: If provider is unavailable
            RateLimitError: If rate limit is exceeded
        """
        pass

    @abstractmethod
    async def generate_chat(
        self, messages: List[Dict[str, str]], max_tokens: int, temperature: float, **kwargs
    ) -> str:
        """
        Generate response from a conversation history.

        Args:
            messages: List of messages with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Temperature for randomness (0.0-1.0)
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated response text

        Raises:
            ProviderUnavailableError: If provider is unavailable
            RateLimitError: If rate limit is exceeded
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if provider is currently available.

        Returns:
            True if provider can accept requests, False otherwise
        """
        pass

    async def get_status(self) -> ProviderStatus:
        """
        Get current provider status.

        Returns:
            Current status enum value
        """
        return self._status

    def set_status(self, status: ProviderStatus, error: Optional[str] = None):
        """
        Update provider status.

        Args:
            status: New status
            error: Optional error message
        """
        self._status = status
        self._last_error = error

    def get_last_error(self) -> Optional[str]:
        """Get last error message."""
        return self._last_error

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', priority={self.priority}, status={self._status.value})"


class ProviderUnavailableError(Exception):
    """Raised when a provider is unavailable."""

    pass


class RateLimitError(Exception):
    """Raised when a provider hits rate limits."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after
