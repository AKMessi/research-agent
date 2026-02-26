"""
JSON formatter for hierarchical/nested data.
"""
import json
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

from research_agent.formatters.base import BaseFormatter


class JSONFormatter(BaseFormatter):
    """
    Formatter for JSON output.
    Best for: API-like data, nested structures, hierarchical data, configurations
    """
    
    @property
    def file_extension(self) -> str:
        return "json"
    
    def format(
        self, 
        data: List[Dict[str, Any]], 
        title: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format data as JSON string."""
        output = {
            "title": title,
            "generated_at": datetime.now().isoformat(),
            "count": len(data),
            "data": data
        }
        
        if metadata:
            output["metadata"] = metadata
        
        return json.dumps(output, indent=2, ensure_ascii=False, default=str)
    
    def save(
        self, 
        content: str, 
        filename: str
    ) -> Path:
        """Save JSON content to file."""
        filepath = self.output_dir / f"{filename}.json"
        filepath.write_text(content, encoding='utf-8')
        return filepath


class JSONLinesFormatter(BaseFormatter):
    """
    Formatter for JSON Lines (JSONL) output.
    Best for: Large datasets, streaming data, log-like data
    """
    
    @property
    def file_extension(self) -> str:
        return "jsonl"
    
    def format(
        self, 
        data: List[Dict[str, Any]], 
        title: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format data as JSON Lines string."""
        lines = []
        for item in data:
            lines.append(json.dumps(item, ensure_ascii=False, default=str))
        return "\n".join(lines)
    
    def save(
        self, 
        content: str, 
        filename: str
    ) -> Path:
        """Save JSONL content to file."""
        filepath = self.output_dir / f"{filename}.jsonl"
        filepath.write_text(content, encoding='utf-8')
        return filepath
