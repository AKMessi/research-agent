"""
Pattern-based extraction - Tier 3 fallback that always works.
Extracts structured data using regex patterns when LLMs fail.
"""
import re
from typing import List, Dict, Any


class PatternExtractor:
    """Extracts structured data using regex patterns."""
    
    # Price patterns
    PRICE_PATTERNS = [
        r'\$([0-9,]+(?:\.[0-9]{2})?)',
        r'([0-9,]+)\s*(?:USD|dollars?)',
        r'price[d\s]*[:\s]*\$?([0-9,]+)',
        r'cost[s\s]*[:\s]*\$?([0-9,]+)',
    ]
    
    # Rating patterns
    RATING_PATTERNS = [
        r'([0-9]\.[0-9])\s*/\s*5',
        r'([0-9]\.[0-9])\s*out of\s*5',
        r'rating[d\s]*[:\s]*([0-9]\.[0-9])',
        r'score[d\s]*[:\s]*([0-9]\.[0-9])',
    ]
    
    # GPU/CPU model patterns
    HARDWARE_PATTERNS = [
        r'(RTX\s+\d{3,4}(?:\s*Ti)?)',
        r'(RX\s+\d{3,4}(?:\s*XT)?)',
        r'(GTX\s+\d{3,4})',
        r'(Arc\s+[A-Z]\d{3,4})',
        r'(Core\s+i\d+-\d{4,5}[A-Z]?)',
        r'(Ryzen\s+\d\s+\d{4,5}X?)',
    ]
    
    # Common specs
    SPEC_PATTERNS = {
        "vram": r'(\d{1,3})\s*GB\s*(?:VRAM|memory|GDDR)',
        "memory": r'(\d{1,3})\s*GB\s*(?:RAM|memory)',
        "storage": r'(\d{1,4})\s*(?:GB|TB)\s*(?:SSD|storage)',
        "screen": r'(\d{1,2}\.\d)"|(\d{1,2})-inch',
        "battery": r'(\d{1,5})\s*mAh',
    }
    
    @classmethod
    def extract_products(cls, search_results: List[Any]) -> List[Dict]:
        """
        Extract product information from search results using patterns.
        This is the TIER 3 fallback - always works, no AI needed.
        """
        products = []
        seen = set()
        
        for result in search_results:
            text = ""
            if hasattr(result, 'full_content') and result.full_content:
                text = result.full_content
            elif hasattr(result, 'snippet') and result.snippet:
                text = result.snippet
            elif hasattr(result, 'title') and result.title:
                text = result.title
            
            if not text:
                continue
            
            text = text[:3000]  # Limit text length
            
            # Try to find hardware models in the text
            found_models = []
            for pattern in cls.HARDWARE_PATTERNS:
                matches = re.findall(pattern, text, re.IGNORECASE)
                found_models.extend(matches)
            
            # If no hardware models found, use the title as product name
            if not found_models:
                title = result.title if hasattr(result, 'title') else "Unknown"
                # Clean up title
                title = re.sub(r'\|.*$', '', title)  # Remove site name
                title = re.sub(r'[\-\:].*$', '', title)  # Remove after dash/colon
                title = title.strip()
                if title and title.lower() not in seen:
                    seen.add(title.lower())
                    products.append({
                        "name": title,
                        "brand": cls._extract_brand(text),
                        "price": cls._extract_price(text),
                        "key_specs": cls._extract_specs(text),
                        "rating": cls._extract_rating(text),
                        "source": result.link if hasattr(result, 'link') else ""
                    })
            else:
                # Extract each model found
                for model in found_models:
                    model_clean = model.strip()
                    if model_clean.lower() in seen:
                        continue
                    seen.add(model_clean.lower())
                    
                    # Find context around this model
                    context_match = re.search(
                        r'.{0,200}' + re.escape(model_clean) + r'.{0,300}',
                        text,
                        re.IGNORECASE
                    )
                    context = context_match.group(0) if context_match else text[:500]
                    
                    products.append({
                        "name": model_clean,
                        "brand": cls._extract_brand(context) or cls._extract_brand(text),
                        "price": cls._extract_price(context),
                        "key_specs": cls._extract_specs(context),
                        "rating": cls._extract_rating(context),
                        "source": result.link if hasattr(result, 'link') else ""
                    })
        
        # Remove duplicates and sort by completeness
        products = cls._deduplicate(products)
        products = cls._rank_by_quality(products)
        
        return products[:10]
    
    @classmethod
    def _extract_price(cls, text: str) -> str:
        """Extract price from text."""
        for pattern in cls.PRICE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                price = match.group(1).replace(',', '')
                try:
                    val = float(price)
                    if 10 <= val <= 50000:  # Reasonable price range
                        return f"${int(val)}"
                except:
                    pass
        return "N/A"
    
    @classmethod
    def _extract_rating(cls, text: str) -> str:
        """Extract rating from text."""
        for pattern in cls.RATING_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return "N/A"
    
    @classmethod
    def _extract_brand(cls, text: str) -> str:
        """Extract brand from text."""
        brands = ["NVIDIA", "AMD", "Intel", "Apple", "Samsung", "Sony", "Dell", "HP", "Lenovo", "Asus"]
        text_upper = text.upper()
        for brand in brands:
            if brand in text_upper:
                return brand
        return "N/A"
    
    @classmethod
    def _extract_specs(cls, text: str) -> List[str]:
        """Extract specifications from text."""
        specs = []
        
        for spec_name, pattern in cls.SPEC_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] or match[1]
                if match:
                    specs.append(f"{spec_name}: {match}")
        
        return specs if specs else ["N/A"]
    
    @classmethod
    def _deduplicate(cls, products: List[Dict]) -> List[Dict]:
        """Remove duplicate products."""
        seen = set()
        unique = []
        
        for p in products:
            name = p.get("name", "").lower().strip()
            # Normalize name for deduplication
            name = re.sub(r'\s+', ' ', name)
            if name and name not in seen and len(name) > 3:
                seen.add(name)
                unique.append(p)
        
        return unique
    
    @classmethod
    def _rank_by_quality(cls, products: List[Dict]) -> List[Dict]:
        """Rank products by data completeness."""
        def score(p):
            s = 0
            if p.get("price") and p["price"] != "N/A":
                s += 3
            if p.get("rating") and p["rating"] != "N/A":
                s += 2
            if p.get("key_specs") and p["key_specs"] != ["N/A"]:
                s += 2
            if p.get("brand") and p["brand"] != "N/A":
                s += 1
            return s
        
        return sorted(products, key=score, reverse=True)
