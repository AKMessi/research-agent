"""
Research Agent V2 - Synthesis-Based Approach

INSTEAD OF: Extracting structured data from HTML (impossible reliably)
WE DO: Synthesize research findings from multiple sources

Output: Research report with recommendations, not just a data table
"""
import asyncio
from datetime import datetime
from pathlib import Path

from rich.console import Console

from research_agent.core.state import ResearchState, ResearchStatus, DataStructureType
from research_agent.core.synthesis_engine import SynthesisEngine, ReportFormatter
from research_agent.tools.serper_search import SerperSearchTool
from research_agent.tools.reddit_scraper import get_reddit_scraper
from research_agent.config import config

console = Console(legacy_windows=True)


class ResearchAgentV2Optimized:
    """
    Research agent that synthesizes findings instead of extracting data.
    """
    
    def __init__(self, use_firecrawl: bool = False, quick_mode: bool = False):
        self.search_tool = SerperSearchTool()
        self.reddit = get_reddit_scraper()
        self.synthesis = SynthesisEngine()
        self.quick_mode = quick_mode
    
    async def research(self, query: str, context: str = None) -> ResearchState:
        """Execute research by synthesis."""
        state = ResearchState(
            query=query,
            original_query=query,
            context=context,
            status=ResearchStatus.SEARCHING,
            start_time=datetime.now()
        )
        
        try:
            # Step 1: Search
            console.print("[bold blue]Researching...[/bold blue]")
            sources = await self._gather_sources(query, context)
            
            if not sources:
                state.status = ResearchStatus.ERROR
                state.error_message = "No sources found"
                return state
            
            console.print(f"[green]Found {len(sources)} sources[/green]")
            
            # Step 2: Synthesize (the key step)
            console.print("[bold blue]Analyzing and synthesizing...[/bold blue]")
            result = self.synthesis.synthesize(query, sources)
            
            # Step 3: Format output
            state = self._save_output(state, result, sources)
            state.status = ResearchStatus.COMPLETED
            
        except Exception as e:
            state.status = ResearchStatus.ERROR
            state.error_message = str(e)
            console.print(f"[red]Error: {e}[/red]")
        
        return state
    
    async def _gather_sources(self, query: str, context: str) -> list:
        """Gather sources from multiple search engines."""
        full_query = f"{query} {context}" if context else query
        
        # Add year for freshness
        if not any(y in full_query for y in ['2024', '2025']):
            full_query += " 2024"
        
        sources = []
        
        # Google search
        try:
            results = self.search_tool.search(full_query, num_results=10)
            for r in results:
                sources.append({
                    'title': r.title,
                    'link': r.link,
                    'snippet': r.snippet,
                })
        except Exception as e:
            console.print(f"[dim]Search warning: {e}[/dim]")
        
        # Reddit
        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.reddit.search_reddit_json, query, 5)
                reddit = future.result(timeout=8)
            
            for r in reddit:
                sources.append({
                    'title': r.title,
                    'link': r.url,
                    'snippet': r.content[:500] if r.content else "",
                })
        except:
            pass
        
        # Fetch full content for top sources
        if not self.quick_mode:
            await self._fetch_content(sources[:6])
        
        return sources
    
    async def _fetch_content(self, sources: list):
        """Fetch full content from URLs."""
        import requests
        from concurrent.futures import ThreadPoolExecutor
        
        def fetch(url):
            try:
                clean = url.replace('https://', '').replace('http://', '')
                resp = requests.get(
                    f"https://r.jina.ai/http://{clean}",
                    timeout=10,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                if resp.status_code == 200:
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
    
    def _save_output(self, state: ResearchState, result: dict, sources: list) -> ResearchState:
        """Save formatted output."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(c if c.isalnum() else "_" for c in state.query[:35])
        filename = f"{safe}_{timestamp}"
        
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as Markdown report (primary output)
        md_content = ReportFormatter.to_markdown(result, state.query)
        md_path = output_dir / f"{filename}.md"
        md_path.write_text(md_content, encoding='utf-8')
        
        # Also save as CSV (flattened)
        csv_content = ReportFormatter.to_csv(result)
        csv_path = output_dir / f"{filename}.csv"
        csv_path.write_text(csv_content, encoding='utf-8-sig')
        
        # Save sources
        sources_md = "\n".join([f"- [{s['title']}]({s['link']})" for s in sources[:10]])
        full_md = f"{md_content}\n\n## Sources\n{sources_md}"
        md_path.write_text(full_md, encoding='utf-8')
        
        state.output_file_path = str(md_path)
        state.output_format = DataStructureType.MARKDOWN
        state.extracted_data = result.get("recommendations", [])
        
        return state
    
    def research_sync(self, query: str, context: str = None) -> ResearchState:
        """Synchronous entry point."""
        return asyncio.run(self.research(query, context))


def create_agent(use_firecrawl=False, quick_mode=False):
    return ResearchAgentV2Optimized(use_firecrawl, quick_mode)
