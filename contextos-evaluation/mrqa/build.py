"""MRQA example -> ContextOS pipeline inputs (chunk the context into a candidate pool)."""
import hashlib
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from models.schemas.chunk import Chunk  # noqa: E402
from scenarios.chunker import chunk_text  # noqa: E402
from hotpotqa.em_f1 import normalize_answer  # noqa: E402


def _uuid(s: str) -> uuid.UUID:
    return uuid.UUID(hashlib.md5(s.encode()).hexdigest())


def build(example: dict):
    """Return (candidates: list[Chunk], gold_chunk_ids: set, gold_answer: str).

    gold_chunk_ids = chunks whose normalized text contains a gold answer string
    (a generic 'answer-bearing chunk' recall proxy; MRQA has no supporting-chunk
    annotation that survives re-chunking).
    """
    raw = chunk_text(example["context"])
    doc = _uuid(example["id"])
    answers_norm = [a for a in (normalize_answer(x) for x in example["answers"]) if a]
    candidates, gold_ids = [], set()
    for ch in raw:
        cid = _uuid(f"{example['id']}:{ch['chunk_index']}")
        ck = Chunk(id=cid, content=ch["content"], token_count=ch["token_count"],
                   document_id=doc, metadata={"subset": example["subset"]})
        candidates.append(ck)
        cn = normalize_answer(ck.content)
        if any(a in cn for a in answers_norm):
            gold_ids.add(cid)
    return candidates, gold_ids, example["gold_answer"]
