"""RL-304: Add performance indexes for slow queries

Revision ID: f1a2b3c4d5e6
Revises: e5f6g7h8i9j0
Create Date: 2026-03-05 00:00:00.000000+00:00

Addresses production slow queries:
  - SELECT adventure_memories... (1.024s)
  - POST /api/v1/game/save (1.542s)
  - POST /api/v1/conversations/action (22.205s)
  - SELECT users... (0.612s)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "e5f6g7h8i9j0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adventure Memories - composite indexes for search_memories() / get_recent_memories()
    op.create_index(
        "idx_memories_session_importance",
        "adventure_memories",
        ["session_id", "importance", "timestamp"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_memories_session_created",
        "adventure_memories",
        ["session_id", "created_at"],
        if_not_exists=True,
    )

    # Game Sessions - composite for user session listing & active session lookups
    op.create_index(
        "idx_sessions_user_activity",
        "game_sessions",
        ["user_id", "last_activity_at"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_sessions_active_partial",
        "game_sessions",
        ["user_id", "character_id"],
        postgresql_where="is_active = TRUE",
        if_not_exists=True,
    )

    # Characters - composite for level-sorted lists
    op.create_index(
        "idx_characters_user_level",
        "characters",
        ["user_id", "level"],
        if_not_exists=True,
    )

    # Conversation Messages - composite for role-filtered queries
    op.create_index(
        "idx_messages_session_role",
        "conversation_messages",
        ["session_id", "role", "created_at"],
        if_not_exists=True,
    )

    # Active Effects - partial indexes
    op.create_index(
        "idx_effects_char_active",
        "active_effects",
        ["character_id", "session_id"],
        postgresql_where="is_active = TRUE",
        if_not_exists=True,
    )
    op.create_index(
        "idx_effects_expires",
        "active_effects",
        ["expires_at"],
        postgresql_where="expires_at IS NOT NULL",
        if_not_exists=True,
    )

    # Combat Encounters - partial index for active combats
    op.create_index(
        "idx_combat_active_partial",
        "combat_encounters",
        ["session_id"],
        postgresql_where="is_active = TRUE",
        if_not_exists=True,
    )

    # Companions - partial index for active alive companions
    op.create_index(
        "idx_companions_char_active",
        "companions",
        ["character_id"],
        postgresql_where="is_active = TRUE AND is_alive = TRUE",
        if_not_exists=True,
    )

    # Character Quests - composite for quest-join queries
    op.create_index(
        "idx_character_quests_quest",
        "character_quests",
        ["character_id", "quest_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("idx_memories_session_importance", table_name="adventure_memories")
    op.drop_index("idx_memories_session_created", table_name="adventure_memories")
    op.drop_index("idx_sessions_user_activity", table_name="game_sessions")
    op.drop_index("idx_sessions_active_partial", table_name="game_sessions")
    op.drop_index("idx_characters_user_level", table_name="characters")
    op.drop_index("idx_messages_session_role", table_name="conversation_messages")
    op.drop_index("idx_effects_char_active", table_name="active_effects")
    op.drop_index("idx_effects_expires", table_name="active_effects")
    op.drop_index("idx_combat_active_partial", table_name="combat_encounters")
    op.drop_index("idx_companions_char_active", table_name="companions")
    op.drop_index("idx_character_quests_quest", table_name="character_quests")
