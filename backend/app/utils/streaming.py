"""
SSE Streaming Utilities for Working Memory Updates

Provides event streaming for real-time agent progress updates including:
- Working memory updates (tree, timeline, index)
- Node additions and updates
- Step progress tracking
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator, Callable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """SSE event model."""

    event: str  # memory_update, node_added, node_updated, step_progress, thought, complete, error
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class SSEEventManager:
    """
    Manages SSE event queues and emissions for working memory updates.

    Thread-safe implementation using asyncio.Queue for event streaming.
    """

    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, session_id: str) -> asyncio.Lock:
        """Get or create a lock for the session."""
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    def get_queue(self, session_id: str) -> asyncio.Queue:
        """Get or create an event queue for a session."""
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue()
        return self._queues[session_id]

    async def emit(
        self,
        session_id: str,
        event_type: str,
        data: Dict[str, Any],
    ) -> None:
        """
        Emit an SSE event to the session's queue.

        Args:
            session_id: Session identifier
            event_type: Type of event (memory_update, node_added, etc.)
            data: Event data payload
        """
        async with self._get_lock(session_id):
            queue = self.get_queue(session_id)
            event = StreamEvent(event=event_type, data=data)
            await queue.put(event)
            logger.debug(f"Emitted {event_type} event for session {session_id}")

    async def emit_memory_update(
        self,
        session_id: str,
        memory_tree: Dict[str, Any],
        timeline: list,
        index: Dict[str, Any],
        update_type: str = "full",
    ) -> None:
        """
        Emit a working memory update event.

        Args:
            session_id: Session identifier
            memory_tree: The memory tree structure
            timeline: The timeline entries
            index: The node index
            update_type: Type of update ('full', 'incremental', 'node_add', 'node_update')
        """
        await self.emit(
            session_id,
            "memory_update",
            {
                "update_type": update_type,
                "memory_tree": memory_tree,
                "timeline": timeline,
                "index": index,
                "stats": {
                    "total_nodes": len(index),
                    "timeline_length": len(timeline),
                },
            },
        )

    async def emit_node_added(
        self,
        session_id: str,
        node_id: str,
        agent: str,
        node_type: str,
        description: str,
        parent_id: Optional[str] = None,
        content: Optional[Any] = None,
    ) -> None:
        """
        Emit a node added event.

        Args:
            session_id: Session identifier
            node_id: ID of the new node
            agent: Agent that created the node
            node_type: Type of node (step, thought, result, etc.)
            description: Node description
            parent_id: Parent node ID
            content: Node content
        """
        await self.emit(
            session_id,
            "node_added",
            {
                "node_id": node_id,
                "agent": agent,
                "node_type": node_type,
                "description": description,
                "parent_id": parent_id,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def emit_node_updated(
        self,
        session_id: str,
        node_id: str,
        status: Optional[str] = None,
        content: Optional[Any] = None,
        completed: bool = False,
    ) -> None:
        """
        Emit a node updated event.

        Args:
            session_id: Session identifier
            node_id: ID of the updated node
            status: New status (pending, running, completed, failed)
            content: Updated content
            completed: Whether the node is completed
        """
        await self.emit(
            session_id,
            "node_updated",
            {
                "node_id": node_id,
                "status": status,
                "content": content,
                "completed": completed,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def emit_timeline_update(
        self,
        session_id: str,
        node_id: str,
        agent: str,
        node_type: str,
        description: str,
        status: str,
        parent_id: Optional[str] = None,
    ) -> None:
        """
        Emit a timeline update event.

        Args:
            session_id: Session identifier
            node_id: ID of the node
            agent: Agent that created the entry
            node_type: Type of node
            description: Entry description
            status: Current status
            parent_id: Parent node ID
        """
        await self.emit(
            session_id,
            "timeline_update",
            {
                "node_id": node_id,
                "agent": agent,
                "node_type": node_type,
                "description": description,
                "status": status,
                "parent_id": parent_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def emit_step_progress(
        self,
        session_id: str,
        step_id: str,
        step_number: int,
        total_steps: int,
        agent: str,
        status: str,
        description: str,
        logs: Optional[str] = None,
    ) -> None:
        """
        Emit a step progress update event.

        Args:
            session_id: Session identifier
            step_id: Step node ID
            step_number: Current step number (1-indexed)
            total_steps: Total number of steps in plan
            agent: Agent responsible for the step
            status: Step status
            description: Step description
            logs: Optional logs for the step
        """
        await self.emit(
            session_id,
            "step_progress",
            {
                "step_id": step_id,
                "step_number": step_number,
                "total_steps": total_steps,
                "agent": agent,
                "status": status,
                "description": description,
                "logs": logs,
                "progress_percentage": round(
                    (step_number / max(total_steps, 1)) * 100, 1
                ),
            },
        )

    async def emit_thought(
        self,
        session_id: str,
        agent: str,
        content: str,
    ) -> None:
        """
        Emit a thought event (agent thinking process).

        Args:
            session_id: Session identifier
            agent: Agent producing the thought
            content: Thought content
        """
        await self.emit(
            session_id,
            "thought",
            {
                "agent": agent,
                "content": content,
            },
        )

    async def emit_error(
        self,
        session_id: str,
        error: str,
        error_type: str = "execution_error",
        can_retry: bool = True,
    ) -> None:
        """
        Emit an error event.

        Args:
            session_id: Session identifier
            error: Error message
            error_type: Type of error
            can_retry: Whether the operation can be retried
        """
        await self.emit(
            session_id,
            "error",
            {
                "error": error,
                "error_type": error_type,
                "can_retry": can_retry,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def emit_complete(
        self,
        session_id: str,
        message_id: str,
        final_answer: str = "",
    ) -> None:
        """
        Emit a completion event.

        Args:
            session_id: Session identifier
            message_id: Assistant message ID
            final_answer: Final response content
        """
        await self.emit(
            session_id,
            "complete",
            {
                "message_id": message_id,
                "session_id": session_id,
                "final_answer": final_answer,
            },
        )

    async def emit_message_chunk(
        self,
        session_id: str,
        content: str,
        delta: str = "",
        is_complete: bool = False,
    ) -> None:
        """
        Emit a message chunk event for streaming LLM responses.

        Args:
            session_id: Session identifier
            content: Accumulated content so far
            delta: New content chunk
            is_complete: Whether this is the final chunk
        """
        await self.emit(
            session_id,
            "message_chunk",
            {
                "content": content,
                "delta": delta,
                "is_complete": is_complete,
            },
        )

    async def close(self, session_id: str) -> None:
        """Close and clean up the event queue for a session."""
        async with self._get_lock(session_id):
            if session_id in self._queues:
                await self._queues[session_id].put(None)
                del self._queues[session_id]
            if session_id in self._locks:
                del self._locks[session_id]

    def get_queue_count(self) -> int:
        """Get the number of active event queues."""
        return len(self._queues)


# Global event manager instance
event_manager = SSEEventManager()


def format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """
    Format data as an SSE event.

    Args:
        event_type: Type of the event
        data: Event data dictionary

    Returns:
        Formatted SSE event string
    """
    return f"event: {event_type}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


async def event_generator(
    session_id: str,
    timeout: float = 30.0,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events from the session queue.

    Args:
        session_id: Session identifier
        timeout: Timeout for waiting on queue (seconds)

    Yields:
        Formatted SSE event strings
    """
    queue = event_manager.get_queue(session_id)

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=timeout)

                if event is None:
                    break

                yield format_sse_event(
                    event.event,
                    {
                        **event.data,
                        "_timestamp": event.timestamp,
                    },
                )

            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

    except asyncio.CancelledError:
        logger.debug(f"SSE stream cancelled for session {session_id}")
        raise
    finally:
        await event_manager.close(session_id)


