"""fix_inventory_system

Revision ID: 004
Revises: 003
Create Date: 2026-01-14 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    """Add inventory system tables and ItemType enum"""

    # Create ItemType enum using raw SQL with IF NOT EXISTS
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'itemtype') THEN
                CREATE TYPE itemtype AS ENUM ('weapon', 'armor', 'consumable', 'quest', 'misc');
            END IF;
        END $$;
    """)

    # Create items table
    op.create_table(
        "items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "character_id",
            UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "item_type",
            sa.Enum(
                "weapon", "armor", "consumable", "quest", "misc", name="itemtype", create_type=False
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("weight", sa.Integer, default=0, nullable=False),
        sa.Column("value", sa.Integer, default=0, nullable=False),
        sa.Column("properties", JSONB, nullable=True, default=dict),
        sa.Column("equipped", sa.Boolean, default=False, nullable=False),
        sa.Column("quantity", sa.Integer, default=1, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    """Remove inventory system"""
    op.drop_table("items")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS itemtype CASCADE;")
