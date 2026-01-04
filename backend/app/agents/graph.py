"""
LangGraph State Machine for Agent Orchestration

Implements the master agent orchestration using LangGraph's StateGraph.
Handles routing to subagents based on plan steps and manages working memory.
Supports streaming working memory updates via SSE.
"""

import asyncio
import uuid
from datetime import datetime
from typing import (
    TypedDict,
    Annotated,
    List,
    Dict,
    Any,
    Optional,
    Union,
    AsyncIterator,
    Callable,
)
from enum import Enum
from operator import add
import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.config.config_manager import get_config
from app.llm.providers import (
    BaseLLMProvider,
    LLMProviderFactory,
    StreamChunk,
)
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
from .types import AgentState, AgentType, StepType, StepStatus


logger = logging.getLogger(__name__)

_llm_provider: Optional[BaseLLMProvider] = None


def get_llm_provider() -> BaseLLMProvider:
    """Get or create the LLM provider for the master agent."""
    global _llm_provider
    if _llm_provider is None:
        config = get_config()
        api_keys: Dict[str, str] = {}
        if config.api_keys.anthropic:
            api_keys["anthropic"] = config.api_keys.anthropic
        if config.api_keys.openai:
            api_keys["openai"] = config.api_keys.openai
        if config.api_keys.openrouter:
            api_keys["openrouter"] = config.api_keys.openrouter
        agent_config = config.agents.master.model_dump()
        _llm_provider = LLMProviderFactory.from_agent_config(agent_config, api_keys)
    return _llm_provider


async def synthesize_response(
    user_message: str,
    subagent_results: Dict[str, Any],
    working_memory: Dict[str, Any],
) -> str:
    """
    Synthesize a final response using the LLM based on subagent results.

    Args:
        user_message: The original user message
        subagent_results: Dictionary containing results from all subagents
        working_memory: The working memory tree for context

    Returns:
        Synthesized response string
    """
    provider = get_llm_provider()

    research_info = subagent_results.get("researcher_output", {})
    tools_info = subagent_results.get("tools_output", {})
    database_info = subagent_results.get("database_output", {})

    context_parts = []
    if research_info:
        research_summary = research_info.get("summary", "")
        findings = research_info.get("findings", [])
        if research_summary:
            context_parts.append(f"Research findings:\n{research_summary}")
        if findings:
            findings_text = "\n".join(f"- {f}" for f in findings[:10])
            context_parts.append(f"Specific findings:\n{findings_text}")

    if tools_info and tools_info.get("result"):
        context_parts.append(f"Tool execution result: {tools_info['result']}")

    if database_info and database_info.get("results"):
        row_count = database_info.get("row_count", 0)
        results = database_info.get("results", [])
        if row_count > 0:
            sample = results[:5]
            context_parts.append(
                f"Database query returned {row_count} rows. Sample results:\n{sample}"
            )

    context = (
        "\n\n".join(context_parts)
        if context_parts
        else "No subagent results available."
    )

    system_prompt = """You are a master orchestrator for a multi-agent chatbot system.
Your task is to synthesize a coherent, helpful response to the user's question based on
results from specialized subagents (researcher, tools, database).

Guidelines:
- Provide a clear, concise answer directly addressing the user's question
- Incorporate findings from research, tool executions, and database queries
- Use a conversational but professional tone
- If results are incomplete or unavailable, acknowledge this honestly
- Format your response appropriately (bullets for lists, code blocks for code, etc.)
- Keep responses focused and avoid unnecessary verbosity"""

    messages = [
        {
            "role": "user",
            "content": f"User question: {user_message}\n\nSubagent context:\n{context}\n\nPlease provide a synthesized response addressing the user's question.",
        }
    ]

    response = await provider.complete(
        messages=messages,
        system_prompt=system_prompt,
        temperature=0.7,
        max_tokens=2048,
    )

    return response.content


