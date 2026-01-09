#!/usr/bin/env python3
"""
Simple script to check if memories are being captured in the database.
Connects directly to the local PostgreSQL database.
"""

import asyncio
from datetime import datetime

import asyncpg


async def check_memories():
    print("🔍 Checking adventure memories in database...\n")

    # Connect to local database
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="realms_user",
        password="realms_password",
        database="mistral_realms",
    )

    try:
        # Get count of memories
        count = await conn.fetchval("SELECT COUNT(*) FROM adventure_memories")
        print(f"📊 Total memories stored: {count}\n")

        if count == 0:
            print(
                "ℹ️  No memories found yet. This is expected if you haven't played the game yet."
            )
            print("\n💡 To generate memories, play the game and:")
            print("   • Have a conversation (triggers dialogue memory)")
            print("   • Fight in combat (triggers combat memory)")
            print("   • Cast a spell (triggers spell memory)")
            print("   • Pick up loot (triggers loot memory)")
            return

        # Get recent memories
        print("📝 Recent memories:\n")
        rows = await conn.fetch("""
            SELECT
                event_type,
                importance,
                LEFT(content, 100) as content_preview,
                created_at
            FROM adventure_memories
            ORDER BY created_at DESC
            LIMIT 10
        """)

        for row in rows:
            timestamp = row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            importance = "⭐" * row["importance"]
            print(f"[{timestamp}] {row['event_type'].upper()}")
            print(f"  {importance}")
            print(f"  {row['content_preview']}...")
            print()

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_memories())
