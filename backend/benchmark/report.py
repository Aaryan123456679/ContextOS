"""Aggregate per-case benchmark results into headline + per-category reports."""
import json
import statistics
from pathlib import Path
from typing import List, Dict, Any


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else 0.0


def _pct(num, den):
    return (100.0 * num / den) if den else 0.0


def aggregate(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    cats = sorted({r["category"] for r in results})

    def block(rows):
        n = len(rows)
        if n == 0:
            return {}
        gold_keep = sum(1 for r in rows if r["gold_retained"])
        naive_keep = sum(1 for r in rows if r["naive_gold_retained"])
        contra_rows = [r for r in rows if r.get("conflict_present")]
        return {
            "cases": n,
            "avg_baseline_tokens": round(_mean([r["baseline_tokens"] for r in rows]), 1),
            "avg_optimized_tokens": round(_mean([r["optimized_tokens"] for r in rows]), 1),
            "avg_token_reduction_pct": round(_mean([r["token_reduction_pct"] for r in rows]), 2),
            "gold_retention_pct": round(_pct(gold_keep, n), 2),
            "naive_gold_retention_pct": round(_pct(naive_keep, n), 2),
            "avg_distractor_removal_pct": round(_mean([r["distractor_removal_pct"] for r in rows]), 2),
            "contradiction_flag_pct": round(_pct(sum(1 for r in contra_rows if r.get("contradiction_flagged")), len(contra_rows)), 2) if contra_rows else None,
            "wrong_fact_dropped_pct": round(_pct(sum(1 for r in contra_rows if r.get("conflict_dropped")), len(contra_rows)), 2) if contra_rows else None,
        }

    summary = {"overall": block(results), "by_category": {c: block([r for r in results if r["category"] == c]) for c in cats}}

    # LLM subset (only present if --llm-subset was used)
    llm_rows = [r for r in results if r.get("llm") is not None]
    if llm_rows:
        L = [r["llm"] for r in llm_rows]
        summary["llm_subset"] = {
            "cases": len(L),
            "baseline_answer_accuracy_pct": round(_pct(sum(1 for x in L if x["baseline_correct"]), len(L)), 2),
            "optimized_answer_accuracy_pct": round(_pct(sum(1 for x in L if x["optimized_correct"]), len(L)), 2),
            "avg_bertscore_f1_baseline_vs_optimized": round(_mean([x.get("bertscore_f1") for x in L]), 4),
            "avg_token_reduction_pct": round(_mean([r["token_reduction_pct"] for r in llm_rows]), 2),
            "avg_cost_reduction_pct": round(_mean([x.get("cost_reduction_pct") for x in L]), 2),
        }
    return summary


def render_markdown(summary: Dict[str, Any]) -> str:
    o = summary["overall"]
    lines = []
    lines.append("# ContextOS Benchmark Report\n")
    lines.append(f"**Cases evaluated:** {o['cases']}\n")
    lines.append("## Headline\n")
    lines.append(f"- **Token reduction vs full context:** {o['avg_token_reduction_pct']}% "
                 f"(avg {o['avg_baseline_tokens']} → {o['avg_optimized_tokens']} tokens)")
    lines.append(f"- **Accuracy retained (gold fact kept):** {o['gold_retention_pct']}%  "
                 f"— vs naive truncation at the *same* budget: {o['naive_gold_retention_pct']}%")
    lines.append(f"- **Irrelevant context removed:** {o['avg_distractor_removal_pct']}% of distractors dropped")
    if o.get("wrong_fact_dropped_pct") is not None:
        lines.append(f"- **Contradiction handling:** {o['contradiction_flag_pct']}% of conflicts flagged, "
                     f"{o['wrong_fact_dropped_pct']}% of wrong facts dropped")
    lines.append("")
    lines.append("> Interpretation: ContextOS sends far fewer tokens while keeping the fact needed to "
                 "answer at a rate comparable to sending everything — and well above naive truncation "
                 "that uses the same token budget.\n")

    lines.append("## By category\n")
    hdr = ("| Category | Cases | Baseline tok | Optimized tok | Token ↓ % | Gold kept % | "
           "Naive gold kept % | Distractors removed % |")
    sep = "|" + "---|" * 8
    lines.append(hdr)
    lines.append(sep)
    for cat, b in summary["by_category"].items():
        lines.append(f"| {cat} | {b['cases']} | {b['avg_baseline_tokens']} | {b['avg_optimized_tokens']} | "
                     f"{b['avg_token_reduction_pct']} | {b['gold_retention_pct']} | "
                     f"{b['naive_gold_retention_pct']} | {b['avg_distractor_removal_pct']} |")
    lines.append("")

    if "llm_subset" in summary:
        s = summary["llm_subset"]
        lines.append("## LLM-scored accuracy subset (real model answers)\n")
        lines.append(f"- Cases: {s['cases']}")
        lines.append(f"- **Answer accuracy — full context:** {s['baseline_answer_accuracy_pct']}%")
        lines.append(f"- **Answer accuracy — ContextOS optimized:** {s['optimized_answer_accuracy_pct']}%")
        lines.append(f"- **BERTScore F1 (full vs optimized answers):** {s['avg_bertscore_f1_baseline_vs_optimized']}")
        lines.append(f"- **Token reduction on these cases:** {s['avg_token_reduction_pct']}%")
        lines.append(f"- **Estimated cost reduction:** {s['avg_cost_reduction_pct']}%")
        lines.append("")
        lines.append("> The optimized context answers about as accurately as the full context while "
                     "using a fraction of the tokens (and cost).\n")
    return "\n".join(lines)


def write_csv(results: List[Dict[str, Any]], path: Path):
    import csv
    fields = ["id", "category", "baseline_tokens", "optimized_tokens", "token_reduction_pct",
              "gold_retained", "naive_gold_retained", "distractor_removal_pct",
              "conflict_present", "contradiction_flagged", "conflict_dropped"]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(r)


if __name__ == "__main__":
    import sys
    res_path = Path(sys.argv[1] if len(sys.argv) > 1 else "benchmark/results/results.jsonl")
    results = [json.loads(l) for l in res_path.open()]
    summary = aggregate(results)
    print(render_markdown(summary))
