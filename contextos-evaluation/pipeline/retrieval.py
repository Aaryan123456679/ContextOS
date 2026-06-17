"""
Local, in-memory retrieval over a scenario's document set.

Chunks each document (production chunker), embeds chunks with a LOCAL
sentence-transformer (no API, no cloud vector store), and returns the top-K
candidate chunks for the query as backend `Chunk` objects. Per-document chunk
embeddings are cached in-memory and reused across scenarios for speed.
"""
import hashlib
import uuid
from functools import lru_cache

import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from corpus.store import CorpusStore
from scenarios.chunker import chunk_text
from models.schemas.chunk import Chunk  # backend schema

_EMB_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_emb_model = None
_store = None
_doc_cache = {}  # source_id -> (list[Chunk], np.ndarray embeddings)


def _model():
    global _emb_model
    if _emb_model is None:
        from sentence_transformers import SentenceTransformer
        _emb_model = SentenceTransformer(_EMB_MODEL_NAME)
    return _emb_model


def _corpus():
    global _store
    if _store is None:
        _store = CorpusStore()
    return _store


def _uuid_for(s: str) -> uuid.UUID:
    return uuid.UUID(hashlib.md5(s.encode()).hexdigest())


def _doc_chunks(source_id: str, created_at: str = None):
    """Chunk + embed a document once; cache the result."""
    if source_id in _doc_cache:
        return _doc_cache[source_id]
    text = _corpus().get_text(source_id)
    raw = chunk_text(text)
    doc_uuid = _uuid_for(source_id)
    chunks = []
    for ch in raw:
        meta = {"source": source_id}
        if created_at:
            meta["created_at"] = created_at
        chunks.append(Chunk(
            id=_uuid_for(f"{source_id}:{ch['chunk_index']}"),
            content=ch["content"], token_count=ch["token_count"],
            document_id=doc_uuid, metadata=meta,
        ))
    if chunks:
        embs = _model().encode([c.content for c in chunks], normalize_embeddings=True,
                               show_progress_bar=False)
        embs = np.asarray(embs, dtype=np.float32)
    else:
        embs = np.zeros((0, 384), dtype=np.float32)
    _doc_cache[source_id] = (chunks, embs)
    return chunks, embs


def retrieve(scenario: dict, top_k: int = 40):
    """Return (candidate_chunks, gold_chunk_ids) for a scenario's query."""
    all_chunks, all_embs = [], []
    gold_ids = set(scenario.get("gold_doc_ids", []))
    gold_chunk_ids = set()

    for sid in scenario["doc_ids"]:
        chunks, embs = _doc_chunks(sid)
        all_chunks.extend(chunks)
        all_embs.append(embs)
        if sid in gold_ids:
            gold_chunk_ids.update(c.id for c in chunks)

    # Inject a controlled contradiction chunk if the scenario calls for it.
    inject = scenario.get("contradiction_inject")
    if inject:
        cid = _uuid_for(f"{scenario['run_id']}:inject")
        ck = Chunk(id=cid, content=inject, token_count=max(1, len(inject) // 4),
                   document_id=_uuid_for("inject"), metadata={"source": "injected_contradiction"})
        all_chunks.append(ck)
        e = _model().encode([inject], normalize_embeddings=True, show_progress_bar=False)
        all_embs.append(np.asarray(e, dtype=np.float32))

    if not all_chunks:
        return [], gold_chunk_ids
    embs = np.vstack(all_embs)
    qv = _model().encode([scenario["query"]], normalize_embeddings=True, show_progress_bar=False)[0]
    scores = embs @ np.asarray(qv, dtype=np.float32)
    order = np.argsort(-scores)[:top_k]
    candidates = [all_chunks[i] for i in order]
    return candidates, gold_chunk_ids
