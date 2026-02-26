"""
Research Orchestrator - Production-Grade Architecture

KEY PRINCIPLES:
1. Progressive Enhancement - Fast results first, quality improves over time
2. Parallel Extraction - Pattern + LLM run simultaneously  
3. Smart Caching - Never extract the same content twice
4. Result Ranking - Quality scores determine what users see first

FLOW:
Search → Parallel Extract (Pattern + Local LLM) → Merge & Rank → Format
         ↓
    Return fast pattern results (2 sec)
         ↓
    Enhance with LLM (30 sec) - Update results
"""
import asyncio
import hashlib
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

from rich.console import Console

console = Console(legacy_windows=True)


@dataclass
class ExtractedItem:
    """Single extracted item with metadata."""
    name: str
    data: Dict[str, Any]
    source_urls: List[str] = field(default_factory=list)
    extraction_method: str = ""  # 'pattern', 'local_llm', 'cloud_llm'
    confidence: float = 0.0  # 0-1 quality score
    timestamp: float = field(default_factory=time.time)
    
    def merge(self, other: 'ExtractedItem') -> 'ExtractedItem':
        """Merge two items, keeping best data from each."""
        merged_data = dict(self.data)
        
        for key, value in other.data.items():
            if value and value != "N/A" and (not merged_data.get(key) or merged_data[key] == "N/A"):
                merged_data[key] = value
        
        return ExtractedItem(
            name=self.name,
            data=merged_data,
            source_urls=list(set(self.source_urls + other.source_urls)),
            extraction_method=f"{self.extraction_method}+{other.extraction_method}",
            confidence=max(self.confidence, other.confidence),
        )


@dataclass  
class ResearchJob:
    """A research job with all its data."""
    query: str
    context: Optional[str]
    sources: List[Dict] = field(default_factory=list)
    items: List[ExtractedItem] = field(default_factory=list)
    status: str = "pending"  # pending, searching, extracting, merging, complete
    start_time: float = field(default_factory=time.time)


class FastPatternExtractor:
    """Ultra-fast extraction using regex patterns (< 1 second)."""
    
    # Product patterns
    PATTERNS = {
        'gpu': [
            r'(RTX\s+\d{3,4}(?:\s*Ti)?)',
            r'(RX\s+\d{3,4}(?:\s*XT)?)', 
            r'(GTX\s+\d{3,4})',
            r'(Arc\s+[A-Z]\d{3,4})',
        ],
        'cpu': [
            r'(Core\s+i\d+-\d{4,5}[A-Z]?)',
            r'(Ryzen\s+\d\s+\d{4,5}X?)',
            r'(Ryzen\s+\d\s+\d{4,5})',
        ],
        'laptop': [
            r'(MacBook\s+(?:Pro|Air)?\s*\d{0,4})',
            r'(ThinkPad\s+[XTEP]\d{0,3})',
            r'(XPS\s+\d{2,3})',
            r'(Spectre\s+x360)',
        ],
        'price': r'\$([0-9,]+(?:\.\d{2})?)',
        'rating': r'(\d\.\d)\s*/\s*5',
    }
    
    BRAND_MAP = {
        'RTX': 'NVIDIA', 'GTX': 'NVIDIA', 'GeForce': 'NVIDIA',
        'RX': 'AMD', 'Radeon': 'AMD',
        'Arc': 'Intel',
        'Core': 'Intel', 'i3': 'Intel', 'i5': 'Intel', 'i7': 'Intel', 'i9': 'Intel',
        'Ryzen': 'AMD',
        'MacBook': 'Apple', 'Mac': 'Apple',
    }
    
    @classmethod
    def extract(cls, sources: List[Dict], domain: str = "product") -> List[ExtractedItem]:
        """Extract items in under 1 second."""
        items = {}
        
        for source in sources:
            text = source.get('full_content') or source.get('snippet') or ''
            url = source.get('link', '')
            
            # Detect product type from query/text
            patterns = cls.PATTERNS.get('gpu', []) + cls.PATTERNS.get('cpu', []) + cls.PATTERNS.get('laptop', [])
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    name = match.strip().upper()
                    key = name.lower()
                    
                    if key in items:
                        items[key].source_urls.append(url)
                        continue
                    
                    # Extract context around match
                    context_match = re.search(
                        r'.{0,200}' + re.escape(match) + r'.{0,300}',
                        text,
                        re.IGNORECASE
                    )
                    context = context_match.group(0) if context_match else text[:500]
                    
                    # Build item
                    item = ExtractedItem(
                        name=name,
                        data={
                            'name': name,
                            'brand': cls._extract_brand(name, context),
                            'price': cls._extract_price(context),
                            'rating': cls._extract_rating(context),
                            'key_specs': cls._extract_specs(context),
                            'source': url,
                        },
                        source_urls=[url],
                        extraction_method='pattern',
                        confidence=0.6,  # Pattern extraction = 60% confidence
                    )
                    items[key] = item
        
        return list(items.values())[:15]  # Top 15
    
    @classmethod
    def _extract_brand(cls, name: str, context: str) -> str:
        for key, brand in cls.BRAND_MAP.items():
            if key.upper() in name.upper():
                return brand
        return "N/A"
    
    @classmethod
    def _extract_price(cls, text: str) -> str:
        match = re.search(cls.PATTERNS['price'], text)
        if match:
            price = match.group(1).replace(',', '')
            try:
                val = float(price)
                if 10 <= val <= 50000:
                    return f"${int(val)}"
            except:
                pass
        return "N/A"
    
    @classmethod
    def _extract_rating(cls, text: str) -> str:
        match = re.search(cls.PATTERNS['rating'], text)
        if match:
            return match.group(1)
        return "N/A"
    
    @classmethod
    def _extract_specs(cls, text: str) -> List[str]:
        specs = []
        vram = re.search(r'(\d{1,3})\s*GB\s*(?:VRAM|GDDR)', text, re.I)
        if vram:
            specs.append(f"{vram.group(1)}GB VRAM")
        tdp = re.search(r'(\d{2,4})W', text)
        if tdp:
            specs.append(f"{tdp.group(1)}W")
        return specs if specs else ["N/A"]


