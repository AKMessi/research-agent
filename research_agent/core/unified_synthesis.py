"""
Unified Synthesis Engine - Handles all research types
"""
import re
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import requests

from rich.console import Console
from research_agent.core.query_analyzer import QueryAnalyzer, ResearchDomain, OutputFormat
from research_agent.core.synthesis_prompts import SynthesisPrompts

console = Console(legacy_windows=True)


@dataclass
class SynthesisResult:
    """Result of synthesis."""
    domain: str
    format: str
    content: Dict[str, Any]
    sources_used: int
    confidence: float


class UnifiedSynthesisEngine:
    """Universal synthesis engine for any research type."""
    
    OLLAMA_URL = "http://localhost:11434/api/generate"
    
    def __init__(self):
        self.analyzer = QueryAnalyzer()
        self.ollama_model = self._detect_model()
    
    def _detect_model(self) -> Optional[str]:
        """Detect available Ollama model."""
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                
                # Prefer faster models
                for preferred in ["llama3.2", "llama3.1", "mistral"]:
                    for m in models:
                        if preferred in m.get("name", "").lower():
                            return m.get("name")
                
                if models:
                    return models[0].get("name")
        except:
            pass
        return None
    
    def synthesize(self, query: str, sources: List[Dict]) -> SynthesisResult:
        """
        Main synthesis method - automatically handles any query type.
        """
        # Step 1: Analyze query
        analysis = self.analyzer.analyze(query)
        console.print(f"[dim]{analysis.reasoning}[/dim]")
        console.print(f"[dim]Output format: {analysis.output_format.value}[/dim]")
        
        if not sources:
            return SynthesisResult(
                domain=analysis.domain.value,
                format=analysis.output_format.value,
                content={"error": "No sources found"},
                sources_used=0,
                confidence=0
            )
        
        # Step 2: Build evidence
        evidence = self._build_evidence(sources)
        
        # Step 3: Get appropriate prompt
        prompt = SynthesisPrompts.get_prompt(
            analysis.domain.value,
            query,
            evidence
        )
        
        # Step 4: Synthesize with AI
        content = self._ai_synthesize(prompt, analysis.output_format)
        
        # Step 5: Parse based on format
        parsed_content = self._parse_response(
            content,
            analysis.output_format,
            analysis.domain
        )
        
        return SynthesisResult(
            domain=analysis.domain.value,
            format=analysis.output_format.value,
            content=parsed_content,
            sources_used=len(sources),
            confidence=analysis.confidence
        )
    
    def _build_evidence(self, sources: List[Dict]) -> str:
        """Build formatted evidence from sources."""
        parts = []
        for i, src in enumerate(sources[:8], 1):
            title = src.get('title', '')
            text = src.get('full_content') or src.get('snippet') or ''
            
            # Extract key sentences
            sentences = re.split(r'(?<=[.!?])\s+', text)
            key_sentences = [s for s in sentences if 30 < len(s) < 200][:2]
            
            if key_sentences:
                parts.append(f"[{i}] {title}\n{' '.join(key_sentences)}")
        
        return "\n\n".join(parts)
    
    def _ai_synthesize(self, prompt: str, output_format: OutputFormat) -> str:
        """Use Ollama to synthesize."""
        if not self.ollama_model:
            return ""
        
        try:
            resp = requests.post(
                self.OLLAMA_URL,
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 2000,
                    }
                },
                timeout=60
            )
            
            if resp.status_code == 200:
                return resp.json().get("response", "")
                
        except Exception as e:
            console.print(f"[dim]AI synthesis error: {e}[/dim]")
        
        return ""
    
    def _parse_response(self, text: str, fmt: OutputFormat, domain: ResearchDomain) -> Dict:
        """Parse AI response based on format."""
        if not text:
            return {"error": "No synthesis generated"}
        
        # Try to extract structured data based on format
        if fmt == OutputFormat.TABLE:
            return self._parse_table(text)
        elif fmt == OutputFormat.PROFILES:
            return self._parse_profiles(text)
        elif fmt == OutputFormat.TIMELINE:
            return self._parse_timeline(text)
        else:
            # Report/List format
            return {
                "content": text,
                "sections": self._split_sections(text)
            }
    
    def _parse_table(self, text: str) -> Dict:
        """Parse table format (products, comparisons)."""
        items = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Match bullet or numbered items
            if not re.match(r'^[\-*•\d]', line):
                continue
            
            # Clean up
            line = re.sub(r'^[\-*•\d\.\s]*', '', line).strip()
            if not line or len(line) < 5:
                continue
            
            # Extract fields
            name = line
            price = "N/A"
            best_for = ""
            features = ""
            
            # Find price
            price_match = re.search(r'\$([0-9,]+)', line)
            if price_match:
                price = f"${price_match.group(1)}"
                name = re.sub(r'[\s:]*\$[0-9,]+', '', name).strip()
            
            # Extract "Best for"
            bf_match = re.search(r'[Bb]est for[:\s]+([^|]+)', line)
            if bf_match:
                best_for = bf_match.group(1).strip()
                name = re.sub(r'[Bb]est for[:\s]+[^|]+', '', name).strip()
            
            # Extract "Features"
            f_match = re.search(r'[Ff]eatures?[:\s]+(.+)$', line)
            if f_match:
                features = f_match.group(1).strip()
            
            # Clean name
            name = re.sub(r'[\|\-]+$', '', name).strip()
            
            if name and len(name) > 2:
                items.append({
                    "name": name,
                    "price": price,
                    "best_for": best_for,
                    "features": features
                })
        
        return {
            "items": items,
            "count": len(items),
            "raw": text
        }
    
    def _parse_profiles(self, text: str) -> Dict:
        """Parse profile format (people, companies)."""
        profiles = []
        
        # Split by double newlines or headers
        sections = re.split(r'\n\n+|(?=^[A-Z][^\n:]+:$)', text, flags=re.MULTILINE)
        
        for section in sections:
            lines = section.strip().split('\n')
            if not lines:
                continue
            
            name = lines[0].strip()
            if len(name) < 2 or name.endswith(':'):
                continue
            
            profile = {
                "name": name,
                "details": '\n'.join(lines[1:]) if len(lines) > 1 else ""
            }
            profiles.append(profile)
        
        return {
            "profiles": profiles,
            "count": len(profiles),
            "raw": text
        }
    
    def _parse_timeline(self, text: str) -> Dict:
        """Parse timeline format (events, news)."""
        events = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Look for dates
            date_match = re.search(r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}|January|February|March|April|May|June|July|August|September|October|November|December)', line, re.I)
            
            event = {
                "description": line,
                "date": date_match.group(1) if date_match else ""
            }
            events.append(event)
        
        return {
            "events": events,
            "raw": text
        }
    
    def _split_sections(self, text: str) -> Dict[str, str]:
        """Split report into sections."""
        sections = {}
        current_section = "Overview"
        current_content = []
        
        for line in text.split('\n'):
            # Check for section header
            if re.match(r'^[A-Z][A-Z\s]+:$|^[A-Z][a-z]+.*:$', line.strip()):
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = line.strip().rstrip(':')
                current_content = []
            else:
                current_content.append(line)
        
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
