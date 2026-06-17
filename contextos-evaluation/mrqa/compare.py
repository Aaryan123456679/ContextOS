"""
Frozen cross-dataset generalization test on the compiled MRQA benchmark (12 datasets).

ONE frozen policy, NO per-dataset tuning. We compare:
  - baseline   : full context -> LLM (reference; 0% reduction)
  - coverage   : query-coverage selection (the generic policy under test)
  - fixed@512  : a fixed token budget (expected to NOT generalize: too big for short
                 SQuAD contexts, too small for long SearchQA/TriviaQA ones)
  - fixed@2048 : another fixed point, same point

Reports EM/F1 + token reduction + answer-bearing recall, aggregate AND per-subset.
The genericity claim holds iff coverage keeps EM/F1 ~baseline across ALL subsets
while cutting tokens, without any knob change between datasets.

Usage:
    python -m mrqa.compare --limit 120
"""
import argparse
import asyncio
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
import time
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from providers import get_provider  # noqa: E402
from pipeline import contextos_pipeline as cop  # noqa: E402
from hotpotqa import em_f1  # noqa: E402
from mrqa import loader, build as mrqa_build  # noqa: E402

CONFIGS = [
    ("coverage",  "coverage",  8192, {}),
    ("fixed@512", "fixed",     512,  {}),
    ("fixed@2048","fixed",     2048, {}),
]
_PROMPT = ("Answer the question with a short factual answer (a few words), using ONLY "
           "the context. Do not explain.\n\nContext:\n{ctx}\n\nQuestion: {q}\nAnswer:")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=120)
    ap.add_argument("--per-subset", type=int, default=30)
    ap.add_argument("--provider", default=config.DEFAULT_PROVIDER)
    ap.add_argument("--model", default=config.DEFAULT_MODEL)
    ap.add_argument("--engines", default="roi,dependency,contradiction")
    ap.add_argument("--run-name", default="mrqa_generalize")
    args = ap.parse_args()

    engine_set = {e: (e in {x.strip() for x in args.engines.split(",") if x.strip()})
                  for e in cop.ALL_ENGINES}
    examples = loader.load(args.limit, per_subset=args.per_subset)
    provider = get_provider(args.provider, model=args.model)
    out_dir = config.RESULTS_DIR / args.run_name
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    t0 = time.time()
    print(f"MRQA generalization: {len(examples)} examples · frozen configs={[c[0] for c in CONFIGS]} "
          f"· model={provider.model}\n")
    for i, ex in enumerate(examples):
        cands, gold_ids, gold = mrqa_build.build(ex)
        if not cands:
            continue
        base_ctx = "\n\n".join(c.content for c in cands)
        base_tokens = sum(c.token_count for c in cands)
        base = provider.complete(_PROMPT.format(ctx=base_ctx[:12000], q=ex["question"]), max_tokens=48)
        bsc = em_f1.score(base.text, gold)
        gold_in_pool = gold_ids & {c.id for c in cands}
        for label, mode, budget, params in CONFIGS:
            res = await cop.run(cands, ex["question"], budget, engine_set,
                                llm_provider=provider, select_mode=mode, select_params=params)
            opt_t = res["optimized_tokens"]
            red = 100.0 * (base_tokens - opt_t) / base_tokens if base_tokens else 0.0
            recall = (len(gold_in_pool & res["selected_chunk_ids"]) / len(gold_in_pool)
                      if gold_in_pool else float("nan"))
            opt = provider.complete(_PROMPT.format(ctx=res["optimized_context"][:12000], q=ex["question"]), max_tokens=48)
            osc = em_f1.score(opt.text, gold)
            rows.append({
                "id": ex["id"], "subset": ex["subset"], "config": label,
                "n_candidates": res["n_candidates"], "n_selected": res["n_selected"],
                "base_tokens": base_tokens, "opt_tokens": opt_t, "reduction_pct": round(red, 2),
                "recall": "" if recall != recall else round(recall, 3),
                "base_em": bsc["em"], "base_f1": bsc["f1"],
                "opt_em": osc["em"], "opt_f1": osc["f1"],
            })
        if (i + 1) % 20 == 0:
            print(f"  ...{i+1}/{len(examples)} ({time.time()-t0:.0f}s)")

    with (out_dir / "results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    # ---- aggregate (overall + per config) and per-subset for coverage ----
    def agg(rs):
        rec = [r["recall"] for r in rs if r["recall"] != ""]
        return {
            "n": len(rs), "kept": round(mean(r["n_selected"] for r in rs), 1),
            "reduction": round(mean(r["reduction_pct"] for r in rs), 1),
            "recall": round(mean(rec), 3) if rec else None,
            "EM": round(mean(r["opt_em"] for r in rs), 3),
            "F1": round(mean(r["opt_f1"] for r in rs), 3),
        }
    base_f1 = round(mean(r["base_f1"] for r in rows if r["config"] == CONFIGS[0][0]), 3)
    base_em = round(mean(r["base_em"] for r in rows if r["config"] == CONFIGS[0][0]), 3)

    lines = [f"# MRQA generalization (frozen, no per-dataset tuning) — model={provider.model}",
             f"\n12 subsets · {len(examples)} examples · baseline(all-context) EM={base_em} F1={base_f1}\n",
             "## Overall by config", "",
             f"{'config':12}{'kept':>6}{'red%':>7}{'recall':>8}{'EM':>7}{'F1':>7}", "-"*47]
    by_cfg = defaultdict(list)
    for r in rows:
        by_cfg[r["config"]].append(r)
    for label, *_ in CONFIGS:
        a = agg(by_cfg[label])
        lines.append(f"{label:12}{a['kept']:>6}{a['reduction']:>7}{str(a['recall']):>8}{a['EM']:>7}{a['F1']:>7}")

    lines += ["", "## Coverage (the frozen policy) per subset", "",
              f"{'subset':22}{'kept':>6}{'red%':>7}{'baseF1':>8}{'covF1':>7}{'Δ':>7}", "-"*57]
    cov = [r for r in rows if r["config"] == "coverage"]
    by_sub = defaultdict(list)
    for r in cov:
        by_sub[r["subset"]].append(r)
    base_by_sub = defaultdict(list)
    for r in rows:
        if r["config"] == "coverage":
            base_by_sub[r["subset"]].append(r["base_f1"])
    for sub in sorted(by_sub):
        rs = by_sub[sub]
        bf = mean(base_by_sub[sub]); cf = mean(r["opt_f1"] for r in rs)
        lines.append(f"{sub:22}{mean(r['n_selected'] for r in rs):>6.1f}"
                     f"{mean(r['reduction_pct'] for r in rs):>7.0f}{bf:>8.2f}{cf:>7.2f}{cf-bf:>+7.2f}")

    report = "\n".join(lines)
    (out_dir / "comparison.md").write_text(report + "\n")
    (out_dir / "comparison.json").write_text(json.dumps({l: agg(by_cfg[l]) for l, *_ in CONFIGS}, indent=2))
    print("\n" + report)
    print(f"\nwrote {out_dir}/comparison.md  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    asyncio.run(main())
