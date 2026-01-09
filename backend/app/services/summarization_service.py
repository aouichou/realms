"""
Message Summarization Service
Condenses conversation history to reduce token usage and prevent repetitive responses
"""

from typing import Dict, List, Optional

from app.services.mistral_client import get_mistral_client
from app.utils.logger import logger


class SummarizationService:
    """
    Service to summarize long conversation histories
    
    Uses Mistral to create concise summaries of past conversations,
    reducing token usage while maintaining context
    """

    SUMMARIZATION_PROMPT = """You are a helpful assistant that creates concise summaries of D&D game conversations.

Given a conversation between a player and a Dungeon Master, create a brief summary that captures:
- Key events and actions
- Important discoveries or revelations
- Combat outcomes
- NPC interactions
- Current quest status
- Character state changes (damage taken, items found, etc.)

Keep the summary under 200 words and focus on facts, not speculation.
Do not include conversational fluff or meta-commentary.

Format: Clear, chronological bullet points."""

    @staticmethod
    async def summarize_conversation(
        messages: List[Dict[str, str]],
        character_name: Optional[str] = None,
    ) -> str:
        """
        Summarize a list of conversation messages
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            character_name: Optional character name to personalize summary
            
        Returns:
            Concise summary string
            
        Raises:
            Exception: If summarization fails
        """
        try:
            if not messages:
                return "No conversation history yet."
                
            if len(messages) < 5:
                # Too short to summarize effectively
                return SummarizationService._format_messages_as_summary(messages)
            
            # Build conversation text
            conversation_text = "\n\n".join(
                [f"{msg['role'].upper()}: {msg['content']}" for msg in messages]
            )
            
            # Add character context if available
            context_prefix = ""
            if character_name:
                context_prefix = f"Character: {character_name}\n\n"
            
            # Create summarization request
            mistral_client = get_mistral_client()
            summary_messages = [
                {"role": "system", "content": SummarizationService.SUMMARIZATION_PROMPT},
                {
                    "role": "user",
                    "content": f"{context_prefix}CONVERSATION TO SUMMARIZE:\n\n{conversation_text}\n\nPlease provide a concise summary:",
                },
            ]
            
            logger.debug(f"Summarizing {len(messages)} messages...")
            
            response = await mistral_client.chat_completion(summary_messages)
            summary_content = response.choices[0].message.content
            summary = str(summary_content) if summary_content else "Unable to generate summary."
            
            logger.info(
                f"Summary generated: {len(messages)} messages -> {len(summary)} chars "
                f"(saved ~{len(conversation_text) - len(summary)} chars)"
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to summarize conversation: {e}")
            # Fallback to simple formatting
            return SummarizationService._format_messages_as_summary(messages[-5:])

    @staticmethod
    def _format_messages_as_summary(messages: List[Dict[str, str]]) -> str:
        """
        Fallback: Format messages as a simple text summary
        
        Args:
            messages: List of message dicts
            
        Returns:
            Simple formatted summary
        """
        if not messages:
            return "No conversation history."
            
        summary_parts = ["RECENT EVENTS:"]
        
        for msg in messages:
            role = "Player" if msg["role"] == "user" else "DM"
            content = msg["content"]
            
            # Truncate long messages
            if len(content) > 150:
                content = content[:147] + "..."
                
            summary_parts.append(f"- {role}: {content}")
            
        return "\n".join(summary_parts)

    @staticmethod
    def should_summarize(message_count: int, threshold: int = 10) -> bool:
        """
        Determine if conversation should be summarized
        
        Args:
            message_count: Number of messages in conversation
            threshold: Minimum messages before summarizing (default: 10)
            
        Returns:
            True if conversation should be summarized
        """
        return message_count >= threshold

    @staticmethod
    async def get_summarized_context(
        messages: List[Dict[str, str]],
        character_name: Optional[str] = None,
        keep_recent: int = 3,
    ) -> tuple[str, List[Dict[str, str]]]:
        """
        Get conversation context with summarization
        
        Returns summary of older messages + recent full messages
        
        Args:
            messages: Full conversation history
            character_name: Optional character name
            keep_recent: Number of recent messages to keep in full (default: 3)
            
        Returns:
            Tuple of (summary_text, recent_messages)
        """
        if len(messages) <= keep_recent + 2:
            # Not enough to summarize
            return "", messages
            
        # Split into older and recent
        older_messages = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]
        
        # Summarize older messages
        summary = await SummarizationService.summarize_conversation(
            older_messages, character_name
        )
        
        logger.debug(
            f"Context split: {len(older_messages)} messages summarized, "
            f"{len(recent_messages)} kept in full"
        )
        
        return summary, recent_messages
