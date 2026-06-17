"""
Run the ContextOS pipeline over the benchmark dataset and measure, per case:

  • token reduction  — full candidate pool vs the pipeline-selected context
  • gold retention   — was the chunk that actually answers the query kept?
  • naive comparison — gold retention if you just truncate to the same token budget
  • distractor removal, contradiction flagging, wrong-fact suppression

The token/retention metrics are fully deterministic (no LLM), so they scale to
10k cases. With --llm-subset N, N cases are additionally answered by the real
model (full context vs optimized) and scored for answer accuracy + BERTScore.

Usage (run from the backend/ directory):
    python -m benchmark.generate_dataset --n 10000
    python -m benchmark.run_benchmark --limit 1000
    python -m benchmark.run_benchmark --full --llm-subset 20
"""
import argparse
import asyncio
import json
import time
import uuid
from pathlib import Path

from models.schemas.chunk import Chunk
from services.engines.roi_engine import ROIEngine
from services.engines.dependency_graph import DependencyGraphBuilder
from services.engines.contradiction import ContradictionDetector
from services.engines.fusion import FusionEngine
from services.engines.token_budget import TokenBudgetAllocator

_FALLBACK_GEMINI_MODELS = [
    "gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite", "gemini-flash-latest",
]

roi_engine = ROIEngine()
dep_builder = DependencyGraphBuilder()
contra_detector = ContradictionDetector()
fusion_engine = FusionEngine()
allocator = TokenBudgetAllocator()


def build_chunks(case):
    chunks, meta_by_id = [], {}
    for c in case["chunks"]:
        cid = uuid.UUID(c["id"])
        md = {"source": "benchmark"}
        if c.get("timestamp"):
            md["created_at"] = c["timestamp"]
        chunks.append(Chunk(id=cid, content=c["content"], token_count=c["token_count"],
                            document_id=uuid.uuid4(), metadata=md))
        meta_by_id[cid] = c
    return chunks, meta_by_id


def naive_select(chunks, budget):
    """Baseline selection: keep chunks in original (retrieval) order until budget."""
    kept, remaining = [], budget
    for c in chunks:
        if c.token_count <= remaining:
            kept.append(c)
            remaining -= c.token_count
    return {c.id for c in kept}


async def run_case(case):
    chunks, meta = build_chunks(case)
    query, budget = case["query"], case["budget"]

    # ── ContextOS pipeline (mirrors api/routes/chat.py) ──────────────────────
    try:
        roi_tuples = roi_engine.score(query, chunks)
        roi_by_id = {c.id: s for c, s in roi_tuples}
    except Exception:
        roi_by_id = {c.id: 0.5 for c in chunks}
    roi_scores = [roi_by_id.get(c.id, 0.5) for c in chunks]

    try:
        dep = await dep_builder.build(query, chunks)
        dep_mask = dep.pruning_mask
        dep_boost = dep.chain_chunk_ids
    except Exception:
        dep_mask, dep_boost = {}, set()

    try:
        contra_flags = await contra_detector.detect(chunks)
    except Exception:
        contra_flags = []

    scored = fusion_engine.fuse(chunks, roi_scores, dep_mask, contra_flags, dep_boost)
    selected = allocator.allocate(scored, budget).selected
    selected_ids = {sc.chunk.id for sc in selected}

    # ── Metrics ──────────────────────────────────────────────────────────────
    baseline_tokens = sum(c.token_count for c in chunks)
    optimized_tokens = sum(sc.chunk.token_count for sc in selected)

    gold_ids = {c.id for c in chunks if meta[c.id]["is_gold"]}
    distractor_ids = {c.id for c in chunks if meta[c.id]["is_distractor"]}
    conflict_ids = {c.id for c in chunks if meta[c.id]["is_conflict"]}

    naive_ids = naive_select(chunks, budget)

    distractors_dropped = len(distractor_ids - selected_ids)
    contra_involved = {fid for f in contra_flags for fid in (f.chunk_a_id, f.chunk_b_id)}

    return {
        "id": case["id"],
        "category": case["category"],
        "baseline_tokens": baseline_tokens,
        "optimized_tokens": optimized_tokens,
        "token_reduction_pct": round(100.0 * (baseline_tokens - optimized_tokens) / baseline_tokens, 2) if baseline_tokens else 0.0,
        "gold_retained": bool(gold_ids) and gold_ids.issubset(selected_ids),
        "naive_gold_retained": bool(gold_ids) and gold_ids.issubset(naive_ids),
        "distractor_removal_pct": round(100.0 * distractors_dropped / len(distractor_ids), 2) if distractor_ids else 0.0,
        "conflict_present": bool(conflict_ids),
        "contradiction_flagged": bool(conflict_ids & contra_involved),
        "conflict_dropped": bool(conflict_ids) and not (conflict_ids & selected_ids),
        # carry context for an optional LLM pass
        "_chunks": [c.content for c in chunks],
        "_selected": [sc.chunk.content for sc in selected],
        "_query": query,
        "_gold_answer": case["gold_answer"],
    }


