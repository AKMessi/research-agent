"""
Query expansion for better search coverage.

Uses LLM to expand a single query into multiple targeted searches.
"""
from typing import List, Dict
from rich.console import Console
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from research_agent.config import config

console = Console(legacy_windows=True)


class QueryExpander:
    """
    Expands user queries for better search coverage.
    
    Example:
    "best budget GPUs" -> [
        "best budget GPUs 2024",
        "RTX 4060 vs RX 7600 comparison",
        "affordable GPU for machine learning benchmarks",
        ...
    ]
    """
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=config.default_llm_model,
            temperature=0.3,
            api_key=config.gemini_api_key
        )
    
    def expand(
        self, 
        query: str, 
        context: str = "",
        num_variations: int = 5
    ) -> List[str]:
        """
        Expand a query into multiple search queries.
        
        Args:
            query: Original user query
            context: Additional context
            num_variations: Number of variations to generate
        
        Returns:
            List of expanded queries
        """
        if not config.gemini_api_key:
            # Simple fallback expansion
            return self._simple_expand(query)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a search query optimization expert.

Generate {num_variations} distinct search queries that would help gather comprehensive information.

Each variation should:
1. Target a different aspect of the topic
2. Use different keywords/synonyms
3. Be specific enough to find relevant results
4. Cover different intents (comparison, reviews, benchmarks, buying guide)

Output as JSON with a "queries" array containing the search queries."""),
            ("human", """Original Query: {{query}}
Context: {{context}}

Generate {{num_variations}} search query variations:""")
        ])
        
        try:
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            
            result = chain.invoke({
                "query": query,
                "context": context or "No additional context",
                "num_variations": num_variations
            })
            
            queries = result.get("queries", [])
            
            # Always include original
            if query not in queries:
                queries.insert(0, query)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_queries = []
            for q in queries:
                q_lower = q.lower().strip()
                if q_lower not in seen:
                    seen.add(q_lower)
                    unique_queries.append(q)
            
            console.print(f"[green]Expanded into {len(unique_queries)} search queries[/green]")
            return unique_queries[:num_variations + 1]
            
        except Exception as e:
            console.print(f"[dim]Query expansion failed: {e}, using simple expansion[/dim]")
            return self._simple_expand(query)
    
    def _simple_expand(self, query: str) -> List[str]:
        """
        Simple rule-based query expansion.
        
        Args:
            query: Original query
        
        Returns:
            List of expanded queries
        """
        expansions = [query]
        query_lower = query.lower()
        
        # Add year for tech products
        if any(word in query_lower for word in ["gpu", "cpu", "phone", "laptop", "camera"]):
            expansions.append(f"{query} 2024")
            expansions.append(f"{query} 2025")
        
        # Add comparison keywords
        if "best" in query_lower or "top" in query_lower:
            expansions.append(f"{query} comparison")
            expansions.append(f"{query} vs")
        
        # Add review keywords
        if "buy" in query_lower or "budget" in query_lower:
            expansions.append(f"{query} reviews")
            expansions.append(f"{query} benchmark")
        
        # Add Reddit for authentic discussions
        expansions.append(f"{query} reddit")
        
        return list(dict.fromkeys(expansions))  # Remove duplicates
    
    def get_search_targets(self, query: str) -> Dict[str, List[str]]:
        """
        Get expanded queries organized by target platform.
        
        Args:
            query: Original query
        
        Returns:
            Dict with platform-specific queries
        """
        base_expansions = self.expand(query, num_variations=6)
        
        return {
            "general": base_expansions[:4],
            "reddit": [f"{q} reddit" for q in base_expansions[:2]],
            "youtube": [f"{q} review" for q in base_expansions[:2]],
            "news": [f"{q} 2024 news" for q in base_expansions[:2]]
        }


def get_query_expander() -> QueryExpander:
    """Factory function to get query expander."""
    return QueryExpander()
