"""
Researcher Agent

Performs deep research using Tavily API and intelligent web scraping.
Detects when findings require re-planning and sets the requires_replan flag.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.tools.tavily import TavilyClient
from app.tools.scraper import WebScraper

from .memory import AsyncWorkingMemory
from .types import AgentType, StepStatus

logger = logging.getLogger(__name__)


class RePlanDetector:
    """Detects when research findings require re-planning."""

    # Indicators that might require re-planning
    REPLAN_INDICATORS = [
        "unexpected",
        "contradicts",
        "different from",
        "actually",
        "however",
        "but more importantly",
        "this changes",
        "suggests that",
        "indicates that",
        "research shows",
        "studies have found",
        "new discovery",
        "recently discovered",
        "breakthrough",
        "paradigm shift",
    ]

    def __init__(self):
        self.findings_context: List[str] = []

    def analyze_findings(
        self,
        query: str,
        results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze research findings to determine if re-planning is needed.

        Args:
            query: Original search query
            results: Search results and scraped content
            context: Previous context (original plan, etc.)

        Returns:
            Analysis result with requires_replan flag
        """
        # Extract all text content
        all_content = " ".join(
            result.get("content", "") or result.get("snippet", "")
            for result in results
            if result.get("success", True)
        )

        # Check for re-plan indicators
        requires_replan = self._check_replan_indicators(all_content)

        # Check for significant new information
        new_info_score = self._assess_new_information(all_content, query)

        # Check if findings contradict original plan
        contradiction_score = self._check_contradictions(all_content, context)

        # Determine if re-planning is needed
        should_replan = (
            requires_replan or new_info_score > 0.7 or contradiction_score > 0.6
        )

        # Collect key findings for the planner
        key_findings = self._extract_key_findings(results, query)

        return {
            "requires_replan": should_replan,
            "reason": self._get_replan_reason(
                requires_replan, new_info_score, contradiction_score
            ),
            "key_findings": key_findings,
            "new_info_score": new_info_score,
            "contradiction_score": contradiction_score,
        }

    def _check_replan_indicators(self, content: str) -> bool:
        """Check if content contains re-plan indicators."""
        content_lower = content.lower()
        for indicator in self.REPLAN_INDICATORS:
            if indicator.lower() in content_lower:
                logger.debug(f"Found re-plan indicator: {indicator}")
                return True
        return False

    def _assess_new_information(self, content: str, query: str) -> float:
        """Assess how much new information is in the content (0-1)."""
        # Simple heuristic: check for specific, factual statements
        # In production, this would use the LLM
        score = 0.0

        # Check for quantitative information
        if any(char.isdigit() for char in content):
            score += 0.2

        # Check for recent dates (suggests current information)
        import re

        years = re.findall(r"20[1-2]\d", content)
        if years:
            score += 0.2

        # Check for specific named entities (suggests detailed info)
        if len(content.split()) > 100:
            score += 0.2

        # Check for comparative language
        if any(
            word in content.lower()
            for word in ["compared to", "versus", "more than", "less than"]
        ):
            score += 0.2

        return min(score, 1.0)

    def _check_contradictions(
        self, content: str, context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Check if findings contradict original plan assumptions."""
        if not context or not context.get("original_plan"):
            return 0.0

        # In production, this would use semantic similarity
        # For now, return 0 (no contradiction detected)
        return 0.0

    def _extract_key_findings(
        self, results: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """Extract key findings from results for the planner."""
        key_findings = []
        for result in results:
            if not result.get("success", True):
                continue

            # Extract first few sentences as key finding
            content = result.get("content", "")
            if content:
                sentences = content.split(". ")[:2]
                finding = {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "summary": ". ".join(sentences) + ".",
                    "relevance_score": result.get("score", 0.5),
                }
                key_findings.append(finding)

        return key_findings

    def _get_replan_reason(
        self,
        has_indicators: bool,
        new_info_score: float,
        contradiction_score: float,
    ) -> Optional[str]:
        """Get a human-readable reason for re-planning decision."""
        if has_indicators:
            return "Research found unexpected or significant new information"
        if new_info_score > 0.7:
            return "Research revealed substantial new information that may change the approach"
        if contradiction_score > 0.6:
            return "Research findings contradict original plan assumptions"
        return None


class ResearcherAgent:
    """Researcher agent for deep research tasks."""

    def __init__(
        self,
        tavily_api_key: Optional[str] = None,
        max_urls_to_scrape: int = 5,
        scraping_timeout: int = 600,
    ):
        self.tavily_client = TavilyClient(tavily_api_key)
        self.web_scraper = WebScraper(timeout=scraping_timeout)
        self.replan_detector = RePlanDetector()
        self.max_urls_to_scrape = max_urls_to_scrape

    async def research(
        self,
        query: str,
        session_id: str,
        deep_search: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform research on a query.

        Args:
            query: Research query
            session_id: Session identifier
            deep_search: Whether to use deep search mode
            context: Previous context (original plan, etc.)

        Returns:
            Research output with requires_replan flag
        """
        # Get working memory
        memory = AsyncWorkingMemory(session_id)
        if context and context.get("working_memory"):
            await memory.load(context["working_memory"])

        # Add researcher thought
        node_id = await memory.add_node(
            agent=AgentType.RESEARCHER.value,
            node_type="thought",
            description=f"Researching: {query[:100]}...",
        )

        try:
            # Step 1: Search with Tavily
            search_results = await self.tavily_client.search(
                query=query,
                max_results=self.max_urls_to_scrape,
            )

            # Step 2: Select top URLs for scraping
            urls_to_scrape = self._select_urls_for_scraping(search_results)

            # Step 3: Scrape URLs in parallel
            scraped_content = await self.web_scraper.scrape_urls(urls_to_scrape)

            # Step 4: Analyze findings for re-planning needs
            all_results = search_results.get("results", []) + scraped_content
            analysis = self.replan_detector.analyze_findings(
                query=query,
                results=all_results,
                context=context,
            )

            # Build comprehensive output
            output = {
                "query": query,
                "search_results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", "")[:500],
                        "score": r.get("score", 0),
                    }
                    for r in search_results.get("results", [])
                ],
                "scraped_content": [
                    {
                        "url": r.get("url", ""),
                        "title": r.get("title", ""),
                        "word_count": r.get("word_count", 0),
                        "content_preview": r.get("content", "")[:500],
                    }
                    for r in scraped_content
                    if r.get("success", True)
                ],
                "sources": [r.get("url") for r in search_results.get("results", [])],
                "findings": analysis["key_findings"],
                "requires_replan": analysis["requires_replan"],
                "replan_reason": analysis["reason"],
                "research_summary": self._summarize_research(
                    search_results, scraped_content, query
                ),
                "research_timestamp": datetime.utcnow().isoformat(),
            }

            # Add result node
            await memory.add_node(
                agent=AgentType.RESEARCHER.value,
                node_type="result",
                description=f"Research complete: {len(search_results.get('results', []))} sources found",
                parent_id=node_id,
                content={
                    "sources_found": len(search_results.get("results", [])),
                    "requires_replan": output["requires_replan"],
                },
            )

            logger.info(
                f"Research completed for '{query}': requires_replan={output['requires_replan']}"
            )

            return output

        except Exception as e:
            logger.error(f"Research failed: {e}")
            error_output = {
                "query": query,
                "error": str(e),
                "requires_replan": False,
                "findings": [],
                "sources": [],
            }

            await memory.add_node(
                agent=AgentType.RESEARCHER.value,
                node_type="error",
                description=f"Research failed: {str(e)[:100]}",
                parent_id=node_id,
                content={"error": str(e)},
            )

            return error_output

    def _select_urls_for_scraping(self, search_results: Dict[str, Any]) -> List[str]:
        """Select top URLs for scraping based on relevance scores."""
        results = search_results.get("results", [])
        if not results:
            return []

        # Sort by score and take top N
        sorted_results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
        urls = [r.get("url") for r in sorted_results[: self.max_urls_to_scrape]]

        # Filter out invalid URLs
        valid_urls = []
        for url in urls:
            try:
                parsed = urlparse(url)
                if parsed.scheme in ("http", "https") and parsed.netloc:
                    valid_urls.append(url)
            except Exception:
                continue

        return valid_urls

    def _summarize_research(
        self,
        search_results: Dict[str, Any],
        scraped_content: List[Dict[str, Any]],
        query: str,
    ) -> str:
        """Generate a summary of the research."""
        source_count = len(search_results.get("results", []))
        scraped_count = len([c for c in scraped_content if c.get("success", True)])

        return (
            f"Research on '{query}' found {source_count} sources. "
            f"Successfully scraped {scraped_count} pages for detailed content."
        )


