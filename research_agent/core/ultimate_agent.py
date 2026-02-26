"""
Ultimate Research Agent - One-stop solution for ANY research

Features:
- Auto-detects query type and output format
- Multi-source research (Google, Reddit, Firecrawl)
- Format-specific synthesis
- Professional output formatting
"""
import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
import requests

from rich.console import Console
from rich.table import Table

from research_agent.core.state import ResearchState, ResearchStatus, DataStructureType
from research_agent.core.query_analyzer import QueryAnalyzer, OutputFormat
from research_agent.core.unified_synthesis import UnifiedSynthesisEngine, SynthesisResult
from research_agent.tools.serper_search import SerperSearchTool
from research_agent.tools.reddit_scraper import get_reddit_scraper
from research_agent.config import config

console = Console(legacy_windows=True)


class UltimateResearchAgent:
    """
    The ultimate generic research agent.
    """
    
    def __init__(self, use_firecrawl: bool = True):
        self.search_tool = SerperSearchTool()
        self.reddit = get_reddit_scraper()
        self.synthesis = UnifiedSynthesisEngine()
        self.use_firecrawl = use_firecrawl
        
        # Firecrawl setup
        self.firecrawl = None
        if use_firecrawl and config.firecrawl_api_key:
            from research_agent.tools.firecrawl_client import FirecrawlClient
            self.firecrawl = FirecrawlClient(config.firecrawl_api_key)
    
    async def research(self, query: str, context: str = None) -> ResearchState:
        """Execute research."""
        start_time = time.time()
        
        state = ResearchState(
            query=query,
            original_query=query,
            context=context,
            status=ResearchStatus.SEARCHING,
            start_time=datetime.now()
        )
        
        try:
            console.print(f"\n[bold cyan]Researching: {query}[/bold cyan]\n")
            
            # Step 1: Search
            sources = await self._gather_sources(query, context)
            if not sources:
                state.status = ResearchStatus.ERROR
                state.error_message = "No sources found"
                return state
            
            console.print(f"[green] Found {len(sources)} sources[/green]\n")
            
            # Step 2: Deep content extraction (Firecrawl/Jina)
            await self._enrich_sources(sources)
            
            # Step 3: Synthesize
            console.print("[bold blue] Analyzing and synthesizing...[/bold blue]")
            result = self.synthesis.synthesize(query, sources)
            
            # Step 4: Format output
            state = self._format_output(state, result, sources)
            
            # Step 5: Finalize
            state.status = ResearchStatus.COMPLETED
            duration = time.time() - start_time
            console.print(f"\n[green] Complete in {duration:.1f}s[/green]")
            
        except Exception as e:
            state.status = ResearchStatus.ERROR
            state.error_message = str(e)
            console.print(f"\n[red] Error: {e}[/red]")
        
        return state
    
    async def _gather_sources(self, query: str, context: str) -> List[Dict]:
        """Gather sources from multiple search engines."""
        full_query = f"{query} {context}" if context else query
        
        # Add freshness if no year specified
        if not any(y in full_query for y in ['2023', '2024', '2025']):
            full_query += " 2024"
        
        sources = []
        
        # Google Search
        try:
            results = self.search_tool.search(full_query, num_results=12)
            for r in results:
                sources.append({
                    'title': r.title,
                    'link': r.link,
                    'snippet': r.snippet,
                    'source': 'google'
                })
        except Exception as e:
            console.print(f"[dim]Search warning: {e}[/dim]")
        
        # Reddit
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.reddit.search_reddit_json, query, 5)
                reddit = future.result(timeout=10)
            
            for r in reddit:
                sources.append({
                    'title': r.title,
                    'link': r.url,
                    'snippet': r.content[:400] if r.content else "",
                    'source': 'reddit'
                })
        except:
            pass
        
        return sources
    
    async def _enrich_sources(self, sources: List[Dict]):
        """Fetch full content from top sources."""
        console.print("[dim] Fetching detailed content...[/dim]")
        
        # Get top 5 URLs
        top_sources = [s for s in sources if s.get('link')][:5]
        
        if self.firecrawl:
            # Use Firecrawl for premium sites
            for source in top_sources:
                try:
                    result = self.firecrawl.scrape_url(source['link'])
                    if result.success:
                        source['full_content'] = result.markdown[:3000]
                        console.print(f"[dim]   {source['title'][:50]}...[/dim]")
                except Exception as e:
                    console.print(f"[dim]   Firecrawl failed: {e}[/dim]")
        else:
            # Use Jina AI Reader
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    executor.submit(self._fetch_jina, s['link']): s 
                    for s in top_sources
                }
                for future in futures:
                    try:
                        url, content = future.result(timeout=15)
                        for s in sources:
                            if s.get('link') == url and content:
                                s['full_content'] = content
                    except:
                        pass
    
    def _fetch_jina(self, url: str) -> tuple:
        """Fetch content via Jina AI."""
        try:
            clean = url.replace('https://', '').replace('http://', '')
            resp = requests.get(
                f"https://r.jina.ai/http://{clean}",
                timeout=12,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if resp.status_code == 200:
                return url, resp.text[:2500]
        except:
            pass
        return url, None
    
    def _format_output(self, state: ResearchState, result: SynthesisResult, sources: List[Dict]) -> ResearchState:
        """Format output based on synthesis result."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c if c.isalnum() else "_" for c in state.query[:30])
        
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        filename = f"{safe}_{timestamp}"
        
        # Format based on output type
        if result.format == 'table':
            # CSV output
            content = self._format_csv(result.content)
            filepath = output_dir / f"{filename}.csv"
            filepath.write_text(content, encoding='utf-8-sig')
            state.output_format = DataStructureType.CSV
        else:
            # Markdown report
            content = self._format_markdown(result, sources, state.query)
            filepath = output_dir / f"{filename}.md"
            filepath.write_text(content, encoding='utf-8')
            state.output_format = DataStructureType.MARKDOWN
        
        state.output_file_path = str(filepath)
        state.extracted_data = result.content.get('items', result.content.get('profiles', []))
        
        # Print summary
        self._print_summary(result)
        
        return state
    
    def _format_csv(self, content: Dict) -> str:
        """Format as CSV."""
        import io
        import csv
        
        output = io.StringIO()
        
        items = content.get('items', [])
        if items:
            writer = csv.DictWriter(output, fieldnames=items[0].keys())
            writer.writeheader()
            writer.writerows(items)
        
        return output.getvalue()
    
    def _format_markdown(self, result: SynthesisResult, sources: List[Dict], query: str) -> str:
        """Format as Markdown report."""
        lines = [
            f"# Research: {query}",
            "",
            f"**Domain:** {result.domain}  ",
            f"**Sources:** {result.sources_used}  ",
            f"**Confidence:** {result.confidence:.0%}",
            "",
            "## Summary",
            "",
        ]
        
        # Add content
        if 'items' in result.content:
            lines.append("### Key Findings\n")
            for item in result.content['items'][:10]:
                name = item.get('name', 'Unknown')
                price = item.get('price', 'N/A')
                lines.append(f"- **{name}** ({price})")
                if item.get('best_for'):
                    lines.append(f"  - Best for: {item['best_for']}")
                lines.append("")
        
        elif 'profiles' in result.content:
            lines.append("### Profiles\n")
            for profile in result.content['profiles'][:10]:
                lines.append(f"### {profile.get('name', 'Unknown')}")
                if profile.get('details'):
                    lines.append(profile['details'])
                lines.append("")
        
        else:
            lines.append(result.content.get('content', 'No content generated'))
        
        # Add sources
        lines.extend([
            "",
            "## Sources",
            "",
        ])
        for s in sources[:10]:
            title = s.get('title', 'Link')[:60]
            link = s.get('link', '')
            lines.append(f"- [{title}]({link})")
        
        return "\n".join(lines)
    
    def _print_summary(self, result: SynthesisResult):
        """Print research summary."""
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Domain", result.domain)
        table.add_row("Format", result.format)
        
        if 'items' in result.content:
            table.add_row("Items Found", str(len(result.content['items'])))
        elif 'profiles' in result.content:
            table.add_row("Profiles Found", str(len(result.content['profiles'])))
        
        table.add_row("Sources", str(result.sources_used))
        table.add_row("Confidence", f"{result.confidence:.0%}")
        
        console.print("\n")
        console.print(table)
    
    def research_sync(self, query: str, context: str = None) -> ResearchState:
        """Synchronous entry point."""
        return asyncio.run(self.research(query, context))


def create_ultimate_agent(use_firecrawl: bool = True):
    """Factory function."""
    return UltimateResearchAgent(use_firecrawl)
