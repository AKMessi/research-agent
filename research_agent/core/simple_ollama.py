"""
Simple Ollama wrapper with retries and timeout handling.
"""
import requests
import json
import time
from typing import Optional

OLLAMA_URL = "http://localhost:11434/api/generate"


def ask_ollama_simple(prompt: str, model: str = "mistral", timeout: int = 60) -> Optional[str]:
    """
    Simple Ollama query with timeout.
    Returns raw response text or None on failure.
    """
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 1000,  # Limit output tokens
                }
            },
            timeout=timeout
        )
        
        if resp.status_code == 200:
            return resp.json().get("response", "")
            
    except requests.exceptions.Timeout:
        print(f"[Ollama timeout after {timeout}s]")
    except Exception as e:
        print(f"[Ollama error: {e}]")
    
    return None


def extract_products_with_ollama(query: str, sources_text: str) -> Optional[list]:
    """
    Use Ollama to extract product list from sources.
    Simplified for speed.
    """
    prompt = f"""Extract GPU products from this text about "{query}".

TEXT:
{sources_text[:2000]}

List each product with price. Format:
- Product Name: $Price (Best for: use case)

Product list:"""

    response = ask_ollama_simple(prompt, timeout=45)
    
    if not response:
        return None
    
    # Parse the list format
    products = []
    for line in response.split('\n'):
        line = line.strip()
        if line.startswith('-') or line.startswith('*'):
            # Try to extract product and price
            parts = line.replace('-', '').replace('*', '').strip().split(':')
            if len(parts) >= 1:
                name = parts[0].strip()
                price = "N/A"
                best_for = ""
                
                if len(parts) > 1:
                    rest = ':'.join(parts[1:])
                    # Extract price
                    import re
                    price_match = re.search(r'\$([0-9,]+)', rest)
                    if price_match:
                        price = f"${price_match.group(1)}"
                    # Extract best for
                    bf_match = re.search(r'Best for: ([^)]+)', rest)
                    if bf_match:
                        best_for = bf_match.group(1)
                
                products.append({
                    "name": name,
                    "price": price,
                    "best_for": best_for,
                    "why": "Extracted from research"
                })
    
    return products if products else None
