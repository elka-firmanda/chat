"""
Session management endpoints.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.repositories.chat import ChatRepository
from app.tools.pdf_exporter import export_session_to_pdf
from pydantic import BaseModel


router = APIRouter()


class SessionCreateRequest(BaseModel):
    title: Optional[str] = None


class SessionUpdateRequest(BaseModel):
    title: Optional[str] = None
    archived: Optional[bool] = None


@router.get("")
async def list_sessions(
    archived: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    List all chat sessions with pagination.
    """
    repo = ChatRepository(db)
    sessions = await repo.get_sessions(archived=archived, limit=limit, offset=offset)
    total = await repo.get_sessions_count(archived=archived)

    return {
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                "archived": s.archived,
            }
            for s in sessions
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("")
async def create_session(
    request: SessionCreateRequest = None, db: AsyncSession = Depends(get_db)
):
    """
    Create a new chat session.
    """
    repo = ChatRepository(db)
    title = request.title if request else None
    session = await repo.create_session(title=title)

    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


@router.get("/search")
async def search_sessions(
    q: str,
    limit: int = 20,
    search_type: str = "all",  # 'all', 'sessions', 'messages'
    db: AsyncSession = Depends(get_db),
):
    """
    Search sessions and messages with full-text search.

    - q: Search query string
    - limit: Maximum number of results (default 20, max 100)
    - search_type: Search type - 'all' (default), 'sessions' (title only), 'messages' (content only)

    Returns matching sessions with highlighted snippets for fast, relevant results.
    Performance target: <100ms for typical queries.
    """
    import time

    start_time = time.time()

    # Validate and sanitize query
    if not q or len(q.strip()) < 2:
        return {
            "query": q,
            "results": [],
            "total": 0,
            "time_ms": round((time.time() - start_time) * 1000, 2),
            "message": "Query must be at least 2 characters",
        }

    query = q.strip()
    limit = min(limit, 100)  # Cap at 100 for performance

    repo = ChatRepository(db)

    # Search based on type
    if search_type == "sessions":
        # Search session titles only (faster)
        sessions = await repo.search_sessions_by_title(query, limit=limit)
        results = [
            {
                "session_id": s.id,
                "session_title": s.title,
                "message_content": None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "highlighted_content": None,
                "type": "session",
            }
            for s in sessions
        ]
    else:
        # Search messages with FTS5 (default)
        raw_results = await repo.search_messages(query, limit=limit)

        # Transform results with highlighting
        seen_sessions = set()
        results = []
        for message, session, highlighted in raw_results:
            # Deduplicate by session (show first match per session)
            if session.id in seen_sessions:
                continue
            seen_sessions.add(session.id)

            results.append(
                {
                    "session_id": session.id,
                    "session_title": session.title,
                    "message_content": message.content[:200],
                    "created_at": message.created_at.isoformat()
                    if message.created_at
                    else None,
                    "highlighted_content": highlighted,
                    "message_id": message.id,
                    "role": message.role,
                    "agent_type": message.agent_type,
                    "type": "message",
                }
            )

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "query": query,
        "results": results,
        "total": len(results),
        "time_ms": elapsed_ms,
        "search_type": search_type,
    }


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    limit: int = 30,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    repo = ChatRepository(db)
    session = await repo.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await repo.get_messages(session_id, limit=limit, offset=offset)
    total = await repo.get_message_count(session_id)
    has_more = (offset + len(messages)) < total

    return {
        "session": {
            "id": session.id,
            "title": session.title,
            "created_at": session.created_at.isoformat()
            if session.created_at
            else None,
            "updated_at": session.updated_at.isoformat()
            if session.updated_at
            else None,
            "archived": session.archived,
        },
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "agent_type": m.agent_type,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "metadata": m.metadata,
            }
            for m in messages
        ],
        "total": total,
        "has_more": has_more,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/{session_id}")
async def update_session(
    session_id: str, request: SessionUpdateRequest, db: AsyncSession = Depends(get_db)
):
    """
    Update a session (title or archive status).
    """
    repo = ChatRepository(db)
    session = await repo.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if request.title is not None:
        session = await repo.update_session_title(session_id, request.title)

    if request.archived is not None:
        session = await repo.update_session_archive_status(session_id, request.archived)

    return {
        "id": session.id,
        "title": session.title,
        "archived": session.archived,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    permanent: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a session.

    - Default: Soft delete (archive) the session
    - permanent=true: Permanently delete all data (messages, working memory, agent steps)
    """
    repo = ChatRepository(db)

    if permanent:
        success = await repo.hard_delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return Response(status_code=204)
    else:
        success = await repo.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "archived", "session_id": session_id}


@router.get("/{session_id}/export")
async def export_session(
    session_id: str,
    format: str = "pdf",
    db: AsyncSession = Depends(get_db),
):
    """
    Export a session to PDF format.
    Returns the PDF file as a downloadable response.
    """
    repo = ChatRepository(db)
    session = await repo.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get all messages for the session
    messages = await repo.get_messages(session_id, limit=1000, offset=0)

    # Prepare session data
    session_data = {
        "id": session.id,
        "title": session.title or "Untitled Session",
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "agent_type": m.agent_type,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "metadata": m.extra_data,
            }
            for m in messages
        ],
    }

    # Generate PDF
    filename, pdf_bytes = export_session_to_pdf(session_data)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
