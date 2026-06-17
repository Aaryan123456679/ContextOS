"""
Compiled multi-dataset benchmark via MRQA.

MRQA unifies 12 extractive-QA datasets into ONE schema, so it's the cleanest way
to test generalization on "many datasets at once" without per-dataset glue:
  validation (in-domain) : SQuAD, NewsQA, TriviaQA, SearchQA, HotpotQA, NaturalQuestions
  test       (out-domain): BioASQ, DROP, DuoRC, RACE, RelationExtraction, TextbookQA

We sample a balanced slice across every subset, so one frozen policy is judged on
diverse shapes (single-hop, multi-hop, long web/news contexts, science, exams).
Each example's `context` is chunked into a candidate pool (relevant + irrelevant
chunks = natural distractors); gold answers give real EM/F1.
"""
import json
import ssl
import urllib.request
from collections import defaultdict
from pathlib import Path

import certifi

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
COMPILED = DATA_DIR / "mrqa_compiled.jsonl"

_SPLIT_URL = ("https://huggingface.co/api/datasets/mrqa-workshop/mrqa/"
              "parquet/plain_text/{split}")


def _ctx():
    return ssl.create_default_context(cafile=certifi.where())


def _download(split: str) -> Path:
    p = DATA_DIR / f"mrqa_{split}.parquet"
    if p.exists():
        return p
    with urllib.request.urlopen(_SPLIT_URL.format(split=split), timeout=60, context=_ctx()) as r:
        urls = json.loads(r.read())
    print(f"downloading {split}: {urls[0]} ...")
    with urllib.request.urlopen(urls[0], timeout=900, context=_ctx()) as r:
        p.write_bytes(r.read())
    print(f"  saved {p} ({p.stat().st_size//1024//1024} MB)")
    return p


def _answers(row) -> list:
    """MRQA stores gold spans under detected_answers.text (and/or answers)."""
    a = row.get("answers")
    if a is not None and len(a):
        return [str(x) for x in a]
    da = row.get("detected_answers")
    if isinstance(da, dict) and da.get("text") is not None and len(da["text"]):
        return [str(x) for x in da["text"]]
    return []


def compile_sample(per_subset: int = 30, seed: int = 42) -> Path:
    """Build a balanced JSONL: up to `per_subset` examples from each MRQA subset."""
    if COMPILED.exists():
        return COMPILED
    import pandas as pd
    import random
    rng = random.Random(seed)
    buckets = defaultdict(list)
    for split in ("validation", "test"):
        df = pd.read_parquet(_download(split))
        cols = set(df.columns)
        for _, row in df.iterrows():
            sub = row.get("subset") or row.get("dataset") or split
            buckets[str(sub)].append(row)
    print(f"subsets found: { {k: len(v) for k, v in buckets.items()} }")
    out = []
    for sub, rows in sorted(buckets.items()):
        rng.shuffle(rows)
        for row in rows:
            ans = _answers(row)
            ctx = row.get("context")
            q = row.get("question")
            if not ans or not ctx or not q:
                continue
            out.append({
                "id": str(row.get("qid") or row.get("id") or f"{sub}-{len(out)}"),
                "subset": sub,
                "question": str(q),
                "context": str(ctx),
                "answers": ans,
                "gold_answer": ans[0],
            })
            if sum(1 for o in out if o["subset"] == sub) >= per_subset:
                break
    rng.shuffle(out)
    with COMPILED.open("w") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    print(f"wrote {COMPILED}: {len(out)} examples across {len(buckets)} subsets")
    return COMPILED


def load(n: int | None = None, per_subset: int = 30) -> list:
    compile_sample(per_subset=per_subset)
    out = []
    with COMPILED.open() as f:
        for i, line in enumerate(f):
            if n is not None and i >= n:
                break
            out.append(json.loads(line))
    return out


if __name__ == "__main__":
    ex = load(per_subset=30)
    from collections import Counter
    print("total:", len(ex), "| per-subset:", dict(Counter(e["subset"] for e in ex)))
    e = ex[0]
    print("\nsubset:", e["subset"], "| Q:", e["question"][:90])
    print("A:", e["answers"], "| context chars:", len(e["context"]))
