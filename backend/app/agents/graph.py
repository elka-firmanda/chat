"""Graph module stub for backward compatibility.

This module is deprecated. Use the new MasterAgent directly.
These stubs are kept for existing code compatibility until API routes are updated.
"""

from typing import Any

from .types import AgentType, StepType, StepStatus, AgentState
from .master import (
    MasterAgent,
    run_agent_workflow,
    run_agent_workflow_with_streaming,
    create_agent_graph,
)


app = create_agent_graph()
master_agent = None


def create_initial_state(
    user_message: str,
    session_id: str,
    deep_search_enabled: bool = False,
    user_timezone: str = "UTC",
) -> AgentState:
    return AgentState(
        user_message=user_message,
        session_id=session_id,
        deep_search_enabled=deep_search_enabled,
        user_timezone=user_timezone,
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
        usage=None,
        skip_planner=not deep_search_enabled,
        retry_state=None,
    )


__all__ = [
    "app",
    "master_agent",
    "create_agent_graph",
    "run_agent_workflow",
    "run_agent_workflow_with_streaming",
    "create_initial_state",
    "AgentType",
    "StepType",
    "StepStatus",
    "AgentState",
]
