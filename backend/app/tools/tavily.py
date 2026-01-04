"""
Tavily Search Client

Client for the Tavily search API, providing intelligent search capabilities
with support for raw content extraction.
"""

import logging
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


class TavilyClient:
    """Client for Tavily search API."""

    def __init__(
        self, api_key: Optional[str] = None, base_url: str = "https://api.tavily.com"
    ):
        """
        Initialize the Tavily client.

        Args:
            api_key: Tavily API key (optional, will use mock results if not provided)
            base_url: Base URL for the Tavily API
        """
        self.api_key = api_key
        self.base_url = base_url

    async def search(
        self,
        query: str,
        max_results: int = 5,
        include_raw_content: bool = False,
    ) -> Dict[str, Any]:
        """
        Search Tavily for relevant results.

        Args:
            query: Search query
            max_results: Maximum number of results (default: 5)
            include_raw_content: Whether to include raw content (default: False)

        Returns:
            Search results dictionary with query, results, and follow_up_questions
        """
        if not self.api_key:
            logger.warning("Tavily API key not set, returning mock results")
            return self._mock_search(query, max_results)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "query": query,
                        "max_results": max_results,
                        "include_raw_content": include_raw_content,
                    },
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return self._mock_search(query, max_results)

    async def get_search_context(
        self,
        query: str,
        max_results: int = 5,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        Get search results with extracted context.

        Args:
            query: Search query
            max_results: Maximum number of results (default: 5)
            max_tokens: Maximum tokens for context (default: 4000)

        Returns:
            Search context results
        """
        if not self.api_key:
            return self._mock_search(query, max_results)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "query": query,
                        "max_results": max_results,
                        "include_raw_content": True,
                    },
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Tavily search context failed: {e}")
            return self._mock_search(query, max_results)

    def _mock_search(self, query: str, max_results: int) -> Dict[str, Any]:
        """Return mock search results for testing when API key is not set."""
        return {
            "query": query,
            "results": [
                {
                    "title": f"Result {i + 1} for {query}",
                    "url": f"https://example.com/result{i + 1}",
                    "content": f"Mock content for result {i + 1} about {query}",
                    "score": 0.9 - (i * 0.1),
                }
                for i in range(min(max_results, 5))
            ],
            "follow_up_questions": [],
        }


default_tavily_client = TavilyClient()


async def tavily_search(
    query: str,
    api_key: Optional[str] = None,
    max_results: int = 5,
    include_raw_content: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to perform a Tavily search.

    Args:
        query: Search query
        api_key: Tavily API key (optional)
        max_results: Maximum number of results (default: 5)
        include_raw_content: Whether to include raw content (default: False)

    Returns:
        Search results dictionary
    """
    client = TavilyClient(api_key=api_key)
    return await client.search(
        query=query,
        max_results=max_results,
        include_raw_content=include_raw_content,
    )
