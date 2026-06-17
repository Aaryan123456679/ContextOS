"""
Cross-LLM evaluation: run the SAME judged scenarios across several models and
compare. Token/cost/retrieval reduction is model-independent (computed before the
LLM), so it stays constant; what varies is answer quality/similarity/faithfulness
— this proves the quality-maintained claim is robust across model families.

Best run on a GPU (Colab T4) where local LLM calls are fast.

Usage:
    python multi_model.py --limit 200 --models llama3.1:8b,mistral:7b,qwen2.5:7b
"""
import argparse
import asyncio
import csv
import json
from pathlib import Path
from statistics import mean

import config
from providers import get_provider
from pipeline import contextos_pipeline as cop
from runner import run_scenario, CSV_FIELDS


def _agg(rows):
    def col(name):
        return [float(r[name]) for r in rows if r.get(name) not in ("", None)]
    sim, qual, bqual = col("answer_similarity_score"), col("quality_score"), col("baseline_quality_score")
    return {
        "n": len(rows),
        "mean_token_reduction_pct": round(mean(col("token_reduction_pct")), 2) if rows else 0,
        "mean_answer_similarity": round(mean(sim), 4) if sim else None,
        "mean_quality": round(mean(qual), 3) if qual else None,
        "mean_baseline_quality": round(mean(bqual), 3) if bqual else None,
        "mean_faithfulness": round(mean(col("faithfulness_score")), 4) if col("faithfulness_score") else None,
        "pass_rate_pct": round(100.0 * sum(1 for r in rows if r.get("pass_fail") == "pass") / len(rows), 2) if rows else 0,
        "quality_maintained_pct": round(100.0 * sum(1 for q, b in zip(qual, bqual) if q >= b) / len(qual), 2) if qual else None,
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default=str(config.SCENARIOS_PATH))
    ap.add_argument("--models", default="llama3.1:8b,mistral:7b")
    ap.add_argument("--provider", default=config.DEFAULT_PROVIDER)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--engines", default="roi,dependency,contradiction")
    ap.add_argument("--top-k", type=int, default=40)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    engine_set = {e: (e in {x.strip() for x in args.engines.split(",")}) for e in cop.ALL_ENGINES}
    scenarios = [json.loads(l) for l in Path(args.scenarios).open()][: args.limit]
    for s in scenarios:
        s["top_k"] = args.top_k

    out = Path(args.out_dir) if args.out_dir else (config.RESULTS_DIR / "multimodel")
    out.mkdir(parents=True, exist_ok=True)

    comparison = {}
    for model in models:
        provider = get_provider(args.provider, model=model)
        safe = model.replace(":", "_").replace("/", "_")
        csv_path = out / f"results_{safe}.csv"
        done = set()
        if csv_path.exists():
            done = {r["run_id"] for r in csv.DictReader(csv_path.open())}
        write_header = not csv_path.exists()
        f = csv_path.open("a", newline="")
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if write_header:
            w.writeheader()
        rows = []
        print(f"\n=== model: {model} ({len(scenarios)} scenarios, resuming {len(done)}) ===")
        for i, sc in enumerate(scenarios):
            if sc["run_id"] in done:
                continue
            try:
                row = await run_scenario(sc, provider, judged=True, engine_set=engine_set)
            except Exception as e:
                print(f"  {sc['run_id']} failed: {str(e)[:80]}")
                continue
            w.writerow(row); f.flush(); rows.append(row)
            if (i + 1) % 20 == 0:
                print(f"  {i+1}/{len(scenarios)}")
        f.close()
        # aggregate over the full CSV (incl. prior resumed rows)
        all_rows = list(csv.DictReader(csv_path.open()))
        comparison[model] = _agg(all_rows)

    (out / "comparison.json").write_text(json.dumps(comparison, indent=2))
    md = ["# Cross-LLM Comparison\n",
          f"Scenarios per model: {len(scenarios)} · engines: {args.engines}\n",
          "Token/cost reduction is model-independent (computed before the LLM); quality varies.\n",
          "| Model | Token ↓ % | Answer sim | Quality | Baseline qual | Faithfulness | Quality kept % | Pass % |",
          "|---|---|---|---|---|---|---|---|"]
    for m, a in comparison.items():
        md.append(f"| {m} | {a['mean_token_reduction_pct']} | {a['mean_answer_similarity']} | "
                  f"{a['mean_quality']} | {a['mean_baseline_quality']} | {a['mean_faithfulness']} | "
                  f"{a['quality_maintained_pct']} | {a['pass_rate_pct']} |")
    (out / "comparison.md").write_text("\n".join(md))
    print("\n" + "\n".join(md))
    print(f"\nWrote cross-model comparison to {out}/")


if __name__ == "__main__":
    asyncio.run(main())
