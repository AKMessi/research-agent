"""Configuration management for the Research Agent."""
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
    browserbase_api_key: str = os.getenv("BROWSERBASE_API_KEY", "")
    serper_api_key: str = os.getenv("SERPER_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    firecrawl_api_key: str = os.getenv("FIRECRAWL_API_KEY", "")
    
    # Ollama Configuration
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    ollama_timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "45"))
    
    # LLM Configuration
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
    def is_browserbase_configured(self) -> bool:
        """Check if Browserbase Search API key is configured."""
        return bool(self.browserbase_api_key)

    @property
    def is_serper_configured(self) -> bool:
        """Check if Serper API key is configured."""
        return bool(self.serper_api_key)

    @property
    def is_search_configured(self) -> bool:
        """Check if any web search provider is configured."""
        return self.is_browserbase_configured or self.is_serper_configured
    
    @property
    def is_gemini_configured(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self.gemini_api_key)
    
    @property
    def is_firecrawl_configured(self) -> bool:
        """Check if Firecrawl API key is configured."""
        return bool(self.firecrawl_api_key)


# Global configuration instance
config = Config()
