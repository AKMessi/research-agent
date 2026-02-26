"""
Firecrawl API Client - Premium web scraping with 514 free credits.

Firecrawl handles:
- JavaScript-rendered pages (React, Vue, Angular)
- Anti-bot protection bypass
- Automatic structured data extraction
- Clean markdown output
"""
import requests
import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from rich.console import Console

console = Console(legacy_windows=True)

FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1"


@dataclass
class FirecrawlResult:
    """Result from Firecrawl scraping."""
    url: str
    markdown: str
    html: str
    metadata: Dict[str, Any]
    links: List[str]
    success: bool
    error: Optional[str] = None
    credits_used: int = 0


class FirecrawlClient:
    """
    Firecrawl API client for premium web scraping.
    
    Free tier: 514 credits (1 credit = 1 page scrape)
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.credits_remaining = 514  # Will be updated after each request
    
    def scrape_url(
        self, 
        url: str, 
        formats: List[str] = ["markdown"],
        only_main_content: bool = True,
        wait_for: int = 0
    ) -> FirecrawlResult:
        """
        Scrape a single URL with Firecrawl.
        
        Args:
            url: URL to scrape
            formats: Output formats ("markdown", "html", "links", "screenshot")
            only_main_content: Extract only main content (removes nav/ads)
            wait_for: Wait time in ms for JS rendering
        
        Returns:
            FirecrawlResult object
        """
        endpoint = f"{FIRECRAWL_API_URL}/scrape"
        
        payload = {
            "url": url,
            "formats": formats,
            "onlyMainContent": only_main_content
        }
        
        if wait_for > 0:
            payload["waitFor"] = wait_for
        
        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    result_data = data.get("data", {})
                    
                    # Update credits from header if available
                    if "X-Credits-Remaining" in response.headers:
                        self.credits_remaining = int(response.headers["X-Credits-Remaining"])
                    
                    return FirecrawlResult(
                        url=url,
                        markdown=result_data.get("markdown", ""),
                        html=result_data.get("html", ""),
                        metadata=result_data.get("metadata", {}),
                        links=result_data.get("links", []),
                        success=True,
                        credits_used=1
                    )
                else:
                    return FirecrawlResult(
                        url=url,
                        markdown="",
                        html="",
                        metadata={},
                        links=[],
                        success=False,
                        error=data.get("error", "Unknown error")
                    )
            else:
                return FirecrawlResult(
                    url=url,
                    markdown="",
                    html="",
                    metadata={},
                    links=[],
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text[:200]}"
                )
                
        except Exception as e:
            return FirecrawlResult(
                url=url,
                markdown="",
                html="",
                metadata={},
                links=[],
                success=False,
                error=str(e)
            )
    
    def scrape_multiple(
        self, 
        urls: List[str], 
        formats: List[str] = ["markdown"],
        only_main_content: bool = True
    ) -> List[FirecrawlResult]:
        """
        Scrape multiple URLs (sequential to respect rate limits).
        
        Args:
            urls: List of URLs to scrape
            formats: Output formats
            only_main_content: Extract only main content
        
        Returns:
            List of FirecrawlResult objects
        """
        results = []
        
        for i, url in enumerate(urls, 1):
            console.print(f"[dim]  Firecrawl [{i}/{len(urls)}]: {url[:60]}...[/dim]")
            
            result = self.scrape_url(url, formats, only_main_content)
            results.append(result)
            
            if result.success:
                console.print(f"[green]    [OK] Scraped ({self.credits_remaining} credits left)[/green]")
            else:
                console.print(f"[red]    [FAIL] Failed: {result.error[:50]}[/red]")
            
            # Rate limiting - be nice to the API
            if i < len(urls):
                time.sleep(0.5)
        
        return results
    
    def extract_structured(
        self, 
        url: str, 
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract structured data from URL using LLM extraction.
        
        Args:
            url: URL to extract from
            schema: JSON schema for extraction
        
        Returns:
            Extracted structured data
        """
        endpoint = f"{FIRECRAWL_API_URL}/scrape"
        
        payload = {
            "url": url,
            "formats": ["extract"],
            "extract": {
                "schema": schema,
                "systemPrompt": "Extract all relevant product information accurately."
            }
        }
        
        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("data", {}).get("extract", {})
        except Exception as e:
            console.print(f"[dim]Structured extraction error: {e}[/dim]")
        
        return {}
    
    def map_website(self, url: str, search: str = "") -> List[str]:
        """
        Map a website to find all relevant URLs.
        
        Args:
            url: Base URL to map
            search: Optional search term to filter URLs
        
        Returns:
            List of discovered URLs
        """
        endpoint = f"{FIRECRAWL_API_URL}/map"
        
        payload = {"url": url}
        if search:
            payload["search"] = search
        
        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("data", {}).get("links", [])
        except Exception as e:
            console.print(f"[dim]Map error: {e}[/dim]")
        
        return []
    
    def get_credits(self) -> int:
        """Get remaining credits."""
        return self.credits_remaining


def get_firecrawl_client(api_key: Optional[str] = None) -> Optional[FirecrawlClient]:
    """
    Factory function to get Firecrawl client.
    
    Args:
        api_key: Firecrawl API key. If None, tries to get from environment.
    
    Returns:
        FirecrawlClient or None if no API key
    """
    import os
    
    key = api_key or os.getenv("FIRECRAWL_API_KEY")
    
    if not key:
        return None
    
    return FirecrawlClient(key)