async def stream_synthesize_response(
    user_message: str,
    subagent_results: Dict[str, Any],
    working_memory: Dict[str, Any],
) -> AsyncIterator[StreamChunk]:
    """
    Stream a synthesized response using the LLM.

    Args:
        user_message: The original user message
        subagent_results: Dictionary containing results from all subagents
        working_memory: The working memory tree for context

    Yields:
        StreamChunk objects with response content
    """
    provider = get_llm_provider()

    research_info = subagent_results.get("researcher_output", {})
    tools_info = subagent_results.get("tools_output", {})
    database_info = subagent_results.get("database_output", {})

    context_parts = []
    if research_info:
        research_summary = research_info.get("summary", "")
        findings = research_info.get("findings", [])
        if research_summary:
            context_parts.append(f"Research findings:\n{research_summary}")
        if findings:
            findings_text = "\n".join(f"- {f}" for f in findings[:10])
            context_parts.append(f"Specific findings:\n{findings_text}")

    if tools_info and tools_info.get("result"):
        context_parts.append(f"Tool execution result: {tools_info['result']}")

    if database_info and database_info.get("results"):
        row_count = database_info.get("row_count", 0)
        results = database_info.get("results", [])
        if row_count > 0:
            sample = results[:5]
            context_parts.append(
                f"Database query returned {row_count} rows. Sample results:\n{sample}"
            )

    context = (
        "\n\n".join(context_parts)
        if context_parts
        else "No subagent results available."
    )

    system_prompt = """You are a master orchestrator for a multi-agent chatbot system.
Your task is to synthesize a coherent, helpful response to the user's question based on
results from specialized subagents (researcher, tools, database).

Guidelines:
- Provide a clear, concise answer directly addressing the user's question
- Incorporate findings from research, tool executions, and database queries
- Use a conversational but professional tone
- If results are incomplete or unavailable, acknowledge this honestly
- Format your response appropriately (bullets for lists, code blocks for code, etc.)
- Keep responses focused and avoid unnecessary verbosity"""

    messages = [
        {
            "role": "user",
            "content": f"User question: {user_message}\n\nSubagent context:\n{context}\n\nPlease provide a synthesized response addressing the user's question.",
        }
    ]

    async for chunk in provider.stream_complete(
        messages=messages,
        system_prompt=system_prompt,
        temperature=0.7,
        max_tokens=2048,
    ):
        yield chunk


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
        skip_planner=not deep_search_enabled,
    )


