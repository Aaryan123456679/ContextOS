"""LLM-as-judge quality scoring (reference-free) and answer relevance."""
import json
import re

_SYS = ("You are a strict evaluator of answer quality. Score only from the given "
        "context and question. Output strict JSON only.")

_PROMPT = """Question:
{query}

Context provided to the answerer:
{context}

Answer to evaluate:
{answer}

Rate the answer 1-5 on each criterion and output JSON exactly:
{{"completeness": int, "correctness": int, "clarity": int, "grounding": int}}
- completeness: covers what the question asks
- correctness: factually right per the context
- clarity: clear and well-structured
- grounding: supported by the context, no invented facts
JSON:"""


def _parse(text: str):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def judge_quality(provider, query: str, context: str, answer: str) -> dict:
    """Return {quality_score (0-10), completeness, correctness, clarity, grounding}."""
    if not answer.strip():
        return {"quality_score": 0.0, "completeness": 0, "correctness": 0,
                "clarity": 0, "grounding": 0}
    try:
        r = provider.complete(_PROMPT.format(query=query, context=context[:6000], answer=answer[:3000]),
                              system=_SYS, max_tokens=120, temperature=0.0)
        d = _parse(r.text) or {}
    except Exception:
        d = {}
    comp = int(d.get("completeness", 0) or 0)
    corr = int(d.get("correctness", 0) or 0)
    clar = int(d.get("clarity", 0) or 0)
    grnd = int(d.get("grounding", 0) or 0)
    quality = (comp + corr + clar + grnd) / 20.0 * 10.0  # → 0..10
    return {"quality_score": round(quality, 3), "completeness": comp,
            "correctness": corr, "clarity": clar, "grounding": grnd}
