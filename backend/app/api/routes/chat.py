"""Chat API endpoints with SSE streaming."""

import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.config.config_manager import config_manager, get_config
from app.db.session import get_db
from app.db.repositories.chat import ChatRepository
from app.models.chat import (
    ChatRequest,
    ChatResponse,
    Message,
    MessageRole,
    PlanStep,
    PlanStepStatus,
)
from app.utils.validators import sanitize_message_content

router = APIRouter()


async def stream_chat_response(
    chat_request: ChatRequest,
    session_id: str,
    db: AsyncSession,
) -> AsyncGenerator[dict, None]:
    """Stream chat response with progress updates."""
    from app.agents.master import MasterAgent

    repo = ChatRepository(db)
    config = get_config()

    try:
        master = MasterAgent(session_id=session_id)

        if chat_request.deep_search:
            yield {
                "event": "status",
                "data": json.dumps({"message": "Creating execution plan..."}),
            }

            plan = await master.planner.create_plan(
                chat_request.message, session_id, deep_search=True
            )

            plan_steps = [
                PlanStep(
                    step_number=i + 1,
                    description=step.get("description", ""),
                    agent=step.get("agent"),
                )
                for i, step in enumerate(plan)
            ]

            yield {
                "event": "plan",
                "data": json.dumps({"steps": [s.model_dump() for s in plan_steps]}),
            }

            results = []
            for i, step in enumerate(plan):
                agent_name = step.get("agent", "researcher")
                step_desc = step.get("description", "")[:80]
                if len(step.get("description", "")) > 80:
                    step_desc += "..."

                status_messages = {
                    "researcher": f"Searching the web: {step_desc}",
                    "tools": f"Running tools: {step_desc}",
                    "database": f"Querying database: {step_desc}",
                    "python": f"Running Python analysis: {step_desc}",
                    "master": "Synthesizing final response...",
                }
                status_msg = status_messages.get(agent_name, f"Processing: {step_desc}")

                yield {
                    "event": "status",
                    "data": json.dumps({"message": status_msg}),
                }

                yield {
                    "event": "step_update",
                    "data": json.dumps({"step_index": i, "status": "in_progress"}),
                }

                try:
                    result = await master._execute_single_step(
                        step, chat_request.message, results, session_id
                    )
                    results.append(
                        {
                            "step": step.get("description", f"Step {i + 1}"),
                            "result": result,
                            "agent": agent_name,
                        }
                    )

                    yield {
                        "event": "step_update",
                        "data": json.dumps(
                            {
                                "step_index": i,
                                "status": "completed",
                                "result": result[:500] if result else None,
                            }
                        ),
                    }
                except Exception as e:
                    yield {
                        "event": "step_update",
                        "data": json.dumps(
                            {
                                "step_index": i,
                                "status": "failed",
                                "error": str(e),
                            }
                        ),
                    }

            yield {
                "event": "status",
                "data": json.dumps({"message": "Generating final response..."}),
            }

            final_response = ""
            async for token in master.synthesize_response_stream(
                chat_request.message, results
            ):
                final_response += token
                yield {
                    "event": "token",
                    "data": json.dumps({"token": token}),
                }

            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=final_response,
                metadata={
                    "deep_search": True,
                    "plan": [s.model_dump() for s in plan_steps],
                },
            )

        else:
            response = ""
            async for token in master.chat_stream(chat_request.message):
                response += token
                yield {
                    "event": "token",
                    "data": json.dumps({"token": token}),
                }

            assistant_message = Message(
                role=MessageRole.ASSISTANT,
                content=response,
                metadata={"deep_search": False},
            )

        user_message = Message(role=MessageRole.USER, content=chat_request.message)

        await repo.create_message(
            session_id=session_id,
            role="user",
            content=chat_request.message,
            extra_data={"deep_search": chat_request.deep_search},
        )

        db_assistant_msg = await repo.create_message(
            session_id=session_id,
            role="assistant",
            content=assistant_message.content,
            agent_type="master",
            extra_data=assistant_message.metadata,
        )

        title = await master.generate_title(
            chat_request.message, assistant_message.content
        )
        await repo.update_session_title(session_id, title)

        yield {
            "event": "message",
            "data": json.dumps(
                {
                    "session_id": session_id,
                    "message": assistant_message.model_dump(),
                },
                default=str,
            ),
        }

        yield {"event": "done", "data": json.dumps({})}

    except Exception as e:
        yield {"event": "error", "data": json.dumps({"message": str(e)})}


class ChatMessageRequest(BaseModel):
    """Request for /message endpoint (legacy)."""

    content: str = Field(..., min_length=1, max_length=10000)
    deep_search: bool = False
    timezone: str = "UTC"


