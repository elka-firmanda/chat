"""Researcher subagent for web search and scraping."""

from typing import Any

from app.agents.base import BaseAgent
from app.config.config_manager import config_manager, get_config
from app.tools.tavily import TavilyClient
from app.tools.scraper import WebScraper

RESEARCHER_SYSTEM_PROMPT = """You are an expert research agent specialized in gathering, analyzing, and synthesizing information from web sources.

## Core Capabilities
- **Web Search**: Query the Tavily search API for relevant, up-to-date information
- **Content Scraping**: Extract and analyze full content from web pages
- **Synthesis**: Transform raw data into clear, actionable insights

## Research Methodology

### 1. Search Strategy
- Formulate precise search queries targeting the specific information need
- Consider multiple angles and perspectives on the topic
- Prioritize authoritative, recent, and relevant sources

### 2. Source Evaluation
Assess each source for:
- **Authority**: Is the source credible? (official sites, reputable publications, expert authors)
- **Recency**: When was this published? Is it still current?
- **Relevance**: Does it directly address the query?
- **Objectivity**: Is there potential bias?

### 3. Synthesis Standards
When presenting findings:
- **Structure**: Organize by theme or importance, not by source
- **Citations**: Always include [Source: URL] for factual claims
- **Confidence Levels**: Indicate certainty (e.g., "According to multiple sources...", "One study suggests...")
- **Gaps**: Explicitly note what information could NOT be found

## Output Format

### Research Summary Structure
1. **Key Findings**: 3-5 bullet points of the most important discoveries
2. **Detailed Analysis**: Organized discussion of findings with citations
3. **Sources Used**: List of primary sources with URLs
4. **Limitations**: Any gaps, conflicting information, or areas of uncertainty

## Quality Guidelines

### DO:
- Cross-reference claims across multiple sources when possible
- Distinguish between facts, opinions, and speculation
- Provide context for statistics and claims
- Note the date of information when relevant

### DON'T:
- Present information without source attribution
- Ignore contradictory findings
- Overstate certainty on contested topics
- Fabricate or extrapolate beyond what sources support"""


class ResearcherAgent(BaseAgent):
    def __init__(
        self,
        tavily_api_key: str | None = None,
        max_urls_to_scrape: int = 5,
        scraping_timeout: int = 600,
    ):
        config = get_config()
        agent_config = config.agents.researcher
        agent_config.system_prompt = RESEARCHER_SYSTEM_PROMPT
        super().__init__("researcher", agent_config, config_manager)

        if not tavily_api_key:
            api_keys = config_manager.get_api_keys()
            tavily_api_key = api_keys.tavily if api_keys else None

        self.tavily_client = TavilyClient(tavily_api_key)
        self.web_scraper = WebScraper(timeout=scraping_timeout)
        self.max_urls_to_scrape = max_urls_to_scrape

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        query = input_data.get("query", "")
        deep_scrape = input_data.get("deep_scrape", True)
        context = input_data.get("context", "")

        result = await self.research(query, deep_scrape, context)

        return {
            "query": query,
            "summary": result,
            "sources": input_data.get("sources", []),
        }

    async def research(
        self,
        query: str,
        session_id: str = "default",
        deep_search: bool = True,
        context: dict[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        search_results = await self.tavily_client.search(
            query=query,
            max_results=self.max_urls_to_scrape,
        )

        if search_results.get("error"):
            return {
                "error": search_results["error"],
                "research_summary": f"Search failed: {search_results['error']}",
            }

        scraped_content = []
        if deep_search and search_results.get("results"):
            urls = [r.get("url") for r in search_results.get("results", [])][
                : self.max_urls_to_scrape
            ]
            urls = [u for u in urls if u]
            scraped_content = await self.web_scraper.scrape_urls(urls)

        context_parts = []

        if context:
            if isinstance(context, dict):
                prev = context.get("previous_results", "")
                if prev:
                    context_parts.append(f"Previous context:\n{prev}")
            else:
                context_parts.append(f"Previous context:\n{context}")

        if search_results.get("answer"):
            context_parts.append(f"Search summary:\n{search_results['answer']}")

        context_parts.append("Search results:")
        for i, result in enumerate(search_results.get("results", [])[:5], 1):
            context_parts.append(
                f"\n[{i}] {result.get('title', 'No title')}\n"
                f"URL: {result.get('url', '')}\n"
                f"Snippet: {result.get('content', '')[:500]}"
            )

        if scraped_content:
            context_parts.append("\n\nDetailed page content:")
            for item in scraped_content:
                if item.get("success", True) and item.get("content"):
                    context_parts.append(
                        f"\n--- {item.get('title', 'Unknown')} ({item.get('url', '')}) ---\n"
                        f"{item['content'][:3000]}"
                    )

        full_context = "\n".join(context_parts)

        synthesis_prompt = f"""Based on the following research results, provide a comprehensive summary that answers the query.

Query: {query}

Research Data:
{full_context}

Please synthesize these findings into a clear, well-organized response. Include relevant citations with URLs."""

        summary = await self.llm_service.chat(synthesis_prompt)

        return {
            "query": query,
            "research_summary": summary,
            "summary": summary,
            "sources": [r.get("url") for r in search_results.get("results", [])],
            "search_results": search_results.get("results", []),
            "scraped_count": len(
                [c for c in scraped_content if c.get("success", True)]
            ),
        }

    async def search_only(self, query: str) -> dict[str, Any]:
        return await self.tavily_client.search(query)

    async def scrape_url(self, url: str) -> dict[str, Any]:
        results = await self.web_scraper.scrape_urls([url])
        return results[0] if results else {"error": "Failed to scrape"}
