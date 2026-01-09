"""add_active_effects_table

Revision ID: e9af717b27c8
Revises: 20260108_1835
Create Date: 2026-01-09 20:39:24.237728

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e9af717b27c8'
down_revision = '20260108_1835'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'active_effects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('character_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('effect_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=200), nullable=True),
        sa.Column('source_character_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('duration_type', sa.String(length=50), nullable=False),
        sa.Column('duration_value', sa.Integer(), nullable=True),
        sa.Column('rounds_remaining', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('bonus_value', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('dice_bonus', sa.String(length=20), nullable=True),
        sa.Column('advantage', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('disadvantage', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('stacks', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('stack_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('requires_concentration', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('concentration_dc', sa.Integer(), nullable=True, server_default='10'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['game_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_active_effects_character_id', 'active_effects', ['character_id'])
    op.create_index('ix_active_effects_session_id', 'active_effects', ['session_id'])
    op.create_index('ix_active_effects_is_active', 'active_effects', ['is_active'])


def downgrade() -> None:
    op.drop_index('ix_active_effects_is_active', table_name='active_effects')
    op.drop_index('ix_active_effects_session_id', table_name='active_effects')
    op.drop_index('ix_active_effects_character_id', table_name='active_effects')
    op.drop_table('active_effects')
