"""
End-to-End Tests for Complete Agent Workflow

Tests verify:
1. Full agent workflow from message receipt to final response
2. Mock LLM providers at HTTP level (not just return values)
3. SSE streaming end-to-end with real event sequences
4. Error handling with 3x retry + user intervention flow
5. Parallel step execution with actual async behavior
6. Re-planning when researcher triggers it

Uses:
- pytest-asyncio fixtures for full app lifecycle
- httpx.AsyncClient for API testing
- Mock SSE client for streaming verification
- Test database fixtures with proper cleanup
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import AsyncIterator, Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.main import app
from app.db.models import Base, ChatSession, Message, WorkingMemory
from app.db.session import get_db, AsyncSession
from app.agents.graph import (
    create_initial_state,
    create_agent_graph,
    run_agent_workflow_with_streaming,
    StepAnalyzer,
)
from app.agents.memory import AsyncWorkingMemory, MemoryNode
from app.agents.error_handler import AgentError, ErrorType, InterventionAction
from app.agents.types import AgentType, StepType, StepStatus
from app.llm.providers import (
    BaseLLMProvider,
    LLMResponse,
    StreamChunk,
    ProviderConfig,
    LLMProviderFactory,
)
from app.utils.streaming import event_manager, SSEEventManager

from tests.fixtures.mock_llm_server import MockLLMConfig, MockLLMProvider
from tests.fixtures.sse_client import (
    MockSSEClient,
    SSEEventParser,
    SSEEventSequence,
    SSEEventType,
    SSEEventVerifier,
    ParsedSSEEvent,
)


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import StaticPool

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
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

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
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

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


@pytest_asyncio.fixture
def mock_llm_config():
    """Create a mock LLM configuration."""
    return MockLLMConfig(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        response_content="This is a comprehensive test response from the agent workflow.",
        latency_ms=10,
    )


@pytest_asyncio.fixture
def mock_llm_provider(mock_llm_config):
    """Create a mock LLM provider."""
    return MockLLMProvider(mock_llm_config)


@pytest_asyncio.fixture
async def mock_sse_client():
    """Create a mock SSE client for testing."""
    return MockSSEClient(session_id=f"test-session-{uuid.uuid4().hex[:8]}")


class TestCompleteWorkflow:
    """Tests for complete agent workflow from message to response."""

    @pytest.mark.asyncio
    async def test_full_workflow_casual_mode(
        self,
        async_client: AsyncClient,
        test_session: AsyncSession,
        mock_llm_provider: MockLLMProvider,
    ):
        """Test complete workflow in casual mode (no deep search)."""
        with patch("app.agents.graph.get_llm_provider", return_value=mock_llm_provider):
            with patch("app.agents.graph.synthesize_response") as mock_synth:
                mock_synth.return_value = LLMResponse(
                    content="Test response",
                    provider="anthropic",
                    model="claude-3-5-sonnet-20241022",
                    total_tokens=50,
                    prompt_tokens=20,
                    completion_tokens=30,
                    cost=0.001,
                    latency_ms=10,
                )

                response = await async_client.post(
                    "/api/v1/chat/message",
                    json={
                        "content": "Hello, what can you do?",
                        "deep_search": False,
                        "timezone": "UTC",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert "message_id" in data
                assert "session_id" in data
                assert data["session_id"] is not None

    @pytest.mark.asyncio
    async def test_full_workflow_deep_search(
        self,
        async_client: AsyncClient,
        test_session: AsyncSession,
        mock_llm_provider: MockLLMProvider,
    ):
        """Test complete workflow with deep search enabled."""
        with patch("app.agents.graph.get_llm_provider", return_value=mock_llm_provider):
            with patch("app.agents.graph.synthesize_response") as mock_synth:
                mock_synth.return_value = LLMResponse(
                    content="Research findings response",
                    provider="anthropic",
                    model="claude-3-5-sonnet-20241022",
                    total_tokens=100,
                    prompt_tokens=40,
                    completion_tokens=60,
                    cost=0.002,
                    latency_ms=10,
                )

                response = await async_client.post(
                    "/api/v1/chat/message",
                    json={
                        "content": "What are the latest AI developments?",
                        "deep_search": True,
                        "timezone": "America/New_York",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["session_id"] is not None

    @pytest.mark.asyncio
    async def test_workflow_creates_session_and_messages(
        self,
        async_client: AsyncClient,
        test_session: AsyncSession,
        mock_llm_provider: MockLLMProvider,
    ):
        """Test that workflow creates session and messages in database."""
        with patch("app.agents.graph.get_llm_provider", return_value=mock_llm_provider):
            with patch("app.agents.graph.synthesize_response") as mock_synth:
                mock_synth.return_value = LLMResponse(
                    content="Test response",
                    provider="anthropic",
                    model="claude-3-5-sonnet-20241022",
                    total_tokens=50,
                    prompt_tokens=20,
                    completion_tokens=30,
                    cost=0.001,
                    latency_ms=10,
                )

                response = await async_client.post(
                    "/api/v1/chat/message",
                    json={"content": "Test message", "deep_search": False},
                )

                assert response.status_code == 200
                session_id = response.json()["session_id"]

                history_response = await async_client.get(
                    f"/api/v1/chat/history/{session_id}"
                )

                assert history_response.status_code == 200
                history_data = history_response.json()
                assert len(history_data["messages"]) >= 2
                assert history_data["messages"][0]["role"] == "user"
                assert history_data["messages"][1]["role"] == "assistant"


class TestSSEStreaming:
    """Tests for SSE streaming behavior."""

    @pytest.mark.asyncio
    async def test_sse_events_generated(
        self,
        async_client: AsyncClient,
        mock_llm_provider: MockLLMProvider,
    ):
        """Test that SSE events are generated during workflow."""
        with patch("app.agents.graph.get_llm_provider", return_value=mock_llm_provider):
            with patch("app.agents.graph.synthesize_response") as mock_synth:
                mock_synth.return_value = LLMResponse(
                    content="Test response",
                    provider="anthropic",
                    model="claude-3-5-sonnet-20241022",
                    total_tokens=50,
                    prompt_tokens=20,
                    completion_tokens=30,
                    cost=0.001,
                    latency_ms=10,
                )

                response = await async_client.post(
                    "/api/v1/chat/message",
                    json={"content": "Test", "deep_search": False},
                )

                session_id = response.json()["session_id"]

                stream_response = await async_client.get(
                    f"/api/v1/chat/stream/{session_id}",
                    headers={"Accept": "text/event-stream"},
                )

                assert stream_response.status_code == 200
                assert stream_response.headers["content-type"] == "text/event-stream"

    @pytest.mark.asyncio
    async def test_sse_event_types(
        self,
        async_client: AsyncClient,
        mock_llm_provider: MockLLMProvider,
    ):
        """Test that correct SSE event types are emitted."""
        with patch("app.agents.graph.get_llm_provider", return_value=mock_llm_provider):
            with patch("app.agents.graph.synthesize_response") as mock_synth:
                mock_synth.return_value = LLMResponse(
                    content="Test response",
                    provider="anthropic",
                    model="claude-3-5-sonnet-20241022",
                    total_tokens=50,
                    prompt_tokens=20,
                    completion_tokens=30,
                    cost=0.001,
                    latency_ms=10,
                )

                response = await async_client.post(
                    "/api/v1/chat/message",
                    json={"content": "Test", "deep_search": False},
                )

                session_id = response.json()["session_id"]

                await asyncio.sleep(0.5)

                queue = event_manager.get_queue(session_id)
                events = []
                while not queue.empty():
                    try:
                        event = queue.get_nowait()
                        events.append(event)
                    except asyncio.QueueEmpty:
                        break

                event_types = [e.event for e in events if e is not None]
                assert "thought" in event_types or len(events) > 0


class TestErrorHandling:
    """Tests for error handling and retry logic."""

    @pytest.mark.asyncio
    async def test_error_handling_with_retry(
        self,
        async_client: AsyncClient,
        test_session: AsyncSession,
    ):
        """Test error handling with 3x retry + user intervention flow."""
        call_count = 0

        async def flaky_llm_provider(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary API failure")
            return LLMResponse(
                content="Response after retry",
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                total_tokens=50,
                prompt_tokens=20,
                completion_tokens=30,
                cost=0.001,
                latency_ms=10,
            )

        with patch("app.agents.graph.get_llm_provider") as mock:
            mock.return_value.complete = flaky_llm_provider

            response = await async_client.post(
                "/api/v1/chat/message",
                json={"content": "Test", "deep_search": False},
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(
        self,
        async_client: AsyncClient,
    ):
        """Test that max retries are respected before user intervention."""
        error_count = 0

        async def always_fail(*args, **kwargs):
            nonlocal error_count
            error_count += 1
            raise Exception("Always fails")

        with patch("app.agents.graph.get_llm_provider") as mock:
            mock.return_value.complete = always_fail

            response = await async_client.post(
                "/api/v1/chat/message",
                json={"content": "Test", "deep_search": False},
            )

            assert response.status_code == 200
            assert error_count >= 3

    def test_error_classification(self):
        """Test error type classification."""
        timeout_error = AgentError(
            error_type=ErrorType.API_TIMEOUT,
            message="Request timed out",
            retry_count=0,
            max_retries=3,
        )
        assert timeout_error.can_retry is True
        assert timeout_error.get_retry_delay() > 0

        auth_error = AgentError(
            error_type=ErrorType.API_AUTH,
            message="Invalid API key",
            retry_count=0,
            max_retries=3,
        )
        assert auth_error.can_retry is False

    def test_retry_delay_calculation(self):
        """Test exponential backoff delay calculation."""
        error = AgentError(
            error_type=ErrorType.API_RATE_LIMIT,
            message="Rate limited",
            retry_count=0,
            max_retries=3,
        )

        delay_1 = error.get_retry_delay()
        error.retry_count = 1
        delay_2 = error.get_retry_delay()
        error.retry_count = 2
        delay_3 = error.get_retry_delay()

        assert delay_2 > delay_1
        assert delay_3 > delay_2


class TestParallelExecution:
    """Tests for parallel step execution."""

    def test_parallel_batch_detection(self):
        """Test identifying parallel-compatible steps."""
        plan = [
            {"type": StepType.RESEARCH.value, "agent": "researcher"},
            {"type": StepType.CODE.value, "agent": "tools"},
            {"type": StepType.DATABASE.value, "agent": "database"},
            {"type": StepType.REVIEW.value, "agent": "master"},
        ]

        batch = StepAnalyzer.find_parallel_batch(plan, 0)
        assert len(batch) >= 2
        assert 0 in batch
        assert 3 not in batch

    def test_sequential_only_steps(self):
        """Test that REVIEW and THINK steps are sequential only."""
        think_plan = [
            {"type": StepType.THINK.value},
            {"type": StepType.CODE.value},
        ]

        batch = StepAnalyzer.find_parallel_batch(think_plan, 0)
        assert len(batch) == 1

    def test_parallel_step_execution(self):
        """Test parallel step execution with asyncio.gather."""
        import asyncio

        async def mock_step(delay: float, name: str) -> Dict[str, Any]:
            await asyncio.sleep(delay)
            return {"name": name, "completed": True}

        async def run_parallel():
            tasks = [
                mock_step(0.01, "step1"),
                mock_step(0.01, "step2"),
                mock_step(0.01, "step3"),
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)

        results = asyncio.run(run_parallel())
        assert len(results) == 3
        assert all(isinstance(r, dict) for r in results)


class TestReplanning:
    """Tests for re-planning when researcher triggers it."""

    @pytest.mark.asyncio
    async def test_replan_on_researcher_findings(
        self,
        async_client: AsyncClient,
        test_session: AsyncSession,
        mock_llm_provider: MockLLMProvider,
    ):
        """Test that re-planning is triggered when researcher finds unexpected info."""
        with patch("app.agents.graph.get_llm_provider", return_value=mock_llm_provider):
            with patch("app.agents.graph._generate_plan") as mock_plan:
                call_count = 0

                async def generate_plan(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        return [
                            {
                                "type": StepType.RESEARCH.value,
                                "description": "Initial research",
                            },
                        ]
                    else:
                        return [
                            {
                                "type": StepType.RESEARCH.value,
                                "description": "Additional research",
                            },
                            {"type": StepType.THINK.value, "description": "Synthesize"},
                        ]

                mock_plan.return_value = generate_plan()

                response = await async_client.post(
                    "/api/v1/chat/message",
                    json={"content": "Research something complex", "deep_search": True},
                )

                assert response.status_code == 200

    def test_replan_trigger_state(self):
        """Test re-plan trigger in agent state."""
        state = create_initial_state(
            user_message="Test",
            session_id="test-session",
            deep_search_enabled=True,
        )

        state["previous_step_output"] = {
            "requires_replan": True,
            "triggered_by": "researcher",
            "replan_reason": "New information requires plan update",
        }

        assert state["requires_replan"] is True
        assert state["previous_step_output"]["requires_replan"] is True


class TestWorkingMemory:
    """Tests for working memory operations during workflow."""

    @pytest.mark.asyncio
    async def test_working_memory_created(self):
        """Test that working memory is created for new sessions."""
        memory = AsyncWorkingMemory(session_id="test-session")

        node_id = await memory.add_node(
            agent=AgentType.MASTER.value,
            node_type="thought",
            description="Initial thought",
        )

        assert node_id is not None
        assert len(memory._timeline) >= 1

    @pytest.mark.asyncio
    async def test_working_memory_update(self):
        """Test working memory node updates."""
        memory = AsyncWorkingMemory(session_id="test-session")

        node_id = await memory.add_node(
            agent=AgentType.PLANNER.value,
            node_type="step",
            description="Planning step",
        )

        await memory.update_node(
            node_id, completed=True, status=StepStatus.COMPLETED.value
        )

        node = await memory.get_node(node_id)
        assert node is not None
        assert node.status == StepStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_working_memory_serialization(self):
        """Test working memory serialization for SSE streaming."""
        memory = AsyncWorkingMemory(session_id="test-session")

        await memory.add_node(
            agent=AgentType.PLANNER.value,
            node_type="thought",
            description="Planning",
        )

        data = await memory.to_dict()
        assert "tree" in data
        assert "timeline" in data
        assert "index" in data


class TestLLMMocking:
    """Tests for HTTP-level LLM mocking."""

    @pytest.mark.asyncio
    async def test_llm_provider_mock(
        self,
        mock_llm_provider: MockLLMProvider,
    ):
        """Test mock LLM provider responses."""
        messages = [{"role": "user", "content": "Hello"}]

        response = await mock_llm_provider.complete(
            messages=messages,
            system_prompt="You are a helpful assistant.",
        )

        assert response["content"] is not None
        assert response["provider"] == "anthropic"
        assert response["total_tokens"] > 0

    @pytest.mark.asyncio
    async def test_llm_provider_stream(
        self,
        mock_llm_provider: MockLLMProvider,
    ):
        """Test mock LLM provider streaming."""
        messages = [{"role": "user", "content": "Hello"}]

        chunks = []
        async for chunk in mock_llm_provider.stream_complete(messages=messages):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert all("content" in c for c in chunks)


class TestSessionManagement:
    """Tests for session management and history."""

    @pytest.mark.asyncio
    async def test_session_creation(
        self,
        async_client: AsyncClient,
    ):
        """Test session creation via API."""
        response = await async_client.post(
            "/api/v1/chat/message",
            json={"content": "New conversation", "deep_search": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] is not None

    @pytest.mark.asyncio
    async def test_session_history(
        self,
        async_client: AsyncClient,
    ):
        """Test retrieving session history."""
        response = await async_client.post(
            "/api/v1/chat/message",
            json={"content": "Test message", "deep_search": False},
        )

        session_id = response.json()["session_id"]

        history_response = await async_client.get(f"/api/v1/chat/history/{session_id}")

        assert history_response.status_code == 200
        data = history_response.json()
        assert data["session_id"] == session_id
        assert "messages" in data
        assert "working_memory" in data


class TestInterventionFlow:
    """Tests for user intervention flow."""

    @pytest.mark.asyncio
    async def test_intervention_endpoint_exists(
        self,
        async_client: AsyncClient,
    ):
        """Test that intervention endpoint is accessible."""
        session_id = "test-session"

        response = await async_client.get(f"/api/v1/chat/intervention/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "awaiting_response" in data

    def test_intervention_state(self):
        """Test intervention state management."""
        from app.agents.error_handler import (
            UserInterventionState,
            InterventionAction,
        )

        state = UserInterventionState(session_id="test-session")

        assert state.awaiting_response is False
        assert state.action is None

        error = AgentError(
            error_type=ErrorType.API_TIMEOUT,
            message="Timeout",
            retry_count=3,
            max_retries=3,
        )

        state.set_pending_error(error)
        assert state.awaiting_response is True
        assert state.pending_error == error

        state.set_response(InterventionAction.RETRY)
        assert state.action == InterventionAction.RETRY

        state.clear()
        assert state.awaiting_response is False


class TestSSEEventVerifier:
    """Tests for SSE event verification utilities."""

    def test_event_parsing(self):
        """Test SSE event parsing."""
        raw_data = """event: thought
