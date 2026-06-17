"""Unit tests for ROI Engine — no external service calls."""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4


class MockChunk:
    def __init__(self, content: str, token_count: int = 100):
        self.id = uuid4()
        self.content = content
        self.token_count = token_count


class TestROIEngineNormalization:
    def test_normalize_uniform_scores(self):
        """Uniform input scores → all 0.5 after min-max normalization."""
        from services.engines.roi_engine import normalize_scores
        scores = [0.8, 0.8, 0.8]
        result = normalize_scores(scores)
        assert all(s == 0.5 for s in result)

    def test_normalize_spread_scores(self):
        """Min score → 0.0, max score → 1.0."""
        from services.engines.roi_engine import normalize_scores
        scores = [0.2, 0.5, 0.8]
        result = normalize_scores(scores)
        assert result[0] == pytest.approx(0.0)
        assert result[2] == pytest.approx(1.0)
        assert 0.0 < result[1] < 1.0

    def test_normalize_single_score(self):
        """Single score → 0.5 (edge case)."""
        from services.engines.roi_engine import normalize_scores
        result = normalize_scores([0.7])
        assert result[0] == 0.5

    def test_normalize_empty(self):
        """Empty input → empty output."""
        from services.engines.roi_engine import normalize_scores
        assert normalize_scores([]) == []


class TestDynamicThreshold:
    def test_threshold_typical_distribution(self):
        """Threshold = mean - 0.5 * std for typical score distribution."""
        from services.engines.roi_engine import compute_dynamic_threshold
        import statistics
        scores = [0.3, 0.5, 0.6, 0.7, 0.9]
        mean = statistics.mean(scores)
        std = statistics.stdev(scores)
        expected = mean - 0.5 * std
        assert compute_dynamic_threshold(scores) == pytest.approx(expected)

    def test_threshold_minimum_is_zero(self):
        """Threshold never goes below 0.0."""
        from services.engines.roi_engine import compute_dynamic_threshold
        scores = [0.01, 0.02, 0.01]  # very low scores, std would make threshold negative
        assert compute_dynamic_threshold(scores) >= 0.0


class TestROIEngineMocked:
    @patch("services.engines.roi_engine.get_cross_encoder")
    def test_score_returns_one_result_per_chunk(self, mock_get_encoder):
        """Score method returns exactly len(chunks) results."""
        mock_encoder = MagicMock()
        mock_encoder.predict.return_value = [0.5, 0.8, 0.3]
        mock_get_encoder.return_value = mock_encoder

        from services.engines.roi_engine import ROIEngine
        engine = ROIEngine()
        chunks = [MockChunk(f"content {i}") for i in range(3)]
        results = engine.score("test query", chunks)

        assert len(results) == 3

    @patch("services.engines.roi_engine.get_cross_encoder")
    def test_score_returns_normalized_values(self, mock_get_encoder):
        """All returned ROI scores are in [0, 1]."""
        mock_encoder = MagicMock()
        mock_encoder.predict.return_value = [2.5, -1.0, 0.0, 5.0]  # raw cross-encoder scores
        mock_get_encoder.return_value = mock_encoder

        from services.engines.roi_engine import ROIEngine
        engine = ROIEngine()
        chunks = [MockChunk(f"content {i}") for i in range(4)]
        results = engine.score("test query", chunks)

        for _, score in results:
            assert 0.0 <= score <= 1.0

    @patch("services.engines.roi_engine.get_cross_encoder")
    def test_engine_failure_returns_uniform(self, mock_get_encoder):
        """If CrossEncoder raises, return uniform 0.5 scores (graceful degradation)."""
        mock_encoder = MagicMock()
        mock_encoder.predict.side_effect = RuntimeError("OOM")
        mock_get_encoder.return_value = mock_encoder

        from services.engines.roi_engine import ROIEngine
        engine = ROIEngine()
        chunks = [MockChunk(f"content {i}") for i in range(3)]
        results = engine.score("test query", chunks)

        assert len(results) == 3
        for _, score in results:
            assert score == 0.5
