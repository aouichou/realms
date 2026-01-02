"""Make game_sessions.user_id nullable for development without auth

Revision ID: 003
Revises: 002
Create Date: 2026-01-01 00:10:00

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Make user_id nullable in game_sessions table."""
    op.alter_column('game_sessions', 'user_id', nullable=True)


def downgrade() -> None:
    """Revert user_id to NOT NULL."""
    # First remove any rows with NULL user_id
    op.execute("DELETE FROM game_sessions WHERE user_id IS NULL")
    # Then make it NOT NULL again
    op.alter_column('game_sessions', 'user_id', nullable=False)
