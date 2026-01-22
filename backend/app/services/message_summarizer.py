"""
Message Summarizer Service
Summarizes conversation history to stay within token limits
"""

from typing import Dict, List

from app.observability.logger import get_logger
from app.services.provider_selector import provider_selector
from app.services.token_counter import TokenCounter

logger = get_logger(__name__)


class MessageSummarizer:
    """Summarize conversation history to stay within token limits"""

    # Threshold: start summarizing after this many messages
    SUMMARY_THRESHOLD = 20

    # Maximum tokens allowed before triggering summarization
    MAX_CONTEXT_TOKENS = 3000

    def __init__(self):
        """Initialize message summarizer"""
        self.provider = provider_selector
        self.token_counter = TokenCounter

    async def summarize_if_needed(
        self, messages: List[Dict], current_context: str = ""
    ) -> List[Dict]:
        """
        Summarize older messages if approaching token limit.

        Strategy:
        - Keep last 10 messages intact (recent context)
        - Summarize messages 1-10 (old context, skipping system message at 0)
        - Keep message 0 (initial system message)

        Args:
            messages: List of conversation messages
            current_context: Additional context to account for (game state, etc.)

        Returns:
            Original messages or summarized version if needed
        """
        # Don't summarize if below threshold
        if len(messages) < self.SUMMARY_THRESHOLD:
            return messages

        # Count total tokens
        total_tokens = self.token_counter.count_message_tokens(messages)
        context_tokens = self.token_counter.count_tokens(current_context)
        combined_tokens = total_tokens + context_tokens

        logger.info(
            f"Context check: {len(messages)} messages, "
            f"{total_tokens} msg tokens + {context_tokens} context tokens = {combined_tokens} total"
        )

        # Only summarize if approaching limit
        if combined_tokens < self.MAX_CONTEXT_TOKENS:
            return messages

        logger.info(
            f"Context window approaching limit ({combined_tokens}/{self.MAX_CONTEXT_TOKENS} tokens). "
            f"Summarizing old messages..."
        )

        # Summarize old messages (messages 1-10, keeping system message at 0)
        # If there are fewer than 11 messages, summarize what we can
        if len(messages) <= 11:
            # Not enough messages to split properly, just keep recent ones
            logger.warning("Not enough messages to summarize properly, truncating instead")
            return self.token_counter.truncate_to_fit(messages, self.MAX_CONTEXT_TOKENS)

        old_messages = messages[1:11]  # Messages 1-10
        recent_messages = messages[11:]  # Keep last 10+

        # Create summary of old messages
        summary = await self._create_summary(old_messages)

        # Build new message list
        summarized = [
            messages[0],  # Keep original system message
            {"role": "system", "content": f"[SUMMARY OF EARLIER EVENTS: {summary}]"},
            *recent_messages,
        ]

        new_token_count = self.token_counter.count_message_tokens(summarized)
        logger.info(
            f"Summarization complete: {len(messages)} messages → {len(summarized)} messages. "
            f"Tokens: {total_tokens} → {new_token_count} (saved {total_tokens - new_token_count})"
        )

        return summarized

    async def _create_summary(self, messages: List[Dict]) -> str:
        """
        Use AI to create concise summary of message history

        Args:
            messages: List of messages to summarize

        Returns:
            Concise summary text
        """
        # Format messages for summarization
        formatted = self._format_messages(messages)

        summary_prompt = f"""Summarize these D&D game events in 2-3 concise sentences.
Focus on: Key player decisions, NPCs encountered, locations visited, quests started or completed, significant outcomes.

{formatted}

Provide a brief narrative summary:"""

        try:
            # Use provider selector to generate summary
            summary = await self.provider.generate_chat(
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=150,  # Keep summary short
                temperature=0.3,  # More focused/deterministic
            )

            logger.info(
                f"Created summary of {len(messages)} messages",
                extra={"extra_data": {"summary_preview": summary[:100]}},
            )

            return summary.strip()

        except Exception as e:
            logger.error(f"Failed to create summary: {e}")
            # Fallback: simple concatenation of key content
            return self._fallback_summary(messages)

    def _format_messages(self, messages: List[Dict]) -> str:
        """
        Format message list for summarization

        Args:
            messages: List of messages

        Returns:
            Formatted string
        """
        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Skip system messages
            if role == "system":
                continue

            # Truncate very long messages
            if len(content) > 300:
                content = content[:297] + "..."

            # Format as dialogue
            if role == "user":
                formatted.append(f"Player: {content}")
            elif role == "assistant":
                formatted.append(f"DM: {content}")

        return "\n".join(formatted)

    def _fallback_summary(self, messages: List[Dict]) -> str:
        """
        Create simple fallback summary if AI summarization fails

        Args:
            messages: List of messages

        Returns:
            Basic summary
        """
        user_actions = []
        dm_responses = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")[:100]  # First 100 chars

            if role == "user":
                user_actions.append(content)
            elif role == "assistant":
                dm_responses.append(content)

        summary_parts = []
        if user_actions:
            summary_parts.append(f"Player took {len(user_actions)} actions")
        if dm_responses:
            summary_parts.append(f"DM provided {len(dm_responses)} responses")

        return " | ".join(summary_parts) if summary_parts else "Earlier conversation"
