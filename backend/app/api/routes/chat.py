"""
Chat endpoints with message sending and SSE streaming.

Implements:
- POST /api/v1/chat/message - Send message and start agent
- GET /api/v1/chat/stream/{session_id} - SSE stream for real-time updates
- POST /api/v1/chat/cancel/{session_id} - Cancel ongoing execution
- POST /api/v1/chat/fork/{message_id} - Fork conversation
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.repositories.chat import ChatRepository
from app.config.config_manager import get_config, config_manager
from app.agents.graph import run_agent_workflow
from app.agents.memory import AsyncWorkingMemory


router = APIRouter()


# Event queue storage (in-memory, per-session)
event_queues: Dict[str, asyncio.Queue] = {}


class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message."""

    content: str
    deep_search: bool = False


class ChatMessageResponse(BaseModel):
    """Response model for message creation."""

    message_id: str
    session_id: str
    created_at: str


class StreamEvent(BaseModel):
    """SSE event model."""

    event: str  # thought, step_update, message_chunk, error, complete
    data: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


def get_event_queue(session_id: str) -> asyncio.Queue:
    """Get or create event queue for a session."""
    if session_id not in event_queues:
        event_queues[session_id] = asyncio.Queue()
    return event_queues[session_id]


def format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """Format data as SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def event_generator(session_id: str) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for a session.

    Yields formatted SSE events until the queue is closed or cancelled.
    """
    queue = get_event_queue(session_id)

    try:
        while True:
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(queue.get(), timeout=30.0)

                # Check for termination signal
                if event is None:
                    break

                # Format and yield event
                yield format_sse_event(event["event"], event["data"])

            except asyncio.TimeoutError:
                # Send keep-alive comment
                yield ": keepalive\n\n"

    except asyncio.CancelledError:
        # Client disconnected
        pass
    finally:
        # Cleanup
        if session_id in event_queues:
            del event_queues[session_id]


async def run_agent_with_events(
    session_id: str,
    user_message: str,
    deep_search: bool,
    message_id: str,
) -> Dict[str, Any]:
    """
    Run agent workflow and stream events.

    Args:
        session_id: Session identifier
        user_message: User's message
        deep_search: Whether to use deep search
        message_id: Message ID for tracking

    Returns:
        Final state from agent execution
    """
    queue = get_event_queue(session_id)

    # Send thought event
    await queue.put(
        {
            "event": "thought",
            "data": {
                "agent": "master",
                "content": f"Processing: {user_message[:100]}...",
            },
        }
    )

    try:
        # Run the agent workflow
        final_state = await run_agent_workflow(
            user_message=user_message,
            session_id=session_id,
            deep_search=deep_search,
        )

        # Send complete event
        await queue.put(
            {
                "event": "complete",
                "data": {
                    "message_id": message_id,
                    "session_id": session_id,
                    "final_answer": final_state.get("final_answer", ""),
                },
            }
        )

        return final_state

    except Exception as e:
        error_data = {
            "error": str(e),
            "message_id": message_id,
            "session_id": session_id,
        }

        await queue.put(
            {
                "event": "error",
                "data": error_data,
            }
        )

        return {"error": str(e), "session_id": session_id}


