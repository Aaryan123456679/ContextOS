import statistics
from typing import List, Tuple, Any

_cross_encoder = None


def get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder


def normalize_scores(scores: List[float]) -> List[float]:
    """Min-max normalize to [0, 1]. Uniform input returns all 0.5. Empty returns []."""
    if not scores:
        return []
    if len(scores) == 1:
        return [0.5]
    mn, mx = min(scores), max(scores)
    if mn == mx:
        return [0.5] * len(scores)
    return [(s - mn) / (mx - mn) for s in scores]


def compute_dynamic_threshold(scores: List[float]) -> float:
    """Threshold = mean - 0.5 * std, floored at 0.0."""
    if not scores:
        return 0.0
    mean = statistics.mean(scores)
    std = statistics.stdev(scores) if len(scores) > 1 else 0.0
    return max(0.0, mean - 0.5 * std)


class ROIEngine:
    def score(self, query: str, chunks: List[Any]) -> List[Tuple[Any, float]]:
        """Return [(chunk, normalized_score), ...] for each chunk. Gracefully degrades on error."""
        if not chunks:
            return []
        try:
            encoder = get_cross_encoder()
            pairs = [(query, c.content) for c in chunks]
            raw_scores = list(encoder.predict(pairs))
            normalized = normalize_scores(raw_scores)
            return list(zip(chunks, normalized))
        except Exception:
            return [(c, 0.5) for c in chunks]
