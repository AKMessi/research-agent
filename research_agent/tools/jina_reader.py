"""
Jina AI Reader API integration for high-quality content extraction.

Jina Reader converts any URL to clean, LLM-friendly text with 95% success rate.
Free tier: 10,000 requests/month
"""
import requests
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from rich.console import Console

console = Console(legacy_windows=True)

JINA_READER_BASE = "https://r.jina.ai/http://"
JINA_READER_HTTPS = "https://r.jina.ai/http://"


@dataclass
class JinaExtractedContent:
    """Content extracted by Jina AI Reader."""
    url: str
    title: str
    content: str
    excerpt: str
    links: List[str]
    success: bool
    error: Optional[str] = None


class JinaReader:
    """
    Jina AI Reader client for extracting clean text from URLs.
    
    Features:
    - 95% success rate on any website
    - Returns clean markdown/text
    - Handles JavaScript sites
    - Respects robots.txt
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.headers = {
            "Accept": "application/json",
            "X-Return-Format": "markdown"
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    def extract(self, url: str) -> JinaExtractedContent:
        """
        Extract content from a URL using Jina AI Reader.
        
        Args:
            url: URL to extract content from
        
        Returns:
            JinaExtractedContent with clean text
        """
        # Clean URL
        url = url.strip()
        if url.startswith('https://'):
            jina_url = f"https://r.jina.ai/http://{url[8:]}"
        elif url.startswith('http://'):
            jina_url = f"https://r.jina.ai/http://{url[7:]}"
        else:
            jina_url = f"https://r.jina.ai/http://{url}"
        
        try:
            response = requests.get(
                jina_url,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json() if 'json' in response.headers.get('content-type', '') else None
                
                if data:
                    return JinaExtractedContent(
                        url=url,
                        title=data.get('data', {}).get('title', ''),
                        content=data.get('data', {}).get('content', ''),
                        excerpt=data.get('data', {}).get('excerpt', ''),
                        links=data.get('data', {}).get('links', []),
                        success=True
                    )
                else:
                    # Plain text response
                    text = response.text
                    lines = text.split('\n')
                    title = lines[0] if lines else ""
                    return JinaExtractedContent(
                        url=url,
                        title=title,
                        content=text,
                        excerpt=text[:500],
                        links=[],
                        success=True
                    )
            else:
                return JinaExtractedContent(
                    url=url,
                    title="",
                    content="",
                    excerpt="",
                    links=[],
                    success=False,
                    error=f"HTTP {response.status_code}"
                )
                
        except Exception as e:
            return JinaExtractedContent(
                url=url,
                title="",
                content="",
                excerpt="",
                links=[],
                success=False,
                error=str(e)
            )
    
    async def extract_async(self, url: str, session: aiohttp.ClientSession) -> JinaExtractedContent:
        """Async version of extract."""
        url = url.strip()
        if url.startswith('https://'):
            jina_url = f"https://r.jina.ai/http://{url[8:]}"
        elif url.startswith('http://'):
            jina_url = f"https://r.jina.ai/http://{url[7:]}"
        else:
            jina_url = f"https://r.jina.ai/http://{url}"
        
        try:
            async with session.get(jina_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    text = await response.text()
                    lines = text.split('\n')
                    title = lines[0] if lines else ""
                    return JinaExtractedContent(
                        url=url,
                        title=title,
                        content=text,
                        excerpt=text[:500],
                        links=[],
                        success=True
                    )
                else:
                    return JinaExtractedContent(
                        url=url,
                        title="",
                        content="",
                        excerpt="",
                        links=[],
                        success=False,
                        error=f"HTTP {response.status}"
                    )
        except Exception as e:
            return JinaExtractedContent(
                url=url,
                title="",
                content="",
                excerpt="",
                links=[],
                success=False,
                error=str(e)
            )
    
    async def extract_multiple(self, urls: List[str], max_concurrent: int = 5) -> List[JinaExtractedContent]:
        """
        Extract content from multiple URLs concurrently.
        
        Args:
            urls: List of URLs to extract
            max_concurrent: Maximum concurrent requests
        
        Returns:
            List of JinaExtractedContent
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_with_limit(url: str, session: aiohttp.ClientSession) -> JinaExtractedContent:
            async with semaphore:
                result = await self.extract_async(url, session)
                await asyncio.sleep(0.5)  # Rate limiting
                return result
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            tasks = [extract_with_limit(url, session) for url in urls]
            return await asyncio.gather(*tasks)
    
    def search_and_extract(self, query: str) -> JinaExtractedContent:
        """
        Use Jina AI to search and extract from top result.
        
        Args:
            query: Search query
        
        Returns:
            JinaExtractedContent from top search result
        """
        search_url = f"https://s.jina.ai/http://{query.replace(' ', '%20')}"
        
        try:
            response = requests.get(search_url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                text = response.text
                lines = text.split('\n')
                title = lines[0] if lines else ""
                return JinaExtractedContent(
                    url=search_url,
                    title=title,
                    content=text,
                    excerpt=text[:500],
                    links=[],
                    success=True
                )
        except Exception as e:
            pass
        
        return JinaExtractedContent(
            url=search_url,
            title="",
            content="",
            excerpt="",
            links=[],
            success=False,
            error="Search failed"
        )


def get_jina_reader(api_key: Optional[str] = None) -> JinaReader:
    """Factory function to get Jina Reader instance."""
    return JinaReader(api_key)
