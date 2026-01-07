"""
Main FastAPI application for the Agentic Chatbot.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.config_manager import config_manager
from app.db.session import init_db, initialize_engine, get_database_info, _engine
from app.api.routes import health, sessions, config, chat, tools, websocket, auth
from app.utils.shutdown import (
    get_shutdown_manager,
    create_shutdown_handler,
    save_working_memory_state,
)
from app.utils.rate_limiter import get_rate_limiter, apply_rate_limit_config


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

        # Initialize rate limiting from config
        rate_limiting_config = config.rate_limiting
        rate_limit_dict = {
            "enabled": rate_limiting_config.enabled,
            "endpoints": {
                key: {
                    "requests": value.requests,
                    "window_seconds": value.window_seconds,
                }
                for key, value in rate_limiting_config.endpoints.items()
            },
        }
        apply_rate_limit_config(rate_limit_dict)
        print(f"Rate limiting enabled: {rate_limiting_config.enabled}")
    except Exception as e:
        print(f"Warning: Could not load configuration: {e}")

    yield

    print("Shutting down Agentic Chatbot...")

    # Use the centralized shutdown manager for graceful shutdown
    shutdown_manager = get_shutdown_manager()

    try:
        # Cancel all active session tasks
        from app.utils.session_task_manager import get_session_task_manager

        task_manager = get_session_task_manager()
        active_sessions = task_manager.get_active_session_count()
        if active_sessions > 0:
            print(f"Cancelling {active_sessions} active sessions...")
            result = await task_manager.shutdown_all_sessions(timeout=25.0)
            print(
                f"Session cancellation: {result['cancelled']} cancelled, {result['pending']} pending"
            )
    except Exception as e:
        print(f"Warning: Could not cancel session tasks: {e}")

    try:
        from app.utils.streaming import event_manager

        active_queues = event_manager.get_queue_count()
        if active_queues > 0:
            print(f"Closing {active_queues} active SSE event queues...")
            for session_id in list(event_manager._queues.keys()):
                await event_manager.close(session_id)
                await save_working_memory_state(session_id)
            print("All SSE event queues closed")
    except Exception as e:
        print(f"Warning: Could not close event queues: {e}")

    # Use the shutdown manager's complete shutdown (disposes engine, etc.)
    # This is the final cleanup step
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


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware for all endpoints.

    Applies endpoint-specific rate limits based on the request path.
    """
    rate_limiter = get_rate_limiter()

    if not rate_limiter.is_enabled():
        return await call_next(request)

    # Determine endpoint key based on path
    path = request.url.path
    method = request.method

    endpoint_key = "default"
    is_concurrent = False

    if path == "/api/v1/chat/message" and method == "POST":
        endpoint_key = "chat_message"
    elif "/api/v1/chat/stream/" in path and method == "GET":
        endpoint_key = "chat_stream"
        is_concurrent = True
    # Skip rate limiting for config updates - user settings saves should not be rate limited
    elif path == "/api/v1/config" and method == "POST":
        return await call_next(request)

    # Check rate limit
    is_allowed, response = await rate_limiter.check_rate_limit(
        request,
        endpoint_key=endpoint_key,
        is_concurrent=is_concurrent,
    )

    if not is_allowed:
        return response

    # Process request
    try:
        response = await call_next(request)

        # Add rate limit headers to successful responses
        if response.status_code < 400:
            limiter = get_rate_limiter()
            config = limiter.get_config(endpoint_key)
            response.headers["X-RateLimit-Limit"] = str(config.requests)

        return response
    finally:
        # Release concurrent connection slot if applicable
        if is_concurrent and rate_limiter.is_enabled():
            await rate_limiter.release_concurrent(request, endpoint_key)


# Include routers
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(config.router, prefix="/api/v1/config", tags=["config"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(tools.router, prefix="/api/v1", tags=["tools"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
# WebSocket routes are included directly (not via include_router for proper WebSocket handling)
app.include_router(websocket.router)


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