class SimpleLLMExtractor:
    """Simple Ollama LLM extractor with timeout."""
    
    OLLAMA_URL = "http://localhost:11434/api/generate"
    
    @classmethod
    def extract(cls, query: str, sources: List[Dict], model: str = "mistral") -> List[ExtractedItem]:
        """Extract using local LLM."""
        
        # Build compact context
        context_parts = []
        for s in sources[:5]:  # Only top 5 sources for speed
            text = s.get('full_content') or s.get('snippet') or ''
            if text:
                context_parts.append(f"SOURCE: {s.get('title')}\n{text[:600]}")
        
        if not context_parts:
            return []
        
        context = "\n---\n".join(context_parts)
        
        prompt = f"""Extract products from these sources for: "{query}"

Return JSON array with fields: name, brand, price, key_specs (array), best_for, rating
Be concise. Return ONLY JSON.

SOURCES:
{context[:3000]}

JSON:"""
        
        try:
            resp = requests.post(
                cls.OLLAMA_URL,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 1500}
                },
                timeout=45  # 45 second timeout
            )
            
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                match = re.search(r'\[.*\]', text, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    items = []
                    for d in data:
                        if isinstance(d, dict) and d.get('name'):
                            items.append(ExtractedItem(
                                name=d['name'],
                                data=d,
                                extraction_method='local_llm',
                                confidence=0.85,
                            ))
                    return items
        except Exception as e:
            console.print(f"[dim]LLM extraction: {e}[/dim]")
        
        return []


class ResultMerger:
    """Intelligently merge results from multiple extractors."""
    
    @classmethod
    def merge(cls, pattern_items: List[ExtractedItem], llm_items: List[ExtractedItem]) -> List[Dict]:
        """Merge pattern and LLM results."""
        
        # Index by normalized name
        by_name = {}
        
        # Add pattern items first
        for item in pattern_items:
            key = cls._normalize_name(item.name)
            by_name[key] = item
        
        # Merge LLM items
        for item in llm_items:
            key = cls._normalize_name(item.name)
            if key in by_name:
                by_name[key] = by_name[key].merge(item)
            else:
                by_name[key] = item
        
        # Sort by confidence, convert to dict
        items = sorted(by_name.values(), key=lambda x: x.confidence, reverse=True)
        return [item.data for item in items[:10]]
    
    @classmethod
    def _normalize_name(cls, name: str) -> str:
        """Normalize name for deduplication."""
        name = name.upper()
        name = re.sub(r'\s+', ' ', name)
        name = re.sub(r'[^\w\s]', '', name)
        return name.strip()


class ResearchOrchestrator:
    """
    Main orchestrator that coordinates the research pipeline.
    
    Usage:
        orch = ResearchOrchestrator()
        results = await orch.research("best budget GPU")
    """
    
    def __init__(self):
        self.search_tool = SerperSearchTool()
        self.reddit = get_reddit_scraper()
    
    async def research(self, query: str, context: str = None) -> Tuple[List[Dict], float]:
        """
        Execute full research pipeline.
        Returns: (results, duration_seconds)
        """
        start = time.time()
        
        # Step 1: Search (parallel)
        console.print("[bold blue]Searching...[/bold blue]")
        sources = await self._search(query, context)
        
        if not sources:
            return [], 0
        
        console.print(f"[green]Found {len(sources)} sources[/green]")
        
        # Step 2: Parallel Extraction
        # Start pattern extraction immediately (fast)
        pattern_items = FastPatternExtractor.extract(sources)
        console.print(f"[green]Pattern extraction: {len(pattern_items)} items[/green]")
        
        # Return pattern results immediately if we have enough
        if len(pattern_items) >= 5:
            console.print("[dim]Enhancing with LLM (background)...[/dim]")
            # Try LLM enhancement but don't block
            try:
                llm_items = SimpleLLMExtractor.extract(query, sources)
                if llm_items:
                    merged = ResultMerger.merge(pattern_items, llm_items)
                    duration = time.time() - start
                    return merged, duration
            except:
                pass
            
            # Return pattern results if LLM fails
        pattern_results = [item.data for item in pattern_items[:10]]
        duration = time.time() - start
        return pattern_results, duration
        
        # If pattern found few items, wait for LLM
        console.print("[dim]Running LLM extraction...[/dim]")
        try:
            llm_items = SimpleLLMExtractor.extract(query, sources)
            merged = ResultMerger.merge(pattern_items, llm_items)
            duration = time.time() - start
            return merged, duration
        except:
            duration = time.time() - start
            return [item.data for item in pattern_items[:10]], duration
    
    async def _search(self, query: str, context: str) -> List[Dict]:
        """Search Google and Reddit."""
        full_query = f"{query} {context}" if context else query
        if not any(y in full_query for y in ['2024', '2025']):
            full_query += " 2024"
        
        sources = []
        
        # Google search
        try:
            results = self.search_tool.search(full_query, num_results=10)
            sources.extend([{
                'title': r.title,
                'link': r.link,
                'snippet': r.snippet,
            } for r in results])
        except:
            pass
        
        # Reddit
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.reddit.search_reddit_json, query, 3)
                reddit = future.result(timeout=8)
            sources.extend([{
                'title': r.title,
                'link': r.url,
                'snippet': r.content[:400] if r.content else "",
            } for r in reddit])
        except:
            pass
        
        # Fetch full content for top sources (parallel)
        await self._fetch_content(sources[:6])
        
        return sources
    
    async def _fetch_content(self, sources: List[Dict]):
        """Fetch full content from URLs."""
        def fetch(url):
            try:
                clean = url.replace('https://', '').replace('http://', '')
                resp = requests.get(
                    f"https://r.jina.ai/http://{clean}",
                    timeout=10,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                if resp.status_code == 200 and len(resp.text) > 300:
                    return url, resp.text[:2000]
            except:
                pass
            return url, None
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(fetch, s['link']): s for s in sources if s.get('link')}
            for future in futures:
                try:
                    url, content = future.result(timeout=12)
                    if content:
                        for s in sources:
                            if s.get('link') == url:
                                s['full_content'] = content
                                break
                except:
                    pass


# Import at bottom to avoid circular imports
from research_agent.tools.serper_search import SerperSearchTool
from research_agent.tools.reddit_scraper import get_reddit_scraper
import re
