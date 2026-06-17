"""
HotpotQA (distractor) runner for ContextOS.

baseline  = all 10 paragraphs -> LLM -> answer
ContextOS = optimizer selects paragraphs -> LLM -> answer
Both answers scored with EM / token-F1 against the gold answer. Also reports
deterministic token reduction and gold-paragraph recall (the 2 supporting paras).

Usage (from contextos-evaluation/):
    python -m hotpotqa.runner_hotpot --limit 20
    python -m hotpotqa.runner_hotpot --limit 20 --engines roi,dependency,contradiction
"""
import argparse
import asyncio
import csv
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from providers import get_provider  # noqa: E402
from pipeline import contextos_pipeline as cop  # noqa: E402
from hotpotqa import loader, retrieve_hotpot, em_f1  # noqa: E402

CSV_FIELDS = [
    "id", "type", "level", "question", "gold_answer", "select_mode",
    "baseline_tokens", "optimized_tokens", "token_reduction_pct",
    "n_candidates", "n_selected", "gold_para_recall", "engines_used",
    "opt_pipeline_ms",
    "baseline_answer", "optimized_answer",
    "baseline_em", "baseline_f1", "optimized_em", "optimized_f1",
    "f1_delta", "provider", "model",
]

_PROMPT = ("Answer the question with a short factual answer (a few words, or "
           "yes/no), using ONLY the context. Do not explain.\n\n"
           "Context:\n{ctx}\n\nQuestion: {q}\nAnswer:")


async def run_one(example, provider, engine_set, budget, select_mode="fixed", select_params=None):
    candidates, gold_ids, gold = retrieve_hotpot.build(example)
    baseline_ctx = "\n\n".join(c.content for c in candidates)
    baseline_tokens = sum(c.token_count for c in candidates)

    res = await cop.run(candidates, example["question"], budget, engine_set,
                        llm_provider=provider, select_mode=select_mode,
                        select_params=select_params)
    opt_tokens = res["optimized_tokens"]
    red = 100.0 * (baseline_tokens - opt_tokens) / baseline_tokens if baseline_tokens else 0.0

    gold_in_pool = gold_ids & {c.id for c in candidates}
    gold_kept = gold_in_pool & res["selected_chunk_ids"]
    recall = len(gold_kept) / len(gold_in_pool) if gold_in_pool else 0.0

    base = provider.complete(_PROMPT.format(ctx=baseline_ctx[:12000], q=example["question"]), max_tokens=64)
    opt = provider.complete(_PROMPT.format(ctx=res["optimized_context"][:12000], q=example["question"]), max_tokens=64)
    bs = em_f1.score(base.text, gold)
    os_ = em_f1.score(opt.text, gold)

    return {
        "id": example["id"], "type": example.get("type", ""), "level": example.get("level", ""),
        "question": example["question"][:300], "gold_answer": gold, "select_mode": res["select_mode"],
        "baseline_tokens": baseline_tokens, "optimized_tokens": opt_tokens,
        "token_reduction_pct": round(red, 2),
        "n_candidates": res["n_candidates"], "n_selected": res["n_selected"],
        "gold_para_recall": round(recall, 3), "engines_used": ";".join(res["engines_used"]),
        "opt_pipeline_ms": round(res["opt_pipeline_ms"], 1),
        "baseline_answer": base.text.replace("\n", " ")[:300],
        "optimized_answer": opt.text.replace("\n", " ")[:300],
        "baseline_em": bs["em"], "baseline_f1": bs["f1"],
        "optimized_em": os_["em"], "optimized_f1": os_["f1"],
        "f1_delta": round(os_["f1"] - bs["f1"], 4),
        "provider": provider.name, "model": provider.model,
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--provider", default=config.DEFAULT_PROVIDER)
    ap.add_argument("--model", default=config.DEFAULT_MODEL)
    ap.add_argument("--engines", default="roi,dependency,contradiction")
    ap.add_argument("--budget", type=int, default=config.DEFAULT_TOKEN_BUDGET,
                    help="fixed mode: target tokens. adaptive modes: hard token cap.")
    ap.add_argument("--select", default="fixed",
                    choices=["fixed", "gap", "top_p", "threshold"],
                    help="selection policy (gap/top_p/threshold = content-adaptive)")
    ap.add_argument("--min-keep", type=int, default=1)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--alpha", type=float, default=0.5)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--run-name", default="hotpot_smoke")
    args = ap.parse_args()

    engine_set = {e: (e in {x.strip() for x in args.engines.split(",") if x.strip()})
                  for e in cop.ALL_ENGINES}
    select_params = {"min_keep": args.min_keep, "top_p": args.top_p, "alpha": args.alpha}
    examples = loader.load(args.limit)
    provider = get_provider(args.provider, model=args.model)
    out_dir = Path(args.out_dir) if args.out_dir else (config.RESULTS_DIR / args.run_name)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "results.csv"

    capword = "cap" if args.select != "fixed" else "target"
    print(f"HotpotQA distractor: {len(examples)} examples · select={args.select} "
          f"· budget({capword})={args.budget} · engines={args.engines} · model={provider.model}")
    rows = []
    t0 = time.time()
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for i, ex in enumerate(examples):
            try:
                row = await run_one(ex, provider, engine_set, args.budget,
                                    select_mode=args.select, select_params=select_params)
            except Exception as e:
                print(f"  {ex['id']} failed: {str(e)[:120]}")
                continue
            w.writerow(row); f.flush(); rows.append(row)
            print(f"  [{i+1}/{len(examples)}] kept={row['n_selected']}/{row['n_candidates']}  "
                  f"red={row['token_reduction_pct']:>5}%  recall={row['gold_para_recall']}  "
                  f"baseF1={row['baseline_f1']}  optF1={row['optimized_f1']}")

    # aggregate
    def m(k):
        v = [float(r[k]) for r in rows]
        return sum(v) / len(v) if v else 0.0
    print(f"\n=== HotpotQA smoke summary (n={len(rows)}, {time.time()-t0:.0f}s) ===")
    print(f"  mean token reduction : {m('token_reduction_pct'):.1f}%")
    print(f"  gold-paragraph recall: {m('gold_para_recall'):.3f}")
    print(f"  baseline  EM / F1    : {m('baseline_em'):.3f} / {m('baseline_f1'):.3f}")
    print(f"  ContextOS EM / F1    : {m('optimized_em'):.3f} / {m('optimized_f1'):.3f}")
    print(f"  F1 delta (opt-base)  : {m('optimized_f1')-m('baseline_f1'):+.4f}")
    print(f"\nWrote {csv_path}")


if __name__ == "__main__":
    asyncio.run(main())
