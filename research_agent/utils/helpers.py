"""
Utility helper functions.
"""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitize a string to be used as a filename.
    
    Args:
        filename: Original filename
        max_length: Maximum length of the filename
    
    Returns:
        Sanitized filename
    """
    # Replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Replace multiple spaces/underscores
    sanitized = re.sub(r'[\s_]+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized or "output"


def get_timestamp() -> str:
    """Get current timestamp string."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def ensure_dir(path: Path) -> Path:
    """
    Ensure directory exists.
    
    Args:
        path: Directory path
    
    Returns:
        Path object
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to maximum length.
    
    Args:
        s: Original string
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def count_tokens_approx(text: str) -> int:
    """
    Approximate token count for text.
    
    Args:
        text: Input text
    
    Returns:
        Approximate token count
    """
    # Rough approximation: ~4 characters per token
    return len(text) // 4


def format_number(num: float, decimals: int = 2) -> str:
    """
    Format a number with thousand separators.
    
    Args:
        num: Number to format
        decimals: Decimal places
    
    Returns:
        Formatted string
    """
    return f"{num:,.{decimals}f}"
