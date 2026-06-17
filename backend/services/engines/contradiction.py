import re
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from models.schemas.chunk import Chunk

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "of", "to", "and",
    "or", "for", "with", "its", "it", "as", "by", "that", "this", "where", "which",
    "has", "have", "had", "from", "main", "new",
}


def _content_words(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS and len(w) > 1}


def _topically_related(a: str, b: str, min_jaccard: float = 0.18) -> bool:
    """A real contradiction requires the two statements to be about the same thing.
    NLI alone labels many *unrelated* sentence pairs as 'contradiction', so we gate
    on content-word overlap first."""
    wa, wb = _content_words(a), _content_words(b)
    if not wa or not wb:
        return False
    return len(wa & wb) / len(wa | wb) >= min_jaccard

class ContradictionFlag(BaseModel):
    chunk_a_id: UUID
    chunk_b_id: UUID
    confidence: float
    resolution: str      # "keep_a" | "keep_b" | "surface_both"
    keep_chunk_id: Optional[UUID] = None

_nli_model = None

def get_nli_model():
    global _nli_model
    if _nli_model is None:
        from sentence_transformers import CrossEncoder
        # Lazy load the NLI model (num_labels=3: contradiction, neutral, entailment)
        _nli_model = CrossEncoder("cross-encoder/nli-deberta-v3-small", num_labels=3)
    return _nli_model

class ContradictionDetector:
    CONTRADICTION_THRESHOLD = 0.55

    async def detect(self, chunks: List[Chunk]) -> List[ContradictionFlag]:
        candidates = chunks[:20]  # Cap to top-20 pairwise
        flags = []
        
        if not candidates or len(candidates) < 2:
            return flags

        nli_model = get_nli_model()

        # Build list of pairs to predict — only topically-related pairs, so NLI
        # can't raise false-positive "contradictions" between unrelated chunks.
        pairs = []
        pairs_indices = []
        for i, c1 in enumerate(candidates):
            for j in range(i + 1, len(candidates)):
                c2 = candidates[j]
                if not _topically_related(c1.content, c2.content):
                    continue
                pairs.append((c1.content[:512], c2.content[:512]))
                pairs_indices.append((c1, c2))

        if not pairs:
            return flags

        # Batch prediction
        predictions = nli_model.predict(pairs)

        for idx, pred in enumerate(predictions):
            # Label 0 is usually contradiction in standard NLI deberta
            # Let's check probability/score of contradiction label
            # pred can be logits or probabilities depending on model config.
            # Let's map via softmax if logits, or just index [0]
            # Deberta v3 small contradiction is index 0
            import numpy as np
            # Softmax
            exp_pred = np.exp(pred)
            probs = exp_pred / np.sum(exp_pred)
            contra_prob = float(probs[0])

            if contra_prob > self.CONTRADICTION_THRESHOLD:
                c1, c2 = pairs_indices[idx]
                keep_id, res_str = self._resolve(c1, c2)
                flags.append(ContradictionFlag(
                    chunk_a_id=c1.id,
                    chunk_b_id=c2.id,
                    confidence=contra_prob,
                    resolution=res_str,
                    keep_chunk_id=keep_id
                ))

        return flags

    def _resolve(self, c1: Chunk, c2: Chunk) -> tuple[Optional[UUID], str]:
        # Resolution priority:
        # 1. More recent (if timestamps in metadata)
        # 2. Surface both if tie
        ts1 = c1.metadata.get("created_at") or c1.metadata.get("timestamp")
        ts2 = c2.metadata.get("created_at") or c2.metadata.get("timestamp")
        
        if ts1 and ts2:
            if ts1 > ts2:
                return c1.id, "keep_a"
            elif ts2 > ts1:
                return c2.id, "keep_b"
        
        return None, "surface_both"
