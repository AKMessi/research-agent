"""
Configuration management for the Research Agent.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Config:
    """Application configuration."""
    
    # API Keys
    serper_api_key: str = os.getenv("SERPER_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    firecrawl_api_key: str = os.getenv("FIRECRAWL_API_KEY", "")
    
    # LLM Configuration
    default_llm_model: str = os.getenv("DEFAULT_LLM_MODEL", "gemini-2.5-flash")
    temperature: float = float(os.getenv("TEMPERATURE", "0.3"))
    
    # Search Configuration
    max_search_results: int = int(os.getenv("MAX_SEARCH_RESULTS", "10"))
    
    # Output Configuration
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "./research_agent/outputs"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    def __post_init__(self):
        """Ensure output directory exists."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def is_serper_configured(self) -> bool:
        """Check if Serper API key is configured."""
        return bool(self.serper_api_key)
    
    @property
    def is_gemini_configured(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self.gemini_api_key)


# Global configuration instance
config = Config()
