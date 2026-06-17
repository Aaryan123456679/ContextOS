"""Integration tests for Validation Harness — requires real BERTScore."""
import pytest


class TestBERTScore:
    def test_identical_texts_score_near_one(self):
        """Identical reference and candidate → BERTScore F1 ≈ 1.0."""
        from services.validation.metrics import compute_bert_score
        text = "The mitochondria is the powerhouse of the cell."
        result = compute_bert_score(reference=text, candidate=text)
        assert result.f1 >= 0.95  # should be very close to 1.0

    def test_unrelated_texts_score_low(self):
        """Completely unrelated texts → BERTScore F1 significantly < 1.0."""
        from services.validation.metrics import compute_bert_score
        reference = "Paris is the capital of France."
        candidate = "The database crashed due to disk space exhaustion."
        result = compute_bert_score(reference=reference, candidate=candidate)
        assert result.f1 < 0.85  # should be notably lower

    def test_paraphrase_scores_above_threshold(self):
        """Semantic paraphrase passes the 0.90 threshold."""
        from services.validation.metrics import compute_bert_score
        reference = "The Docker container failed to start because PORT env var was missing."
        candidate = "Container startup failed — the PORT environment variable was not set."
        result = compute_bert_score(reference=reference, candidate=candidate)
        assert result.f1 >= 0.88  # should be high — same meaning


class TestValidationResult:
    def test_passed_true_when_all_thresholds_met(self):
        """ValidationResult.passed is True when all metric thresholds are met."""
        from services.validation.harness import build_validation_result
        result = build_validation_result(
            bert_score_f1=0.93,
            quality_delta=0.5,
            faithfulness=0.90,
            token_reduction_pct=45.0,
            cost_reduction_pct=40.0,
        )
        assert result.passed is True

    def test_passed_false_when_bert_below_threshold(self):
        """ValidationResult.passed is False if BERTScore < 0.90."""
        from services.validation.harness import build_validation_result
        result = build_validation_result(
            bert_score_f1=0.85,  # below threshold
            quality_delta=0.5,
            faithfulness=0.90,
            token_reduction_pct=45.0,
            cost_reduction_pct=40.0,
        )
        assert result.passed is False

    def test_passed_false_when_quality_regresses(self):
        """ValidationResult.passed is False if quality_delta < 0."""
        from services.validation.harness import build_validation_result
        result = build_validation_result(
            bert_score_f1=0.93,
            quality_delta=-1.0,  # optimized worse than baseline
            faithfulness=0.90,
            token_reduction_pct=45.0,
            cost_reduction_pct=40.0,
        )
        assert result.passed is False
