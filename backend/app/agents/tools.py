"""
Tools Agent - Executes various tools including code execution, calculations,
chart generation, and custom user-defined tools.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .graph import AgentState, StepType
from .error_handler import AgentError, ErrorType
from app.tools import (
    execute_code as execute_code_tool,
    calculate as calculate_tool,
    generate_chart as generate_chart_tool,
)
from app.tools.custom_tool_runner import (
    execute_custom_tool,
    load_enabled_custom_tools,
    ValidationError,
    ExecutionError,
    TimeoutError,
)


logger = logging.getLogger(__name__)


BUILTIN_TOOLS = {
    StepType.CODE.value: execute_code_tool,
    StepType.CALCULATE.value: calculate_tool,
    StepType.CHART.value: generate_chart_tool,
}


class ToolsAgent:
    """Agent responsible for executing various tools.
    Supports built-in tools and custom user-defined tools.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize the tools agent.

        Args:
            db_session: Database session for loading custom tools
        """
        self.db_session = db_session
        self.custom_tools: Dict[str, Dict[str, Any]] = {}
        self._tools_loaded = False

    async def load_custom_tools(self) -> None:
        """Load enabled custom tools from the database."""
        if self._tools_loaded:
            return

        try:
            self.custom_tools = load_enabled_custom_tools(self.db_session)
            self._tools_loaded = True
            logger.info(f"Loaded {len(self.custom_tools)} custom tools")
        except Exception as e:
            logger.warning(f"Failed to load custom tools: {e}")
            self.custom_tools = {}

    async def execute_tool(
        self,
        step_type: str,
        arguments: Dict[str, Any],
        custom_tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a tool based on the step type.

        Args:
            step_type: Type of tool to execute (from StepType)
            arguments: Arguments to pass to the tool
            custom_tool_name: Name of custom tool to execute (if step_type is custom)

        Returns:
            Dict containing the tool result

        Raises:
            AgentError: If tool execution fails
        """
        await self.load_custom_tools()

        if step_type == "custom" and custom_tool_name:
            return await self._execute_custom(custom_tool_name, arguments)

        if step_type in BUILTIN_TOOLS:
            tool_func = BUILTIN_TOOLS[step_type]
            return await self._execute_builtin(tool_func, arguments, step_type)

        raise AgentError(
            error_type=ErrorType.VALIDATION_ERROR,
            message=f"Unknown tool type: {step_type}",
        )

    async def _execute_builtin(
        self,
        tool_func,
        arguments: Dict[str, Any],
        step_type: str,
    ) -> Dict[str, Any]:
        """Execute a built-in tool.

        Args:
            tool_func: The tool function to execute
            arguments: Arguments to pass
            step_type: Type identifier for error messages

        Returns:
            Tool result dict
        """
        try:
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**arguments)
            else:
                result = tool_func(**arguments)

            return {
                "success": True,
                "tool_type": step_type,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Built-in tool {step_type} failed: {e}")
            raise AgentError(
                error_type=ErrorType.EXECUTION_ERROR,
                message=f"Tool execution failed: {str(e)}",
                context={"tool_type": step_type},
            )

    async def _execute_custom(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a custom tool.

        Args:
            tool_name: Name of the custom tool
            arguments: Arguments to pass

        Returns:
            Tool result dict
        """
        if tool_name not in self.custom_tools:
            raise AgentError(
                error_type=ErrorType.DATA_NOT_FOUND,
                message=f"Custom tool '{tool_name}' not found or disabled",
            )

        tool_info = self.custom_tools[tool_name]

        try:
            result = await execute_custom_tool(
                code=tool_info["code"],
                tool_name=tool_name,
                arguments=arguments,
                timeout=30.0,
            )

            return {
                "success": result["success"],
                "tool_type": "custom",
                "tool_name": tool_name,
                "result": result.get("result"),
                "output": result.get("output"),
                "execution_time": result["execution_time"],
                "timestamp": datetime.utcnow().isoformat(),
            }
        except ValidationError as e:
            raise AgentError(
                error_type=ErrorType.VALIDATION_ERROR,
                message=f"Custom tool validation failed: {e.message}",
                context={"tool_name": tool_name},
            )
        except TimeoutError as e:
            raise AgentError(
                error_type=ErrorType.EXECUTION_TIMEOUT,
                message=f"Custom tool timed out: {e.message}",
                context={"tool_name": tool_name},
            )
        except ExecutionError as e:
            raise AgentError(
                error_type=ErrorType.EXECUTION_ERROR,
                message=f"Custom tool execution failed: {e.message}",
                context={"tool_name": tool_name},
            )

    async def get_available_tools(self) -> Dict[str, List[str]]:
        """Get list of available tools (built-in and custom).

        Returns:
            Dict with 'builtin' and 'custom' keys containing tool lists
        """
        await self.load_custom_tools()

        return {
            "builtin": list(BUILTIN_TOOLS.keys()),
            "custom": list(self.custom_tools.keys()),
        }


async def tools_agent(state: AgentState) -> AgentState:
    """LangGraph node for the tools agent.

    Executes the appropriate tool based on the current plan step.

    Args:
        state: Current agent state

    Returns:
        Updated state with tool execution results
    """
    db_session = state.get("db_session")

    if not db_session:
        from app.db.session import get_db_session

        async with get_db_session() as session:
            agent = ToolsAgent(session)
            return await _run_tools_agent(agent, state)

    agent = ToolsAgent(db_session)
    return await _run_tools_agent(agent, state)


async def _run_tools_agent(agent: ToolsAgent, state: AgentState) -> AgentState:
    """Run the tools agent logic.

    Args:
        agent: Initialized tools agent
        state: Current agent state

    Returns:
        Updated state
    """
    current_plan = state.get("current_plan", [])
    active_step = state.get("active_step", 0)

    if active_step >= len(current_plan):
        state["tools_output"] = {
            "success": False,
            "error": "No active step to execute",
        }
        return state

    step = current_plan[active_step]
    step_type = step.get("type") or ""
    arguments = step.get("arguments", {})
    custom_tool_name = step.get("custom_tool_name")

    logger.info(f"Executing tool step: {step_type} with args: {arguments}")

    try:
        result = await agent.execute_tool(
            step_type=step_type,
            arguments=arguments,
            custom_tool_name=custom_tool_name,
        )

        state["tools_output"] = result
        state["previous_step_output"] = result

    except AgentError as e:
        logger.error(f"Tools agent error: {e}")
        state["tools_output"] = {
            "success": False,
            "error": e.message,
            "error_type": e.error_type.value if e.error_type else None,
        }
        state["previous_step_output"] = state["tools_output"]
        state["error_log"] = state.get("error_log", []) + [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "agent": "tools",
                "error": e.message,
                "error_type": e.error_type.value if e.error_type else None,
            }
        ]

    return state
