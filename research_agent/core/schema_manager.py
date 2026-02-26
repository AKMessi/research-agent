"""
Dynamic Schema Manager - Intelligently structures data based on query type.

This is the KEY differentiator - we analyze the query, determine the domain,
and extract structured data with appropriate fields.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import re


class DomainType(Enum):
    PRODUCT = "product"           # Physical products (laptops, cameras, etc.)
    SOFTWARE = "software"         # Apps, tools, software
    SERVICE = "service"           # Services (hotels, restaurants, etc.)
    PERSON = "person"             # People (experts, influencers, etc.)
    PLACE = "place"               # Locations (cities, countries, tourist spots)
    COMPANY = "company"           # Companies, startups
    EVENT = "event"               # Conferences, events
    COMPARISON = "comparison"     # Ranked comparisons
    ARTICLE = "article"           # General articles/info


@dataclass
class FieldSchema:
    name: str
    type: str  # string, number, array, boolean
    description: str
    required: bool = False
    example: str = ""


@dataclass
class DomainSchema:
    domain: DomainType
    name: str
    description: str
    fields: List[FieldSchema]
    indicators: List[str]  # Keywords that indicate this domain


# Domain-specific schemas for intelligent extraction
DOMAIN_SCHEMAS = {
    DomainType.PRODUCT: DomainSchema(
        domain=DomainType.PRODUCT,
        name="Product",
        description="Physical products like electronics, appliances, etc.",
        fields=[
            FieldSchema("name", "string", "Product name including model", True, "iPhone 15 Pro"),
            FieldSchema("brand", "string", "Brand/Manufacturer", True, "Apple"),
            FieldSchema("price", "string", "Current price with currency", False, "$999"),
            FieldSchema("category", "string", "Product category", False, "Smartphone"),
            FieldSchema("key_specs", "array", "Key specifications/features", False, "[256GB, A17 Pro chip]"),
            FieldSchema("pros", "array", "Advantages/positives", False, "[Great camera, Fast performance]"),
            FieldSchema("cons", "array", "Disadvantages/drawbacks", False, "[Expensive, No charger]"),
            FieldSchema("rating", "number", "Rating out of 5 or 10", False, "4.5"),
            FieldSchema("best_for", "string", "Who/what is this best for", False, "Power users, photographers"),
            FieldSchema("release_date", "string", "When released", False, "2024"),
            FieldSchema("source", "string", "Source URL", False, "https://..."),
        ],
        indicators=["buy", "best", "budget", "price", "review", "compare", "laptop", "phone", "camera", "headphones", "watch", "gpu", "cpu", "monitor", "keyboard", "mouse", "tablet", "console", "speaker", "drone"]
    ),
    
    DomainType.SOFTWARE: DomainSchema(
        domain=DomainType.SOFTWARE,
        name="Software/Tool",
        description="Software applications, tools, SaaS products",
        fields=[
            FieldSchema("name", "string", "Software name", True, "VS Code"),
            FieldSchema("category", "string", "Type of software", True, "Code Editor"),
            FieldSchema("pricing", "string", "Pricing model", False, "Free / $10/mo"),
            FieldSchema("features", "array", "Key features", False, "[Syntax highlighting, Git integration]"),
            FieldSchema("platforms", "array", "Supported platforms", False, "[Windows, Mac, Linux]"),
            FieldSchema("pros", "array", "Advantages", False, "[Lightweight, Free]"),
            FieldSchema("cons", "array", "Disadvantages", False, "[Steep learning curve]"),
            FieldSchema("best_for", "string", "Ideal users/use cases", False, "Developers, beginners"),
            FieldSchema("alternatives", "array", "Alternative tools", False, "[Sublime Text, Atom]"),
            FieldSchema("website", "string", "Official website", False, "https://code.visualstudio.com"),
        ],
        indicators=["software", "app", "tool", "platform", "service", "api", "framework", "library", "editor", "ide", "crm", "database", "hosting", "cloud"]
    ),
    
    DomainType.PERSON: DomainSchema(
        domain=DomainType.PERSON,
        name="Person",
        description="Individuals, experts, influencers, professionals",
        fields=[
            FieldSchema("name", "string", "Full name", True, "Elon Musk"),
            FieldSchema("title", "string", "Job title/role", True, "CEO"),
            FieldSchema("company", "string", "Company/Organization", False, "Tesla"),
            FieldSchema("expertise", "array", "Areas of expertise", False, "[AI, Electric Vehicles]"),
            FieldSchema("achievements", "array", "Notable achievements", False, "[Founded SpaceX, Tesla]"),
            FieldSchema("social_media", "object", "Social media links", False, "{twitter: '@elonmusk'}"),
            FieldSchema("website", "string", "Personal website", False, "https://..."),
            FieldSchema("location", "string", "Location", False, "Austin, Texas"),
        ],
        indicators=["person", "people", "expert", "author", "ceo", "founder", "influencer", "developer", "researcher", "scientist", "leader"]
    ),
    
    DomainType.PLACE: DomainSchema(
        domain=DomainType.PLACE,
        name="Place",
        description="Locations, tourist destinations, cities, countries",
        fields=[
            FieldSchema("name", "string", "Place name", True, "Kyoto"),
            FieldSchema("type", "string", "Type of place", True, "City"),
            FieldSchema("location", "string", "Country/Region", True, "Japan"),
            FieldSchema("best_time_to_visit", "string", "When to visit", False, "March-May"),
            FieldSchema("attractions", "array", "Top attractions", False, "[Fushimi Inari, Kinkaku-ji]"),
            FieldSchema("activities", "array", "Things to do", False, "[Temple visits, Cherry blossom viewing]"),
            FieldSchema("budget", "string", "Budget level", False, "$$ - Moderate"),
            FieldSchema("rating", "number", "Overall rating", False, "4.7"),
            FieldSchema("tips", "array", "Travel tips", False, "[Get JR Pass, Book early]"),
        ],
        indicators=["visit", "travel", "destination", "city", "country", "place", "tourist", "vacation", "trip", "hotel", "resort", "beach", "mountain"]
    ),
    
    DomainType.COMPANY: DomainSchema(
        domain=DomainType.COMPANY,
        name="Company",
        description="Businesses, startups, organizations",
        fields=[
            FieldSchema("name", "string", "Company name", True, "OpenAI"),
            FieldSchema("industry", "string", "Industry sector", True, "AI/ML"),
            FieldSchema("founded", "string", "Year founded", False, "2015"),
            FieldSchema("headquarters", "string", "HQ location", False, "San Francisco"),
            FieldSchema("products", "array", "Main products/services", False, "[ChatGPT, GPT-4, DALL-E]"),
            FieldSchema("funding", "string", "Funding status", False, "$11B raised"),
            FieldSchema("valuation", "string", "Company valuation", False, "$80B"),
            FieldSchema("website", "string", "Company website", False, "https://openai.com"),
        ],
        indicators=["company", "startup", "business", "corporation", "enterprise", "unicorn", "organization"]
    ),
    
    DomainType.COMPARISON: DomainSchema(
        domain=DomainType.COMPARISON,
        name="Comparison/Ranking",
        description="Ranked lists and comparisons",
        fields=[
            FieldSchema("rank", "number", "Position in ranking", True, "1"),
            FieldSchema("name", "string", "Item name", True, "Product X"),
            FieldSchema("category", "string", "Item category", False, "Laptop"),
            FieldSchema("score", "number", "Overall score/rating", False, "9.2"),
            FieldSchema("pros", "array", "Key advantages", False, "[Fast, Reliable]"),
            FieldSchema("cons", "array", "Key drawbacks", False, "[Expensive]"),
            FieldSchema("verdict", "string", "Final recommendation", False, "Best overall"),
            FieldSchema("price", "string", "Price if applicable", False, "$999"),
        ],
        indicators=["top", "best", "ranking", "compare", "versus", "vs", "list", "rated", "reviewed"]
    ),
}


class SchemaManager:
    """Manages dynamic schemas based on query analysis."""
    
    def detect_domain(self, query: str) -> DomainType:
        """Detect the domain type from query."""
        query_lower = query.lower()
        
        # Score each domain based on keyword matches
        scores = {domain: 0 for domain in DomainType}
        
        for domain, schema in DOMAIN_SCHEMAS.items():
            for indicator in schema.indicators:
                if indicator in query_lower:
                    scores[domain] += 1
        
        # Return highest scoring domain, default to PRODUCT
        best_domain = max(scores, key=scores.get)
        return best_domain if scores[best_domain] > 0 else DomainType.PRODUCT
    
    def get_schema(self, domain: DomainType) -> DomainSchema:
        """Get schema for a domain."""
        return DOMAIN_SCHEMAS.get(domain, DOMAIN_SCHEMAS[DomainType.PRODUCT])
    
    def get_extraction_prompt(self, query: str, content: str, domain: DomainType) -> str:
        """Generate extraction prompt for a specific domain."""
        schema = self.get_schema(domain)
        
        # Build field descriptions
        field_descs = []
        for field in schema.fields:
            req = "(REQUIRED)" if field.required else "(optional)"
            example = f"Example: {field.example}" if field.example else ""
            field_descs.append(f"  - {field.name}: {field.description} {req} {example}".strip())
        
        prompt = f"""Extract {schema.name} information for: {query}

