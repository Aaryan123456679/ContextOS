import statistics
from typing import List, Tuple, Any


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
        """Score chunks by cosine similarity already computed by Qdrant during retrieval.
        No local model — zero additional memory overhead."""
        if not chunks:
            return []
        raw = [c.embedding_score for c in chunks]
        normalized = normalize_scores(raw)
        return list(zip(chunks, normalized))
