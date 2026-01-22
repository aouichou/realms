"""Memory capture hooks for automatic event recording"""

import re
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventType
from app.observability.logger import get_logger
from app.services.memory_service import MemoryService

logger = get_logger(__name__)


class MemoryCaptureService:
    """Service for automatically capturing game events as memories"""

    @staticmethod
    async def capture_combat_event(
        db: AsyncSession,
        session_id: UUID,
        combatant_names: List[str],
        outcome: str,
        details: str,
        importance: Optional[int] = None,
    ):
        """Capture combat event

        Args:
            db: Database session
            session_id: Game session ID
            combatant_names: Names of combatants
            outcome: Combat outcome (victory/defeat/flee)
            details: Full combat description
            importance: Optional importance override (auto-calculated if None)
        """
        try:
            content = f"Combat: {details}\nOutcome: {outcome}"

            # Auto-calculate importance if not provided
            if importance is None:
                # Boss fights, defeats are more important
                if "boss" in details.lower() or "defeat" in outcome.lower():
                    importance = 9
                elif "victory" in outcome.lower():
                    importance = 7
                else:
                    importance = 6

            await MemoryService.store_memory(
                db=db,
                session_id=session_id,
                event_type=EventType.COMBAT,
                content=content,
                importance=importance,
                npcs_involved=combatant_names,
            )

            logger.info("Captured combat memory for session %s", session_id)

        except Exception as e:
            logger.error("Failed to capture combat memory: %s", e)

    @staticmethod
    async def capture_dialogue(
        db: AsyncSession,
        session_id: UUID,
        npc_name: str,
        dialogue: str,
        importance: Optional[int] = None,
    ):
        """Capture NPC dialogue

        Args:
            db: Database session
            session_id: Game session ID
            npc_name: Name of NPC
            dialogue: Dialogue content
            importance: Optional importance override
        """
        try:
            content = f"Conversation with {npc_name}: {dialogue}"

            if importance is None:
                # Quest-related dialogue is more important
                if any(
                    word in dialogue.lower()
                    for word in ["quest", "task", "mission", "important", "secret"]
                ):
                    importance = 6
                else:
                    importance = 4

            await MemoryService.store_memory(
                db=db,
                session_id=session_id,
                event_type=EventType.DIALOGUE,
                content=content,
                importance=importance,
                npcs_involved=[npc_name],
            )

            logger.debug("Captured dialogue memory for session %s", session_id)

        except Exception as e:
            logger.error("Failed to capture dialogue memory: %s", e)

    @staticmethod
    async def capture_summary(
        db: AsyncSession,
        session_id: UUID,
        summary: str,
        message_count: int,
        importance: Optional[int] = None,
    ):
        """Capture conversation summary as memory (GAME-DESIGN.md: Auto-Summarization)

        Stores AI-generated summary with vector embedding every 10+ messages.
        Extracts and tags NPCs, locations, and items from the summary.

        Args:
            db: Database session
            session_id: Game session ID
            summary: AI-generated summary text
            message_count: Number of messages summarized
            importance: Optional importance override (default: 8 for summaries)
        """
        try:
            # Extract entities from summary
            npcs = MemoryCaptureService._extract_npcs(summary)
            locations = MemoryCaptureService._extract_locations(summary)
            items = MemoryCaptureService._extract_items(summary)

            # Summaries are important context
            if importance is None:
                importance = 8

            content = f"Summary of {message_count} messages: {summary}"

            await MemoryService.store_memory(
                db=db,
                session_id=session_id,
                event_type=EventType.SUMMARY,
                content=content,
                importance=importance,
                tags=["summary", f"messages_{message_count}"],
                npcs_involved=npcs,
                locations=locations,
                items_involved=items,
            )

            logger.info(
                "Captured summary memory for session %s (entities: %d NPCs, %d locations, %d items)",
                session_id,
                len(npcs),
                len(locations),
                len(items),
            )

        except Exception as e:
            logger.error("Failed to capture summary memory: %s", e)

    @staticmethod
    def _extract_npcs(text: str) -> List[str]:
        """Extract NPC names from text using heuristics

        Args:
            text: Text to analyze

        Returns:
            List of potential NPC names
        """
        npcs = []

        # Pattern 1: "NPC_NAME said/asked/told/replied"
        dialogue_pattern = r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(?:said|asked|told|replied|mentioned|explained|warned)"
        npcs.extend(re.findall(dialogue_pattern, text))

        # Pattern 2: "met NPC_NAME" or "spoke with NPC_NAME"
        meeting_pattern = (
            r"(?:met|spoke with|talked to|encountered)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)"
        )
        npcs.extend(re.findall(meeting_pattern, text))

        # Pattern 3: Common NPC titles
        title_pattern = r"(?:the\s+)?([A-Z][a-z]+)\s+(?:Mayor|Captain|Guard|Merchant|Innkeeper|Blacksmith|Priest|Wizard)"
        npcs.extend(re.findall(title_pattern, text))

        # Deduplicate and limit
        unique_npcs = list(dict.fromkeys(npcs))  # Preserve order
        return unique_npcs[:10]  # Max 10 NPCs

    @staticmethod
    def _extract_locations(text: str) -> List[str]:
        """Extract location names from text

        Args:
            text: Text to analyze

        Returns:
            List of location names
        """
        locations = []

        # Pattern 1: "in/at/to LOCATION_NAME"
        location_pattern = r"(?:in|at|to|from|entered|left|arrived at)\s+(?:the\s+)?([A-Z][a-z]+(?:\s[A-Z][a-z]+)?(?:\s[A-Z][a-z]+)?)"
        locations.extend(re.findall(location_pattern, text))

        # Pattern 2: Common location words
        place_pattern = r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(?:Cave|Forest|Castle|Village|Town|City|Temple|Tavern|Inn|Mountain|River)"
        locations.extend(re.findall(place_pattern, text))

        # Deduplicate and limit
        unique_locations = list(dict.fromkeys(locations))
        return unique_locations[:8]  # Max 8 locations

    @staticmethod
    def _extract_items(text: str) -> List[str]:
        """Extract item names from text

        Args:
            text: Text to analyze

        Returns:
            List of item names
        """
        items = []

        # Pattern 1: "found/acquired/obtained ITEM"
        acquisition_pattern = r"(?:found|acquired|obtained|received|picked up|looted)\s+(?:a|an|the)?\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)"
        items.extend(re.findall(acquisition_pattern, text))

        # Pattern 2: Common item types
        item_pattern = r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(?:Sword|Shield|Potion|Scroll|Ring|Amulet|Key|Map|Book|Gem)"
        items.extend(re.findall(item_pattern, text))

        # Deduplicate and limit
        unique_items = list(dict.fromkeys(items))
        return unique_items[:10]  # Max 10 items

    @staticmethod
    async def capture_discovery(
        db: AsyncSession,
        session_id: UUID,
        discovery_type: str,
        details: str,
        location: Optional[str] = None,
        items: Optional[List[str]] = None,
        importance: Optional[int] = None,
    ):
        """Capture discovery event

        Args:
            db: Database session
            session_id: Game session ID
            discovery_type: Type of discovery (treasure, secret, clue, etc.)
            details: Discovery description
            location: Location of discovery
            items: Items discovered
            importance: Optional importance override
        """
        try:
            content = f"Discovery ({discovery_type}): {details}"

            if importance is None:
                # Legendary items, major secrets are very important
                if "legendary" in details.lower() or "secret" in discovery_type.lower():
                    importance = 8
                elif "treasure" in discovery_type.lower():
                    importance = 7
                else:
                    importance = 6

            await MemoryService.store_memory(
                db=db,
                session_id=session_id,
                event_type=EventType.DISCOVERY,
                content=content,
                importance=importance,
                locations=[location] if location else None,
                items_involved=items,
            )

            logger.info("Captured discovery memory for session %s", session_id)

        except Exception as e:
            logger.error("Failed to capture discovery memory: %s", e)

    @staticmethod
    async def capture_quest_milestone(
        db: AsyncSession,
        session_id: UUID,
        quest_title: str,
        milestone: str,
        details: str,
        importance: int = 8,
    ):
        """Capture quest milestone

        Args:
            db: Database session
            session_id: Game session ID
            quest_title: Quest title
            milestone: Milestone type (started, completed, failed)
            details: Milestone details
            importance: Importance (default 8 for quests)
        """
        try:
            content = f"Quest '{quest_title}' - {milestone}: {details}"

            await MemoryService.store_memory(
                db=db,
                session_id=session_id,
                event_type=EventType.QUEST,
                content=content,
                importance=importance,
                tags=[quest_title, milestone],
            )

            logger.info("Captured quest memory for session %s", session_id)

        except Exception as e:
            logger.error("Failed to capture quest memory: %s", e)

    @staticmethod
    async def capture_decision(
        db: AsyncSession,
        session_id: UUID,
        decision: str,
        consequences: Optional[str] = None,
        importance: int = 7,
    ):
        """Capture major player decision

        Args:
            db: Database session
            session_id: Game session ID
            decision: Decision made
            consequences: Consequences of decision
            importance: Importance (default 7)
        """
        try:
            content = f"Decision: {decision}"
            if consequences:
                content += f"\nConsequences: {consequences}"

            await MemoryService.store_memory(
                db=db,
                session_id=session_id,
                event_type=EventType.DECISION,
                content=content,
                importance=importance,
            )

            logger.info("Captured decision memory for session %s", session_id)

        except Exception as e:
            logger.error("Failed to capture decision memory: %s", e)

    @staticmethod
    async def capture_npc_interaction(
        db: AsyncSession,
        session_id: UUID,
        npc_name: str,
        interaction_type: str,
        details: str,
        importance: Optional[int] = None,
    ):
        """Capture NPC interaction

        Args:
            db: Database session
            session_id: Game session ID
            npc_name: NPC name
            interaction_type: Type of interaction (met, befriended, betrayed, etc.)
            details: Interaction details
            importance: Optional importance override
        """
        try:
            content = f"{interaction_type} {npc_name}: {details}"

            if importance is None:
                # Betrayals, deaths are very important
                if interaction_type in ["betrayed", "killed", "saved"]:
                    importance = 8
                elif interaction_type in ["met", "befriended"]:
                    importance = 5
                else:
                    importance = 6

            await MemoryService.store_memory(
                db=db,
                session_id=session_id,
                event_type=EventType.NPC_INTERACTION,
                content=content,
                importance=importance,
                npcs_involved=[npc_name],
            )

            logger.info("Captured NPC interaction memory for session %s", session_id)

        except Exception as e:
            logger.error("Failed to capture NPC interaction memory: %s", e)

    @staticmethod
    async def capture_location_visit(
        db: AsyncSession,
        session_id: UUID,
        location_name: str,
        details: str,
        importance: int = 5,
    ):
        """Capture location visit

        Args:
            db: Database session
            session_id: Game session ID
            location_name: Location name
            details: Visit details
            importance: Importance (default 5)
        """
        try:
            content = f"Visited {location_name}: {details}"

            await MemoryService.store_memory(
                db=db,
                session_id=session_id,
                event_type=EventType.LOCATION,
                content=content,
                importance=importance,
                locations=[location_name],
            )

            logger.debug("Captured location memory for session %s", session_id)

        except Exception as e:
            logger.error("Failed to capture location memory: %s", e)

    @staticmethod
    async def capture_loot(
        db: AsyncSession,
        session_id: UUID,
        items: List[str],
        source: str,
        importance: Optional[int] = None,
    ):
        """Capture loot acquisition

        Args:
            db: Database session
            session_id: Game session ID
            items: Items acquired
            source: Source of loot
            importance: Optional importance override
        """
        try:
            content = f"Acquired loot from {source}: {', '.join(items)}"

            if importance is None:
                # Legendary/rare items are more important
                if any("legendary" in item.lower() or "rare" in item.lower() for item in items):
                    importance = 7
                else:
                    importance = 5

            await MemoryService.store_memory(
                db=db,
                session_id=session_id,
                event_type=EventType.LOOT,
                content=content,
                importance=importance,
                items_involved=items,
            )

            logger.debug("Captured loot memory for session %s", session_id)

        except Exception as e:
            logger.error("Failed to capture loot memory: %s", e)

    @staticmethod
    async def capture_spell_cast(
        db: AsyncSession,
        session_id: UUID,
        spell_name: str,
        spell_level: int,
        target: Optional[str] = None,
        outcome: Optional[str] = None,
        importance: Optional[int] = None,
    ):
        """Capture spell casting event

        Args:
            db: Database session
            session_id: Game session ID
            spell_name: Name of spell cast
            spell_level: Level of spell
            target: Optional target name
            outcome: Optional outcome description
            importance: Optional importance override
        """
        try:
            content = f"Cast {spell_name} (level {spell_level})"
            if target:
                content += f" on {target}"
            if outcome:
                content += f": {outcome}"

            if importance is None:
                # Higher level spells are more important
                if spell_level >= 7:
                    importance = 8
                elif spell_level >= 5:
                    importance = 7
                elif spell_level >= 3:
                    importance = 6
                else:
                    importance = 5

            await MemoryService.store_memory(
                db=db,
                session_id=session_id,
                event_type=EventType.OTHER,
                content=content,
                importance=importance,
            )

            logger.debug("Captured spell cast memory for session %s", session_id)

        except Exception as e:
            logger.error("Failed to capture spell cast memory: %s", e)
