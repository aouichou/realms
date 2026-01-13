"""fix npcs_involved type from UUID[] to String[]

Revision ID: 20260113_fix_npcs
Revises: 20260113_add_generated_images
Create Date: 2026-01-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260113_fix_npcs"
down_revision: Union[str, None] = "20260113_add_generated_images"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change npcs_involved from ARRAY(UUID) to ARRAY(String)

    This allows storing NPC names directly instead of requiring UUID references.
    NPCs in the game are often unnamed ("bandit", "guard", "barkeep") and no NPC
    database table exists yet. String names are more useful for semantic search.
    """
    # Drop the existing column
    op.drop_column("adventure_memories", "npcs_involved")

    # Re-create it with String[] type
    op.add_column(
        "adventure_memories",
        sa.Column("npcs_involved", postgresql.ARRAY(sa.String()), nullable=True),
    )


def downgrade() -> None:
    """Revert npcs_involved back to ARRAY(UUID)"""
    # Drop the String[] column
    op.drop_column("adventure_memories", "npcs_involved")

    # Re-create it with UUID[] type
    op.add_column(
        "adventure_memories",
        sa.Column("npcs_involved", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
    )
