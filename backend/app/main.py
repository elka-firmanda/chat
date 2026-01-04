"""
Main FastAPI application for the Agentic Chatbot.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.config_manager import config_manager
from app.db.session import init_db, initialize_engine, get_database_info
from app.api.routes import health, sessions, config, chat, tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    """
    print("Starting Agentic Chatbot...")

    # Initialize database engine
    initialize_engine()
    print(f"Database engine initialized: {get_database_info()}")

    # Initialize database tables
    await init_db()
    print("Database tables initialized")

    # Load configuration
    try:
        config = config_manager.load()
        print(f"Configuration loaded: {config.version}")
    except Exception as e:
        print(f"Warning: Could not load configuration: {e}")

    yield

    # Shutdown
    print("Shutting down Agentic Chatbot...")


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
