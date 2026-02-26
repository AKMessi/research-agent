"""
Multi-engine search aggregation (all free tiers).

Combines results from multiple search engines for maximum coverage.
"""
import requests
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import quote_plus
from rich.console import Console

console = Console(legacy_windows=True)


@dataclass
class SearchResult:
    """Unified search result from any engine."""
    title: str
    link: str
    snippet: str
    source_engine: str
    position: int = 0


class DuckDuckGoSearch:
    """DuckDuckGo search (completely free, no API key)."""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search using DuckDuckGo HTML interface."""
        try:
            # DuckDuckGo Lite is simpler to parse
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query, "kl": "us-en"}
            
            response = requests.post(url, data=data, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                results = []
                for i, result in enumerate(soup.find_all('div', class_='result')[:max_results]):
                    title_elem = result.find('a', class_='result__a')
                    snippet_elem = result.find('a', class_='result__snippet')
                    
                    if title_elem and snippet_elem:
                        results.append(SearchResult(
                            title=title_elem.get_text(strip=True),
                            link=title_elem.get('href', ''),
                            snippet=snippet_elem.get_text(strip=True),
                            source_engine="duckduckgo",
                            position=i
                        ))
                
                return results
        except Exception as e:
            console.print(f"[dim]DuckDuckGo error: {e}[/dim]")
        
        return []


class BingSearch:
    """Bing Web Search API (free tier: 1000 queries/month)."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.endpoint = "https://api.bing.microsoft.com/v7.0/search"
    
    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search using Bing API if key available."""
        if not self.api_key:
            return []
        
        try:
            headers = {"Ocp-Apim-Subscription-Key": self.api_key}
            params = {"q": query, "count": max_results, "mkt": "en-US"}
            
            response = requests.get(
                self.endpoint,
                headers=headers,
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for i, item in enumerate(data.get("webPages", {}).get("value", [])[:max_results]):
                    results.append(SearchResult(
                        title=item.get("name", ""),
                        link=item.get("url", ""),
                        snippet=item.get("snippet", ""),
                        source_engine="bing",
                        position=i
                    ))
                
                return results
        except Exception as e:
            console.print(f"[dim]Bing error: {e}[/dim]")
        
        return []


class WikipediaSearch:
    """Wikipedia API (completely free)."""
    
    def __init__(self):
        self.endpoint = "https://en.wikipedia.org/w/api.php"
        self.headers = {
            "User-Agent": "ResearchAgent/1.0 (research@example.com)"
        }
    
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search Wikipedia for knowledge articles."""
        try:
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": max_results
            }
            
            response = requests.get(
                self.endpoint,
                params=params,
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for i, item in enumerate(data.get("query", {}).get("search", [])[:max_results]):
                    page_id = item.get("pageid", "")
                    results.append(SearchResult(
                        title=f"[Wikipedia] {item.get('title', '')}",
                        link=f"https://en.wikipedia.org/?curid={page_id}",
                        snippet=item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", ""),
                        source_engine="wikipedia",
                        position=i
                    ))
                
                return results
        except Exception as e:
            console.print(f"[dim]Wikipedia error: {e}[/dim]")
        
        return []
    
    def get_page_content(self, title: str) -> str:
        """Get full Wikipedia page content."""
        try:
            params = {
                "action": "query",
                "prop": "extracts",
                "titles": title,
                "format": "json",
                "explaintext": True,
                "exlimit": 1
            }
            
            response = requests.get(
                self.endpoint,
                params=params,
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    return page_data.get("extract", "")[:5000]
        except Exception as e:
            console.print(f"[dim]Wikipedia content error: {e}[/dim]")
        
        return ""


class GitHubSearch:
    """GitHub API (free tier: 60 requests/hour unauthenticated)."""
    
    def __init__(self):
        self.endpoint = "https://api.github.com/search/repositories"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ResearchAgent/1.0"
        }
    
    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search GitHub repositories for technical topics."""
        try:
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": max_results
            }
            
            response = requests.get(
                self.endpoint,
                params=params,
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for i, item in enumerate(data.get("items", [])[:max_results]):
                    results.append(SearchResult(
                        title=f"[GitHub] {item.get('full_name', '')}",
                        link=item.get("html_url", ""),
                        snippet=f"⭐ {item.get('stargazers_count', 0)} | {item.get('description', '')[:200]}",
                        source_engine="github",
                        position=i
                    ))
                
                return results
        except Exception as e:
            console.print(f"[dim]GitHub error: {e}[/dim]")
        
        return []


class MultiSearchAggregator:
    """Aggregates search results from multiple free engines."""
    
    def __init__(self, bing_api_key: Optional[str] = None):
        self.serper = None  # Will be set by caller
        self.duckduckgo = DuckDuckGoSearch()
        self.bing = BingSearch(bing_api_key) if bing_api_key else None
        self.wikipedia = WikipediaSearch()
        self.github = GitHubSearch()
    
    def search_all(
        self, 
        query: str, 
        max_results_per_engine: int = 10,
        include_tech: bool = False
    ) -> List[SearchResult]:
        """
        Search across all available engines and aggregate results.
        
        Args:
            query: Search query
            max_results_per_engine: Max results from each engine
            include_tech: Include GitHub for technical queries
        
        Returns:
            Deduplicated list of search results
        """
        all_results = []
        
        # 1. Serper (Google) - primary source
        if self.serper:
            console.print("[dim]Searching Google via Serper...[/dim]")
            try:
                serper_results = self.serper.search(query, max_results_per_engine)
                for r in serper_results:
                    all_results.append(SearchResult(
                        title=r.title,
                        link=r.link,
                        snippet=r.snippet,
                        source_engine="google",
                        position=r.position
                    ))
            except Exception as e:
                console.print(f"[dim]Serper error: {e}[/dim]")
        
        # 2. DuckDuckGo (always free)
        console.print("[dim]Searching DuckDuckGo...[/dim]")
        dd_results = self.duckduckgo.search(query, max_results_per_engine)
        all_results.extend(dd_results)
        
        # 3. Bing (if API key available)
        if self.bing:
            console.print("[dim]Searching Bing...[/dim]")
            bing_results = self.bing.search(query, max_results_per_engine)
            all_results.extend(bing_results)
        
        # 4. Wikipedia (for knowledge queries)
        if any(word in query.lower() for word in ["what is", "how to", "guide", "explained", "vs", "versus"]):
            console.print("[dim]Searching Wikipedia...[/dim]")
            wiki_results = self.wikipedia.search(query, 5)
            all_results.extend(wiki_results)
        
        # 5. GitHub (for technical queries)
        if include_tech or any(word in query.lower() for word in ["github", "code", "api", "library", "framework", "tool"]):
            console.print("[dim]Searching GitHub...[/dim]")
            gh_results = self.github.search(query, max_results_per_engine)
            all_results.extend(gh_results)
        
        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            url_normalized = result.link.lower().rstrip('/')
            if url_normalized not in seen_urls and len(unique_results) < 30:
                seen_urls.add(url_normalized)
                unique_results.append(result)
        
        return unique_results


def get_multi_search(bing_api_key: Optional[str] = None) -> MultiSearchAggregator:
    """Factory function."""
    return MultiSearchAggregator(bing_api_key)