async def master_agent(state: AgentState) -> AgentState:
    """Master agent node - orchestrates subagents based on plan."""
    session_id = state["session_id"]
    deep_search = state["deep_search_enabled"]
    skip_planner = state.get("skip_planner", False)
    current_plan = state.get("current_plan", [])
    active_step = state.get("active_step", 0)
    previous_step_output = state.get("previous_step_output", {})

    if not state.get("working_memory"):
        memory = AsyncWorkingMemory(session_id)
        state["working_memory"] = await memory.to_dict()
    else:
        memory = AsyncWorkingMemory(session_id)
        await memory.load(state["working_memory"])

    if skip_planner and state.get("final_answer"):
        return state

    if skip_planner and not state.get("final_answer"):
        node_id = await memory.add_node(
            agent=AgentType.MASTER.value,
            node_type="thought",
            description="Casual mode - generating quick response",
        )

        await memory.update_node(
            node_id, completed=True, status=StepStatus.COMPLETED.value
        )

        subagent_results = {
            "researcher_output": state.get("researcher_output", {}),
            "tools_output": state.get("tools_output", {}),
            "database_output": state.get("database_output", {}),
        }
        synthesized_response = await synthesize_response(
            user_message=state["user_message"],
            subagent_results=subagent_results,
            working_memory=state.get("working_memory", {}),
        )

        await memory.add_node(
            agent=AgentType.MASTER.value,
            node_type="result",
            description="Quick response generated (casual mode)",
            content=synthesized_response,
        )

        state["working_memory"] = await memory.to_dict()
        state["final_answer"] = synthesized_response
        state["master_output"] = synthesized_response
        return state

    if previous_step_output.get("requires_replan", False):
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

        state["plan_version"] = state.get("plan_version", 1) + 1
        state["requires_replan"] = True
        state["previous_step_output"] = {}

        await memory.add_node(
            agent=AgentType.MASTER.value,
            node_type="thought",
            description=f"Re-planning (v{state['plan_version']}) based on new findings",
            parent_id=trigger_node_id,
        )

        state["working_memory"] = await memory.to_dict()
        return state

    node_id = await memory.add_node(
        agent=AgentType.MASTER.value,
        node_type="thought",
        description="Master agent evaluating next step",
    )

    if not deep_search or not current_plan:
        await memory.update_node(
            node_id, completed=True, status=StepStatus.COMPLETED.value
        )

        subagent_results = {
            "researcher_output": state.get("researcher_output", {}),
            "tools_output": state.get("tools_output", {}),
            "database_output": state.get("database_output", {}),
        }
        synthesized_response = await synthesize_response(
            user_message=state["user_message"],
            subagent_results=subagent_results,
            working_memory=state.get("working_memory", {}),
        )

        await memory.add_node(
            agent=AgentType.MASTER.value,
            node_type="result",
            description="Final response generated",
            content=synthesized_response,
        )

        state["working_memory"] = await memory.to_dict()
        state["final_answer"] = synthesized_response
        state["master_output"] = synthesized_response
        return state

    if state.get("requires_replan", False):
        await memory.update_node(
            node_id,
            content="Re-planning triggered by subagent findings",
            completed=True,
        )
        state["working_memory"] = await memory.to_dict()
        return state

    if active_step >= len(current_plan):
        await memory.update_node(
            node_id, completed=True, status=StepStatus.COMPLETED.value
        )

        subagent_results = {
            "researcher_output": state.get("researcher_output", {}),
            "tools_output": state.get("tools_output", {}),
            "database_output": state.get("database_output", {}),
        }

        synthesized_response = await synthesize_response(
            user_message=state["user_message"],
            subagent_results=subagent_results,
            working_memory=state.get("working_memory", {}),
        )

        await memory.add_node(
            agent=AgentType.MASTER.value,
            node_type="result",
            description="All steps completed - final response synthesized",
            content=synthesized_response,
        )

        state["working_memory"] = await memory.to_dict()
        state["final_answer"] = synthesized_response
        state["master_output"] = synthesized_response
        state["requires_replan"] = False
        return state

    current_step = current_plan[active_step]
    step_type = current_step.get("type", StepType.THINK.value)

    await memory.update_node(
        node_id,
        content=f"Routing to {step_type} agent for step {active_step + 1}/{len(current_plan)}",
        completed=True,
    )

    parallel_indices = StepAnalyzer.find_parallel_batch(current_plan, active_step)

    if len(parallel_indices) > 1:
        return await execute_steps_parallel(state, parallel_indices, memory)

    step_node_id = await memory.add_node(
        agent=AgentType.MASTER.value,
        node_type="step",
        description=current_step.get("description", f"Step {active_step + 1}"),
        parent_id=node_id,
        content={"step_type": step_type, "step_number": active_step},
    )

    state["working_memory"] = await memory.to_dict()
    state["active_step"] = active_step

    return state


