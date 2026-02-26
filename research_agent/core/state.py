"""
State management for the Research Agent using LangGraph.
"""
from typing import Annotated, Any, Optional, List, Dict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import operator


class DataStructureType(str, Enum):
    """Supported data structure types."""
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    MARKDOWN = "markdown"
    PDF = "pdf"
    HTML = "html"
    
    @classmethod
    def from_string(cls, value: str) -> "DataStructureType":
        """Parse DataStructureType from string (case-insensitive)."""
        value_lower = value.lower().strip()
        try:
            return cls(value_lower)
        except ValueError:
            # Default to markdown if invalid
            return cls.MARKDOWN


class ResearchStatus(str, Enum):
    """Research workflow status."""
    IDLE = "idle"
    ANALYZING = "analyzing"
    SEARCHING = "searching"
    EXTRACTING = "extracting"
    STRUCTURING = "structuring"
    FORMATTING = "formatting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SearchResult:
    """Individual search result."""
    title: str
    link: str
    snippet: str
    position: int
    source: str = "google"
    full_content: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "link": self.link,
            "snippet": self.snippet,
            "position": self.position,
            "source": self.source,
        }


@dataclass
class ResearchState:
    """
    Main state object for the research workflow.
    
    This state is passed between nodes in the LangGraph.
    """
    # Input
    query: str = ""
    original_query: str = ""
    context: Optional[str] = None
    
    # Analysis
    query_intent: str = ""
    query_category: str = ""
    data_structure_recommended: Optional[DataStructureType] = None
    reasoning: str = ""
    
    # Research
    search_queries: List[str] = field(default_factory=list)
    search_results: List[SearchResult] = field(default_factory=list)
    extracted_data: List[Dict[str, Any]] = field(default_factory=list)
    
    # Structure
    schema: Dict[str, Any] = field(default_factory=dict)
    column_headers: List[str] = field(default_factory=list)
    
    # Output
    output_content: Any = None
    output_file_path: Optional[str] = None
    output_format: Optional[DataStructureType] = None
    
    # Metadata
    status: ResearchStatus = ResearchStatus.IDLE
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    iteration_count: int = 0
    max_iterations: int = 3
    
    def get_duration(self) -> Optional[float]:
        """Get research duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def to_summary(self) -> Dict[str, Any]:
        """Generate a summary of the research state."""
        return {
            "query": self.query,
            "intent": self.query_intent,
            "category": self.query_category,
            "recommended_format": self.data_structure_recommended.value if self.data_structure_recommended else None,
            "status": self.status.value,
            "search_results_count": len(self.search_results),
            "extracted_items_count": len(self.extracted_data),
            "output_file": self.output_file_path,
            "duration_seconds": self.get_duration(),
        }


def merge_states(left: ResearchState, right: ResearchState) -> ResearchState:
    """Merge two states - used for state updates."""
    # For simplicity, we just return the right state (newer)
    # In complex scenarios, we might want to merge specific fields
    return right
