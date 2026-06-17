"""
ContextOS optimization pipeline wrapper with per-engine ablation toggles.

Mirrors backend/api/routes/chat.py orchestration (ROI → dependency → contradiction
→ fusion → token-budget → compression) but lets each engine be switched on/off so
the ablation study can measure each engine's contribution. Compression runs
through the local Ollama provider.
"""
import time
from types import SimpleNamespace

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

from services.engines.roi_engine import ROIEngine
from services.engines.dependency_graph import DependencyGraphBuilder
from services.engines.contradiction import ContradictionDetector
from services.engines.fusion import FusionEngine
from services.engines.token_budget import TokenBudgetAllocator
from services.engines.compression import RecoverableCompressor
from pipeline.adaptive_select import adaptive_select
from pipeline.coverage_select import coverage_select

_roi = ROIEngine()
_dep = DependencyGraphBuilder()
_contra = ContradictionDetector()
_fusion = FusionEngine()
_alloc = TokenBudgetAllocator()

ALL_ENGINES = ["roi", "dependency", "contradiction", "compression"]
FULL = {e: True for e in ALL_ENGINES}
NONE = {e: False for e in ALL_ENGINES}


def _concepts(text: str) -> set:
    """Salient query/chunk concepts (entities + noun phrases) for coverage selection.
    Reuses the dependency engine's extractor so there's no new dependency."""
    try:
        return {c.lower() for c in _dep._extract_concepts(text) if c and len(c) > 2}
    except Exception:
        return set()


class _OllamaGateway:
    """Adapter so RecoverableCompressor can call Ollama via its gateway interface."""
    def __init__(self, provider):
        self.provider = provider

    async def complete_with_fallback(self, prompt, models, api_key, **kw):
        import asyncio
        r = await asyncio.to_thread(self.provider.complete, prompt, None, 1024, 0.0)
        return SimpleNamespace(content=r.text, model=r.model,
                               usage=SimpleNamespace(prompt_tokens=r.prompt_tokens,
                                                     completion_tokens=r.completion_tokens))

    async def complete(self, prompt, model=None, api_key=None, **kw):
        return await self.complete_with_fallback(prompt, [model], api_key)


def _tokens(text: str) -> int:
    import tiktoken
    return len(tiktoken.get_encoding("cl100k_base").encode(text))


async def _score_all(candidates, query, engine_set):
    """Run ROI -> dependency -> contradiction -> fusion and return the full scored
    list plus chain ids (no selection, no LLM). Shared by run() and feature export."""
    es = {**NONE, **(engine_set or {})}
    if es["roi"]:
        roi_by_id = {c.id: s for c, s in _roi.score(query, candidates)}
    else:
        roi_by_id = {c.id: 0.5 for c in candidates}
    roi_scores = [roi_by_id.get(c.id, 0.5) for c in candidates]
    dep_mask, dep_boost = {}, set()
    if es["dependency"]:
        try:
            dg = await _dep.build(query, candidates)
            dep_mask, dep_boost = dg.pruning_mask, dg.chain_chunk_ids
        except Exception:
            pass
    contra_flags = []
    if es["contradiction"]:
        try:
            contra_flags = await _contra.detect(candidates)
        except Exception:
            contra_flags = []
    scored = _fusion.fuse(candidates, roi_scores, dep_mask, contra_flags, dep_boost)
    return scored, dep_boost, roi_by_id


