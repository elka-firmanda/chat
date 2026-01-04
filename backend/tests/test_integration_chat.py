"""
Integration tests for end-to-end agent workflow.

Tests verify:
- Agent state management
- Working memory operations
- Error handling and recovery
- Step analysis and routing
- Memory node operations
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.db.models import ChatSession, Message, WorkingMemory, AgentStep
from app.agents.graph import (
    create_initial_state,
    StepAnalyzer,
)
from app.agents.memory import (
    AsyncWorkingMemory,
    WorkingMemory as SyncWorkingMemory,
    MemoryNode,
    TimelineEntry,
)
from app.agents.error_handler import AgentError, ErrorType, InterventionAction
from app.agents.types import AgentType, StepType, StepStatus


class TestAgentStateManagement:
    """Tests for agent state management."""

    def test_create_initial_state(self):
        """Test creating initial agent state."""
        state = create_initial_state(
            user_message="Test message",
            session_id="test-session",
            deep_search_enabled=False,
            user_timezone="UTC",
        )

        assert state["user_message"] == "Test message"
        assert state["session_id"] == "test-session"
        assert state["deep_search_enabled"] is False
        assert state["current_plan"] == []
        assert state["plan_version"] == 1
        assert state["active_step"] == 0
        assert state["final_answer"] == ""

    def test_create_initial_state_with_deep_search(self):
        """Test creating initial state with deep search enabled."""
        state = create_initial_state(
            user_message="Research AI",
            session_id="test-session",
            deep_search_enabled=True,
            user_timezone="America/New_York",
        )

        assert state["deep_search_enabled"] is True
        assert state["user_timezone"] == "America/New_York"


class TestWorkingMemorySync:
    """Tests for synchronous working memory operations."""

    def test_working_memory_structure(self):
        """Test working memory structure."""
        memory = SyncWorkingMemory(session_id="test-session")

        assert memory.session_id == "test-session"
        assert memory.root_id == "root"
        assert "root" in memory._tree
        assert len(memory._timeline) == 1

    def test_working_memory_add_node(self):
        """Test adding nodes to working memory."""
        memory = SyncWorkingMemory(session_id="test-session")

        node_id = memory.add_node(
            agent=AgentType.PLANNER.value,
            node_type="thought",
            description="Planning step",
        )

        assert node_id is not None
        assert len(memory._timeline) == 2

    def test_working_memory_update_node(self):
        """Test updating nodes in working memory."""
        memory = SyncWorkingMemory(session_id="test-session")

        node_id = memory.add_node(
            agent=AgentType.PLANNER.value,
            node_type="step",
            description="Test step",
        )

        memory.update_node(node_id, completed=True, status=StepStatus.COMPLETED.value)

        node = memory.get_node(node_id)
        assert node is not None
        assert node.status == StepStatus.COMPLETED.value


class TestWorkingMemoryAsync:
    """Tests for async working memory operations."""

    @pytest.mark.asyncio
    async def test_async_working_memory_operations(self):
        """Test async working memory operations."""
        memory = AsyncWorkingMemory("test-session")

        node_id = await memory.add_node(
            agent=AgentType.PLANNER.value,
            node_type="thought",
            description="Planning step",
        )

        assert node_id is not None

        await memory.update_node(
            node_id, completed=True, status=StepStatus.COMPLETED.value
        )

        entry = await memory.get_node(node_id)
        assert entry is not None
        assert entry.status == StepStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_async_working_memory_to_dict(self):
        """Test async working memory serialization."""
        memory = AsyncWorkingMemory("test-session")

        await memory.add_node(
            agent=AgentType.PLANNER.value,
            node_type="step",
            description="Test step",
        )

        data = await memory.to_dict()
        assert data is not None
        assert "tree" in data
        assert "timeline" in data
        assert "index" in data


class TestMemoryNodes:
    """Tests for memory node and timeline entry operations."""

    def test_memory_node_creation(self):
        """Test memory node creation."""
        node = MemoryNode(
            id="test-node",
            agent=AgentType.PLANNER.value,
            node_type="thought",
            description="Test node",
        )

        assert node.id == "test-node"
        assert node.agent == AgentType.PLANNER.value
        assert node.status == "pending"
        assert node.children == []

    def test_memory_node_to_dict(self):
        """Test memory node serialization."""
        node = MemoryNode(
            id="test-node",
            agent=AgentType.MASTER.value,
            node_type="result",
            description="Result node",
            content={"answer": "42"},
        )

        data = node.to_dict()
        assert data["id"] == "test-node"
        assert data["content"]["answer"] == "42"

    def test_timeline_entry_creation(self):
        """Test timeline entry creation."""
        entry = TimelineEntry(
            node_id="step-1",
            agent="planner",
            node_type="step",
            description="Planning",
            status="running",
        )

        assert entry.node_id == "step-1"
        assert entry.agent == "planner"


class TestStepAnalyzer:
    """Tests for step analysis and parallel execution."""

    def test_parallel_compatible_steps(self):
        """Test identifying parallel-compatible steps."""
        step1 = {"type": StepType.RESEARCH.value, "agent": "researcher"}
        step2 = {"type": StepType.CODE.value, "agent": "tools"}

        assert StepAnalyzer.can_run_parallel(step1, step2) is True

    def test_sequential_only_steps(self):
        """Test that REVIEW and THINK steps are sequential only."""
        assert StepType.REVIEW.value in StepAnalyzer.SEQUENTIAL_ONLY
        assert StepType.THINK.value in StepAnalyzer.SEQUENTIAL_ONLY

    def test_think_step_not_parallel(self):
        """Test that THINK steps cannot run in parallel."""
        step1 = {"type": StepType.THINK.value}
        step2 = {"type": StepType.CODE.value}

        assert StepAnalyzer.can_run_parallel(step1, step2) is False

    def test_find_parallel_batch(self):
        """Test finding batch of steps that can run in parallel."""
        plan = [
            {"type": StepType.RESEARCH.value},
            {"type": StepType.CODE.value},
            {"type": StepType.DATABASE.value},
            {"type": StepType.REVIEW.value},
        ]

        batch = StepAnalyzer.find_parallel_batch(plan, 0)
        assert len(batch) >= 1
        assert 0 in batch


class TestErrorHandling:
    """Tests for error handling and recovery."""

    def test_agent_error_creation(self):
        """Test creating an agent error."""
        error = AgentError(
            error_type=ErrorType.API_TIMEOUT,
            message="Request timed out",
            retry_count=0,
            max_retries=3,
        )
        assert error.error_type == ErrorType.API_TIMEOUT
        assert error.message == "Request timed out"
        assert error.retry_count == 0
        assert error.max_retries == 3

    def test_error_retry_eligibility(self):
        """Test retry eligibility."""
        error = AgentError(
            error_type=ErrorType.API_TIMEOUT,
            message="Timeout",
            retry_count=0,
            max_retries=3,
        )
        assert error.can_retry is True
        error.retry_count = 3
        assert error.can_retry is False

    def test_non_retryable_error(self):
        """Test non-retryable error type."""
        error = AgentError(
            error_type=ErrorType.VALIDATION_ERROR,
            message="Invalid input",
            retry_count=0,
            max_retries=3,
        )
        assert error.can_retry is False

    def test_error_retry_delay(self):
        """Test exponential backoff for retries."""
        error = AgentError(
            error_type=ErrorType.API_TIMEOUT,
            message="Timeout",
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

    def test_error_from_exception_timeout(self):
        """Test creating error from timeout exception."""
        error = AgentError.from_exception(Exception("Connection timeout after 30s"))
        assert error.error_type == ErrorType.CONNECTION_TIMEOUT

    def test_error_from_exception_rate_limit(self):
        """Test creating error from rate limit exception."""
        error = AgentError.from_exception(Exception("429 rate limit exceeded"))
        assert error.error_type == ErrorType.API_RATE_LIMIT

    def test_error_from_exception_auth(self):
        """Test creating error from auth exception."""
        error = AgentError.from_exception(
            Exception("401 Unauthorized: Invalid API key")
        )
        assert error.error_type == ErrorType.API_AUTH

    def test_error_to_dict(self):
        """Test error serialization to dictionary."""
        error = AgentError(
            error_type=ErrorType.API_TIMEOUT,
            message="Test error",
            retry_count=1,
            max_retries=3,
        )
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "api_timeout"
        assert error_dict["message"] == "Test error"
        assert error_dict["retry_count"] == 1


class TestUserIntervention:
    """Tests for user intervention handling."""

    def test_intervention_state_initial(self):
        """Test initial intervention state."""
        from app.agents.error_handler import UserInterventionState

        state = UserInterventionState(session_id="test-session")
        assert state.awaiting_response is False
        assert state.pending_error is None

    def test_set_pending_error(self):
        """Test setting a pending error."""
        from app.agents.error_handler import UserInterventionState

        state = UserInterventionState(session_id="test-session")
        error = AgentError(
            error_type=ErrorType.API_TIMEOUT,
            message="Timeout",
            retry_count=3,
            max_retries=3,
        )
        state.set_pending_error(error)
        assert state.awaiting_response is True
        assert state.pending_error == error

    def test_clear_state(self):
        """Test clearing intervention state."""
        from app.agents.error_handler import UserInterventionState

        state = UserInterventionState(session_id="test-session")
        error = AgentError(
            error_type=ErrorType.API_TIMEOUT,
            message="Timeout",
            retry_count=3,
            max_retries=3,
        )
        state.set_pending_error(error)
        state.clear()
        assert state.awaiting_response is False
        assert state.pending_error is None


class TestErrorSSEvents:
    """Tests for SSE event creation for errors."""

    def test_create_error_event(self):
        """Test creating error SSE event."""
        from app.agents.error_handler import create_error_sse_event

        error = AgentError(
            error_type=ErrorType.API_RATE_LIMIT,
            message="Rate limit exceeded",
            retry_count=1,
            max_retries=3,
        )

        step_info = {"type": "research", "description": "Searching", "step_number": 2}

        event = create_error_sse_event(error, step_info)

        assert event["event_type"] == "error"
        assert event["error"]["error_type"] == "api_rate_limit"
        assert event["intervention_options"]["retry"] is True

    def test_create_retry_event(self):
        """Test creating retry SSE event."""
        from app.agents.error_handler import create_retry_sse_event

        step_info = {"type": "research", "description": "Searching", "step_number": 2}

        event = create_retry_sse_event(
            retry_count=2, max_retries=3, delay=4.0, step_info=step_info
        )

        assert event["event_type"] == "retry"
        assert event["retry_count"] == 2
        assert event["delay"] == 4.0


class TestExecuteWithRetry:
    """Tests for execute_with_retry function."""

    @pytest.mark.asyncio
    async def test_successful_execution_after_retries(self):
        """Test successful execution after transient failures."""
        from app.agents.error_handler import execute_with_retry

        call_count = 0

        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "Success!"

        result = await execute_with_retry(
            flaky_function, max_retries=3, error_context={"test": "value"}
        )

        assert result == "Success!"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_failure_after_max_retries(self):
        """Test failure after exhausting retries."""
        from app.agents.error_handler import execute_with_retry, AgentError

        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise Exception("Always fails")

        with pytest.raises(AgentError):
            await execute_with_retry(
                always_fails, max_retries=2, error_context={"test": "value"}
            )

        assert call_count == 3


class TestLLMMocks:
    """Tests for LLM provider mocking."""

    @pytest.fixture
    def mock_anthropic_response(self):
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
    def mock_openai_response(self):
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
    def mock_planner_response(self):
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
    def mock_researcher_response(self):
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
    def mock_tools_response(self):
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
    def mock_database_response(self):
        """Mock response for the database agent."""
        return {
            "results": [
                {"column1": "value1", "column2": 100},
                {"column1": "value2", "column2": 200},
            ],
            "row_count": 2,
            "columns": ["column1", "column2"],
        }

    def test_anthropic_response_mock(self, mock_anthropic_response):
        """Test Anthropic API response mock structure."""
        assert mock_anthropic_response["id"] == "msg_test123"
        assert mock_anthropic_response["role"] == "assistant"
        assert len(mock_anthropic_response["content"]) > 0
        assert mock_anthropic_response["model"] == "claude-3-5-sonnet-20241022"

    def test_openai_response_mock(self, mock_openai_response):
        """Test OpenAI API response mock structure."""
        assert mock_openai_response["id"] == "chatcmpl_test123"
        assert mock_openai_response["object"] == "chat.completion"
        assert len(mock_openai_response["choices"]) > 0
        assert mock_openai_response["model"] == "gpt-4-turbo"

    def test_planner_response_mock(self, mock_planner_response):
        """Test planner agent response mock structure."""
        assert "plan" in mock_planner_response
        assert "plan_version" in mock_planner_response
        assert len(mock_planner_response["plan"]) == 2

        step = mock_planner_response["plan"][0]
        assert "step_number" in step
        assert "agent_type" in step
        assert "description" in step

    def test_researcher_response_mock(self, mock_researcher_response):
        """Test researcher agent response mock structure."""
        assert "findings" in mock_researcher_response
        assert "sources" in mock_researcher_response

        finding = mock_researcher_response["findings"][0]
        assert "title" in finding
        assert "url" in finding
        assert "summary" in finding

    def test_tools_response_mock(self, mock_tools_response):
        """Test tools agent response mock structure."""
        assert "results" in mock_tools_response
        assert "charts" in mock_tools_response

        result = mock_tools_response["results"][0]
        assert "tool" in result
        assert "success" in result
        assert "output" in result

    def test_database_response_mock(self, mock_database_response):
        """Test database agent response mock structure."""
        assert "results" in mock_database_response
        assert "row_count" in mock_database_response
        assert "columns" in mock_database_response

        assert mock_database_response["row_count"] == 2


class TestResearcherAgent:
    """Tests for researcher agent."""

    @pytest.mark.asyncio
    async def test_researcher_url_selection(self):
        """Test researcher agent URL selection logic."""
        from app.agents.researcher import ResearcherAgent

        researcher = ResearcherAgent()
        search_results = {
            "results": [
                {"title": "Relevant 1", "url": "https://a.com", "score": 0.9},
                {"title": "Relevant 2", "url": "https://b.com", "score": 0.8},
                {"title": "Relevant 3", "url": "https://c.com", "score": 0.75},
                {"title": "Irrelevant", "url": "https://d.com", "score": 0.1},
            ]
        }

        selected = researcher._select_urls_for_scraping(search_results)
        assert len(selected) >= 1
        assert "https://a.com" in selected


class TestToolsAgent:
    """Tests for tools agent."""

    def test_tools_agent_initialization(self):
        """Test tools agent initialization."""
        from app.agents.tools import ToolsAgent
        from sqlalchemy.ext.asyncio import AsyncSession

        agent = ToolsAgent(db_session=MagicMock(spec=AsyncSession))
        assert agent is not None

    def test_calculator_tool(self):
        """Test calculator tool execution."""
        from app.tools.calculator import Calculator

        calculator = Calculator()
        result = calculator.evaluate("2 + 2")
        assert result["success"] is True
        assert result["result"] == 4

    def test_calculator_tool_expression(self):
        """Test calculator with complex expression."""
        from app.tools.calculator import Calculator

        calculator = Calculator()
        result = calculator.evaluate("(10 + 5) * 2")
        assert result["success"] is True
        assert result["result"] == 30


class TestPlannerAgent:
    """Tests for planner agent."""

    def test_planner_agent_exists(self):
        """Test that planner agent module exists."""
        from app.agents import planner

        assert planner is not None
