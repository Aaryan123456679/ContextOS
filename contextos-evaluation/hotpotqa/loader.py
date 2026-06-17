"""
HotpotQA (distractor setting) loader.

Downloads the HotpotQA distractor *validation* split from the HuggingFace
parquet mirror (the CMU URL is frequently down) and caches it locally. Each
example provides a question, a gold short answer, 10 context paragraphs (2 gold
"supporting" + 8 distractors), and sentence-level supporting-fact annotations.

This is a ground-truth, standard benchmark: it gives real EM/F1 (vs gold answer)
and real gold-paragraph recall — exactly what the scraped, reference-free corpus
could not. The ContextOS optimizer is dataset-agnostic, so the 10 paragraphs feed
straight into the pipeline as candidate chunks (see retrieve_hotpot.py).
"""
import json
import ssl
import urllib.request
from pathlib import Path

import certifi

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PARQUET_PATH = DATA_DIR / "hotpot_distractor_validation.parquet"
JSONL_PATH = DATA_DIR / "hotpot_distractor_validation.jsonl"

# HF datasets-server resolves the actual parquet file URL for us.
_HF_RESOLVE = ("https://huggingface.co/api/datasets/hotpotqa/hotpot_qa/"
               "parquet/distractor/validation")


def _ctx():
    return ssl.create_default_context(cafile=certifi.where())


def _download_parquet():
    if PARQUET_PATH.exists():
        return PARQUET_PATH
    # 1) ask HF for the concrete parquet file URL(s)
    with urllib.request.urlopen(_HF_RESOLVE, timeout=60, context=_ctx()) as r:
        urls = json.loads(r.read())
    if not urls:
        raise RuntimeError("HF returned no parquet URLs for HotpotQA distractor/validation")
    print(f"downloading {urls[0]} ...")
    with urllib.request.urlopen(urls[0], timeout=600, context=_ctx()) as r:
        PARQUET_PATH.write_bytes(r.read())
    print(f"saved {PARQUET_PATH} ({PARQUET_PATH.stat().st_size//1024} KB)")
    return PARQUET_PATH


def _normalize_row(row) -> dict:
    """HF schema -> a flat example dict.

    HF stores context as {'title': [...], 'sentences': [[...], ...]} and
    supporting_facts as {'title': [...], 'sent_id': [...]}.
    """
    ctx = row["context"]
    paragraphs = [{"title": t, "sentences": list(s)}
                  for t, s in zip(ctx["title"], ctx["sentences"])]
    sf = row["supporting_facts"]
    gold_titles = sorted(set(sf["title"]))
    return {
        "id": row["id"],
        "question": row["question"],
        "answer": row["answer"],
        "type": row.get("type", ""),
        "level": row.get("level", ""),
        "paragraphs": paragraphs,
        "gold_titles": gold_titles,
    }


def ensure_jsonl():
    """Materialize a compact JSONL of normalized examples (one-time)."""
    if JSONL_PATH.exists():
        return JSONL_PATH
    import pandas as pd
    _download_parquet()
    df = pd.read_parquet(PARQUET_PATH)
    with JSONL_PATH.open("w") as f:
        for _, row in df.iterrows():
            f.write(json.dumps(_normalize_row(row), ensure_ascii=False) + "\n")
    print(f"wrote {JSONL_PATH}")
    return JSONL_PATH


def load(n: int | None = None, offset: int = 0) -> list[dict]:
    """Return n normalized examples starting at `offset` (all if n is None).
    offset enables held-out evaluation disjoint from the policy's training split."""
    ensure_jsonl()
    out = []
    with JSONL_PATH.open() as f:
        for i, line in enumerate(f):
            if i < offset:
                continue
            if n is not None and len(out) >= n:
                break
            out.append(json.loads(line))
    return out


if __name__ == "__main__":
    ex = load(2)
    print(f"loaded {len(ex)} examples")
    e = ex[0]
    print("Q:", e["question"])
    print("A:", e["answer"])
    print("gold titles:", e["gold_titles"])
    print("n paragraphs:", len(e["paragraphs"]))
