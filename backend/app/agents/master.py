"""Master agent orchestrator using LangGraph."""

import json
from collections.abc import AsyncIterator
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.base import BaseAgent
from app.agents.planner import Planner, get_planner_llm_provider
from app.agents.researcher import ResearcherAgent
from app.agents.tools import ToolsAgent
from app.config.config_manager import config_manager, get_config
from app.models.chat import PlanStep, PlanStepStatus
from app.services.datetime_service import DateTimeService

MASTER_SYSTEM_PROMPT = """You are an advanced AI orchestrator that coordinates specialized agents to deliver comprehensive, accurate, and actionable responses.

## Core Identity
You are the central intelligence hub of a multi-agent system. Your role is to understand user intent, determine the best approach, and either respond directly or coordinate specialized agents for complex tasks.

## Operational Modes

### Direct Response Mode (Simple Queries)
For straightforward questions, factual queries, or conversational exchanges:
- Respond immediately with clear, accurate information
- Be concise yet thorough
- Cite your knowledge boundaries when uncertain

### Deep Search Mode (Complex Queries)
When activated, you coordinate multiple specialized agents:
- **Planner Agent**: Breaks complex tasks into actionable steps
- **Researcher Agent**: Searches the web, scrapes content, synthesizes findings
- **Database Agent**: Queries configured databases for internal data analysis
- **Tools Agent**: Executes utilities (datetime, calculations, formatting)

## Response Guidelines

### Quality Standards
1. **Accuracy First**: Never fabricate information. Clearly distinguish facts from inferences
2. **Source Attribution**: Always cite sources when presenting research findings
3. **Structured Output**: Use clear formatting, headers, and bullet points for readability
4. **Completeness**: Address all aspects of the user's query
5. **Actionability**: Provide practical, implementable recommendations when applicable

### Synthesis Principles
When integrating information from multiple agents:
1. Identify and resolve any contradictions between sources
2. Prioritize recent and authoritative sources
3. Highlight key insights and patterns across data
4. Acknowledge gaps, limitations, or areas of uncertainty
5. Provide a coherent narrative, not just a data dump

### Communication Style
- Be professional yet approachable
- Adapt tone to match the query complexity
- Use technical language appropriately based on context
- Be direct—avoid unnecessary hedging or filler phrases

## Context Awareness
You have access to:
- Current date and time (provided in each query)
- Configured database connections for data analysis
- Web search and content scraping capabilities
- Utility tools for calculations and formatting

Always consider temporal context when answering questions about events, data, or trends."""


class AgentState(TypedDict, total=False):
    query: str
    session_id: str
    plan: list[dict[str, Any]]
    current_step: int
    results: list[dict[str, Any]]
    final_answer: str
    error: str | None


