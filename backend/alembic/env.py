"""Alembic environment configuration"""

# Import app config and models
import logging
import sys
from logging.config import fileConfig
from pathlib import Path

# Add backend root to path BEFORE importing app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.config import settings
from app.db import models  # noqa: F401 - Import all models
from app.db.base import Base

logger = logging.getLogger("alembic.env")

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set metadata for autogenerate support
target_metadata = Base.metadata

# Override database URL from app settings
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a connection"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def post_migration_seed(connectable):
    """Run seeding after migrations if tables are empty"""
    logger.info("Checking if database needs seeding...")

    async with connectable.connect() as connection:
        # Check if spells table is empty
        result = await connection.execute(text("SELECT COUNT(*) FROM spells"))
        spell_count = result.scalar()

        if spell_count == 0:
            logger.info("Spells table is empty, running seed_database.py...")
            # Import and run seeder
            from scripts.seed_database import seed_all

            try:
                await seed_all(force=False)
                logger.info("✅ Database seeding completed")
            except Exception as e:
                logger.error(f"❌ Seeding failed: {e}")
        else:
            logger.info(f"Database already seeded ({spell_count} spells)")


async def run_async_migrations() -> None:
    """Run migrations in async mode"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=settings.database_connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    # Run post-migration seeding
    try:
        await post_migration_seed(connectable)
    except Exception as e:
        logger.warning(f"Post-migration seeding skipped: {e}")

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    import asyncio

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
