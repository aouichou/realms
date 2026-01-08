"""add spell upcasting and concentration

Revision ID: 20260107_1000
Revises: 20260105_1944_b9cb7c68a254
Create Date: 2026-01-07 10:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260107_1000"
down_revision: Union[str, None] = "20260105_1944_b9cb7c68a254"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new fields to spells table
    op.add_column("spells", sa.Column("upcast_damage_dice", sa.String(length=20), nullable=True))
    op.add_column("spells", sa.Column("material_cost", sa.Integer(), nullable=True))
    op.add_column(
        "spells",
        sa.Column("material_consumed", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Add active concentration tracking to characters table
    from sqlalchemy.dialects import postgresql

    op.add_column(
        "characters",
        sa.Column("active_concentration_spell", postgresql.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    # Remove concentration tracking from characters
    op.drop_column("characters", "active_concentration_spell")

    # Remove new spell fields
    op.drop_column("spells", "material_consumed")
    op.drop_column("spells", "material_cost")
    op.drop_column("spells", "upcast_damage_dice")
