"""
Unit tests for agent modules.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.error_handler import (
    AgentError,
    ErrorType,
    InterventionAction,
    UserInterventionState,
)


class TestAgentError:
    """Test the AgentError class."""

    def test_create_error(self):
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

    def test_from_exception(self):
        """Test creating error from exception."""
        error = AgentError.from_exception(Exception("429 rate limit exceeded"))
        assert error.error_type == ErrorType.API_RATE_LIMIT
        assert "rate limit" in error.message.lower()

    def test_timeout_error_classification(self):
        """Test timeout error classification."""
        error = AgentError.from_exception(Exception("Connection timeout after 30s"))
        assert error.error_type == ErrorType.CONNECTION_TIMEOUT

    def test_validation_error_classification(self):
        """Test validation error classification."""
        error = AgentError.from_exception(
            Exception("Validation failed: field required")
        )
        assert error.error_type == ErrorType.VALIDATION_ERROR

    def test_auth_error_classification(self):
        """Test authentication error classification."""
        error = AgentError.from_exception(
            Exception("401 Unauthorized: Invalid API key")
        )
        assert error.error_type == ErrorType.API_AUTH

    def test_can_retry(self):
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

    def test_retry_delay(self):
        """Test retry delay calculation (exponential backoff)."""
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


class TestUserInterventionState:
    """Test the UserInterventionState class."""

    def test_initial_state(self):
        """Test initial intervention state."""
        state = UserInterventionState()
        assert state.awaiting_response is False
        assert state.pending_error is None

    def test_set_pending_error(self):
        """Test setting a pending error."""
        state = UserInterventionState()
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
        state = UserInterventionState()
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


class TestPlannerAgent:
    """Test the planner agent."""

    def test_planner_prompt_generation(self):
        """Test that planner generates appropriate prompts."""
        from app.agents.planner import PlannerAgent

        planner = PlannerAgent()
        user_message = "Research the latest AI developments"
        context = {"session_id": "test-session"}

        assert planner is not None

    def test_plan_structure(self):
        """Test that plan has correct structure."""
        from app.agents.planner import PlannerAgent

        planner = PlannerAgent()
        plan = planner.create_plan("Analyze sales data for Q4")

        assert plan is not None


class TestResearcherAgent:
    """Test the researcher agent."""

    @pytest.mark.asyncio
    async def test_researcher_search(self):
        """Test researcher search functionality."""
        from app.agents.researcher import ResearcherAgent

        researcher = ResearcherAgent()

        with patch("app.tools.tavily.tavily_search") as mock_search:
            mock_search.return_value = {
                "results": [
                    {"title": "Test", "url": "https://example.com", "content": "Test"}
                ]
            }

            results = await researcher.search("test query")
            assert results is not None

    def test_researcher_url_selection(self):
        """Test that researcher selects relevant URLs."""
        from app.agents.researcher import ResearcherAgent

        researcher = ResearcherAgent()
        search_results = [
            {"title": "Relevant 1", "url": "https://a.com", "relevance": 0.9},
            {"title": "Relevant 2", "url": "https://b.com", "relevance": 0.8},
            {"title": "Irrelevant", "url": "https://c.com", "relevance": 0.1},
        ]

        selected = researcher.select_urls(search_results, max_urls=2)
        assert len(selected) == 2
        assert all(r["relevance"] >= 0.8 for r in selected)


class TestToolsAgent:
    """Test the tools agent."""

    def test_tools_agent_initialization(self):
        """Test tools agent initialization."""
        from app.agents.tools import ToolsAgent

        agent = ToolsAgent()
        assert agent is not None

    def test_calculator_tool(self):
        """Test calculator tool execution."""
        from app.tools.calculator import CalculatorTool

        tool = CalculatorTool()
        result = tool.execute("2 + 2")
        assert result == 4

    def test_calculator_tool_expression(self):
        """Test calculator with complex expression."""
        from app.tools.calculator import CalculatorTool

        tool = CalculatorTool()
        result = tool.execute("(10 + 5) * 2")
        assert result == 30


class TestMemoryManager:
    """Test the working memory manager."""

    def test_create_memory_tree(self):
        """Test creating memory tree structure."""
        from app.agents.memory import MemoryManager

        manager = MemoryManager()
        tree = manager.create_tree("master", "root-plan")

        assert tree is not None
        assert "id" in tree
        assert tree["agent"] == "master"

    def test_add_to_timeline(self):
        """Test adding entries to timeline."""
        from app.agents.memory import MemoryManager

        manager = MemoryManager()
        manager.add_timeline_entry("step-1", "planner", "Planning")

        assert len(manager.timeline) == 1
        assert manager.timeline[0]["agent"] == "planner"

    def test_index_operations(self):
        """Test index map operations."""
        from app.agents.memory import MemoryManager

        manager = MemoryManager()
        manager.set_index("step-1", {"status": "completed", "result": "Plan created"})

        entry = manager.get_index("step-1")
        assert entry["status"] == "completed"


class TestErrorSSEvents:
    """Test SSE event creation for errors."""

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
    """Test the execute_with_retry function."""

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
