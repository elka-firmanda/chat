"""Planner subagent for creating execution plans."""

import json
import re
from datetime import datetime
from typing import Any

from app.agents.base import BaseAgent
from app.config.config_manager import config_manager, get_config
from app.models.chat import PlanStep, PlanStepStatus

PLANNER_SYSTEM_PROMPT = """You are a strategic planning agent responsible for decomposing complex queries into clear, actionable execution plans.

## Your Role
Analyze user queries and create step-by-step plans that will be executed by specialized agents. Your plans must be precise, efficient, and optimized for the capabilities of each agent.

## Output Format
You MUST output a JSON array of steps. Each step must have:
- "step_number": Sequential integer (1, 2, 3, ...)
- "description": Clear, specific action to perform
- "agent": The agent responsible for this step

```json
[
    {"step_number": 1, "description": "Specific action description", "agent": "agent_name"},
    {"step_number": 2, "description": "Another action", "agent": "agent_name"}
]
```

## Available Agents

### researcher
Use for: External information gathering
- Web search via Tavily API
- Content scraping from websites
- Synthesizing findings from multiple sources
- Current events, news, public information
- Technical documentation, tutorials, guides

### database
Use for: Internal data analysis
- Querying configured databases (PostgreSQL, MySQL, ClickHouse, BigQuery)
- Data aggregation and analysis
- Metrics, KPIs, business intelligence

### tools
Use for: Utility operations
- Current date, time, timezone information
- Mathematical calculations
- Data formatting and transformation

### master
Use for: Final synthesis ONLY
- Combining results from all previous steps
- Creating the final, coherent response
- Always the LAST step in any plan

## Planning Guidelines

### Step Design Principles
1. **Be Specific**: "Search for Q3 2024 revenue trends in the tech sector" NOT "Search for information"
2. **One Focus Per Step**: Each step should accomplish a single, clear objective
3. **Logical Order**: Gather data before analysis, research before synthesis
4. **Minimize Steps**: 3-6 steps is typical. More complex queries may need up to 8
5. **Avoid Redundancy**: Don't repeat similar searches across steps

### Common Patterns

**Research Query:**
1. tools: Get current date for context
2. researcher: Search for main topic
3. researcher: Search for related/comparison data
4. master: Synthesize findings

**Hybrid Query (Internal + External):**
1. tools: Get temporal context
2. database: Query internal data
3. researcher: Find external benchmarks/context
4. master: Combine internal data with external insights

## Critical Rules
- ALWAYS end with a master synthesis step
- Output ONLY the JSON array—no explanations, no markdown outside the JSON"""


class PlannerAgent(BaseAgent):
    def __init__(self):
        config = get_config()
        agent_config = config.agents.planner
        agent_config.system_prompt = PLANNER_SYSTEM_PROMPT
        super().__init__("planner", agent_config, config_manager)

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        query = input_data.get("query", "")
        plan = await self.create_plan(query)
        return {"plan": plan}

    async def create_plan(self, query: str) -> list[PlanStep]:
        current_date = datetime.now().strftime("%A, %B %d, %Y")
        current_year = datetime.now().year

        prompt = f"""Today's date: {current_date} (Year: {current_year})

Create an execution plan for the following query:

{query}"""

        response = await self.llm_service.chat(prompt)
        return self._parse_plan_response(response)

    def _parse_plan_response(self, response: str) -> list[PlanStep]:
        json_match = re.search(r"\[.*\]", response, re.DOTALL)

        if json_match:
            try:
                plan_data = json.loads(json_match.group())

                steps = []
                for item in plan_data:
                    step = PlanStep(
                        step_number=item.get("step_number", len(steps) + 1),
                        description=item.get("description", ""),
                        status=PlanStepStatus.PENDING,
                        agent=item.get("agent", "researcher"),
                    )
                    steps.append(step)

                return steps

            except json.JSONDecodeError:
                pass

        return [
            PlanStep(
                step_number=1,
                description="Research the query",
                status=PlanStepStatus.PENDING,
                agent="researcher",
            ),
            PlanStep(
                step_number=2,
                description="Synthesize findings",
                status=PlanStepStatus.PENDING,
                agent="master",
            ),
        ]

    async def refine_plan(
        self, original_plan: list[PlanStep], feedback: str
    ) -> list[PlanStep]:
        plan_json = json.dumps(
            [
                {
                    "step_number": s.step_number,
                    "description": s.description,
                    "agent": s.agent,
                }
                for s in original_plan
            ],
            indent=2,
        )

        prompt = f"""Current plan:
{plan_json}

Feedback: {feedback}

Please refine the plan based on the feedback. Output the updated plan as a JSON array."""

        response = await self.llm_service.chat(prompt)
        return self._parse_plan_response(response)


class Planner:
    """Legacy Planner class for backward compatibility with MasterAgent."""

    def __init__(self, llm_provider=None):
        self._agent = PlannerAgent()

    async def create_plan(
        self,
        user_message: str,
        session_id: str,
        deep_search: bool = True,
    ) -> list[dict[str, Any]]:
        steps = await self._agent.create_plan(user_message)
        return [
            {
                "step_number": s.step_number,
                "description": s.description,
                "agent": s.agent,
                "type": self._get_step_type(s.agent),
            }
            for s in steps
        ]

    def _get_step_type(self, agent: str | None) -> str:
        type_map = {
            "researcher": "research",
            "database": "database",
            "tools": "tools",
            "master": "review",
        }
        return type_map.get(agent or "researcher", "research")

    async def replan(
        self,
        user_message: str,
        previous_plan: list[dict[str, Any]],
        findings: dict[str, Any],
        session_id: str,
    ) -> list[dict[str, Any]]:
        original_steps = [
            PlanStep(
                step_number=s.get("step_number", i + 1),
                description=s.get("description", ""),
                agent=s.get("agent"),
            )
            for i, s in enumerate(previous_plan)
        ]

        feedback = f"New findings: {json.dumps(findings)}"
        refined = await self._agent.refine_plan(original_steps, feedback)

        return [
            {
                "step_number": s.step_number,
                "description": s.description,
                "agent": s.agent,
                "type": self._get_step_type(s.agent),
            }
            for s in refined
        ]


def get_planner_llm_provider():
    """Legacy function - returns None since PlannerAgent uses LLMService."""
    return None
