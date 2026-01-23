"""add_generated_images_table

Revision ID: 947d662450ab
Revises: 20260123_1510
Create Date: 2026-01-23 19:23:02.048045

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "947d662450ab"
down_revision = "20260123_1510"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create generated_images table for scene image caching
    op.create_table(
        "generated_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("description_hash", sa.String(length=32), nullable=False),
        sa.Column("description_text", sa.Text(), nullable=False),
        sa.Column("image_path", sa.String(length=255), nullable=False),
        sa.Column("model_used", sa.String(length=50), nullable=True),
        sa.Column("reuse_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_generated_images_description_hash"),
        "generated_images",
        ["description_hash"],
        unique=True,
    )
    op.create_index(op.f("ix_generated_images_id"), "generated_images", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_generated_images_id"), table_name="generated_images")
    op.drop_index(op.f("ix_generated_images_description_hash"), table_name="generated_images")
    op.drop_table("generated_images")