async def planner_agent(state: AgentState) -> AgentState:
    """Planner agent - creates and modifies execution plans."""
    session_id = state["session_id"]
    user_message = state["user_message"]
    plan_version = state.get("plan_version", 1)
    current_plan = state.get("current_plan", [])
    requires_replan = state.get("requires_replan", False)

    memory = AsyncWorkingMemory(session_id)
    if state.get("working_memory"):
        await memory.load(state["working_memory"])

    node_id = await memory.add_node(
        agent=AgentType.PLANNER.value,
        node_type="thought",
        description="Creating execution plan"
        if not requires_replan
        else "Re-planning based on new findings",
        parent_id="root",
    )

    if not current_plan or requires_replan:
        plan = await _generate_plan(
            user_message=user_message,
            deep_search=state["deep_search_enabled"],
            previous_plan=current_plan if requires_replan else None,
            research_findings=state.get("researcher_output", {}),
        )

        plan_node_id = await memory.add_node(
            agent=AgentType.PLANNER.value,
            node_type="result",
            description=f"Plan v{plan_version} created with {len(plan)} steps",
            parent_id=node_id,
            content=plan,
        )

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
    """Generate a plan using LLM based on the user message and context."""
    provider = get_llm_provider()

    context_parts = []
    if previous_plan:
        context_parts.append(f"Previous plan that needs revision:\n{previous_plan}")
    if research_findings:
        summary = research_findings.get("summary", "")
        findings = research_findings.get("findings", [])
        if summary:
            context_parts.append(
                f"Research findings that may affect planning:\n{summary}"
            )
        if findings:
            context_parts.append(
                f"Key findings:\n{chr(10).join(f'- {f}' for f in findings[:5])}"
            )

    context = "\n\n".join(context_parts) if context_parts else "No previous context."

    is_replan = previous_plan is not None

    system_prompt = """You are a planning agent for a multi-agent chatbot system.
Your task is to create a step-by-step execution plan to answer the user's question.

Available agent types:
- researcher: Search the web for information using Tavily API
- tools: Execute Python code, calculations, or generate charts
- database: Query a data warehouse for structured data
- master: Direct thinking and response synthesis

Guidelines:
- Create a concise plan with 2-5 steps maximum
- Only include steps that are necessary to answer the question
- For simple questions, skip research and just use direct synthesis
- For complex questions, break down into research, analysis, and synthesis steps
- Use "think" step type for direct master agent reasoning
- Use "review" step type for final synthesis before responding

Return your plan as a JSON array of steps with the following structure:
[
  {
    "type": "think|research|code|database|calculate|chart|review",
    "description": "Brief description of the step",
    "agent": "master|researcher|tools|database",
    "query": "optional query for research steps",
    "code": "optional code for execution steps"
  }
]"""

    messages = [
        {
            "role": "user",
            "content": f"""User question: {user_message}

Planning context:
{context}

Planning mode: {"Re-planning" if is_replan else "Initial planning"}
Deep search enabled: {deep_search}

Please create a JSON execution plan.""",
        }
    ]

    response = await provider.complete(
        messages=messages,
        system_prompt=system_prompt,
        temperature=0.3,
        max_tokens=1024,
    )

    import json

    try:
        plan = json.loads(response.content)
        if isinstance(plan, list):
            return plan
    except json.JSONDecodeError:
        pass

    fallback_plan = []

    fallback_plan.append(
        {
            "type": StepType.THINK.value,
            "description": "Analyze user request",
            "agent": AgentType.MASTER.value,
        }
    )

    if deep_search:
        fallback_plan.append(
            {
                "type": StepType.RESEARCH.value,
                "description": "Research information on the topic",
                "agent": AgentType.RESEARCHER.value,
                "query": user_message,
            }
        )

    fallback_plan.append(
        {
            "type": StepType.REVIEW.value,
            "description": "Review and synthesize findings",
            "agent": AgentType.MASTER.value,
        }
    )

    return fallback_plan


