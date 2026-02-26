"""
Ultimate Research Agent - Production-grade web research with AI synthesis.
"""

__version__ = "1.0.0"
__author__ = "Your Name"

from research_agent.core.ultimate_agent import UltimateResearchAgent, create_ultimate_agent
from research_agent.core.query_analyzer import QueryAnalyzer, OutputFormat
from research_agent.core.unified_synthesis import UnifiedSynthesisEngine, SynthesisResult

__all__ = [
    "UltimateResearchAgent",
    "create_ultimate_agent",
    "QueryAnalyzer",
    "OutputFormat",
    "UnifiedSynthesisEngine",
    "SynthesisResult",
]
