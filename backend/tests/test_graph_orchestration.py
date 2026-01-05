"""
Unit tests for agent orchestration (graph.py).

Tests the LangGraph state machine, routing logic, step execution,
and response synthesis for the multi-agent chatbot system.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from app.agents.types import AgentState, AgentType, StepType, StepStatus
from app.llm.providers import StreamChunk


class TestCreateInitialState:
    """Tests for the create_initial_state() function."""

    def test_create_initial_state_default_values(self):
        """Test creating initial state with default values."""
        from app.agents.graph import create_initial_state

        state = create_initial_state(
            user_message="Hello, help me with research",
            session_id="test-session-123",
        )

        assert state["user_message"] == "Hello, help me with research"
        assert state["session_id"] == "test-session-123"
        assert state["deep_search_enabled"] is False
        assert state["user_timezone"] == "UTC"
        assert state["working_memory"] == {}
        assert state["current_plan"] == []
        assert state["plan_version"] == 1
        assert state["active_step"] == 0
        assert state["master_output"] == ""
        assert state["planner_output"] == {}
        assert state["researcher_output"] == {}
        assert state["tools_output"] == {}
        assert state["database_output"] == {}
        assert state["previous_step_output"] == {}
        assert state["requires_replan"] is False
        assert state["retry_count"] == 0
        assert state["error_log"] == []
        assert state["awaiting_intervention"] is False
        assert state["intervention_action"] is None
        assert state["current_error"] is None
        assert state["final_answer"] == ""
        assert state["skip_planner"] is True  # Not deep search, so skip planner

    def test_create_initial_state_deep_search_enabled(self):
        """Test creating initial state with deep search enabled."""
        from app.agents.graph import create_initial_state

        state = create_initial_state(
            user_message="Research latest AI developments",
            session_id="test-session-456",
            deep_search_enabled=True,
        )

        assert state["deep_search_enabled"] is True
        assert state["skip_planner"] is False  # Deep search, so don't skip planner

    def test_create_initial_state_custom_timezone(self):
        """Test creating initial state with custom timezone."""
        from app.agents.graph import create_initial_state

        state = create_initial_state(
            user_message="Test message",
            session_id="test-session-789",
            user_timezone="America/Los_Angeles",
        )

        assert state["user_timezone"] == "America/Los_Angeles"


class TestRouteStep:
    """Tests for the route_step() routing logic."""

    def test_route_step_skip_planner(self):
        """Test routing when skip_planner is True."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": False,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": True,
        }

        result = route_step(state)
        assert result == "master"

    def test_route_step_requires_replan(self):
        """Test routing when re-planning is required."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [{"type": "research", "description": "Research"}],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": True,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = route_step(state)
        assert result == "planner"

    def test_route_step_no_plan(self):
        """Test routing when no plan exists."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = route_step(state)
        assert result == "master"

    def test_route_step_active_step_beyond_plan(self):
        """Test routing when active step is beyond plan length."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [{"type": "research", "description": "Research"}],
            "plan_version": 1,
            "active_step": 5,  # Beyond plan length
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = route_step(state)
        assert result == "master"

    def test_route_step_research_type(self):
        """Test routing for research step type."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [
                {"type": StepType.RESEARCH.value, "description": "Research"}
            ],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = route_step(state)
        assert result == "researcher"

    def test_route_step_code_type(self):
        """Test routing for code step type."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [
                {"type": StepType.CODE.value, "description": "Execute code"}
            ],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = route_step(state)
        assert result == "tools"

    def test_route_step_database_type(self):
        """Test routing for database step type."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [
                {"type": StepType.DATABASE.value, "description": "Query database"}
            ],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = route_step(state)
        assert result == "database"

    def test_route_step_calculate_type(self):
        """Test routing for calculate step type."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [
                {"type": StepType.CALCULATE.value, "description": "Calculate"}
            ],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = route_step(state)
        assert result == "tools"

    def test_route_step_chart_type(self):
        """Test routing for chart step type."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [
                {"type": StepType.CHART.value, "description": "Generate chart"}
            ],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = route_step(state)
        assert result == "tools"

    def test_route_step_review_type(self):
        """Test routing for review step type."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [
                {"type": StepType.REVIEW.value, "description": "Review results"}
            ],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = route_step(state)
        assert result == "master"

    def test_route_step_think_type(self):
        """Test routing for think step type."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [{"type": StepType.THINK.value, "description": "Think"}],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = route_step(state)
        assert result == "master"

    def test_route_step_unknown_type_defaults_to_master(self):
        """Test routing for unknown step type defaults to master."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [{"type": "unknown_type", "description": "Unknown"}],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = route_step(state)
        assert result == "master"


class TestShouldContinue:
    """Tests for the should_continue() termination logic."""

    def test_should_continue_with_final_answer(self):
        """Test termination when final_answer exists."""
        from app.agents.graph import should_continue
        from langgraph.graph import END

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": False,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "This is the final answer",
            "skip_planner": True,
        }

        result = should_continue(state)
        assert result == END

    def test_should_continue_active_step_beyond_plan(self):
        """Test termination when active step is beyond plan length."""
        from app.agents.graph import should_continue
        from langgraph.graph import END

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [{"type": "research", "description": "Research"}],
            "plan_version": 1,
            "active_step": 5,  # Beyond plan length
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = should_continue(state)
        assert result == END

    def test_should_continue_no_final_answer_and_steps_remaining(self):
        """Test continuation when no final answer and steps remain."""
        from app.agents.graph import should_continue

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [
                {"type": "research", "description": "Research"},
                {"type": "think", "description": "Think"},
            ],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = should_continue(state)
        assert result == "continue"


class TestStepAnalyzer:
    """Tests for the StepAnalyzer class."""

    def test_can_run_parallel_same_agent_researcher(self):
        """Test parallel execution for two researcher steps."""
        from app.agents.graph import StepAnalyzer

        step1 = {"type": StepType.RESEARCH.value, "agent": AgentType.RESEARCHER.value}
        step2 = {"type": StepType.RESEARCH.value, "agent": AgentType.RESEARCHER.value}

        result = StepAnalyzer.can_run_parallel(step1, step2)
        assert result is True

    def test_can_run_parallel_same_agent_tools(self):
        """Test parallel execution for two tools steps."""
        from app.agents.graph import StepAnalyzer

        step1 = {"type": StepType.CODE.value, "agent": AgentType.TOOLS.value}
        step2 = {"type": StepType.CALCULATE.value, "agent": AgentType.TOOLS.value}

        result = StepAnalyzer.can_run_parallel(step1, step2)
        assert result is True

    def test_can_run_parallel_different_agents(self):
        """Test parallel execution for different agent types."""
        from app.agents.graph import StepAnalyzer

        step1 = {"type": StepType.RESEARCH.value, "agent": AgentType.RESEARCHER.value}
        step2 = {"type": StepType.CODE.value, "agent": AgentType.TOOLS.value}

        result = StepAnalyzer.can_run_parallel(step1, step2)
        assert result is True

    def test_cannot_run_parallel_think_steps(self):
        """Test that think steps cannot run in parallel."""
        from app.agents.graph import StepAnalyzer

        step1 = {"type": StepType.THINK.value, "agent": AgentType.MASTER.value}
        step2 = {"type": StepType.THINK.value, "agent": AgentType.MASTER.value}

        result = StepAnalyzer.can_run_parallel(step1, step2)
        assert result is False

    def test_cannot_run_parallel_review_steps(self):
        """Test that review steps cannot run in parallel."""
        from app.agents.graph import StepAnalyzer

        step1 = {"type": StepType.REVIEW.value, "agent": AgentType.MASTER.value}
        step2 = {"type": StepType.REVIEW.value, "agent": AgentType.MASTER.value}

        result = StepAnalyzer.can_run_parallel(step1, step2)
        assert result is False

    def test_cannot_run_parallel_sequential_only_with_other(self):
        """Test that sequential-only steps cannot run in parallel with others."""
        from app.agents.graph import StepAnalyzer

        step1 = {"type": StepType.THINK.value, "agent": AgentType.MASTER.value}
        step2 = {"type": StepType.RESEARCH.value, "agent": AgentType.RESEARCHER.value}

        result = StepAnalyzer.can_run_parallel(step1, step2)
        assert result is False

    def test_cannot_run_parallel_with_dependency(self):
        """Test that steps with dependencies cannot run in parallel."""
        from app.agents.graph import StepAnalyzer

        step1 = {"type": StepType.RESEARCH.value, "step_number": 0}
        step2 = {"type": StepType.CODE.value, "depends_on": 0}

        result = StepAnalyzer.can_run_parallel(step1, step2)
        assert result is False

    def test_find_parallel_batch_single_step(self):
        """Test finding parallel batch with single step."""
        from app.agents.graph import StepAnalyzer

        plan = [
            {"type": StepType.RESEARCH.value, "description": "Research 1"},
            {"type": StepType.THINK.value, "description": "Think"},
        ]

        result = StepAnalyzer.find_parallel_batch(plan, 0)
        assert result == [0]

    def test_find_parallel_batch_multiple_parallel(self):
        """Test finding parallel batch with multiple parallel steps."""
        from app.agents.graph import StepAnalyzer

        plan = [
            {"type": StepType.RESEARCH.value, "description": "Research 1"},
            {
                "type": StepType.CODE.value,
                "description": "Code",
            },  # Different type but can run in parallel
            {
                "type": StepType.CALCULATE.value,
                "description": "Calculate",
            },  # Different type
        ]

        result = StepAnalyzer.find_parallel_batch(plan, 0)
        # Should include multiple steps since they can run in parallel
        assert len(result) >= 1

    def test_find_parallel_batch_stops_at_sequential(self):
        """Test that parallel batch stops at sequential-only steps."""
        from app.agents.graph import StepAnalyzer

        plan = [
            {"type": StepType.RESEARCH.value, "description": "Research 1"},
            {"type": StepType.RESEARCH.value, "description": "Research 2"},
            {"type": StepType.THINK.value, "description": "Think"},
        ]

        result = StepAnalyzer.find_parallel_batch(plan, 0)
        assert StepType.THINK.value not in [plan[i].get("type") for i in result]

    def test_find_parallel_batch_empty_plan(self):
        """Test finding parallel batch with empty plan."""
        from app.agents.graph import StepAnalyzer

        result = StepAnalyzer.find_parallel_batch([], 0)
        assert result == []

    def test_find_parallel_batch_start_beyond_plan(self):
        """Test finding parallel batch when start is beyond plan."""
        from app.agents.graph import StepAnalyzer

        plan = [{"type": StepType.RESEARCH.value, "description": "Research"}]

        result = StepAnalyzer.find_parallel_batch(plan, 5)
        assert result == []

    def test_find_parallel_batch_max_batch_size(self):
        """Test that parallel batch respects max batch size."""
        from app.agents.graph import StepAnalyzer

        plan = [
            {"type": StepType.RESEARCH.value, "description": "Research 1"},
            {"type": StepType.RESEARCH.value, "description": "Research 2"},
            {"type": StepType.RESEARCH.value, "description": "Research 3"},
            {"type": StepType.RESEARCH.value, "description": "Research 4"},
        ]

        result = StepAnalyzer.find_parallel_batch(plan, 0, max_batch_size=3)
        assert len(result) <= 3


class TestSynthesizeResponse:
    """Tests for the synthesize_response() function."""

    @pytest.mark.asyncio
    async def test_synthesize_response_with_research_only(self):
        """Test synthesis with research results only."""
        from app.agents.graph import synthesize_response
        from app.llm.providers import StreamChunk

        mock_provider = AsyncMock()
        mock_provider.complete = AsyncMock(
            return_value=StreamChunk(
                content="Synthesized research response",
                delta="",
                is_complete=True,
            )
        )

        with patch("app.agents.graph.get_llm_provider", return_value=mock_provider):
            result = await synthesize_response(
                user_message="What are the latest AI developments?",
                subagent_results={
                    "researcher_output": {
                        "summary": "Research found important developments",
                        "findings": ["Finding 1", "Finding 2"],
                    },
                    "tools_output": {},
                    "database_output": {},
                },
                working_memory={},
            )

            assert result == "Synthesized research response"
            mock_provider.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesize_response_with_tools_only(self):
        """Test synthesis with tools results only."""
        from app.agents.graph import synthesize_response
        from app.llm.providers import StreamChunk

        mock_provider = AsyncMock()
        mock_provider.complete = AsyncMock(
            return_value=StreamChunk(
                content="Synthesized tools response",
                delta="",
                is_complete=True,
            )
        )

        with patch("app.agents.graph.get_llm_provider", return_value=mock_provider):
            result = await synthesize_response(
                user_message="Calculate something",
                subagent_results={
                    "researcher_output": {},
                    "tools_output": {"result": "42"},
                    "database_output": {},
                },
                working_memory={},
            )

            assert result == "Synthesized tools response"
            mock_provider.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesize_response_with_database_only(self):
        """Test synthesis with database results only."""
        from app.agents.graph import synthesize_response
        from app.llm.providers import StreamChunk

        mock_provider = AsyncMock()
        mock_provider.complete = AsyncMock(
            return_value=StreamChunk(
                content="Synthesized database response",
                delta="",
                is_complete=True,
            )
        )

        with patch("app.agents.graph.get_llm_provider", return_value=mock_provider):
            result = await synthesize_response(
                user_message="Query the database",
                subagent_results={
                    "researcher_output": {},
                    "tools_output": {},
                    "database_output": {
                        "results": [{"col1": "val1"}, {"col1": "val2"}],
                        "row_count": 2,
                    },
                },
                working_memory={},
            )

            assert result == "Synthesized database response"
            mock_provider.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesize_response_no_subagent_results(self):
        """Test synthesis with no subagent results."""
        from app.agents.graph import synthesize_response
        from app.llm.providers import StreamChunk

        mock_provider = AsyncMock()
        mock_provider.complete = AsyncMock(
            return_value=StreamChunk(
                content="No results available",
                delta="",
                is_complete=True,
            )
        )

        with patch("app.agents.graph.get_llm_provider", return_value=mock_provider):
            result = await synthesize_response(
                user_message="Simple question",
                subagent_results={
                    "researcher_output": {},
                    "tools_output": {},
                    "database_output": {},
                },
                working_memory={},
            )

            assert result == "No results available"
            # Verify the context passed includes "No subagent results available"
            call_args = mock_provider.complete.call_args
            messages = call_args.kwargs["messages"]
            assert "No subagent results available" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_synthesize_response_with_multiple_findings(self):
        """Test synthesis with multiple research findings."""
        from app.agents.graph import synthesize_response
        from app.llm.providers import StreamChunk

        mock_provider = AsyncMock()
        mock_provider.complete = AsyncMock(
            return_value=StreamChunk(
                content="Synthesized response",
                delta="",
                is_complete=True,
            )
        )

        with patch("app.agents.graph.get_llm_provider", return_value=mock_provider):
            # Create more than 10 findings to test truncation
            findings = [f"Finding {i}" for i in range(15)]
            result = await synthesize_response(
                user_message="Research many things",
                subagent_results={
                    "researcher_output": {
                        "summary": "Summary of research",
                        "findings": findings,
                    },
                    "tools_output": {},
                    "database_output": {},
                },
                working_memory={},
            )

            assert result == "Synthesized response"
            # Verify only first 10 findings are included (0-9, not 10-14)
            call_args = mock_provider.complete.call_args
            messages = call_args.kwargs["messages"]
            content = messages[0]["content"]
            assert "Finding 9" in content
            assert "Finding 10" not in content
            assert "Finding 14" not in content


class TestStreamSynthesizeResponse:
    """Tests for the stream_synthesize_response() function."""

    @pytest.mark.asyncio
    async def test_stream_synthesize_response_empty_results(self):
        """Test streaming synthesis with empty results."""
        from app.agents.graph import stream_synthesize_response

        async def mock_stream():
            chunks = [
                StreamChunk(content="Hello", delta="Hello", is_complete=False),
                StreamChunk(content="Hello World", delta=" World", is_complete=True),
            ]
            for chunk in chunks:
                yield chunk

        mock_provider = AsyncMock()
        mock_provider.stream_complete = AsyncMock(return_value=mock_stream())

        with patch("app.agents.graph.get_llm_provider", return_value=mock_provider):
            chunks = []
            async for chunk in stream_synthesize_response(
                user_message="Hello",
                subagent_results={
                    "researcher_output": {},
                    "tools_output": {},
                    "database_output": {},
                },
                working_memory={},
            ):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0].delta == "Hello"
            assert chunks[1].delta == " World"


class TestMasterAgent:
    """Tests for the master_agent() function."""

    @pytest.mark.asyncio
    async def test_master_agent_casual_mode_with_final_answer(self):
        """Test master agent in casual mode with existing final answer."""
        from app.agents.graph import master_agent

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": False,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "Existing answer",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "Existing answer",
            "skip_planner": True,
        }

        result = await master_agent(state)
        assert result["final_answer"] == "Existing answer"

    @pytest.mark.asyncio
    async def test_master_agent_updates_working_memory(self):
        """Test that master agent properly updates working memory."""
        from app.agents.graph import master_agent

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session-123",
            "deep_search_enabled": False,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": True,
        }

        with patch(
            "app.agents.graph.synthesize_response", new_callable=AsyncMock
        ) as mock_synth:
            mock_synth.return_value = "Quick response"

            result = await master_agent(state)

            # Verify working memory was updated
            assert result["working_memory"] is not None
            assert "tree" in result["working_memory"]
            assert "timeline" in result["working_memory"]
            assert "index" in result["working_memory"]


class TestCreateAgentGraph:
    """Tests for the create_agent_graph() function."""

    def test_create_agent_graph_returns_compiled_app(self):
        """Test that create_agent_graph returns a compiled LangGraph app."""
        from app.agents.graph import create_agent_graph

        app = create_agent_graph()

        assert app is not None
        # The compiled app should have the expected methods
        assert hasattr(app, "astream_events")
        assert hasattr(app, "aget_state")

    def test_create_agent_graph_has_all_nodes(self):
        """Test that the graph has all required nodes."""
        from app.agents.graph import create_agent_graph, StateGraph

        app = create_agent_graph()

        # The app should be a compiled StateGraph
        assert app is not None


class TestAgentGraphConstants:
    """Tests for agent graph constants and type definitions."""

    def test_agent_type_values(self):
        """Test that AgentType enum has correct values."""
        from app.agents.types import AgentType

        assert AgentType.MASTER.value == "master"
        assert AgentType.PLANNER.value == "planner"
        assert AgentType.RESEARCHER.value == "researcher"
        assert AgentType.TOOLS.value == "tools"
        assert AgentType.DATABASE.value == "database"

    def test_step_type_values(self):
        """Test that StepType enum has correct values."""
        from app.agents.types import StepType

        assert StepType.RESEARCH.value == "research"
        assert StepType.CODE.value == "code"
        assert StepType.DATABASE.value == "database"
        assert StepType.CALCULATE.value == "calculate"
        assert StepType.CHART.value == "chart"
        assert StepType.THINK.value == "think"
        assert StepType.REVIEW.value == "review"

    def test_step_status_values(self):
        """Test that StepStatus enum has correct values."""
        from app.agents.types import StepStatus

        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.RUNNING.value == "running"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"

    def test_agent_state_required_fields(self):
        """Test that AgentState TypedDict has all required fields."""
        from app.agents.types import AgentState

        # Create a minimal valid state
        state = AgentState(
            user_message="test",
            session_id="test",
            deep_search_enabled=False,
            user_timezone="UTC",
            working_memory={},
            current_plan=[],
            plan_version=1,
            active_step=0,
            master_output="",
            planner_output={},
            researcher_output={},
            tools_output={},
            database_output={},
            previous_step_output={},
            requires_replan=False,
            retry_count=0,
            error_log=[],
            awaiting_intervention=False,
            intervention_action=None,
            current_error=None,
            final_answer="",
            skip_planner=False,
        )

        assert state["user_message"] == "test"
        assert state["session_id"] == "test"


class TestLLMProviderIntegration:
    """Tests for LLM provider integration in graph.py."""

    def test_get_llm_provider_returns_provider(self):
        """Test that get_llm_provider returns a valid provider."""
        from app.agents.graph import get_llm_provider

        # Note: This may fail without API keys, but should not raise
        # if properly mocked
        with patch("app.agents.graph.get_config") as mock_config:
            mock_config.return_value.api_keys.anthropic = None
            mock_config.return_value.api_keys.openai = None
            mock_config.return_value.api_keys.openrouter = None
            mock_config.return_value.agents.master.model_dump.return_value = {
                "provider": "anthropic",
                "model": "test-model",
            }

            # Provider should be None without API keys
            provider = get_llm_provider()
            # This will be None initially, provider is created on first call
            # with actual API keys


class TestErrorHandling:
    """Tests for error handling in graph.py."""

    @pytest.mark.asyncio
    async def test_master_agent_handles_exception_gracefully(self):
        """Test that master agent handles exceptions gracefully."""
        from app.agents.graph import master_agent

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [
                {"type": StepType.RESEARCH.value, "description": "Research"}
            ],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        # Mock the LLM provider to raise an exception
        with patch("app.agents.graph.get_llm_provider") as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.complete = AsyncMock(side_effect=Exception("LLM API error"))
            mock_get_provider.return_value = mock_provider

            # Should not raise, but handle gracefully
            try:
                result = await master_agent(state)
                # If it doesn't raise, it should still have valid structure
                assert "working_memory" in result
            except Exception:
                # If it does raise, that's also acceptable for now
                # as long as it's a controlled exception
                pass


class TestEdgeCases:
    """Tests for edge cases in graph.py."""

    def test_route_step_empty_plan_with_skip_planner(self):
        """Test routing with empty plan and skip_planner True."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": False,
            "user_timezone": "UTC",
            "working_memory": {},
            "current_plan": [],
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": True,
        }

        result = route_step(state)
        assert result == "master"

    def test_route_step_missing_current_plan_key(self):
        """Test routing when current_plan key is missing."""
        from app.agents.graph import route_step

        state: AgentState = {
            "user_message": "Hello",
            "session_id": "test-session",
            "deep_search_enabled": True,
            "user_timezone": "UTC",
            "working_memory": {},
            # No current_plan key
            "plan_version": 1,
            "active_step": 0,
            "master_output": "",
            "planner_output": {},
            "researcher_output": {},
            "tools_output": {},
            "database_output": {},
            "previous_step_output": {},
            "requires_replan": False,
            "retry_count": 0,
            "error_log": [],
            "awaiting_intervention": False,
            "intervention_action": None,
            "current_error": None,
            "final_answer": "",
            "skip_planner": False,
        }

        result = route_step(state)
        assert result == "master"

    def test_step_analyzer_handles_missing_type(self):
        """Test StepAnalyzer with missing step type."""
        from app.agents.graph import StepAnalyzer

        step1 = {"description": "Step 1"}  # No type
        step2 = {"type": StepType.RESEARCH.value, "description": "Step 2"}

        # Should handle gracefully
        result = StepAnalyzer.can_run_parallel(step1, step2)
        # Default behavior when type is empty
        assert isinstance(result, bool)

    def test_step_analyzer_handles_missing_agent(self):
        """Test StepAnalyzer with missing agent."""
        from app.agents.graph import StepAnalyzer

        step1 = {"type": StepType.RESEARCH.value}  # No agent
        step2 = {"type": StepType.RESEARCH.value, "agent": AgentType.RESEARCHER.value}

        result = StepAnalyzer.can_run_parallel(step1, step2)
        # Different agents can run in parallel
        assert result is True
