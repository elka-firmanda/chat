"""
Chat endpoints with message sending and SSE streaming.
"""

import uuid
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.repositories.chat import ChatRepository
from app.config.config_manager import get_config


router = APIRouter()


class ChatMessageRequest(BaseModel):
    content: str
    deep_search: bool = False


class ChatMessageResponse(BaseModel):
    message_id: str
    session_id: str
    created_at: str


@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    session_id: str = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message and start agent processing.
    Returns immediately with message_id for SSE streaming.
    """
    repo = ChatRepository(db)

    # Get or create session
    if session_id:
        chat_session = await repo.get_session(session_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        # Create new session
        chat_session = await repo.create_session(
            title=request.content[:50] if len(request.content) > 50 else request.content
        )
        session_id = chat_session.id

    # Create user message
    message = await repo.create_message(
        session_id=session_id,
        role="user",
        content=request.content,
        extra_data={"deep_search": request.deep_search},
    )

    return {
        "message_id": message.id,
        "session_id": session_id,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


@router.get("/stream/{session_id}")
async def stream_response(session_id: str):
    """
    SSE stream for real-time agent updates.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        # This is a placeholder - actual implementation will stream agent events
        yield f"data: {session_id}\n\n"

        # Simulate some processing
        import asyncio

        await asyncio.sleep(0.5)
        yield f'data: {{"event": "complete", "session_id": "{session_id}"}}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/cancel/{session_id}")
async def cancel_execution(session_id: str):
    """
    Cancel ongoing agent execution for a session.
    """
    # TODO: Implement cancellation logic
    return {
        "status": "cancelled",
        "session_id": session_id,
        "message": "Agent execution has been cancelled",
    }


@router.post("/fork/{message_id}")
async def fork_conversation(message_id: str, db: AsyncSession = Depends(get_db)):
    """
    Fork conversation from a specific message.
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

    return {
        "new_session_id": new_session.id,
        "forked_from_message_id": message_id,
        "message_count": len(
            [
                m
                for m in original_messages
                if m.created_at <= original_message.created_at
            ]
        ),
    }
