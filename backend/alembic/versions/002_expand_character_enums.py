"""Expand character class and race enums to support all D&D 5e options

Revision ID: 002
Revises: 001
Create Date: 2026-01-01 00:00:00

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add new character classes and races to enums."""
    # Add new character classes (8 new classes)
    op.execute("ALTER TYPE characterclass ADD VALUE IF NOT EXISTS 'Barbarian'")
    op.execute("ALTER TYPE characterclass ADD VALUE IF NOT EXISTS 'Bard'")
    op.execute("ALTER TYPE characterclass ADD VALUE IF NOT EXISTS 'Druid'")
    op.execute("ALTER TYPE characterclass ADD VALUE IF NOT EXISTS 'Monk'")
    op.execute("ALTER TYPE characterclass ADD VALUE IF NOT EXISTS 'Paladin'")
    op.execute("ALTER TYPE characterclass ADD VALUE IF NOT EXISTS 'Ranger'")
    op.execute("ALTER TYPE characterclass ADD VALUE IF NOT EXISTS 'Sorcerer'")
    op.execute("ALTER TYPE characterclass ADD VALUE IF NOT EXISTS 'Warlock'")
    
    # Add new character races (5 new races)
    op.execute("ALTER TYPE characterrace ADD VALUE IF NOT EXISTS 'Dragonborn'")
    op.execute("ALTER TYPE characterrace ADD VALUE IF NOT EXISTS 'Gnome'")
    op.execute("ALTER TYPE characterrace ADD VALUE IF NOT EXISTS 'Half-Elf'")
    op.execute("ALTER TYPE characterrace ADD VALUE IF NOT EXISTS 'Half-Orc'")
    op.execute("ALTER TYPE characterrace ADD VALUE IF NOT EXISTS 'Tiefling'")


def downgrade() -> None:
    """PostgreSQL does not support removing enum values.
    
    To downgrade, you would need to:
    1. Remove all rows using the new enum values
    2. Recreate the enum type with only the old values
    3. Update all tables to use the new type
    
    This is complex and risky, so we don't implement it here.
    """
    ...
