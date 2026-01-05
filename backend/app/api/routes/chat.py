"""
Chat endpoints with message sending and SSE streaming.

Optimized for low latency (< 100ms):
- Uses asyncio.Queue for efficient event streaming
- Working memory update streaming for real-time agent progress
- Keep-alive comments every 30 seconds
- Optimized event formatting
- Minimal buffering

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
from app.agents.graph import run_agent_workflow_with_streaming
from app.agents.memory import AsyncWorkingMemory
from app.utils.streaming import (
    event_manager,
    event_generator,
    SSEEventManager,
    format_sse_event,
)
from app.utils.validators import sanitize_message_content


router = APIRouter()


class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message."""

    content: str = Field(
        ..., min_length=1, max_length=10000, description="User message content"
    )
    deep_search: bool = False
    timezone: str = "UTC"


class ChatMessageResponse(BaseModel):
    """Response model for message creation."""

    message_id: str
    session_id: str
    created_at: str


async def run_agent_with_events(
    session_id: str,
    user_message: str,
    deep_search: bool,
    message_id: str,
    user_timezone: str = "UTC",
) -> Dict[str, Any]:
    """
    Run agent workflow and stream events including working memory updates.

    Args:
        session_id: Session identifier
        user_message: User's message
        deep_search: Whether to use deep search
        message_id: Message ID for tracking
        user_timezone: User's timezone for context

    Returns:
        Final state from agent execution
    """
    from app.utils.session_task_manager import get_session_task_manager

    task_manager = get_session_task_manager()
    current_task = asyncio.current_task()

    if current_task:
        task_manager.register_task(session_id, current_task)

    try:
        if task_manager.is_cancelled(session_id):
            return {
                "status": "cancelled",
                "session_id": session_id,
                "message": "Agent execution has been cancelled",
            }

        await event_manager.emit_thought(
            session_id=session_id,
            agent="master",
            content=f"Processing: {user_message[:100]}...",
        )

        final_state = await run_agent_workflow_with_streaming(
            user_message=user_message,
            session_id=session_id,
            deep_search=deep_search,
            user_timezone=user_timezone,
            event_manager=event_manager,
        )

        if task_manager.is_cancelled(session_id):
            return {
                "status": "cancelled",
                "session_id": session_id,
                "message": "Agent execution has been cancelled",
            }

        await event_manager.emit_complete(
            session_id=session_id,
            message_id=message_id,
            final_answer=final_state.get("final_answer", ""),
        )

        return final_state

    except asyncio.CancelledError:
        await event_manager.emit_error(
            session_id=session_id,
            error="Execution cancelled by user",
            error_type="cancellation",
            can_retry=False,
        )
        return {
            "status": "cancelled",
            "session_id": session_id,
            "message": "Agent execution has been cancelled",
        }

    except Exception as e:
        error_data = {
            "error": str(e),
            "message_id": message_id,
            "session_id": session_id,
        }

        await event_manager.emit_error(
            session_id=session_id,
            error=str(e),
            error_type="execution_error",
            can_retry=True,
        )

        return {"error": str(e), "session_id": session_id}

    finally:
        if current_task:
            task_manager.unregister_task(session_id, current_task)


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
    Sanitizes input to prevent XSS attacks.
    """
    sanitized_content = sanitize_message_content(request.content, max_length=10000)

    repo = ChatRepository(db)
    config = config_manager.load()

    if session_id:
        chat_session = await repo.get_session(session_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        title = (
            sanitized_content[:50] + "..."
            if len(sanitized_content) > 50
            else sanitized_content
        )
        chat_session = await repo.create_session(title=title)
        session_id = chat_session.id

    message = await repo.create_message(
        session_id=session_id,
        role="user",
        content=sanitized_content,
        extra_data={"deep_search": request.deep_search},
    )

    assistant_message = await repo.create_message(
        session_id=session_id,
        role="assistant",
        content="",
        agent_type="master",
        extra_data={"deep_search": request.deep_search},
    )

    await repo.save_working_memory(
        session_id=session_id,
        memory_tree={},
        timeline=[],
        index_map={},
    )

    asyncio.create_task(
        run_agent_with_events(
            session_id=session_id,
            user_message=sanitized_content,
            deep_search=request.deep_search,
            message_id=assistant_message.id,
            user_timezone=request.timezone,
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
    - memory_update: Working memory update
    - node_added: New memory node added
    - node_updated: Memory node updated
    - timeline_update: New timeline entry
    - step_progress: Step progress update
    - message_chunk: Streaming final response
    - error: Error occurred
    - complete: Execution finished
    """
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

    Sends termination signal to stop the agent workflow and close the event queue.
    """
    from app.utils.shutdown import cancel_session_execution
    from app.utils.session_task_manager import get_session_task_manager

    task_manager = get_session_task_manager()
    task_manager.get_cancellation_event(session_id).set()

    task_success = await task_manager.cancel_session(session_id)
    event_success = await cancel_session_execution(session_id)

    return {
        "status": "cancelled" if (task_success or event_success) else "error",
        "session_id": session_id,
        "message": "Agent execution has been cancelled"
        if (task_success or event_success)
        else "Failed to cancel session",
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

    Returns paginated messages with total count for client-side pagination.
    """
    repo = ChatRepository(db)

    session = await repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await repo.get_messages(session_id, limit=limit, offset=offset)
    total = await repo.get_message_count(session_id)
    has_more = (offset + len(messages)) < total

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
            "total": total,
            "has_more": has_more,
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
