"""
Semantic Search Service for D&D Content (RL-144)
Enables natural language search across items, monsters, and spells.
Reuses sentence-transformer model from ImageDetectionService.
"""

from typing import Any, Dict, List, Optional

import numpy as np
import torch
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.creature import Creature
from app.db.models.item_catalog import ItemCatalog
from app.db.models.spell import Spell
from app.observability.logger import get_logger
from app.services.image_detection_service import ImageDetectionService

logger = get_logger(__name__)


class SemanticSearchService:
    """
    Search items, monsters, and spells using semantic similarity.

    Examples:
    - "healing magic" → Potion of Healing, Cure Wounds
    - "fire damage" → Fireball, Fire Bolt, Flame Tongue
    - "undead creatures" → Zombie, Skeleton, Vampire, Lich
    """

    SIMILARITY_THRESHOLD = 0.3  # Tunable threshold for matches

    def __init__(self):
        """Initialize semantic search service with embedding model."""
        self.embedding_service: Optional[ImageDetectionService] = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the sentence transformer model for embeddings."""
        try:
            self.embedding_service = ImageDetectionService()
        except Exception as e:
            logger.error(f"RL-144: Error initializing embedding model: {e}")

    def _generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for text query.

        Args:
            text: Text to embed

        Returns:
            Numpy array embedding or None if error
        """
        if not self.embedding_service or not self.embedding_service._model:
            return None

        try:
            with torch.inference_mode():
                embedding = self.embedding_service._model.encode(
                    text,
                    convert_to_tensor=True,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                )
                return embedding.cpu().numpy()
        except Exception as e:
            logger.error(f"RL-144: Error generating embedding: {e}")
            return None

    def _calculate_similarity(self, query_embedding: np.ndarray, text: str) -> float:
        """
        Calculate cosine similarity between query and text.

        Args:
            query_embedding: Pre-computed query embedding
            text: Text to compare against

        Returns:
            Similarity score (0-1)
        """
        text_embedding = self._generate_embedding(text)
        if text_embedding is None:
            return 0.0

        # Cosine similarity (already normalized embeddings)
        similarity = np.dot(query_embedding, text_embedding)
        return float(similarity)

    async def search_items(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 10,
        category: Optional[str] = None,
        rarity: Optional[str] = None,
        similarity_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for items.

        Args:
            query: Natural language search query
            db: Database session
            limit: Maximum results to return
            category: Optional category filter (weapon, armor, potion, etc.)
            rarity: Optional rarity filter (common, uncommon, rare, etc.)
            similarity_threshold: Custom threshold (default: 0.3)

        Returns:
            List of items with similarity scores

        Examples:
            - "healing magic" → Potion of Healing, Cure Wounds scroll
            - "fire weapons" → Flame Tongue, +1 Flaming Longsword
        """
        threshold = similarity_threshold or self.SIMILARITY_THRESHOLD

        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        if query_embedding is None:
            logger.warning("RL-144: Failed to generate query embedding, returning empty")
            return []

        # Build base query with filters
        stmt = select(ItemCatalog)
        if category:
            stmt = stmt.where(func.lower(ItemCatalog.category) == func.lower(category))
        if rarity:
            stmt = stmt.where(func.lower(ItemCatalog.rarity).contains(func.lower(rarity)))

        # Limit to reasonable size for performance
        stmt = stmt.limit(1000)

        result = await db.execute(stmt)
        items = result.scalars().all()

        # Calculate similarity for each item
        scored_items = []
        for item in items:
            # Create searchable text from item properties
            search_text = " ".join(
                [
                    str(getattr(item, "name", "")),
                    str(getattr(item, "category", "")),
                    str(getattr(item, "item_type", "")),
                    str(getattr(item, "rarity", "")),
                    str(getattr(item, "description", ""))[:100],  # Limit description length
                    str(getattr(item, "damage_type", "")),
                ]
            )

            similarity = self._calculate_similarity(query_embedding, search_text)

            if similarity >= threshold:
                scored_items.append((item, similarity))

        # Sort by similarity (highest first)
        scored_items.sort(key=lambda x: x[1], reverse=True)
        top_items = scored_items[:limit]

        # Format results
        return [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "rarity": item.rarity,
                "description": item.description[:200] + "..."
                if len(item.description) > 200
                else item.description,
                "damage_type": item.damage_type,
                "cost_gp": item.cost_gp,
                "similarity": round(similarity, 3),
            }
            for item, similarity in top_items
        ]

    async def search_monsters(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 10,
        creature_type: Optional[str] = None,
        min_cr: Optional[float] = None,
        max_cr: Optional[float] = None,
        similarity_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for monsters and creatures.

        Args:
            query: Natural language search query
            db: Database session
            limit: Maximum results to return
            creature_type: Optional type filter (undead, dragon, humanoid, etc.)
            min_cr: Minimum challenge rating
            max_cr: Maximum challenge rating
            similarity_threshold: Custom threshold (default: 0.3)

        Returns:
            List of creatures with similarity scores

        Examples:
            - "undead creatures" → Zombie, Skeleton, Vampire
            - "fire breathing" → Red Dragon, Hell Hound, Fire Elemental
            - "weak goblins" → Goblin (CR 1/4), Goblin Boss (CR 1)
        """
        threshold = similarity_threshold or self.SIMILARITY_THRESHOLD

        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        if query_embedding is None:
            logger.warning("RL-144: Failed to generate query embedding, returning empty")
            return []

        # Build base query with filters
        stmt = select(Creature)
        if creature_type:
            stmt = stmt.where(
                func.lower(Creature.creature_type).contains(func.lower(creature_type))
            )
        if min_cr is not None:
            # CR can be string like "1/4" so need to handle carefully
            # For now, just filter by exact match or comparison
            pass  # TODO: Handle CR filtering properly
        if max_cr is not None:
            pass  # TODO: Handle CR filtering properly

        # Limit to reasonable size
        stmt = stmt.limit(500)

        result = await db.execute(stmt)
        creatures = result.scalars().all()

        # Calculate similarity for each creature
        scored_creatures = []
        for creature in creatures:
            # Create searchable text from creature properties
            search_text = " ".join(
                [
                    str(getattr(creature, "name", "")),
                    str(getattr(creature, "creature_type", "")),
                    str(getattr(creature, "size", "")),
                    str(getattr(creature, "alignment", "")),
                    str(getattr(creature, "traits", ""))[:100],  # Limit traits length
                    str(getattr(creature, "actions", ""))[:100],  # Limit actions length
                    f"CR {getattr(creature, 'cr', '')}",
                ]
            )

            similarity = self._calculate_similarity(query_embedding, search_text)

            if similarity >= threshold:
                scored_creatures.append((creature, similarity))

        # Sort by similarity (highest first)
        scored_creatures.sort(key=lambda x: x[1], reverse=True)
        top_creatures = scored_creatures[:limit]

        # Format results
        return [
            {
                "id": creature.id,
                "name": creature.name,
                "creature_type": creature.creature_type,
                "size": creature.size,
                "cr": creature.cr,
                "ac": creature.ac,
                "hp": creature.hp,
                "alignment": creature.alignment,
                "traits_preview": (creature.traits[:150] + "...")
                if creature.traits and len(creature.traits) > 150
                else creature.traits,
                "similarity": round(similarity, 3),
            }
            for creature, similarity in top_creatures
        ]

    async def search_spells(
        self,
        query: str,
        db: AsyncSession,
        limit: int = 10,
        spell_level: Optional[int] = None,
        school: Optional[str] = None,
        similarity_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for spells.

        Args:
            query: Natural language search query
            db: Database session
            limit: Maximum results to return
            spell_level: Optional level filter (0-9)
            school: Optional school filter (evocation, abjuration, etc.)
            similarity_threshold: Custom threshold (default: 0.3)

        Returns:
            List of spells with similarity scores

        Examples:
            - "fire damage" → Fireball, Fire Bolt, Burning Hands
            - "healing magic" → Cure Wounds, Healing Word, Mass Cure Wounds
            - "protective spells" → Shield, Mage Armor, Protection from Evil
        """
        threshold = similarity_threshold or self.SIMILARITY_THRESHOLD

        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        if query_embedding is None:
            logger.warning("RL-144: Failed to generate query embedding, returning empty")
            return []

        # Build base query with filters
        stmt = select(Spell)
        if spell_level is not None:
            stmt = stmt.where(Spell.level == spell_level)
        if school:
            stmt = stmt.where(func.lower(Spell.school) == func.lower(school))

        # Limit to reasonable size
        stmt = stmt.limit(1000)

        result = await db.execute(stmt)
        spells = result.scalars().all()

        # Calculate similarity for each spell
        scored_spells = []
        for spell in spells:
            # Create searchable text from spell properties
            search_text = " ".join(
                filter(
                    None,
                    [
                        spell.name,
                        str(spell.school),
                        f"level {spell.level}",
                        spell.description or "",
                        spell.damage_type or "",
                    ],
                )
            )

            similarity = self._calculate_similarity(query_embedding, search_text)

            if similarity >= threshold:
                scored_spells.append((spell, similarity))

        # Sort by similarity (highest first)
        scored_spells.sort(key=lambda x: x[1], reverse=True)
        top_spells = scored_spells[:limit]

        # Format results
        return [
            {
                "id": str(spell.id),
                "name": spell.name,
                "level": spell.level,
                "school": str(spell.school),
                "casting_time": str(spell.casting_time),
                "range": spell.range,
                "duration": spell.duration,
                "description": spell.description[:200] + "..."
                if len(spell.description) > 200
                else spell.description,
                "damage_type": spell.damage_type,
                "is_concentration": spell.is_concentration,
                "similarity": round(similarity, 3),
            }
            for spell, similarity in top_spells
        ]

    async def search_memories(
        self,
        query: str,
        db: AsyncSession,
        character_id: int,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search adventure memories using semantic similarity.
        Enables DM to recall past events semantically.

        Args:
            query: Natural language search query
            db: Database session
            character_id: Character ID to filter memories
            limit: Max results (default 5, max 10)

        Returns:
            List of memories with content, timestamp, type

        Example:
            search_memories("dragon encounter", db, character_id=1, limit=5)
            → Returns memories about dragon encounters
        """
        if not self.embedding_service or not self.embedding_service._model:
            logger.error("RL-144: Embedding model not initialized for memory search")
            return []

        if not query or not query.strip():
            logger.warning("RL-144: Empty query for memory search")
            return []

        # Import here to avoid circular dependency
        from app.db.models.adventure import AdventureMemory

        try:
            # Generate embedding for query
            query_embedding = self._generate_embedding(query)
            if query_embedding is None:
                logger.warning("RL-144: Failed to generate query embedding for memory search")
                return []

            # Convert to list for pgvector
            query_vector = query_embedding.tolist()

            # Search memories by cosine similarity (pgvector)
            from sqlalchemy import select

            stmt = (
                select(AdventureMemory)
                .where(AdventureMemory.character_id == character_id)
                .order_by(AdventureMemory.embedding.cosine_distance(query_vector))
                .limit(min(limit, 10))
            )

            result = await db.execute(stmt)
            memories = result.scalars().all()

            # Format results
            return [
                {
                    "content": (
                        memory.content[:200] + "..."
                        if len(memory.content) > 200
                        else memory.content
                    ),
                    "timestamp": memory.created_at.isoformat(),
                    "type": memory.memory_type,
                }
                for memory in memories
            ]

        except Exception as e:
            logger.error(f"RL-144: Error in memory search: {e}")
            return []


# Singleton instance
_semantic_search_instance: Optional[SemanticSearchService] = None


def get_semantic_search_service() -> SemanticSearchService:
    """Get or create singleton SemanticSearchService instance."""
    global _semantic_search_instance
    if _semantic_search_instance is None:
        _semantic_search_instance = SemanticSearchService()
    return _semantic_search_instance