@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message and start agent processing.

    Creates a new session if session_id is not provided.
    Returns immediately with message_id for SSE streaming.
    """
    repo = ChatRepository(db)
    config = config_manager.load()

    # Get or create session
    if session_id:
        chat_session = await repo.get_session(session_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        # Create new session
        title = (
            request.content[:50] + "..."
            if len(request.content) > 50
            else request.content
        )
        chat_session = await repo.create_session(title=title)
        session_id = chat_session.id

    # Create user message
    message = await repo.create_message(
        session_id=session_id,
        role="user",
        content=request.content,
        extra_data={"deep_search": request.deep_search},
    )

    # Create assistant message placeholder
    assistant_message = await repo.create_message(
        session_id=session_id,
        role="assistant",
        content="",
        agent_type="master",
        extra_data={"deep_search": request.deep_search},
    )

    # Initialize working memory for session
    await repo.save_working_memory(
        session_id=session_id,
        memory_tree={},
        timeline=[],
        index_map={},
    )

    # Start agent execution in background
    asyncio.create_task(
        run_agent_with_events(
            session_id=session_id,
            user_message=request.content,
            deep_search=request.deep_search,
            message_id=assistant_message.id,
        )
    )

    return {
        "message_id": assistant_message.id,
        "session_id": session_id,
        "created_at": assistant_message.created_at.isoformat()
        if assistant_message.created_at
        else None,
    }


@router.get("/stream/{session_id}")
async def stream_response(
    session_id: str,
    request: Request,
):
    """
    SSE stream for real-time agent updates.

    Events:
    - thought: Agent thinking process
    - step_update: Progress step status change
    - message_chunk: Streaming final response
    - error: Error occurred
    - complete: Execution finished
    """
    # Verify session exists
    # Note: We'd need db dependency but StreamingResponse doesn't support it cleanly
    # For now, we assume session is valid if stream is requested

    return StreamingResponse(
        event_generator(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.post("/cancel/{session_id}")
async def cancel_execution(session_id: str):
    """
    Cancel ongoing agent execution for a session.

    Sends termination signal to the event queue.
    """
    queue = event_queues.get(session_id)

    if queue:
        # Signal termination
        await queue.put(None)
        del event_queues[session_id]

    return {
        "status": "cancelled",
        "session_id": session_id,
        "message": "Agent execution has been cancelled",
    }


@router.post("/fork/{message_id}")
async def fork_conversation(
    message_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Fork conversation from a specific message.

    Creates a new session with all messages up to and including the fork point.
    """
    repo = ChatRepository(db)

    # Get the original message
    original_message = await repo.get_message(message_id)
    if not original_message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Create new session with messages up to fork point
    new_session = await repo.create_session(
        title=f"Fork: {original_message.content[:50]}"
    )

    # Copy messages up to and including the fork message
    original_messages = await repo.get_messages(original_message.session_id)

    fork_count = 0
    for msg in original_messages:
        if msg.created_at <= original_message.created_at:
            await repo.create_message(
                session_id=new_session.id,
                role=msg.role,
                content=msg.content,
                agent_type=msg.agent_type,
                parent_message_id=msg.parent_message_id,
                extra_data=msg.extra_data,
            )
            fork_count += 1

    # Copy working memory from original session
    working_memory = await repo.get_working_memory(original_message.session_id)
    if working_memory:
        await repo.save_working_memory(
            session_id=new_session.id,
            memory_tree=working_memory.memory_tree,
            timeline=working_memory.timeline,
            index_map=working_memory.index_map,
        )

    return {
        "new_session_id": new_session.id,
        "forked_from_message_id": message_id,
        "message_count": fork_count,
    }


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    limit: int = 30,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Get chat history for a session.

    Returns all messages in the conversation.
    """
    repo = ChatRepository(db)

    # Verify session exists
    session = await repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get messages
    messages = await repo.get_messages(session_id, limit=limit, offset=offset)

    # Get working memory
    working_memory = await repo.get_working_memory(session_id)

    return {
        "session_id": session_id,
        "title": session.title,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "agent_type": msg.agent_type,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "extra_data": msg.extra_data,
            }
            for msg in messages
        ],
        "working_memory": {
            "memory_tree": working_memory.memory_tree if working_memory else None,
            "timeline": working_memory.timeline if working_memory else None,
            "index_map": working_memory.index_map if working_memory else None,
        }
        if working_memory
        else None,
        "pagination": {
            "limit": limit,
            "offset": offset,
        },
    }


class InterventionRequest(BaseModel):
    """Request model for user intervention."""

    action: str  # 'retry', 'skip', 'abort'


@router.post("/intervene/{session_id}")
async def handle_intervention(
    session_id: str,
    request: InterventionRequest,
):
    """
    Handle user intervention for a session.

    Allows user to retry, skip, or abort after error.
    """
    from app.agents.error_handler import (
        InterventionAction,
        get_intervention_state,
        clear_intervention_state,
    )

    intervention_state = get_intervention_state(session_id)

    if not intervention_state.awaiting_response:
        return {
            "status": "error",
            "message": "No pending intervention for this session",
            "session_id": session_id,
        }

    # Map action string to InterventionAction
    action_map = {
        "retry": InterventionAction.RETRY,
        "skip": InterventionAction.SKIP,
        "abort": InterventionAction.ABORT,
    }

    action = action_map.get(request.action.lower())
    if not action:
        return {
            "status": "error",
            "message": f"Invalid action: {request.action}. Must be 'retry', 'skip', or 'abort'",
            "session_id": session_id,
        }

    # Set the intervention response
    intervention_state.set_response(action)

    return {
        "status": "success",
        "message": f"Intervention '{request.action}' recorded",
        "session_id": session_id,
        "action": request.action,
    }


@router.get("/intervention/{session_id}")
async def get_intervention_status(session_id: str):
    """
    Get the current intervention status for a session.

    Returns whether the session is awaiting user intervention.
    """
    from app.agents.error_handler import get_intervention_state

    intervention_state = get_intervention_state(session_id)

    return {
        "session_id": session_id,
        "awaiting_response": intervention_state.awaiting_response,
        "pending_error": intervention_state.pending_error.to_dict()
        if intervention_state.pending_error
        else None,
        "available_actions": ["retry", "skip", "abort"]
        if intervention_state.awaiting_response
        else [],
    }
