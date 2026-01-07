"""Abstract storage interface and factory."""

from abc import ABC, abstractmethod
from typing import Any

from app.models.chat import PlanStep


class ChatSession:
    """Chat session model for storage interface (simplified)."""

    def __init__(
        self,
        id: str,
        title: str,
        created_at,
        updated_at,
        archived: bool = False,
        extra_data: dict | None = None,
    ):
        self.id = id
        self.title = title
        self.created_at = created_at
        self.updated_at = updated_at
        self.archived = archived
        self.extra_data = extra_data or {}


class Message:
    """Message model for storage interface (simplified)."""

    def __init__(
        self,
        id: str,
        session_id: str,
        role: str,
        content: str,
        created_at,
        agent_type: str | None = None,
        extra_data: dict | None = None,
    ):
        self.id = id
        self.session_id = session_id
        self.role = role
        self.content = content
        self.created_at = created_at
        self.agent_type = agent_type
        self.extra_data = extra_data or {}


class StorageInterface(ABC):
    """Abstract base class for storage implementations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage backend."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the storage connection."""
        pass

    # Session operations

    @abstractmethod
    async def create_session(self, title: str = "New Chat") -> ChatSession:
        """Create a new chat session."""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> ChatSession | None:
        """Get a chat session by ID."""
        pass

    @abstractmethod
    async def update_session(
        self,
        session_id: str,
        title: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> ChatSession | None:
        """Update a chat session."""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session."""
        pass

    @abstractmethod
    async def list_sessions(
        self, limit: int = 50, offset: int = 0, archived: bool = False
    ) -> list[ChatSession]:
        """List chat sessions ordered by updated_at desc."""
        pass

    @abstractmethod
    async def archive_session(self, session_id: str) -> ChatSession | None:
        """Archive a chat session."""
        pass

    @abstractmethod
    async def unarchive_session(self, session_id: str) -> ChatSession | None:
        """Unarchive a chat session."""
        pass

    # Message operations

    @abstractmethod
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_type: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> Message | None:
        """Add a message to a chat session."""
        pass

    @abstractmethod
    async def get_messages(self, session_id: str) -> list[Message]:
        """Get all messages for a session."""
        pass

    # Plan/Step operations

    @abstractmethod
    async def save_plan(self, session_id: str, plan: list[dict[str, Any]]) -> None:
        """Save the execution plan for a session."""
        pass

    @abstractmethod
    async def get_plan(self, session_id: str) -> list[dict[str, Any]] | None:
        """Get the execution plan for a session."""
        pass

    @abstractmethod
    async def update_step_status(
        self,
        session_id: str,
        step_id: str,
        status: str,
        result: str | None = None,
    ) -> None:
        """Update a step status in the plan."""
        pass


def get_storage(db_type: str, connection_string: str) -> StorageInterface:
    """Factory function to get storage implementation based on config."""
    if db_type == "sqlite":
        from app.storage.sqlite import SQLiteStorage

        return SQLiteStorage(connection_string)
    elif db_type == "postgresql":
        from app.storage.postgresql import PostgreSQLStorage

        return PostgreSQLStorage(connection_string)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
