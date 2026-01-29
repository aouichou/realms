"""Quick script to check imported items."""

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.models.item_catalog import ItemCatalog


async def check_items():
    """Check imported items statistics."""
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Total count
        result = await db.execute(select(func.count(ItemCatalog.id)))
        total = result.scalar()
        print(f"\n=== Item Catalog Statistics ===")
        print(f"Total Items: {total}\n")

        # By category
        print("Items by Category:")
        result = await db.execute(
            select(ItemCatalog.category, func.count(ItemCatalog.id))
            .group_by(ItemCatalog.category)
            .order_by(func.count(ItemCatalog.id).desc())
        )
        for category, count in result:
            print(f"  {count:5d}  {category}")

        # By rarity
        print("\nItems by Rarity (top 10):")
        result = await db.execute(
            select(ItemCatalog.rarity, func.count(ItemCatalog.id))
            .group_by(ItemCatalog.rarity)
            .order_by(func.count(ItemCatalog.id).desc())
            .limit(10)
        )
        for rarity, count in result:
            print(f"  {count:5d}  {rarity}")

        # Sample weapons
        print("\nSample Weapons (5 random):")
        result = await db.execute(
            select(ItemCatalog.name, ItemCatalog.damage_dice, ItemCatalog.damage_type)
            .where(ItemCatalog.category == "weapon")
            .limit(5)
        )
        for name, dice, dtype in result:
            print(f"  - {name}: {dice} {dtype}")

        # Sample armor
        print("\nSample Armor (5 random):")
        result = await db.execute(
            select(ItemCatalog.name, ItemCatalog.ac_base, ItemCatalog.ac_bonus)
            .where(ItemCatalog.category == "armor")
            .limit(5)
        )
        for name, ac_base, ac_bonus in result:
            print(f"  - {name}: AC {ac_base} {'+' + str(ac_bonus) if ac_bonus else ''}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_items())
