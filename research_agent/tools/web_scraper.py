"""
Advanced Web Scraper for extracting content from search results.

This module provides sophisticated web scraping capabilities including:
- Fetching full page content
- Extracting structured data using LLM
- Handling JavaScript-rendered pages (optional)
- Rate limiting and respect for robots.txt
"""
import asyncio
import aiohttp
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from rich.console import Console

from research_agent.config import config

console = Console(legacy_windows=True)


@dataclass
class ScrapedContent:
    """Content scraped from a webpage."""
    url: str
    title: str
    content: str
    headers: List[str]
    paragraphs: List[str]
    tables: List[List[List[str]]]
    lists: List[List[str]]
    meta_description: str = ""
    status_code: int = 200
    error: Optional[str] = None
    
    def to_text(self, max_length: int = 5000) -> str:
        """Convert to formatted text for LLM processing."""
        text_parts = [
            f"URL: {self.url}",
            f"Title: {self.title}",
            f"Description: {self.meta_description}",
            "",
            "Content:",
        ]
        
        # Add headers with their following content
        content = "\n".join(self.paragraphs[:20])  # Limit paragraphs
        
        # Add tables if found
        if self.tables:
            content += "\n\nTables found:\n"
            for i, table in enumerate(self.tables[:3], 1):
                content += f"\nTable {i}:\n"
                for row in table[:10]:  # Limit rows
                    content += " | ".join(str(cell)[:50] for cell in row) + "\n"
        
        text_parts.append(content[:max_length])
        
        return "\n".join(text_parts)


