"""
Database migration utilities for SQLite to PostgreSQL migration.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import text, select, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from .models import (
    Base,
    ChatSession,
    Message,
    WorkingMemory,
    AgentStep,
    CustomTool,
    Configuration,
)


class DatabaseMigration:
    """
    Handles database migration between SQLite and PostgreSQL.
    """

    def __init__(self, source_url: str, target_url: str):
        """
        Initialize migration with source and target database URLs.

        Args:
            source_url: URL of the source database (SQLite)
            target_url: URL of the target database (PostgreSQL)
        """
        self.source_url = source_url
        self.target_url = target_url
        self.source_engine = None
        self.target_engine = None
        self.source_session_factory = None
        self.target_session_factory = None

    async def initialize(self) -> None:
        """Initialize database connections."""
        self.source_engine = create_async_engine(
            self.source_url,
            echo=False,
        )
        self.target_engine = create_async_engine(
            self.target_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
        )

        self.source_session_factory = async_sessionmaker(
            self.source_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self.target_session_factory = async_sessionmaker(
            self.target_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def cleanup(self) -> None:
        """Close database connections."""
        if self.source_engine:
            await self.source_engine.dispose()
        if self.target_engine:
            await self.target_engine.dispose()

    async def create_target_schema(self) -> None:
        """Create the schema on the target database."""
        async with self.target_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def check_source_data(self) -> Dict[str, int]:
        """
        Check the data in the source database.

        Returns:
            Dictionary with table names and row counts
        """
        counts = {}
        async with self.source_session_factory() as session:
            tables = [
                ChatSession,
                Message,
                WorkingMemory,
                AgentStep,
                CustomTool,
                Configuration,
            ]
            for table in tables:
                result = await session.execute(select(table))
                count = len(result.scalars().all())
                counts[table.__tablename__] = count
        return counts

    async def migrate_chat_sessions(self) -> int:
        """
        Migrate chat sessions from source to target.

        Returns:
            Number of sessions migrated
        """
        async with self.source_session_factory() as source_session:
            result = await source_session.execute(select(ChatSession))
            sessions = result.scalars().all()

        async with self.target_session_factory() as target_session:
            for session in sessions:
                new_session = ChatSession(
                    id=session.id,
                    title=session.title,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    archived=session.archived,
                    extra_data=session.extra_data,
                )
                target_session.add(new_session)
            await target_session.commit()

        return len(sessions)

    async def migrate_messages(self) -> int:
        """
        Migrate messages from source to target.

        Returns:
            Number of messages migrated
        """
        async with self.source_session_factory() as source_session:
            result = await source_session.execute(select(Message))
            messages = result.scalars().all()

        async with self.target_session_factory() as target_session:
            for message in messages:
                new_message = Message(
                    id=message.id,
                    session_id=message.session_id,
                    role=message.role,
                    content=message.content,
                    agent_type=message.agent_type,
                    parent_message_id=message.parent_message_id,
                    created_at=message.created_at,
                    extra_data=message.extra_data,
                )
                target_session.add(new_message)
            await target_session.commit()

        return len(messages)

    async def migrate_working_memory(self) -> int:
        """
        Migrate working memory from source to target.

        Returns:
            Number of working memory records migrated
        """
        async with self.source_session_factory() as source_session:
            result = await source_session.execute(select(WorkingMemory))
            memories = result.scalars().all()

        async with self.target_session_factory() as target_session:
            for memory in memories:
                new_memory = WorkingMemory(
                    id=memory.id,
                    session_id=memory.session_id,
                    memory_tree=memory.memory_tree,
                    timeline=memory.timeline,
                    index_map=memory.index_map,
                    updated_at=memory.updated_at,
                )
                target_session.add(new_memory)
            await target_session.commit()

        return len(memories)

    async def migrate_agent_steps(self) -> int:
        """
        Migrate agent steps from source to target.

        Returns:
            Number of agent steps migrated
        """
        async with self.source_session_factory() as source_session:
            result = await source_session.execute(select(AgentStep))
            steps = result.scalars().all()

        async with self.target_session_factory() as target_session:
            for step in steps:
                new_step = AgentStep(
                    id=step.id,
                    session_id=step.session_id,
                    message_id=step.message_id,
                    step_number=step.step_number,
                    agent_type=step.agent_type,
                    description=step.description,
                    status=step.status,
                    result=step.result,
                    logs=step.logs,
                    created_at=step.created_at,
                    completed_at=step.completed_at,
                )
                target_session.add(new_step)
            await target_session.commit()

        return len(steps)

    async def migrate_custom_tools(self) -> int:
        """
        Migrate custom tools from source to target.

        Returns:
            Number of custom tools migrated
        """
        async with self.source_session_factory() as source_session:
            result = await source_session.execute(select(CustomTool))
            tools = result.scalars().all()

        async with self.target_session_factory() as target_session:
            for tool in tools:
                new_tool = CustomTool(
                    id=tool.id,
                    name=tool.name,
                    description=tool.description,
                    code=tool.code,
                    enabled=tool.enabled,
                    created_at=tool.created_at,
                )
                target_session.add(new_tool)
            await target_session.commit()

        return len(tools)

    async def migrate_configurations(self) -> int:
        """
        Migrate configurations from source to target.

        Returns:
            Number of configurations migrated
        """
        async with self.source_session_factory() as source_session:
            result = await source_session.execute(select(Configuration))
            configs = result.scalars().all()

        async with self.target_session_factory() as target_session:
            for config in configs:
                new_config = Configuration(
                    id=config.id,
                    config_json=config.config_json,
                    version=config.version,
                    created_at=config.created_at,
                )
                target_session.add(new_config)
            await target_session.commit()

        return len(configs)

    async def run_full_migration(self) -> Dict[str, Any]:
        """
        Run a complete database migration.

        Returns:
            Migration results with counts and status
        """
        results = {
            "status": "started",
            "started_at": datetime.utcnow().isoformat(),
            "tables": {},
            "errors": [],
        }

        try:
            await self.initialize()

            # Check source data
            source_counts = await self.check_source_data()
            results["source_data"] = source_counts

            # Create target schema
            await self.create_target_schema()

            # Migrate each table
            results["tables"]["chat_sessions"] = await self.migrate_chat_sessions()
            results["tables"]["messages"] = await self.migrate_messages()
            results["tables"]["working_memory"] = await self.migrate_working_memory()
            results["tables"]["agent_steps"] = await self.migrate_agent_steps()
            results["tables"]["custom_tools"] = await self.migrate_custom_tools()
            results["tables"]["configurations"] = await self.migrate_configurations()

            results["status"] = "completed"
            results["completed_at"] = datetime.utcnow().isoformat()

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            results["completed_at"] = datetime.utcnow().isoformat()

        finally:
            await self.cleanup()

        return results

    async def verify_migration(self, target_url: str) -> Dict[str, Any]:
        """
        Verify that migration was successful by comparing counts.

        Args:
            target_url: URL of the target database to verify

        Returns:
            Verification results
        """
        verification = {
            "verified": False,
            "source_counts": {},
            "target_counts": {},
            "differences": {},
        }

        try:
            # Get source counts
            verification["source_counts"] = await self.check_source_data()

            # Get target counts
            target_engine = create_async_engine(target_url, echo=False)
            target_session_factory = async_sessionmaker(
                target_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            async with target_session_factory() as session:
                tables = [
                    ChatSession,
                    Message,
                    WorkingMemory,
                    AgentStep,
                    CustomTool,
                    Configuration,
                ]
                for table in tables:
                    result = await session.execute(select(table))
                    count = len(result.scalars().all())
                    verification["target_counts"][table.__tablename__] = count

            await target_engine.dispose()

            # Compare counts
            all_match = True
            for table in verification["source_counts"]:
                source_count = verification["source_counts"][table]
                target_count = verification["target_counts"].get(table, 0)
                diff = target_count - source_count
                verification["differences"][table] = {
                    "source": source_count,
                    "target": target_count,
                    "difference": diff,
                }
                if diff != 0:
                    all_match = False

            verification["verified"] = all_match

        except Exception as e:
            verification["error"] = str(e)

        return verification


async def migrate_sqlite_to_postgresql(
    sqlite_url: str,
    postgresql_url: str,
) -> Dict[str, Any]:
    """
    Convenience function to run a full SQLite to PostgreSQL migration.

    Args:
        sqlite_url: SQLite database URL
        postgresql_url: PostgreSQL database URL

    Returns:
        Migration results
    """
    migration = DatabaseMigration(sqlite_url, postgresql_url)
    return await migration.run_full_migration()
