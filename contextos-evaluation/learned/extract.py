"""
Extract per-chunk features + keep/drop labels for the learned selection policy.

Label = 1 if the chunk is gold evidence (HotpotQA supporting paragraph), else 0.
Features fuse ALL engine signals (see contextos_pipeline.chunk_features). No LLM.

Usage:
    python -m learned.extract --dataset hotpot --limit 300 --out learned/features_hotpot.csv
"""
import argparse
import asyncio
import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from pipeline import contextos_pipeline as cop  # noqa: E402


def _loader(dataset):
    if dataset == "hotpot":
        from hotpotqa import loader, retrieve_hotpot
        return loader.load, retrieve_hotpot.build, "hotpot"
    if dataset == "mrqa":
        from mrqa import loader, build as mrqa_build
        return (lambda n: loader.load(n)), mrqa_build.build, "mrqa"
    if dataset == "musique":
        from musique import loader, build as mq_build
        return (lambda n: loader.load(n)), mq_build.build, "musique"
    raise ValueError(dataset)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="hotpot", choices=["hotpot", "mrqa", "musique"])
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--engines", default="roi,dependency,contradiction")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    load_fn, build_fn, tag = _loader(args.dataset)
    engine_set = {e: (e in {x.strip() for x in args.engines.split(",") if x.strip()})
                  for e in cop.ALL_ENGINES}
    examples = load_fn(args.limit)
    out = Path(args.out) if args.out else (Path(__file__).resolve().parent / f"features_{tag}.csv")

    fields = ["example_id", "subset", "label"] + cop.FEATURE_COLS
    n_rows = n_pos = 0
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for i, ex in enumerate(examples):
            cands, gold_ids, _ = build_fn(ex)
            if not cands:
                continue
            rows = await cop.chunk_features(cands, ex.get("question") or ex.get("query"), engine_set)
            for r in rows:
                from uuid import UUID
                label = 1 if UUID(r["chunk_id"]) in gold_ids else 0
                r.update({"example_id": ex["id"], "subset": ex.get("subset", tag), "label": label})
                w.writerow(r); n_rows += 1; n_pos += label
            if (i + 1) % 50 == 0:
                print(f"  {i+1}/{len(examples)} examples, {n_rows} chunks, {n_pos} positive")
    print(f"\nwrote {out}: {n_rows} chunks, {n_pos} positive ({100*n_pos/max(n_rows,1):.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())
