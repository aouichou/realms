"""add_summary_event_type

Revision ID: 86f37dd0b8cc
Revises: 001
Create Date: 2026-01-22 17:13:25.329681

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "86f37dd0b8cc"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'summary' value to eventtype ENUM
    # PostgreSQL requires special handling for adding enum values
    op.execute("ALTER TYPE eventtype ADD VALUE IF NOT EXISTS 'summary'")


def downgrade() -> None:
    # Removing enum values is complex in PostgreSQL and rarely needed
    # For safety, we skip downgrade (summary memories would just remain in DB)
    pass
