"""
Professional Extractor - The RIGHT way to structure data

Strategy:
1. Collect ALL sources
2. Use LLM to extract SPECIFIC fields with examples
3. Multi-pass extraction (extract -> validate -> enrich)
4. Deduplicate intelligently
5. Output clean, consistent structure
"""
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
from rich.console import Console

console = Console(legacy_windows=True)


@dataclass
class ExtractionField:
    name: str
    type: str
    description: str
    example: str
    required: bool = True


# Define EXACT schemas for different domains
PRODUCT_SCHEMA = [
    ExtractionField("name", "string", "Full product name with model", "NVIDIA RTX 4060 Ti 8GB", True),
    ExtractionField("brand", "string", "Brand/Manufacturer", "NVIDIA", True),
    ExtractionField("price", "string", "Current price", "$399", False),
    ExtractionField("rating", "number", "Rating out of 5", "4.5", False),
    ExtractionField("best_for", "string", "Who/what this is ideal for", "1080p gaming, ML beginners", False),
    ExtractionField("key_specs", "array", "Key specifications", "[\"8GB VRAM\", \"DLSS 3\", \"115W TDP\"]", False),
    ExtractionField("pros", "array", "Advantages", "[\"Great value\", \"Low power\"]", False),
    ExtractionField("cons", "array", "Disadvantages", "[\"Only 8GB VRAM\"]", False),
    ExtractionField("source", "string", "Source URL", "https://...", False),
]