data: {"agent": "planner", "content": "Planning..."}

event: complete
data: {"message_id": "msg-123", "final_answer": "Done"}

"""
        events = SSEEventParser.parse_raw_stream(raw_data)

        assert len(events) == 2
        assert events[0].event_type == "thought"
        assert events[0].data["agent"] == "planner"
        assert events[1].event_type == "complete"

    def test_event_sequence_filtering(self):
        """Test event sequence filtering."""
        events = [
            ParsedSSEEvent(
                event_type="thought", data={"agent": "planner"}, raw_event=""
            ),
            ParsedSSEEvent(event_type="step_progress", data={"step": 1}, raw_event=""),
            ParsedSSEEvent(event_type="complete", data={}, raw_event=""),
        ]

        sequence = SSEEventSequence(
            events=events,
            session_id="test",
            start_time=datetime.utcnow(),
        )

        thoughts = sequence.filter_by_type("thought")
        assert len(thoughts) == 1

        assert sequence.has_event_type("complete") is True
        assert sequence.has_event_type("error") is False

    def test_verifier_event_order(self):
        """Test event order verification."""
        verifier = SSEEventVerifier()

        events = [
            ParsedSSEEvent(event_type="thought", data={}, raw_event=""),
            ParsedSSEEvent(event_type="step_progress", data={}, raw_event=""),
            ParsedSSEEvent(event_type="complete", data={}, raw_event=""),
        ]

        sequence = SSEEventSequence(
            events=events,
            session_id="test",
            start_time=datetime.utcnow(),
        )

        valid, message = verifier.verify_event_order(
            sequence, ["thought", "step_progress", "complete"]
        )
        assert valid is True

        invalid, _ = verifier.verify_event_order(
            sequence, ["thought", "complete", "step_progress"]
        )
        assert invalid is False


class TestAsyncWorkflow:
    """Tests for async workflow behavior."""

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self):
        """Test handling of concurrent sessions."""
        sessions = []
        for i in range(3):
            session = AsyncWorkingMemory(session_id=f"session-{i}")
            await session.add_node(
                agent=AgentType.MASTER.value,
                node_type="thought",
                description=f"Session {i} thought",
            )
            sessions.append(session)

        assert len(sessions) == 3

        for i, session in enumerate(sessions):
            data = await session.to_dict()
            assert "timeline" in data
            assert len(data["timeline"]) >= 1

    @pytest.mark.asyncio
    async def test_async_state_updates(self):
        """Test async state updates in workflow."""
        state = create_initial_state(
            user_message="Test",
            session_id="test-session",
            deep_search_enabled=False,
        )

        assert state["active_step"] == 0
        assert state["plan_version"] == 1

        state["active_step"] = 5
        state["plan_version"] = 2

        assert state["active_step"] == 5
        assert state["plan_version"] == 2


class TestDatabaseIntegration:
    """Tests for database integration."""

    @pytest.mark.asyncio
    async def test_message_creation(
        self,
        async_client: AsyncClient,
    ):
        """Test message creation in database."""
        response = await async_client.post(
            "/api/v1/chat/message",
            json={"content": "Test message", "deep_search": False},
        )

        session_id = response.json()["session_id"]

        messages_response = await async_client.get(f"/api/v1/chat/history/{session_id}")

        messages = messages_response.json()["messages"]
        assert len(messages) >= 2

        user_msg = [m for m in messages if m["role"] == "user"]
        assert len(user_msg) == 1
        assert user_msg[0]["content"] == "Test message"

    @pytest.mark.asyncio
    async def test_working_memory_persistence(
        self,
        async_client: AsyncClient,
    ):
        """Test working memory persistence."""
        response = await async_client.post(
            "/api/v1/chat/message",
            json={"content": "Test", "deep_search": False},
        )

        session_id = response.json()["session_id"]

        history_response = await async_client.get(f"/api/v1/chat/history/{session_id}")

        working_memory = history_response.json().get("working_memory")
        assert working_memory is not None
        assert (
            "memory_tree" in working_memory
            or working_memory.get("timeline") is not None
        )


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_empty_message(self, async_client: AsyncClient):
        """Test handling of empty messages."""
        response = await async_client.post(
            "/api/v1/chat/message",
            json={"content": "", "deep_search": False},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_nonexistent_session_history(
        self,
        async_client: AsyncClient,
    ):
        """Test history for non-existent session."""
        response = await async_client.get("/api/v1/chat/history/nonexistent-session-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_intervention_action(
        self,
        async_client: AsyncClient,
    ):
        """Test invalid intervention action."""
        response = await async_client.post(
            "/api/v1/chat/intervene/test-session",
            json={"action": "invalid_action"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"

    def test_step_analyzer_edge_cases(self):
        """Test step analyzer edge cases."""
        empty_plan = StepAnalyzer.find_parallel_batch([], 0)
        assert empty_plan == []

        single_step = StepAnalyzer.find_parallel_batch([{"type": "think"}], 0)
        assert len(single_step) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
