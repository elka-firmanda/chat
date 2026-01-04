"""
Parallel Web Scraper

A robust web scraper that fetches and parses multiple URLs in parallel
with proper error handling and BeautifulSoup4 for HTML parsing.
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebScraper:
    """Parallel web scraper using BeautifulSoup."""

    def __init__(
        self,
        timeout: int = 30,
        max_concurrent: int = 5,
        max_content_length: int = 10000,
    ):
        """
        Initialize the web scraper.

        Args:
            timeout: Timeout per URL in seconds (default: 30)
            max_concurrent: Maximum concurrent requests (default: 5)
            max_content_length: Maximum content length to extract (default: 10000)
        """
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.max_content_length = max_content_length

    async def scrape_urls(
        self, urls: List[str], urls_to_scrape: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs in parallel with concurrency control.

        Args:
            urls: List of URLs to scrape
            urls_to_scrape: Optional specific URLs to scrape (if provided, only these are scraped)

        Returns:
            List of scraped content dictionaries with url, title, content, word_count, success
        """
        if not urls:
            return []

        if urls_to_scrape is not None:
            urls_to_scrape_set = set(urls_to_scrape)
            urls = [url for url in urls if url in urls_to_scrape_set]

        if not urls:
            return []

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = [
                self._scrape_with_semaphore(semaphore, client, url) for url in urls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            return [
                r
                for r in results
                if isinstance(r, dict) and not isinstance(r, Exception)
            ]

    async def _scrape_with_semaphore(
        self, semaphore: asyncio.Semaphore, client: httpx.AsyncClient, url: str
    ) -> Dict[str, Any]:
        """Scrape a single URL with semaphore control."""
        async with semaphore:
            return await self._scrape_single(client, url)

    async def _scrape_single(
        self, client: httpx.AsyncClient, url: str
    ) -> Dict[str, Any]:
        """
        Scrape a single URL and extract content.

        Args:
            client: httpx AsyncClient instance
            url: URL to scrape

        Returns:
            Dictionary with url, title, content, word_count, success, and optionally error
        """
        try:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            for comment in soup.find_all(
                string=lambda text: isinstance(text, type(soup.string.__class__))
                and text.startswith("<!--")
            ):
                comment.extract()

            main_content = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", {"class": "content"})
                or soup.find("div", {"class": "post"})
                or soup.body
            )

            if main_content:
                text = main_content.get_text(separator="\n", strip=True)
            else:
                text = ""

            text = self._clean_text(text)

            if len(text) > self.max_content_length:
                text = text[: self.max_content_length] + "... [truncated]"

            title = ""
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            else:
                h1 = soup.find("h1")
                if h1:
                    h1_text = h1.get_text(strip=True)
                    if h1_text:
                        title = h1_text

            word_count = len(text.split()) if text else 0

            return {
                "url": url,
                "title": title or url,
                "content": text,
                "word_count": word_count,
                "success": True,
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error scraping {url}: {e.response.status_code}")
            return {
                "url": url,
                "error": f"HTTP {e.response.status_code}",
                "success": False,
            }
        except httpx.TimeoutException:
            logger.error(f"Timeout scraping {url}")
            return {
                "url": url,
                "error": "Timeout",
                "success": False,
            }
        except httpx.ConnectError as e:
            logger.error(f"Connection error scraping {url}: {e}")
            return {
                "url": url,
                "error": "Connection error",
                "success": False,
            }
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return {
                "url": url,
                "error": str(e),
                "success": False,
            }

    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing extra whitespace and artifacts."""
        if not text:
            return ""

        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        lines = [line.strip() for line in text.split("\n")]
        lines = [line for line in lines if line]

        return "\n".join(lines)

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """Scrape a single URL."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await self._scrape_single(client, url)


default_scraper = WebScraper()


async def scrape_urls(
    urls: List[str],
    timeout: int = 30,
    max_concurrent: int = 5,
) -> List[Dict[str, Any]]:
    """
    Convenience function to scrape multiple URLs.

    Args:
        urls: List of URLs to scrape
        timeout: Timeout per URL in seconds (default: 30)
        max_concurrent: Maximum concurrent requests (default: 5)

    Returns:
        List of scraped content dictionaries
    """
    scraper = WebScraper(timeout=timeout, max_concurrent=max_concurrent)
    return await scraper.scrape_urls(urls)
