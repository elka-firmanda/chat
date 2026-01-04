"""
Planner Agent

Creates and modifies step-by-step execution plans for the master agent.
Uses LLM to generate structured plans based on user queries.
"""

from typing import Dict, List, Any, Optional
import json
import logging

from .memory import AsyncWorkingMemory

logger = logging.getLogger(__name__)


class StepType:
    """Plan step types."""

    RESEARCH = "research"
    CODE = "code"
    DATABASE = "database"
    CALCULATE = "calculate"
    CHART = "chart"
    THINK = "think"
    REVIEW = "review"


# System prompt for the planner agent
PLANNER_SYSTEM_PROMPT = """You are a planning specialist for a multi-agent AI system. Your job is to create step-by-step execution plans that break down complex user queries into manageable steps.

For each plan, you must:
1. Analyze the user's query to understand what information or actions are needed
2. Break it down into discrete steps with clear descriptions
3. Assign the appropriate agent type to each step (research, code, database, calculate, chart, think, review)
4. Specify the expected output of each step

Step types and their purposes:
- research: Find and analyze information from web sources
- code: Write and execute Python code
- database: Query a data warehouse for structured data
- calculate: Perform mathematical calculations
- chart: Generate visualizations
- think: Analyze and reason about the problem
- review: Synthesize findings and produce final answer

Always start with understanding the request, then plan the necessary steps in logical order.
Steps that depend on previous results should come later in the plan.

Return your plan as a JSON array of steps with this format:
```json
[
  {
    "step_number": 1,
    "type": "think",
    "description": "Analyze the user's question about X",
    "agent": "master",
    "expected_output": "Clear understanding of what's needed"
  },
  {
    "step_number": 2,
    "type": "research",
    "description": "Find information about X",
    "agent": "researcher",
    "expected_output": "List of relevant sources and key findings"
  }
]
```

For re-planning (when previous plan needs modification):
- Review the previous plan and any new findings
- Keep steps that are still valid
- Add new steps if needed based on new information
- Modify step descriptions to reflect new understanding
- Clearly mark any steps that should be skipped
"""


