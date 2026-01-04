"""
Main FastAPI application for the Agentic Chatbot.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.config_manager import config_manager
from app.db.session import init_db, initialize_engine, get_database_info, _engine
from app.api.routes import health, sessions, config, chat, tools
from app.utils.shutdown import (
    get_shutdown_manager,
    create_shutdown_handler,
    save_working_memory_state,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    """
    print("Starting Agentic Chatbot...")

    await create_shutdown_handler(app)

    initialize_engine()
    print(f"Database engine initialized: {get_database_info()}")

    await init_db()
    print("Database tables initialized")

    try:
        config = config_manager.load()
        print(f"Configuration loaded: {config.version}")
    except Exception as e:
        print(f"Warning: Could not load configuration: {e}")

    yield

    print("Shutting down Agentic Chatbot...")

    shutdown_manager = get_shutdown_manager()

    active_queues = 0
    try:
        from app.utils.streaming import event_manager

        active_queues = event_manager.get_queue_count()
        if active_queues > 0:
            print(f"Closing {active_queues} active SSE event queues...")
            for session_id in list(event_manager._queues.keys()):
                await save_working_memory_state(session_id)
    except Exception as e:
        print(f"Warning: Could not close event queues: {e}")

    if _engine is not None:
        print("Disposing database engine...")
        try:
            await _engine.dispose()
            print("Database engine disposed")
        except Exception as e:
            print(f"Warning: Error disposing database engine: {e}")

    print("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Agentic Chatbot API",
    description="Multi-agent chatbot system with deep research capabilities",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(config.router, prefix="/api/v1/config", tags=["config"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(tools.router, prefix="/api/v1", tags=["tools"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Agentic Chatbot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc) if app.debug else "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