async def researcher_agent(state: AgentState) -> AgentState:
    """Researcher agent - searches and scrapes information."""
    from .researcher import default_researcher

    session_id = state["session_id"]
    current_step = state.get("current_plan", [])[state.get("active_step", 0)]
    query = current_step.get("query", state["user_message"])

    memory = AsyncWorkingMemory(session_id)
    if state.get("working_memory"):
        await memory.load(state["working_memory"])

    node_id = await memory.add_node(
        agent=AgentType.RESEARCHER.value,
        node_type="thought",
        description=f"Researching: {query[:50]}...",
    )

    research_output = await default_researcher.research(
        query=query,
        session_id=session_id,
        deep_search=state.get("deep_search_enabled", False),
        context={
            "original_plan": state.get("current_plan", []),
            "working_memory": state.get("working_memory", {}),
        },
    )

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

    await memory.update_node(
        node_id,
        content=output,
        completed=True,
        status=StepStatus.COMPLETED.value,
    )

    state["researcher_output"] = output

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
    """Tools agent - executes code, calculations, and generates charts."""
    from .tools import tools_agent as execute_tools

    return await execute_tools(state)


async def database_agent(state: AgentState) -> AgentState:
    """Database agent - queries data warehouse."""
    session_id = state["session_id"]

    memory = AsyncWorkingMemory(session_id)
    if state.get("working_memory"):
        await memory.load(state["working_memory"])

    node_id = await memory.add_node(
        agent=AgentType.DATABASE.value,
        node_type="thought",
        description="Processing database query",
    )

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


class StepAnalyzer:
    """Analyzes plan steps to determine which can run in parallel."""

    PARALLEL_COMPATIBLE = {
        StepType.RESEARCH.value,
        StepType.CODE.value,
        StepType.DATABASE.value,
        StepType.CALCULATE.value,
        StepType.CHART.value,
    }

    SEQUENTIAL_ONLY = {
        StepType.REVIEW.value,
        StepType.THINK.value,
    }

    @staticmethod
    def can_run_parallel(step1: Dict[str, Any], step2: Dict[str, Any]) -> bool:
        type1 = step1.get("type", "")
        type2 = step2.get("type", "")

        if (
            type1 in StepAnalyzer.SEQUENTIAL_ONLY
            or type2 in StepAnalyzer.SEQUENTIAL_ONLY
        ):
            return False

        dep1 = step1.get("depends_on")
        dep2 = step2.get("step_number")
        if dep1 is not None and dep1 == dep2:
            return False

        dep1 = step2.get("depends_on")
        dep2 = step1.get("step_number")
        if dep1 is not None and dep1 == dep2:
            return False

        agent1 = step1.get("agent", "")
        agent2 = step2.get("agent", "")

        if agent1 == agent2 and agent1 in [
            AgentType.RESEARCHER.value,
            AgentType.TOOLS.value,
            AgentType.DATABASE.value,
        ]:
            return True

        if agent1 != agent2:
            return True

        return False

    @staticmethod
    def find_parallel_batch(
        plan: List[Dict[str, Any]], start_step: int, max_batch_size: int = 3
    ) -> List[int]:
        if start_step >= len(plan):
            return []

        batch = [start_step]
        current_step = plan[start_step]

        if current_step.get("type") in StepAnalyzer.SEQUENTIAL_ONLY:
            return batch

        for i in range(start_step + 1, len(plan)):
            if len(batch) >= max_batch_size:
                break

            next_step = plan[i]
            next_type = next_step.get("type", "")

            if next_type in StepAnalyzer.SEQUENTIAL_ONLY:
                break

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
    """Execute multiple steps in parallel using asyncio.gather()."""
    from .tools import tools_agent as execute_tools_agent
    from .researcher import researcher_agent

    session_id = state["session_id"]
    plan = state.get("current_plan", [])

    if not step_indices or step_indices[0] >= len(plan):
        return state

    batch_node_id = await memory.add_node(
        agent=AgentType.MASTER.value,
        node_type="parallel_batch",
        description=f"Parallel execution of {len(step_indices)} steps",
        content={
            "step_indices": step_indices,
            "step_count": len(step_indices),
        },
    )

    async def run_single_step(step_idx: int) -> Dict[str, Any]:
        step = plan[step_idx]
        step_type = step.get("type", StepType.THINK.value)
        step_description = step.get("description", f"Step {step_idx + 1}")

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

        step_state = state.copy()
        step_state["active_step"] = step_idx
        step_state["working_memory"] = await memory.to_dict()

        agent_functions = {
            StepType.RESEARCH.value: researcher_agent,
            StepType.CODE.value: execute_tools_agent,
            StepType.DATABASE.value: database_agent,
            StepType.CALCULATE.value: execute_tools_agent,
            StepType.CHART.value: execute_tools_agent,
        }

        agent_func = agent_functions.get(step_type, master_agent)

        try:
            result_state = await agent_func(step_state)

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

    tasks = [run_single_step(idx) for idx in step_indices]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, BaseException):
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

            for key in ["researcher_output", "tools_output", "database_output"]:
                if key in result_state and result_state[key]:
                    existing = state.get(key, [])
                    new_output = result_state[key]

                    if isinstance(existing, list):
                        existing.append(new_output)
                        state[key] = existing
                    elif isinstance(existing, dict):
                        state[key] = {**existing, **new_output}

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

    state["active_step"] = max(step_indices) + 1
    state["working_memory"] = await memory.to_dict()

    return state


