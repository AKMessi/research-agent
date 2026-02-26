"""
Query Analyzer - Determines research strategy and output format
"""
import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ResearchDomain(Enum):
    PRODUCTS = "products"           # Physical items: GPUs, laptops, headphones
    SOFTWARE = "software"           # Apps, tools, SaaS
    PLACES = "places"               # Travel destinations, cities
    PEOPLE = "people"               # Experts, influencers, professionals
    COMPANIES = "companies"         # Businesses, startups
    EVENTS = "events"               # Conferences, concerts
    HOW_TO = "how_to"               # Tutorials, guides
    NEWS = "news"                   # Current events, trends
    COMPARISON = "comparison"       # Vs, best, top rankings
    GENERAL = "general"             # Fallback


class OutputFormat(Enum):
    TABLE = "table"                 # CSV/Excel - for comparisons
    REPORT = "report"               # Markdown - for guides
    PROFILES = "profiles"           # JSON - for people/companies
    TIMELINE = "timeline"           # Markdown - for events/news
    LIST = "list"                   # Simple list - for quick answers


@dataclass
class QueryAnalysis:
    domain: ResearchDomain
    output_format: OutputFormat
    keywords: list
    confidence: float
    reasoning: str


class QueryAnalyzer:
    """Analyzes queries to determine research strategy."""
    
    DOMAIN_PATTERNS = {
        ResearchDomain.PRODUCTS: {
            'keywords': ['buy', 'best', 'budget', 'price', 'review', 'compare', 'vs'],
            'entities': ['laptop', 'phone', 'camera', 'headphones', 'gpu', 'monitor', 
                        'keyboard', 'mouse', 'tablet', 'watch', 'earbuds', 'speaker',
                        'drone', 'console', 'bike', 'car', 'shoes', 'bag'],
        },
        ResearchDomain.SOFTWARE: {
            'keywords': ['app', 'software', 'tool', 'platform', 'service', 'api'],
            'entities': ['editor', 'ide', 'crm', 'database', 'hosting', 'vpn'],
        },
        ResearchDomain.PLACES: {
            'keywords': ['visit', 'travel', 'destination', 'trip', 'vacation', 'hotel'],
            'entities': ['city', 'country', 'beach', 'mountain', 'island', 'resort'],
        },
        ResearchDomain.PEOPLE: {
            'keywords': ['expert', 'influencer', 'author', 'founder', 'ceo', 'developer'],
            'entities': ['person', 'people', 'researcher', 'scientist', 'leader'],
        },
        ResearchDomain.COMPANIES: {
            'keywords': ['company', 'startup', 'business', 'enterprise', 'unicorn'],
            'entities': ['inc', 'corp', 'ltd', 'gmbh'],
        },
        ResearchDomain.EVENTS: {
            'keywords': ['conference', 'event', 'festival', 'summit', 'expo'],
            'entities': ['2024', '2025', 'annual', 'upcoming'],
        },
        ResearchDomain.HOW_TO: {
            'keywords': ['how to', 'guide', 'tutorial', 'learn', 'steps', 'setup'],
            'entities': ['install', 'configure', 'build', 'create', 'make'],
        },
        ResearchDomain.NEWS: {
            'keywords': ['news', 'latest', 'recent', 'update', 'trending', 'happening'],
            'entities': ['today', 'this week', 'this month', '2024', '2025'],
        },
        ResearchDomain.COMPARISON: {
            'keywords': ['vs', 'versus', 'compare', 'difference', 'better', 'or'],
            'entities': [],
        },
    }
    
    def analyze(self, query: str) -> QueryAnalysis:
        """Analyze query and determine research strategy."""
        query_lower = query.lower()
        
        # Score each domain
        scores = {domain: 0 for domain in ResearchDomain}
        
        for domain, patterns in self.DOMAIN_PATTERNS.items():
            # Check keywords
            for kw in patterns['keywords']:
                if kw in query_lower:
                    scores[domain] += 2
            
            # Check entities
            for entity in patterns['entities']:
                if entity in query_lower:
                    scores[domain] += 3
        
        # Special cases
        if re.search(r'\b(vs|versus|or)\b', query_lower):
            scores[ResearchDomain.COMPARISON] += 5
        
        if query_lower.startswith('how to'):
            scores[ResearchDomain.HOW_TO] += 10
        
        # Find best match
        best_domain = max(scores, key=scores.get)
        confidence = scores[best_domain] / 10  # Normalize
        
        # Determine output format
        output_format = self._determine_format(best_domain, query_lower)
        
        # Extract keywords
        keywords = self._extract_keywords(query_lower)
        
        reasoning = f"Detected {best_domain.value} domain (confidence: {confidence:.2f})"
        
        return QueryAnalysis(
            domain=best_domain,
            output_format=output_format,
            keywords=keywords,
            confidence=min(confidence, 1.0),
            reasoning=reasoning
        )
    
    def _determine_format(self, domain: ResearchDomain, query: str) -> OutputFormat:
        """Determine best output format for domain."""
        format_map = {
            ResearchDomain.PRODUCTS: OutputFormat.TABLE,
            ResearchDomain.SOFTWARE: OutputFormat.TABLE,
            ResearchDomain.PLACES: OutputFormat.REPORT,
            ResearchDomain.PEOPLE: OutputFormat.PROFILES,
            ResearchDomain.COMPANIES: OutputFormat.PROFILES,
            ResearchDomain.EVENTS: OutputFormat.TIMELINE,
            ResearchDomain.HOW_TO: OutputFormat.REPORT,
            ResearchDomain.NEWS: OutputFormat.TIMELINE,
            ResearchDomain.COMPARISON: OutputFormat.TABLE,
            ResearchDomain.GENERAL: OutputFormat.REPORT,
        }
        
        # Override based on query hints
        if 'list' in query or 'top' in query:
            return OutputFormat.LIST
        
        if 'compare' in query or 'vs' in query:
            return OutputFormat.TABLE
        
        return format_map.get(domain, OutputFormat.REPORT)
    
    def _extract_keywords(self, query: str) -> list:
        """Extract important keywords from query."""
        # Remove common words
        stopwords = {'the', 'a', 'an', 'is', 'are', 'for', 'to', 'in', 'on', 'at', 'best', 'top'}
        words = query.lower().split()
        return [w for w in words if w not in stopwords and len(w) > 2][:5]
