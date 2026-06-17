"""
Generate realistic, document-grounded queries with a local LLM (cached).

For each anchor document we ask the model for a small bank of queries across
categories, plus a key fact and a plausible-but-false counter-claim (used to
inject controlled contradictions). Results are cached to disk so the (slow)
generation runs once and is reused when composing scenarios.

A deterministic fallback (title/first-sentence templating) is used when the LLM
is unavailable or returns unparseable output, so scenario building never blocks.
"""
import json
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from providers import get_provider

CACHE = config.CACHE_DIR / "queries.jsonl"

_SYS = "You write realistic information-seeking questions a user would ask about a document. Output strict JSON only."

_PROMPT = """Read the document excerpt and produce JSON with this exact shape:
{{
  "factual": "a specific factual question answerable from the text",
  "research_open": "an open/analytical question about limitations or implications",
  "long_context_synthesis": "a question asking to summarize/synthesize the key points",
  "key_fact": "one concrete fact stated in the text (short sentence)",
  "counter_claim": "a plausible but FALSE variation of key_fact (same topic, wrong detail)"
}}
Document title: {title}
Excerpt:
{excerpt}

JSON:"""


def _parse_json(text: str):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _fallback(title: str, text: str) -> dict:
    first = re.split(r"(?<=[.!?])\s+", text.strip())[0][:200] if text.strip() else title
    return {
        "factual": f"What does the document say about {title}?",
        "research_open": f"What limitations or open problems are discussed regarding {title}?",
        "long_context_synthesis": f"Summarize the key points about {title}.",
        "key_fact": first,
        "counter_claim": "",
    }


class QueryBank:
    def __init__(self, provider_name="ollama", model=None, use_llm=True):
        self.use_llm = use_llm
        self.provider = get_provider(provider_name, model=model) if use_llm else None
        self.cache = {}
        if CACHE.exists():
            for line in CACHE.open():
                d = json.loads(line)
                self.cache[d["source_id"]] = d["queries"]

    def for_doc(self, source_id: str, title: str, text: str) -> dict:
        if source_id in self.cache:
            return self.cache[source_id]
        if not self.use_llm:
            queries = _fallback(title, text)
            self.cache[source_id] = queries
            return queries
        excerpt = text[:3000]
        queries = None
        try:
            r = self.provider.complete(_PROMPT.format(title=title, excerpt=excerpt),
                                       system=_SYS, max_tokens=400, temperature=0.3)
            queries = _parse_json(r.text)
        except Exception:
            queries = None
        if not queries or "factual" not in queries:
            queries = _fallback(title, text)
        self.cache[source_id] = queries
        with CACHE.open("a") as f:
            f.write(json.dumps({"source_id": source_id, "queries": queries}) + "\n")
        return queries
