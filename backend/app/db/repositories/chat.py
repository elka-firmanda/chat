"""
Chat repository for session and message operations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatSession, Message, WorkingMemory, AgentStep
import uuid


class ChatRepository:
    """Repository for chat-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Session operations
    async def create_session(
        self, title: Optional[str] = None, extra_data: Optional[Dict] = None
    ) -> ChatSession:
        """Create a new chat session."""
        session_obj = ChatSession(
            id=str(uuid.uuid4()), title=title, extra_data=extra_data
        )
        self.session.add(session_obj)
        await self.session.flush()
        return session_obj

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID."""
        result = await self.session.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_sessions(
        self, archived: bool = False, limit: int = 50, offset: int = 0
    ) -> List[ChatSession]:
        """Get list of sessions with pagination."""
        result = await self.session.execute(
            select(ChatSession)
            .where(ChatSession.archived == archived)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_session_title(
        self, session_id: str, title: str
    ) -> Optional[ChatSession]:
        """Update session title."""
        result = await self.session.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session_obj = result.scalar_one_or_none()
        if session_obj:
            session_obj.title = title
            await self.session.flush()
        return session_obj

    async def archive_session(self, session_id: str) -> Optional[ChatSession]:
        """Archive a session."""
        result = await self.session.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session_obj = result.scalar_one_or_none()
        if session_obj:
            session_obj.archived = True
            await self.session.flush()
        return session_obj

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session (soft delete by archiving)."""
        session_obj = await self.archive_session(session_id)
        return session_obj is not None

    # Message operations
    async def create_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_type: Optional[str] = None,
        parent_message_id: Optional[str] = None,
        extra_data: Optional[Dict] = None,
    ) -> Message:
        """Create a new message."""
        message = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            agent_type=agent_type,
            parent_message_id=parent_message_id,
            extra_data=extra_data,
        )
        self.session.add(message)

        # Update session's updated_at timestamp
        session_obj = await self.get_session(session_id)
        if session_obj:
            from datetime import datetime

            session_obj.updated_at = datetime.utcnow()

        await self.session.flush()
        return message

    async def get_messages(
        self, session_id: str, limit: int = 30, offset: int = 0
    ) -> List[Message]:
        """Get messages for a session with pagination."""
        result = await self.session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_message(self, message_id: str) -> Optional[Message]:
        """Get a message by ID."""
        result = await self.session.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    # Working memory operations
    async def get_working_memory(self, session_id: str) -> Optional[WorkingMemory]:
        """Get working memory for a session."""
        result = await self.session.execute(
            select(WorkingMemory).where(WorkingMemory.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def save_working_memory(
        self,
        session_id: str,
        memory_tree: Optional[Dict] = None,
        timeline: Optional[List] = None,
        index_map: Optional[Dict] = None,
    ) -> WorkingMemory:
        """Save or update working memory."""
        working_memory = await self.get_working_memory(session_id)

        if working_memory:
            working_memory.memory_tree = memory_tree
            working_memory.timeline = timeline
            working_memory.index_map = index_map
        else:
            working_memory = WorkingMemory(
                id=str(uuid.uuid4()),
                session_id=session_id,
                memory_tree=memory_tree,
                timeline=timeline,
                index_map=index_map,
            )
            self.session.add(working_memory)

        await self.session.flush()
        return working_memory

    # Agent step operations
    async def create_agent_step(
        self,
        session_id: str,
        step_number: int,
        description: str,
        agent_type: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> AgentStep:
        """Create a new agent step."""
        step = AgentStep(
            id=str(uuid.uuid4()),
            session_id=session_id,
            step_number=step_number,
            description=description,
            agent_type=agent_type,
            message_id=message_id,
            status="pending",
        )
        self.session.add(step)
        await self.session.flush()
        return step

    async def update_agent_step(
        self,
        step_id: str,
        status: Optional[str] = None,
        result: Optional[str] = None,
        logs: Optional[str] = None,
    ) -> Optional[AgentStep]:
        """Update an agent step."""
        result = await self.session.execute(
            select(AgentStep).where(AgentStep.id == step_id)
        )
        step = result.scalar_one_or_none()
        if step:
            if status:
                step.status = status
            if result:
                step.result = result
            if logs:
                step.logs = logs
            if status == "completed":
                from datetime import datetime

                step.completed_at = datetime.utcnow()
            await self.session.flush()
        return step

    async def get_agent_steps(
        self, session_id: str, message_id: Optional[str] = None
    ) -> List[AgentStep]:
        """Get agent steps for a session."""
        query = select(AgentStep).where(AgentStep.session_id == session_id)
        if message_id:
            query = query.where(AgentStep.message_id == message_id)
        query = query.order_by(AgentStep.step_number.asc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # Search operations
    async def search_messages(self, query: str, limit: int = 50) -> List[tuple]:
        """
        Search messages by content.
        Returns list of (session, message, match_info) tuples.
        Falls back to LIKE query if FTS5 is not available.
        """
        # Try FTS5 first for better performance and highlighting
        try:
            return await self.search_messages_fts5(query, limit)
        except Exception:
            # Fallback to LIKE query
            search_pattern = f"%{query}%"
            result = await self.session.execute(
                select(Message, ChatSession)
                .join(ChatSession, Message.session_id == ChatSession.id)
                .where(
                    and_(
                        Message.content.like(search_pattern),
                        ChatSession.archived == False,
                    )
                )
                .limit(limit)
            )
            return list(result.all())

    async def search_messages_fts5(self, query: str, limit: int = 50) -> List[tuple]:
        """
        Full-text search using SQLite FTS5.
        Returns results with highlighted snippets and ranking.
        """
        from sqlalchemy import text

        # FTS5 search with ranking and highlighting
        # Uses bm25 ranking for relevance and snippet() for highlighting
        fts_query = f"""
            SELECT 
                messages.id,
                messages.session_id,
                messages.content,
                messages.role,
                messages.agent_type,
                messages.created_at,
                messages.extra_data,
                chat_sessions.title,
                bm25(messages_fts) as rank,
                snippet(messages_fts, 0, '<mark>', '</mark>', '...', 64) as highlighted_content
            FROM messages_fts
            JOIN messages ON messages.id = messages_fts.rowid
            JOIN chat_sessions ON messages.session_id = chat_sessions.id
            WHERE messages_fts MATCH :query
                AND chat_sessions.archived = 0
            ORDER BY rank ASC
            LIMIT :limit
        """

        result = await self.session.execute(
            text(fts_query), {"query": query, "limit": limit}
        )

        results = []
        for row in result.fetchall():
            # Create a tuple-like structure (message, session, highlight)
            message = type(
                "FTSMessage",
                (),
                {
                    "id": row[0],
                    "session_id": row[1],
                    "content": row[2],
                    "role": row[3],
                    "agent_type": row[4],
                    "created_at": row[5],
                    "extra_data": row[6],
                },
            )()

            session = type(
                "FTSChatSession",
                (),
                {"id": row[1], "title": row[8], "archived": False},
            )()

            highlight = row[10] if row[10] else row[2][:200]

            results.append((message, session, highlight))

        return results

    async def search_sessions_by_title(
        self, query: str, limit: int = 20
    ) -> List[ChatSession]:
        """
        Search sessions by title (for quick session search).
        """
        search_pattern = f"%{query}%"
        result = await self.session.execute(
            select(ChatSession)
            .where(
                and_(
                    ChatSession.title.like(search_pattern),
                    ChatSession.archived == False,
                )
            )
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_search_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """
        Get search suggestions based on recent message content.
        Returns a list of suggested search terms.
        """
        # Get unique words from recent messages that match the query prefix
        search_pattern = f"{query}%"
        result = await self.session.execute(
            select(Message.content)
            .join(ChatSession, Message.session_id == ChatSession.id)
            .where(
                and_(
                    Message.content.like(search_pattern),
                    ChatSession.archived == False,
                )
            )
            .limit(limit)
        )
        return [row[0] for row in result.fetchall() if row[0]]
