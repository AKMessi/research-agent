"""
Synthesis Engine - Uses Ollama for structured extraction
"""
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import requests

from rich.console import Console

console = Console(legacy_windows=True)


class SynthesisEngine:
    """Synthesizes research findings from multiple sources."""
    
    OLLAMA_URL = "http://localhost:11434/api/generate"
    
    def __init__(self):
        self.ollama_model = self._detect_model()
    
    def _detect_model(self) -> Optional[str]:
        """Detect available Ollama model - prefer llama3.2."""
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                
                # Prefer llama3.2 (faster)
                for m in models:
                    name = m.get("name", "").lower()
                    if "llama3.2" in name:
                        console.print(f"[dim]Using Ollama: {m.get('name')}[/dim]")
                        return m.get("name")
                
                # Fallback to other fast models
                for m in models:
                    name = m.get("name", "").lower()
                    if any(x in name for x in ["mistral", "llama3.1", "llama3"]):
                        return m.get("name")
                        
        except Exception as e:
            console.print(f"[dim]Ollama not available: {e}[/dim]")
        return None
    
    def synthesize(self, query: str, sources: List[Dict]) -> Dict[str, Any]:
        """Main synthesis method."""
        if not sources:
            return {"error": "No sources found"}
        
        # Build evidence
        evidence = self._build_evidence(sources)
        
        # Try AI synthesis if available
        if self.ollama_model:
            result = self._ai_synthesis(query, evidence)
            if result:
                return result
        
        # Fallback to pattern synthesis
        return self._pattern_synthesis(query, evidence)
    
    def _build_evidence(self, sources: List[Dict]) -> str:
        """Build evidence text from sources."""
        parts = []
        for i, src in enumerate(sources[:8], 1):
            text = src.get('full_content') or src.get('snippet') or ''
            if text:
                parts.append(f"[{i}] {src.get('title', '')}\n{text[:400]}")
        return "\n---\n".join(parts)
    
    def _ai_synthesis(self, query: str, evidence: str) -> Optional[Dict]:
        """Use Ollama to extract products."""
        
        prompt = f"""Extract products from this text about "{query}".

TEXT:
{evidence[:1200]}

List product names with prices mentioned in the text.
Format: - Product Name: $Price

Product List:"""
        
        try:
            resp = requests.post(
                self.OLLAMA_URL,
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 800,
                    }
                },
                timeout=45
            )
            
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                console.print(f"[dim]LLM response: {text[:200]}...[/dim]")
                products = self._parse_product_list(text)
                console.print(f"[dim]Parsed {len(products)} products[/dim]")
                
                if products:
                    return {
                        "executive_summary": f"Found {len(products)} products",
                        "recommendations": products,
                        "key_insights": [],
                        "price_range": "Varies",
                        "avoid": []
                    }
                    
        except Exception as e:
            console.print(f"[dim]AI synthesis failed: {e}[/dim]")
        
        return None
    
    def _parse_product_list(self, text: str) -> List[Dict]:
        """Parse product list from LLM output."""
        products = []
        
        for line in text.split('\n'):
            line = line.strip()
            
            # Check if line starts with bullet or number
            if not line:
                continue
            
            # Match bullet points or numbered lists
            if not re.match(r'^[\-*•\d]', line):
                continue
            
            # Remove bullet/number (e.g., "- " or "1. " or "• ")
            line = re.sub(r'^[\-*•]?\s*\d*\.?\s*', '', line).strip()
            if not line:
                continue
            
            # Extract name and price
            name = line
            price = "N/A"
            best_for = ""
            
            # Find price with $ sign
            price_match = re.search(r'\$([0-9,]+(?:\.\d{2})?)', line)
            if price_match:
                price = f"${price_match.group(1)}"
                # Remove price from name for cleaner output
                name = re.sub(r'[:\s]*\$[0-9,]+(?:\.\d{2})?[^\w]*$', '', name).strip()
            
            # Clean up name (remove trailing colons, etc.)
            name = re.sub(r'[:\-]+\s*$', '', name).strip()
            
            # Filter out non-product items
            skip_keywords = ['http', 'www.', '.com', 'article', 'reddit', 'discussion', 
                           'thread', 'best value', 'guide', 'top', 'ranked', 'website']
            if any(kw in name.lower() for kw in skip_keywords):
                continue
            
            # Keep only items that look like products (have model numbers or known brands)
            product_keywords = [
                # Tech
                'RTX', 'GTX', 'RX', 'Arc', 'Radeon', 'GeForce', 'AMD', 'NVIDIA', 'Intel',
                'Apple', 'Samsung', 'Sony', 'Bose', 'JBL', 'Beats', 'AirPods', 'Galaxy',
                'iPhone', 'iPad', 'MacBook', 'ThinkPad', 'XPS', 'Surface', 'Pixel',
                # Audio
                'earbuds', 'headphones', 'speaker', 'soundbar', 'earphones',
                # General
                'Pro', 'Max', 'Ultra', 'Plus', 'Series', 'Gen', 'Model'
            ]
            if not any(kw.upper() in name.upper() for kw in product_keywords):
                # Also allow if it has numbers that look like model numbers
                if not re.search(r'\d{3,4}', name):
                    continue
            
            if name and len(name) > 2:
                products.append({
                    "name": name,
                    "price": price,
                    "best_for": best_for,
                    "why": "From research"
                })
        
        return products
    
    def _pattern_synthesis(self, query: str, text: str) -> Dict:
        """Pattern-based synthesis fallback."""
        products = self._find_products(text)
        
        recommendations = []
        for p in products[:8]:
            recommendations.append({
                "name": p,
                "price": "N/A",
                "best_for": "",
                "why": "Found in sources"
            })
        
        return {
            "executive_summary": f"Found {len(recommendations)} products",
            "recommendations": recommendations,
            "key_insights": [],
            "price_range": "N/A",
            "avoid": []
        }
    
    def _find_products(self, text: str) -> List[str]:
        """Find product mentions."""
        patterns = [
            r'(RTX\s+\d{3,4}(?:\s*Ti)?)',
            r'(RX\s+\d{3,4}(?:\s*XT)?)',
            r'(GTX\s+\d{3,4})',
            r'(Arc\s+[A-Z]\d{3,4})',
        ]
        
        found = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.I)
            found.update(m.strip().upper() for m in matches)
        
        return sorted(found, key=lambda x: text.upper().count(x.upper()), reverse=True)


class ReportFormatter:
    """Formats synthesis results."""
    
    @staticmethod
    def to_markdown(data: Dict, query: str) -> str:
        """Convert to Markdown."""
        lines = [
            f"# Research: {query}",
            "",
            f"**{data.get('executive_summary', '')}**",
            "",
            "## Recommendations",
        ]
        
        for rec in data.get("recommendations", []):
            lines.append(f"""
### {rec.get('name', 'Unknown')}
- **Price:** {rec.get('price', 'N/A')}
- **Best For:** {rec.get('best_for', 'N/A')}
- **Why:** {rec.get('why', '')}
""")
        
        lines.append(f"""
## Price Range
{data.get('price_range', 'N/A')}
""")
        
        return "\n".join(lines)
    
    @staticmethod
    def to_csv(data: Dict) -> str:
        """Convert to CSV."""
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["name", "price", "best_for", "why"])
        
        for rec in data.get("recommendations", []):
            writer.writerow([
                rec.get("name", ""),
                rec.get("price", ""),
                rec.get("best_for", ""),
                rec.get("why", "")
            ])
        
        return output.getvalue()
