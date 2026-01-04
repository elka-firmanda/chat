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
from .error_handler import (
    AgentError,
    ErrorType,
    InterventionAction,
    UserInterventionState,
    get_intervention_state,
    clear_intervention_state,
    create_error_sse_event,
    create_retry_sse_event,
    create_intervention_sse_event,
)

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
    user_timezone: str

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
    previous_step_output: Dict[str, Any]

    # Control flow
    requires_replan: bool
    retry_count: int
    error_log: List[Dict[str, Any]]

    # Error handling and user intervention
    awaiting_intervention: bool
    intervention_action: Optional[str]
    current_error: Optional[Dict[str, Any]]

    # Final output
    final_answer: str


def create_initial_state(
    user_message: str,
    session_id: str,
    deep_search_enabled: bool = False,
    user_timezone: str = "UTC",
) -> AgentState:
    """Create initial state for a new conversation."""
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
    )


async def master_agent(state: AgentState) -> AgentState:
    """
    Master agent node - orchestrates subagents based on plan.

    This is the entry point and coordinator for all agent operations.
    Handles re-planning when subagents discover new information.
    """
    session_id = state["session_id"]
    deep_search = state["deep_search_enabled"]
    current_plan = state.get("current_plan", [])
    active_step = state.get("active_step", 0)
    previous_step_output = state.get("previous_step_output", {})

    # Get or create working memory
    if not state.get("working_memory"):
        memory = AsyncWorkingMemory(session_id)
        state["working_memory"] = await memory.to_dict()
    else:
        memory = AsyncWorkingMemory(session_id)
        await memory.load(state["working_memory"])

    # Check if re-planning was triggered by previous subagent
    if previous_step_output.get("requires_replan", False):
        # Mark the triggering event in working memory
        trigger_node_id = await memory.add_node(
            agent=AgentType.MASTER.value,
            node_type="replan_trigger",
            description=f"Re-plan triggered by {previous_step_output.get('triggered_by', 'subagent')}",
            triggered_by=previous_step_output.get("triggering_node_id"),
            content={
                "reason": previous_step_output.get(
                    "replan_reason", "New information requires plan update"
                ),
                "findings_summary": previous_step_output.get("findings_summary", ""),
                "plan_version": state.get("plan_version", 1),
            },
        )

        # Mark current plan as superseded
        await memory.add_node(
            agent=AgentType.PLANNER.value,
            node_type="plan_superseded",
            description=f"Plan v{state.get('plan_version', 1)} superseded by re-planning",
            triggered_by=trigger_node_id,
            content={
                "superseded_version": state.get("plan_version", 1),
                "reason": previous_step_output.get(
                    "replan_reason", "New information requires plan update"
                ),
            },
        )

        # Increment plan version for new plan
        state["plan_version"] = state.get("plan_version", 1) + 1
        state["requires_replan"] = True
        state["previous_step_output"] = {}

        # Add master thought about re-planning
        await memory.add_node(
            agent=AgentType.MASTER.value,
            node_type="thought",
            description=f"Re-planning (v{state['plan_version']}) based on new findings",
            parent_id=trigger_node_id,
        )

        state["working_memory"] = await memory.to_dict()
        return state

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

    # Check if this step can run with subsequent steps in parallel
    parallel_indices = StepAnalyzer.find_parallel_batch(current_plan, active_step)

    if len(parallel_indices) > 1:
        # Execute steps in parallel
        return await execute_steps_parallel(state, parallel_indices, memory)

    # Single step - create step node and continue with sequential execution
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
    Sets requires_replan flag when findings indicate plan needs updating.
    """
    from .researcher import default_researcher

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

    # Run real research using the researcher module
    research_output = await default_researcher.research(
        query=query,
        session_id=session_id,
        deep_search=state.get("deep_search_enabled", False),
        context={
            "original_plan": state.get("current_plan", []),
            "working_memory": state.get("working_memory", {}),
        },
    )

    # Build structured output for state
    output = {
        "query": research_output.get("query", query),
        "results": research_output.get("search_results", []),
        "scraped_content": research_output.get("scraped_content", []),
        "findings": research_output.get("findings", []),
        "sources": research_output.get("sources", []),
        "summary": research_output.get("research_summary", ""),
        "requires_replan": research_output.get("requires_replan", False),
        "replan_reason": research_output.get("replan_reason"),
    }

    # Update node with results
    await memory.update_node(
        node_id,
        content=output,
        completed=True,
        status=StepStatus.COMPLETED.value,
    )

    state["researcher_output"] = output

    # If re-planning is needed, set up previous_step_output for master
    if output.get("requires_replan", False):
        state["previous_step_output"] = {
            "requires_replan": True,
            "triggered_by": "researcher",
            "triggering_node_id": node_id,
            "replan_reason": output.get(
                "replan_reason", "Research found unexpected information"
            ),
            "findings_summary": output.get("summary", ""),
            "findings": output.get("findings", []),
        }

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


# ==================== Parallel Execution ====================


class StepAnalyzer:
    """Analyzes plan steps to determine which can run in parallel."""

    # Steps that can run in parallel with same-type steps
    PARALLEL_COMPATIBLE = {
        StepType.RESEARCH.value,
        StepType.CODE.value,
        StepType.DATABASE.value,
        StepType.CALCULATE.value,
        StepType.CHART.value,
    }

    # Steps that must run sequentially (produce/consume shared state)
    SEQUENTIAL_ONLY = {
        StepType.REVIEW.value,
        StepType.THINK.value,
    }

    @staticmethod
    def can_run_parallel(step1: Dict[str, Any], step2: Dict[str, Any]) -> bool:
        """
        Determine if two steps can run in parallel.

        Steps can run parallel if:
        1. Both are compatible types (not review/think)
        2. Neither has a depends_on pointing to the other
        3. They don't have conflicting resource requirements
        """
        type1 = step1.get("type", "")
        type2 = step2.get("type", "")

        # Sequential-only steps must run alone
        if (
            type1 in StepAnalyzer.SEQUENTIAL_ONLY
            or type2 in StepAnalyzer.SEQUENTIAL_ONLY
        ):
            return False

        # Check dependency constraints
        dep1 = step1.get("depends_on")
        dep2 = step2.get("step_number")
        if dep1 is not None and dep1 == dep2:
            return False

        dep1 = step2.get("depends_on")
        dep2 = step1.get("step_number")
        if dep1 is not None and dep1 == dep2:
            return False

        # Different agent types can run in parallel
        agent1 = step1.get("agent", "")
        agent2 = step2.get("agent", "")

        # Same agent type can run parallel (e.g., multiple research steps)
        if agent1 == agent2 and agent1 in [
            AgentType.RESEARCHER.value,
            AgentType.TOOLS.value,
            AgentType.DATABASE.value,
        ]:
            return True

        # Different agents can run parallel if no shared state dependencies
        if agent1 != agent2:
            return True

        return False

    @staticmethod
    def find_parallel_batch(
        plan: List[Dict[str, Any]], start_step: int, max_batch_size: int = 3
    ) -> List[int]:
        """
        Find a batch of steps that can run in parallel starting from start_step.

        Args:
            plan: The execution plan
            start_step: Index to start looking from
            max_batch_size: Maximum number of parallel steps

        Returns:
            List of step indices that can run in parallel
        """
        if start_step >= len(plan):
            return []

        batch = [start_step]
        current_step = plan[start_step]

        # REVIEW and THINK steps must run alone
        if current_step.get("type") in StepAnalyzer.SEQUENTIAL_ONLY:
            return batch

        # Look ahead for parallel-compatible steps
        for i in range(start_step + 1, len(plan)):
            if len(batch) >= max_batch_size:
                break

            next_step = plan[i]
            next_type = next_step.get("type", "")

        for i in range(start_step + 1, len(plan)):
            if len(batch) >= max_batch_size:
                break

            next_step = plan[i]
            next_type = next_step.get("type", "")

            # REVIEW and THINK break the parallel batch
            if next_type in StepAnalyzer.SEQUENTIAL_ONLY:
                break

            # Check if this step can run in parallel with all in batch
            can_parallelize = True
            for batch_idx in batch:
                if not StepAnalyzer.can_run_parallel(plan[batch_idx], next_step):
                    can_parallelize = False
                    break

            if can_parallelize:
                batch.append(i)

        return batch


async def execute_steps_parallel(
    state: AgentState,
    step_indices: List[int],
    memory: AsyncWorkingMemory,
) -> AgentState:
    """
    Execute multiple steps in parallel using asyncio.gather().

    Args:
        state: Current agent state
        step_indices: List of step indices to execute
        memory: Working memory instance

    Returns:
        Updated state with all parallel results merged
    """
    session_id = state["session_id"]
    plan = state.get("current_plan", [])

    if not step_indices or step_indices[0] >= len(plan):
        return state

    # Create parallel batch node in working memory
    batch_node_id = await memory.add_node(
        agent=AgentType.MASTER.value,
        node_type="parallel_batch",
        description=f"Parallel execution of {len(step_indices)} steps",
        content={
            "step_indices": step_indices,
            "step_count": len(step_indices),
        },
    )

    # Create coroutines for each step
    async def run_single_step(step_idx: int) -> Dict[str, Any]:
        """Run a single step and return its result."""
        step = plan[step_idx]
        step_type = step.get("type", StepType.THINK.value)
        step_description = step.get("description", f"Step {step_idx + 1}")

        # Create step node
        step_node_id = await memory.add_node(
            agent=AgentType.MASTER.value,
            node_type="step",
            description=step_description,
            parent_id=batch_node_id,
            content={
                "step_type": step_type,
                "step_number": step_idx,
                "parallel_with": step_indices,
            },
        )

        # Route to appropriate agent based on step type
        step_state = state.copy()
        step_state["active_step"] = step_idx
        step_state["working_memory"] = await memory.to_dict()

        # Execute the appropriate agent
        agent_functions = {
            StepType.RESEARCH.value: researcher_agent,
            StepType.CODE.value: tools_agent,
            StepType.DATABASE.value: database_agent,
            StepType.CALCULATE.value: tools_agent,
            StepType.CHART.value: tools_agent,
        }

        agent_func = agent_functions.get(step_type, master_agent)

        try:
            result_state = await agent_func(step_state)

            # Mark step node as completed
            await memory.update_node(
                step_node_id,
                completed=True,
                status=StepStatus.COMPLETED.value,
                content={
                    "completed": True,
                    "step_type": step_type,
                    "step_number": step_idx,
                },
            )

            return {
                "step_index": step_idx,
                "step_type": step_type,
                "success": True,
                "state": result_state,
                "error": None,
            }
        except Exception as e:
            # Mark step node as failed
            await memory.update_node(
                step_node_id,
                completed=True,
                status=StepStatus.FAILED.value,
                content={
                    "failed": True,
                    "step_type": step_type,
                    "step_number": step_idx,
                    "error": str(e),
                },
            )

            return {
                "step_index": step_idx,
                "step_type": step_type,
                "success": False,
                "state": None,
                "error": str(e),
            }

    # Run all steps in parallel
    tasks = [run_single_step(idx) for idx in step_indices]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and merge into state
    for result in results:
        # Handle exceptions from asyncio.gather
        if isinstance(result, BaseException):
            # Log exception but continue with other results
            state["error_log"].append(
                {
                    "type": "parallel_execution",
                    "error": str(result),
                    "step_indices": step_indices,
                }
            )
            continue

        if isinstance(result, dict) and result.get("success") and result.get("state"):
            result_state = result["state"]

            # Merge outputs from each agent into main state
            for key in ["researcher_output", "tools_output", "database_output"]:
                if key in result_state and result_state[key]:
                    # For parallel results, we need to merge them
                    # Use the last successful result or combine intelligently
                    existing = state.get(key, [])
                    new_output = result_state[key]

                    if isinstance(existing, list):
                        existing.append(new_output)
                        state[key] = existing
                    elif isinstance(existing, dict):
                        # Merge dictionaries, preserving existing data
                        state[key] = {**existing, **new_output}

    # Mark batch as completed
    await memory.update_node(
        batch_node_id,
        completed=True,
        status=StepStatus.COMPLETED.value,
        content={
            "completed": True,
            "step_count": len(step_indices),
            "success_count": sum(
                1 for r in results if isinstance(r, dict) and r.get("success")
            ),
        },
    )

    # Update active_step to after the parallel batch
    state["active_step"] = max(step_indices) + 1
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
    user_timezone: str = "UTC",
) -> Dict[str, Any]:
    """
    Run the agent workflow and return results.

    Args:
        user_message: The user's input message
        session_id: Unique session identifier
        deep_search: Whether to use deep search mode
        user_timezone: User's configured timezone for context

    Returns:
        Final state with answer and working memory
    """
    from app.utils.datetime import get_user_timezone_context

    timezone_context = get_user_timezone_context(user_timezone)

    app = create_agent_graph()

    initial_state = create_initial_state(
        user_message=user_message,
        session_id=session_id,
        deep_search_enabled=deep_search,
        user_timezone=user_timezone,
    )

    config = {"configurable": {"thread_id": session_id}}

    final_state = None
    async for chunk in app.astream_events(initial_state, config, version="v1"):
        pass

    final_state = await app.aget_state(config)

    if final_state:
        state_dict = dict(final_state.values)
        state_dict["timezone_context"] = timezone_context
        return state_dict

    initial_state["timezone_context"] = timezone_context
    return initial_state


# Export the graph as 'app' for compatibility with imports
app = create_agent_graph()
