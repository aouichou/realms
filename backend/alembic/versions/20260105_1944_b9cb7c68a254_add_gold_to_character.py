"""add_gold_to_character

Revision ID: b9cb7c68a254
Revises: 3d13c4229f47
Create Date: 2026-01-05 19:44:40.212299

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b9cb7c68a254'
down_revision = '3d13c4229f47'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add gold column to characters table
    op.add_column('characters', sa.Column('gold', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    # Remove gold column from characters table
    op.drop_column('characters', 'gold')
