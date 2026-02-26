"""State management for the research agent."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ResearchStatus(Enum):
    """Research execution status."""
    IDLE = "idle"
    SEARCHING = "searching"
    EXTRACTING = "extracting"
    SYNTHESIZING = "synthesizing"
    FORMATTING = "formatting"
    COMPLETED = "completed"
    ERROR = "error"


class DataStructureType(Enum):
    """Types of output data structures."""
    TABLE = "table"
    LIST = "list"
    MARKDOWN = "markdown"
    CSV = "csv"
    JSON = "json"


@dataclass
class SearchResult:
    """Individual search result."""
    title: str
    link: str
    snippet: str
    position: int = 0
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
    """Current state of a research task."""
    query: str
    original_query: str = ""
    context: Optional[str] = None
    status: ResearchStatus = ResearchStatus.IDLE
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    output_format: Optional[DataStructureType] = None
    output_file_path: Optional[str] = None
    extracted_data: List[Dict] = field(default_factory=list)
    sources: List[Dict] = field(default_factory=list)
    error_message: Optional[str] = None