async def llm_score(rows, api_key, n):
    from services.llm.gateway import LLMGateway
    gw = LLMGateway()
    try:
        from bert_score import score as bert_score
    except Exception:
        bert_score = None

    def prompt_for(ctx, q):
        return (f"Answer the question using ONLY the context. Be concise.\n\n"
                f"Context:\n{ctx}\n\nQuestion: {q}\nAnswer:")

    done = 0
    for r in rows:
        if done >= n:
            break
        try:
            full_ctx = "\n".join(r["_chunks"])
            opt_ctx = "\n".join(r["_selected"])
            base = await gw.complete_with_fallback(prompt_for(full_ctx, r["_query"]), _FALLBACK_GEMINI_MODELS, api_key, max_tokens=64)
            opt = await gw.complete_with_fallback(prompt_for(opt_ctx, r["_query"]), _FALLBACK_GEMINI_MODELS, api_key, max_tokens=64)
        except Exception as e:
            print(f"  LLM scoring stopped ({e}); scored {done} cases")
            break
        gold = r["_gold_answer"].lower()
        f1 = None
        if bert_score is not None:
            try:
                _, _, F = bert_score([opt.content], [base.content], lang="en", verbose=False)
                f1 = float(F.mean())
            except Exception:
                f1 = None
        base_cost = gw.cost_tracker.calculate_cost(base.model, r["baseline_tokens"], base.usage.completion_tokens)
        opt_cost = gw.cost_tracker.calculate_cost(opt.model, r["optimized_tokens"], opt.usage.completion_tokens)
        r["llm"] = {
            "baseline_correct": gold in base.content.lower(),
            "optimized_correct": gold in opt.content.lower(),
            "bertscore_f1": f1,
            "cost_reduction_pct": round(100.0 * (base_cost - opt_cost) / base_cost, 2) if base_cost else 0.0,
        }
        done += 1
        if done % 5 == 0:
            print(f"  LLM-scored {done}/{n}")
    return done


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="benchmark/data/dataset.jsonl")
    ap.add_argument("--out-dir", default="benchmark/results")
    ap.add_argument("--limit", type=int, default=1000, help="number of cases to run")
    ap.add_argument("--full", action="store_true", help="run the entire dataset")
    ap.add_argument("--llm-subset", type=int, default=0, help="also LLM-score the first N cases")
    ap.add_argument("--api-key", default=None, help="LLM key (defaults to server GEMINI_API_KEY)")
    args = ap.parse_args()

    cases = [json.loads(l) for l in Path(args.dataset).open()]
    if not args.full:
        cases = cases[: args.limit]
    print(f"Running {len(cases)} cases through the ContextOS pipeline...")

    t0 = time.time()
    results = []
    for i, case in enumerate(cases, 1):
        results.append(await run_case(case))
        if i % 100 == 0 or i == len(cases):
            elapsed = time.time() - t0
            print(f"  {i}/{len(cases)}  ({elapsed:.0f}s, {i/elapsed:.1f} cases/s)")

    if args.llm_subset > 0:
        api_key = args.api_key
        if not api_key:
            from core.config import settings
            api_key = settings.GEMINI_API_KEY
        if not api_key:
            print("No API key for --llm-subset; skipping LLM scoring.")
        else:
            print(f"LLM-scoring up to {args.llm_subset} cases (full vs optimized answers)...")
            await llm_score(results, api_key, args.llm_subset)

    # Strip internal fields before persisting case rows.
    for r in results:
        for k in ("_chunks", "_selected", "_query", "_gold_answer"):
            r.pop(k, None)

    from benchmark import report
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "results.jsonl").open("w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    summary = report.aggregate(results)
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    md = report.render_markdown(summary)
    (out / "report.md").write_text(md)
    report.write_csv(results, out / "results.csv")

    print("\n" + md)
    print(f"\nArtifacts written to {out}/  (report.md, summary.json, results.jsonl, results.csv)")


if __name__ == "__main__":
    asyncio.run(main())
