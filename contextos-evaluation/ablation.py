"""
Ablation study: quantify each engine's contribution to token savings and quality.

Runs the SAME scenarios under several engine configurations (none, cumulative
add-one, leave-one-out, +compression) and reports, per engine, how much it adds
to token reduction and answer quality. Engines map to the REAL implementation
(roi≈attention-utility, dependency-graph, contradiction, compression); the spec's
Entropy/Reliability/Personalization engines do not exist and are omitted.

Usage:
    python ablation.py --limit 30
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

CONFIGS = {
    "none": set(),
    "roi": {"roi"},
    "roi+dep": {"roi", "dependency"},
    "full_select": {"roi", "dependency", "contradiction"},
    "full_select+compression": {"roi", "dependency", "contradiction", "compression"},
    "leave_out_roi": {"dependency", "contradiction"},
    "leave_out_dependency": {"roi", "contradiction"},
    "leave_out_contradiction": {"roi", "dependency"},
}
FULL = "full_select"


def _es(names):
    return {e: (e in names) for e in cop.ALL_ENGINES}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default=str(config.SCENARIOS_PATH))
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--provider", default=config.DEFAULT_PROVIDER)
    ap.add_argument("--model", default=config.DEFAULT_MODEL)
    ap.add_argument("--top-k", type=int, default=40)
    ap.add_argument("--run-name", default="ablation")
    args = ap.parse_args()

    scenarios = [json.loads(l) for l in Path(args.scenarios).open()][: args.limit]
    for s in scenarios:
        s["top_k"] = args.top_k
    provider = get_provider(args.provider, model=args.model)
    out = config.RESULTS_DIR / args.run_name
    out.mkdir(parents=True, exist_ok=True)

    per_config = {}
    rows_all = []
    for cfg_name, names in CONFIGS.items():
        es = _es(names)
        reds, quals, recalls = [], [], []
        print(f"\n=== config: {cfg_name} ({sorted(names) or 'naive'}) ===")
        for i, sc in enumerate(scenarios):
            try:
                row = await run_scenario(sc, provider, judged=True, engine_set=es)
            except Exception as e:
                print(f"  {sc['run_id']} failed: {str(e)[:80]}")
                continue
            row["config"] = cfg_name
            rows_all.append(row)
            reds.append(float(row["token_reduction_pct"]))
            recalls.append(float(row["gold_chunk_recall"]))
            if row["quality_score"] != "":
                quals.append(float(row["quality_score"]))
            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(scenarios)}")
        per_config[cfg_name] = {
            "mean_token_reduction_pct": round(mean(reds), 2) if reds else 0.0,
            "mean_quality": round(mean(quals), 3) if quals else 0.0,
            "mean_gold_recall": round(mean(recalls), 3) if recalls else 0.0,
            "n": len(reds),
        }

    # Per-engine contribution = full − leave_out(engine)
    contrib = {}
    full = per_config.get(FULL, {})
    for eng, lo in [("roi", "leave_out_roi"), ("dependency", "leave_out_dependency"),
                    ("contradiction", "leave_out_contradiction")]:
        if lo in per_config and full:
            contrib[eng] = {
                "token_savings_contribution_pct": round(full["mean_token_reduction_pct"] - per_config[lo]["mean_token_reduction_pct"], 2),
                "quality_contribution": round(full["mean_quality"] - per_config[lo]["mean_quality"], 3),
                "gold_recall_contribution": round(full["mean_gold_recall"] - per_config[lo]["mean_gold_recall"], 3),
            }
    # Compression contribution = (full+compression) − full
    if "full_select+compression" in per_config and full:
        c = per_config["full_select+compression"]
        contrib["compression"] = {
            "token_savings_contribution_pct": round(c["mean_token_reduction_pct"] - full["mean_token_reduction_pct"], 2),
            "quality_contribution": round(c["mean_quality"] - full["mean_quality"], 3),
            "gold_recall_contribution": round(c["mean_gold_recall"] - full["mean_gold_recall"], 3),
        }

    summary = {"per_config": per_config, "engine_contribution": contrib,
               "n_scenarios": len(scenarios), "model": provider.model}
    (out / "ablation_summary.json").write_text(json.dumps(summary, indent=2))
    with (out / "ablation_rows.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS + ["config"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows_all)

    # Markdown
    md = ["# ContextOS Ablation Study\n", f"Scenarios per config: {len(scenarios)} · model {provider.model}\n",
          "## Configurations\n", "| Config | Token reduction % | Quality | Gold recall | N |", "|---|---|---|---|---|"]
    for k, v in per_config.items():
        md.append(f"| {k} | {v['mean_token_reduction_pct']} | {v['mean_quality']} | {v['mean_gold_recall']} | {v['n']} |")
    md += ["\n## Per-engine contribution (full − leave-one-out; compression = +compression − full)\n",
           "| Engine | Δ token reduction % | Δ quality | Δ gold recall |", "|---|---|---|---|"]
    for eng, c in contrib.items():
        md.append(f"| {eng} | {c['token_savings_contribution_pct']} | {c['quality_contribution']} | {c['gold_recall_contribution']} |")
    (out / "ablation_report.md").write_text("\n".join(md))
    print("\n" + "\n".join(md))
    print(f"\nWrote ablation artifacts to {out}/")


if __name__ == "__main__":
    asyncio.run(main())
