"""
Evaluation runner: baseline path vs ContextOS path over the scenarios, → CSV.

Deterministic metrics (tokens, cost, compression ratio, retrieval quality,
pipeline latency) are computed for every scenario. LLM-dependent metrics
(answers, similarity, faithfulness, relevance, LLM-judge quality) are computed
for the first --judge-subset scenarios (the expensive part). Resumable: re-runs
skip run_ids already present in the output CSV.

Usage (from contextos-evaluation/):
    python runner.py --limit 50 --judge-subset 50
    python runner.py --full                      # deterministic on all 10k
    python runner.py --full --judge-subset 1000  # + judge 1k (resumable, slow)
"""
import argparse
import asyncio
import csv
import json
import time
from datetime import datetime
from pathlib import Path

import config
from providers import get_provider
from pipeline import retrieval, contextos_pipeline as cop
from metrics import similarity, faithfulness, judge as judgemod, relevance

CSV_FIELDS = [
    "run_id", "seed", "query", "query_type", "document_domain", "document_count",
    "document_sizes", "contains_noise", "contains_redundancy", "contains_contradictions",
    "baseline_tokens", "optimized_tokens", "token_reduction_pct",
    "baseline_cost", "optimized_cost", "cost_savings_pct", "engines_used",
    "compression_ratio", "n_candidates", "n_selected", "gold_chunk_recall",
    "baseline_latency_ms", "optimized_latency_ms", "opt_pipeline_ms",
    "baseline_answer", "optimized_answer", "answer_similarity_score", "bertscore_f1",
    "faithfulness_score", "hallucination_score", "relevance_score",
    "quality_score", "baseline_quality_score",
    "completeness", "correctness", "clarity", "grounding",
    "provider", "model", "model_digest", "pass_fail",
]

_ANSWER_PROMPT = ("Answer the question using ONLY the provided context. Be concise and factual.\n\n"
                  "Context:\n{ctx}\n\nQuestion: {q}\nAnswer:")


def _existing_ids(csv_path: Path):
    done = set()
    if csv_path.exists():
        with csv_path.open() as f:
            for row in csv.DictReader(f):
                done.add(row["run_id"])
    return done


