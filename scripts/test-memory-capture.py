#!/usr/bin/env python3
"""Test script to verify memory capture integration"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.db.base import async_session
from app.db.models import AdventureMemory
from sqlalchemy import select


async def test_memory_capture():
    """Test that memories are being captured"""
    async with async_session() as db:
        # Check if any memories exist
        result = await db.execute(
            select(AdventureMemory)
            .order_by(AdventureMemory.created_at.desc())
            .limit(10)
        )
        memories = result.scalars().all()

        print(f"\n{'=' * 60}")
        print(f"Memory Capture Integration Test")
        print(f"{'=' * 60}\n")

        if not memories:
            print("❌ No memories found in database")
            print("\nTo test memory capture:")
            print("1. Start the backend: docker-compose up")
            print("2. Create a character and start a game")
            print("3. Perform actions: combat, cast spells, get loot")
            print("4. Run this script again to verify memories were captured")
        else:
            print(f"✅ Found {len(memories)} recent memories:\n")
            for i, memory in enumerate(memories, 1):
                print(
                    f"{i}. [{memory.event_type.value}] Importance: {memory.importance}/10"
                )
                print(f"   Content: {memory.content[:100]}...")
                print(f"   Created: {memory.created_at}")
                print()

        print(f"{'=' * 60}\n")


if __name__ == "__main__":
    asyncio.run(test_memory_capture())
