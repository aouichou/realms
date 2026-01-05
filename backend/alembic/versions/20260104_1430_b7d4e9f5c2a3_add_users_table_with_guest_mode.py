"""add_users_table_with_guest_mode

Revision ID: b7d4e9f5c2a3
Revises: a6c9e08ba461
Create Date: 2026-01-04 14:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d4e9f5c2a3"
down_revision: Union[str, None] = "a6c9e08ba461"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add guest mode fields to existing users table"""

    # Add new columns
    op.add_column(
        "users", sa.Column("is_guest", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column("users", sa.Column("guest_token", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("last_login", sa.DateTime(timezone=True), nullable=True))

    # Make email nullable for guest mode
    op.alter_column("users", "email", nullable=True)

    # Make hashed_password nullable
    op.alter_column("users", "hashed_password", nullable=True)

    # Rename hashed_password to password_hash
    op.alter_column("users", "hashed_password", new_column_name="password_hash")

    # Create index for guest_token
    op.create_index(
        "idx_users_guest_token",
        "users",
        ["guest_token"],
        unique=True,
        postgresql_where=sa.text("guest_token IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove guest mode fields from users table"""

    # Drop guest mode indexes
    op.drop_index("idx_users_guest_token", "users")

    # Revert column name
    op.alter_column("users", "password_hash", new_column_name="hashed_password")

    # Revert column nullability
    op.alter_column("users", "hashed_password", nullable=False)
    op.alter_column("users", "email", nullable=False)

    # Drop guest mode columns
    op.drop_column("users", "last_login")
    op.drop_column("users", "guest_token")
    op.drop_column("users", "is_guest")
