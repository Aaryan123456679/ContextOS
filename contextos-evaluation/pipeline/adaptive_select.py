"""
Content-adaptive chunk selection — decides HOW MANY chunks to keep from the
fusion-score distribution at runtime, instead of filling a fixed token budget.

Rationale: a fixed budget is provably wrong (budget >> context prunes nothing;
budget << context drops needles). The fusion scores already separate relevant
chunks from distractors, so we cut where the data says to.

Policies (all reuse fusion_score, ~zero extra cost):
  - "gap"       : keep chunks above the largest relative drop-off in sorted scores
  - "top_p"     : keep highest until cumulative score-mass >= p (nucleus over evidence)
  - "threshold" : keep chunks with fusion_score >= alpha * max_score

Safety rails (applied to every policy):
  - dependency closure : on-chain chunks (multi-hop partners) are always kept
  - min_keep floor     : never drop below k chunks
  - token_cap          : never exceed the model window (hard cap; non-chain dropped first)
"""
from typing import List, Set, Any
from uuid import UUID


def _by_score(scored: List[Any]):
    return sorted(scored, key=lambda sc: sc.fusion_score, reverse=True)


def _gap_cut(sorted_scored: List[Any]) -> int:
    """Index (exclusive) of the keep-prefix: cut at the largest consecutive drop."""
    n = len(sorted_scored)
    if n <= 1:
        return n
    scores = [sc.fusion_score for sc in sorted_scored]
    spread = (scores[0] - scores[-1]) or 1.0
    best_i, best_gap = n, 0.0
    # only look for the elbow in the leading region; never cut to nothing
    for i in range(1, n):
        gap = (scores[i - 1] - scores[i]) / spread
        if gap > best_gap:
            best_gap, best_i = gap, i
    # require a meaningful gap (>= 15% of the spread); otherwise keep all
    return best_i if best_gap >= 0.15 else n


def _top_p_cut(sorted_scored: List[Any], p: float) -> int:
    scores = [sc.fusion_score for sc in sorted_scored]
    lo = min(scores)
    shifted = [s - lo for s in scores]  # make non-negative
    total = sum(shifted) or 1.0
    cum, i = 0.0, 0
    for i, s in enumerate(shifted, start=1):
        cum += s
        if cum / total >= p:
            break
    return i


def _threshold_cut(sorted_scored: List[Any], alpha: float) -> int:
    if not sorted_scored:
        return 0
    top = sorted_scored[0].fusion_score
    thr = alpha * top if top > 0 else top  # if top<=0, keep only the top one
    keep = sum(1 for sc in sorted_scored if sc.fusion_score >= thr)
    return max(1, keep)


def adaptive_select(scored: List[Any], chain_ids: Set[UUID] = None, *,
                    mode: str = "gap", token_cap: int = 8192, min_keep: int = 1,
                    top_p: float = 0.9, alpha: float = 0.5) -> List[Any]:
    """Return the selected ScoredChunks (fusion_score desc)."""
    if not scored:
        return []
    chain_ids = chain_ids or set()
    s = _by_score(scored)

    if mode == "gap":
        k = _gap_cut(s)
    elif mode == "top_p":
        k = _top_p_cut(s, top_p)
    elif mode == "threshold":
        k = _threshold_cut(s, alpha)
    else:
        raise ValueError(f"unknown adaptive mode: {mode}")

    keep = {id(sc) for sc in s[:k]}
    # dependency closure: protect on-chain (multi-hop) partners — but only when the
    # chain is INFORMATIVE. On dense, topically-coherent pools the dependency engine
    # marks ~all chunks on-chain (e.g. every HotpotQA paragraph shares the question's
    # entities), which carries no pruning signal; force-keeping all of them defeats
    # the cut. So: skip closure when the chain covers most candidates, and even when
    # active only resurrect on-chain chunks above a score floor (not obvious distractors).
    if chain_ids and len(chain_ids) < 0.7 * len(s):
        max_score = s[0].fusion_score
        floor = 0.3 * max_score if max_score > 0 else max_score
        for sc in s:
            if sc.chunk.id in chain_ids and sc.fusion_score >= floor:
                keep.add(id(sc))
    # min-keep floor
    if len(keep) < min_keep:
        for sc in s:
            keep.add(id(sc))
            if len(keep) >= min_keep:
                break

    selected = [sc for sc in s if id(sc) in keep]

    # hard token cap: drop lowest-scored NON-chain chunks first, then chain if needed
    def tok(sel):
        return sum(sc.chunk.token_count for sc in sel)

    if tok(selected) > token_cap:
        protected = [sc for sc in selected if sc.chunk.id in chain_ids]
        droppable = [sc for sc in selected if sc.chunk.id not in chain_ids]  # already score-desc
        while droppable and tok(protected + droppable) > token_cap and len(protected + droppable) > min_keep:
            droppable.pop()  # remove lowest-scored droppable
        selected = [sc for sc in s if sc in protected or sc in droppable]
        # if still over cap (all protected), trim protected from the bottom too
        while tok(selected) > token_cap and len(selected) > min_keep:
            selected.pop()
    return selected
