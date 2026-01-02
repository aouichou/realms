"""add_combat_encounters

Revision ID: a4353768274f
Revises: 873c750f27e1
Create Date: 2026-01-02 14:58:22.642759

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a4353768274f'
down_revision = '873c750f27e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create combat_encounters table
    op.create_table(
        'combat_encounters',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('current_turn', sa.Integer(), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('participants', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('turn_order', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('combat_log', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['game_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_combat_encounters_session_id', 'combat_encounters', ['session_id'], unique=False)
    op.create_index('ix_combat_encounters_is_active', 'combat_encounters', ['is_active'], unique=False)
    op.create_index('ix_combat_session_active', 'combat_encounters', ['session_id', 'is_active'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_combat_session_active', table_name='combat_encounters')
    op.drop_index('ix_combat_encounters_is_active', table_name='combat_encounters')
    op.drop_index('ix_combat_encounters_session_id', table_name='combat_encounters')
    op.drop_table('combat_encounters')

