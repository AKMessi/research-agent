"""
Browserbase Search API integration.
"""
from typing import Any, Dict, List, Optional

import aiohttp
import requests

from research_agent.config import config
from research_agent.core.state import SearchResult


class BrowserbaseSearchTool:
    """Search the web with the Browserbase Search API."""

    BASE_URL = "https://api.browserbase.com/v1/search"
    MAX_RESULTS = 25

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.browserbase_api_key
        if not self.api_key:
            raise ValueError(
                "Browserbase API key is required. Set BROWSERBASE_API_KEY "
                "environment variable or pass api_key to the constructor."
            )

        self.headers = {
            "X-BB-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session

    def search(self, query: str, num_results: int = 10, **kwargs) -> List[SearchResult]:
        """Perform a synchronous web search."""
        payload = {
            "query": query,
            "numResults": min(num_results, self.MAX_RESULTS),
            **kwargs,
        }

        response = requests.post(
            self.BASE_URL,
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return self._parse_results(response.json())

    async def search_async(
        self,
        query: str,
        num_results: int = 10,
        **kwargs,
    ) -> List[SearchResult]:
        """Perform an asynchronous web search."""
        payload = {
            "query": query,
            "numResults": min(num_results, self.MAX_RESULTS),
            **kwargs,
        }

        session = await self._get_session()
        async with session.post(self.BASE_URL, json=payload, timeout=30) as response:
            response.raise_for_status()
            data = await response.json()
            return self._parse_results(data)

    def _parse_results(self, data: Dict[str, Any]) -> List[SearchResult]:
        """Parse Browserbase search results into SearchResult objects."""
        raw_results = self._extract_result_items(data)
        results: List[SearchResult] = []

        for position, item in enumerate(raw_results, start=1):
            title = item.get("title") or item.get("name") or ""
            link = item.get("url") or item.get("link") or item.get("href") or ""
            snippet = self._build_snippet(item)

            if not any([title, link, snippet]):
                continue

            results.append(
                SearchResult(
                    title=title,
                    link=link,
                    snippet=snippet,
                    position=position,
                    source="browserbase",
                )
            )

        return results

    def _build_snippet(self, item: Dict[str, Any]) -> str:
        """Build the best available snippet from Browserbase result fields."""
        snippet = (
            item.get("snippet")
            or item.get("description")
            or item.get("text")
            or item.get("content")
            or ""
        )

        if snippet:
            return snippet

        metadata_parts = []
        if item.get("author"):
            metadata_parts.append(f"Author: {item['author']}")
        if item.get("publishedDate"):
            metadata_parts.append(f"Published: {item['publishedDate'][:10]}")

        return " | ".join(metadata_parts)

    def _extract_result_items(self, data: Any) -> List[Dict[str, Any]]:
        """Handle a few common API response layouts defensively."""
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]

        if not isinstance(data, dict):
            return []

        candidates = [
            data.get("results"),
            data.get("data"),
            data.get("organic"),
            data.get("web"),
        ]

        for candidate in candidates:
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
            if isinstance(candidate, dict):
                nested_results = candidate.get("results")
                if isinstance(nested_results, list):
                    return [item for item in nested_results if isinstance(item, dict)]

        return []

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
