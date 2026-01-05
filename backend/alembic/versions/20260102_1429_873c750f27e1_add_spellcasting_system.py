"""add_spellcasting_system

Revision ID: 873c750f27e1
Revises: 7cd1aeb1a6ec
Create Date: 2026-01-02 14:29:44.237080

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "873c750f27e1"
down_revision = "7cd1aeb1a6ec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create SpellSchool enum
    spell_school_enum = postgresql.ENUM(
        "Abjuration",
        "Conjuration",
        "Divination",
        "Enchantment",
        "Evocation",
        "Illusion",
        "Necromancy",
        "Transmutation",
        name="spellschool",
        create_type=False,
    )
    spell_school_enum.create(op.get_bind(), checkfirst=True)

    # Create CastingTime enum
    casting_time_enum = postgresql.ENUM(
        "1 action",
        "1 bonus action",
        "1 reaction",
        "1 minute",
        "10 minutes",
        "1 hour",
        "1 minute (ritual)",
        name="castingtime",
        create_type=False,
    )
    casting_time_enum.create(op.get_bind(), checkfirst=True)

    # Add spell_slots column to characters table
    op.add_column(
        "characters",
        sa.Column("spell_slots", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Create spells table
    op.create_table(
        "spells",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("school", spell_school_enum, nullable=False),
        sa.Column("casting_time", casting_time_enum, nullable=False),
        sa.Column("range", sa.String(length=50), nullable=False),
        sa.Column("duration", sa.String(length=50), nullable=False),
        sa.Column("verbal", sa.Boolean(), nullable=False),
        sa.Column("somatic", sa.Boolean(), nullable=False),
        sa.Column("material", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_concentration", sa.Boolean(), nullable=False),
        sa.Column("is_ritual", sa.Boolean(), nullable=False),
        sa.Column("damage_dice", sa.String(length=20), nullable=True),
        sa.Column("damage_type", sa.String(length=20), nullable=True),
        sa.Column("save_ability", sa.String(length=20), nullable=True),
        sa.Column("available_to_classes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_spells_name", "spells", ["name"], unique=True)
    op.create_index("ix_spells_level", "spells", ["level"], unique=False)
    op.create_index("ix_spells_level_school", "spells", ["level", "school"], unique=False)

    # Create character_spells junction table
    op.create_table(
        "character_spells",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("spell_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_known", sa.Boolean(), nullable=False),
        sa.Column("is_prepared", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spell_id"], ["spells.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_character_spells_character_id", "character_spells", ["character_id"], unique=False
    )
    op.create_index("ix_character_spells_spell_id", "character_spells", ["spell_id"], unique=False)
    op.create_index(
        "ix_character_spells_char_spell",
        "character_spells",
        ["character_id", "spell_id"],
        unique=True,
    )
    op.create_index(
        "ix_character_spells_prepared",
        "character_spells",
        ["character_id", "is_prepared"],
        unique=False,
    )


def downgrade() -> None:
    # Drop indexes and tables
    op.drop_index("ix_character_spells_prepared", table_name="character_spells")
    op.drop_index("ix_character_spells_char_spell", table_name="character_spells")
    op.drop_index("ix_character_spells_spell_id", table_name="character_spells")
    op.drop_index("ix_character_spells_character_id", table_name="character_spells")
    op.drop_table("character_spells")

    op.drop_index("ix_spells_level_school", table_name="spells")
    op.drop_index("ix_spells_level", table_name="spells")
    op.drop_index("ix_spells_name", table_name="spells")
    op.drop_table("spells")

    op.drop_column("characters", "spell_slots")

    # Drop enums
    sa.Enum(name="castingtime").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="spellschool").drop(op.get_bind(), checkfirst=True)
