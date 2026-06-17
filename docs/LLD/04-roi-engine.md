# ROI Engine — Detailed Design

## Purpose

Score each candidate chunk by expected answer quality gain per token. This is the core differentiator of ContextOS — not similarity scoring, but utility scoring.

## The Distinction

| Standard RAG | ContextOS ROI Engine |
|---|---|
| cosine_similarity(query_vec, chunk_vec) | ΔQuality(answer \| chunk) / tokens(chunk) |
| ranks by embedding closeness | ranks by expected answer improvement |
| includes "related" but useless chunks | includes only chunks that improve the answer |

## Implementation (MVP — V1)

Two-stage proxy for true ROI:

**Stage 1:** Embedding cosine similarity from Qdrant retrieval (free signal, already computed)

**Stage 2:** Cross-encoder reranking as quality proxy

```
ROI_proxy(chunk) = CrossEncoder(query, chunk.content)
                 normalized to [0, 1]
```

The cross-encoder captures semantic relevance at a much finer granularity than bi-encoder similarity. It reads the query and chunk together (not separately), so it understands context.

## Model

`cross-encoder/ms-marco-MiniLM-L-6-v2`
- Trained on MS-MARCO passage retrieval
- 22MB on disk
- CPU inference: ~2ms per pair
- 200 chunks × 2ms = ~400ms total (acceptable for Render free tier)

## Singleton Pattern (Memory Safety)

```python
_cross_encoder_instance = None

def get_cross_encoder():
    global _cross_encoder_instance
    if _cross_encoder_instance is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder_instance = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder_instance
```

Load once at first use. Never reload per request.

## Dynamic Threshold

Instead of a fixed cutoff, compute a dynamic threshold per request:

```python
def compute_threshold(scores: list[float]) -> float:
    mean = sum(scores) / len(scores)
    std = statistics.stdev(scores)
    return mean - 0.5 * std  # keep chunks within 0.5 std above mean
```

This adapts to different query difficulty levels.

## V2 — Trained Utility Scorer

Replace cross-encoder with a DistilBERT-class model trained on:
```
(query, chunk, answer_quality_with, answer_quality_without) tuples
```

Training data generated synthetically:
1. For each (query, chunk) pair, generate LLM answer with and without chunk
2. Use LLM judge to score both answers
3. Label: quality_delta = score_with - score_without

This gives true ROI scores, not a proxy.

## Output

```python
@dataclass
class ROIResult:
    scores: dict[UUID, float]   # chunk_id → roi_score ∈ [0, 1]
    threshold: float
    tokens_above_threshold: int
    tokens_below_threshold: int  # will be removed by budget allocator
    attribution: ROIAttribution
```

## Failure Mode

If CrossEncoder fails (OOM, import error): return uniform scores of 0.5 for all chunks. Pipeline continues with semantic similarity as the only signal (graceful degradation).
