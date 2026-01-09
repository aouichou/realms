"""Memory capture hooks for automatic event recording"""

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

            logger.info(f"Captured combat memory for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to capture combat memory: {e}")

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

            logger.debug(f"Captured dialogue memory for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to capture dialogue memory: {e}")

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

            logger.info(f"Captured discovery memory for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to capture discovery memory: {e}")

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

            logger.info(f"Captured quest memory for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to capture quest memory: {e}")

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

            logger.info(f"Captured decision memory for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to capture decision memory: {e}")

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

            logger.info(f"Captured NPC interaction memory for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to capture NPC interaction memory: {e}")

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

            logger.debug(f"Captured location memory for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to capture location memory: {e}")

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

            logger.debug(f"Captured loot memory for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to capture loot memory: {e}")
