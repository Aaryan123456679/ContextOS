"""MuSiQue example -> ContextOS pipeline inputs (one Chunk per paragraph)."""
import hashlib
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from models.schemas.chunk import Chunk  # noqa: E402


def _uuid(s: str) -> uuid.UUID:
    return uuid.UUID(hashlib.md5(s.encode()).hexdigest())


def _tok(text):
    import tiktoken
    return len(tiktoken.get_encoding("cl100k_base").encode(text))


def build(example: dict):
    """Return (candidates: list[Chunk], gold_chunk_ids: set, gold_answer: str)."""
    doc = _uuid(example["id"])
    candidates, gold = [], set()
    for i, p in enumerate(example["paragraphs"]):
        text = f"{p['title']}: {p['text']}".strip()
        cid = _uuid(f"{example['id']}:{i}")
        candidates.append(Chunk(id=cid, content=text, token_count=max(1, _tok(text)),
                                document_id=doc, metadata={"is_gold": p["is_supporting"]}))
        if p["is_supporting"]:
            gold.add(cid)
    return candidates, gold, example["answer"]
