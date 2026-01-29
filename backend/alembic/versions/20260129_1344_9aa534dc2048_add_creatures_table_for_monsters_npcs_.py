"""add creatures table for monsters npcs and companions

Revision ID: 9aa534dc2048
Revises: 947d662450ab
Create Date: 2026-01-29 13:44:27.352494

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "9aa534dc2048"
down_revision = "947d662450ab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create creatures table
    op.create_table(
        "creatures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("size", sa.String(length=20), nullable=True),
        sa.Column("creature_type", sa.String(length=50), nullable=True),
        sa.Column("alignment", sa.String(length=50), nullable=True),
        sa.Column("ac", sa.Integer(), nullable=True),
        sa.Column("armor_type", sa.String(length=100), nullable=True),
        sa.Column("hp", sa.Integer(), nullable=True),
        sa.Column("hit_dice", sa.String(length=50), nullable=True),
        sa.Column("speed", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("strength", sa.Integer(), nullable=True),
        sa.Column("dexterity", sa.Integer(), nullable=True),
        sa.Column("constitution", sa.Integer(), nullable=True),
        sa.Column("intelligence", sa.Integer(), nullable=True),
        sa.Column("wisdom", sa.Integer(), nullable=True),
        sa.Column("charisma", sa.Integer(), nullable=True),
        sa.Column("saving_throws", sa.Text(), nullable=True),
        sa.Column("skills", sa.Text(), nullable=True),
        sa.Column("damage_resistances", sa.Text(), nullable=True),
        sa.Column("damage_immunities", sa.Text(), nullable=True),
        sa.Column("condition_immunities", sa.Text(), nullable=True),
        sa.Column("senses", sa.Text(), nullable=True),
        sa.Column("languages", sa.Text(), nullable=True),
        sa.Column("cr", sa.String(length=10), nullable=True),
        sa.Column("xp", sa.String(length=100), nullable=True),
        sa.Column("actions", sa.Text(), nullable=True),
        sa.Column("legendary_actions", sa.Text(), nullable=True),
        sa.Column("traits", sa.Text(), nullable=True),
        sa.Column("dc", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for common queries
    op.create_index("idx_creature_name_search", "creatures", ["name"])
    op.create_index("idx_creature_type_cr", "creatures", ["creature_type", "cr"])
    op.create_index("idx_creature_cr", "creatures", ["cr"])
    op.create_index(op.f("ix_creatures_id"), "creatures", ["id"], unique=False)
    op.create_index(op.f("ix_creatures_name"), "creatures", ["name"], unique=False)
    op.create_index(
        op.f("ix_creatures_creature_type"), "creatures", ["creature_type"], unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_creatures_creature_type"), table_name="creatures")
    op.drop_index(op.f("ix_creatures_name"), table_name="creatures")
    op.drop_index(op.f("ix_creatures_id"), table_name="creatures")
    op.drop_index("idx_creature_cr", table_name="creatures")
    op.drop_index("idx_creature_type_cr", table_name="creatures")
    op.drop_index("idx_creature_name_search", table_name="creatures")

    # Drop table
    op.drop_table("creatures")
