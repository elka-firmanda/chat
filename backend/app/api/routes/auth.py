"""
Chat authentication endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix="/auth", tags=["auth"])


class AuthStatusResponse(BaseModel):
    """Response model for auth status check."""

    auth_required: bool


@router.get("/chat/status")
async def check_chat_auth_status() -> AuthStatusResponse:
    """
    Check if chat authentication is required.

    Currently returns auth_required: false as authentication is not implemented.
    """
    return AuthStatusResponse(auth_required=False)


@router.post("/chat/login")
async def chat_login(password: str):
    """
    Login to chat (placeholder - not yet implemented).
    """
    raise HTTPException(
        status_code=501, detail="Chat authentication not yet implemented"
    )


@router.post("/chat/logout")
async def chat_logout():
    """
    Logout from chat (placeholder - not yet implemented).
    """
    return {"message": "Logged out"}
