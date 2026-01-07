"""
Error-Aware Agent Execution

Provides wrapper functions for agent execution with retry logic,
error logging to working memory, and user intervention handling.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional, List

from .types import AgentState, AgentType, StepStatus
from .memory import AsyncWorkingMemory
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
    execute_with_retry,
)

logger = logging.getLogger(__name__)


async def execute_agent_with_error_handling(
    agent_func: Callable,
    state: AgentState,
    session_id: str,
    event_queue: Optional[asyncio.Queue] = None,
) -> AgentState:
    """
    Execute an agent function with comprehensive error handling.

    Args:
        agent_func: The agent function to execute
        state: Current agent state
        session_id: Session identifier
        event_queue: Optional SSE event queue for real-time updates

    Returns:
        Updated state after agent execution
    """
    working_memory = AsyncWorkingMemory(session_id)
    if state.get("working_memory"):
        await working_memory.load(state["working_memory"])

    # Get current step info
    current_plan = state.get("current_plan", [])
    active_step = state.get("active_step", 0)
    step_info = (
        current_plan[active_step]
        if current_plan and active_step < len(current_plan)
        else None
    )

    try:
        # Execute with retry logic
        result_state = await execute_with_retry(
            agent_func,
            state,
            max_retries=3,
            error_context={
                "agent": agent_func.__name__,
                "session_id": session_id,
                "step": active_step,
            },
        )

        # Send completion event if queue available
        if event_queue:
            await event_queue.put(
                {
                    "event": "step_complete",
                    "data": {
                        "step": active_step,
                        "agent": agent_func.__name__,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
            )

        return result_state

    except AgentError as e:
        # Handle agent error with retry logic exhausted
        return await handle_agent_error(
            error=e,
            state=state,
            session_id=session_id,
            working_memory=working_memory,
            event_queue=event_queue,
            step_info=step_info,
        )

    except Exception as e:
        # Handle unexpected errors
        agent_error = AgentError.from_exception(
            exception=e,
            step_info=step_info,
            context={"agent": agent_func.__name__},
        )

        return await handle_agent_error(
            error=agent_error,
            state=state,
            session_id=session_id,
            working_memory=working_memory,
            event_queue=event_queue,
            step_info=step_info,
        )


async def handle_agent_error(
    error: AgentError,
    state: AgentState,
    session_id: str,
    working_memory: AsyncWorkingMemory,
    event_queue: Optional[asyncio.Queue] = None,
    step_info: Optional[Dict[str, Any]] = None,
) -> AgentState:
    """
    Handle an agent error with logging and user intervention.

    Args:
        error: The error that occurred
        state: Current agent state
        session_id: Session identifier
        working_memory: Working memory instance
        event_queue: Optional SSE event queue
        step_info: Information about the step that failed

    Returns:
        Updated state after error handling
    """
    # Log error to state
    error_entry = {
        "timestamp": error.timestamp,
        "error_type": error.error_type.value,
        "message": error.message,
        "step_info": step_info,
        "retry_count": error.retry_count,
        "handled": False,
    }

    state["error_log"] = state.get("error_log", []) + [error_entry]

    # Add error node to working memory
    error_node_id = await working_memory.add_node(
        agent=AgentType.MASTER.value,
        node_type="error",
        description=f"Error: {error.message[:100]}",
        content={
            "error_type": error.error_type.value,
            "message": error.message,
            "retry_count": error.retry_count,
            "can_retry": error.can_retry,
        },
    )

    state["working_memory"] = await working_memory.to_dict()

    # Check if we should retry automatically
    if error.can_retry and error.retry_count < 3:
        # Send retry event
        if event_queue:
            retry_event = create_retry_sse_event(
                retry_count=error.retry_count + 1,
                max_retries=3,
                delay=error.get_retry_delay(),
                step_info=step_info,
            )
            await event_queue.put({"event": "retry", "data": retry_event})

        logger.info(
            f"Retrying after error: {error.message} (attempt {error.retry_count + 1}/3)"
        )
        return state

    # If max retries exceeded, prompt for user intervention
    # Set up intervention state
    intervention_state = get_intervention_state(session_id)
    intervention_state.set_pending_error(error)
    state["awaiting_intervention"] = True
    state["current_error"] = error.to_dict()

    # Send error event with intervention options
    if event_queue:
        error_event = create_error_sse_event(
            error=error,
            step_info=step_info,
        )
        await event_queue.put({"event": "error", "data": error_event})

    # Wait for user intervention (with timeout)
    action = await intervention_state.wait_for_response(timeout=300.0)

    # Process user action
    if action:
        state["intervention_action"] = action.value

        # Send intervention event
        if event_queue:
            intervention_event = create_intervention_sse_event(action, error)
            await event_queue.put({"event": "intervention", "data": intervention_event})

        if action == InterventionAction.RETRY:
            # Reset retry count and retry
            error.retry_count = 0
            state["retry_count"] = 0
            state["awaiting_intervention"] = False
            state["current_error"] = None
            clear_intervention_state(session_id)
            logger.info(f"User requested retry for failed step")
            return state

        elif action == InterventionAction.SKIP:
            # Skip this step
            state["active_step"] = state.get("active_step", 0) + 1
            state["awaiting_intervention"] = False
            state["current_error"] = None
            clear_intervention_state(session_id)
            logger.info(f"User requested to skip failed step")

            # Add skipped node to working memory
            await working_memory.add_node(
                agent=AgentType.MASTER.value,
                node_type="skipped",
                description=f"Step skipped by user: {error.message[:100]}",
                parent_id=error_node_id,
                content={"error": error.to_dict()},
            )
            state["working_memory"] = await working_memory.to_dict()
            return state

        elif action == InterventionAction.ABORT:
            # Abort the entire workflow
            state["awaiting_intervention"] = False
            state["current_error"] = None
            clear_intervention_state(session_id)
            logger.info(f"User requested to abort workflow")

            # Add abort node to working memory
            await working_memory.add_node(
                agent=AgentType.MASTER.value,
                node_type="aborted",
                description=f"Workflow aborted by user: {error.message[:100]}",
                parent_id=error_node_id,
                content={"error": error.to_dict()},
            )
            state["working_memory"] = await working_memory.to_dict()

            # Set final answer to error message
            state["final_answer"] = (
                f"Workflow aborted due to error: {error.message}\n\n"
                "Please try again or modify your request."
            )
            return state

    # Timeout - default to abort
    state["awaiting_intervention"] = False
    state["current_error"] = None
    state["intervention_action"] = "timeout"
    clear_intervention_state(session_id)
    logger.warning(f"User intervention timeout for session {session_id}")

    return state


async def log_error_to_memory(
    working_memory: AsyncWorkingMemory,
    agent: str,
    error: AgentError,
    parent_id: Optional[str] = None,
) -> str:
    """
    Log an error to working memory.

    Args:
        working_memory: Working memory instance
        agent: Agent that encountered the error
        error: The error that occurred
        parent_id: Optional parent node ID

    Returns:
        Node ID of the error node
    """
    node_id = await working_memory.add_node(
        agent=agent,
        node_type="error",
        description=f"Error: {error.message[:100]}",
        parent_id=parent_id,
        content={
            "error_type": error.error_type.value,
            "message": error.message,
            "timestamp": error.timestamp,
            "retry_count": error.retry_count,
            "can_retry": error.can_retry,
            "context": error.context,
        },
    )

    return node_id


def get_retry_delay_for_error(error: AgentError) -> float:
    """
    Get delay in seconds before next retry based on error type.

    Uses exponential backoff with different base delays per error type.

    Args:
        error: The error that occurred

    Returns:
        Delay in seconds before next retry
    """
    base_delays = {
        ErrorType.API_RATE_LIMIT: 5.0,
        ErrorType.API_TIMEOUT: 2.0,
        ErrorType.CONNECTION_TIMEOUT: 2.0,
        ErrorType.NETWORK_ERROR: 3.0,
        ErrorType.API_UNAVAILABLE: 10.0,
    }

    base = base_delays.get(error.error_type, 1.0)
    # Exponential backoff: base * 2^retry_count
    delay = base * (2**error.retry_count)
    # Cap at 60 seconds
    return min(delay, 60.0)
