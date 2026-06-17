from pydantic import BaseModel
from typing import List, Dict, Set
from uuid import UUID
from models.schemas.chunk import Chunk, ScoredChunk

class ChunkSignals(BaseModel):
    roi_score: float
    dependency_pruned: bool
    contradiction_risk: float
    source_reliability: float = 0.5   # default neutral
    dependency_relevant: bool = False  # on the dependency chain to the answer

class FusionEngine:
    WEIGHTS = {
        "roi": 0.35,
        "dependency_redundancy": -0.20,   # negative: redundancy penalizes
        "dependency_relevance": 0.25,      # positive: keep on-chain chunks together
        "contradiction_risk": -0.20,       # negative
        "source_reliability": 0.15,
        "recency": 0.10,
    }
    def score(self, chunk, signals) -> float:
        return self.score_chunk(chunk, signals)

    def score_chunk(self, chunk, signals) -> float:
        """
        Utility(chunk) =
          α·roi + β·dependency_redundancy + ε·dependency_relevance
          + γ·source_reliability + δ·contradiction_risk
        (Weights contain the sign, so we just add them)
        """
        score = (
            self.WEIGHTS["roi"] * signals.roi_score
            + self.WEIGHTS["dependency_redundancy"] * (1.0 if signals.dependency_pruned else 0.0)
            + self.WEIGHTS["dependency_relevance"] * (1.0 if signals.dependency_relevant else 0.0)
            + self.WEIGHTS["contradiction_risk"] * signals.contradiction_risk
            + self.WEIGHTS["source_reliability"] * signals.source_reliability
        )
        # Clip to [0.0, 1.0]
        return max(0.0, min(1.0, score))

    def fuse(
        self,
        chunks: List[Chunk],
        roi_scores: List[float],
        dependency_mask: Dict[UUID, bool],
        contradiction_flags: List,
        dependency_boost_ids: Set[UUID] = None,
    ) -> List[ScoredChunk]:
        scored_chunks = []
        dependency_boost_ids = dependency_boost_ids or set()

        # Resolve contradictions: when the detector picked a winner (e.g. the newer
        # fact), spare the winner and penalize the loser; otherwise (surface_both)
        # apply the risk to both sides.
        contra_risk: Dict[UUID, float] = {}
        winners: Set[UUID] = set()
        losers: Set[UUID] = set()
        for flag in contradiction_flags:
            a, b, conf = flag.chunk_a_id, flag.chunk_b_id, flag.confidence
            keep = getattr(flag, "keep_chunk_id", None)
            if keep is not None:
                loser = b if keep == a else a
                winners.add(keep)
                losers.add(loser)
                contra_risk[loser] = max(contra_risk.get(loser, 0.0), conf)
            else:
                contra_risk[a] = max(contra_risk.get(a, 0.0), conf)
                contra_risk[b] = max(contra_risk.get(b, 0.0), conf)
        # A resolved winner carries no contradiction penalty.
        for w in winners:
            contra_risk[w] = 0.0

        for idx, chunk in enumerate(chunks):
            # A definitively-resolved contradiction loser (a superseded/older fact)
            # is removed outright — keeping it would risk feeding the model a known
            # wrong fact, and merely down-weighting it isn't enough when distractors
            # are also penalized to ~0.
            if chunk.id in losers:
                continue

            roi = roi_scores[idx] if idx < len(roi_scores) else 0.5
            pruned = dependency_mask.get(chunk.id, False)
            risk = 0.0 if chunk.id in winners else contra_risk.get(chunk.id, 0.0)

            signals = ChunkSignals(
                roi_score=roi,
                dependency_pruned=pruned,
                contradiction_risk=risk,
                source_reliability=0.5,
                dependency_relevant=chunk.id in dependency_boost_ids,
            )

            fscore = self.score_chunk(chunk, signals)

            scored_chunks.append(ScoredChunk(
                chunk=chunk,
                roi_score=roi,
                dependency_pruned=pruned,
                contradiction_risk=risk,
                fusion_score=fscore,
                allocated=False
            ))

        return scored_chunks