class Planner:
    """
    Planner agent that generates and modifies execution plans.

    Integrates with LLM for plan generation.
    """

    def __init__(self, llm_provider=None):
        """
        Initialize the planner.

        Args:
            llm_provider: Optional LLM provider for generating plans.
                         If None, uses rule-based planning.
        """
        self.llm = llm_provider
        self.system_prompt = PLANNER_SYSTEM_PROMPT

    async def create_plan(
        self,
        user_message: str,
        session_id: str,
        deep_search: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Create an initial execution plan.

        Args:
            user_message: The user's query
            session_id: Session identifier
            deep_search: Whether deep search mode is enabled

        Returns:
            List of step dictionaries
        """
        if self.llm:
            return await self._generate_plan_with_llm(user_message, deep_search)
        return self._create_default_plan(user_message, deep_search)

    async def replan(
        self,
        user_message: str,
        previous_plan: List[Dict[str, Any]],
        findings: Dict[str, Any],
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Create a modified plan based on new findings.

        Args:
            user_message: Original user query
            previous_plan: The previous plan that needs modification
            findings: New information from subagents
            session_id: Session identifier

        Returns:
            Modified plan with version incremented
        """
        if self.llm:
            return await self._replan_with_llm(user_message, previous_plan, findings)
        return self._create_replan_default(previous_plan, findings)

    async def _generate_plan_with_llm(
        self,
        user_message: str,
        deep_search: bool,
    ) -> List[Dict[str, Any]]:
        """Generate plan using LLM."""
        if not self.llm:
            return self._create_default_plan(user_message, deep_search)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": f"Create a {'detailed ' if deep_search else ''}plan for: {user_message}",
            },
        ]

        try:
            response = await self.llm.complete(
                messages=messages,
                temperature=0.3,
                max_tokens=2000,
            )

            # Parse JSON from response
            return self._parse_plan_response(response.content)
        except Exception as e:
            logger.error(f"LLM plan generation failed: {e}")
            return self._create_default_plan(user_message, deep_search)

    async def _replan_with_llm(
        self,
        user_message: str,
        previous_plan: List[Dict[str, Any]],
        findings: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Re-plan using LLM with previous plan and findings."""
        if not self.llm:
            return self._create_replan_default(previous_plan, findings)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": f"""Re-plan based on new findings.

Original request: {user_message}

Previous plan steps:
{json.dumps(previous_plan, indent=2)}

New findings from subagents:
{json.dumps(findings, indent=2)}

Analyze the findings and create an updated plan. Keep valid steps from the previous plan, add new steps if needed, and mark any steps that should be skipped due to the new information.
""",
            },
        ]

        try:
            response = await self.llm.complete(
                messages=messages,
                temperature=0.4,
                max_tokens=2000,
            )
            return self._parse_plan_response(response.content)
        except Exception as e:
            logger.error(f"LLM replanning failed: {e}")
            return self._create_replan_default(previous_plan, findings)

    def _parse_plan_response(self, content: str) -> List[Dict[str, Any]]:
        """Parse JSON plan from LLM response."""
        try:
            # Try to extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            plan = json.loads(content)

            # Ensure plan is a list
            if isinstance(plan, dict):
                plan = plan.get("steps", plan.get("plan", [plan]))

            # Add step numbers if not present
            for i, step in enumerate(plan):
                if "step_number" not in step:
                    step["step_number"] = i + 1

            return plan
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse plan JSON: {e}")
            return []

    def _create_default_plan(
        self,
        user_message: str,
        deep_search: bool,
    ) -> List[Dict[str, Any]]:
        """Create a simple default plan without LLM."""
        plan = []

        # Always start with thinking
        plan.append(
            {
                "step_number": 1,
                "type": StepType.THINK,
                "description": f"Analyze: {user_message[:100]}...",
                "agent": "master",
                "expected_output": "Understanding of what's needed",
            }
        )

        if deep_search:
            plan.append(
                {
                    "step_number": 2,
                    "type": StepType.RESEARCH,
                    "description": f"Research: {user_message[:100]}...",
                    "agent": "researcher",
                    "expected_output": "Relevant information and sources",
                }
            )

        # Always end with review
        plan.append(
            {
                "step_number": len(plan) + 1,
                "type": StepType.REVIEW,
                "description": "Synthesize and provide answer",
                "agent": "master",
                "expected_output": "Final response to user",
            }
        )

        return plan

    def _create_replan_default(
        self,
        previous_plan: List[Dict[str, Any]],
        findings: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Create a modified plan without LLM."""
        # Keep previous plan and add a review step at the end
        new_plan = [step.copy() for step in previous_plan]

        # Check if findings indicate we need new steps
        if findings.get("requires_replan", False):
            # Add research step if not present
            has_research = any(
                step.get("type") == StepType.RESEARCH for step in new_plan
            )
            if not has_research:
                # Insert research step after thinking
                research_step = {
                    "step_number": 2,
                    "type": StepType.RESEARCH,
                    "description": "Research based on new findings",
                    "agent": "researcher",
                    "expected_output": "Additional information",
                }
                new_plan.insert(1, research_step)

        # Renumber steps
        for i, step in enumerate(new_plan):
            step["step_number"] = i + 1

        return new_plan


# Default planner instance
default_planner = Planner()


async def planner_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planner agent function for LangGraph integration.

    This is the node function that gets called by the graph.

    Args:
        state: AgentState dictionary

    Returns:
        Updated state with planner_output
    """
    session_id = state.get("session_id", "default")
    user_message = state.get("user_message", "")
    deep_search = state.get("deep_search_enabled", False)
    requires_replan = state.get("requires_replan", False)
    current_plan = state.get("current_plan", [])
    findings = state.get("researcher_output", {})

    memory = AsyncWorkingMemory(session_id)
    if state.get("working_memory"):
        await memory.load(state["working_memory"])

    # Add planner thought
    node_id = await memory.add_node(
        agent="planner",
        node_type="thought",
        description="Creating execution plan" if not requires_replan else "Re-planning",
    )

    try:
        if requires_replan and current_plan:
            # Re-plan with findings
            plan = await default_planner.replan(
                user_message=user_message,
                previous_plan=current_plan,
                findings=findings,
                session_id=session_id,
            )
        else:
            # Create initial plan
            plan = await default_planner.create_plan(
                user_message=user_message,
                session_id=session_id,
                deep_search=deep_search,
            )

        # Add plan result node
        plan_node_id = await memory.add_node(
            agent="planner",
            node_type="result",
            description=f"Plan v{state.get('plan_version', 1)}: {len(plan)} steps",
            parent_id=node_id,
            content=plan,
        )

        # Create step nodes
        for step in plan:
            await memory.add_node(
                agent="planner",
                node_type="step",
                description=step.get(
                    "description", f"Step {step.get('step_number', '?')}"
                ),
                parent_id=plan_node_id,
                content=step,
            )

        # Update state
        state["current_plan"] = plan
        state["active_step"] = 0
        state["requires_replan"] = False
        state["planner_output"] = {
            "plan": plan,
            "version": state.get("plan_version", 1),
        }

    except Exception as e:
        logger.error(f"Planner agent error: {e}")
        state["error_log"].append(
            {
                "agent": "planner",
                "error": str(e),
            }
        )

    await memory.update_node(node_id, completed=True, status="completed")
    state["working_memory"] = await memory.to_dict()

    return state
