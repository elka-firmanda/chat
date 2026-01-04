"""
Health check endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.config.config_manager import get_config


router = APIRouter()


@router.get("")
async def health_check():
    """
    Basic health check endpoint.
    """
    return {"status": "healthy", "service": "agentic-chatbot"}


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check - verifies database connection.
    """
    try:
        # Try to execute a simple query
        from sqlalchemy import text

        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ready" if db_status == "connected" else "not_ready",
        "database": db_status,
    }


@router.get("/live")
async def liveness_check():
    """
    Liveness check - verifies the service is running.
    """
    return {"status": "alive", "service": "agentic-chatbot"}


@router.get("/config")
async def config_status():
    """
    Get current configuration status.
    """
    try:
        config = get_config()
        return {
            "version": config.version,
            "database_type": config.database.type,
            "agents_loaded": True,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
