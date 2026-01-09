"""add_preferred_language_to_user

Revision ID: 7526be5a8d04
Revises: e9af717b27c8
Create Date: 2026-01-09 22:12:45.518475

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "7526be5a8d04"
down_revision = "e9af717b27c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add preferred_language column to users table
    op.add_column(
        "users",
        sa.Column("preferred_language", sa.String(length=5), nullable=False, server_default="en"),
    )


def downgrade() -> None:
    # Remove preferred_language column from users table
    op.drop_column("users", "preferred_language")
