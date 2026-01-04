"""
Database session management with async SQLAlchemy.
Supports both SQLite and PostgreSQL with dynamic switching.
"""

import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Tuple
from threading import Lock

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from .models import Base
from .postgresql import (
    test_postgresql_connection,
    validate_postgresql_connection_string,
)


_engine_lock = Lock()
_engine = None
_engine_url = None


def get_database_url(from_config: Optional[dict] = None) -> str:
    """
    Get the database URL from configuration or use default.

    Args:
        from_config: Optional config dict to read from (for testing)

    Returns:
        Database connection URL
    """
    if from_config is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json"
        )

        if os.path.exists(config_path):
            try:
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

    db_path = "./data/chatbot.db"
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path}"


def get_pool_size(from_config: Optional[dict] = None) -> int:
    """
    Get database pool size from config or use default.

    Args:
        from_config: Optional config dict to read from (for testing)

    Returns:
        Pool size integer
    """
    if from_config is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json"
        )

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)

                db_config = config.get("database", {})
                return db_config.get("pool_size", 5)
            except Exception:
                pass

    return 5


def _get_engine():
    """Get or create the global database engine."""
    global _engine, _engine_url
    return _engine, _engine_url


def _set_engine(engine, url: str):
    """Set the global database engine."""
    global _engine, _engine_url
    _engine = engine
    _engine_url = url


def create_database_engine(url: str, pool_size: int = 5):
    """
    Create a database engine from a URL.

    Args:
        url: Database connection URL
        pool_size: Pool size for connection pooling

    Returns:
        SQLAlchemy async engine
    """
    is_postgresql = url.startswith("postgresql") or url.startswith("postgres")

    if is_postgresql:
        return create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=10,
            pool_recycle=3600,
        )
    else:
        return create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=10,
        )


def initialize_engine(
    url: Optional[str] = None, pool_size: Optional[int] = None
) -> None:
    """
    Initialize or reinitialize the global database engine.
    This is called on startup and when database settings change.

    Args:
        url: Optional database URL, will use config if not provided
        pool_size: Optional pool size, will use config if not provided
    """
    global _engine, _engine_url

    with _engine_lock:
        if _engine is not None:
            try:
                asyncio.get_event_loop().run_until_complete(_engine.dispose())
            except Exception:
                pass

        db_url = url or get_database_url()
        db_pool_size = pool_size if pool_size is not None else get_pool_size()

        _engine = create_database_engine(db_url, db_pool_size)
        _engine_url = db_url


def get_engine():
    """Get the current database engine, initializing if necessary."""
    global _engine, _engine_url

    if _engine is None:
        initialize_engine()

    return _engine


def get_engine_url() -> str:
    """Get the current database URL."""
    global _engine_url
    if _engine_url is None:
        _engine_url = get_database_url()
    return _engine_url


def get_session_factory():
    """Get the async session factory for the current engine."""
    engine = get_engine()
    return async_sessionmaker(
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
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """
    Drop all database tables (use with caution).
    """
    engine = get_engine()
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
    session_factory = get_session_factory()
    session = session_factory()
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


async def validate_database_connection(
    db_type: str, connection_string: str, pool_size: int = 5
) -> Tuple[bool, str]:
    """
    Validate a database connection configuration.

    Args:
        db_type: 'sqlite' or 'postgresql'
        connection_string: Connection string (full URL for PostgreSQL, path for SQLite)
        pool_size: Pool size for PostgreSQL

    Returns:
        Tuple of (is_valid, message)
    """
    if db_type == "sqlite":
        if not connection_string:
            return False, "SQLite path is required"

        db_path = connection_string
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception as e:
                return False, f"Cannot create SQLite directory: {e}"

        try:
            test_url = f"sqlite+aiosqlite:///{db_path}"
            engine = create_async_engine(test_url, echo=False)
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            return True, "SQLite connection successful"
        except Exception as e:
            return False, f"SQLite connection failed: {e}"

    elif db_type == "postgresql":
        if not connection_string:
            return False, "PostgreSQL connection string is required"

        format_valid, format_error = validate_postgresql_connection_string(
            connection_string
        )
        if not format_valid:
            return False, format_error or "Invalid connection string format"

        is_valid, error = await test_postgresql_connection(connection_string)
        if is_valid:
            return True, "PostgreSQL connection successful"
        else:
            return False, error if error else "PostgreSQL connection failed"

    return False, f"Unknown database type: {db_type}"


def get_database_info() -> dict:
    """
    Get information about the current database configuration.

    Returns:
        Dictionary with database info
    """
    current_url = get_engine_url()
    is_postgresql = current_url.startswith("postgresql") or current_url.startswith(
        "postgres"
    )

    return {
        "type": "postgresql" if is_postgresql else "sqlite",
        "url": current_url,
        "pool_size": get_pool_size(),
    }


def update_config_file(
    db_type: str, sqlite_path: str, postgresql_connection: str, pool_size: int
) -> None:
    """
    Update the config.json file with new database settings.

    Args:
        db_type: 'sqlite' or 'postgresql'
        sqlite_path: Path to SQLite database
        postgresql_connection: PostgreSQL connection string
        pool_size: Pool size
    """
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json"
    )

    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)

    if "database" not in config:
        config["database"] = {}

    config["database"]["type"] = db_type
    config["database"]["sqlite_path"] = sqlite_path
    config["database"]["postgresql_connection"] = postgresql_connection
    config["database"]["pool_size"] = pool_size

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


async def switch_database(
    db_type: str, connection_string: str, pool_size: int = 5
) -> Tuple[bool, str]:
    """
    Switch to a different database configuration.

    Args:
        db_type: 'sqlite' or 'postgresql'
        connection_string: Connection string or path
        pool_size: Pool size for PostgreSQL

    Returns:
        Tuple of (success, message)
    """
    is_valid, message = await validate_database_connection(
        db_type, connection_string, pool_size
    )

    if not is_valid:
        return False, message

    if db_type == "sqlite":
        db_url = f"sqlite+aiosqlite:///{connection_string}"
    else:
        db_url = connection_string

    try:
        initialize_engine(db_url, pool_size)

        await init_db()

        return True, f"Successfully switched to {db_type}"

    except Exception as e:
        return False, f"Failed to switch database: {e}"
