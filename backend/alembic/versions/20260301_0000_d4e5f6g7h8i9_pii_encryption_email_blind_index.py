"""PII encryption: widen email column and add email_blind_index

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-03-01 00:00:00.000000

Changes:
- Alter users.email from String(255) to String(512) (encrypted values are longer)
- Drop unique constraint and index on email (encrypted values aren't unique-able)
- Add email_blind_index column (String(64), unique, indexed) for lookups
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: str | None = "c3d4e5f6g7h8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Widen email column to accommodate encrypted (base64) values
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(255),
        type_=sa.String(512),
        existing_nullable=True,
    )

    # 2. Drop old index on email (if exists)
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE tablename='users' AND indexname='ix_users_email'")
    )
    if result.fetchone():
        op.drop_index("ix_users_email", table_name="users")

    # 3. Drop old unique constraint on email (if exists)
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_constraint "
            "WHERE conrelid='users'::regclass AND conname='users_email_key'"
        )
    )
    if result.fetchone():
        op.drop_constraint("users_email_key", "users", type_="unique")

    # 4. Add email_blind_index column for deterministic lookups (if not exists)
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='email_blind_index'"
        )
    )
    if not result.fetchone():
        op.add_column(
            "users",
            sa.Column("email_blind_index", sa.String(64), nullable=True),
        )
    op.create_unique_constraint("uq_users_email_blind_index", "users", ["email_blind_index"])
    op.create_index("ix_users_email_blind_index", "users", ["email_blind_index"])


def downgrade() -> None:
    # Remove blind index
    op.drop_index("ix_users_email_blind_index", table_name="users")
    op.drop_constraint("uq_users_email_blind_index", "users", type_="unique")
    op.drop_column("users", "email_blind_index")

    # Restore email unique constraint and index
    op.create_unique_constraint("users_email_key", "users", ["email"])
    op.create_index("ix_users_email", "users", ["email"])

    # Shrink email column back
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(512),
        type_=sa.String(255),
        existing_nullable=True,
    )
