"""
Pytest configuration and fixtures for the backend test suite.
"""

import asyncio
import os
import sys
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.main import app
from app.db.models import Base
from app.db.session import get_db


# Test database URL - use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def async_client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with database override."""

    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def override_get_db():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def sync_client():
    """Create synchronous test client."""
    return TestClient(app)


# LLM Mock Fixtures
@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    return {
        "id": "msg_test123",
        "type": "message",
        "role": "assistant",
        "content": [
            {"type": "text", "text": "This is a test response from the mock LLM."}
        ],
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 50,
            "output_tokens": 100,
        },
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "id": "chatcmpl_test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4-turbo",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a test response from the mock LLM.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 100,
            "total_tokens": 150,
        },
    }


@pytest.fixture
def mock_planner_response():
    """Mock response for the planner agent."""
    return {
        "plan": [
            {
                "step_number": 1,
                "agent_type": "researcher",
                "description": "Research the topic",
                "action": "research",
                "parameters": {"query": "test query"},
            },
            {
                "step_number": 2,
                "agent_type": "tools",
                "description": "Analyze results",
                "action": "analyze",
                "parameters": {},
            },
        ],
        "plan_version": 1,
    }


@pytest.fixture
def mock_researcher_response():
    """Mock response for the researcher agent."""
    return {
        "findings": [
            {
                "title": "Test Finding 1",
                "url": "https://example.com/1",
                "summary": "This is a test finding.",
                "relevance_score": 0.9,
            },
            {
                "title": "Test Finding 2",
                "url": "https://example.com/2",
                "summary": "This is another test finding.",
                "relevance_score": 0.8,
            },
        ],
        "sources": [
            {
                "url": "https://example.com/1",
                "content": "Full content of the page...",
                "title": "Test Finding 1",
            }
        ],
    }


@pytest.fixture
def mock_tools_response():
    """Mock response for the tools agent."""
    return {
        "results": [
            {
                "tool": "calculator",
                "success": True,
                "output": "42",
            }
        ],
        "charts": [],
    }


@pytest.fixture
def mock_database_response():
    """Mock response for the database agent."""
    return {
        "results": [
            {"column1": "value1", "column2": 100},
            {"column1": "value2", "column2": 200},
        ],
        "row_count": 2,
        "columns": ["column1", "column2"],
    }


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    mock = MagicMock()
    mock.complete = AsyncMock(return_value="This is a test response.")
    mock.stream_complete = MagicMock(return_value=AsyncMock())
    return mock


@pytest_asyncio.fixture
async def sample_session(test_session):
    """Create a sample chat session in the database."""
    from app.db.models import ChatSession

    session_obj = ChatSession(id="test-session-123", title="Test Session")
    test_session.add(session_obj)
    await test_session.commit()
    await test_session.refresh(session_obj)

    yield session_obj


@pytest_asyncio.fixture
async def sample_message(test_session, sample_session):
    """Create a sample message in the database."""
    from app.db.models import Message

    message = Message(
        id="test-message-123",
        session_id=sample_session.id,
        role="user",
        content="Hello, this is a test message.",
    )
    test_session.add(message)
    await test_session.commit()
    await test_session.refresh(message)

    yield message


@pytest_asyncio.fixture
async def sample_working_memory(test_session, sample_session):
    """Create sample working memory in the database."""
    from app.db.models import WorkingMemory

    memory = WorkingMemory(
        id="test-memory-123",
        session_id=sample_session.id,
        memory_tree={"root": {"agent": "master", "children": []}},
        timeline=[{"id": "step-1", "agent": "planner"}],
        index_map={"step-1": {"status": "completed"}},
    )
    test_session.add(memory)
    await test_session.commit()
    await test_session.refresh(memory)

    yield memory


# Configuration fixtures
@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return {
        "version": "1.0",
        "general": {
            "timezone": "UTC",
            "theme": "light",
            "example_questions": [
                "What are the latest AI breakthroughs?",
                "Analyze my sales data for Q4",
            ],
        },
        "database": {
            "type": "sqlite",
            "sqlite_path": "./data/chatbot.db",
        },
        "agents": {
            "master": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 4096,
            },
            "planner": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 2048,
            },
        },
    }


# SSE event fixtures
@pytest.fixture
def sample_sse_events():
    """Sample SSE events for testing."""
    return [
        {"event": "thought", "data": {"agent": "planner", "content": "Planning..."}},
        {"event": "step_update", "data": {"step_id": "1", "status": "running"}},
        {"event": "message_chunk", "data": {"content": "Hello"}},
        {"event": "complete", "data": {"message_id": "msg-123"}},
    ]


# Error fixtures
@pytest.fixture
def sample_agent_error():
    """Sample agent error for testing."""
    from app.agents.error_handler import AgentError, ErrorType

    return AgentError(
        error_type=ErrorType.API_TIMEOUT,
        message="Request timed out after 30 seconds",
        retry_count=0,
        max_retries=3,
    )


# Async helpers
@pytest_asyncio.fixture
async def run_async_test():
    """Helper to run async test code."""

    async def _run(test_coroutine):
        return await test_coroutine

    return _run
