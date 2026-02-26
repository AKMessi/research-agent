"""
Base formatter interface.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path


class BaseFormatter(ABC):
    """Base class for all output formatters."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension for this format."""
        pass
    
    @abstractmethod
    def format(
        self, 
        data: List[Dict[str, Any]], 
        title: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format data and return as string/content.
        
        Args:
            data: List of dictionaries containing the data
            title: Title/filename for the output
            metadata: Optional metadata to include
        
        Returns:
            Formatted content as string
        """
        pass
    
    def save(
        self, 
        content: str, 
        filename: str
    ) -> Path:
        """
        Save formatted content to file.
        
        Args:
            content: Formatted content string
            filename: Base filename (without extension)
        
        Returns:
            Path to saved file
        """
        filepath = self.output_dir / f"{filename}.{self.file_extension}"
        filepath.write_text(content, encoding='utf-8')
        return filepath
    
    def format_and_save(
        self, 
        data: List[Dict[str, Any]], 
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Format data and save to file.
        
        Args:
            data: List of dictionaries containing the data
            filename: Base filename
            metadata: Optional metadata
        
        Returns:
            Path to saved file
        """
        content = self.format(data, filename, metadata)
        return self.save(content, filename)
