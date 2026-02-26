"""
Ollama LLM Manager - Uses local Ollama instance

Ollama API Docs: https://github.com/ollama/ollama/blob/main/docs/api.md

Endpoints:
- GET  /api/tags         - List models
- POST /api/generate     - Generate completion
- POST /api/chat         - Chat completion
"""
import json
import re
from typing import Optional, List, Dict
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from research_agent.config import config
from rich.console import Console

console = Console(legacy_windows=True)


class LLMManager:
    """LLM Manager with Ollama local-first priority."""
    
    OLLAMA_BASE_URL = "http://localhost:11434"
    
    def __init__(self):
        self.ollama_available = False
        self.ollama_model = None
        
        # Detect available Ollama models
        self._detect_ollama_models()
        
        # Cloud fallback
        self.cloud_llm = None
        if config.gemini_api_key:
            self.cloud_llm = ChatGoogleGenerativeAI(
                model=config.default_llm_model,
                temperature=0.1,
                api_key=config.gemini_api_key,
                timeout=30
            )
    
    def _detect_ollama_models(self):
        """List available Ollama models."""
        try:
            resp = requests.get(
                f"{self.OLLAMA_BASE_URL}/api/tags",
                timeout=5
            )
            
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                
                if models:
                    # Priority order for models (fastest first for extraction tasks)
                    priority = ["mistral", "llama3.2", "llama3.1", "llama3", "deepseek-r1:7b", "deepseek-r1"]
                    
                    for p in priority:
                        for m in models:
                            name = m.get("name", "").lower()
                            if p in name:
                                self.ollama_available = True
                                self.ollama_model = m.get("name")
                                console.print(f"[green]Using Ollama model: {self.ollama_model}[/green]")
                                return
                    
                    # Use first available
                    self.ollama_available = True
                    self.ollama_model = models[0].get("name")
                    console.print(f"[green]Using Ollama model: {self.ollama_model}[/green]")
                    
        except requests.exceptions.ConnectionError:
            console.print("[yellow]Ollama not running on localhost:11434[/yellow]")
        except Exception as e:
            console.print(f"[dim]Ollama detection error: {e}[/dim]")
    
    def _generate_ollama(self, prompt: str) -> Optional[str]:
        """
        Generate using Ollama /api/generate endpoint.
        
        Request format:
        {
            "model": "model-name",
            "prompt": "...",
            "stream": false,
            "options": {
                "temperature": 0.1
            }
        }
        """
        try:
            resp = requests.post(
                f"{self.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 2000,
                        "num_ctx": 4096,
                    }
                },
                timeout=30  # 30 second timeout for local models
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "")
            else:
                console.print(f"[dim]Ollama error: {resp.status_code}[/dim]")
                
        except requests.exceptions.Timeout:
            console.print("[yellow]Ollama request timed out[/yellow]")
        except Exception as e:
            console.print(f"[dim]Ollama error: {e}[/dim]")
        
        return None
    
    def _chat_ollama(self, messages: List[Dict]) -> Optional[str]:
        """
        Chat using Ollama /api/chat endpoint.
        
        Request format:
        {
            "model": "model-name",
            "messages": [
                {"role": "user", "content": "..."}
            ],
            "stream": false
        }
        """
        try:
            resp = requests.post(
                f"{self.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": self.ollama_model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 4000,
                    }
                },
                timeout=180
            )
            
            if resp.status_code == 200:
                data = resp.json()
                message = data.get("message", {})
                return message.get("content", "")
                
        except Exception as e:
            console.print(f"[dim]Ollama chat error: {e}[/dim]")
        
        return None
    
    def extract_structured(self, prompt: str) -> Optional[List[Dict]]:
        """
        Extract structured data using Ollama or cloud fallback.
        """
        # TIER 1: Ollama
        if self.ollama_available and self.ollama_model:
            console.print(f"[dim]Using Ollama ({self.ollama_model})...[/dim]")
            
            response = self._generate_ollama(prompt)
            
            if response:
                # Parse JSON
                try:
                    match = re.search(r'\[.*\]', response, re.DOTALL)
                    if match:
                        data = json.loads(match.group())
                        if isinstance(data, list) and len(data) > 0:
                            console.print(f"[green]Ollama extracted {len(data)} items[/green]")
                            return data
                except json.JSONDecodeError:
                    console.print("[dim]Ollama response not valid JSON, trying fallback[/dim]")
        
        # TIER 2: Cloud LLM
        if self.cloud_llm:
            console.print("[dim]Using Gemini (cloud fallback)...[/dim]")
            try:
                response = self.cloud_llm.invoke(prompt)
                text = response.content
                
                match = re.search(r'\[.*\]', text, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    if isinstance(data, list) and len(data) > 0:
                        return data
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e):
                    console.print("[yellow]Gemini rate limited[/yellow]")
        
        return None
    
    def get_status(self) -> Dict:
        """Get current LLM status."""
        return {
            "ollama": {
                "available": self.ollama_available,
                "model": self.ollama_model,
            },
            "gemini": {
                "available": self.cloud_llm is not None,
            }
        }


# Singleton
_llm_manager = None

def get_llm_manager() -> LLMManager:
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager
