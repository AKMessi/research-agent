#!/usr/bin/env python3
"""
Ultimate Research Agent - One-stop solution for ANY research

Usage:
    python main.py research "best budget laptops for students"
    python main.py research "places to visit in Japan"
    python main.py research "top machine learning experts 2024"
    python main.py research "how to learn python programming"
    python main.py research "startup companies in AI space"
"""
import os
import sys
import asyncio
from pathlib import Path
from typing import Optional, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

from research_agent.core.ultimate_agent import create_ultimate_agent
from research_agent.core.state import ResearchStatus
from research_agent.config import config


# Type alias for cleaner code
ResearchResult = Any

app = typer.Typer(name="research-agent", add_completion=False, help="Ultimate Research Agent")
console = Console(legacy_windows=True)


def print_banner():
    """Print application banner."""
    console.print("""
[bold cyan]
===============================================================
                 ULTIMATE RESEARCH AGENT
       Research Anything | Smart Analysis | Beautiful Output
===============================================================
[/bold cyan]
""")


def check_config() -> bool:
    """Check required API keys."""
    missing = []
    if not config.is_serper_configured:
        missing.append("SERPER_API_KEY")
    
    if missing:
        console.print(f"[red]Missing required: {', '.join(missing)}[/red]")
        console.print("[dim]Get free API key at: https://serper.dev[/dim]")
        return False
    
    # Check optional services
    if not config.is_firecrawl_configured:
        console.print("[yellow]Tip: Add FIRECRAWL_API_KEY for better content extraction[/yellow]")
    
    return True


@app.command()
def research(
    query: str = typer.Argument(..., help="Your research query - anything!"),
    context: Optional[str] = typer.Option(None, "--context", "-c", help="Additional context"),
    no_firecrawl: bool = typer.Option(False, "--no-firecrawl", help="Skip Firecrawl (use Jina AI instead)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    no_banner: bool = typer.Option(False, "--no-banner", help="Hide banner"),
):
    """
    Research ANY topic and get structured results.
    
    Examples:
        research "best wireless earbuds under $100"
        research "places to visit in Japan"
        research "top AI researchers 2024"
        research "how to start a podcast"
    """
    
    if not no_banner:
        print_banner()
    
    if not check_config():
        raise typer.Exit(1)
    
    console.print(f"[bold]Query:[/bold] {query}")
    if context:
        console.print(f"[dim]Context: {context}[/dim]")
    console.print()
    
    try:
        # Create agent
        agent = create_ultimate_agent(use_firecrawl=not no_firecrawl)
        
        # Run research
        result = agent.research_sync(query, context)
        
        if result.status == ResearchStatus.COMPLETED and result.output_file_path:
            console.print(f"\n[bold green]📄 Output saved to:[/bold green] {result.output_file_path}")
            
            # Preview if verbose
            if verbose and result.extracted_data:
                console.print("\n[bold]Preview:[/bold]")
                for i, item in enumerate(result.extracted_data[:5], 1):
                    name = item.get('name', item.get('title', 'Item'))
                    console.print(f"  {i}. {name}")
            
            console.print()
        else:
            console.print(f"[red]Research failed: {result.error_message}[/red]")
            raise typer.Exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def info():
    """Show system info and capabilities."""
    print_banner()
    
    table = Table(title="System Status")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")
    
    table.add_row("Serper API (Search)", "OK" if config.is_serper_configured else "Missing")
    table.add_row("Firecrawl API", "OK" if config.is_firecrawl_configured else "Not configured (optional)")
    table.add_row("Ollama (Local LLM)", f"{config.ollama_model} @ {config.ollama_url}")
    
    console.print(table)
    
    console.print("\n[bold]Supported Research Types:[/bold]")
    types_table = Table()
    types_table.add_column("Type", style="cyan")
    types_table.add_column("Example Query", style="green")
    
    types_table.add_row("Products", "best budget laptop under $1000")
    types_table.add_row("Places", "best places to visit in Japan")
    types_table.add_row("People", "top AI researchers 2024")
    types_table.add_row("Companies", "AI startups in healthcare")
    types_table.add_row("How-To", "how to learn Python programming")
    types_table.add_row("Events", "tech conferences 2024")
    types_table.add_row("General", "climate change effects on agriculture")
    
    console.print(types_table)
    console.print()


@app.command()
def examples():
    """Show usage examples."""
    console.print("""
[bold cyan]Product Research:[/bold cyan]
  research "best budget GPU for machine learning"
  research "wireless earbuds for workout under $150"
  research "mechanical keyboards for programming"

[bold cyan]Travel Research:[/bold cyan]
  research "best places to visit in Japan"
  research "budget travel destinations in Europe"
  research "weekend getaways near New York"

[bold cyan]People & Companies:[/bold cyan]
  research "top machine learning experts"
  research "AI startups to watch in 2024"
  research "best software engineering blogs"

[bold cyan]How-To Guides:[/bold cyan]
  research "how to start a podcast"
  research "learn python programming for beginners"
  research "how to invest in stocks"

[bold cyan]Quick Mode (no Firecrawl):[/bold cyan]
  research "current gold price" --no-firecrawl
""")


def main():
    if len(sys.argv) == 1:
        print_banner()
        console.print("[dim]Run 'research-agent --help' for usage[/dim]")
        console.print("[dim]Or 'research-agent examples' for examples[/dim]\n")
        return
    
    app()


if __name__ == "__main__":
    main()
