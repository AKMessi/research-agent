#!/usr/bin/env python3
"""
Demo Script for Ultimate Research Agent

This script demonstrates the capabilities of the research agent
with various query types.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from research_agent.core.data_structure_decider import DataStructureDecider, DataStructureType


def demo_structure_decider():
    """Demonstrate the intelligent structure decider using heuristics."""
    print("\n" + "=" * 60)
    print("INTELLIGENT DATA STRUCTURE DECIDER DEMO")
    print("=" * 60 + "\n")
    
    decider = DataStructureDecider()
    
    # Test queries
    test_queries = [
        ("best cameras under 50000 rupees in india", "Product comparison"),
        ("top machine learning frameworks comparison", "Technical comparison"),
        ("climate change effects on agriculture summary", "Informational Report"),
        ("countries gdp per capita ranking 2024", "Ranked data"),
        ("kubernetes architecture explained", "Documentation"),
        ("startup funding rounds in india 2024", "Business data"),
    ]
    
    print(f"{'Query':<45} {'Format':<10} {'Type'}")
    print("-" * 80)
    
    for query, description in test_queries:
        # Use quick_decide which doesn't require API calls
        result = decider.quick_decide(query)
        
        query_display = (query[:42] + '...') if len(query) > 45 else query
        
        print(f"{query_display:<45} {result.value.upper():<10} {description}")
    
    print()


def demo_format_guidance():
    """Show format guidance."""
    print("\n" + "=" * 60)
    print("FORMAT GUIDANCE")
    print("=" * 60 + "\n")
    
    decider = DataStructureDecider()
    
    for format_type in DataStructureType:
        guidance = decider.get_format_guidance(format_type)
        
        if not guidance:
            continue
            
        print(f"\n{format_type.value.upper()}")
        print("-" * 40)
        print("Best For:")
        for item in guidance.get("best_for", [])[:3]:
            print(f"  - {item}")
        print(f"Characteristics: {', '.join(guidance.get('characteristics', []))}")


def main():
    """Run all demos."""
    print("\n" + "=" * 60)
    print("              RESEARCH AGENT DEMO")
    print("=" * 60 + "\n")
    
    print("This demo showcases the intelligent data structure detection")
    print("using heuristics (no API calls required).")
    print("To run full research queries with Gemini, set up your API keys.\n")
    
    # Run demos
    demo_structure_decider()
    demo_format_guidance()
    
    # Quick start guide
    print("\n" + "=" * 60)
    print("QUICK START GUIDE")
    print("=" * 60 + "\n")
    print("""
1. Set up your API keys in .env file:
   SERPER_API_KEY=your_key
   GEMINI_API_KEY=your_key

2. Install dependencies:
   pip install -r requirements.txt

3. Run your first research:
   python main.py research "best smartphones under 30000"

4. Try different formats:
   python main.py research "ml frameworks comparison" --format excel
    """)
    
    print("\nDemo completed!\n")


if __name__ == "__main__":
    main()
