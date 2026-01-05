"""add_personality_system_fields

Revision ID: 48f7dee6983d
Revises: b7d4e9f5c2a3
Create Date: 2026-01-05 16:05:52.190655

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "48f7dee6983d"
down_revision = "b7d4e9f5c2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add D&D 5e personality system fields to characters table
    op.add_column("characters", sa.Column("personality_trait", sa.Text(), nullable=True))
    op.add_column("characters", sa.Column("ideal", sa.Text(), nullable=True))
    op.add_column("characters", sa.Column("bond", sa.Text(), nullable=True))
    op.add_column("characters", sa.Column("flaw", sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove personality system fields
    op.drop_column("characters", "flaw")
    op.drop_column("characters", "bond")
    op.drop_column("characters", "ideal")
    op.drop_column("characters", "personality_trait")