def route_step(state: AgentState) -> str:
    """Route to the next agent based on current step type."""
    current_plan = state.get("current_plan", [])
    active_step = state.get("active_step", 0)
    requires_replan = state.get("requires_replan", False)
    deep_search = state.get("deep_search_enabled", False)
    skip_planner = state.get("skip_planner", False)

    if skip_planner:
        return "master"

    if requires_replan:
        return "planner"

    if not current_plan or active_step >= len(current_plan):
        return "master"

    if not deep_search or not current_plan:
        return "master"

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
    """Determine if execution should continue or end."""
    current_plan = state.get("current_plan", [])
    active_step = state.get("active_step", 0)
    final_answer = state.get("final_answer", "")

    if final_answer:
        return END

    if active_step >= len(current_plan):
        return END

    return "continue"


def create_agent_graph() -> StateGraph:
    """Create the LangGraph state machine."""
    workflow = StateGraph(AgentState)

    workflow.add_node("master", master_agent)
    workflow.add_node("planner", planner_agent)
    workflow.add_node("researcher", researcher_agent)
    workflow.add_node("tools", tools_agent)
    workflow.add_node("database", database_agent)

    workflow.set_entry_point("master")

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

    workflow.add_edge("planner", "master")
    workflow.add_edge("researcher", "master")
    workflow.add_edge("tools", "master")
    workflow.add_edge("database", "master")

    checkpointer = MemorySaver()

    compiled_app = workflow.compile(checkpointer=checkpointer)

    return compiled_app


app = create_agent_graph()


async def run_agent_workflow(
    user_message: str,
    session_id: str,
    deep_search: bool = False,
    user_timezone: str = "UTC",
) -> Dict[str, Any]:
    """Run the agent workflow and return results."""
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
        state_dict: Dict[str, Any] = dict(final_state.values)
        state_dict["timezone_context"] = timezone_context
        return state_dict

    result: Dict[str, Any] = dict(initial_state)
    result["timezone_context"] = timezone_context
    return result


