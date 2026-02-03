"""
Token Counter Service
Tracks and manages token usage for context window management
"""

from typing import Dict, List

from app.observability.logger import get_logger

logger = get_logger(__name__)


class TokenCounter:
    """Track token usage for context window management"""

    # Approximate tokens per character (Mistral uses BPE)
    # This is a rough estimate: actual tokenization varies by content
    CHARS_PER_TOKEN = 4

    @classmethod
    def count_tokens(cls, text: str) -> int:
        """
        Estimate token count from text

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return len(text) // cls.CHARS_PER_TOKEN

    @classmethod
    def count_message_tokens(cls, messages: List[Dict]) -> int:
        """
        Count tokens in message list

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Total estimated token count
        """
        total = 0
        for msg in messages:
            # Count message content
            content = msg.get("content", "")
            total += cls.count_tokens(content)

            # Account for message formatting overhead
            # Each message has role, separators, etc.
            total += 4

        return total

    @classmethod
    def fits_in_context(cls, messages: List[Dict], max_tokens: int = 28000) -> bool:
        """
        Check if messages fit in context window

        Args:
            messages: List of messages
            max_tokens: Maximum allowed tokens (default 28000, leaving 4K for response)

        Returns:
            True if messages fit, False otherwise
        """
        token_count = cls.count_message_tokens(messages)
        return token_count < max_tokens

    @classmethod
    def truncate_to_fit(cls, messages: List[Dict], max_tokens: int = 28000) -> List[Dict]:
        """
        Remove oldest messages until fits in context window

        Strategy:
        - Always keep ALL system messages (they contain critical DM instructions)
        - Remove oldest user/assistant messages
        - Keep removing until under limit

        Args:
            messages: List of messages
            max_tokens: Maximum allowed tokens

        Returns:
            Truncated message list
        """
        if cls.fits_in_context(messages, max_tokens):
            return messages

        # Separate system messages from conversation messages
        system_messages = [m for m in messages if m.get("role") == "system"]
        conversation_messages = [m for m in messages if m.get("role") != "system"]

        # Start with all system messages (NEVER truncate these!)
        truncated = system_messages.copy()

        # Add conversation messages one by one until we hit the limit
        # Start from most recent and work backwards
        for msg in reversed(conversation_messages):
            test_messages = truncated + [msg]
            if cls.fits_in_context(test_messages, max_tokens):
                truncated.insert(len(system_messages), msg)
            else:
                # Log that we're dropping this message
                logger.warning(
                    "Truncated message to fit context window",
                    extra={
                        "extra_data": {
                            "removed_role": msg.get("role"),
                            "content_preview": msg.get("content", "")[:50],
                            "remaining_messages": len(truncated),
                            "estimated_tokens": cls.count_message_tokens(truncated),
                        }
                    },
                )

        return truncated

    @classmethod
    def get_token_stats(cls, messages: List[Dict]) -> Dict[str, int]:
        """
        Get detailed token statistics

        Args:
            messages: List of messages

        Returns:
            Dict with token counts and percentages
        """
        total_tokens = cls.count_message_tokens(messages)

        return {
            "total_tokens": total_tokens,
            "message_count": len(messages),
            "avg_tokens_per_message": total_tokens // len(messages) if messages else 0,
            "percent_of_4k_context": int((total_tokens / 4096) * 100),
            "percent_of_32k_context": int((total_tokens / 32768) * 100),
        }
