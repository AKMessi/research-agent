"""
Primary web search provider with automatic fallback.
"""
from typing import List, Optional

from rich.console import Console

from research_agent.config import config
from research_agent.core.state import SearchResult
from research_agent.tools.browserbase_search import BrowserbaseSearchTool
from research_agent.tools.serper_search import SerperSearchTool

console = Console(legacy_windows=True)


class WebSearchTool:
    """Use Browserbase first and fall back to Serper if Browserbase fails."""

    def __init__(
        self,
        browserbase_api_key: Optional[str] = None,
        serper_api_key: Optional[str] = None,
    ):
        self.primary: Optional[BrowserbaseSearchTool] = None
        self.fallback: Optional[SerperSearchTool] = None

        if browserbase_api_key or config.browserbase_api_key:
            self.primary = BrowserbaseSearchTool(browserbase_api_key)

        if serper_api_key or config.serper_api_key:
            self.fallback = SerperSearchTool(serper_api_key)

        if not self.primary and not self.fallback:
            raise ValueError(
                "At least one search provider must be configured. "
                "Set BROWSERBASE_API_KEY or SERPER_API_KEY."
            )

    def search(self, query: str, num_results: int = 10, **kwargs) -> List[SearchResult]:
        """Search with Browserbase first, then Serper on provider failure."""
        if self.primary:
            try:
                return self.primary.search(query, num_results=num_results, **kwargs)
            except Exception as exc:
                if self.fallback:
                    console.print(
                        f"[yellow]Browserbase search failed, falling back to Serper: {exc}[/yellow]"
                    )
                else:
                    raise

        if self.fallback:
            return self.fallback.search(query, num_results=num_results, **kwargs)

        return []

    async def search_async(
        self,
        query: str,
        num_results: int = 10,
        **kwargs,
    ) -> List[SearchResult]:
        """Async search with Browserbase first, then Serper on provider failure."""
        if self.primary:
            try:
                return await self.primary.search_async(query, num_results=num_results, **kwargs)
            except Exception as exc:
                if self.fallback:
                    console.print(
                        f"[yellow]Browserbase search failed, falling back to Serper: {exc}[/yellow]"
                    )
                else:
                    raise

        if self.fallback:
            return await self.fallback.search_async(query, num_results=num_results, **kwargs)

        return []

    async def close(self):
        """Close provider sessions."""
        if self.primary:
            await self.primary.close()
        if self.fallback:
            await self.fallback.close()


def get_search_tool() -> WebSearchTool:
    """Factory function to get the configured search tool."""
    return WebSearchTool()
