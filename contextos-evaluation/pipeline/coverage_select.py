"""
Coverage-driven selection (recall-safe) — a dataset-agnostic selector.

Instead of "keep N chunks" (hop-count overfit), "fit a token budget" (context-size
overfit), or "score >= alpha*max" (score-scale overfit), this keeps the smallest
*relevance prefix* that both (a) covers the query's information need and (b) spans
the clearly-relevant cluster.

Why the two-part rule (the recall-safe fix): pure concept-coverage stops the instant
the query's concepts are nominally covered — but the answer-bearing chunk often does
NOT add a *new* query concept (it shares ones already covered), so coverage would
stop just before it and tank recall. So we take the deeper of two budget-free signals:

  - coverage depth : how far down the ranking we must go to cover all query concepts
  - relevance-gap depth : the leading cluster of chunks before the first big score drop

We keep the FULL prefix to max(coverage_depth, gap_depth) — re-including high-relevance
chunks coverage skipped. Single-fact query -> ~1 chunk; multi-hop -> the covering span;
flat/ambiguous scores -> stay conservative (keep more) rather than prune blindly.
The only hard number is a physical token cap.
"""
from typing import List, Set, Callable, Any
from pipeline.adaptive_select import _gap_cut


def coverage_select(scored: List[Any], query_concepts: Set[str],
                    chunk_concepts_fn: Callable[[Any], Set[str]], *,
                    token_cap: int = 8192) -> List[Any]:
    """Return selected ScoredChunks (relevance order)."""
    if not scored:
        return []
    s = sorted(scored, key=lambda sc: sc.fusion_score, reverse=True)
    qc = set(query_concepts or set())

    # (1) coverage depth: rank by which all query concepts are covered
    covered: Set[str] = set()
    cov_depth = 1
    for i, sc in enumerate(s):
        cc = chunk_concepts_fn(sc.chunk) & qc if qc else set()
        if i == 0 or (cc - covered):
            covered |= cc
            cov_depth = i + 1
            if qc and covered >= qc:
                break

    # (2) relevance-gap depth: leading cluster before the first large score drop
    #     (returns len(s) when scores are flat -> stay conservative)
    gap_depth = _gap_cut(s)

    # keep the deeper prefix (recall-safe), then enforce the physical token cap
    keep_depth = max(cov_depth, gap_depth)
    selected = s[:keep_depth]
    while len(selected) > 1 and sum(sc.chunk.token_count for sc in selected) > token_cap:
        selected.pop()
    return selected