class WorkingMemoryStreamer:
    """
    Helper class for streaming working memory updates.

    Wraps AsyncWorkingMemory to emit SSE events on mutations.
    """

    def __init__(
        self,
        session_id: str,
        event_manager: Optional[SSEEventManager] = None,
    ):
        self.session_id = session_id
        if event_manager is not None:
            self.event_manager = event_manager
        else:
            import app.utils.streaming as streaming_module

            self.event_manager = streaming_module.event_manager
        self._memory_data: Optional[Dict[str, Any]] = None

    async def emit_node_added(
        self,
        node_id: str,
        agent: str,
        node_type: str,
        description: str,
        parent_id: Optional[str] = None,
        content: Optional[Any] = None,
    ) -> None:
        """Emit node added event and update state."""
        await self.event_manager.emit_node_added(
            session_id=self.session_id,
            node_id=node_id,
            agent=agent,
            node_type=node_type,
            description=description,
            parent_id=parent_id,
            content=content,
        )

        # Update cached memory data for incremental updates
        if self._memory_data:
            self._memory_data["index"][node_id] = {
                "id": node_id,
                "agent": agent,
                "node_type": node_type,
                "description": description,
                "status": "running",
                "parent_id": parent_id,
                "content": content,
                "children": [],
            }
            self._memory_data["timeline"].append(
                {
                    "node_id": node_id,
                    "agent": agent,
                    "node_type": node_type,
                    "description": description,
                    "status": "running",
                }
            )

    async def emit_node_updated(
        self,
        node_id: str,
        status: Optional[str] = None,
        content: Optional[Any] = None,
        completed: bool = False,
    ) -> None:
        """Emit node updated event."""
        await self.event_manager.emit_node_updated(
            session_id=self.session_id,
            node_id=node_id,
            status=status,
            content=content,
            completed=completed,
        )

        # Update cached memory data
        if self._memory_data and node_id in self._memory_data["index"]:
            if status:
                self._memory_data["index"][node_id]["status"] = status
            if content is not None:
                self._memory_data["index"][node_id]["content"] = content
            if completed:
                self._memory_data["index"][node_id]["completed_at"] = (
                    datetime.utcnow().isoformat()
                )

    async def emit_memory_snapshot(
        self,
        memory_tree: Dict[str, Any],
        timeline: list,
        index: Dict[str, Any],
        update_type: str = "full",
    ) -> None:
        """Emit full working memory snapshot."""
        self._memory_data = {
            "tree": memory_tree,
            "timeline": timeline,
            "index": index,
        }

        await self.event_manager.emit_memory_update(
            session_id=self.session_id,
            memory_tree=memory_tree,
            timeline=timeline,
            index=index,
            update_type=update_type,
        )

    def get_cached_memory(self) -> Optional[Dict[str, Any]]:
        """Get cached memory data for incremental updates."""
        return self._memory_data