def _feature_rows(scored, candidates, chain_ids, query):
    """Build per-chunk feature dicts from already-computed scored chunks (no recompute)."""
    qc = _concepts(query)
    by_id = {sc.chunk.id: sc for sc in scored}
    fusions = [sc.fusion_score for sc in scored]
    max_fus = max(fusions) if fusions else 1.0
    order = sorted(scored, key=lambda sc: sc.fusion_score, reverse=True)
    rank_of = {sc.chunk.id: r for r, sc in enumerate(order)}
    n = len(candidates)
    rows = []
    for pos, c in enumerate(candidates):
        sc = by_id.get(c.id)
        if sc is None:
            continue
        cov = _concepts(c.content) & qc
        rows.append({
            "chunk_id": str(c.id),
            "roi_score": round(float(sc.roi_score), 5),
            "fusion_score": round(float(sc.fusion_score), 5),
            "density": round(float(sc.fusion_score) / max(c.token_count, 1), 6),
            "contradiction_risk": round(float(sc.contradiction_risk), 5),
            "dependency_pruned": int(bool(sc.dependency_pruned)),
            "on_chain": int(c.id in chain_ids),
            "qconcept_overlap": len(cov),
            "qconcept_frac": round(len(cov) / max(len(qc), 1), 4),
            "fusion_rel": round(float(sc.fusion_score) / max_fus, 4) if max_fus else 0.0,
            "rank_frac": round(rank_of[c.id] / max(n - 1, 1), 4),
            "position_frac": round(pos / max(n - 1, 1), 4),
            "token_count": c.token_count,
            "n_candidates": n,
        })
    return rows


async def chunk_features(candidates, query, engine_set):
    """Per-chunk feature rows fusing ALL engine signals — input to a learned policy.
    No LLM; deterministic."""
    scored, chain_ids, _ = await _score_all(candidates, query, engine_set)
    return _feature_rows(scored, candidates, chain_ids, query)


FEATURE_COLS = ["roi_score", "fusion_score", "density", "contradiction_risk",
                "dependency_pruned", "on_chain", "qconcept_overlap", "qconcept_frac",
                "fusion_rel", "rank_frac", "position_frac", "token_count", "n_candidates"]

_POLICY = None


def _load_policy(path=None):
    global _POLICY
    if _POLICY is None:
        import joblib
        path = path or (config.EVAL_ROOT / "learned" / "policy.pkl")
        _POLICY = joblib.load(path)
    return _POLICY


def _gap_k(vals):
    """Number of leading items to keep, cut at the largest relative drop (>=15% of spread).
    Returns len(vals) when flat (no clear cut)."""
    n = len(vals)
    if n <= 1:
        return n
    spread = (vals[0] - vals[-1]) or 1.0
    best_i, best = n, 0.0
    for i in range(1, n):
        g = (vals[i - 1] - vals[i]) / spread
        if g > best:
            best, best_i = g, i
    return best_i if best >= 0.15 else n


def _learned_select(scored, candidates, chain_ids, query, threshold, token_cap):
    """Select with the learned policy. `threshold` is a float (static alpha) OR
    "auto"/"dynamic" -> per-instance cutoff at the largest gap in the policy's
    predicted keep-probabilities. Always keeps >=1; respects the token cap."""
    import numpy as np
    rows = _feature_rows(scored, candidates, chain_ids, query)
    pol = _load_policy()
    X = np.array([[r[c] for c in pol["features"]] for r in rows], dtype=float)
    probs = pol["model"].predict_proba(X)[:, 1]
    prob_by_id = {rows[i]["chunk_id"]: float(probs[i]) for i in range(len(rows))}
    ordered = sorted(scored, key=lambda sc: prob_by_id.get(str(sc.chunk.id), 0.0), reverse=True)

    if threshold in (None, "auto", "dynamic"):
        sorted_probs = [prob_by_id.get(str(sc.chunk.id), 0.0) for sc in ordered]
        k = _gap_k(sorted_probs)
        keep = ordered[:max(1, k)]
    else:
        keep = [sc for sc in ordered if prob_by_id.get(str(sc.chunk.id), 0.0) >= float(threshold)]
        if not keep:
            keep = ordered[:1]
    out, used = [], 0
    for sc in keep:
        if out and used + sc.chunk.token_count > token_cap:
            continue
        out.append(sc); used += sc.chunk.token_count
    return out


