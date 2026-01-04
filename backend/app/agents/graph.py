"""
LangGraph State Machine for Agent Orchestration

Implements the master agent orchestration using LangGraph's StateGraph.
Handles routing to subagents based on plan steps and manages working memory.
"""

import asyncio
import uuid
from datetime import datetime
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Union
from enum import Enum
from operator import add
import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .memory import WorkingMemory, MemoryNode, AsyncWorkingMemory

logger = logging.getLogger(__name__)


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
    THINK = "think"  # Master agent thinks directly
    REVIEW = "review"  # Review and synthesize


class StepStatus(str, Enum):
    """Step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentState(TypedDict):
    """
    State for the LangGraph agent workflow.

    All fields are typed for LangGraph's StateGraph.
    """

    # Core inputs
    user_message: str
    session_id: str
    deep_search_enabled: bool

    # Working memory
    working_memory: Dict[str, Any]
    current_plan: List[Dict[str, Any]]
    plan_version: int
    active_step: int

    # Agent outputs (shared state for results)
    master_output: str
    planner_output: Dict[str, Any]
    researcher_output: Dict[str, Any]
    tools_output: Dict[str, Any]
    database_output: Dict[str, Any]

    # Control flow
    requires_replan: bool
    retry_count: int
    error_log: List[Dict[str, Any]]

    # Final output
    final_answer: str


def create_initial_state(
    user_message: str,
    session_id: str,
    deep_search_enabled: bool = False,
) -> AgentState:
    """Create initial state for a new conversation."""
    return AgentState(
        user_message=user_message,
        session_id=session_id,
        deep_search_enabled=deep_search_enabled,
        working_memory={},
        current_plan=[],
        plan_version=1,
        active_step=0,
        master_output="",
        planner_output={},
        researcher_output={},
        tools_output={},
        database_output={},
        requires_replan=False,
        retry_count=0,
        error_log=[],
        final_answer="",
    )


async def master_agent(state: AgentState) -> AgentState:
    """
    Master agent node - orchestrates subagents based on plan.

    This is the entry point and coordinator for all agent operations.
    """
    session_id = state["session_id"]
    deep_search = state["deep_search_enabled"]
    current_plan = state.get("current_plan", [])
    active_step = state.get("active_step", 0)

    # Get or create working memory
    if not state.get("working_memory"):
        memory = AsyncWorkingMemory(session_id)
        state["working_memory"] = await memory.to_dict()
    else:
        memory = AsyncWorkingMemory(session_id)
        await memory.load(state["working_memory"])

    # Add master thought
    node_id = await memory.add_node(
        agent=AgentType.MASTER.value,
        node_type="thought",
        description="Master agent evaluating next step",
    )

    # Casual chat mode - no orchestration needed
    if not deep_search or not current_plan:
        # Direct response without subagents
        await memory.update_node(
            node_id, completed=True, status=StepStatus.COMPLETED.value
        )

        # Add final answer node
        await memory.add_node(
            agent=AgentType.MASTER.value,
            node_type="result",
            description="Final response generated",
            content=state.get("master_output", state["user_message"]),
        )

        state["working_memory"] = await memory.to_dict()
        state["final_answer"] = state.get("master_output", state["user_message"])
        return state

    # Check if we need re-planning
    if state.get("requires_replan", False):
        await memory.update_node(
            node_id,
            content="Re-planning triggered by subagent findings",
            completed=True,
        )
        # Will route to planner
        state["working_memory"] = await memory.to_dict()
        return state

    # Check if plan is complete
    if active_step >= len(current_plan):
        # Plan complete - synthesize final answer
        await memory.update_node(
            node_id, completed=True, status=StepStatus.COMPLETED.value
        )

        await memory.add_node(
            agent=AgentType.MASTER.value,
            node_type="result",
            description="All steps completed - finalizing answer",
            content="Plan execution complete",
        )

        state["working_memory"] = await memory.to_dict()
        state["requires_replan"] = False
        return state

    # Get current step and route to appropriate agent
    current_step = current_plan[active_step]
    step_type = current_step.get("type", StepType.THINK.value)

    await memory.update_node(
        node_id,
        content=f"Routing to {step_type} agent for step {active_step + 1}/{len(current_plan)}",
        completed=True,
    )

    # Create step node for tracking
    step_node_id = await memory.add_node(
        agent=AgentType.MASTER.value,
        node_type="step",
        description=current_step.get("description", f"Step {active_step + 1}"),
        parent_id=node_id,
        content={"step_type": step_type, "step_number": active_step},
    )

    state["working_memory"] = await memory.to_dict()
    state["active_step"] = active_step

    # Route based on step type
    # This will be handled by conditional edges in the graph
    return state


async def planner_agent(state: AgentState) -> AgentState:
    """
    Planner agent - creates and modifies execution plans.

    Returns a structured plan with steps, or modifies existing plan for re-planning.
    """
    session_id = state["session_id"]
    user_message = state["user_message"]
    plan_version = state.get("plan_version", 1)
    current_plan = state.get("current_plan", [])
    requires_replan = state.get("requires_replan", False)

    # Get working memory
    memory = AsyncWorkingMemory(session_id)
    if state.get("working_memory"):
        await memory.load(state["working_memory"])

    # Add planner thought
    node_id = await memory.add_node(
        agent=AgentType.PLANNER.value,
        node_type="thought",
        description="Creating execution plan"
        if not requires_replan
        else "Re-planning based on new findings",
        parent_id="root",
    )

    # For initial planning
    if not current_plan or requires_replan:
        # Create plan based on user message
        # In production, this would call the LLM
        plan = await _generate_plan(
            user_message=user_message,
            deep_search=state["deep_search_enabled"],
            previous_plan=current_plan if requires_replan else None,
            research_findings=state.get("researcher_output", {}),
        )

        # Create plan node
        plan_node_id = await memory.add_node(
            agent=AgentType.PLANNER.value,
            node_type="result",
            description=f"Plan v{plan_version} created with {len(plan)} steps",
            parent_id=node_id,
            content=plan,
        )

        # Create step nodes for each plan step
        for i, step in enumerate(plan):
            await memory.add_node(
                agent=AgentType.PLANNER.value,
                node_type="step",
                description=step.get("description", f"Step {i + 1}"),
                parent_id=plan_node_id,
                content={"step_number": i, **step},
            )

        state["current_plan"] = plan
        state["plan_version"] = plan_version + 1 if requires_replan else plan_version
        state["requires_replan"] = False
        state["active_step"] = 0

    await memory.update_node(node_id, completed=True, status=StepStatus.COMPLETED.value)
    state["working_memory"] = await memory.to_dict()

    return state


async def _generate_plan(
    user_message: str,
    deep_search: bool,
    previous_plan: Optional[List[Dict]] = None,
    research_findings: Optional[Dict] = None,
) -> List[Dict[str, Any]]:
    """Generate a plan using LLM (simplified version)."""
    # In production, this would call the LLM to generate a structured plan
    # For now, return a simple plan structure

    plan = []

    # Always start with understanding the request
    plan.append(
        {
            "type": StepType.THINK.value,
            "description": "Analyze user request",
            "agent": AgentType.MASTER.value,
        }
    )

    if deep_search:
        # Add research step
        plan.append(
            {
                "type": StepType.RESEARCH.value,
                "description": "Research information on the topic",
                "agent": AgentType.RESEARCHER.value,
                "query": user_message,
            }
        )

    # Add thought/review step
    plan.append(
        {
            "type": StepType.REVIEW.value,
            "description": "Review and synthesize findings",
            "agent": AgentType.MASTER.value,
        }
    )

    return plan


async def researcher_agent(state: AgentState) -> AgentState:
    """
    Researcher agent - searches and scrapes information.

    Uses Tavily API for search and parallel scraping for content.
    """
    session_id = state["session_id"]
    current_step = state.get("current_plan", [])[state.get("active_step", 0)]
    query = current_step.get("query", state["user_message"])

    # Get working memory
    memory = AsyncWorkingMemory(session_id)
    if state.get("working_memory"):
        await memory.load(state["working_memory"])

    # Add researcher thought
    node_id = await memory.add_node(
        agent=AgentType.RESEARCHER.value,
        node_type="thought",
        description=f"Researching: {query[:50]}...",
    )

    # In production, this would:
    # 1. Call Tavily API for search results
    # 2. Select top N URLs
    # 3. Scrape URLs in parallel
    # 4. Extract and clean content

    # Simulated research output
    research_output = {
        "query": query,
        "results": [],
        "sources": [],
        "findings": "Research completed",
        "requires_replan": False,  # Set to True if unexpected findings
    }

    await memory.update_node(
        node_id,
        content=research_output,
        completed=True,
        status=StepStatus.COMPLETED.value,
    )

    state["researcher_output"] = research_output
    state["working_memory"] = await memory.to_dict()

    return state


async def tools_agent(state: AgentState) -> AgentState:
    """
    Tools agent - executes code, calculations, and generates charts.

    Uses RestrictedPython sandbox for safe code execution.
    """
    session_id = state["session_id"]
    current_step = state.get("current_plan", [])[state.get("active_step", 0)]
    step_type = current_step.get("type", "code")

    # Get working memory
    memory = AsyncWorkingMemory(session_id)
    if state.get("working_memory"):
        await memory.load(state["working_memory"])

    # Add tools thought
    node_id = await memory.add_node(
        agent=AgentType.TOOLS.value,
        node_type="thought",
        description=f"Executing {step_type} operation",
    )

    # In production, this would:
    # 1. Parse the step type (code, calculate, chart)
    # 2. Execute in RestrictedPython sandbox
    # 3. Capture output and errors

    tools_output = {
        "type": step_type,
        "result": None,
        "stdout": "",
        "stderr": "",
        "execution_time_ms": 0,
    }

    await memory.update_node(
        node_id,
        content=tools_output,
        completed=True,
        status=StepStatus.COMPLETED.value,
    )

    state["tools_output"] = tools_output
    state["working_memory"] = await memory.to_dict()

    return state


async def database_agent(state: AgentState) -> AgentState:
    """
    Database agent - queries data warehouse.

    Executes SQL queries and returns structured results.
    """
    session_id = state["session_id"]

    # Get working memory
    memory = AsyncWorkingMemory(session_id)
    if state.get("working_memory"):
        await memory.load(state["working_memory"])

    # Add database thought
    node_id = await memory.add_node(
        agent=AgentType.DATABASE.value,
        node_type="thought",
        description="Processing database query",
    )

    # In production, this would:
    # 1. Parse query requirements
    # 2. Execute against data warehouse
    # 3. Return structured results

    database_output = {
        "query": "",
        "results": [],
        "row_count": 0,
        "execution_time_ms": 0,
    }

    await memory.update_node(
        node_id,
        content=database_output,
        completed=True,
        status=StepStatus.COMPLETED.value,
    )

    state["database_output"] = database_output
    state["working_memory"] = await memory.to_dict()

    return state


def route_step(state: AgentState) -> str:
    """
    Route to the next agent based on current step type.

    This is the conditional edge function for LangGraph.
    """
    current_plan = state.get("current_plan", [])
    active_step = state.get("active_step", 0)
    requires_replan = state.get("requires_replan", False)
    deep_search = state.get("deep_search_enabled", False)

    # Check for re-planning
    if requires_replan:
        return "planner"

    # Check if plan is complete
    if not current_plan or active_step >= len(current_plan):
        return "master"

    # Check for casual chat (no plan)
    if not deep_search or not current_plan:
        return "master"

    # Route based on step type
    current_step = current_plan[active_step]
    step_type = current_step.get("type", StepType.THINK.value)

    routing = {
        StepType.RESEARCH.value: "researcher",
        StepType.CODE.value: "tools",
        StepType.DATABASE.value: "database",
        StepType.CALCULATE.value: "tools",
        StepType.CHART.value: "tools",
        StepType.REVIEW.value: "master",
        StepType.THINK.value: "master",
    }

    return routing.get(step_type, "master")


def should_continue(state: AgentState) -> str:
    """
    Determine if execution should continue or end.

    Returns "continue" to stay in graph, or "end" to exit.
    """
    current_plan = state.get("current_plan", [])
    active_step = state.get("active_step", 0)
    final_answer = state.get("final_answer", "")

    # Check if we have a final answer
    if final_answer:
        return END

    # Check if plan is complete
    if active_step >= len(current_plan):
        return END

    return "continue"


def create_agent_graph() -> StateGraph:
    """
    Create the LangGraph state machine.

    Returns a compiled StateGraph ready for execution.
    """
    # Create the state graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("master", master_agent)
    workflow.add_node("planner", planner_agent)
    workflow.add_node("researcher", researcher_agent)
    workflow.add_node("tools", tools_agent)
    workflow.add_node("database", database_agent)

    # Set entry point
    workflow.set_entry_point("master")

    # Add conditional routing from master
    workflow.add_conditional_edges(
        "master",
        route_step,
        {
            "master": "master",
            "planner": "planner",
            "researcher": "researcher",
            "tools": "tools",
            "database": "database",
        },
    )

    # Add edges from other agents back to master
    workflow.add_edge("planner", "master")
    workflow.add_edge("researcher", "master")
    workflow.add_edge("tools", "master")
    workflow.add_edge("database", "master")

    # Add checkpointer for state persistence
    checkpointer = MemorySaver()

    # Compile the graph
    app = workflow.compile(checkpointer=checkpointer)

    return app


async def run_agent_workflow(
    user_message: str,
    session_id: str,
    deep_search: bool = False,
) -> Dict[str, Any]:
    """
    Run the agent workflow and return results.

    Args:
        user_message: The user's input message
        session_id: Unique session identifier
        deep_search: Whether to use deep search mode

    Returns:
        Final state with answer and working memory
    """
    # Create the graph
    app = create_agent_graph()

    # Create initial state
    initial_state = create_initial_state(
        user_message=user_message,
        session_id=session_id,
        deep_search_enabled=deep_search,
    )

    # Run the workflow
    config = {"configurable": {"thread_id": session_id}}

    final_state = None
    async for chunk in app.astream_events(initial_state, config, version="v1"):
        # Can process streaming events here if needed
        pass

    # Get final state
    final_state = await app.aget_state(config)

    return final_state.values if final_state else initial_state


# Export the graph as 'app' for compatibility with imports
app = create_agent_graph()
