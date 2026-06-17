"""
Matched-reduction Pareto sweep + dynamic router, mixed datasets, cost-capped, resumable.

At each target reduction r every method gets the same per-example budget B=(1-r)*base:
  - llmlingua : LLMLingua-2 compresses full context to ~B tokens (SOTA)
  - learned   : keep top policy-prob chunks to B tokens (ours)
  - fixed     : score-density allocator to B tokens (heuristic baseline)
  - router    : DYNAMIC — LLMLingua if r<=crossover else learned (derived, no extra cost)

Engine signals computed once/example. Crash-safe + resumable (skips finished ids).
Live cost tracking with a hard --max-usd stop.

Usage:
    python -m bench.pareto --dataset mix --limit 2000 --levels 0.55,0.70,0.85 \
        --provider openrouter --model openai/gpt-4o-mini --max-usd 9 --run-name pareto_2k
"""
import argparse
import asyncio
import csv
import random
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
CROSSOVER = 0.60  # router: SOTA at/below this reduction, ours above
IN_RATE, OUT_RATE = 0.15 / 1e6, 0.60 / 1e6  # gpt-4o-mini USD/token


def _load_mix(dataset, n, offset):
    """Return list of (example, build_fn). 'mix' interleaves hotpot + musique held-out."""
    from hotpotqa import loader as hl, retrieve_hotpot
    from musique import loader as ml, build as mb
    if dataset == "hotpot":
        return [(e, retrieve_hotpot.build) for e in hl.load(n, offset=offset)]
    if dataset == "musique":
        return [(e, mb.build) for e in ml.load(n, offset=offset)]
    if dataset == "mix":
        half = n // 2
        a = [(e, retrieve_hotpot.build) for e in hl.load(half, offset=offset)]
        b = [(e, mb.build) for e in ml.load(n - half, offset=offset)]
        mixed = a + b
        random.Random(42).shuffle(mixed)
        return mixed
    raise ValueError(dataset)


def _ctx(scs):
    return "\n\n".join(sc.chunk.content for sc in scs)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="mix", choices=["hotpot", "musique", "mix"])
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--offset", type=int, default=300)
    ap.add_argument("--levels", default="0.55,0.70,0.85")
    ap.add_argument("--provider", default="openrouter")
    ap.add_argument("--model", default="openai/gpt-4o-mini")
    ap.add_argument("--engines", default="roi,dependency,contradiction")
    ap.add_argument("--max-usd", type=float, default=9.0)
    ap.add_argument("--run-name", default="pareto_2k")
    args = ap.parse_args()

    levels = [float(x) for x in args.levels.split(",")]
    methods = ["llmlingua", "learned", "fixed"]
    engine_set = {e: (e in {x.strip() for x in args.engines.split(",") if x.strip()})
                  for e in cop.ALL_ENGINES}
    items = _load_mix(args.dataset, args.limit, args.offset)
    provider = get_provider(args.provider, model=args.model)
    out_dir = config.RESULTS_DIR / args.run_name
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "results.csv"

    # resume: skip ids already complete
    expected = 1 + len(levels) * len(methods)
    done_count = defaultdict(int)
    if csv_path.exists():
        for r in csv.DictReader(csv_path.open()):
            done_count[r["id"]] += 1
    done = {k for k, v in done_count.items() if v >= expected}
    write_header = not csv_path.exists()
    f = csv_path.open("a", newline="")
    cw = csv.DictWriter(f, fieldnames=["id", "ds", "method", "level", "tokens", "reduction_pct", "em", "f1"])
    if write_header:
        cw.writeheader()

    usd = [0.0]

    def gen(ctx, q):
        r = provider.complete(_PROMPT.format(ctx=ctx[:12000], q=q), max_tokens=64)
        usd[0] += r.prompt_tokens * IN_RATE + r.completion_tokens * OUT_RATE
        return r.text

    t0 = time.time()
    todo = [it for it in items if it[0]["id"] not in done]
    print(f"Pareto {args.dataset}: {len(todo)} to do ({len(done)} resumed) · levels={levels} "
          f"· router crossover={CROSSOVER} · cap=${args.max_usd} · model={provider.model}\n")
    n_proc = 0
    try:
        for ex, build_fn in todo:
            if usd[0] >= args.max_usd:
                print(f"\n!! hit cost cap ${args.max_usd} — stopping cleanly")
                break
            cands, gold_ids, gold = build_fn(ex)
            if not cands:
                continue
            q = ex.get("question") or ex.get("query")
            ds = "musique" if "paragraphs" in ex and len(ex.get("paragraphs", [])) > 12 else "hotpot"
            full = "\n\n".join(c.content for c in cands)
            base_tok = sum(c.token_count for c in cands)
            scored, chain_ids, _ = await cop._score_all(cands, q, engine_set)

            row0 = {"id": ex["id"], "ds": ds, "method": "baseline", "level": 0.0,
                    "tokens": base_tok, "reduction_pct": 0.0}
            sc = em_f1.score(gen(full, q), gold)
            cw.writerow({**row0, **sc}); f.flush()
            for r in levels:
                B = max(16, int((1 - r) * base_tok))
                ctxs = {
                    "llmlingua": llmlingua2.compress(full, target_token=B),
                    "learned": _ctx(cop._learned_select(scored, cands, chain_ids, q, threshold=0.0, token_cap=B)),
                    "fixed": _ctx(cop._alloc.allocate(scored, B).selected),
                }
                for m in methods:
                    ctx = ctxs[m]
                    tok = cop._tokens(ctx)
                    red = 100.0 * (base_tok - tok) / base_tok if base_tok else 0.0
                    s = em_f1.score(gen(ctx, q), gold)
                    cw.writerow({"id": ex["id"], "ds": ds, "method": m, "level": r,
                                 "tokens": tok, "reduction_pct": round(red, 2), **s})
                f.flush()
            n_proc += 1
            if n_proc % 25 == 0:
                el = time.time() - t0
                print(f"  {n_proc}/{len(todo)} · ${usd[0]:.2f} · {el:.0f}s · {el/n_proc:.1f}s/ex")
    except Exception as e:
        print(f"\n!! stopped: {str(e)[:160]}")
    finally:
        f.close()
    print(f"\nspent ${usd[0]:.2f} on {n_proc} new examples")
    _report(csv_path, out_dir, levels, provider.model)


