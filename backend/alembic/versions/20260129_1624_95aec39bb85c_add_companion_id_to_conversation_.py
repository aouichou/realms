"""Add companion_id to conversation messages

Revision ID: 95aec39bb85c
Revises: 20260129_1700
Create Date: 2026-01-29 16:24:44.508662

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "95aec39bb85c"
down_revision = "20260129_1700"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add companion_id column to conversation_messages table
    op.add_column(
        "conversation_messages",
        sa.Column("companion_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Add foreign key constraint to companions table
    op.create_foreign_key(
        "fk_conversation_messages_companion_id",
        "conversation_messages",
        "companions",
        ["companion_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint(
        "fk_conversation_messages_companion_id", "conversation_messages", type_="foreignkey"
    )

    # Drop companion_id column
    op.drop_column("conversation_messages", "companion_id")
