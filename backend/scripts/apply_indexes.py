"""
Apply recommended database indexes for performance optimization.

RL-304: Addresses slow queries logged in production:
  - SELECT adventure_memories... (1.024s)
  - POST /api/v1/game/save (1.542s)
  - POST /api/v1/conversations/action (22.205s)
  - SELECT users... (0.612s)

Usage:
    python -m scripts.apply_indexes          # Dry run (show SQL only)
    python -m scripts.apply_indexes --apply  # Apply indexes

All indexes use CREATE INDEX CONCURRENTLY to avoid table locks.
"""

import argparse
import asyncio
import sys

# Indexes that already exist in SQLAlchemy models (via index=True or __table_args__):
EXISTING_INDEXES = [
    # User model
    "ix_users_email_blind_index",  # unique
    "ix_users_username",  # unique
    "ix_users_guest_token",  # unique
    # Character model
    "ix_characters_user_id",
    "ix_characters_character_type",
    "ix_characters_deleted_at",
    "ix_characters_user_type",  # composite
    # CharacterSpell
    "ix_character_spells_character_id",
    "ix_character_spells_spell_id",
    "ix_character_spells_char_spell",  # composite unique
    "ix_character_spells_prepared",  # composite
    # CharacterQuest
    "ix_character_quests_character_id",
    "ix_character_quests_quest_id",
    "ix_character_quest_unique",  # composite unique
    # GameSession
    "ix_game_sessions_user_id",
    "ix_game_sessions_character_id",
    "ix_game_sessions_companion_id",
    "ix_game_sessions_is_active",
    "ix_game_sessions_last_activity_at",
    "ix_game_sessions_user_active",  # composite
    # ConversationMessage
    "ix_conversation_messages_session_id",
    "ix_conversation_messages_created_at",
    "ix_messages_session_created",  # composite
    # AdventureMemory
    "ix_adventure_memories_session_id",
    "ix_adventure_memories_importance",
    "ix_adventure_memories_timestamp",
    # Item
    "ix_items_character_id",
    "ix_items_item_type",
    "ix_items_character_type",  # composite
    "ix_items_character_equipped",  # composite
    # Quest
    "ix_quests_state",
    # CombatEncounter
    "ix_combat_encounters_session_id",
    "ix_combat_encounters_is_active",
    # Adventure
    "ix_adventures_character_id",
    # ActiveEffect
    "ix_active_effects_character_id",
    "ix_active_effects_session_id",
    "ix_active_effects_is_active",
    # Companion
    "ix_companions_character_id",
    "ix_companions_creature_id",
]

