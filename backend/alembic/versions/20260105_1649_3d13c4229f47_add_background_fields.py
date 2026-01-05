"""add_background_fields

Revision ID: 3d13c4229f47
Revises: 48f7dee6983d
Create Date: 2026-01-05 16:49:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d13c4229f47"
down_revision: Union[str, None] = "48f7dee6983d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add background fields to characters table
    op.add_column("characters", sa.Column("background_name", sa.String(), nullable=True))
    op.add_column("characters", sa.Column("background_description", sa.String(), nullable=True))
    op.add_column(
        "characters", sa.Column("background_skill_proficiencies", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    # Remove background fields from characters table
    op.drop_column("characters", "background_skill_proficiencies")
    op.drop_column("characters", "background_description")
    op.drop_column("characters", "background_name")
