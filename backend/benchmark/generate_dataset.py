"""
Generate a large, reproducible benchmark dataset for ContextOS.

Each case is a self-contained RAG scenario: a query, a pool of candidate chunks
(one or more GOLD chunks that actually answer the query, plus distractors and —
depending on the category — a contradicting chunk or a dependency chain), and the
ground-truth answer. Categories are designed to exercise specific engines:

  • roi          — many irrelevant distractors; ROI cross-encoder must rank gold up.
  • contradiction— a stale/wrong chunk conflicts with the correct (newer) gold chunk.
  • dependency   — the answer needs a 2-hop chain; off-topic chunks are concept-disjoint.
  • compression  — a verbose gold chunk that should compress heavily.
  • mixed        — a blend of the above in one pool.

Usage:
    python -m benchmark.generate_dataset --n 10000 --out benchmark/data/dataset.jsonl
"""
import argparse
import json
import random
import uuid
from pathlib import Path

import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")


def tok(text: str) -> int:
    return len(_enc.encode(text))


# ─── Entity pools (combine for ~millions of distinct facts) ───────────────────
NAMES = [
    "Jane Doe", "Arjun Mehta", "Maria Garcia", "Wei Chen", "Liam Murphy", "Sofia Rossi",
    "Omar Hassan", "Nina Petrova", "Kenji Tanaka", "Aisha Khan", "Lucas Silva", "Emma Schmidt",
    "Noah Williams", "Priya Nair", "Diego Torres", "Hannah Cohen", "Yuki Sato", "Mateo Lopez",
    "Chloe Dubois", "Ravi Kumar", "Grace Park", "Tomas Novak", "Fatima Zahra", "Ivan Volkov",
]
COMPANIES = [
    "Northwind", "Acme Corp", "Globex", "Initech", "Umbrella Labs", "Hooli", "Stark Industries",
    "Wayne Enterprises", "Soylent", "Cyberdyne", "Vandelay", "Massive Dynamic", "Pied Piper",
    "Aperture", "BlueOrigin Co", "Tyrell", "Wonka Inc", "Gekko Capital", "Oscorp", "Nakatomi",
]
CITIES = [
    "Berlin", "Toronto", "Singapore", "Austin", "Dublin", "Milan", "Cairo", "Lisbon",
    "Seoul", "Nairobi", "Bogota", "Helsinki", "Tokyo", "Bengaluru", "Warsaw", "Lima",
]
LANGUAGES = ["Go", "Python", "Rust", "Java", "TypeScript", "Kotlin", "Scala", "Elixir", "C++", "Ruby"]
DOMAINS = [
    "payments", "logistics", "healthcare", "gaming", "robotics", "fintech", "biotech",
    "aerospace", "agritech", "cybersecurity", "edtech", "energy",
]
PRODUCTS = ["Atlas", "Comet", "Pulse", "Nimbus", "Quartz", "Vertex", "Echo", "Lumen", "Forge", "Halo"]


def _id() -> str:
    return str(uuid.uuid4())


def _chunk(content, *, gold=False, distractor=False, conflict=False, ts=None, label=""):
    return {
        "id": _id(),
        "content": content,
        "token_count": tok(content),
        "is_gold": gold,
        "is_distractor": distractor,
        "is_conflict": conflict,
        "timestamp": ts,
        "label": label,
    }


# ─── Fact templates: each returns (gold_sentence, query, gold_answer) ──────────
def fact_join_year(rng):
    name, comp, yr = rng.choice(NAMES), rng.choice(COMPANIES), rng.randint(2005, 2022)
    return (f"{name} joined {comp} in {yr} as a senior engineer.",
            f"In what year did {name} join {comp}?", str(yr), (name, comp, yr))


def fact_hq_city(rng):
    comp, city = rng.choice(COMPANIES), rng.choice(CITIES)
    return (f"{comp} is headquartered in {city}, where it runs its main office.",
            f"In which city is {comp} headquartered?", city, (comp, city))


def fact_language(rng):
    name, lang = rng.choice(NAMES), rng.choice(LANGUAGES)
    return (f"{name} primarily writes production code in {lang}.",
            f"Which programming language does {name} primarily use?", lang, (name, lang))


def fact_domain(rng):
    comp, dom = rng.choice(COMPANIES), rng.choice(DOMAINS)
    return (f"{comp} operates mainly in the {dom} domain.",
            f"Which domain does {comp} operate in?", dom, (comp, dom))


FACTS = [fact_join_year, fact_hq_city, fact_language, fact_domain]


def make_distractor(rng) -> str:
    """A factual-but-irrelevant sentence about unrelated entities."""
    kind = rng.randint(0, 3)
    if kind == 0:
        return f"{rng.choice(NAMES)} enjoys hiking near {rng.choice(CITIES)} on weekends."
    if kind == 1:
        return f"{rng.choice(COMPANIES)} launched a new {rng.choice(PRODUCTS)} product line last quarter."
    if kind == 2:
        return f"The {rng.choice(DOMAINS)} market in {rng.choice(CITIES)} grew steadily this year."
    return f"{rng.choice(NAMES)} gave a talk about {rng.choice(LANGUAGES)} tooling at a meetup."


