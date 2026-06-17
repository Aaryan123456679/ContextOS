"""
Beat-SOTA benchmark: our learned selector & the selection+compression HYBRID vs
LLMLingua-2 (SOTA token compressor) and the full-context baseline.

Configs (per example, same generator):
  baseline        : full context -> LLM
  llmlingua2@r    : LLMLingua-2 compresses the FULL context (SOTA)
  learned         : our flexible policy selects chunks (dynamic threshold)
  hybrid          : learned selection THEN LLMLingua-2 compresses survivors

Reports EM/F1 + token reduction per config -> a reduction-vs-quality Pareto.
"Beat SOTA" = learned/hybrid sits above the LLMLingua-2 points on that frontier.
Crash-safe (incremental CSV). Held-out via --offset.

Usage:
    python -m bench.beat_sota --dataset hotpot --limit 40 --offset 300 \
        --provider openrouter --model openai/gpt-4o-mini
"""
import argparse
import asyncio
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean
import time
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from providers import get_provider  # noqa: E402
from pipeline import contextos_pipeline as cop  # noqa: E402
from pipeline import llmlingua2  # noqa: E402
from hotpotqa import em_f1  # noqa: E402

_PROMPT = ("Answer the question with a short factual answer (a few words), using ONLY "
           "the context. Do not explain.\n\nContext:\n{ctx}\n\nQuestion: {q}\nAnswer:")


def _loader(dataset):
    if dataset == "hotpot":
        from hotpotqa import loader, retrieve_hotpot
        return loader.load, retrieve_hotpot.build
    if dataset == "musique":
        from musique import loader, build
        return loader.load, build.build
    raise ValueError(dataset)


def _toks(text):
    return cop._tokens(text)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="hotpot", choices=["hotpot", "musique"])
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--provider", default="openrouter")
    ap.add_argument("--model", default="openai/gpt-4o-mini")
    ap.add_argument("--engines", default="roi,dependency,contradiction")
    ap.add_argument("--rate", type=float, default=0.5, help="LLMLingua-2 keep rate")
    ap.add_argument("--run-name", default=None)
    args = ap.parse_args()

    engine_set = {e: (e in {x.strip() for x in args.engines.split(",") if x.strip()})
                  for e in cop.ALL_ENGINES}
    load_fn, build_fn = _loader(args.dataset)
    examples = load_fn(args.limit, offset=args.offset) if args.offset else load_fn(args.limit)
    provider = get_provider(args.provider, model=args.model)
    out_dir = config.RESULTS_DIR / (args.run_name or f"beatsota_{args.dataset}")
    out_dir.mkdir(parents=True, exist_ok=True)

    def gen(ctx, q):
        return provider.complete(_PROMPT.format(ctx=ctx[:12000], q=q), max_tokens=64).text

    rows = []
    combined = (out_dir / "results.csv").open("w", newline="")
    cw = csv.DictWriter(combined, fieldnames=["id", "config", "tokens", "reduction_pct", "em", "f1"])
    cw.writeheader()
    t0 = time.time()
    print(f"beat-SOTA: {args.dataset} n={len(examples)} · LLMLingua-2 rate={args.rate} · model={provider.model}\n")
    try:
        for i, ex in enumerate(examples):
            cands, gold_ids, gold = build_fn(ex)
            if not cands:
                continue
            q = ex.get("question") or ex.get("query")
            full_ctx = "\n\n".join(c.content for c in cands)
            base_tok = sum(c.token_count for c in cands)

            # learned selection context (dynamic threshold)
            res = await cop.run(cands, q, 8192, engine_set, llm_provider=provider,
                                select_mode="learned", select_params={"threshold": "auto"})
            sel_ctx = res["optimized_context"]

            variants = {
                "baseline":      full_ctx,
                f"llmlingua@{args.rate}": llmlingua2.compress(full_ctx, rate=args.rate),
                "learned":       sel_ctx,
                "hybrid":        llmlingua2.compress(sel_ctx, rate=args.rate),
            }
            for name, ctx in variants.items():
                tok = _toks(ctx)
                red = 100.0 * (base_tok - tok) / base_tok if base_tok else 0.0
                sc = em_f1.score(gen(ctx, q), gold)
                row = {"id": ex["id"], "config": name, "tokens": tok,
                       "reduction_pct": round(red, 2), "em": sc["em"], "f1": sc["f1"]}
                rows.append(row); cw.writerow(row); combined.flush()
            if (i + 1) % 10 == 0:
                print(f"  ...{i+1}/{len(examples)} ({time.time()-t0:.0f}s)")
    except Exception as e:
        print(f"\n!! stopped at {i}: {str(e)[:140]}")
    finally:
        combined.close()

    by = defaultdict(list)
    for r in rows:
        by[r["config"]].append(r)
    lines = [f"# Beat-SOTA — {args.dataset}, model={provider.model}, n={len(set(r['id'] for r in rows))}",
             "", f"{'config':18}{'tokens':>8}{'reduction%':>12}{'EM':>7}{'F1':>7}", "-" * 52]
    order = ["baseline", f"llmlingua@{args.rate}", "learned", "hybrid"]
    for name in order:
        rs = by.get(name, [])
        if not rs:
            continue
        lines.append(f"{name:18}{mean(r['tokens'] for r in rs):>8.0f}"
                     f"{mean(r['reduction_pct'] for r in rs):>12.1f}"
                     f"{mean(r['em'] for r in rs):>7.3f}{mean(r['f1'] for r in rs):>7.3f}")
    report = "\n".join(lines)
    (out_dir / "comparison.md").write_text(report + "\n")
    print("\n" + report + f"\n\nwrote {out_dir}/comparison.md ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    asyncio.run(main())
