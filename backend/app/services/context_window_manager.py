"""
Context Window Management Service
Manages context size to stay within model token limits
"""

from typing import Dict, List, Optional, Tuple

import tiktoken

from app.observability.logger import get_logger

logger = get_logger(__name__)


class ContextWindowManager:
    """
    Manages conversation context to stay within token limits

    Strategies:
    - Count tokens accurately using tiktoken
    - Prune older messages when approaching limit
    - Preserve: system prompt, character context, recent messages, summaries
    - Drop: older full conversation messages
    """

    # Mistral models use cl100k_base encoding (same as GPT-4)
    # Reference: https://github.com/mistralai/mistral-common
    ENCODING_NAME = "cl100k_base"

    # Context limits (conservative estimates)
    # Mistral Large: 32k tokens
    # Mistral Small: 32k tokens
    # Leave buffer for response generation
    MAX_CONTEXT_TOKENS = 28000  # 4k buffer for response
    MAX_RESPONSE_TOKENS = 2048

    def __init__(self):
        """Initialize context window manager"""
        try:
            self.encoder = tiktoken.get_encoding(self.ENCODING_NAME)
            logger.info("Initialized context window manager with %s encoding", self.ENCODING_NAME)
        except Exception as e:
            logger.warning("Failed to load tiktoken encoder: %s. Using fallback counting.", e)
            self.encoder = None

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text

        Args:
            text: Text to count

        Returns:
            Token count
        """
        if not text:
            return 0

        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception as e:
                logger.warning("Token counting failed: %s. Using fallback.", e)

        # Fallback: rough estimate (1 token ≈ 4 characters)
        return len(text) // 4

    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Count total tokens in message list

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Total token count
        """
        total = 0

        for msg in messages:
            # Count role
            total += self.count_tokens(msg.get("role", ""))
            # Count content
            total += self.count_tokens(msg.get("content", ""))
            # Add overhead per message (formatting, delimiters)
            total += 4

        return total

    def prune_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        keep_recent: int = 3,
    ) -> Tuple[List[Dict[str, str]], int]:
        """
        Prune messages to fit within token limit

        Strategy:
        1. Always keep system messages (index 0, 1, 2 usually)
        2. Always keep last N recent messages
        3. Drop messages from middle if over limit

        Args:
            messages: Full message list
            max_tokens: Maximum tokens (defaults to MAX_CONTEXT_TOKENS)
            keep_recent: Number of recent messages to always keep

        Returns:
            Tuple of (pruned_messages, tokens_removed)
        """
        if not messages:
            return [], 0

        max_tokens = max_tokens or self.MAX_CONTEXT_TOKENS
        current_tokens = self.count_messages_tokens(messages)

        if current_tokens <= max_tokens:
            logger.debug("Context within limits: %d/%d tokens", current_tokens, max_tokens)
            return messages, 0

        logger.info("Context exceeds limit: %d/%d tokens. Pruning...", current_tokens, max_tokens)

        # Identify system messages (usually first 1-3 messages)
        system_count = 0
        for msg in messages:
            if msg.get("role") == "system":
                system_count += 1
            else:
                break

        # Split messages: system | middle | recent
        system_messages = messages[:system_count]
        middle_messages = (
            messages[system_count:-keep_recent]
            if len(messages) > system_count + keep_recent
            else []
        )
        recent_messages = messages[-keep_recent:] if keep_recent > 0 else []

        # Calculate tokens for must-keep sections
        system_tokens = self.count_messages_tokens(system_messages)
        recent_tokens = self.count_messages_tokens(recent_messages)
        reserved_tokens = system_tokens + recent_tokens

        if reserved_tokens >= max_tokens:
            logger.warning(
                "System + recent messages exceed limit! (%d/%d tokens)",
                reserved_tokens,
                max_tokens,
            )
            # Emergency: keep only system and most recent message
            return system_messages + [messages[-1]], current_tokens - self.count_messages_tokens(
                system_messages + [messages[-1]]
            )

        # Tokens available for middle messages
        available_tokens = max_tokens - reserved_tokens

        # Add middle messages until we hit limit (FIFO: keep newer middle messages)
        kept_middle = []
        middle_tokens = 0

        for msg in reversed(middle_messages):
            msg_tokens = self.count_messages_tokens([msg])
            if middle_tokens + msg_tokens <= available_tokens:
                kept_middle.insert(0, msg)
                middle_tokens += msg_tokens
            else:
                # No more room
                break

        # Reconstruct message list
        pruned_messages = system_messages + kept_middle + recent_messages
        pruned_tokens = self.count_messages_tokens(pruned_messages)
        tokens_removed = current_tokens - pruned_tokens

        logger.info(
            "Pruned %d messages (%d tokens removed). New total: %d/%d tokens",
            len(messages) - len(pruned_messages),
            tokens_removed,
            pruned_tokens,
            max_tokens,
        )

        return pruned_messages, tokens_removed

    def get_context_stats(self, messages: List[Dict[str, str]]) -> Dict[str, int]:
        """
        Get statistics about current context

        Args:
            messages: Message list

        Returns:
            Dict with token counts and limits
        """
        total_tokens = self.count_messages_tokens(messages)
        remaining = self.MAX_CONTEXT_TOKENS - total_tokens
        usage_percent = (total_tokens / self.MAX_CONTEXT_TOKENS) * 100

        return {
            "total_tokens": total_tokens,
            "max_tokens": self.MAX_CONTEXT_TOKENS,
            "remaining_tokens": remaining,
            "usage_percent": round(usage_percent, 1),
            "message_count": len(messages),
            "system_message_count": sum(1 for m in messages if m.get("role") == "system"),
            "is_over_limit": total_tokens > self.MAX_CONTEXT_TOKENS,
        }


# Singleton instance
_context_manager = None


def get_context_manager() -> ContextWindowManager:
    """Get singleton context window manager instance"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextWindowManager()
    return _context_manager