@router.post("/send")
async def send_message(
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Send a chat message and get response (non-streaming)."""
    repo = ChatRepository(db)
    sanitized_content = sanitize_message_content(chat_request.message, max_length=10000)

    session_id = chat_request.session_id
    if not session_id:
        session = await repo.create_session(title=sanitized_content[:50])
        session_id = session.id
    else:
        session = await repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    from app.agents.master import MasterAgent

    master = MasterAgent(session_id=session_id)

    plan = None
    plan_steps = None
    if chat_request.deep_search:
        result = await master.execute(
            {
                "query": sanitized_content,
                "deep_search": True,
                "session_id": session_id,
            }
        )
        response_content = result.get("answer", "")
        plan_steps = result.get("plan", [])
    else:
        response_content = await master.chat(sanitized_content)

    await repo.create_message(
        session_id=session_id,
        role="user",
        content=sanitized_content,
        extra_data={"deep_search": chat_request.deep_search},
    )

    assistant_db_msg = await repo.create_message(
        session_id=session_id,
        role="assistant",
        content=response_content,
        agent_type="master",
        extra_data={
            "deep_search": chat_request.deep_search,
            "plan": [s.model_dump() for s in plan_steps] if plan_steps else None,
        },
    )

    title = await master.generate_title(sanitized_content, response_content)
    await repo.update_session_title(session_id, title)

    assistant_message = Message(
        role=MessageRole.ASSISTANT,
        content=response_content,
        metadata={
            "deep_search": chat_request.deep_search,
            "plan": [s.model_dump() for s in plan_steps] if plan_steps else None,
        },
    )

    return ChatResponse(
        session_id=session_id,
        message=assistant_message,
        plan=plan_steps,
    )


@router.post("/stream")
async def stream_message(
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """Send a chat message and stream response with SSE."""
    repo = ChatRepository(db)
    sanitized_content = sanitize_message_content(chat_request.message, max_length=10000)

    session_id = chat_request.session_id
    if not session_id:
        session = await repo.create_session(title=sanitized_content[:50])
        session_id = session.id
    else:
        session = await repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    sanitized_request = ChatRequest(
        message=sanitized_content,
        session_id=session_id,
        deep_search=chat_request.deep_search,
    )

    return EventSourceResponse(
        stream_chat_response(sanitized_request, session_id, db),
        media_type="text/event-stream",
    )


@router.post("/message")
async def send_message_legacy(
    request: ChatMessageRequest,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Legacy endpoint - Send a message and start agent processing."""
    sanitized_content = sanitize_message_content(request.content, max_length=10000)
    repo = ChatRepository(db)

    if session_id:
        chat_session = await repo.get_session(session_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        chat_session = await repo.create_session(title=sanitized_content[:50])
        session_id = chat_session.id

    await repo.create_message(
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

    return {
        "message_id": assistant_message.id,
        "session_id": session_id,
        "created_at": assistant_message.created_at.isoformat()
        if assistant_message.created_at
        else None,
        "stream_url": f"/api/v1/chat/stream",
    }


@router.get("/stream/{session_id}")
async def stream_response_legacy(session_id: str):
    """Legacy SSE stream endpoint - deprecated, use POST /stream instead."""
    raise HTTPException(
        status_code=410,
        detail="This endpoint is deprecated. Use POST /api/v1/chat/stream instead.",
    )


@router.post("/cancel/{session_id}")
async def cancel_execution(session_id: str):
    """Cancel ongoing agent execution for a session."""
    return {
        "status": "cancelled",
        "session_id": session_id,
        "message": "Cancellation requested",
    }


@router.post("/fork/{message_id}")
async def fork_conversation(
    message_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Fork conversation from a specific message."""
    repo = ChatRepository(db)

    original_message = await repo.get_message(message_id)
    if not original_message:
        raise HTTPException(status_code=404, detail="Message not found")

    new_session = await repo.create_session(
        title=f"Fork: {original_message.content[:50]}"
    )

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
    """Get chat history for a session."""
    repo = ChatRepository(db)

    session = await repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await repo.get_messages(session_id, limit=limit, offset=offset)
    total = await repo.get_message_count(session_id)
    has_more = (offset + len(messages)) < total

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
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": has_more,
        },
    }


@router.post("/regenerate/{message_id}")
async def regenerate_message(
    message_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Regenerate the assistant response for a given message."""
    repo = ChatRepository(db)

    original_message = await repo.get_message(message_id)
    if not original_message:
        raise HTTPException(status_code=404, detail="Message not found")

    if original_message.role != "user":
        raise HTTPException(
            status_code=400, detail="Can only regenerate responses to user messages"
        )

    session_id = original_message.session_id
    chat_session = await repo.get_session(session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Session not found")

    deep_search = (
        original_message.extra_data.get("deep_search", False)
        if original_message.extra_data
        else False
    )

    from app.agents.master import MasterAgent

    master = MasterAgent(session_id=session_id)

    if deep_search:
        result = await master.execute(
            {
                "query": original_message.content,
                "deep_search": True,
                "session_id": session_id,
            }
        )
        response_content = result.get("answer", "")
    else:
        response_content = await master.chat(original_message.content)

    assistant_message = await repo.create_message(
        session_id=session_id,
        role="assistant",
        content=response_content,
        agent_type="master",
        extra_data={"deep_search": deep_search, "regenerated_from": message_id},
    )

    return {
        "message_id": assistant_message.id,
        "session_id": session_id,
        "content": response_content,
        "created_at": assistant_message.created_at.isoformat()
        if assistant_message.created_at
        else None,
    }


@router.get("/sessions/{session_id}/usage")
async def get_session_usage(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get usage statistics for a session including token counts and costs."""
    repo = ChatRepository(db)

    messages = await repo.get_messages(session_id=session_id)

    total_tokens = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost = 0.0
    message_usage = []

    for message in messages:
        extra_data = message.extra_data or {}
        usage = extra_data.get("usage", {})

        if usage:
            tokens = usage.get("tokens", {})
            total_tokens += tokens.get("total", 0)
            total_prompt_tokens += tokens.get("prompt", 0)
            total_completion_tokens += tokens.get("completion", 0)
            total_cost += usage.get("cost", 0.0)

            message_usage.append(
                {
                    "message_id": message.id,
                    "role": message.role,
                    "tokens": tokens,
                    "cost": usage.get("cost", 0.0),
                    "model": usage.get("model", ""),
                    "provider": usage.get("provider", ""),
                }
            )

    return {
        "session_id": session_id,
        "total_tokens": total_tokens,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_cost": round(total_cost, 6),
        "message_count": len(messages),
        "messages_with_usage": len(message_usage),
        "message_usage": message_usage,
    }
