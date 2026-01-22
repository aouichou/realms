"""Initial consolidated schema

Revision ID: 001
Revises:
Create Date: 2026-01-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (required for vector memory system)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create all ENUM types with idempotent DO blocks
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE charactertype AS ENUM ('player', 'companion', 'npc'); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE characterclass AS ENUM ("
        "'Barbarian', 'Bard', 'Cleric', 'Druid', 'Fighter', 'Monk', "
        "'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock', 'Wizard'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE characterrace AS ENUM ("
        "'Dragonborn', 'Dwarf', 'Elf', 'Gnome', 'Half-Elf', 'Half-Orc', "
        "'Halfling', 'Human', 'Tiefling'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE itemtype AS ENUM ('weapon', 'armor', 'consumable', 'quest', 'misc'); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE spellschool AS ENUM ("
        "'Abjuration', 'Conjuration', 'Divination', 'Enchantment', "
        "'Evocation', 'Illusion', 'Necromancy', 'Transmutation'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE castingtime AS ENUM ("
        "'1 action', '1 bonus action', '1 reaction', '1 minute', "
        "'10 minutes', '1 hour', '1 minute (ritual)'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE conditiontype AS ENUM ("
        "'Blinded', 'Charmed', 'Deafened', 'Frightened', 'Grappled', "
        "'Incapacitated', 'Invisible', 'Paralyzed', 'Petrified', 'Poisoned', "
        "'Prone', 'Restrained', 'Stunned', 'Unconscious'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE queststate AS ENUM ('not_started', 'in_progress', 'completed', 'failed'); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE eventtype AS ENUM ("
        "'combat', 'dialogue', 'discovery', 'decision', 'quest', "
        "'npc_interaction', 'loot', 'location', 'other'"
        "); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE messagerole AS ENUM ('user', 'assistant', 'system'); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_guest", sa.Boolean(), nullable=False),
        sa.Column("guest_token", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("preferred_language", sa.String(length=5), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("guest_token"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_guest_token", "users", ["guest_token"])

    # Create characters table
    op.create_table(
        "characters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "character_type",
            postgresql.ENUM(name="charactertype", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "character_class",
            postgresql.ENUM(name="characterclass", create_type=False),
            nullable=False,
        ),
        sa.Column("race", postgresql.ENUM(name="characterrace", create_type=False), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("hp_current", sa.Integer(), nullable=False),
        sa.Column("hp_max", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False),
        sa.Column("dexterity", sa.Integer(), nullable=False),
        sa.Column("constitution", sa.Integer(), nullable=False),
        sa.Column("intelligence", sa.Integer(), nullable=False),
        sa.Column("wisdom", sa.Integer(), nullable=False),
        sa.Column("charisma", sa.Integer(), nullable=False),
        sa.Column("carrying_capacity", sa.Integer(), nullable=False),
        sa.Column("spell_slots", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("active_concentration_spell", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("skill_proficiencies", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("background_name", sa.String(length=100), nullable=True),
        sa.Column("background_description", sa.String(length=1000), nullable=True),
        sa.Column(
            "background_skill_proficiencies", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("known_spells", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("prepared_spells", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("cantrips", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("asi_distribution", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("experience_points", sa.Integer(), nullable=False),
        sa.Column("gold", sa.Integer(), nullable=False, comment="Gold pieces"),
        sa.Column("silver", sa.Integer(), nullable=False, comment="Silver pieces"),
        sa.Column("copper", sa.Integer(), nullable=False, comment="Copper pieces"),
        sa.Column("background", sa.Text(), nullable=True),
        sa.Column("personality", sa.Text(), nullable=True),
        sa.Column("personality_trait", sa.Text(), nullable=True),
        sa.Column("ideal", sa.Text(), nullable=True),
        sa.Column("bond", sa.Text(), nullable=True),
        sa.Column("flaw", sa.Text(), nullable=True),
        sa.Column("motivation", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_characters_user_id", "characters", ["user_id"])
    op.create_index("ix_characters_character_type", "characters", ["character_type"])
    op.create_index("ix_characters_user_type", "characters", ["user_id", "character_type"])

    # Create spells table
    op.create_table(
        "spells",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("school", postgresql.ENUM(name="spellschool", create_type=False), nullable=False),
        sa.Column(
            "casting_time", postgresql.ENUM(name="castingtime", create_type=False), nullable=False
        ),
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
        sa.Column("upcast_damage_dice", sa.String(length=20), nullable=True),
        sa.Column("material_cost", sa.Integer(), nullable=True),
        sa.Column("material_consumed", sa.Boolean(), nullable=False),
        sa.Column("save_ability", sa.String(length=20), nullable=True),
        sa.Column("available_to_classes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_spells_name", "spells", ["name"])
    op.create_index("ix_spells_level", "spells", ["level"])
    op.create_index("ix_spells_level_school", "spells", ["level", "school"])

    # Create game_sessions table
    op.create_table(
        "game_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("companion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("current_location", sa.String(length=255), nullable=True),
        sa.Column("state_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["companion_id"], ["characters.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_game_sessions_user_id", "game_sessions", ["user_id"])
    op.create_index("ix_game_sessions_character_id", "game_sessions", ["character_id"])
    op.create_index("ix_game_sessions_companion_id", "game_sessions", ["companion_id"])
    op.create_index("ix_game_sessions_is_active", "game_sessions", ["is_active"])
    op.create_index("ix_game_sessions_last_activity_at", "game_sessions", ["last_activity_at"])
    op.create_index("ix_game_sessions_user_active", "game_sessions", ["user_id", "is_active"])

    # Create conversation_messages table
    op.create_table(
        "conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", postgresql.ENUM(name="messagerole", create_type=False), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("scene_image_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["game_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_conversation_messages_session_id", "conversation_messages", ["session_id"])
    op.create_index("ix_conversation_messages_created_at", "conversation_messages", ["created_at"])
    op.create_index(
        "ix_messages_session_created", "conversation_messages", ["session_id", "created_at"]
    )

    # Create adventures table
    op.create_table(
        "adventures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("setting", sa.String(length=100), nullable=False),
        sa.Column("goal", sa.String(length=100), nullable=False),
        sa.Column("tone", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scenes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_adventures_character_id", "adventures", ["character_id"])

    # Create adventure_memories table
    op.create_table(
        "adventure_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "event_type", postgresql.ENUM(name="eventtype", create_type=False), nullable=False
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=True),  # Will be converted to vector(1024)
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("npcs_involved", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("locations", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("items_involved", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["game_sessions.id"], ondelete="CASCADE"),
    )

    # Convert embedding column to vector type after table creation
    op.execute(
        "ALTER TABLE adventure_memories ALTER COLUMN embedding TYPE vector(1024) USING embedding::vector"
    )

    op.create_index("ix_adventure_memories_session_id", "adventure_memories", ["session_id"])
    op.create_index("ix_adventure_memories_event_type", "adventure_memories", ["event_type"])
    op.create_index("ix_adventure_memories_importance", "adventure_memories", ["importance"])
    op.create_index("ix_adventure_memories_timestamp", "adventure_memories", ["timestamp"])

    # Create encounters table
    op.create_table(
        "encounters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("participants", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )

    # Create combat_encounters table
    op.create_table(
        "combat_encounters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("current_turn", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("participants", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("turn_order", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("combat_log", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["game_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_combat_encounters_session_id", "combat_encounters", ["session_id"])
    op.create_index("ix_combat_encounters_is_active", "combat_encounters", ["is_active"])

    # Create quests table
    op.create_table(
        "quests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("state", postgresql.ENUM(name="queststate", create_type=False), nullable=False),
        sa.Column("quest_giver_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rewards", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["quest_giver_id"], ["characters.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_quests_state", "quests", ["state"])

    # Create quest_objectives table
    op.create_table(
        "quest_objectives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("quest_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["quest_id"], ["quests.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_quest_objectives_quest_id", "quest_objectives", ["quest_id"])

    # Create character_spells table
    op.create_table(
        "character_spells",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("spell_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_known", sa.Boolean(), nullable=False),
        sa.Column("is_prepared", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spell_id"], ["spells.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_character_spells_character_id", "character_spells", ["character_id"])
    op.create_index("ix_character_spells_spell_id", "character_spells", ["spell_id"])
    op.create_index(
        "ix_character_spells_char_spell",
        "character_spells",
        ["character_id", "spell_id"],
        unique=True,
    )
    op.create_index(
        "ix_character_spells_prepared", "character_spells", ["character_id", "is_prepared"]
    )

    # Create character_conditions table
    op.create_table(
        "character_conditions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "condition", postgresql.ENUM(name="conditiontype", create_type=False), nullable=False
        ),
        sa.Column("duration", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_character_conditions_character_id", "character_conditions", ["character_id"]
    )

    # Create character_quests table
    op.create_table(
        "character_quests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quest_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quest_id"], ["quests.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_character_quests_character_id", "character_quests", ["character_id"])
    op.create_index("ix_character_quests_quest_id", "character_quests", ["quest_id"])
    op.create_index(
        "ix_character_quest_unique", "character_quests", ["character_id", "quest_id"], unique=True
    )

    # Create items table
    op.create_table(
        "items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("item_type", postgresql.ENUM(name="itemtype", create_type=False), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("properties", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("equipped", sa.Boolean(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_items_character_id", "items", ["character_id"])
    op.create_index("ix_items_item_type", "items", ["item_type"])
    op.create_index("ix_items_character_type", "items", ["character_id", "item_type"])
    op.create_index("ix_items_character_equipped", "items", ["character_id", "equipped"])


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table("items")
    op.drop_table("character_quests")
    op.drop_table("character_conditions")
    op.drop_table("character_spells")
    op.drop_table("quest_objectives")
    op.drop_table("quests")
    op.drop_table("combat_encounters")
    op.drop_table("encounters")
    op.drop_table("adventure_memories")
    op.drop_table("adventures")
    op.drop_table("conversation_messages")
    op.drop_table("game_sessions")
    op.drop_table("spells")
    op.drop_table("characters")
    op.drop_table("users")

    # Drop all ENUM types
    op.execute("DROP TYPE IF EXISTS messagerole CASCADE")
    op.execute("DROP TYPE IF EXISTS eventtype CASCADE")
    op.execute("DROP TYPE IF EXISTS queststate CASCADE")
    op.execute("DROP TYPE IF EXISTS conditiontype CASCADE")
    op.execute("DROP TYPE IF EXISTS castingtime CASCADE")
    op.execute("DROP TYPE IF EXISTS spellschool CASCADE")
    op.execute("DROP TYPE IF EXISTS itemtype CASCADE")
    op.execute("DROP TYPE IF EXISTS characterrace CASCADE")
    op.execute("DROP TYPE IF EXISTS characterclass CASCADE")
    op.execute("DROP TYPE IF EXISTS charactertype CASCADE")
