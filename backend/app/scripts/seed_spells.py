"""Seed spell data into the database"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import uuid
from app.db.base import async_session_maker
from app.db.models import Spell
from app.data.spell_seed_data import SPELL_SEED_DATA


async def seed_spells():
    """Seed spell data into database"""
    async with async_session_maker() as db:
        print("Starting spell data seeding...")
        
        for spell_data in SPELL_SEED_DATA:
            spell = Spell(
                id=uuid.uuid4(),
                **spell_data
            )
            db.add(spell)
        
        await db.commit()
        print(f"Successfully seeded {len(SPELL_SEED_DATA)} spells!")


if __name__ == "__main__":
    asyncio.run(seed_spells())
