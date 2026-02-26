"""
Serper.dev Google Search API integration.
"""
import os
import json
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import quote_plus

import requests
from rich.console import Console

from research_agent.core.state import SearchResult
from research_agent.config import config

console = Console(legacy_windows=True)


class SerperSearchTool:
    """
    Advanced Google Search tool using Serper.dev API.
    
    Supports both synchronous and asynchronous search operations.
    """
    
    BASE_URL = "https://google.serper.dev"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Serper search tool.
        
        Args:
            api_key: Serper API key. If not provided, uses environment variable.
        """
        self.api_key = api_key or config.serper_api_key
        if not self.api_key:
            raise ValueError(
                "Serper API key is required. Set SERPER_API_KEY environment variable "
                "or pass api_key to the constructor."
            )
        
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session
    
    def search(
        self, 
        query: str, 
        num_results: int = 10,
        search_type: str = "search",
        **kwargs
    ) -> List[SearchResult]:
        """
        Perform a synchronous Google search.
        
        Args:
            query: Search query string
            num_results: Number of results to return (max 100)
            search_type: Type of search - "search", "images", "news", "places"
            **kwargs: Additional parameters like gl (country), hl (language)
        
        Returns:
            List of SearchResult objects
        """
        url = f"{self.BASE_URL}/{search_type}"
        
        payload = {
            "q": query,
            "num": min(num_results, 100),
            **kwargs
        }
        
        try:
            response = requests.post(
                url, 
                headers=self.headers, 
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            return self._parse_results(data, search_type)
            
        except requests.RequestException as e:
            console.print(f"[red]Search error: {e}[/red]")
            return []
    
    async def search_async(
        self, 
        query: str, 
        num_results: int = 10,
        search_type: str = "search",
        **kwargs
    ) -> List[SearchResult]:
        """
        Perform an asynchronous Google search.
        
        Args:
            query: Search query string
            num_results: Number of results to return
            search_type: Type of search
            **kwargs: Additional parameters
        
        Returns:
            List of SearchResult objects
        """
        url = f"{self.BASE_URL}/{search_type}"
        
        payload = {
            "q": query,
            "num": min(num_results, 100),
            **kwargs
        }
        
        session = await self._get_session()
        
        try:
            async with session.post(url, json=payload, timeout=30) as response:
                response.raise_for_status()
                data = await response.json()
                return self._parse_results(data, search_type)
                
        except aiohttp.ClientError as e:
            console.print(f"[red]Async search error: {e}[/red]")
            return []
    
    async def search_multiple(
        self, 
        queries: List[str], 
        num_results: int = 10,
        **kwargs
    ) -> Dict[str, List[SearchResult]]:
        """
        Search multiple queries concurrently.
        
        Args:
            queries: List of search queries
            num_results: Results per query
            **kwargs: Additional parameters
        
        Returns:
            Dictionary mapping queries to their results
        """
        tasks = [
            self.search_async(query, num_results, **kwargs)
            for query in queries
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            query: result if not isinstance(result, Exception) else []
            for query, result in zip(queries, results)
        }
    
    def _parse_results(
        self, 
        data: Dict[str, Any], 
        search_type: str
    ) -> List[SearchResult]:
        """
        Parse API response into SearchResult objects.
        
        Args:
            data: Raw API response
            search_type: Type of search performed
        
        Returns:
            List of SearchResult objects
        """
        results = []
        position = 1
        
        # Parse organic results
        if "organic" in data:
            for item in data["organic"]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    link=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    position=position,
                    source="google"
                ))
                position += 1
        
        # Parse news results
        if "news" in data:
            for item in data["news"]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    link=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    position=position,
                    source="news"
                ))
                position += 1
        
        # Parse places results
        if "places" in data:
            for item in data["places"]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    link=item.get("website", ""),
                    snippet=f"Rating: {item.get('rating', 'N/A')} - {item.get('address', '')}",
                    position=position,
                    source="places"
                ))
                position += 1
        
        # Parse answer box
        if "answerBox" in data:
            answer = data["answerBox"]
            results.insert(0, SearchResult(
                title="Answer Box",
                link=answer.get("link", ""),
                snippet=answer.get("snippet", answer.get("answer", "")),
                position=0,
                source="answer_box"
            ))
        
        return results
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            asyncio.run(self.close())
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


def get_search_tool() -> SerperSearchTool:
    """Factory function to get a configured search tool."""
    return SerperSearchTool()
