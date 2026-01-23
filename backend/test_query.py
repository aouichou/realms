#!/usr/bin/env python3
import asyncio

from sqlalchemy import select

from app.db.base import async_session
from app.db.models import Character, GameSession


async def test():
    async with async_session() as db:
        print("Testing GameSession query...")
        result = await db.execute(select(GameSession).limit(1))
        session = result.scalar_one_or_none()
        print(f"Session: {session}")
        if session:
            print(f"Character ID: {session.character_id}")

            # Try to access the character relationship
            print("\nTrying to access character relationship...")
            try:
                print(f"Session.character: {session.character}")
            except Exception as e:
                print(f"ERROR accessing session.character: {e}")

        print("\n\nTesting Character query...")
        result2 = await db.execute(select(Character).limit(1))
        char = result2.scalar_one_or_none()
        print(f"Character: {char}")
        if char:
            print("\nTrying to access game_sessions relationship...")
            try:
                print(f"Character.game_sessions: {char.game_sessions}")
            except Exception as e:
                print(f"ERROR accessing char.game_sessions: {e}")


asyncio.run(test())
