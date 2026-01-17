"""
Context Transfer Service

Generates adventure summaries and compresses context for transferring
between AI providers to maintain story continuity.
"""

import uuid
from typing import Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Character, GameSession
from app.observability.logger import get_logger
from app.services.memory_service import MemoryService

logger = get_logger(__name__)


class ContextTransferService:
    """
    Service for generating context summaries when switching AI providers.

    Compresses game history into a concise format that preserves:
    - Character details and current state
    - Recent events and decisions
    - Active NPCs and their relationships
    - Current location and quest objectives
    """

    @staticmethod
    async def generate_session_summary(
        db: AsyncSession,
        session_id: uuid.UUID,
        character: Character,
        max_memories: int = 10,
    ) -> str:
        """
        Generate a comprehensive session summary for context transfer.

        Args:
            db: Database session
            session_id: Game session ID
            character: Character object
            max_memories: Maximum number of memories to include

        Returns:
            Formatted context summary string
        """
        try:
            # Retrieve recent memories
            memories = await MemoryService.get_recent_memories(
                db=db,
                session_id=session_id,
                limit=max_memories,
            )

            # Get session info
            from sqlalchemy import select

            stmt = select(GameSession).where(GameSession.id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()

            # Build comprehensive summary
            summary = "ADVENTURE SUMMARY:\n"
            summary += "You are continuing a D&D adventure in progress. Here's what has happened so far:\n\n"

            # Character details
            summary += await ContextTransferService._format_character_details(character)
            summary += "\n"

            # Session context
            if session:
                summary += await ContextTransferService._format_session_context(session)
                summary += "\n"

            # Recent events
            if memories:
                summary += await ContextTransferService._format_recent_events(memories)
                summary += "\n"

            summary += "\nCONTINUE THE ADVENTURE as Dungeon Master, maintaining the established tone and story...\n"

            logger.info(
                f"Generated context transfer summary for session {session_id} ({len(summary)} chars)"
            )
            return summary

        except Exception as e:
            logger.error(f"Error generating session summary: {e}")
            return "ADVENTURE SUMMARY: Continue the D&D adventure in progress."

    @staticmethod
    async def _format_character_details(character: Character) -> str:
        """Format character details for context transfer"""
        details = f"CHARACTER: {character.name}, Level {character.level} {character.race} {character.class_name}\n"

        # Personality
        if character.personality:
            details += f"- Personality: {character.personality}\n"

        # Current state
        details += f"- Current HP: {character.current_hp}/{character.max_hp}\n"

        # Ability scores
        details += "- Abilities: "
        abilities = []
        if character.strength:
            abilities.append(f"STR {character.strength}")
        if character.dexterity:
            abilities.append(f"DEX {character.dexterity}")
        if character.constitution:
            abilities.append(f"CON {character.constitution}")
        if character.intelligence:
            abilities.append(f"INT {character.intelligence}")
        if character.wisdom:
            abilities.append(f"WIS {character.wisdom}")
        if character.charisma:
            abilities.append(f"CHA {character.charisma}")
        details += ", ".join(abilities) + "\n"

        return details

    @staticmethod
    async def _format_session_context(session: GameSession) -> str:
        """Format session context for context transfer"""
        context = "CURRENT SESSION:\n"

        if session.current_location:
            context += f"- Location: {session.current_location}\n"

        # Add any session-specific context here
        # Quest objectives, active NPCs, etc.

        return context

    @staticmethod
    async def _format_recent_events(memories: List) -> str:
        """Format recent events from memories"""
        events = "RECENT EVENTS:\n"

        for memory in reversed(memories):  # Chronological order
            # Format based on event type
            if memory.event_type.value in ["combat", "npc_interaction", "quest_update"]:
                events += f"- {memory.content}\n"

            # Include NPC interactions
            if memory.npcs_involved:
                npc_names = ", ".join(memory.npcs_involved)
                events += f"  (NPCs: {npc_names})\n"

        return events

    @staticmethod
    async def compress_conversation_history(
        messages: List[Dict[str, str]],
        max_messages: int = 10,
    ) -> List[Dict[str, str]]:
        """
        Compress conversation history to recent turns.

        Args:
            messages: Full conversation history
            max_messages: Maximum messages to keep

        Returns:
            Compressed message list
        """
        if len(messages) <= max_messages:
            return messages

        # Keep system message (first) and recent messages
        if messages and messages[0].get("role") == "system":
            return [messages[0]] + messages[-(max_messages - 1) :]
        else:
            return messages[-max_messages:]

    @staticmethod
    def format_context_transfer(
        session_summary: str,
        recent_messages: List[Dict[str, str]],
    ) -> str:
        """
        Format complete context for transfer to new provider.

        Args:
            session_summary: Session summary from generate_session_summary
            recent_messages: Recent conversation history

        Returns:
            Formatted context string
        """
        transfer_context = session_summary + "\n"
        transfer_context += "CONVERSATION CONTEXT (last few turns):\n"

        # Format recent messages
        for msg in recent_messages[-3:]:  # Last 3 turns
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                transfer_context += f"PLAYER: {content}\n"
            elif role == "assistant":
                transfer_context += f"DM: {content[:200]}...\n"  # Truncate long responses

        return transfer_context
