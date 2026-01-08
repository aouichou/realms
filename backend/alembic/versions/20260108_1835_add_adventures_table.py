"""add_adventures_table

Revision ID: 20260108_1835
Revises: 20260108_1824
Create Date: 2026-01-08 18:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260108_1835"
down_revision: Union[str, None] = "20260108_1824"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create adventures table
    op.create_table(
        "adventures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("setting", sa.String(100), nullable=False),
        sa.Column("goal", sa.String(100), nullable=False),
        sa.Column("tone", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scenes", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create indexes
    op.create_index("ix_adventures_character_id", "adventures", ["character_id"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_adventures_character_id", "adventures")

    # Drop table
    op.drop_table("adventures")
