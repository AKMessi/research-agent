"""
Simple data structure decider - fast heuristic-based approach.
No LLM calls needed for format selection.
"""
from dataclasses import dataclass
from typing import List
from research_agent.core.state import DataStructureType


@dataclass
class StructureRecommendation:
    recommended_format: str
    confidence: float
    reasoning: str


class DataStructureDecider:
    """Fast format detection without LLM calls."""
    
    def decide(self, query: str, context: str = "") -> StructureRecommendation:
        """Decide output format based on query analysis."""
        query_lower = query.lower()
        combined = f"{query_lower} {context.lower() if context else ''}"
        
        # Check for table/comparison keywords -> CSV
        table_keywords = ['best', 'top', 'compare', 'vs', 'ranking', 'list', 'budget', 'price']
        if any(kw in combined for kw in table_keywords):
            if any(kw in combined for kw in ['price', 'cost', '$', 'budget', 'cheap']):
                return StructureRecommendation(
                    recommended_format='csv',
                    confidence=0.9,
                    reasoning='Price comparisons work best in CSV/Excel'
                )
        
        # Check for nested/hierarchical data -> JSON
        json_keywords = ['api', 'nested', 'hierarchy', 'structure', 'schema', 'json']
        if any(kw in combined for kw in json_keywords):
            return StructureRecommendation(
                recommended_format='json',
                confidence=0.85,
                reasoning='Complex structured data works best in JSON'
            )
        
        # Check for article/report content -> Markdown
        article_keywords = ['article', 'report', 'guide', 'how to', 'tutorial', 'explained']
        if any(kw in combined for kw in article_keywords):
            return StructureRecommendation(
                recommended_format='markdown',
                confidence=0.8,
                reasoning='Articles and guides work best in Markdown'
            )
        
        # Check for print/export needs -> PDF
        pdf_keywords = ['pdf', 'print', 'document', 'report', 'official']
        if any(kw in combined for kw in pdf_keywords):
            return StructureRecommendation(
                recommended_format='pdf',
                confidence=0.8,
                reasoning='PDF for printable documents'
            )
        
        # Check for multi-sheet/complex -> Excel
        excel_keywords = ['excel', 'spreadsheet', 'sheets', 'multi', 'financial']
        if any(kw in combined for kw in excel_keywords):
            return StructureRecommendation(
                recommended_format='excel',
                confidence=0.85,
                reasoning='Excel for complex spreadsheet data'
            )
        
        # Default to CSV for most queries
        return StructureRecommendation(
            recommended_format='csv',
            confidence=0.7,
            reasoning='Default to CSV for structured data'
        )
