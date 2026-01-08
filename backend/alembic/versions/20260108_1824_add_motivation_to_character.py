"""add_motivation_to_character

Revision ID: 20260108_1824
Revises: 20260108_1100
Create Date: 2026-01-08 18:24:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260108_1824"
down_revision: Union[str, None] = "20260108_1100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add motivation field to characters table
    op.add_column("characters", sa.Column("motivation", sa.String(100), nullable=True))


def downgrade() -> None:
    # Remove motivation field from characters table
    op.drop_column("characters", "motivation")
