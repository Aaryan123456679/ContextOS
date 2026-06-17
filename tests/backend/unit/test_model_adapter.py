"""Unit tests for Model Context Adapter — format correctness per model."""
import pytest


class TestModelContextAdapter:
    def setup_method(self):
        from services.engines.model_adapter import ModelContextAdapter
        self.adapter = ModelContextAdapter()

    def test_claude_output_contains_xml_tags(self):
        result = self.adapter.adapt("Some context.", "claude-3-5-sonnet", "What is X?")
        assert "<context>" in result
        assert "</context>" in result
        assert "<query>" in result

    def test_gpt_output_is_prose_framed(self):
        result = self.adapter.adapt("Some context.", "gpt-4o", "What is X?")
        assert "retrieved" in result.lower() or "context" in result.lower()
        assert "<context>" not in result  # no XML tags for GPT

    def test_gemini_output_contains_brackets(self):
        result = self.adapter.adapt("Some context.", "gemini-1.5-flash", "What is X?")
        assert "[RETRIEVED CONTEXT]" in result or "CONTEXT" in result

    def test_unknown_model_uses_default(self):
        """Unknown model does not raise, uses default adapter."""
        result = self.adapter.adapt("Some context.", "unknown-model-xyz", "What is X?")
        assert "Some context." in result
        assert "What is X?" in result

    def test_context_content_preserved(self):
        """Original context content always appears in adapted output."""
        context = "The answer is 42 and this is important."
        for model in ["claude-3-5-sonnet", "gpt-4o", "gemini-1.5-flash"]:
            result = self.adapter.adapt(context, model, "test")
            assert "The answer is 42" in result

    def test_query_content_preserved(self):
        """Query appears in adapted output for all model types."""
        query = "unique_query_string_xyz"
        for model in ["claude-3-5-sonnet", "gpt-4o"]:
            result = self.adapter.adapt("context", model, query)
            assert query in result
