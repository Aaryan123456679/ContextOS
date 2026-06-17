"""
Compose >=10,000 reproducible evaluation scenarios from the real corpus.

Each scenario is a realistic RAG situation: a query + a mix of documents (the
gold doc(s) that answer it, plus noise, redundancy, and optionally an injected
contradiction). Baseline sends the whole retrieved context; ContextOS optimizes
it. Flags + ids are recorded for reproducibility and per-condition analysis.

Usage:
    python -m scenarios.builder --n 10000                 # LLM queries (slow, high quality)
    python -m scenarios.builder --n 200 --no-llm-queries  # fast templated queries
"""
import argparse
import json
import random
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from corpus.store import CorpusStore
from scenarios.query_gen import QueryBank

NOISE_DOMAINS = {"noise_food", "noise_sports", "noise_travel", "noise_finance"}
RELEVANT_DOMAINS = {"technical_paper", "framework_docs", "technical_article", "business"}

SINGLE_DOC_TYPES = ["factual", "research_open", "long_context_synthesis"]
PAIR_TYPES = ["comparative", "multi_hop"]


def _domain_of(rec):
    return rec.domain


def build(n: int, seed: int, use_llm: bool):
    rng = random.Random(seed)
    store = CorpusStore()
    recs = list(store.records())
    if len(recs) < 10:
        raise SystemExit(f"Corpus too small ({len(recs)} docs). Run corpus.ingest first.")

    relevant = [r for r in recs if r.domain in RELEVANT_DOMAINS]
    noise = [r for r in recs if r.domain in NOISE_DOMAINS]
    by_domain = {}
    for r in relevant:
        by_domain.setdefault(r.domain, []).append(r)
    if not relevant:
        raise SystemExit("No relevant (non-noise) docs in corpus.")

    qbank = QueryBank(use_llm=use_llm)
    out_path = config.SCENARIOS_PATH
    written = 0
    with out_path.open("w") as f:
        # Cycle anchors to reach n; each anchor yields several scenarios.
        anchors = relevant[:]
        rng.shuffle(anchors)
        idx = 0
        while written < n:
            anchor = anchors[idx % len(anchors)]
            idx += 1
            text = store.get_text(anchor.source_id)
            q = qbank.for_doc(anchor.source_id, anchor.title, text)
            qtype = rng.choice(config.QUERY_TYPES)

            gold_ids = [anchor.source_id]
            second = None
            if qtype in PAIR_TYPES:
                pool = [r for r in by_domain.get(anchor.domain, []) if r.source_id != anchor.source_id]
                if pool:
                    second = rng.choice(pool)
                    gold_ids.append(second.source_id)

            # Query text per type (grounded in real titles / LLM bank).
            if qtype == "comparative" and second:
                query = f"Compare {anchor.title} and {second.title}. What are the key tradeoffs?"
            elif qtype == "multi_hop" and second:
                query = f"How does {anchor.title} relate to {second.title}? Explain the connection."
            elif qtype == "contradiction_resolution":
                query = (f"Two sources disagree about {anchor.title}. "
                         f"Which statement is correct and why?")
            else:
                query = q.get(qtype) or q.get("factual")

            # Doc mix: gold + noise + optional redundancy + optional contradiction.
            mix = list(gold_ids)
            contains_noise = rng.random() < 0.85
            if contains_noise and noise:
                k = rng.randint(1, min(5, len(noise)))
                mix += [r.source_id for r in rng.sample(noise, k)]
            contains_redundancy = rng.random() < 0.4
            if contains_redundancy:
                pool = [r for r in by_domain.get(anchor.domain, []) if r.source_id not in mix]
                if pool:
                    mix.append(rng.choice(pool).source_id)
                else:
                    contains_redundancy = False

            inject = None
            contains_contradictions = qtype == "contradiction_resolution" or rng.random() < 0.25
            if contains_contradictions:
                cc = (q.get("counter_claim") or "").strip()
                kf = (q.get("key_fact") or "").strip()
                if cc:
                    inject = f"IMPORTANT UPDATE: {cc}"
                elif kf:
                    inject = f"IMPORTANT UPDATE: Contrary to other sources, it is NOT the case that {kf}"
                else:
                    contains_contradictions = False

            rng.shuffle(mix)
            sizes = [store._index[mid].tokens for mid in mix]
            scenario = {
                "run_id": f"s{written:06d}",
                "seed": seed,
                "query": query,
                "query_type": qtype,
                "document_domain": anchor.domain,
                "doc_ids": mix,
                "gold_doc_ids": gold_ids,
                "document_count": len(mix),
                "document_sizes": sizes,
                "contains_noise": bool(contains_noise and noise),
                "contains_redundancy": bool(contains_redundancy),
                "contains_contradictions": bool(contains_contradictions),
                "contradiction_inject": inject,
                "budget": config.DEFAULT_TOKEN_BUDGET,
            }
            f.write(json.dumps(scenario) + "\n")
            written += 1
            if written % 1000 == 0:
                print(f"  built {written}/{n}")

    print(f"Wrote {written} scenarios to {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=config.SEED)
    ap.add_argument("--no-llm-queries", action="store_true", help="use fast templated queries")
    args = ap.parse_args()
    build(args.n, args.seed, use_llm=not args.no_llm_queries)


if __name__ == "__main__":
    main()
