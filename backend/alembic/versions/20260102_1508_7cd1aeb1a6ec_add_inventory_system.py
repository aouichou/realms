"""add_inventory_system

Revision ID: 7cd1aeb1a6ec
Revises: 003
Create Date: 2026-01-02 15:08:12.621870

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '7cd1aeb1a6ec'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ItemType enum
    item_type_enum = sa.Enum(
        'weapon', 'armor', 'consumable', 'quest', 'misc',
        name='itemtype',
        create_type=True
    )
    item_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Add carrying_capacity column to characters table
    op.add_column('characters',
        sa.Column('carrying_capacity', sa.Integer(), nullable=False, server_default='150')
    )
    
    # Create items table
    op.create_table('items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('character_id', UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('item_type', item_type_enum, nullable=False),
        sa.Column('weight', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('value', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('properties', JSONB, nullable=True),
        sa.Column('equipped', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_items_character_id', 'items', ['character_id'])
    op.create_index('ix_items_character_type', 'items', ['character_id', 'item_type'])
    op.create_index('ix_items_character_equipped', 'items', ['character_id', 'equipped'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_items_character_equipped', 'items')
    op.drop_index('ix_items_character_type', 'items')
    op.drop_index('ix_items_character_id', 'items')
    
    # Drop items table
    op.drop_table('items')
    
    # Drop ItemType enum
    item_type_enum = sa.Enum(name='itemtype')
    item_type_enum.drop(op.get_bind(), checkfirst=True)
    
    # Remove carrying_capacity column
    op.drop_column('characters', 'carrying_capacity')
