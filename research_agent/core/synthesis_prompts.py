"""
Format-specific structured synthesis prompts.
"""


class SynthesisPrompts:
    """Collection of prompts for different output formats."""

    JSON_RULES = """Return valid JSON only. Do not wrap it in markdown fences.
Use only facts that are supported by the evidence. If a field is unknown, use an empty string or an empty list."""

    @classmethod
    def _table_prompt(cls, query: str, evidence: str) -> str:
        return f"""You are synthesizing research for: "{query}".

{cls.JSON_RULES}

Required JSON shape:
{{
  "summary": "2-3 sentence overview",
  "items": [
    {{
      "name": "item name",
      "price": "price or N/A",
      "best_for": "best use case",
      "features": ["feature 1", "feature 2"],
      "notes": "important context"
    }}
  ]
}}

EVIDENCE:
{evidence}
"""

    @classmethod
    def _report_prompt(cls, query: str, evidence: str) -> str:
        return f"""You are synthesizing research for: "{query}".

{cls.JSON_RULES}

Required JSON shape:
{{
  "summary": "2-3 sentence overview",
  "key_findings": ["finding 1", "finding 2"],
  "recommendations": ["recommendation 1", "recommendation 2"],
  "sections": [
    {{
      "heading": "Section title",
      "bullets": ["bullet 1", "bullet 2"]
    }}
  ]
}}

EVIDENCE:
{evidence}
"""

    @classmethod
    def _profiles_prompt(cls, query: str, evidence: str) -> str:
        return f"""You are synthesizing research for: "{query}".

{cls.JSON_RULES}

Required JSON shape:
{{
  "summary": "2-3 sentence overview",
  "profiles": [
    {{
      "name": "person or company name",
      "role": "role or category",
      "organization": "organization if known",
      "details": ["detail 1", "detail 2"]
    }}
  ]
}}

EVIDENCE:
{evidence}
"""

    @classmethod
    def _timeline_prompt(cls, query: str, evidence: str) -> str:
        return f"""You are synthesizing research for: "{query}".

{cls.JSON_RULES}

Required JSON shape:
{{
  "summary": "2-3 sentence overview",
  "events": [
    {{
      "date": "date or year",
      "title": "event title",
      "details": "important details"
    }}
  ]
}}

EVIDENCE:
{evidence}
"""

    @classmethod
    def get_prompt(cls, domain: str, query: str, evidence: str, output_format: str) -> str:
        """Get the appropriate structured prompt."""
        if output_format == "table":
            return cls._table_prompt(query, evidence)
        if output_format == "profiles":
            return cls._profiles_prompt(query, evidence)
        if output_format == "timeline":
            return cls._timeline_prompt(query, evidence)
        return cls._report_prompt(query, evidence)