async def run(candidates, query, budget, engine_set, llm_provider=None,
              select_mode="fixed", select_params=None):
    """Run the (possibly ablated) pipeline over candidate chunks.

    select_mode: "fixed" uses the token-budget allocator (budget = target).
      "gap" | "top_p" | "threshold" use the content-adaptive selector
      (budget = hard token cap; the policy decides how many chunks to keep).
    select_params: optional dict {min_keep, top_p, alpha} for adaptive modes.

    Returns dict: optimized_context, optimized_tokens, selected_chunk_ids,
    engines_used, select_mode, timings_ms, compression_ratio, n_candidates, n_selected.
    """
    es = {**NONE, **(engine_set or {})}
    timings = {}
    used = []

    # ROI
    if es["roi"]:
        t = time.perf_counter()
        roi_by_id = {c.id: s for c, s in _roi.score(query, candidates)}
        timings["roi"] = (time.perf_counter() - t) * 1000
        used.append("roi")
    else:
        roi_by_id = {c.id: 0.5 for c in candidates}
    roi_scores = [roi_by_id.get(c.id, 0.5) for c in candidates]

    # Dependency graph
    dep_mask, dep_boost = {}, set()
    if es["dependency"]:
        t = time.perf_counter()
        try:
            dg = await _dep.build(query, candidates)
            dep_mask, dep_boost = dg.pruning_mask, dg.chain_chunk_ids
        except Exception:
            pass
        timings["dependency"] = (time.perf_counter() - t) * 1000
        used.append("dependency")

    # Contradiction
    contra_flags = []
    if es["contradiction"]:
        t = time.perf_counter()
        try:
            contra_flags = await _contra.detect(candidates)
        except Exception:
            contra_flags = []
        timings["contradiction"] = (time.perf_counter() - t) * 1000
        used.append("contradiction")

    # Fusion + token budget (always — this is the selection mechanism)
    t = time.perf_counter()
    scored = _fusion.fuse(candidates, roi_scores, dep_mask, contra_flags, dep_boost)
    if select_mode == "fixed":
        selected = _alloc.allocate(scored, budget).selected
    elif select_mode == "coverage":
        qc = _concepts(query)
        _cc_cache = {}

        def _chunk_concepts(chunk):
            if chunk.id not in _cc_cache:
                _cc_cache[chunk.id] = _concepts(chunk.content)
            return _cc_cache[chunk.id]

        selected = coverage_select(scored, qc, _chunk_concepts, token_cap=budget)
    elif select_mode == "learned":
        sp = select_params or {}
        selected = _learned_select(scored, candidates, dep_boost, query,
                                   threshold=sp.get("threshold", 0.5), token_cap=budget)
    else:
        sp = select_params or {}
        selected = adaptive_select(
            scored, chain_ids=dep_boost, mode=select_mode, token_cap=budget,
            min_keep=sp.get("min_keep", 1), top_p=sp.get("top_p", 0.9),
            alpha=sp.get("alpha", 0.5))
    selected_chunks = [sc.chunk for sc in selected]
    timings["fusion_budget"] = (time.perf_counter() - t) * 1000

    selected_text = "\n\n".join(c.content for c in selected_chunks)
    pre_comp_tokens = sum(c.token_count for c in selected_chunks)

    # Compression (optional, via Ollama)
    optimized_context = selected_text
    if es["compression"] and llm_provider and selected_chunks:
        t = time.perf_counter()
        try:
            comp = RecoverableCompressor(_OllamaGateway(llm_provider))
            res = await comp.compress(selected_chunks, query, api_key="ollama",
                                      model=llm_provider.model)
            if res.compressed_text and res.compressed_text.strip():
                optimized_context = res.compressed_text
        except Exception:
            pass
        timings["compression"] = (time.perf_counter() - t) * 1000
        used.append("compression")

    opt_tokens = _tokens(optimized_context)
    ratio = (opt_tokens / pre_comp_tokens) if pre_comp_tokens else 1.0

    return {
        "optimized_context": optimized_context,
        "optimized_tokens": opt_tokens,
        "selected_chunk_ids": {c.id for c in selected_chunks},
        "engines_used": used,
        "select_mode": select_mode,
        "timings_ms": timings,
        "opt_pipeline_ms": sum(timings.values()),
        "compression_ratio": round(ratio, 4),
        "n_candidates": len(candidates),
        "n_selected": len(selected_chunks),
    }
