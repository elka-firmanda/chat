from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url():
    """Get database URL from config or environment."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json"
    )

    if os.path.exists(config_path):
        try:
            import json

            with open(config_path, "r") as f:
                db_config = json.load(f).get("database", {})
                db_type = db_config.get("type", "sqlite")

                if db_type == "postgresql" and db_config.get("postgresql_connection"):
                    return db_config["postgresql_connection"]
                elif db_type == "sqlite":
                    db_path = db_config.get("sqlite_path", "./data/chatbot.db")
                    return f"sqlite+aiosqlite:///{db_path}"
        except Exception:
            pass

    return "sqlite+aiosqlite:///./data/chatbot.db"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations asynchronously."""
    url = get_database_url()

    connectable = async_engine_from_config(
        {"sqlalchemy.url": url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_async_migrations())
