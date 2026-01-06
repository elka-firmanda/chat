"""
Planner Agent

Creates and modifies step-by-step execution plans for the master agent.
Uses LLM to generate structured plans based on user queries.
"""

from typing import Dict, List, Any, Optional
import json
import logging
from pydantic import BaseModel, Field, field_validator

from app.config.config_manager import get_config
from app.llm.providers import LLMProviderFactory, BaseLLMProvider
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


class PlanStep(BaseModel):
    """Schema for a single plan step."""

    step_number: int = Field(..., ge=1, description="Step number (1-indexed)")
    type: str = Field(
        ...,
        description="Step type (research, code, database, calculate, chart, think, review)",
    )
    description: str = Field(
        ..., min_length=1, max_length=500, description="Brief description of the step"
    )
    agent: str = Field(..., description="Agent responsible for this step")
    expected_output: str = Field(
        ..., min_length=1, description="Expected output from this step"
    )
    depends_on: Optional[List[int]] = Field(
        default=None, description="Step numbers this step depends on"
    )
    skip: bool = Field(default=False, description="Whether to skip this step")

    @field_validator("type")
    @classmethod
    def validate_step_type(cls, v: str) -> str:
        """Validate step type is one of the allowed types."""
        valid_types = {
            StepType.RESEARCH,
            StepType.CODE,
            StepType.DATABASE,
            StepType.CALCULATE,
            StepType.CHART,
            StepType.THINK,
            StepType.REVIEW,
        }
        if v not in valid_types:
            logger.warning(f"Unknown step type '{v}', allowing but may cause issues")
        return v


class Plan(BaseModel):
    """Schema for a complete execution plan."""

    steps: List[PlanStep] = Field(..., description="List of plan steps")

    @field_validator("steps")
    @classmethod
    def validate_steps_not_empty(cls, v: List[PlanStep]) -> List[PlanStep]:
        """Ensure plan has at least one step."""
        if not v:
            raise ValueError("Plan must have at least one step")
        return v

    @field_validator("steps")
    @classmethod
    def validate_step_numbers(cls, v: List[PlanStep]) -> List[PlanStep]:
        """Ensure step numbers are sequential."""
        step_numbers = [step.step_number for step in v]
        expected = list(range(1, len(v) + 1))
        if step_numbers != expected:
            logger.warning(
                f"Step numbers are not sequential. Expected {expected}, got {step_numbers}. Re-indexing."
            )
            for i, step in enumerate(v):
                step.step_number = i + 1
        return v


class PlanGenerationError(Exception):
    """Raised when plan generation fails."""

    pass


_planner_llm_provider: Optional[BaseLLMProvider] = None


def get_planner_llm_provider() -> BaseLLMProvider:
    """Get or create the LLM provider for the planner agent."""
    global _planner_llm_provider
    if _planner_llm_provider is None:
        config = get_config()
        api_keys: Dict[str, str] = {}
        if config.api_keys.anthropic:
            api_keys["anthropic"] = config.api_keys.anthropic
        if config.api_keys.openai:
            api_keys["openai"] = config.api_keys.openai
        if config.api_keys.openrouter:
            api_keys["openrouter"] = config.api_keys.openrouter
        agent_config = config.agents.planner.model_dump()
        _planner_llm_provider = LLMProviderFactory.from_agent_config(
            agent_config, api_keys
        )
    return _planner_llm_provider


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

