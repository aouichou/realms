"""Add soft delete support for characters

Revision ID: 20260123_1510
Revises: 20260122_1713_86f37dd0b8cc
Create Date: 2026-01-23 15:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260123_1510"
down_revision: Union[str, None] = "86f37dd0b8cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add deleted_at column for soft delete functionality."""
    # Add deleted_at column to characters table
    op.add_column(
        "characters",
        sa.Column("deleted_at", sa.DateTime(), nullable=True, comment="Soft delete timestamp"),
    )

    # Add index for efficient querying of non-deleted characters
    op.create_index("ix_characters_deleted_at", "characters", ["deleted_at"], unique=False)


def downgrade() -> None:
    """Remove soft delete functionality."""
    # Drop index
    op.drop_index("ix_characters_deleted_at", table_name="characters")

    # Drop deleted_at column
    op.drop_column("characters", "deleted_at")