class ProfessionalExtractor:
    """
    Professional multi-pass extraction that produces quality output.
    """
    
    def __init__(self, llm_manager):
        self.llm = llm_manager
    
    def extract(self, query: str, sources: List[Dict]) -> List[Dict]:
        """
        Main extraction pipeline with fallback.
        """
        if not sources:
            return []
        
        # Build rich context
        context = self._build_context(sources)
        
        # Pass 1: Try LLM extraction (quick timeout)
        raw_items = self._extract_raw(query, context)
        
        # If LLM fails/times out, use pattern extraction (much faster)
        if not raw_items:
            console.print("[dim]LLM slow/unavailable, using fast pattern extraction...[/dim]")
            raw_items = self._pattern_extract(query, sources)
        
        if not raw_items:
            return []
        
        # Pass 2: Validate & Clean
        clean_items = self._validate_and_clean(raw_items)
        
        # Pass 3: Deduplicate
        unique_items = self._deduplicate(clean_items)
        
        # Pass 4: Rank by quality
        ranked = self._rank_by_quality(unique_items)
        
        return ranked[:10]  # Top 10
    
    def _build_context(self, sources: List[Dict]) -> str:
        """Build rich context from all sources."""
        parts = []
        for i, src in enumerate(sources[:15], 1):  # Use top 15 sources
            title = src.get('title', '')
            text = src.get('full_content') or src.get('snippet') or ''
            url = src.get('link', '')
            
            if text:
                parts.append(f"""
[{i}] {title}
URL: {url}
{text[:800]}
---""")
        
        return "\n".join(parts)
    
    def _extract_raw(self, query: str, context: str) -> List[Dict]:
        """
        Extract raw items using LLM with CLEAR instructions and examples.
        """
        # Build field descriptions with examples
        fields_desc = []
        for f in PRODUCT_SCHEMA:
            req = "REQUIRED" if f.required else "optional"
            fields_desc.append(
                f'    "{f.name}": {f.type}  // {f.description}. Example: {f.example} [{req}]'
            )
        
        prompt = f"""You are a product research expert. Extract specific products from the research sources.

QUERY: "{query}"

EXTRACTION RULES:
1. Extract ONLY real, specific products mentioned in the sources
2. Include model numbers and versions (e.g., "RTX 4060 Ti" not just "NVIDIA GPU")
3. Use "N/A" for missing optional fields - never guess
4. For arrays, use proper JSON: ["item1", "item2"]
5. Price should include $ sign: "$399"
6. Rating should be number: 4.5
7. Extract 5-10 distinct products minimum

OUTPUT FORMAT - JSON array of objects:
[
{chr(10).join(fields_desc)}
]

SOURCES:
{context[:4000]}

IMPORTANT: Return ONLY a JSON array. No explanations, no markdown formatting."""
        
        # Try extraction
        result = self.llm.extract_structured(prompt)
        
        if result and isinstance(result, list):
            return result
        
        return []
    
    def _pattern_extract(self, query: str, sources: List[Dict]) -> List[Dict]:
        """
        Pattern-based extraction when LLM fails.
        Extracts GPU/product models with associated data.
        """
        items = []
        seen = set()
        
        # Product patterns
        patterns = [
            r'(RTX\s+\d{3,4}(?:\s*Ti)?)',
            r'(RX\s+\d{3,4}(?:\s*XT)?)',
            r'(GTX\s+\d{3,4})',
            r'(Arc\s+[A-Z]\d{3,4})',
        ]
        
        for src in sources:
            text = src.get('full_content') or src.get('snippet') or ''
            title = src.get('title', '')
            url = src.get('link', '')
            
            if not text:
                continue
            
            # Find all product mentions
            found_products = []
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                found_products.extend(matches)
            
            # Extract details for each product
            for product in found_products:
                product_clean = product.strip().upper()
                
                # Deduplicate
                if product_clean.lower() in seen:
                    continue
                seen.add(product_clean.lower())
                
                # Find context around this product
                context_match = re.search(
                    r'.{0,300}' + re.escape(product) + r'.{0,400}',
                    text,
                    re.IGNORECASE
                )
                context = context_match.group(0) if context_match else text[:700]
                
                # Extract price
                price = "N/A"
                price_match = re.search(r'\$([0-9,]+)', context)
                if price_match:
                    try:
                        val = float(price_match.group(1).replace(',', ''))
                        if 50 <= val <= 10000:
                            price = f"${int(val)}"
                    except:
                        pass
                
                # Extract rating
                rating = "N/A"
                rating_match = re.search(r'([0-9]\.[0-9])\s*/\s*5', context)
                if rating_match:
                    rating = rating_match.group(1)
                
                # Determine brand
                brand = "N/A"
                if 'RTX' in product_clean or 'GTX' in product_clean:
                    brand = "NVIDIA"
                elif 'RX' in product_clean:
                    brand = "AMD"
                elif 'ARC' in product_clean:
                    brand = "Intel"
                
                # Build item
                items.append({
                    "name": product_clean,
                    "brand": brand,
                    "price": price,
                    "rating": rating,
                    "best_for": self._extract_best_for(context),
                    "key_specs": self._extract_specs(context),
                    "pros": [],
                    "cons": [],
                    "source": url
                })
        
        return items
    
    def _extract_best_for(self, text: str) -> str:
        """Extract use case from text."""
        patterns = [
            r'best for\s+([^\.]+)',
            r'ideal for\s+([^\.]+)',
            r'great for\s+([^\.]+)',
            r'perfect for\s+([^\.]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:100]
        return "N/A"
    
    def _extract_specs(self, text: str) -> List[str]:
        """Extract specs from text."""
        specs = []
        
        # VRAM
        vram_match = re.search(r'(\d{1,3})\s*GB\s*(?:VRAM|GDDR)', text, re.IGNORECASE)
        if vram_match:
            specs.append(f"{vram_match.group(1)}GB VRAM")
        
        # TDP
        tdp_match = re.search(r'(\d{2,4})W', text)
        if tdp_match:
            specs.append(f"{tdp_match.group(1)}W TDP")
        
        # Architecture
        arch_match = re.search(r'(Ada Lovelace|RDNA \d|Ampere)', text, re.IGNORECASE)
        if arch_match:
            specs.append(arch_match.group(1))
        
        return specs if specs else ["N/A"]
    
    def _validate_and_clean(self, items: List[Dict]) -> List[Dict]:
        """Validate items against schema and clean."""
        valid = []
        required_fields = [f.name for f in PRODUCT_SCHEMA if f.required]
        
        for item in items:
            if not isinstance(item, dict):
                continue
            
            # Check required fields
            has_required = all(
                item.get(f) and item.get(f) != "N/A" 
                for f in required_fields
            )
            
            if not has_required:
                continue
            
            # Clean the item
            cleaned = {}
            for field in PRODUCT_SCHEMA:
                value = item.get(field.name)
                
                # Handle missing
                if value is None or value == "":
                    value = "N/A" if not field.required else None
                
                # Type conversion
                if field.type == "array" and not isinstance(value, list):
                    if isinstance(value, str) and value != "N/A":
                        value = [v.strip() for v in value.split(",") if v.strip()]
                    else:
                        value = ["N/A"]
                
                cleaned[field.name] = value
            
            # Only add if all required present
            if all(cleaned.get(f) for f in required_fields):
                valid.append(cleaned)
        
        return valid
    
    def _deduplicate(self, items: List[Dict]) -> List[Dict]:
        """Intelligent deduplication."""
        seen = {}
        
        for item in items:
            name = item.get("name", "").lower().strip()
            
            # Normalize name for comparison
            name_clean = re.sub(r'\s+', ' ', name)
            name_clean = re.sub(r'[^\w\s]', '', name_clean)
            
            if not name_clean or len(name_clean) < 3:
                continue
            
            # Check if similar name already exists
            is_duplicate = False
            for existing_name in list(seen.keys()):
                # Exact match
                if name_clean == existing_name:
                    is_duplicate = True
                    # Merge better data
                    seen[existing_name] = self._merge_items(seen[existing_name], item)
                    break
                
                # Contains match (e.g., "RTX 4060" vs "NVIDIA RTX 4060")
                if name_clean in existing_name or existing_name in name_clean:
                    if len(name_clean) > len(existing_name) * 0.7:  # 70% similarity
                        is_duplicate = True
                        seen[existing_name] = self._merge_items(seen[existing_name], item)
                        break
            
            if not is_duplicate:
                seen[name_clean] = item
        
        return list(seen.values())
    
    def _merge_items(self, item1: Dict, item2: Dict) -> Dict:
        """Merge two items, keeping the best data from each."""
        merged = dict(item1)
        
        for key, value in item2.items():
            # Prefer non-N/A values
            if value and value != "N/A":
                if key not in merged or merged[key] == "N/A":
                    merged[key] = value
                # For arrays, combine
                elif isinstance(merged[key], list) and isinstance(value, list):
                    merged[key] = list(set(merged[key] + value))
        
        return merged
    
    def _rank_by_quality(self, items: List[Dict]) -> List[Dict]:
        """Rank items by data completeness."""
        def score(item):
            s = 0
            # Name and brand (required)
            if item.get("name") and item["name"] != "N/A":
                s += 2
            if item.get("brand") and item["brand"] != "N/A":
                s += 2
            
            # Price (very valuable)
            if item.get("price") and item["price"] != "N/A":
                s += 3
            
            # Rating
            if item.get("rating") and item["rating"] != "N/A":
                s += 2
            
            # Specs
            if item.get("key_specs") and item["key_specs"] != ["N/A"]:
                s += 2
            
            # Pros/cons
            if item.get("pros") and item["pros"] != ["N/A"]:
                s += 1
            
            return s
        
        return sorted(items, key=score, reverse=True)