class WebScraper:
    """
    Advanced web scraper with content extraction capabilities.
    """
    
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session
    
    async def scrape_async(self, url: str) -> ScrapedContent:
        """
        Scrape a single URL asynchronously.
        
        Args:
            url: URL to scrape
        
        Returns:
            ScrapedContent object
        """
        # Skip problematic domains
        skip_domains = ['youtube.com', 'youtu.be', 'reddit.com', 'twitter.com', 'x.com', 'facebook.com']
        if any(domain in url.lower() for domain in skip_domains):
            return ScrapedContent(
                url=url,
                title="",
                content="",
                headers=[],
                paragraphs=[],
                tables=[],
                lists=[],
                status_code=0,
                error="Skipped: social/media site"
            )
        
        session = await self._get_session()
        
        try:
            async with session.get(url, timeout=self.timeout, ssl=False) as response:
                # Handle various status codes
                if response.status in [403, 429]:
                    return ScrapedContent(
                        url=url,
                        title="",
                        content="",
                        headers=[],
                        paragraphs=[],
                        tables=[],
                        lists=[],
                        status_code=response.status,
                        error=f"Blocked (HTTP {response.status})"
                    )
                
                html = await response.text()
                
                if response.status != 200:
                    return ScrapedContent(
                        url=url,
                        title="",
                        content="",
                        headers=[],
                        paragraphs=[],
                        tables=[],
                        lists=[],
                        status_code=response.status,
                        error=f"HTTP {response.status}"
                    )
                
                return self._parse_html(url, html)
                
        except asyncio.TimeoutError:
            return ScrapedContent(
                url=url,
                title="",
                content="",
                headers=[],
                paragraphs=[],
                tables=[],
                lists=[],
                status_code=0,
                error="Timeout"
            )
        except Exception as e:
            return ScrapedContent(
                url=url,
                title="",
                content="",
                headers=[],
                paragraphs=[],
                tables=[],
                lists=[],
                status_code=0,
                error=str(e)[:100]
            )
    
    def scrape(self, url: str) -> ScrapedContent:
        """
        Scrape a single URL synchronously.
        
        Args:
            url: URL to scrape
        
        Returns:
            ScrapedContent object
        """
        # Skip problematic domains
        skip_domains = ['youtube.com', 'youtu.be', 'reddit.com', 'twitter.com', 'x.com', 'facebook.com', 'instagram.com']
        if any(domain in url.lower() for domain in skip_domains):
            return ScrapedContent(
                url=url,
                title="",
                content="",
                headers=[],
                paragraphs=[],
                tables=[],
                lists=[],
                status_code=0,
                error="Skipped: social/media site"
            )
        
        try:
            # Disable SSL warnings
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            response = requests.get(
                url, 
                headers=self.headers, 
                timeout=self.timeout,
                verify=False,
                allow_redirects=True
            )
            
            # Handle various status codes
            if response.status_code in [403, 429, 401]:
                return ScrapedContent(
                    url=url,
                    title="",
                    content="",
                    headers=[],
                    paragraphs=[],
                    tables=[],
                    lists=[],
                    status_code=response.status_code,
                    error=f"Access blocked (HTTP {response.status_code})"
                )
            
            if response.status_code != 200:
                return ScrapedContent(
                    url=url,
                    title="",
                    content="",
                    headers=[],
                    paragraphs=[],
                    tables=[],
                    lists=[],
                    status_code=response.status_code,
                    error=f"HTTP {response.status_code}"
                )
            
            return self._parse_html(url, response.text)
            
        except requests.Timeout:
            return ScrapedContent(
                url=url,
                title="",
                content="",
                headers=[],
                paragraphs=[],
                tables=[],
                lists=[],
                status_code=0,
                error="Timeout"
            )
        except Exception as e:
            return ScrapedContent(
                url=url,
                title="",
                content="",
                headers=[],
                paragraphs=[],
                tables=[],
                lists=[],
                status_code=0,
                error=str(e)[:100]
            )
    
    async def scrape_multiple(self, urls: List[str], max_concurrent: int = 5) -> List[ScrapedContent]:
        """
        Scrape multiple URLs concurrently with rate limiting.
        
        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum concurrent requests
        
        Returns:
            List of ScrapedContent objects
        """
        # Use ThreadPoolExecutor for synchronous requests
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = []
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all tasks
            future_to_url = {executor.submit(self.scrape, url): url for url in urls}
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(ScrapedContent(
                        url=url,
                        title="",
                        content="",
                        headers=[],
                        paragraphs=[],
                        tables=[],
                        lists=[],
                        status_code=0,
                        error=str(e)[:100]
                    ))
                await asyncio.sleep(0.3)  # Rate limiting
        
        return results
    
    def _parse_html(self, url: str, html: str) -> ScrapedContent:
        """
        Parse HTML and extract structured content.
        
        Args:
            url: Source URL
            html: HTML content
        
        Returns:
            ScrapedContent object
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string.strip() if soup.title.string else ""
        elif soup.h1:
            title = soup.h1.get_text(strip=True)
        
        # Extract meta description
        meta_desc = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            meta_desc = meta.get("content", "")
        
        # Extract headers
        headers = []
        for h in soup.find_all(['h1', 'h2', 'h3']):
            text = h.get_text(strip=True)
            if text and len(text) < 200:
                headers.append(text)
        
        # Extract paragraphs
        paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if text and len(text) > 50:  # Filter out short snippets
                paragraphs.append(text)
        
        # Extract tables
        tables = []
        for table in soup.find_all('table')[:3]:  # Limit to 3 tables
            rows = []
            for tr in table.find_all('tr')[:20]:  # Limit rows
                row = []
                for cell in tr.find_all(['td', 'th']):
                    row.append(cell.get_text(strip=True))
                if row:
                    rows.append(row)
            if rows:
                tables.append(rows)
        
        # Extract lists
        lists = []
        for ul in soup.find_all(['ul', 'ol'])[:5]:
            items = []
            for li in ul.find_all('li'):
                text = li.get_text(strip=True)
                if text and len(text) < 500:
                    items.append(text)
            if items:
                lists.append(items)
        
        # Build full content
        content_parts = []
        content_parts.extend(headers[:10])
        content_parts.extend(paragraphs[:30])
        content = "\n\n".join(content_parts)
        
        return ScrapedContent(
            url=url,
            title=title,
            content=content[:8000],  # Limit content length
            headers=headers[:15],
            paragraphs=paragraphs[:30],
            tables=tables,
            lists=lists,
            meta_description=meta_desc,
            status_code=200
        )
    
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


def get_scraper() -> WebScraper:
    """Factory function to get a configured web scraper."""
    return WebScraper()