def gen_roi(rng, idx):
    sent, query, ans, _ = rng.choice(FACTS)(rng)
    chunks = [_chunk(sent, gold=True, label="gold")]
    for _ in range(rng.randint(6, 10)):
        chunks.append(_chunk(make_distractor(rng), distractor=True, label="distractor"))
    rng.shuffle(chunks)
    return _case("roi", query, ans, chunks, rng)


def gen_contradiction(rng, idx):
    # Build a fact with a conflicting (stale/wrong) variant.
    f = rng.choice([fact_join_year, fact_hq_city, fact_language, fact_domain])
    sent, query, ans, parts = f(rng)
    # Make a wrong answer of the same type.
    if f is fact_join_year:
        name, comp, yr = parts
        wrong = str(rng.choice([y for y in range(2005, 2023) if y != yr]))
        wrong_sent = f"{name} joined {comp} in {wrong} as a senior engineer."
    elif f is fact_hq_city:
        comp, city = parts
        wrong = rng.choice([c for c in CITIES if c != city])
        wrong_sent = f"{comp} is headquartered in {wrong}, where it runs its main office."
    elif f is fact_language:
        name, lang = parts
        wrong = rng.choice([l for l in LANGUAGES if l != lang])
        wrong_sent = f"{name} primarily writes production code in {wrong}."
    else:
        comp, dom = parts
        wrong = rng.choice([d for d in DOMAINS if d != dom])
        wrong_sent = f"{comp} operates mainly in the {wrong} domain."
    # Gold is the newer/correct statement; conflict is older/wrong.
    chunks = [
        _chunk(sent, gold=True, ts="2024-01-01", label="gold_correct"),
        _chunk(wrong_sent, conflict=True, ts="2019-01-01", label="conflict_wrong"),
    ]
    for _ in range(rng.randint(4, 7)):
        chunks.append(_chunk(make_distractor(rng), distractor=True, label="distractor"))
    rng.shuffle(chunks)
    return _case("contradiction", query, ans, chunks, rng)


def gen_dependency(rng, idx):
    name, comp, city = rng.choice(NAMES), rng.choice(COMPANIES), rng.choice(CITIES)
    # 2-hop chain: name -> company -> city
    c1 = _chunk(f"{name} works at {comp} on the platform team.", gold=True, label="gold_hop1")
    c2 = _chunk(f"{comp} is based in {city}, where its engineering office is located.", gold=True, label="gold_hop2")
    query = f"In which city does {name} work?"
    chunks = [c1, c2]
    for _ in range(rng.randint(5, 8)):
        chunks.append(_chunk(make_distractor(rng), distractor=True, label="distractor"))
    rng.shuffle(chunks)
    return _case("dependency", query, city, chunks, rng)


def gen_compression(rng, idx):
    sent, query, ans, _ = rng.choice(FACTS)(rng)
    # Pad the gold chunk with verbose, low-information prose around the key fact.
    filler = (
        "It is worth noting, as has been widely discussed in numerous internal reviews and "
        "retrospective meetings over the years, that this particular detail has consistently "
        "been regarded as relevant background context by various stakeholders. "
    )
    verbose = filler + sent + " " + filler
    chunks = [_chunk(verbose, gold=True, label="gold_verbose")]
    for _ in range(rng.randint(4, 7)):
        chunks.append(_chunk(make_distractor(rng) + " " + filler, distractor=True, label="distractor"))
    rng.shuffle(chunks)
    return _case("compression", query, ans, chunks, rng)


def gen_mixed(rng, idx):
    # ROI distractors + a contradiction + a dependency hop.
    case = gen_contradiction(rng, idx)
    extra = make_distractor(rng)
    case["chunks"].append(_chunk(extra, distractor=True, label="distractor"))
    case["category"] = "mixed"
    return case


GENERATORS = {
    "roi": gen_roi,
    "contradiction": gen_contradiction,
    "dependency": gen_dependency,
    "compression": gen_compression,
    "mixed": gen_mixed,
}

# Distribution of the 10k cases across categories.
MIX = {"roi": 0.35, "contradiction": 0.25, "dependency": 0.20, "compression": 0.12, "mixed": 0.08}


def _case(category, query, answer, chunks, rng):
    total_tokens = sum(c["token_count"] for c in chunks)
    gold_tokens = sum(c["token_count"] for c in chunks if c["is_gold"])
    # Budget: enough to hold the gold chunk(s) plus a little headroom, forcing the
    # pipeline to drop most distractors. ~35% of the full pool, min the gold size.
    budget = max(gold_tokens + 20, int(total_tokens * 0.35))
    return {
        "id": _id(),
        "category": category,
        "query": query,
        "gold_answer": answer,
        "budget": budget,
        "chunks": chunks,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="benchmark/data/dataset.jsonl")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    cats = list(MIX.keys())
    weights = [MIX[c] for c in cats]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    counts = {c: 0 for c in cats}
    with out.open("w") as f:
        for i in range(args.n):
            cat = rng.choices(cats, weights=weights, k=1)[0]
            case = GENERATORS[cat](rng, i)
            counts[case["category"]] = counts.get(case["category"], 0) + 1
            f.write(json.dumps(case) + "\n")

    print(f"Wrote {args.n} cases to {out}")
    print("Category counts:", json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
