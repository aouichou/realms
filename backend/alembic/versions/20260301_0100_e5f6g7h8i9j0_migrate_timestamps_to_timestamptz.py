"""Migrate all timestamp columns from TIMESTAMP to TIMESTAMPTZ

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-03-01 01:00:00.000000

Changes:
- Alter all DateTime columns across all tables from TIMESTAMP WITHOUT TIME ZONE
  to TIMESTAMP WITH TIME ZONE (TIMESTAMPTZ).
- Existing naive timestamps are interpreted as UTC during conversion.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6g7h8i9j0"
down_revision: str | None = "d4e5f6g7h8i9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# All (table_name, column_name) pairs that need migration
TIMESTAMP_COLUMNS = [
    # users
    ("users", "created_at"),
    ("users", "last_login"),
    ("users", "updated_at"),
    # adventures
    ("adventures", "created_at"),
    ("adventures", "updated_at"),
    # adventure_memories
    ("adventure_memories", "timestamp"),
    ("adventure_memories", "created_at"),
    # characters
    ("characters", "created_at"),
    ("characters", "updated_at"),
    ("characters", "deleted_at"),
    # character_spells
    ("character_spells", "created_at"),
    # character_conditions
    ("character_conditions", "applied_at"),
    # character_quests
    ("character_quests", "accepted_at"),
    # companions
    ("companions", "created_at"),
    ("companions", "updated_at"),
    # companion_conversations
    ("companion_conversations", "created_at"),
    # game_sessions
    ("game_sessions", "started_at"),
    ("game_sessions", "last_activity_at"),
    # encounters
    ("encounters", "started_at"),
    ("encounters", "ended_at"),
    # combat_encounters
    ("combat_encounters", "started_at"),
    ("combat_encounters", "ended_at"),
    # conversation_messages
    ("conversation_messages", "created_at"),
    # spells
    ("spells", "created_at"),
    # items
    ("items", "created_at"),
    # quests
    ("quests", "created_at"),
    ("quests", "updated_at"),
    # active_effects
    ("active_effects", "expires_at"),
    ("active_effects", "created_at"),
    ("active_effects", "updated_at"),
    # generated_images
    ("generated_images", "created_at"),
    ("generated_images", "last_used_at"),
]


def upgrade() -> None:
    # Convert all TIMESTAMP WITHOUT TIME ZONE → TIMESTAMP WITH TIME ZONE
    # PostgreSQL interprets existing naive values as UTC during this conversion
    for table, column in TIMESTAMP_COLUMNS:
        op.execute(
            sa.text(
                f'ALTER TABLE {table} ALTER COLUMN "{column}" '
                f"TYPE TIMESTAMP WITH TIME ZONE "
                f"USING \"{column}\" AT TIME ZONE 'UTC'"
            )
        )


def downgrade() -> None:
    # Revert TIMESTAMP WITH TIME ZONE → TIMESTAMP WITHOUT TIME ZONE
    for table, column in TIMESTAMP_COLUMNS:
        op.execute(
            sa.text(
                f'ALTER TABLE {table} ALTER COLUMN "{column}" '
                f"TYPE TIMESTAMP WITHOUT TIME ZONE "
                f"USING \"{column}\" AT TIME ZONE 'UTC'"
            )
        )
