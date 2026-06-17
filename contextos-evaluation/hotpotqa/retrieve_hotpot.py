"""
Turn a HotpotQA example into ContextOS pipeline inputs.

The distractor setting already provides the candidate pool (10 paragraphs), so
no corpus store / embedding retrieval is needed — we wrap each paragraph as a
backend `Chunk` and mark the gold (supporting) paragraphs. The optimizer then
decides which to keep, exactly as in the main eval.
"""
import hashlib
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402  (path shim -> backend importable)
from models.schemas.chunk import Chunk  # noqa: E402

_enc = None


def _tok(text: str) -> int:
    global _enc
    if _enc is None:
        import tiktoken
        _enc = tiktoken.get_encoding("cl100k_base")
    return len(_enc.encode(text))


def _uuid_for(s: str) -> uuid.UUID:
    return uuid.UUID(hashlib.md5(s.encode()).hexdigest())


def build(example: dict):
    """Return (candidates: list[Chunk], gold_chunk_ids: set, gold_answer: str).

    One Chunk per paragraph. content = "Title: <para text>" so the title (the unit
    HotpotQA's supporting_facts reference) stays attached to its evidence.
    """
    gold_titles = set(example["gold_titles"])
    candidates, gold_ids = [], set()
    doc_uuid = _uuid_for(example["id"])
    for i, p in enumerate(example["paragraphs"]):
        text = f"{p['title']}: " + " ".join(p["sentences"]).strip()
        cid = _uuid_for(f"{example['id']}:{i}")
        ck = Chunk(id=cid, content=text, token_count=max(1, _tok(text)),
                   document_id=doc_uuid,
                   metadata={"source": p["title"], "is_gold": p["title"] in gold_titles})
        candidates.append(ck)
        if p["title"] in gold_titles:
            gold_ids.add(cid)
    return candidates, gold_ids, example["answer"]
