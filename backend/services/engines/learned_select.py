"""
Learned selection policy (production) — the method validated in the evaluation suite.

A lightweight GradientBoosting classifier scores each candidate chunk's keep-probability
by fusing ALL engine signals (ROI, fusion, density, contradiction, dependency, query-concept
overlap, rank, position, size). Chunks are kept in descending keep-probability up to the
token budget — a learned drop-in for TokenBudgetAllocator.

In the eval (n=2000, HotpotQA+MuSiQue, matched reduction) this significantly beat both the
density allocator and SOTA LLMLingua-2 across the 55-85% reduction frontier. NOTE: the policy
was trained on Wikipedia multi-hop QA; on app documents the gain is plausible but unvalidated,
so this is gated behind a setting and falls back to density allocation on any error.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_FEATURES = None
_MODEL = None
_POLICY_PATH = Path(__file__).resolve().parent / "learned_policy.pkl"


def _load():
    global _MODEL, _FEATURES
    if _MODEL is None:
        import joblib
        pol = joblib.load(_POLICY_PATH)
        _MODEL, _FEATURES = pol["model"], pol["features"]
    return _MODEL, _FEATURES


def _concepts(text, concepts_fn):
    if concepts_fn is None:
        return set()
    try:
        return {c.lower() for c in concepts_fn(text) if c and len(c) > 2}
    except Exception:
        return set()


def _feature_rows(scored_chunks, query, chain_ids, concepts_fn):
    """Replicate the eval feature schema exactly (order set by the saved policy)."""
    qc = _concepts(query, concepts_fn)
    fusions = [sc.fusion_score for sc in scored_chunks]
    max_fus = max(fusions) if fusions else 1.0
    order = sorted(scored_chunks, key=lambda sc: sc.fusion_score, reverse=True)
    rank_of = {sc.chunk.id: r for r, sc in enumerate(order)}
    n = len(scored_chunks)
    rows = []
    for pos, sc in enumerate(scored_chunks):
        c = sc.chunk
        cov = _concepts(c.content, concepts_fn) & qc
        rows.append({
            "roi_score": float(sc.roi_score),
            "fusion_score": float(sc.fusion_score),
            "density": float(sc.fusion_score) / max(c.token_count, 1),
            "contradiction_risk": float(sc.contradiction_risk),
            "dependency_pruned": int(bool(sc.dependency_pruned)),
            "on_chain": int(c.id in (chain_ids or set())),
            "qconcept_overlap": len(cov),
            "qconcept_frac": len(cov) / max(len(qc), 1),
            "fusion_rel": (float(sc.fusion_score) / max_fus) if max_fus else 0.0,
            "rank_frac": rank_of[c.id] / max(n - 1, 1),
            "position_frac": pos / max(n - 1, 1),
            "token_count": c.token_count,
            "n_candidates": n,
        })
    return rows


class LearnedSelector:
    """Drop-in for TokenBudgetAllocator.allocate using the learned policy."""

    def select(self, scored_chunks, query, token_budget, chain_ids=None, concepts_fn=None):
        """Return selected ScoredChunks (keep-prob order) fitting token_budget; >=1 chunk.
        Falls back to fusion-density selection on any failure."""
        if not scored_chunks:
            return []
        try:
            import numpy as np
            model, feats = _load()
            rows = _feature_rows(scored_chunks, query, chain_ids, concepts_fn)
            X = np.array([[r[f] for f in feats] for r in rows], dtype=float)
            probs = model.predict_proba(X)[:, 1]
            ranked = sorted(zip(scored_chunks, probs), key=lambda t: t[1], reverse=True)
            return self._fill(ranked, token_budget)
        except Exception as e:  # never break a live request
            logger.warning("LearnedSelector fell back to density allocation: %s", e)
            ranked = sorted(((sc, sc.fusion_score / max(sc.chunk.token_count, 1))
                             for sc in scored_chunks), key=lambda t: t[1], reverse=True)
            return self._fill(ranked, token_budget)

    @staticmethod
    def _fill(ranked, token_budget):
        out, used = [], 0
        for sc, _ in ranked:
            if out and used + sc.chunk.token_count > token_budget:
                continue
            out.append(sc); used += sc.chunk.token_count
        return out or [ranked[0][0]]
