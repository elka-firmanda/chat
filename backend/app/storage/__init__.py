"""Storage module for simplified database access."""

from app.storage.base import StorageInterface, get_storage
from app.storage.sqlite import SQLiteStorage
from app.storage.postgresql import PostgreSQLStorage

__all__ = ["StorageInterface", "get_storage", "SQLiteStorage", "PostgreSQLStorage"]
