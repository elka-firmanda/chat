"""
Database session management with async SQLAlchemy.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event

from .models import Base


# Determine database URL
def get_database_url() -> str:
    """Get the database URL from configuration or use default."""
    # Try to load from config.json
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json"
    )

    if os.path.exists(config_path):
        try:
            import json

            with open(config_path, "r") as f:
                config = json.load(f)

            db_config = config.get("database", {})
            db_type = db_config.get("type", "sqlite")

            if db_type == "postgresql" and db_config.get("postgresql_connection"):
                return db_config["postgresql_connection"]
            elif db_type == "sqlite":
                db_path = db_config.get("sqlite_path", "./data/chatbot.db")
                db_dir = os.path.dirname(db_path)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
                return f"sqlite+aiosqlite:///{db_path}"
        except Exception:
            pass

    # Default to SQLite
    db_path = "./data/chatbot.db"
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path}"


def get_pool_size() -> int:
    """Get database pool size from config or use default."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json"
    )

    if os.path.exists(config_path):
        try:
            import json

            with open(config_path, "r") as f:
                config = json.load(f)

            db_config = config.get("database", {})
            return db_config.get("pool_size", 5)
        except Exception:
            pass

    return 5


# Create async engine
DATABASE_URL = get_database_url()

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=get_pool_size(),
    max_overflow=10,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """
    Initialize database tables.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """
    Drop all database tables (use with caution).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session as an async context manager.

    Usage:
        async with get_db_session() as session:
            # do database operations
            pass
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting a database session.

    Usage:
        @router.get("/")
        async def endpoint(session: AsyncSession = Depends(get_db)):
            # do database operations
            pass
    """
    async with get_db_session() as session:
        yield session
