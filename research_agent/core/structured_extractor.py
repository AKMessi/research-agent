"""
Structured data extraction using Gemini Function Calling.

Generic extractor that works for ANY research topic.
"""
from typing import List, Dict, Any, Optional, Type
from dataclasses import dataclass
import json
from rich.console import Console

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from research_agent.config import config

console = Console(legacy_windows=True)


# Generic schema that works for ANY research topic
GENERIC_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Name or title of the item"},
        "category": {"type": "string", "description": "Category or type"},
        "description": {"type": "string", "description": "Brief description"},
        "key_details": {"type": "object", "description": "Any key details found (price, specs, ratings, etc.)"},
        "source": {"type": "string", "description": "Source URL or reference"}
    },
    "required": ["name"]
}


class StructuredExtractor:
    """
    Extracts structured data using Gemini's function calling capability.
    Generic - works for any research topic.
    """
    
    def __init__(self, model_name: str = None):
        self.llm = ChatGoogleGenerativeAI(
            model=model_name or config.default_llm_model,
            temperature=0.1,
            api_key=config.gemini_api_key
        )
    
    def extract_with_function_calling(
        self, 
        content: str, 
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Extract structured data using Gemini function calling.
        
        Args:
            content: Text content to extract from
            query: Original user query
        
        Returns:
            List of extracted items
        """
        if not config.gemini_api_key:
            console.print("[yellow]No Gemini API key, skipping structured extraction[/yellow]")
            return []
        
        # Build function declaration
        extraction_function = {
            "name": "extract_items",
            "description": f"Extract items related to: {query}",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": GENERIC_ITEM_SCHEMA,
                        "description": "List of extracted items"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of findings"
                    }
                },
                "required": ["items"]
            }
        }
        
        # Create messages
        system_msg = f"""You are an expert data extraction specialist.
Extract ALL relevant items mentioned in the content for the query: {query}
Be thorough - extract every item, product, person, place, or concept mentioned.
Use the function to return structured data."""
        
        human_msg = f"""Extract information from this content for the query: {query}

Content:
{content[:8000]}

Use the extract_items function to return structured data."""
        
        try:
            # Try with function calling
            from google.generativeai import GenerativeModel
            import google.generativeai as genai
            
            genai.configure(api_key=config.gemini_api_key)
            
            model = GenerativeModel(
                model_name=config.default_llm_model,
                system_instruction=system_msg
            )
            
            # Generate with function calling
            response = model.generate_content(
                human_msg,
                tools=[{"function_declarations": [extraction_function]}],
                tool_config={"function_calling_config": {"mode": "ANY"}}
            )
            
            # Extract function call result
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            fn_call = part.function_call
                            if fn_call.name == "extract_items":
                                args = dict(fn_call.args)
                                items = args.get("items", [])
                                console.print(f"[green]Extracted {len(items)} items via function calling[/green]")
                                return items
            
            # Fallback to regular response parsing
            text = response.text
            # Try to extract JSON
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0]
            else:
                json_str = text
            
            data = json.loads(json_str)
            if isinstance(data, dict) and "items" in data:
                return data["items"]
            elif isinstance(data, list):
                return data
            
        except Exception as e:
            console.print(f"[dim]Function calling failed: {e}, trying fallback...[/dim]")
        
        # Fallback to regular prompting
        return self._extract_with_prompt(content, query)
    
    def _extract_with_prompt(self, content: str, query: str) -> List[Dict[str, Any]]:
        """
        Fallback extraction using regular prompting.
        
        Args:
            content: Content to extract from
            query: User query
        
        Returns:
            List of extracted items
        """
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import JsonOutputParser
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Extract structured data from the provided content for the query: {query}

Output JSON format with an "items" array containing the extracted objects.
Each item should have: name, category, description, key_details (object with any relevant info), source.

Extract EVERY relevant item mentioned. Be thorough."""),
            ("human", """Query: {query}

Content to extract from:
{content}

Extract all items as JSON:""")
        ])
        
        try:
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            
            result = chain.invoke({
                "query": query,
                "content": content[:10000]
            })
            
            items = result.get("items", []) if isinstance(result, dict) else result
            console.print(f"[green]Extracted {len(items)} items via prompt fallback[/green]")
            return items
            
        except Exception as e:
            console.print(f"[red]Prompt extraction failed: {e}[/red]")
            return []


def get_structured_extractor() -> StructuredExtractor:
    """Factory function to get extractor."""
    return StructuredExtractor()
