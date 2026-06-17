"""Semantic similarity metrics: embedding cosine (fast) + BERTScore F1 (richer)."""
import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_bert = None


def embed_cosine(a: str, b: str) -> float:
    """Cosine similarity of two texts via the shared local sentence-transformer."""
    from pipeline.retrieval import _model
    if not a.strip() or not b.strip():
        return 0.0
    va, vb = _model().encode([a, b], normalize_embeddings=True, show_progress_bar=False)
    return float(np.dot(va, vb))


def bertscore_f1(candidate: str, reference: str) -> float:
    """BERTScore F1 of candidate vs reference answer (lazy import; heavy model)."""
    global _bert
    if not candidate.strip() or not reference.strip():
        return 0.0
    try:
        if _bert is None:
            from bert_score import BERTScorer
            # Lighter model than roberta-large to coexist with a local 8B LLM on 16GB RAM.
            _bert = BERTScorer(model_type="distilbert-base-uncased", num_layers=6,
                               rescale_with_baseline=False)
        _, _, f1 = _bert.score([candidate], [reference])
        return float(f1.mean())
    except Exception:
        # Fall back to embedding cosine if bert-score is unavailable.
        return embed_cosine(candidate, reference)
