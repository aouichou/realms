"""
Content Cross-Reference System (RL-145)
Links monsters to equipment, spells to classes, generates loot tables.
Enables intelligent cross-referencing of D&D 5e content databases.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.creature import Creature
from app.db.models.item_catalog import ItemCatalog
from app.observability.logger import get_logger

logger = get_logger(__name__)


class ContentLinker:
    """
    Cross-reference D&D content datasets for intelligent loot generation.

    Features:
    - Monster → Equipment: Get appropriate loot for defeating monsters
    - CR → Rarity: Map Challenge Rating to item rarity
    - Treasure Hoards: Generate random loot based on encounter difficulty
    """

    # CR → Rarity mappings (D&D 5e Dungeon Master's Guide guidelines)
    CR_TO_RARITY = {
        (0, 4): "common",
        (5, 10): "uncommon",
        (11, 16): "rare",
        (17, 20): "very rare",
        (21, 30): "legendary",
    }

    async def get_monster_equipment(
        self, monster_name: str, db: AsyncSession, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get appropriate equipment for a monster type.

        Uses monster CR to determine item rarity, then finds weapons/armor
        that would be appropriate loot from defeating that monster.

        Args:
            monster_name: Name of the monster (e.g., "Goblin", "Ancient Red Dragon")
            db: Database session
            limit: Max number of items to return (default 10)

        Returns:
            List of items with name, category, rarity, damage, AC, description

        Example:
            get_monster_equipment("Goblin", db)
            → [{"name": "Scimitar", "rarity": "common", ...},
               {"name": "Leather Armor", "rarity": "common", ...}]
        """
        try:
            # Get monster from database
            stmt = select(Creature).where(
                func.lower(Creature.name).contains(func.lower(monster_name))
            )
            result = await db.execute(stmt)
            monster = result.scalar_one_or_none()

            if not monster:
                logger.warning(f"RL-145: Monster '{monster_name}' not found")
                return []

            # Determine rarity based on CR
            cr = float(monster.challenge_rating) if monster.challenge_rating else 0
            rarity = self._get_rarity_for_cr(cr)

            logger.info(f"RL-145: Getting equipment for {monster.name} (CR {cr}) → {rarity} rarity")

            # Get weapons/armor appropriate for monster type
            stmt = (
                select(ItemCatalog)
                .where(
                    ItemCatalog.rarity.ilike(
                        f"%{rarity}%"
                    ),  # Handles "common (requires attunement)" etc.
                    ItemCatalog.category.in_(["weapon", "armor", "shield"]),
                )
                .order_by(func.random())
                .limit(limit)
            )

            result = await db.execute(stmt)
            items = result.scalars().all()

            logger.info(f"RL-145: Found {len(items)} equipment items for {monster.name}")
            logger.debug(
                f"RL-145: Entity matches for {monster.name}",
                extra={
                    "extra_data": {
                        "monster_id": monster.id,
                        "cr": cr,
                        "target_rarity": rarity,
                        "matched_items": [item.name for item in items],
                        "item_categories": [item.category for item in items],
                    }
                },
            )

            # Format results
            return [
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "rarity": item.rarity,
                    "damage_dice": item.damage_dice,
                    "damage_type": item.damage_type,
                    "ac_base": item.ac_base,
                    "ac_bonus": item.ac_bonus,
                    "description": (
                        str(getattr(item, "description", ""))[:150] + "..."
                        if len(str(getattr(item, "description", ""))) > 150
                        else str(getattr(item, "description", ""))
                    ),
                }
                for item in items
            ]

        except Exception as e:
            logger.error(f"RL-145: Error getting monster equipment: {e}")
            return []

    async def generate_loot_table(
        self,
        encounter_cr: float,
        db: AsyncSession,
        num_items: int = 3,
        include_consumables: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Generate loot table based on encounter CR.

        Returns random items of appropriate rarity for the encounter difficulty.
        Follows D&D 5e treasure distribution guidelines.

        Args:
            encounter_cr: Challenge Rating of the encounter
            db: Database session
            num_items: Number of items to generate (default 3, max 10)
            include_consumables: Include potions/scrolls (default True)

        Returns:
            List of items with name, category, rarity, description

        Example:
            generate_loot_table(5, db, num_items=3)
            → [{"name": "Potion of Greater Healing", "rarity": "uncommon", ...},
               {"name": "+1 Longsword", "rarity": "uncommon", ...},
               {"name": "Ring of Protection", "rarity": "uncommon", ...}]
        """
        try:
            rarity = self._get_rarity_for_cr(encounter_cr)
            num_items = min(num_items, 10)  # Cap at 10

            logger.info(
                f"RL-145: Generating {num_items} items for CR {encounter_cr} (rarity: {rarity})"
            )

            # Build category filter
            categories = ["weapon", "armor", "shield", "wondrous_item"]
            if include_consumables:
                categories.extend(["potion", "scroll"])

            # Get random items of appropriate rarity
            stmt = (
                select(ItemCatalog)
                .where(
                    ItemCatalog.rarity.ilike(f"%{rarity}%"),
                    ItemCatalog.category.in_(categories),
                )
                .order_by(func.random())
                .limit(num_items)
            )

            result = await db.execute(stmt)
            items = result.scalars().all()

            logger.info(f"RL-145: Generated {len(items)} loot items (rarity: {rarity})")
            logger.debug(
                f"RL-145: Loot table generated",
                extra={
                    "extra_data": {
                        "encounter_cr": encounter_cr,
                        "target_rarity": rarity,
                        "requested_items": num_items,
                        "generated_items": len(items),
                        "loot_names": [item.name for item in items],
                        "include_consumables": include_consumables,
                    }
                },
            )

            # Format results
            return [
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "rarity": item.rarity,
                    "description": (
                        str(getattr(item, "description", ""))[:200] + "..."
                        if len(str(getattr(item, "description", ""))) > 200
                        else str(getattr(item, "description", ""))
                    ),
                    "damage_dice": item.damage_dice,
                    "damage_type": item.damage_type,
                    "ac_base": item.ac_base,
                    "ac_bonus": item.ac_bonus,
                    "value_gp": item.value_gp,
                }
                for item in items
            ]

        except Exception as e:
            logger.error(f"RL-145: Error generating loot table: {e}")
            return []

    def _get_rarity_for_cr(self, cr: float) -> str:
        """
        Map Challenge Rating to item rarity.

        Based on D&D 5e treasure distribution guidelines:
        - CR 0-4: Common items
        - CR 5-10: Uncommon items
        - CR 11-16: Rare items
        - CR 17-20: Very rare items
        - CR 21+: Legendary items

        Args:
            cr: Challenge Rating

        Returns:
            Rarity string (common, uncommon, rare, very rare, legendary)
        """
        for (min_cr, max_cr), rarity in self.CR_TO_RARITY.items():
            if min_cr <= cr <= max_cr:
                return rarity
        return "common"


# Singleton instance
_content_linker_instance: Optional[ContentLinker] = None


def get_content_linker() -> ContentLinker:
    """Get or create singleton ContentLinker instance."""
    global _content_linker_instance
    if _content_linker_instance is None:
        _content_linker_instance = ContentLinker()
    return _content_linker_instance
