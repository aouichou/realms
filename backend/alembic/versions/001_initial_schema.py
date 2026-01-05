"""Initial database schema with User, Character, GameSession, ConversationMessage

Revision ID: 001
Revises:
Create Date: 2025-12-31 00:00:00

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM types (these need to be created BEFORE tables reference them)
    # Use CREATE TYPE IF NOT EXISTS for idempotency
    op.execute(
        "DO $$ BEGIN CREATE TYPE charactertype AS ENUM ('player', 'companion', 'npc'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE characterclass AS ENUM ('Fighter', 'Wizard', 'Rogue', 'Cleric'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE characterrace AS ENUM ('Human', 'Elf', 'Dwarf', 'Halfling'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE messagerole AS ENUM ('user', 'assistant', 'system'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])

    # Create characters table
    op.create_table(
        "characters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "character_type",
            postgresql.ENUM("player", "companion", "npc", name="charactertype", create_type=False),
            nullable=False,
            server_default="player",
        ),
        sa.Column(
            "character_class",
            postgresql.ENUM(
                "Fighter", "Wizard", "Rogue", "Cleric", name="characterclass", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "race",
            postgresql.ENUM(
                "Human", "Elf", "Dwarf", "Halfling", name="characterrace", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("hp_current", sa.Integer(), nullable=False),
        sa.Column("hp_max", sa.Integer(), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("dexterity", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("constitution", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("intelligence", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("wisdom", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("charisma", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("background", sa.Text(), nullable=True),
        sa.Column("personality", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_characters_user_id", "characters", ["user_id"])
    op.create_index("ix_characters_character_type", "characters", ["character_type"])
    op.create_index("ix_characters_user_type", "characters", ["user_id", "character_type"])

    # Create game_sessions table
    op.create_table(
        "game_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "character_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "companion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("characters.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("current_location", sa.String(255), nullable=True),
        sa.Column("state_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "last_activity_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
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
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("game_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            postgresql.ENUM("user", "assistant", "system", name="messagerole", create_type=False),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_conversation_messages_session_id", "conversation_messages", ["session_id"])
    op.create_index("ix_conversation_messages_created_at", "conversation_messages", ["created_at"])
    op.create_index(
        "ix_messages_session_created", "conversation_messages", ["session_id", "created_at"]
    )


def downgrade() -> None:
    # Drop tables in reverse order (respect foreign keys)
    op.drop_table("conversation_messages")
    op.drop_table("game_sessions")
    op.drop_table("characters")
    op.drop_table("users")

    # Drop ENUM types (split into separate executes for asyncpg)
    op.execute("DROP TYPE IF EXISTS messagerole")
    op.execute("DROP TYPE IF EXISTS characterrace")
    op.execute("DROP TYPE IF EXISTS characterclass")
    op.execute("DROP TYPE IF EXISTS charactertype")