# New indexes to add for performance optimization
NEW_INDEXES = [
    # ── Adventure Memories (slow query: 1.024s) ──
    # Composite index for the most common query: filter by session + importance, order by timestamp
    {
        "name": "idx_memories_session_importance",
        "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_session_importance "
        "ON adventure_memories(session_id, importance DESC, timestamp DESC);",
        "reason": "Optimizes MemoryService.search_memories() and get_recent_memories() "
        "which filter by session_id + importance >= N, ordered by timestamp/similarity",
    },
    # Composite for session + created_at (used in cleanup/archive queries)
    {
        "name": "idx_memories_session_created",
        "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_session_created "
        "ON adventure_memories(session_id, created_at DESC);",
        "reason": "Optimizes memory queries ordered by creation time",
    },
    # ── Game Sessions (slow save: 1.542s) ──
    # Composite for user sessions ordered by activity (list_saves, get_user_sessions)
    {
        "name": "idx_sessions_user_activity",
        "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_user_activity "
        "ON game_sessions(user_id, last_activity_at DESC);",
        "reason": "Optimizes SaveService.list_saves() and get_user_sessions() "
        "which query all sessions for a user ordered by activity",
    },
    # Partial index for active sessions (frequently queried)
    {
        "name": "idx_sessions_active_partial",
        "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_active_partial "
        "ON game_sessions(user_id, character_id) WHERE is_active = TRUE;",
        "reason": "Optimizes get_active_session() and get_active_session_for_character() "
        "which always filter is_active = TRUE",
    },
    # ── Characters (used in conversations/action) ──
    # Composite for user + level (character listing sorted by level)
    {
        "name": "idx_characters_user_level",
        "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_characters_user_level "
        "ON characters(user_id, level DESC);",
        "reason": "Optimizes character list queries that sort by level",
    },
    # ── Conversation Messages (session_id + role for filtered queries) ──
    {
        "name": "idx_messages_session_role",
        "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_session_role "
        "ON conversation_messages(session_id, role, created_at DESC);",
        "reason": "Optimizes queries that filter messages by role within a session",
    },
    # ── Active Effects (conversations/action fetches active effects) ──
    # Partial index for active effects per character
    {
        "name": "idx_effects_char_active",
        "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_effects_char_active "
        "ON active_effects(character_id, session_id) WHERE is_active = TRUE;",
        "reason": "Optimizes active effect lookups in the action endpoint",
    },
    # Index on expires_at for cleanup of expired effects
    {
        "name": "idx_effects_expires",
        "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_effects_expires "
        "ON active_effects(expires_at) WHERE expires_at IS NOT NULL;",
        "reason": "Optimizes expiration cleanup queries",
    },
    # ── Combat Encounters (partial index for active combats) ──
    {
        "name": "idx_combat_active_partial",
        "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_combat_active_partial "
        "ON combat_encounters(session_id) WHERE is_active = TRUE;",
        "reason": "Optimizes active combat lookups (common in action endpoint)",
    },
    # ── Companions (conversations/action queries active alive companions) ──
    {
        "name": "idx_companions_char_active",
        "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_companions_char_active "
        "ON companions(character_id) WHERE is_active = TRUE AND is_alive = TRUE;",
        "reason": "Optimizes the active companion query in conversations/action endpoint",
    },
    # ── Quests (conversations/action queries in-progress quests) ──
    {
        "name": "idx_character_quests_quest",
        "sql": "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_character_quests_quest "
        "ON character_quests(character_id, quest_id);",
        "reason": "Optimizes the quest lookup join in conversations/action",
    },
]


def print_report():
    """Print index analysis report"""
    print("=" * 80)
    print("RL-304: DATABASE INDEX ANALYSIS")
    print("=" * 80)

    print(f"\n✅ {len(EXISTING_INDEXES)} indexes already exist in SQLAlchemy models")
    print(f"🆕 {len(NEW_INDEXES)} new indexes recommended\n")

    print("─" * 80)
    print("NEW INDEXES TO APPLY:")
    print("─" * 80)

    for idx in NEW_INDEXES:
        print(f"\n  📌 {idx['name']}")
        print(f"     Reason: {idx['reason']}")
        print(f"     SQL: {idx['sql']}")

    print("\n" + "=" * 80)


async def apply_indexes():
    """Apply all recommended indexes to the database"""
    # Import here to avoid issues when just printing report
    from sqlalchemy import text

    from app.db.base import async_engine

    print("\n🚀 Applying indexes...")
    print("   Using CONCURRENTLY mode (no table locks)\n")

    applied = 0
    failed = 0

    for idx in NEW_INDEXES:
        try:
            # CONCURRENTLY requires autocommit (not inside a transaction)
            async with async_engine.connect() as conn:
                await conn.execute(text("COMMIT"))  # Exit any implicit transaction
                await conn.execute(text(idx["sql"]))
                print(f"  ✅ {idx['name']}")
                applied += 1
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg:
                print(f"  ⏭️  {idx['name']} (already exists)")
                applied += 1
            else:
                print(f"  ❌ {idx['name']}: {error_msg}")
                failed += 1

    print(f"\n📊 Results: {applied} applied, {failed} failed")
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Apply database performance indexes (RL-304)")
    parser.add_argument(
        "--apply", action="store_true", help="Actually apply indexes (default is dry-run)"
    )
    args = parser.parse_args()

    print_report()

    if args.apply:
        success = asyncio.run(apply_indexes())
        sys.exit(0 if success else 1)
    else:
        print("\n💡 This was a dry run. Use --apply to execute.")
        print("   python -m scripts.apply_indexes --apply\n")


if __name__ == "__main__":
    main()