# Default researcher agent instance
default_researcher = ResearcherAgent()


async def researcher_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Researcher agent function for LangGraph integration.

    This is the node function that gets called by the graph.

    Args:
        state: AgentState dictionary

    Returns:
        Updated state with researcher_output
    """
    session_id = state.get("session_id", "default")
    current_step = state.get("current_plan", [])[state.get("active_step", 0)]
    query = current_step.get("query", state["user_message"])

    # Get context from state
    context = {
        "original_plan": state.get("current_plan", []),
        "working_memory": state.get("working_memory", {}),
    }

    # Run research
    research_output = await default_researcher.research(
        query=query,
        session_id=session_id,
        deep_search=state.get("deep_search_enabled", False),
        context=context,
    )

    # Update state
    state["researcher_output"] = {
        "query": research_output.get("query", query),
        "results": research_output.get("search_results", []),
        "scraped_content": research_output.get("scraped_content", []),
        "findings": research_output.get("findings", []),
        "sources": research_output.get("sources", []),
        "summary": research_output.get("research_summary", ""),
        "requires_replan": research_output.get("requires_replan", False),
        "replan_reason": research_output.get("replan_reason"),
        "research_timestamp": research_output.get("research_timestamp"),
    }

    # Also update working memory with research result
    if state.get("working_memory"):
        memory = AsyncWorkingMemory(session_id)
        await memory.load(state["working_memory"])

        # Add research result node
        result_node_id = await memory.add_node(
            agent=AgentType.RESEARCHER.value,
            node_type="result",
            description=f"Research findings: {len(research_output.get('findings', []))} key findings",
            content={
                "requires_replan": research_output.get("requires_replan", False),
                "findings_count": len(research_output.get("findings", [])),
                "sources_count": len(research_output.get("sources", [])),
            },
        )

        state["working_memory"] = await memory.to_dict()

    return state
