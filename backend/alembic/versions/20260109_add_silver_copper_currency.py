"""add silver and copper currency

Revision ID: 20260109_add_currency
Revises:
Create Date: 2026-01-09

D&D 5e Currency System:
- 1 gold piece (gp) = 10 silver pieces (sp)
- 1 silver piece (sp) = 10 copper pieces (cp)
- 1 gold piece (gp) = 100 copper pieces (cp)
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260109_add_currency"
down_revision = "7526be5a8d04"  # Points to add_preferred_language_to_user
branch_labels = None
depends_on = None


def upgrade():
    # Add silver and copper columns to characters table
    op.add_column(
        "characters", sa.Column("silver", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "characters", sa.Column("copper", sa.Integer(), nullable=False, server_default="0")
    )


def downgrade():
    op.drop_column("characters", "copper")
    op.drop_column("characters", "silver")
