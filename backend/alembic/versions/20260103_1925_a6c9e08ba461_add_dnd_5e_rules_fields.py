"""Add D&D 5e rules fields (skills, spells, ASI)

Revision ID: a6c9e08ba461
Revises: 8fdec8b4060e
Create Date: 2026-01-03 19:25:57.155957

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a6c9e08ba461'
down_revision: Union[str, None] = '8fdec8b4060e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add D&D 5e rules fields to characters table."""
    # Add skill proficiencies (list of skill names)
    op.add_column('characters', sa.Column(
        'skill_proficiencies',
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default='[]'
    ))
    
    # Add known spells (for Bard, Sorcerer, Ranger, Warlock, etc.)
    op.add_column('characters', sa.Column(
        'known_spells',
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default='[]'
    ))
    
    # Add prepared spells (for Wizard, Cleric, Druid, Paladin)
    op.add_column('characters', sa.Column(
        'prepared_spells',
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default='[]'
    ))
    
    # Add cantrips known
    op.add_column('characters', sa.Column(
        'cantrips',
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default='[]'
    ))
    
    # Add ASI distribution tracking
    # Format: {"4": {"strength": 2}, "8": {"dexterity": 1, "constitution": 1}, ...}
    op.add_column('characters', sa.Column(
        'asi_distribution',
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        server_default='{}'
    ))


def downgrade() -> None:
    """Remove D&D 5e rules fields from characters table."""
    op.drop_column('characters', 'asi_distribution')
    op.drop_column('characters', 'cantrips')
    op.drop_column('characters', 'prepared_spells')
    op.drop_column('characters', 'known_spells')
    op.drop_column('characters', 'skill_proficiencies')
