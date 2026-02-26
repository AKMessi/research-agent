"""
Markdown formatter for rich text documents.
"""
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

from research_agent.formatters.base import BaseFormatter


class MarkdownFormatter(BaseFormatter):
    """
    Formatter for Markdown output.
    Best for: Reports, articles, documentation, text-heavy content
    """
    
    @property
    def file_extension(self) -> str:
        return "md"
    
    def format(
        self, 
        data: List[Dict[str, Any]], 
        title: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format data as Markdown string."""
        lines = []
        
        # Header
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        
        # Summary
        lines.append("## Summary")
        lines.append("")
        if metadata and 'summary' in metadata:
            lines.append(metadata['summary'])
        else:
            lines.append(f"This document contains {len(data)} researched items with detailed information.")
        
        # Stats
        if metadata:
            lines.append("")
            lines.append("### Research Stats")
            lines.append(f"- **Items Found:** {len(data)}")
            if 'sources' in metadata:
                lines.append(f"- **Sources:** {len(metadata['sources'])}")
        
        lines.append("")
        
        # Table of Contents
        if len(data) > 3:
            lines.append("## Table of Contents")
            lines.append("")
            for i, item in enumerate(data, 1):
                item_title = item.get('name', f"Item {i}")
                lines.append(f"{i}. [{item_title}](#item-{i})")
            lines.append("")
        
        # Item Details
        lines.append("## Details")
        lines.append("")
        
        for i, item in enumerate(data, 1):
            item_title = item.get('name', f"Item {i}")
            
            # Item Header with anchor
            lines.append(f"### {i}. {item_title}")
            lines.append(f"<a id='item-{i}'></a>")
            lines.append("")
            
            # Dynamic specifications table
            lines.append("#### Information")
            lines.append("")
            lines.append("| Field | Value |")
            lines.append("|-------|-------|")
            
            # Display all item fields dynamically
            for key, value in item.items():
                if key != 'name' and value and value != 'N/A':
                    display_key = self._format_key(key)
                    display_value = str(value)[:100]  # Limit length
                    lines.append(f"| {display_key} | {display_value} |")
            
            lines.append("")
            
            # Separator
            lines.append("---")
            lines.append("")
        
        # Sources section
        if metadata and 'sources' in metadata:
            lines.append("## Sources")
            lines.append("")
            for source in metadata['sources'][:10]:
                title = source.get('title', 'Link')[:60]
                link = source.get('link', '#')
                lines.append(f"- [{title}]({link})")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_key(self, key: str) -> str:
        """Convert snake_case to Title Case."""
        return key.replace('_', ' ').replace('-', ' ').title()
    
    def save(
        self, 
        content: str, 
        filename: str
    ) -> Path:
        """Save Markdown content to file."""
        filepath = self.output_dir / f"{filename}.md"
        filepath.write_text(content, encoding='utf-8')
        return filepath
