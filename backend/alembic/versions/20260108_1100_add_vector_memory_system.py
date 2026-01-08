"""add vector memory system with pgvector

Revision ID: 20260108_1100
Revises: 20260107_1000
Create Date: 2026-01-08 11:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260108_1100"
down_revision: Union[str, None] = "20260107_1000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create event_type enum
    event_type_enum = postgresql.ENUM(
        "combat",
        "dialogue",
        "discovery",
        "decision",
        "quest",
        "npc_interaction",
        "loot",
        "location",
        "other",
        name="eventtype",
        create_type=False,
    )
    event_type_enum.create(op.get_bind(), checkfirst=True)

    # Create adventure_memories table
    op.create_table(
        "adventure_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", event_type_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float(), dimensions=1), nullable=True),
        sa.Column("importance", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("npcs_involved", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("locations", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("items_involved", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["game_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_memories_session", "adventure_memories", ["session_id"], unique=False)
    op.create_index("ix_memories_importance", "adventure_memories", ["importance"], unique=False)
    op.create_index("ix_memories_timestamp", "adventure_memories", ["timestamp"], unique=False)
    op.create_index("ix_memories_event_type", "adventure_memories", ["event_type"], unique=False)

    # Create GIN index for tags array
    op.execute("CREATE INDEX ix_memories_tags ON adventure_memories USING GIN(tags)")

    # Create vector index using ivfflat for fast similarity search
    # Note: This will be created after some data is inserted (needs training data)
    # For now, we'll use default sequential scan which works fine for small datasets


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_memories_tags")
    op.drop_index("ix_memories_event_type", table_name="adventure_memories")
    op.drop_index("ix_memories_timestamp", table_name="adventure_memories")
    op.drop_index("ix_memories_importance", table_name="adventure_memories")
    op.drop_index("ix_memories_session", table_name="adventure_memories")

    # Drop table
    op.drop_table("adventure_memories")

    # Drop enum
    sa.Enum(name="eventtype").drop(op.get_bind(), checkfirst=True)

    # Note: We don't drop the vector extension as it might be used elsewhere
