"""
Unified synthesis engine for turning gathered evidence into structured output.
"""
import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from rich.console import Console

from research_agent.config import config
from research_agent.core.query_analyzer import OutputFormat, QueryAnalysis, QueryAnalyzer, ResearchDomain
from research_agent.core.synthesis_prompts import SynthesisPrompts

console = Console(legacy_windows=True)


@dataclass
class SynthesisResult:
    """Result of synthesis."""

    domain: str
    format: str
    content: Dict[str, Any]
    sources_used: int
    confidence: float
    backend: str = "fallback"


class UnifiedSynthesisEngine:
    """Universal synthesis engine for any research type."""

    def __init__(self):
        self.analyzer = QueryAnalyzer()
        self.ollama_url = config.ollama_url.rstrip("/")
        self.ollama_model = self._detect_model()

    def _detect_model(self) -> Optional[str]:
        """Detect a reachable Ollama model."""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            resp.raise_for_status()
            models = resp.json().get("models", [])

            preferred = [config.ollama_model, "llama3.2", "llama3.1", "mistral"]
            for wanted in preferred:
                for model in models:
                    name = model.get("name", "")
                    if wanted and wanted.lower() in name.lower():
                        return name

            if models:
                return models[0].get("name")
        except Exception:
            return None
        return None

    def synthesize(self, query: str, sources: List[Dict]) -> SynthesisResult:
        """Main synthesis method."""
        analysis = self.analyzer.analyze(query)
        prepared_sources = self._prepare_sources(sources)

        console.print(f"[dim]{analysis.reasoning}[/dim]")
        console.print(f"[dim]Output format: {analysis.output_format.value}[/dim]")

        if not prepared_sources:
            return SynthesisResult(
                domain=analysis.domain.value,
                format=analysis.output_format.value,
                content={"summary": "No sources found.", "error": "No sources found"},
                sources_used=0,
                confidence=0.0,
            )

        backend = "fallback"
        parsed_content: Optional[Dict[str, Any]] = None

        prompt = SynthesisPrompts.get_prompt(
            domain=analysis.domain.value,
            query=query,
            evidence=self._build_evidence(prepared_sources),
            output_format=analysis.output_format.value,
        )
        raw_response, backend = self._ai_synthesize(prompt)

        if raw_response:
            parsed_content = self._parse_response(raw_response, analysis.output_format)

        if not self._is_valid_content(parsed_content, analysis.output_format):
            if backend != "fallback":
                console.print("[dim]Structured AI synthesis was incomplete; using deterministic fallback.[/dim]")
            parsed_content = self._fallback_synthesize(query, analysis, prepared_sources)
            backend = "fallback"

        parsed_content.setdefault("sources", self._build_source_index(prepared_sources))

        return SynthesisResult(
            domain=analysis.domain.value,
            format=analysis.output_format.value,
            content=parsed_content,
            sources_used=len(prepared_sources),
            confidence=analysis.confidence,
            backend=backend,
        )

    def _prepare_sources(self, sources: List[Dict]) -> List[Dict[str, Any]]:
        """Normalize source payloads for ranking and synthesis."""
        prepared = []
        for index, source in enumerate(sources, start=1):
            title = (source.get("title") or "").strip()
            link = (source.get("link") or "").strip()
            snippet = (source.get("snippet") or "").strip()
            raw_text = source.get("full_content") or snippet or title
            text = self._clean_text(raw_text)

            if not title and not text:
                continue

            prepared.append(
                {
                    "rank": index,
                    "title": title,
                    "link": link,
                    "source": source.get("source", "web"),
                    "snippet": snippet,
                    "raw_text": raw_text,
                    "text": text,
                    "sentences": self._extract_sentences(text),
                }
            )

        return prepared

    def _build_evidence(self, sources: List[Dict[str, Any]]) -> str:
        """Build formatted evidence for the LLM."""
        parts = []
        for source in sources[:8]:
            excerpt_lines = []
            if source["title"]:
                excerpt_lines.append(f"Title: {source['title']}")
            if source["link"]:
                excerpt_lines.append(f"URL: {source['link']}")
            excerpt_lines.extend(source["sentences"][:4])
            if excerpt_lines:
                parts.append(f"[Source {source['rank']}]\n" + "\n".join(excerpt_lines))
        return "\n\n".join(parts)

    def _ai_synthesize(self, prompt: str) -> tuple[str, str]:
        """Use Ollama first and Gemini second if configured."""
        if self.ollama_model:
            try:
                resp = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 2200,
                        },
                    },
                    timeout=config.ollama_timeout,
                )
                resp.raise_for_status()
                return resp.json().get("response", ""), "ollama"
            except Exception as exc:
                console.print(f"[dim]Ollama synthesis error: {exc}[/dim]")

        if config.is_gemini_configured:
            text = self._gemini_synthesize(prompt)
            if text:
                return text, "gemini"

        return "", "fallback"

    def _gemini_synthesize(self, prompt: str) -> str:
        """Call Gemini via REST when a valid key is configured."""
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/gemini-1.5-flash:generateContent?key={config.gemini_api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 2200,
                "responseMimeType": "application/json",
            },
        }

        try:
            resp = requests.post(url, json=payload, timeout=45)
            resp.raise_for_status()
            candidates = resp.json().get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
        except Exception as exc:
            console.print(f"[dim]Gemini synthesis error: {exc}[/dim]")

        return ""

    def _parse_response(self, text: str, fmt: OutputFormat) -> Dict[str, Any]:
        """Parse a structured JSON response from the model."""
        parsed = self._extract_json(text)
        if not isinstance(parsed, dict):
            return {}

        if fmt == OutputFormat.TABLE:
            items = parsed.get("items", [])
            if isinstance(items, list):
                parsed["items"] = [self._normalize_item(item) for item in items if isinstance(item, dict)]
        elif fmt == OutputFormat.PROFILES:
            profiles = parsed.get("profiles", [])
            if isinstance(profiles, list):
                parsed["profiles"] = [self._normalize_profile(item) for item in profiles if isinstance(item, dict)]
        elif fmt == OutputFormat.TIMELINE:
            events = parsed.get("events", [])
            if isinstance(events, list):
                parsed["events"] = [self._normalize_event(item) for item in events if isinstance(item, dict)]
        else:
            parsed["key_findings"] = self._normalize_string_list(parsed.get("key_findings", []))
            parsed["recommendations"] = self._normalize_string_list(parsed.get("recommendations", []))
            parsed["sections"] = self._normalize_sections(parsed.get("sections", []))

        return parsed

    def _fallback_synthesize(
        self,
        query: str,
        analysis: QueryAnalysis,
        sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Deterministic fallback when no model backend is usable."""
        summary_sentences = self._select_sentences(sources, analysis.keywords, limit=5)
        summary = " ".join(summary_sentences[:2]) or f"Research collected {len(sources)} sources for {query}."

        if analysis.output_format == OutputFormat.TABLE:
            return self._fallback_table(query, sources, summary)
        if analysis.output_format == OutputFormat.PROFILES:
            return self._fallback_profiles(sources, summary)
        if analysis.output_format == OutputFormat.TIMELINE:
            return self._fallback_timeline(sources, summary)
        if analysis.domain == ResearchDomain.HOW_TO:
            return self._fallback_how_to(sources, summary, analysis.keywords)
        return self._fallback_report(sources, summary, analysis.keywords, list_mode=analysis.output_format == OutputFormat.LIST)

    def _fallback_report(
        self,
        sources: List[Dict[str, Any]],
        summary: str,
        keywords: List[str],
        list_mode: bool = False,
    ) -> Dict[str, Any]:
        findings = self._select_sentences(sources, keywords, limit=8)
        recommendations = self._extract_recommendations(findings)

        sections = [
            {
                "heading": "Key Findings" if not list_mode else "Top Results",
                "bullets": findings[:6],
            }
        ]
        if recommendations:
            sections.append({"heading": "Recommendations", "bullets": recommendations[:4]})

        return {
            "summary": summary,
            "key_findings": findings[:6],
            "recommendations": recommendations[:4],
            "sections": sections,
        }

    def _fallback_how_to(
        self,
        sources: List[Dict[str, Any]],
        summary: str,
        keywords: List[str],
    ) -> Dict[str, Any]:
        findings = self._select_sentences(sources, keywords, limit=10)
        steps = self._extract_steps(sources)
        prerequisites = [
            sentence for sentence in findings
            if re.search(r"\b(before|need|require|prerequisite|foundation)\b", sentence, re.I)
        ]
        mistakes = [
            sentence for sentence in findings
            if re.search(r"\b(avoid|mistake|pitfall|common error|don't)\b", sentence, re.I)
        ]

        sections = [
            {"heading": "Overview", "bullets": findings[:3]},
            {"heading": "Prerequisites", "bullets": prerequisites[:4] or findings[:3]},
            {"heading": "Step-by-Step", "bullets": steps[:6] or findings[:6]},
        ]

        if mistakes:
            sections.append({"heading": "Common Mistakes to Avoid", "bullets": mistakes[:4]})

        return {
            "summary": summary,
            "key_findings": findings[:6],
            "recommendations": self._extract_recommendations(findings)[:4],
            "sections": sections,
        }

    def _fallback_table(self, query: str, sources: List[Dict[str, Any]], summary: str) -> Dict[str, Any]:
        comparison_targets = self._extract_comparison_targets(query)
        candidates = comparison_targets or self._extract_candidate_items(sources)
        items = []

        for name in candidates[:8]:
            evidence = self._gather_item_evidence(name, sources)
            items.append(
                {
                    "name": name,
                    "price": self._extract_price(evidence) or "N/A",
                    "best_for": self._extract_best_for(evidence),
                    "features": self._extract_features(evidence),
                    "notes": " ".join(evidence[:2]),
                }
            )

        if not items:
            # Last-resort fallback to source titles so CSV is never empty.
            for source in sources[:8]:
                items.append(
                    {
                        "name": source["title"] or source["link"],
                        "price": "N/A",
                        "best_for": source["source"],
                        "features": [],
                        "notes": source["snippet"] or "Derived from search result metadata.",
                    }
                )

        return {
            "summary": summary,
            "items": items,
            "count": len(items),
        }

    def _fallback_profiles(self, sources: List[Dict[str, Any]], summary: str) -> Dict[str, Any]:
        candidates = self._extract_candidate_names(sources)
        profiles = []
        for name in candidates[:8]:
            evidence = self._gather_item_evidence(name, sources)
            profiles.append(
                {
                    "name": name,
                    "role": self._extract_role(evidence),
                    "organization": self._extract_organization(evidence),
                    "details": evidence[:3],
                }
            )

        if not profiles:
            for source in sources[:6]:
                profiles.append(
                    {
                        "name": source["title"] or "Unknown",
                        "role": source["source"],
                        "organization": "",
                        "details": source["sentences"][:2],
                    }
                )

        return {
            "summary": summary,
            "profiles": profiles,
            "count": len(profiles),
        }

    def _fallback_timeline(self, sources: List[Dict[str, Any]], summary: str) -> Dict[str, Any]:
        events = []
        for source in sources[:10]:
            date = self._extract_date(source["text"]) or self._extract_date(source["title"])
            details = source["sentences"][:2]
            events.append(
                {
                    "date": date or "Date not specified",
                    "title": source["title"] or source["link"],
                    "details": " ".join(details),
                }
            )

        return {
            "summary": summary,
            "events": events,
            "count": len(events),
        }

    def _select_sentences(
        self,
        sources: List[Dict[str, Any]],
        keywords: List[str],
        limit: int = 6,
    ) -> List[str]:
        """Rank sentences by query relevance and source order."""
        candidates = []
        seen = set()
        for source in sources:
            for sentence in source["sentences"]:
                clean = sentence.strip()
                if len(clean) < 40 or clean in seen:
                    continue
                if self._looks_like_heading(clean):
                    continue
                seen.add(clean)
                keyword_matches = sum(1 for keyword in keywords if keyword in clean.lower())
                if keywords and keyword_matches == 0:
                    continue
                score = 1 / max(source["rank"], 1)
                score += keyword_matches * 0.7
                if re.search(r"\b(best|recommended|important|key|should|need|avoid)\b", clean, re.I):
                    score += 0.5
                candidates.append((score, clean))

        candidates.sort(key=lambda item: item[0], reverse=True)
        selected = [sentence for _, sentence in candidates[:limit]]

        if len(selected) < limit:
            fallback = []
            for source in sources:
                for sentence in source["sentences"]:
                    if sentence not in selected and sentence not in fallback and len(sentence) >= 40:
                        fallback.append(sentence)
            selected.extend(fallback[: max(0, limit - len(selected))])

        return selected[:limit]

    def _extract_steps(self, sources: List[Dict[str, Any]]) -> List[str]:
        """Extract plausible how-to steps from evidence."""
        steps = []
        for source in sources:
            lines = [self._clean_text(line) for line in str(source["raw_text"]).splitlines()]
            for line in lines:
                if len(line) < 30:
                    continue
                if re.match(r"^(\d+[\.\)]|step\s+\d+)", line, re.I):
                    steps.append(re.sub(r"^(\d+[\.\)]|step\s+\d+[:\.\-\s]*)", "", line, flags=re.I).strip())
                elif re.search(r"\b(start|learn|build|practice|focus|use|apply|study)\b", line, re.I):
                    steps.append(line)
        return self._dedupe_strings(steps)[:8]

    def _extract_candidate_items(self, sources: List[Dict[str, Any]]) -> List[str]:
        """Extract product or tool names from source titles and content."""
        counts: Counter[str] = Counter()
        line_items = []
        for source in sources:
            for candidate in self._extract_items_from_lines(str(source["raw_text"])):
                line_items.append(candidate)
                counts[candidate] += 4
        ordered = self._dedupe_strings(line_items)

        if len(ordered) < 8:
            for source in sources:
                for text in [source["title"], source["text"]]:
                    for candidate in self._find_named_candidates(text):
                        counts[candidate] += 1

        for name, _ in counts.most_common(12):
            if name not in ordered:
                ordered.append(name)

        return ordered[:10]

    def _extract_candidate_names(self, sources: List[Dict[str, Any]]) -> List[str]:
        """Extract person or company names from evidence."""
        counts: Counter[str] = Counter()
        for source in sources:
            for candidate in self._find_named_candidates(source["title"], allow_single_word=False):
                counts[candidate] += 2
            for candidate in self._find_named_candidates(source["text"], allow_single_word=False):
                counts[candidate] += 1
        return [name for name, _ in counts.most_common(10)]

    def _find_named_candidates(self, text: str, allow_single_word: bool = False) -> List[str]:
        """Find title-cased or model-like phrases worth considering."""
        if not text:
            return []

        patterns = re.findall(
            r"(?:[A-Z][A-Za-z0-9\-\+]+(?:\s+[A-Z0-9][A-Za-z0-9\-\+]+){%s,4})" % ("0" if allow_single_word else "1"),
            text,
        )
        blocked = {
            "Title", "Markdown Content", "URL Source", "Published Time", "Open in app",
            "Machine Learning", "Research Summary", "Key Findings", "Step By Step",
            "Top Picks", "Sound Quality", "Noise Cancellation", "Battery Life", "RTINGS.com",
        }
        cleaned = []
        for match in patterns:
            candidate = match.strip(" -|:")
            if len(candidate) < 3 or candidate in blocked:
                continue
            if re.fullmatch(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}", candidate):
                continue
            if candidate.endswith(".com") or re.fullmatch(r"20\d{2}", candidate):
                continue
            if candidate.lower() in {"reddit", "google", "browserbase"}:
                continue
            cleaned.append(candidate)
        return cleaned

    def _extract_items_from_lines(self, raw_text: str) -> List[str]:
        """Extract ranked recommendation names from markdown-style lists."""
        items = []
        for raw_line in raw_text.splitlines():
            original = raw_line.strip()
            if not original or not re.match(r"^(\d+\.|[\*\-])", original):
                continue

            line = original
            line = re.sub(r"\*{1,2}", "", line)
            line = re.sub(r"^\d+\.\s*", "", line)
            line = re.sub(r"^[\-\*]\s*", "", line)
            line = line.strip()

            match = re.match(r"^(?P<label>.+?)(?:\s+-\s+|\s*:\s*)(?P<name>.+)$", line)
            if match and re.match(r"^(best|runner-up|strongest)\b", match.group("label"), re.I):
                candidate = match.group("name").strip(" .")
                if 2 < len(candidate) < 80:
                    items.append(candidate)
                continue

        return self._dedupe_strings(items)

    def _gather_item_evidence(self, name: str, sources: List[Dict[str, Any]]) -> List[str]:
        """Gather sentences that mention a candidate item."""
        evidence = []
        for source in sources:
            haystack = [source["title"]] + source["sentences"]
            for sentence in haystack:
                if name.lower() in sentence.lower():
                    evidence.append(re.sub(r"\*{1,2}", "", sentence).strip())
        return self._dedupe_strings(evidence)

    def _extract_price(self, evidence: List[str]) -> str:
        """Extract a price from evidence."""
        for sentence in evidence:
            match = re.search(r"(\$|USD\s?)(\d[\d,]+(?:\.\d{2})?)", sentence, re.I)
            if match:
                return f"${match.group(2)}"
        return ""

    def _extract_best_for(self, evidence: List[str]) -> str:
        """Extract a short 'best for' statement."""
        for sentence in evidence:
            match = re.search(r"best for\s+(.+?)\s*:\s*(.+)$", sentence, re.I)
            if match:
                return match.group(1).strip()
            match = re.search(r"runner-up for\s+(.+?)\s*:\s*(.+)$", sentence, re.I)
            if match:
                return f"Runner-up for {match.group(1).strip()}"
            match = re.search(r"best overall\s*-\s*(.+)$", sentence, re.I)
            if match:
                return "Overall"
            if " - " in sentence:
                label = sentence.split(" - ", 1)[0]
                if re.match(r"^best for\s+", label, re.I):
                    return re.sub(r"^best for\s+", "", label, flags=re.I).strip()
                if re.match(r"^best\s+", label, re.I):
                    return re.sub(r"^best\s+", "", label, flags=re.I).strip()
                if re.match(r"^strongest\s+", label, re.I):
                    return re.sub(r"^strongest\s+", "", label, flags=re.I).strip()
        for sentence in evidence:
            if len(sentence) <= 120:
                return sentence
        return ""

    def _extract_features(self, evidence: List[str]) -> List[str]:
        """Extract brief feature phrases."""
        features = []
        for sentence in evidence:
            parts = re.split(r"[;,]", sentence)
            for part in parts:
                cleaned = part.strip()
                if 10 <= len(cleaned) <= 80:
                    features.append(cleaned)
        return self._dedupe_strings(features)[:4]

    def _extract_role(self, evidence: List[str]) -> str:
        """Extract a role or title for a profile."""
        role_keywords = r"(founder|ceo|researcher|scientist|engineer|developer|author|professor|analyst)"
        for sentence in evidence:
            match = re.search(role_keywords, sentence, re.I)
            if match:
                return match.group(1).title()
        return ""

    def _extract_organization(self, evidence: List[str]) -> str:
        """Extract organization names from profile evidence."""
        for sentence in evidence:
            match = re.search(r"\bat\s+([A-Z][A-Za-z0-9&\-\s]{2,40})", sentence)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_date(self, text: str) -> str:
        """Extract a simple date-like token."""
        match = re.search(
            r"(\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b|\b20\d{2}\b)",
            text,
            re.I,
        )
        return match.group(1) if match else ""

    def _extract_comparison_targets(self, query: str) -> List[str]:
        """Extract comparison targets directly from the user query."""
        if not re.search(r"\b(vs|versus|or)\b", query, re.I):
            return []

        parts = re.split(r"\b(?:vs|versus|or)\b", query, flags=re.I)
        cleaned = []
        for part in parts:
            candidate = re.sub(r"\b(compare|comparison|best|top)\b", "", part, flags=re.I).strip(" -,:")
            if len(candidate) > 2:
                cleaned.append(candidate)
        return self._dedupe_strings(cleaned)

    def _extract_recommendations(self, sentences: List[str]) -> List[str]:
        """Derive recommendation-style bullets from findings."""
        recommendations = []
        for sentence in sentences:
            if re.search(r"\b(should|start|focus|choose|use|avoid|prioritize)\b", sentence, re.I):
                recommendations.append(sentence)
        return self._dedupe_strings(recommendations)

    def _build_source_index(self, sources: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Small source summary for renderers."""
        return [
            {
                "title": source["title"],
                "link": source["link"],
                "source": source["source"],
            }
            for source in sources[:10]
        ]

    def _extract_json(self, text: str) -> Any:
        """Extract a JSON object from a model response."""
        if not text:
            return {}

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.S)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", cleaned, re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
        return {}

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a table row."""
        features = item.get("features", [])
        if isinstance(features, str):
            features = [features]
        return {
            "name": str(item.get("name", "")).strip(),
            "price": str(item.get("price", "N/A")).strip() or "N/A",
            "best_for": str(item.get("best_for", "")).strip(),
            "features": self._normalize_string_list(features),
            "notes": str(item.get("notes", "")).strip(),
        }

    def _normalize_profile(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a profile entry."""
        details = item.get("details", [])
        if isinstance(details, str):
            details = [details]
        return {
            "name": str(item.get("name", "")).strip(),
            "role": str(item.get("role", "")).strip(),
            "organization": str(item.get("organization", "")).strip(),
            "details": self._normalize_string_list(details),
        }

    def _normalize_event(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a timeline event."""
        return {
            "date": str(item.get("date", "")).strip(),
            "title": str(item.get("title", "")).strip(),
            "details": str(item.get("details", "")).strip(),
        }

    def _normalize_sections(self, sections: Any) -> List[Dict[str, Any]]:
        """Normalize markdown sections."""
        normalized = []
        if not isinstance(sections, list):
            return normalized
        for section in sections:
            if not isinstance(section, dict):
                continue
            normalized.append(
                {
                    "heading": str(section.get("heading", "")).strip(),
                    "bullets": self._normalize_string_list(section.get("bullets", [])),
                }
            )
        return normalized

    def _normalize_string_list(self, values: Any) -> List[str]:
        """Normalize a list of strings."""
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            return []
        return [str(value).strip() for value in values if str(value).strip()]

    def _is_valid_content(self, content: Optional[Dict[str, Any]], fmt: OutputFormat) -> bool:
        """Check whether synthesized content is useful."""
        if not content:
            return False
        if fmt == OutputFormat.TABLE:
            return bool(content.get("items"))
        if fmt == OutputFormat.PROFILES:
            return bool(content.get("profiles"))
        if fmt == OutputFormat.TIMELINE:
            return bool(content.get("events"))
        return bool(content.get("summary") or content.get("key_findings") or content.get("sections"))

    def _extract_sentences(self, text: str) -> List[str]:
        """Split and clean sentences from free text."""
        text = self._clean_text(text)
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        cleaned = []
        for sentence in sentences:
            sentence = sentence.strip(" -|")
            if len(sentence) < 20:
                continue
            if sentence.lower().startswith(("title:", "url source:", "markdown content:", "published time:")):
                continue
            if self._is_noise_sentence(sentence):
                continue
            cleaned.append(sentence)
        return self._dedupe_strings(cleaned)

    def _clean_text(self, text: str) -> str:
        """Remove obvious scraper artifacts and compress whitespace."""
        if not text:
            return ""
        text = str(text).replace("\r", "")
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\(", r"\1", text)
        text = re.sub(r"\*{1,2}", "", text)
        text = re.sub(
            r"^\s*(Title|URL Source|Published Time|Markdown Content|Publisher|Legal Name|Phone Number|Email|Website):.*$",
            "",
            text,
            flags=re.M,
        )
        text = re.sub(r"^\s*(Open in app|Sign up|Follow publication|Member-only story).*$", "", text, flags=re.M)
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"`{1,3}", "", text)
        text = re.sub(r"^=+$", "", text, flags=re.M)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _is_noise_sentence(self, sentence: str) -> bool:
        """Filter obvious scraper or unrelated forum noise."""
        lowered = sentence.lower()
        blocked_phrases = [
            "editor's note",
            "originally posted",
            "trigger warnings",
            "member-only story",
            "follow publication",
            "legal name",
            "phone number",
            "email:",
            "sign up",
            "reddit post",
            "open in app",
            "](",
        ]
        if sentence.startswith("[") or sentence.endswith("("):
            return True
        return any(phrase in lowered for phrase in blocked_phrases)

    def _looks_like_heading(self, sentence: str) -> bool:
        """Detect short title-like lines that are poor summary bullets."""
        if "|" in sentence:
            return True
        words = sentence.split()
        if len(words) <= 8 and all(word[:1].isupper() or not word[:1].isalpha() for word in words):
            return True
        return False

    def _dedupe_strings(self, values: List[str]) -> List[str]:
        """Preserve order while de-duplicating strings."""
        seen = set()
        result = []
        for value in values:
            key = value.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(value.strip())
        return result
