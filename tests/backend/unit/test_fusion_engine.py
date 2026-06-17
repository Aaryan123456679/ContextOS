"""Unit tests for Fusion Engine — scoring formula correctness."""
import pytest
from dataclasses import dataclass
from uuid import uuid4


@dataclass
class MockSignals:
    roi_score: float
    dependency_pruned: bool
    contradiction_risk: float
    source_reliability: float = 0.5


class TestFusionEngine:
    def test_score_in_zero_to_one_range(self):
        """Fusion score always stays in [0, 1]."""
        from services.engines.fusion import FusionEngine
        engine = FusionEngine()

        # Extreme high signals
        score = engine.score(None, MockSignals(
            roi_score=1.0, dependency_pruned=False,
            contradiction_risk=0.0, source_reliability=1.0
        ))
        assert 0.0 <= score <= 1.0

        # Extreme low signals
        score = engine.score(None, MockSignals(
            roi_score=0.0, dependency_pruned=True,
            contradiction_risk=1.0, source_reliability=0.0
        ))
        assert 0.0 <= score <= 1.0

    def test_dependency_pruned_reduces_score(self):
        """Pruned chunk scores lower than identical non-pruned chunk."""
        from services.engines.fusion import FusionEngine
        engine = FusionEngine()

        base = MockSignals(roi_score=0.8, dependency_pruned=False,
                           contradiction_risk=0.1, source_reliability=0.5)
        pruned = MockSignals(roi_score=0.8, dependency_pruned=True,
                             contradiction_risk=0.1, source_reliability=0.5)

        score_base = engine.score(None, base)
        score_pruned = engine.score(None, pruned)
        assert score_pruned < score_base

    def test_high_contradiction_risk_reduces_score(self):
        """High contradiction risk produces lower score."""
        from services.engines.fusion import FusionEngine
        engine = FusionEngine()

        low_contra = MockSignals(roi_score=0.8, dependency_pruned=False,
                                 contradiction_risk=0.0, source_reliability=0.5)
        high_contra = MockSignals(roi_score=0.8, dependency_pruned=False,
                                  contradiction_risk=1.0, source_reliability=0.5)

        assert engine.score(None, low_contra) > engine.score(None, high_contra)

    def test_weights_sum_direction_correct(self):
        """A chunk with perfect signals scores higher than a chunk with worst signals."""
        from services.engines.fusion import FusionEngine
        engine = FusionEngine()

        best = MockSignals(roi_score=1.0, dependency_pruned=False,
                           contradiction_risk=0.0, source_reliability=1.0)
        worst = MockSignals(roi_score=0.0, dependency_pruned=True,
                            contradiction_risk=1.0, source_reliability=0.0)

        assert engine.score(None, best) > engine.score(None, worst)
