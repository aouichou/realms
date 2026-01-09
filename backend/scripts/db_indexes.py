"""
Database Index Recommendations
Analyzes slow queries and suggests indexes
"""

# Recommended indexes for performance optimization

RECOMMENDED_INDEXES = """
-- Character queries (frequently accessed by user_id)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_characters_user_id ON characters(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_characters_created_at ON characters(created_at DESC);

-- Session queries (frequently accessed)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_character_id ON sessions(character_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_active ON sessions(active) WHERE active = TRUE;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);

-- Conversation messages (frequently queried by session)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_session_created ON messages(session_id, created_at DESC);

-- Inventory (frequently accessed with character_id)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_character_id ON inventory(character_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inventory_equipped ON inventory(character_id, equipped) WHERE equipped = TRUE;

-- Character spells (frequently accessed for spell management)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_character_spells_character_id ON character_spells(character_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_character_spells_prepared ON character_spells(character_id, is_prepared);

-- Memories (vector similarity searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_session_id ON memories(session_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_character_id ON memories(character_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);

-- Quests
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_character_quests_character_id ON character_quests(character_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_quests_state ON quests(state);

-- Active effects
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_active_effects_character_id ON active_effects(character_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_active_effects_expires_at ON active_effects(expires_at) WHERE expires_at IS NOT NULL;

-- Combat encounters
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_combat_encounters_session_id ON combat_encounters(session_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_combat_encounters_active ON combat_encounters(is_active) WHERE is_active = TRUE;

-- Composite indexes for common query patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_characters_user_level ON characters(user_id, level DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_session_role ON messages(session_id, role, created_at DESC);
"""

OPTIMIZATION_NOTES = """
Performance Optimization Notes:

1. **CONCURRENTLY**: Indexes are created concurrently to avoid locking tables
2. **Partial Indexes**: Used for common WHERE clauses (active=TRUE, equipped=TRUE)
3. **Composite Indexes**: For queries with multiple conditions (user_id + level)
4. **DESC Ordering**: For queries that ORDER BY created_at DESC

Query Optimization Tips:

1. Use `select_from()` with explicit joins instead of relationship loading
2. Use `options(selectinload())` for N+1 query prevention
3. Use `options(joinedload())` for single-object eager loading
4. Add `limit()` to all list queries
5. Use pagination (skip/limit) for large result sets
6. Cache frequently accessed data in Redis
7. Use `session.scalar()` instead of `session.scalars().first()` when fetching single records

Example Optimized Query:

```python
# Before (N+1 queries)
characters = await db.execute(select(Character).where(Character.user_id == user_id))
for character in characters.scalars():
    print(character.spells)  # N additional queries!

# After (eager loading)
from sqlalchemy.orm import selectinload

characters = await db.execute(
    select(Character)
    .where(Character.user_id == user_id)
    .options(selectinload(Character.spells))
    .limit(100)
)
for character in characters.scalars():
    print(character.spells)  # No additional queries!
```
"""


def print_recommendations():
    """Print index recommendations"""
    print("=" * 80)
    print("DATABASE INDEX RECOMMENDATIONS")
    print("=" * 80)
    print("\nTo apply these indexes, run:")
    print("  python -m scripts.apply_indexes")
    print("\nOr manually execute in PostgreSQL:")
    print(RECOMMENDED_INDEXES)
    print("\n" + "=" * 80)
    print(OPTIMIZATION_NOTES)


if __name__ == "__main__":
    print_recommendations()
