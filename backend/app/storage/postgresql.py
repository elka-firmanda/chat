"""PostgreSQL storage implementation."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Base, ChatSession, Message, WorkingMemory, AgentStep
from app.storage.base import StorageInterface


def _serialize_for_json(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO format strings for JSON storage."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(item) for item in obj]
    return obj


class PostgreSQLStorage(StorageInterface):
    """PostgreSQL implementation of the storage interface."""

    def __init__(self, connection_string: str, pool_size: int = 5):
        """Initialize PostgreSQL storage."""
        self.connection_string = connection_string
        self.engine = create_async_engine(
            connection_string,
            echo=False,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=10,
            pool_recycle=3600,
        )
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def initialize(self) -> None:
        """Initialize the database schema."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        """Close the database connection."""
        await self.engine.dispose()

    async def create_session(self, title: str = "New Chat") -> ChatSession:
        """Create a new chat session."""
        async with self.async_session() as session:
            chat_session = ChatSession(
                id=str(uuid.uuid4()),
                title=title,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                extra_data={},
            )
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)
            return chat_session

    async def get_session(self, session_id: str) -> ChatSession | None:
        """Get a chat session by ID."""
        async with self.async_session() as session:
            result = await session.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            return result.scalar_one_or_none()

    async def update_session(
        self,
        session_id: str,
        title: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> ChatSession | None:
        """Update a chat session."""
        async with self.async_session() as session:
            result = await session.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            chat_session = result.scalar_one_or_none()

            if not chat_session:
                return None

            if title is not None:
                chat_session.title = title
            if extra_data is not None:
                chat_session.extra_data = extra_data

            chat_session.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(chat_session)
            return chat_session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a chat session."""
        async with self.async_session() as session:
            result = await session.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            chat_session = result.scalar_one_or_none()

            if not chat_session:
                return False

            await session.delete(chat_session)
            await session.commit()
            return True

    async def list_sessions(
        self, limit: int = 50, offset: int = 0, archived: bool = False
    ) -> list[ChatSession]:
        """List chat sessions ordered by updated_at desc."""
        async with self.async_session() as session:
            result = await session.execute(
                select(ChatSession)
                .where(ChatSession.archived == archived)
                .order_by(ChatSession.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())

    async def archive_session(self, session_id: str) -> ChatSession | None:
        """Archive a chat session."""
        async with self.async_session() as session:
            result = await session.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            chat_session = result.scalar_one_or_none()
            if not chat_session:
                return None
            chat_session.archived = True
            chat_session.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(chat_session)
            return chat_session

    async def unarchive_session(self, session_id: str) -> ChatSession | None:
        """Unarchive a chat session."""
        async with self.async_session() as session:
            result = await session.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            chat_session = result.scalar_one_or_none()
            if not chat_session:
                return None
            chat_session.archived = False
            chat_session.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(chat_session)
            return chat_session

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_type: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> Message | None:
        """Add a message to a chat session."""
        async with self.async_session() as session:
            result = await session.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            chat_session = result.scalar_one_or_none()

            if not chat_session:
                return None

            message = Message(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role=role,
                content=content,
                agent_type=agent_type,
                created_at=datetime.now(timezone.utc),
                extra_data=extra_data or {},
            )
            session.add(message)
            await session.commit()
            await session.refresh(message)
            return message

    async def get_messages(self, session_id: str) -> list[Message]:
        """Get all messages for a session."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Message)
                .where(Message.session_id == session_id)
                .order_by(Message.created_at.asc())
            )
            return list(result.scalars().all())

    async def save_plan(self, session_id: str, plan: list[dict[str, Any]]) -> None:
        """Save the execution plan for a session."""
        async with self.async_session() as session:
            result = await session.execute(
                select(WorkingMemory).where(WorkingMemory.session_id == session_id)
            )
            working_memory = result.scalar_one_or_none()

            if not working_memory:
                working_memory = WorkingMemory(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    memory_tree={"steps": plan},
                    timeline=[],
                    index_map={},
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(working_memory)
            else:
                working_memory.memory_tree = {"steps": plan}
                working_memory.updated_at = datetime.now(timezone.utc)

            await session.commit()

    async def get_plan(self, session_id: str) -> list[dict[str, Any]] | None:
        """Get the execution plan for a session."""
        async with self.async_session() as session:
            result = await session.execute(
                select(WorkingMemory).where(WorkingMemory.session_id == session_id)
            )
            working_memory = result.scalar_one_or_none()

            if working_memory and working_memory.memory_tree:
                return working_memory.memory_tree.get("steps")
            return None

    async def update_step_status(
        self,
        session_id: str,
        step_id: str,
        status: str,
        result: str | None = None,
    ) -> None:
        """Update a step status in the plan."""
        async with self.async_session() as session:
            result_query = await session.execute(
                select(AgentStep).where(AgentStep.session_id == session_id)
            )
            step = result_query.scalar_one_or_none()

            if step:
                step.status = status
                if result:
                    step.result = result
                await session.commit()