Return JSON array of objects with these exact fields:
{chr(10).join(field_descs)}

Instructions:
1. Extract EVERY {schema.name.lower()} mentioned in the content
2. Use "N/A" for missing optional fields
3. For arrays, use proper JSON array format: ["item1", "item2"]
4. Be specific with names (include model numbers, versions)
5. Include prices in local currency if mentioned

Content to extract from:
{content[:6000]}

Return ONLY a JSON array. No markdown, no explanations."""
        
        return prompt
    
    def validate_and_clean(self, items: List[Dict], domain: DomainType) -> List[Dict]:
        """Validate and clean extracted items."""
        schema = self.get_schema(domain)
        required_fields = [f.name for f in schema.fields if f.required]
        
        cleaned = []
        seen_names = set()
        
        for item in items:
            if not isinstance(item, dict):
                continue
            
            # Check required fields
            if not all(field in item and item[field] for field in required_fields):
                continue
            
            # Deduplicate by name
            name = str(item.get('name', '')).lower().strip()
            if name in seen_names:
                continue
            seen_names.add(name)
            
            # Clean up fields
            cleaned_item = {}
            for field in schema.fields:
                value = item.get(field.name)
                if value is None or value == '':
                    value = "N/A" if not field.required else None
                cleaned_item[field.name] = value
            
            # Only add if all required fields present
            if all(cleaned_item.get(f) for f in required_fields):
                cleaned.append(cleaned_item)
        
        return cleaned
    
    def sort_by_quality(self, items: List[Dict]) -> List[Dict]:
        """Sort items by data quality (most complete first)."""
        def quality_score(item):
            score = 0
            # More fields filled = higher score
            for key, value in item.items():
                if value and value != "N/A":
                    score += 1
                # Price and rating are valuable
                if key in ['price', 'rating'] and value and value != "N/A":
                    score += 2
            return score
        
        return sorted(items, key=quality_score, reverse=True)


# Singleton instance
_schema_manager = None

def get_schema_manager() -> SchemaManager:
    global _schema_manager
    if _schema_manager is None:
        _schema_manager = SchemaManager()
    return _schema_manager