async def run_scenario(sc, provider, judged: bool, engine_set: dict):
    candidates, gold_chunk_ids = retrieval.retrieve(sc, top_k=sc.get("top_k", 40))
    baseline_ctx = "\n\n".join(c.content for c in candidates)
    baseline_tokens = sum(c.token_count for c in candidates)

    # Compression needs an LLM call, so only run it on judged rows; deterministic
    # rows measure selection-based reduction (free) at full 10k scale.
    res = await cop.run(candidates, sc["query"], sc["budget"], engine_set,
                        llm_provider=provider if judged else None)
    optimized_tokens = res["optimized_tokens"]
    token_red = 100.0 * (baseline_tokens - optimized_tokens) / baseline_tokens if baseline_tokens else 0.0

    # retrieval quality: gold chunk recall within candidate pool
    gold_in_pool = gold_chunk_ids & {c.id for c in candidates}
    gold_kept = gold_in_pool & res["selected_chunk_ids"]
    gold_recall = (len(gold_kept) / len(gold_in_pool)) if gold_in_pool else 0.0

    base_cost = config.estimate_cost(baseline_tokens, 300)
    opt_cost = config.estimate_cost(optimized_tokens, 300)
    cost_sav = 100.0 * (base_cost - opt_cost) / base_cost if base_cost else 0.0

    row = {
        "run_id": sc["run_id"], "seed": sc["seed"], "query": sc["query"][:300],
        "query_type": sc["query_type"], "document_domain": sc["document_domain"],
        "document_count": sc["document_count"], "document_sizes": json.dumps(sc["document_sizes"]),
        "contains_noise": sc["contains_noise"], "contains_redundancy": sc["contains_redundancy"],
        "contains_contradictions": sc["contains_contradictions"],
        "baseline_tokens": baseline_tokens, "optimized_tokens": optimized_tokens,
        "token_reduction_pct": round(token_red, 2),
        "baseline_cost": round(base_cost, 6), "optimized_cost": round(opt_cost, 6),
        "cost_savings_pct": round(cost_sav, 2), "engines_used": ";".join(res["engines_used"]),
        "compression_ratio": res["compression_ratio"], "n_candidates": res["n_candidates"],
        "n_selected": res["n_selected"], "gold_chunk_recall": round(gold_recall, 3),
        "opt_pipeline_ms": round(res["opt_pipeline_ms"], 1),
        "provider": provider.name, "model": provider.model, "model_digest": provider.model_digest(),
        # LLM fields default empty (deterministic-only rows)
        "baseline_latency_ms": "", "optimized_latency_ms": "", "baseline_answer": "",
        "optimized_answer": "", "answer_similarity_score": "", "bertscore_f1": "",
        "faithfulness_score": "", "hallucination_score": "", "relevance_score": "",
        "quality_score": "", "baseline_quality_score": "",
        "completeness": "", "correctness": "", "clarity": "", "grounding": "",
        "pass_fail": "deterministic_only",
    }

    if judged:
        base = provider.complete(_ANSWER_PROMPT.format(ctx=baseline_ctx[:12000], q=sc["query"]), max_tokens=400)
        opt = provider.complete(_ANSWER_PROMPT.format(ctx=res["optimized_context"][:12000], q=sc["query"]), max_tokens=400)
        sim = similarity.bertscore_f1(opt.text, base.text)
        faith, halluc = faithfulness.faithfulness_and_hallucination(opt.text, res["optimized_context"])
        rel = relevance.relevance(sc["query"], opt.text)
        jq = judgemod.judge_quality(provider, sc["query"], res["optimized_context"], opt.text)
        jb = judgemod.judge_quality(provider, sc["query"], baseline_ctx, base.text)
        passed = (token_red > config.SUCCESS_TOKEN_REDUCTION_PCT and sim > config.SUCCESS_SIMILARITY
                  and jq["quality_score"] >= jb["quality_score"])
        row.update({
            "baseline_latency_ms": round(base.latency_ms, 1),
            "optimized_latency_ms": round(opt.latency_ms, 1),
            "baseline_answer": base.text.replace("\n", " ")[:1000],
            "optimized_answer": opt.text.replace("\n", " ")[:1000],
            "answer_similarity_score": round(sim, 4), "bertscore_f1": round(sim, 4),
            "faithfulness_score": faith, "hallucination_score": halluc, "relevance_score": rel,
            "quality_score": jq["quality_score"], "baseline_quality_score": jb["quality_score"],
            "completeness": jq["completeness"], "correctness": jq["correctness"],
            "clarity": jq["clarity"], "grounding": jq["grounding"],
            "pass_fail": "pass" if passed else "fail",
        })
    return row


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default=str(config.SCENARIOS_PATH))
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--judge-subset", type=int, default=0)
    ap.add_argument("--provider", default=config.DEFAULT_PROVIDER)
    ap.add_argument("--model", default=config.DEFAULT_MODEL)
    ap.add_argument("--engines", default="roi,dependency,contradiction",
                    help="comma list from roi,dependency,contradiction,compression "
                         "(default omits compression, which currently degrades quality)")
    ap.add_argument("--top-k", type=int, default=40)
    ap.add_argument("--shard", default=None, help="process a slice, e.g. 0/2 (worker 0 of 2)")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--run-name", default=None)
    args = ap.parse_args()

    engine_set = {e: (e in {x.strip() for x in args.engines.split(",") if x.strip()})
                  for e in cop.ALL_ENGINES}

    scenarios = [json.loads(l) for l in Path(args.scenarios).open()]
    if args.shard:
        i, ntot = (int(x) for x in args.shard.split("/"))
        scenarios = [s for idx, s in enumerate(scenarios) if idx % ntot == i]
        print(f"Shard {i}/{ntot}: {len(scenarios)} scenarios.")
    if not args.full:
        scenarios = scenarios[: args.limit]
    for s in scenarios:
        s["top_k"] = args.top_k

    run_name = args.run_name or datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out_dir) if args.out_dir else (config.RESULTS_DIR / run_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "results.csv"
    done = _existing_ids(csv_path)

    provider = get_provider(args.provider, model=args.model)
    (out_dir / "run_manifest.json").write_text(json.dumps({
        "run_name": run_name, "seed": config.SEED, "provider": provider.name,
        "model": provider.model, "model_digest": provider.model_digest(),
        "pricing_version": config.PRICING_VERSION, "cost_reference_model": config.COST_REFERENCE_MODEL,
        "engines_enabled": [e for e, on in engine_set.items() if on],
        "judge_subset": args.judge_subset, "top_k": args.top_k,
        "n_scenarios": len(scenarios), "started_at": datetime.now().isoformat(),
    }, indent=2))

    write_header = not csv_path.exists()
    f = csv_path.open("a", newline="")
    w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
    if write_header:
        w.writeheader()

    print(f"Running {len(scenarios)} scenarios (judge first {args.judge_subset}); resuming over {len(done)} done.")
    t0 = time.time()
    n = 0
    for i, sc in enumerate(scenarios):
        if sc["run_id"] in done:
            continue
        judged = i < args.judge_subset
        try:
            row = await run_scenario(sc, provider, judged, engine_set)
        except Exception as e:
            print(f"  {sc['run_id']} failed: {str(e)[:120]}")
            continue
        w.writerow(row)
        f.flush()
        n += 1
        if n % 25 == 0:
            el = time.time() - t0
            print(f"  {n} done ({el:.0f}s, {n/el:.2f}/s) — last token_red={row['token_reduction_pct']}%")
    f.close()
    print(f"\nWrote {n} rows to {csv_path}")
    print("Next: python -m analysis.report", out_dir)


if __name__ == "__main__":
    asyncio.run(main())
