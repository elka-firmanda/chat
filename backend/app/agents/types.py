"""
Shared types for agent system.

Contains AgentState, StepType, StepStatus, AgentType enums to avoid circular imports.
"""

from typing import TypedDict, List, Dict, Any, Optional
from enum import Enum


class AgentType(str, Enum):
    """Agent type identifiers."""

    MASTER = "master"
    PLANNER = "planner"
    RESEARCHER = "researcher"
    TOOLS = "tools"
    DATABASE = "database"


class StepType(str, Enum):
    """Plan step types for routing."""

    RESEARCH = "research"
    CODE = "code"
    DATABASE = "database"
    CALCULATE = "calculate"
    CHART = "chart"
    THINK = "think"
    REVIEW = "review"


class StepStatus(str, Enum):
    """Step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentState(TypedDict):
    """State for the LangGraph agent workflow."""

    user_message: str
    session_id: str
    deep_search_enabled: bool
    user_timezone: str
    working_memory: Dict[str, Any]
    current_plan: List[Dict[str, Any]]
    plan_version: int
    active_step: int
    master_output: str
    planner_output: Dict[str, Any]
    researcher_output: Dict[str, Any]
    tools_output: Dict[str, Any]
    database_output: Dict[str, Any]
    previous_step_output: Dict[str, Any]
    requires_replan: bool
    retry_count: int
    error_log: List[Dict[str, Any]]
    awaiting_intervention: bool
    intervention_action: Optional[str]
    current_error: Optional[Dict[str, Any]]
    final_answer: str
    usage: Optional[Dict[str, Any]]
    skip_planner: bool
    retry_state: Optional[Dict[str, Any]]
