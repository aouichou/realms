"""Quick script to count imported data"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.models.creature import Creature
from app.db.models.item_catalog import ItemCatalog
from app.db.models.spell import Spell


async def main():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Count items
        result = await db.execute(select(func.count(ItemCatalog.id)))
        item_count = result.scalar()

        # Count monsters
        result = await db.execute(select(func.count(Creature.id)))
        monster_count = result.scalar()

        # Count spells
        result = await db.execute(select(func.count(Spell.id)))
        spell_count = result.scalar()

        print(f"\n=== Dataset Import Summary ===")
        print(f"Items:    {item_count:,}")
        print(f"Monsters: {monster_count:,}")
        print(f"Spells:   {spell_count:,}")
        print(f"TOTAL:    {item_count + monster_count + spell_count:,}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
