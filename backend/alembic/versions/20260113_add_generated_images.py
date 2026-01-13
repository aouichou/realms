"""Add generated_images table for image cataloguing

Revision ID: 20260113_add_generated_images
Revises:
Create Date: 2026-01-13

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260113_add_generated_images"
down_revision: Union[str, None] = "20260109_add_currency"  # Points to latest migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create generated_images table"""
    op.create_table(
        "generated_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("description_hash", sa.String(length=32), nullable=False),
        sa.Column("description_text", sa.Text(), nullable=False),
        sa.Column("image_path", sa.String(length=255), nullable=False),
        sa.Column(
            "model_used",
            sa.String(length=50),
            nullable=True,
            server_default="mistral-medium-latest",
        ),
        sa.Column("reuse_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index(
        "ix_generated_images_description_hash",
        "generated_images",
        ["description_hash"],
        unique=True,
    )
    op.create_index("ix_generated_images_id", "generated_images", ["id"], unique=False)


def downgrade() -> None:
    """Drop generated_images table"""
    op.drop_index("ix_generated_images_id", table_name="generated_images")
    op.drop_index("ix_generated_images_description_hash", table_name="generated_images")
    op.drop_table("generated_images")
