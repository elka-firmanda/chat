"""
PostgreSQL connection and validation utilities.
"""

import re
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text


def validate_postgresql_connection_string(conn_str: str) -> Tuple[bool, Optional[str]]:
    """
    Validate PostgreSQL connection string format.

    Args:
        conn_str: PostgreSQL connection string (e.g., postgresql://user:pass@localhost:5432/db)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not conn_str:
        return False, "Connection string is required"

    # Check for valid PostgreSQL async URL format
    pattern = r"^postgresql(\+asyncpg)?://[^:]+:[^@]+@[^:]+:\d+/[^$]+$"
    if not re.match(pattern, conn_str):
        return (
            False,
            "Invalid PostgreSQL connection string format. Expected: postgresql://user:password@host:port/database",
        )

    return True, None


async def test_postgresql_connection(
    conn_str: str, timeout: int = 10
) -> Tuple[bool, Optional[str]]:
    """
    Test PostgreSQL connection by attempting to connect and run a simple query.

    Args:
        conn_str: PostgreSQL connection string
        timeout: Connection timeout in seconds

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        engine = create_async_engine(
            conn_str,
            echo=False,
            pool_size=1,
            max_overflow=0,
            pool_timeout=timeout,
        )

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        await engine.dispose()
        return True, None

    except Exception as e:
        error_msg = str(e)

        # Provide more helpful error messages for common issues
        if "connection refused" in error_msg.lower():
            return False, "Connection refused - is the PostgreSQL server running?"
        elif "password authentication failed" in error_msg.lower():
            return False, "Authentication failed - check username and password"
        elif (
            "could not translate host" in error_msg.lower()
            or "name or service not known" in error_msg.lower()
        ):
            return False, "Cannot resolve hostname - check the host name"
        elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
            return False, "Database does not exist"
        else:
            return False, f"Connection failed: {error_msg}"


async def get_postgresql_version(conn_str: str) -> Optional[str]:
    """
    Get PostgreSQL server version.

    Args:
        conn_str: PostgreSQL connection string

    Returns:
        Version string or None if connection fails
    """
    try:
        engine = create_async_engine(conn_str, echo=False)

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            row = result.fetchone()
            if row:
                version = row[0]
                # Extract just the version number
                match = re.search(r"PostgreSQL (\d+\.\d+)", version)
                if match:
                    return match.group(1)
                return version.split("\n")[0]

        await engine.dispose()
        return None

    except Exception:
        return None


def get_async_postgresql_url(sqlite_path: str) -> str:
    """
    Convert a SQLite path to a PostgreSQL async URL format.
    This is a helper for generating suggested connection strings.

    Args:
        sqlite_path: Original SQLite database path

    Returns:
        Suggested PostgreSQL connection string
    """
    db_name = "chatbot"

    return f"postgresql+asyncpg://postgres:password@localhost:5432/{db_name}"