async def run_agent_workflow_with_streaming(
    user_message: str,
    session_id: str,
    deep_search: bool = False,
    user_timezone: str = "UTC",
    event_manager: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Run the agent workflow with streaming working memory updates and message chunks.

    Args:
        user_message: User's message
        session_id: Session identifier
        deep_search: Whether to use deep search
        user_timezone: User's timezone for context
        event_manager: Optional event manager for SSE streaming

    Returns:
        Final state from agent execution
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

    if event_manager:
        await event_manager.emit_thought(
            session_id=session_id,
            agent="master",
            content="Starting agent workflow",
        )

        await event_manager.emit_memory_update(
            session_id=session_id,
            memory_tree={},
            timeline=[
                {
                    "node_id": "root",
                    "agent": "master",
                    "node_type": "root",
                    "description": "Session started",
                    "status": "running",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ],
            index={},
            update_type="full",
        )

    final_state = None
    async for chunk in app.astream_events(initial_state, config, version="v1"):
        if event_manager:
            await _process_graph_event(chunk, session_id, event_manager)

    final_state = await app.aget_state(config)

    if final_state:
        state_dict: Dict[str, Any] = dict(final_state.values)
        state_dict["timezone_context"] = timezone_context

        if event_manager:
            working_memory = state_dict.get("working_memory", {})
            await event_manager.emit_memory_update(
                session_id=session_id,
                memory_tree=working_memory.get("tree", {}),
                timeline=working_memory.get("timeline", []),
                index=working_memory.get("index", {}),
                update_type="full",
            )

            subagent_results = {
                "researcher_output": state_dict.get("researcher_output", {}),
                "tools_output": state_dict.get("tools_output", {}),
                "database_output": state_dict.get("database_output", {}),
            }

            accumulated_content = ""
            async for chunk in stream_synthesize_response(
                user_message=user_message,
                subagent_results=subagent_results,
                working_memory=working_memory,
            ):
                if chunk.delta:
                    accumulated_content += chunk.delta
                    await event_manager.emit_message_chunk(
                        session_id=session_id,
                        content=accumulated_content,
                        delta=chunk.delta,
                        is_complete=chunk.is_complete,
                    )

            if not accumulated_content:
                accumulated_content = state_dict.get("final_answer", "")

            state_dict["final_answer"] = accumulated_content

        return state_dict

    result: Dict[str, Any] = dict(initial_state)
    result["timezone_context"] = timezone_context
    return result


async def _process_graph_event(
    chunk: Dict[str, Any],
    session_id: str,
    event_manager: Any,
) -> None:
    """
    Process LangGraph events and emit SSE events.

    Args:
        chunk: LangGraph event chunk
        session_id: Session identifier
        event_manager: SSE event manager
    """
    event_type = chunk.get("event", "")

    if event_type == "on_chain_start":
        name = chunk.get("name", "")
        data = chunk.get("data", {})

        if name == "master":
            await event_manager.emit_thought(
                session_id=session_id,
                agent="master",
                content="Master agent started",
            )
        elif name == "planner":
            await event_manager.emit_thought(
                session_id=session_id,
                agent="planner",
                content="Planner agent started",
            )
        elif name == "researcher":
            await event_manager.emit_thought(
                session_id=session_id,
                agent="researcher",
                content="Researcher agent started",
            )
        elif name == "tools":
            await event_manager.emit_thought(
                session_id=session_id,
                agent="tools",
                content="Tools agent started",
            )
        elif name == "database":
            await event_manager.emit_thought(
                session_id=session_id,
                agent="database",
                content="Database agent started",
            )

    elif event_type == "on_chain_end":
        name = chunk.get("name", "")
        data = chunk.get("data", {})

        if name == "master" and "output" in data:
            output = data["output"]
            if isinstance(output, dict) and output.get("final_answer"):
                await event_manager.emit_complete(
                    session_id=session_id,
                    message_id="",
                    final_answer=output.get("final_answer", ""),
                )

    elif event_type == "on_chat_model_start":
        await event_manager.emit_thought(
            session_id=session_id,
            agent=chunk.get("metadata", {}).get("agent", "unknown"),
            content="Generating response...",
        )

    elif event_type == "on_chat_model_stream":
        pass

    elif event_type == "on_tool_start":
        tool_name = chunk.get("name", "")
        input_data = chunk.get("input", {})
        query = (
            input_data.get("query", "")
            if isinstance(input_data, dict)
            else str(input_data)
        )

        await event_manager.emit_thought(
            session_id=session_id,
            agent="tools",
            content=f"Executing: {tool_name}",
        )

    elif event_type == "on_tool_end":
        tool_name = chunk.get("name", "")
        output = chunk.get("output", "")

        await event_manager.emit_thought(
            session_id=session_id,
            agent="tools",
            content=f"Completed: {tool_name}",
        )


app = create_agent_graph()