IMPORTANT: You must respond with valid JSON that matches this schema:
```json
{
  "steps": [
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
}
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

        Raises:
            PlanGenerationError: If plan generation fails
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

        Raises:
            PlanGenerationError: If replanning fails
        """
        if self.llm:
            return await self._replan_with_llm(user_message, previous_plan, findings)
        return self._create_replan_default(previous_plan, findings)

    async def _generate_plan_with_llm(
        self,
        user_message: str,
        deep_search: bool,
    ) -> List[Dict[str, Any]]:
        """Generate plan using LLM with JSON mode."""
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
                json_mode=True,
            )

            plan_data = self._parse_plan_response(response.content)
            validated_plan = self._validate_plan(plan_data)

            return [step.model_dump() for step in validated_plan.steps]
        except PlanGenerationError as e:
            logger.error(f"Plan validation failed: {e}")
            raise PlanGenerationError(f"Invalid plan structure: {e}")
        except Exception as e:
            logger.error(f"LLM plan generation failed: {e}")
            raise PlanGenerationError(f"Failed to generate plan: {e}")

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

Respond with valid JSON matching this schema:
```json
{{
  "steps": [
    {{
      "step_number": 1,
      "type": "...",
      "description": "...",
      "agent": "...",
      "expected_output": "..."
    }}
  ]
}}
```
""",
            },
        ]

        try:
            response = await self.llm.complete(
                messages=messages,
                temperature=0.4,
                max_tokens=2000,
                json_mode=True,
            )

            plan_data = self._parse_plan_response(response.content)
            validated_plan = self._validate_plan(plan_data)

            return [step.model_dump() for step in validated_plan.steps]
        except PlanGenerationError as e:
            logger.error(f"Replan validation failed: {e}")
            raise PlanGenerationError(f"Invalid replan structure: {e}")
        except Exception as e:
            logger.error(f"LLM replanning failed: {e}")
            raise PlanGenerationError(f"Failed to replan: {e}")

    def _parse_plan_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON plan from LLM response."""
        try:
            content = content.strip()

            if content.startswith("```json"):
                content = content.split("```json")[1].split("```")[0]
            elif content.startswith("```"):
                content = content.split("```")[1].split("```")[0]

            content = content.strip()

            plan_data = json.loads(content)

            if isinstance(plan_data, list):
                plan_data = {"steps": plan_data}

            if "steps" not in plan_data:
                raise PlanGenerationError("Response does not contain 'steps' field")

            return plan_data
        except json.JSONDecodeError as e:
            raise PlanGenerationError(f"Failed to parse JSON response: {e}")
        except PlanGenerationError:
            raise
        except Exception as e:
            raise PlanGenerationError(f"Unexpected error parsing response: {e}")

    def _validate_plan(self, plan_data: Dict[str, Any]) -> Plan:
        """Validate plan data against schema."""
        try:
            return Plan.model_validate(plan_data)
        except Exception as e:
            raise PlanGenerationError(f"Schema validation failed: {e}")

    def _create_default_plan(
        self,
        user_message: str,
        deep_search: bool,
    ) -> List[Dict[str, Any]]:
        """Create a simple default plan without LLM."""
        plan = []

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
        new_plan = [step.copy() for step in previous_plan]

        if findings.get("requires_replan", False):
            has_research = any(
                step.get("type") == StepType.RESEARCH for step in new_plan
            )
            if not has_research:
                research_step = {
                    "step_number": 2,
                    "type": StepType.RESEARCH,
                    "description": "Research based on new findings",
                    "agent": "researcher",
                    "expected_output": "Additional information",
                }
                new_plan.insert(1, research_step)

        for i, step in enumerate(new_plan):
            step["step_number"] = i + 1

        return new_plan


default_planner = Planner(llm_provider=get_planner_llm_provider())


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

    node_id = await memory.add_node(
        agent="planner",
        node_type="thought",
        description="Creating execution plan" if not requires_replan else "Re-planning",
    )

    try:
        if requires_replan and current_plan:
            plan = await default_planner.replan(
                user_message=user_message,
                previous_plan=current_plan,
                findings=findings,
                session_id=session_id,
            )
        else:
            plan = await default_planner.create_plan(
                user_message=user_message,
                session_id=session_id,
                deep_search=deep_search,
            )

        plan_node_id = await memory.add_node(
            agent="planner",
            node_type="result",
            description=f"Plan v{state.get('plan_version', 1)}: {len(plan)} steps",
            parent_id=node_id,
            content=plan,
        )

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

        state["current_plan"] = plan
        state["active_step"] = 0
        state["requires_replan"] = False
        state["planner_output"] = {
            "plan": plan,
            "version": state.get("plan_version", 1),
        }

    except PlanGenerationError as e:
        logger.error(f"Planner agent plan generation error: {e}")
        state["error_log"].append(
            {
                "agent": "planner",
                "error": str(e),
                "error_type": "plan_generation",
            }
        )
        state["planner_output"] = {
            "plan": [],
            "version": state.get("plan_version", 1),
            "error": str(e),
        }

    except Exception as e:
        logger.error(f"Planner agent error: {e}")
        state["error_log"].append(
            {
                "agent": "planner",
                "error": str(e),
            }
        )
        state["planner_output"] = {
            "plan": [],
            "version": state.get("plan_version", 1),
            "error": str(e),
        }

    await memory.update_node(node_id, completed=True, status="completed")
    state["working_memory"] = await memory.to_dict()

    return state
