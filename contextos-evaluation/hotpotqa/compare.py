"""
HotpotQA: compare fixed budgets vs content-adaptive selection on the SAME examples.

Baseline (all 10 paragraphs) answer is generated ONCE per example and reused as
the reference; only the ContextOS optimized path varies per config. Reports, per
config: mean chunks kept, token reduction, gold-paragraph recall, and EM/F1
against the gold answer.

Usage:
    python -m hotpotqa.compare --limit 50
"""
import argparse
import asyncio
import csv
import json
import time
from pathlib import Path
from statistics import mean
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from providers import get_provider  # noqa: E402
from pipeline import contextos_pipeline as cop  # noqa: E402
from hotpotqa import loader, retrieve_hotpot, em_f1, runner_hotpot  # noqa: E402

# (label, select_mode, budget/cap, params)
CONFIGS = [
    ("fixed@512", "fixed",    512,  {}),                      # reference fixed budget
    ("coverage",  "coverage", 4096, {}),                      # budget-free heuristic
    ("learned",   "learned",  4096, {"threshold": 0.3}),      # learned all-signal policy
]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--offset", type=int, default=0, help="skip first N (held-out eval)")
    ap.add_argument("--provider", default=config.DEFAULT_PROVIDER)
    ap.add_argument("--model", default=config.DEFAULT_MODEL)
    ap.add_argument("--engines", default="roi,dependency,contradiction")
    ap.add_argument("--run-name", default="hotpot_compare")
    args = ap.parse_args()

    engine_set = {e: (e in {x.strip() for x in args.engines.split(",") if x.strip()})
                  for e in cop.ALL_ENGINES}
    examples = loader.load(args.limit, offset=args.offset)
    provider = get_provider(args.provider, model=args.model)
    out_dir = config.RESULTS_DIR / args.run_name
    out_dir.mkdir(parents=True, exist_ok=True)

    P = runner_hotpot._PROMPT
    rows_by_cfg = {c[0]: [] for c in CONFIGS}
    t0 = time.time()
    print(f"compare on {len(examples)} examples · {len(CONFIGS)} configs · model={provider.model}\n")

    # crash-safe: write every row to a combined CSV as it's produced, so a mid-run
    # failure (e.g. API credit cutoff) never wipes completed work.
    combined = (out_dir / "results.csv").open("w", newline="")
    cw = csv.DictWriter(combined, fieldnames=[
        "id", "config", "n_candidates", "n_selected", "token_reduction_pct",
        "gold_para_recall", "baseline_em", "baseline_f1", "optimized_em", "optimized_f1"])
    cw.writeheader()
    try:
        for i, ex in enumerate(examples):
            candidates, gold_ids, gold = retrieve_hotpot.build(ex)
            baseline_ctx = "\n\n".join(c.content for c in candidates)
            baseline_tokens = sum(c.token_count for c in candidates)
            base = provider.complete(P.format(ctx=baseline_ctx[:12000], q=ex["question"]), max_tokens=64)
            bscore = em_f1.score(base.text, gold)
            gold_in_pool = gold_ids & {c.id for c in candidates}

            for label, mode, budget, params in CONFIGS:
                res = await cop.run(candidates, ex["question"], budget, engine_set,
                                    llm_provider=provider, select_mode=mode, select_params=params)
                opt_tokens = res["optimized_tokens"]
                red = 100.0 * (baseline_tokens - opt_tokens) / baseline_tokens if baseline_tokens else 0.0
                gold_kept = gold_in_pool & res["selected_chunk_ids"]
                recall = len(gold_kept) / len(gold_in_pool) if gold_in_pool else 0.0
                opt = provider.complete(P.format(ctx=res["optimized_context"][:12000], q=ex["question"]), max_tokens=64)
                oscore = em_f1.score(opt.text, gold)
                row = {
                    "id": ex["id"], "config": label,
                    "n_candidates": res["n_candidates"], "n_selected": res["n_selected"],
                    "token_reduction_pct": round(red, 2), "gold_para_recall": round(recall, 3),
                    "baseline_em": bscore["em"], "baseline_f1": bscore["f1"],
                    "optimized_em": oscore["em"], "optimized_f1": oscore["f1"],
                }
                rows_by_cfg[label].append(row)
                cw.writerow(row); combined.flush()
            if (i + 1) % 10 == 0:
                print(f"  ...{i+1}/{len(examples)} examples ({time.time()-t0:.0f}s)")
    except Exception as e:
        print(f"\n!! stopped early at example {i}: {str(e)[:140]}\n   aggregating {sum(len(v) for v in rows_by_cfg.values())} completed rows")
    finally:
        combined.close()

    # write per-config CSVs + comparison
    summary = []
    for label, mode, budget, params in CONFIGS:
        rs = rows_by_cfg[label]
        if not rs:
            continue
        with (out_dir / f"results_{label.replace('@','_').replace('-','_')}.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rs[0].keys())); w.writeheader(); w.writerows(rs)
        summary.append({
            "config": label,
            "kept": round(mean(r["n_selected"] for r in rs), 1),
            "reduction_%": round(mean(r["token_reduction_pct"] for r in rs), 1),
            "gold_recall": round(mean(r["gold_para_recall"] for r in rs), 3),
            "base_EM": round(mean(r["baseline_em"] for r in rs), 3),
            "base_F1": round(mean(r["baseline_f1"] for r in rs), 3),
            "opt_EM": round(mean(r["optimized_em"] for r in rs), 3),
            "opt_F1": round(mean(r["optimized_f1"] for r in rs), 3),
            "F1_delta": round(mean(r["optimized_f1"] for r in rs) - mean(r["baseline_f1"] for r in rs), 4),
        })

    (out_dir / "comparison.json").write_text(json.dumps(summary, indent=2))
    hdr = f"{'config':14}{'kept':>6}{'red%':>7}{'recall':>8}{'opt_EM':>8}{'opt_F1':>8}{'F1Δ':>8}"
    lines = [hdr, "-" * len(hdr)]
    for s in summary:
        lines.append(f"{s['config']:14}{s['kept']:>6}{s['reduction_%']:>7}{s['gold_recall']:>8}"
                     f"{s['opt_EM']:>8}{s['opt_F1']:>8}{s['F1_delta']:>+8}")
    base_f1 = summary[0]["base_F1"]
    table = "\n".join(lines)
    (out_dir / "comparison.md").write_text(
        f"# HotpotQA: fixed vs adaptive selection (n={len(examples)}, model={provider.model})\n\n"
        f"Baseline (all 10 paras) F1 = {base_f1} · EM = {summary[0]['base_EM']}\n\n```\n{table}\n```\n")
    print(f"\nbaseline (all paras): F1={base_f1}  EM={summary[0]['base_EM']}")
    print(table)
    print(f"\nwrote {out_dir}/comparison.md  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    asyncio.run(main())