def _report(csv_path, out_dir, levels, model):
    rows = list(csv.DictReader(csv_path.open()))
    for r in rows:
        r["level"] = float(r["level"]); r["f1"] = float(r["f1"]); r["reduction_pct"] = float(r["reduction_pct"])
    n = len(set(r["id"] for r in rows))
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by[r["method"]][r["level"]].append(r)
    base_f1 = mean(r["f1"] for r in rows if r["method"] == "baseline") if rows else 0.0

    def cell(m, lv):
        rs = by[m].get(lv, [])
        return (mean(x["reduction_pct"] for x in rs), mean(x["f1"] for x in rs)) if rs else (None, None)

    lines = [f"# Matched-reduction Pareto + dynamic router — {model}, n={n}",
             f"\nbaseline F1 = {base_f1:.3f} (full context) · router crossover = {CROSSOVER}\n",
             f"{'target':>7}{'llmlingua F1':>14}{'learned F1':>12}{'fixed F1':>10}{'ROUTER F1':>11}{'winner':>10}",
             "-" * 64]
    for lv in levels:
        lr, lf = cell("llmlingua", lv)
        er, ef = cell("learned", lv)
        fr, ff = cell("fixed", lv)
        router_f1 = lf if lv <= CROSSOVER else ef
        win = "ours" if (ef or 0) > (lf or 0) else "SOTA"
        lines.append(f"{int(lv*100):>6}%{(lf or 0):>14.3f}{(ef or 0):>12.3f}{(ff or 0):>10.3f}"
                     f"{(router_f1 or 0):>11.3f}{win:>10}")
    # per-dataset breakdown of the high-reduction win
    lines += ["", "## ours - SOTA (F1) by dataset & level", "",
              f"{'level':>7}{'HotpotQA':>12}{'MuSiQue':>12}"]
    for lv in levels:
        d = {}
        for ds in ("hotpot", "musique"):
            l = [x["f1"] for x in by["llmlingua"].get(lv, []) if x["ds"] == ds]
            e = [x["f1"] for x in by["learned"].get(lv, []) if x["ds"] == ds]
            d[ds] = (mean(e) - mean(l)) if l and e else float("nan")
        lines.append(f"{int(lv*100):>6}%{d['hotpot']:>+12.3f}{d['musique']:>+12.3f}")
    report = "\n".join(lines)
    (out_dir / "comparison.md").write_text(report + "\n")
    print("\n" + report + f"\n\nwrote {out_dir}/comparison.md")


if __name__ == "__main__":
    asyncio.run(main())