class MasterAgent(BaseAgent):
    def __init__(self, session_id: str = "default"):
        config = get_config()
        agent_config = config.agents.master
        agent_config.system_prompt = MASTER_SYSTEM_PROMPT
        super().__init__("master", agent_config, config_manager)

        self.session_id = session_id

        timezone = config.general.timezone
        if timezone == "auto":
            timezone = "UTC"
        self.datetime_service = DateTimeService(timezone)

        self.planner = Planner(get_planner_llm_provider())

        api_keys = config_manager.get_api_keys()
        tavily_key = api_keys.tavily if api_keys else None
        researcher_config = config.agents.researcher
        self.researcher = ResearcherAgent(
            tavily_api_key=tavily_key,
            max_urls_to_scrape=researcher_config.max_urls_to_scrape,
            scraping_timeout=researcher_config.scraping_timeout,
        )

        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        workflow = StateGraph(AgentState)

        workflow.add_node("plan", self._plan_node)
        workflow.add_node("execute_step", self._execute_step_node)
        workflow.add_node("synthesize", self._synthesize_node)

        workflow.set_entry_point("plan")
        workflow.add_edge("plan", "execute_step")
        workflow.add_conditional_edges(
            "execute_step",
            self._should_continue,
            {
                "continue": "execute_step",
                "synthesize": "synthesize",
            },
        )
        workflow.add_edge("synthesize", END)

        return workflow.compile()

    async def _plan_node(self, state: AgentState) -> dict[str, Any]:
        query = state.get("query", "")
        session_id = state.get("session_id", self.session_id)
        plan = await self.planner.create_plan(query, session_id, deep_search=True)
        return {
            "plan": plan,
            "current_step": 0,
            "results": [],
        }

    async def _execute_step_node(self, state: AgentState) -> dict[str, Any]:
        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)
        results = list(state.get("results", []))
        query = state.get("query", "")
        session_id = state.get("session_id", self.session_id)

        if current_step >= len(plan):
            return {}

        step = plan[current_step]
        result = await self._execute_single_step(step, query, results, session_id)

        results.append(
            {
                "step": step.get("description", f"Step {current_step + 1}"),
                "result": result,
                "agent": step.get("agent", "unknown"),
            }
        )

        return {
            "current_step": current_step + 1,
            "results": results,
        }

    def _should_continue(self, state: AgentState) -> str:
        plan = state.get("plan", [])
        current_step = state.get("current_step", 0)

        if current_step < len(plan):
            return "continue"
        return "synthesize"

    async def _synthesize_node(self, state: AgentState) -> dict[str, Any]:
        query = state.get("query", "")
        results = state.get("results", [])

        final_answer = await self.synthesize_response(query, results)

        return {"final_answer": final_answer}

    async def _execute_single_step(
        self,
        step: dict[str, Any],
        query: str,
        previous_results: list[dict[str, Any]],
        session_id: str,
    ) -> str:
        agent_name = step.get("agent", "researcher")
        step_type = step.get("type", "research")
        description = step.get("description", "")

        try:
            context = ""
            if previous_results:
                context_parts = []
                for i, result in enumerate(previous_results, 1):
                    context_parts.append(
                        f"Step {i} ({result.get('agent', 'unknown')}): {result.get('result', '')[:1000]}"
                    )
                context = "\n\n".join(context_parts)

            if agent_name == "researcher" or step_type == "research":
                research_result = await self.researcher.research(
                    query=f"{description}\n\nOriginal query: {query}",
                    session_id=session_id,
                    deep_search=True,
                    context={"previous_results": context} if context else None,
                )
                return research_result.get(
                    "research_summary", research_result.get("summary", "No results")
                )

            elif agent_name == "master" or step_type in ("think", "review"):
                return await self.synthesize_response(query, previous_results)

            return f"Agent type '{agent_name}' not yet implemented for: {description}"

        except Exception as e:
            return f"Error executing step: {str(e)}"

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        query = input_data.get("query", "")
        deep_search = input_data.get("deep_search", False)
        session_id = input_data.get("session_id", self.session_id)

        if deep_search:
            initial_state: AgentState = {
                "query": query,
                "session_id": session_id,
                "plan": [],
                "current_step": 0,
                "results": [],
                "final_answer": "",
                "error": None,
            }

            final_state = await self.graph.ainvoke(initial_state)

            plan_steps = []
            for i, step in enumerate(final_state.get("plan", []), 1):
                plan_steps.append(
                    PlanStep(
                        step_number=i,
                        description=step.get("description", ""),
                        status=PlanStepStatus.COMPLETED,
                        agent=step.get("agent"),
                    )
                )

            return {
                "query": query,
                "plan": plan_steps,
                "results": final_state.get("results", []),
                "answer": final_state.get("final_answer", ""),
            }
        else:
            answer = await self.chat(query)
            return {
                "query": query,
                "answer": answer,
            }

    async def chat(
        self,
        message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        datetime_context = self.datetime_service.get_context_string()
        enhanced_message = f"{datetime_context}\n\nUser query: {message}"
        return await self.llm_service.chat(enhanced_message, history)

    async def synthesize_response(
        self,
        query: str,
        results: list[dict[str, Any]],
    ) -> str:
        if not results:
            return await self.chat(query)

        context_parts = [
            f"Original query: {query}",
            f"\nCurrent datetime: {self.datetime_service.get_context_string()}",
            "\nResearch results from executed steps:",
        ]

        for i, result in enumerate(results, 1):
            agent = result.get("agent", "unknown")
            step_desc = result.get("step", "")
            step_result = result.get("result", "")
            context_parts.append(
                f"\n--- Step {i} ({agent}): {step_desc} ---\n{step_result}"
            )

        full_context = "\n".join(context_parts)

        synthesis_prompt = f"""Based on the following research and gathered information, provide a comprehensive, well-organized response to the user's query.

{full_context}

Provide a clear, accurate, and helpful response that:
1. Directly addresses the user's question
2. Integrates information from all sources
3. Cites sources where appropriate
4. Acknowledges any limitations or uncertainties
5. Is well-structured and easy to read"""

        return await self.llm_service.chat(synthesis_prompt)

    async def chat_stream(
        self,
        message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[str]:
        datetime_context = self.datetime_service.get_context_string()
        enhanced_message = f"{datetime_context}\n\nUser query: {message}"
        async for token in self.llm_service.chat_stream(enhanced_message, history):
            yield token

    async def synthesize_response_stream(
        self,
        query: str,
        results: list[dict[str, Any]],
    ) -> AsyncIterator[str]:
        if not results:
            async for token in self.chat_stream(query):
                yield token
            return

        context_parts = [
            f"Original query: {query}",
            f"\nCurrent datetime: {self.datetime_service.get_context_string()}",
            "\nResearch results from executed steps:",
        ]

        for i, result in enumerate(results, 1):
            agent = result.get("agent", "unknown")
            step_desc = result.get("step", "")
            step_result = result.get("result", "")
            context_parts.append(
                f"\n--- Step {i} ({agent}): {step_desc} ---\n{step_result}"
            )

        full_context = "\n".join(context_parts)

        synthesis_prompt = f"""Based on the following research and gathered information, provide a comprehensive, well-organized response to the user's query.

{full_context}

Provide a clear, accurate, and helpful response that:
1. Directly addresses the user's question
2. Integrates information from all sources
3. Cites sources where appropriate
4. Acknowledges any limitations or uncertainties
5. Is well-structured and easy to read"""

        async for token in self.llm_service.chat_stream(synthesis_prompt):
            yield token

    async def generate_title(self, query: str, response: str) -> str:
        prompt = f"""Generate a very short title (3-6 words, max 50 characters) for this conversation.
The title should capture the main topic.

User asked: {query[:200]}

Reply with ONLY the title, no quotes, no explanation."""

        try:
            title = await self.llm_service.chat(prompt)
            return title.strip()[:50]
        except Exception:
            return query[:50]


async def run_agent_workflow(
    user_message: str,
    session_id: str,
    deep_search: bool = False,
    user_timezone: str = "UTC",
) -> dict[str, Any]:
    master = MasterAgent(session_id=session_id)
    return await master.execute(
        {
            "query": user_message,
            "deep_search": deep_search,
            "session_id": session_id,
        }
    )


async def run_agent_workflow_with_streaming(
    user_message: str,
    session_id: str,
    deep_search: bool = False,
    user_timezone: str = "UTC",
) -> dict[str, Any]:
    return await run_agent_workflow(
        user_message, session_id, deep_search, user_timezone
    )


master_agent = None


def create_agent_graph() -> Any:
    return MasterAgent()._build_graph()


app = None
