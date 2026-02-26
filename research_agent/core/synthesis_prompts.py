"""
Format-specific synthesis prompts for different research types
"""


class SynthesisPrompts:
    """Collection of prompts for different output formats."""
    
    @staticmethod
    def product_comparison(query: str, evidence: str) -> str:
        return f"""Extract product recommendations from this research about "{query}".

EVIDENCE:
{evidence}

Extract products mentioned with:
- Name (include model/version)
- Price (if mentioned)
- Key features/specs
- Who it's best for
- Any pros/cons mentioned

Format as list:
- Product Name | Price | Best for: [use case] | Features: [key specs]

Product List:"""

    @staticmethod
    def travel_guide(query: str, evidence: str) -> str:
        return f"""Create a travel guide from this research about "{query}".

EVIDENCE:
{evidence}

Extract and summarize:
- Best time to visit
- Top attractions/places
- Estimated budget range
- Tips and recommendations
- What to avoid

Travel Guide:"""

    @staticmethod
    def person_profiles(query: str, evidence: str) -> str:
        return f"""Extract people/experts mentioned in this research about "{query}".

EVIDENCE:
{evidence}

For each person found:
- Name
- Title/role
- Area of expertise
- Notable achievements
- Organization/company

People List:"""

    @staticmethod
    def company_analysis(query: str, evidence: str) -> str:
        return f"""Extract companies/startups mentioned in this research about "{query}".

EVIDENCE:
{evidence}

For each company:
- Name
- Industry/sector
- Key products/services
- Funding stage (if mentioned)
- Notable facts

Company List:"""

    @staticmethod
    def how_to_guide(query: str, evidence: str) -> str:
        return f"""Create a how-to guide from this research about "{query}".

EVIDENCE:
{evidence}

Structure as:
- Overview/introduction
- Prerequisites (what you need)
- Step-by-step instructions
- Tips for success
- Common mistakes to avoid

Guide:"""

    @staticmethod
    def event_timeline(query: str, evidence: str) -> str:
        return f"""Extract events and timeline from this research about "{query}".

EVIDENCE:
{evidence}

Extract:
- Event names and dates
- Key highlights
- Important announcements
- Trends and developments

Timeline:"""

    @staticmethod
    def general_research(query: str, evidence: str) -> str:
        return f"""Synthesize key findings from this research about "{query}".

EVIDENCE:
{evidence}

Provide:
- Executive summary (2-3 sentences)
- Key findings (5-7 bullet points)
- Important names/products/places mentioned
- Any recommendations or conclusions

Research Summary:"""

    @classmethod
    def get_prompt(cls, domain: str, query: str, evidence: str) -> str:
        """Get appropriate prompt for domain."""
        prompt_map = {
            'products': cls.product_comparison,
            'software': cls.product_comparison,
            'places': cls.travel_guide,
            'people': cls.person_profiles,
            'companies': cls.company_analysis,
            'how_to': cls.how_to_guide,
            'events': cls.event_timeline,
            'news': cls.event_timeline,
            'comparison': cls.product_comparison,
            'general': cls.general_research,
        }
        
        prompt_func = prompt_map.get(domain, cls.general_research)
        return prompt_func(query, evidence)
