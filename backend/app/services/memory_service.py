"""Memory service for storing and retrieving adventure memories"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdventureMemory, EventType
from app.services.embedding_service import get_embedding_service


class MemoryService:
    """Service for managing adventure memories with semantic search"""

    @staticmethod
    async def store_memory(
        db: AsyncSession,
        session_id: uuid.UUID,
        event_type: str,
        content: str,
        importance: int = 5,
        tags: Optional[List[str]] = None,
        npcs_involved: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        items_involved: Optional[List[str]] = None,
    ) -> AdventureMemory:
        """Store a new memory with embedding

        Args:
            db: Database session
            session_id: Game session ID
            event_type: Type of event
            content: Memory content/description
            importance: Importance score (1-10)
            tags: Optional tags
            npcs_involved: Optional NPC names/IDs (stored as strings in JSONB)
            locations: Optional location names
            items_involved: Optional item names

        Returns:
            Created memory object
        """
        # Generate embedding
        embedding_service = get_embedding_service()
        embedding = await embedding_service.generate_embedding(content)

        # Create memory
        memory = AdventureMemory(
            id=uuid.uuid4(),
            session_id=session_id,
            event_type=EventType(event_type),
            content=content,
            embedding=embedding if embedding else None,
            importance=importance,
            timestamp=datetime.utcnow(),
            tags=tags or [],
            npcs_involved=npcs_involved or [],
            locations=locations or [],
            items_involved=items_involved or [],
            created_at=datetime.utcnow(),
        )

        db.add(memory)
        await db.commit()
        await db.refresh(memory)

        return memory

    @staticmethod
    async def search_memories(
        db: AsyncSession,
        session_id: uuid.UUID,
        query: str,
        limit: int = 10,
        min_importance: Optional[int] = None,
        event_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> List[AdventureMemory]:
        """Search memories using semantic similarity

        Args:
            db: Database session
            session_id: Game session ID
            query: Search query
            limit: Max results
            min_importance: Minimum importance filter
            event_types: Filter by event types
            tags: Filter by tags

        Returns:
            List of matching memories sorted by relevance
        """
        # Generate query embedding
        embedding_service = get_embedding_service()
        query_embedding = await embedding_service.generate_embedding(query)

        if not query_embedding:
            # Fallback to text search if embedding fails
            return await MemoryService._text_search_fallback(
                db, session_id, query, limit, min_importance, event_types, tags
            )

        # Build filter conditions
        conditions = [AdventureMemory.session_id == session_id]

        if min_importance:
            conditions.append(AdventureMemory.importance >= min_importance)

        if event_types:
            conditions.append(AdventureMemory.event_type.in_(event_types))

        # PostgreSQL cosine similarity query with pgvector
        # Calculate similarity: 1 - (embedding <=> query_embedding)
        embedding_array_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # Use parameterized query to avoid SQL injection warnings
        # pgvector requires the <=> operator which isn't natively supported by SQLAlchemy
        similarity_expr = text("1 - (embedding::vector <=> :query_embedding::vector)").bindparams(
            query_embedding=embedding_array_str
        )

        # Build query
        stmt = (
            select(AdventureMemory)
            .where(and_(*conditions))
            .order_by(desc(similarity_expr))
            .limit(limit)
        )

        result = await db.execute(stmt)
        memories = list(result.scalars().all())

        # Additional tag filtering (post-query since JSONB array filtering is complex)
        if tags:
            memories = [m for m in memories if m.tags and any(tag in m.tags for tag in tags)][
                :limit
            ]

        return memories

    @staticmethod
    async def _text_search_fallback(
        db: AsyncSession,
        session_id: uuid.UUID,
        query: str,
        limit: int,
        min_importance: Optional[int],
        event_types: Optional[List[str]],
        tags: Optional[List[str]],
    ) -> List[AdventureMemory]:
        """Fallback text search when embeddings fail"""
        conditions = [
            AdventureMemory.session_id == session_id,
            AdventureMemory.content.ilike(f"%{query}%"),
        ]

        if min_importance:
            conditions.append(AdventureMemory.importance >= min_importance)

        if event_types:
            conditions.append(AdventureMemory.event_type.in_(event_types))

        stmt = (
            select(AdventureMemory)
            .where(and_(*conditions))
            .order_by(desc(AdventureMemory.importance), desc(AdventureMemory.timestamp))
            .limit(limit)
        )

        result = await db.execute(stmt)
        memories = list(result.scalars().all())

        if tags:
            memories = [m for m in memories if m.tags and any(tag in m.tags for tag in tags)][
                :limit
            ]

        return memories

    @staticmethod
    async def get_recent_memories(
        db: AsyncSession, session_id: uuid.UUID, limit: int = 10, min_importance: int = 5
    ) -> List[AdventureMemory]:
        """Get most recent important memories

        Args:
            db: Database session
            session_id: Game session ID
            limit: Max results
            min_importance: Minimum importance threshold

        Returns:
            Recent memories sorted by timestamp
        """
        stmt = (
            select(AdventureMemory)
            .where(
                and_(
                    AdventureMemory.session_id == session_id,
                    AdventureMemory.importance >= min_importance,
                )
            )
            .order_by(desc(AdventureMemory.timestamp))
            .limit(limit)
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_context_for_ai(
        db: AsyncSession, session_id: uuid.UUID, current_situation: str, max_memories: int = 5
    ) -> str:
        """Get formatted memory context for AI DM

        Args:
            db: Database session
            session_id: Game session ID
            current_situation: Current game situation/query
            max_memories: Max memories to include

        Returns:
            Formatted string with relevant memories
        """
        # Search for relevant memories
        memories = await MemoryService.search_memories(
            db=db,
            session_id=session_id,
            query=current_situation,
            limit=max_memories,
            min_importance=6,  # Only important memories
        )

        if not memories:
            return "No relevant past events found."

        # Format memories for AI context
        formatted = []
        for i, memory in enumerate(memories, 1):
            timestamp_str = memory.timestamp.strftime("%Y-%m-%d %H:%M")
            importance_indicator = "⭐" * min(memory.importance, 10)

            formatted_memory = f"{i}. [{memory.event_type.value.upper()}] {importance_indicator}\n"
            formatted_memory += f"   Time: {timestamp_str}\n"
            formatted_memory += f"   Event: {memory.content}\n"

            if memory.locations:
                formatted_memory += f"   Location: {', '.join(memory.locations)}\n"

            if memory.npcs_involved:
                formatted_memory += f"   NPCs: {len(memory.npcs_involved)} involved\n"

            formatted.append(formatted_memory)

        return "\n".join(formatted)

    @staticmethod
    async def calculate_importance(
        event_type: str,
        content: str,
        is_combat_outcome: bool = False,
        is_major_decision: bool = False,
        involves_boss: bool = False,
    ) -> int:
        """Calculate importance score for an event

        Args:
            event_type: Type of event
            content: Event description
            is_combat_outcome: Whether this is a combat result
            is_major_decision: Whether this is a significant choice
            involves_boss: Whether a boss NPC is involved

        Returns:
            Importance score (1-10)
        """
        # Base importance by event type
        base_scores = {
            "combat": 7,
            "dialogue": 4,
            "discovery": 6,
            "decision": 5,
            "quest": 8,
            "npc_interaction": 5,
            "loot": 4,
            "location": 5,
            "other": 3,
        }

        score = base_scores.get(event_type, 5)

        # Modifiers
        if is_combat_outcome:
            score += 2
        if is_major_decision:
            score += 2
        if involves_boss:
            score += 2

        # Content-based hints
        content_lower = content.lower()
        if any(word in content_lower for word in ["death", "died", "killed", "defeated"]):
            score += 1
        if any(word in content_lower for word in ["legendary", "artifact", "ancient", "powerful"]):
            score += 1
        if any(word in content_lower for word in ["betrayed", "ally", "friendship", "trust"]):
            score += 1

        # Clamp to 1-10
        return max(1, min(10, score))
