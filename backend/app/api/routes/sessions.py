"""
Session management endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.repositories.chat import ChatRepository
from pydantic import BaseModel


router = APIRouter()


class SessionCreateRequest(BaseModel):
    title: Optional[str] = None


class SessionUpdateRequest(BaseModel):
    title: Optional[str] = None


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
        "total": len(sessions),
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


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    limit: int = 30,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific session with its messages.
    """
    repo = ChatRepository(db)
    session = await repo.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await repo.get_messages(session_id, limit=limit, offset=offset)

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

    if request.title:
        session = await repo.update_session_title(session_id, request.title)

    return {
        "id": session.id,
        "title": session.title,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


@router.delete("/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete (archive) a session.
    """
    repo = ChatRepository(db)
    success = await repo.delete_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "archived", "session_id": session_id}


@router.get("/search")
async def search_sessions(q: str, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """
    Search sessions and messages.
    """
    repo = ChatRepository(db)
    results = await repo.search_messages(q, limit=limit)

    return {
        "query": q,
        "results": [
            {
                "session_id": session.id,
                "session_title": session.title,
                "message_content": message.content[:200],  # Truncate
                "created_at": message.created_at.isoformat()
                if message.created_at
                else None,
            }
            for message, session in results
        ],
    }
