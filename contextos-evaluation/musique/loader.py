"""MuSiQue (answerable) loader — 20-paragraph multi-hop distractor QA with
supporting-paragraph labels. A genuine many-candidate selection dataset."""
import io
import json
import ssl
import urllib.request
from pathlib import Path

import certifi

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
JSONL = DATA_DIR / "musique_validation.jsonl"
_URL = "https://huggingface.co/api/datasets/dgslibisey/MuSiQue/parquet/default/validation"


def _ctx():
    return ssl.create_default_context(cafile=certifi.where())


def ensure_jsonl():
    if JSONL.exists():
        return JSONL
    import pandas as pd
    u = json.load(urllib.request.urlopen(_URL, timeout=60, context=_ctx()))[0]
    print(f"downloading MuSiQue: {u} ...")
    data = urllib.request.urlopen(u, timeout=300, context=_ctx()).read()
    df = pd.read_parquet(io.BytesIO(data))
    n_written, n_skip = 0, 0
    with JSONL.open("w") as f:
        for _, r in df.iterrows():
            try:
                ans_ble = r["answerable"] if "answerable" in r else True
                if not bool(ans_ble):
                    continue
                paras = [{"title": str(p["title"]), "text": str(p["paragraph_text"]),
                          "is_supporting": bool(p["is_supporting"])} for p in r["paragraphs"]]
                aliases = r["answer_aliases"] if "answer_aliases" in r else None
                aliases = list(aliases) if aliases is not None and len(aliases) > 0 else []
                f.write(json.dumps({
                    "id": str(r["id"]), "question": str(r["question"]),
                    "answer": str(r["answer"]),
                    "answers": [str(r["answer"])] + [str(a) for a in aliases],
                    "paragraphs": paras,
                }, ensure_ascii=False) + "\n")
                n_written += 1
            except Exception:
                n_skip += 1
    print(f"  wrote {n_written} examples ({n_skip} skipped)")
    print(f"wrote {JSONL}")
    return JSONL


def load(n=None, offset=0):
    ensure_jsonl()
    out = []
    with JSONL.open() as f:
        for i, line in enumerate(f):
            if i < offset:
                continue
            if n is not None and len(out) >= n:
                break
            out.append(json.loads(line))
    return out


if __name__ == "__main__":
    ex = load(2)
    e = ex[0]
    print("Q:", e["question"], "| A:", e["answer"])
    print("paras:", len(e["paragraphs"]), "| supporting:",
          sum(p["is_supporting"] for p in e["paragraphs"]))
