"""add companions table for AI-driven NPCs

Revision ID: 20260129_1700
Revises: 9aa534dc2048
Create Date: 2026-01-29 17:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260129_1700"
down_revision = "9aa534dc2048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create companions table
    op.create_table(
        "companions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("creature_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("creature_name", sa.String(length=100), nullable=False),
        sa.Column("personality", sa.Text(), nullable=False),
        sa.Column("goals", sa.Text(), nullable=True),
        sa.Column("secrets", sa.Text(), nullable=True),
        sa.Column("background", sa.Text(), nullable=True),
        sa.Column("relationship_status", sa.String(length=50), nullable=True),
        sa.Column("loyalty", sa.Integer(), nullable=True),
        sa.Column("hp", sa.Integer(), nullable=False),
        sa.Column("max_hp", sa.Integer(), nullable=False),
        sa.Column("ac", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=True),
        sa.Column("dexterity", sa.Integer(), nullable=True),
        sa.Column("constitution", sa.Integer(), nullable=True),
        sa.Column("intelligence", sa.Integer(), nullable=True),
        sa.Column("wisdom", sa.Integer(), nullable=True),
        sa.Column("charisma", sa.Integer(), nullable=True),
        sa.Column("actions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("special_traits", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("speed", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("conversation_memory", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("important_events", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_alive", sa.Boolean(), nullable=True),
        sa.Column("death_save_successes", sa.Integer(), nullable=True),
        sa.Column("death_save_failures", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"],
            ["characters.id"],
        ),
        sa.ForeignKeyConstraint(
            ["creature_id"],
            ["creatures.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        op.f("ix_companions_character_id"), "companions", ["character_id"], unique=False
    )
    op.create_index(op.f("ix_companions_creature_id"), "companions", ["creature_id"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_companions_creature_id"), table_name="companions")
    op.drop_index(op.f("ix_companions_character_id"), table_name="companions")

    # Drop table
    op.drop_table("companions")
