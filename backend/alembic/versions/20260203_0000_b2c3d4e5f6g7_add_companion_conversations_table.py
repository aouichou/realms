"""add_companion_conversations_table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-03 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6g7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create companion_conversations table for storing shared player-companion chats."""
    op.create_table(
        "companion_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "companion_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("shared_with_dm", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["character_id"],
            ["characters.id"],
        ),
        sa.ForeignKeyConstraint(
            ["companion_id"],
            ["companions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add indexes for efficient queries
    op.create_index(
        op.f("ix_companion_conversations_id"),
        "companion_conversations",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_companion_conversations_companion_id"),
        "companion_conversations",
        ["companion_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_companion_conversations_character_id"),
        "companion_conversations",
        ["character_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_companion_conversations_shared_with_dm"),
        "companion_conversations",
        ["shared_with_dm"],
        unique=False,
    )
    op.create_index(
        op.f("ix_companion_conversations_created_at"),
        "companion_conversations",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove companion_conversations table."""
    op.drop_index(
        op.f("ix_companion_conversations_created_at"),
        table_name="companion_conversations",
    )
    op.drop_index(
        op.f("ix_companion_conversations_shared_with_dm"),
        table_name="companion_conversations",
    )
    op.drop_index(
        op.f("ix_companion_conversations_character_id"),
        table_name="companion_conversations",
    )
    op.drop_index(
        op.f("ix_companion_conversations_companion_id"),
        table_name="companion_conversations",
    )
    op.drop_index(
        op.f("ix_companion_conversations_id"),
        table_name="companion_conversations",
    )
    op.drop_table("companion_conversations")
