"""Unit tests for Recoverable Compressor — pointer parsing logic."""
import pytest
from uuid import uuid4


class TestRecoveryPointerParsing:
    def _parse(self, raw_output: str):
        """Helper that imports and calls the parsing function."""
        from services.engines.compression import parse_pointers
        return parse_pointers(raw_output, original_chunks=[])

    def test_single_pointer_parsed(self):
        """Single PTR tag is parsed into recovery_map."""
        raw = "Compressed text. [PTR:ptr_01|trigger:user asks for error details|source:logs.txt:100-200|summary:Stack trace]"
        clean_text, recovery_map = self._parse(raw)
        assert "ptr_01" in recovery_map
        assert recovery_map["ptr_01"].trigger == "user asks for error details"
        assert recovery_map["ptr_01"].source_doc == "logs.txt"
        assert recovery_map["ptr_01"].byte_range == (100, 200)
        assert recovery_map["ptr_01"].summary == "Stack trace"

    def test_ptr_tag_replaced_with_inline_ref(self):
        """PTR tags are replaced with [ptr_XX] in clean text."""
        raw = "Before [PTR:ptr_01|trigger:x|source:doc.txt:0-100|summary:y] After"
        clean_text, _ = self._parse(raw)
        assert "[ptr_01]" in clean_text
        assert "[PTR:" not in clean_text

    def test_multiple_pointers_parsed(self):
        """Multiple PTR tags all parsed correctly."""
        raw = (
            "A [PTR:ptr_01|trigger:trigger1|source:a.txt:0-50|summary:summary1] "
            "B [PTR:ptr_02|trigger:trigger2|source:b.txt:51-100|summary:summary2]"
        )
        clean_text, recovery_map = self._parse(raw)
        assert len(recovery_map) == 2
        assert "ptr_01" in recovery_map
        assert "ptr_02" in recovery_map

    def test_no_pointers_returns_empty_map(self):
        """Text without PTR tags returns empty recovery_map."""
        raw = "This is compressed text with no pointers."
        clean_text, recovery_map = self._parse(raw)
        assert recovery_map == {}
        assert clean_text == raw

    def test_malformed_pointer_skipped(self):
        """Malformed PTR tag (missing fields) is skipped, no crash."""
        raw = "Text [PTR:broken_format] more text"
        clean_text, recovery_map = self._parse(raw)
        assert recovery_map == {}

    def test_source_without_byte_range(self):
        """Source without byte range gets (0, 0) default."""
        raw = "[PTR:ptr_01|trigger:test|source:doc.txt|summary:test summary]"
        _, recovery_map = self._parse(raw)
        assert recovery_map["ptr_01"].byte_range == (0, 0)

    def test_compression_ratio_assertion(self):
        """CompressionResult validates token ratio."""
        from services.engines.compression import validate_compression_result
        # 600 compressed tokens from 1000 original = 60% — below 60% threshold, should warn
        result = validate_compression_result(
            original_token_count=1000,
            compressed_token_count=600
        )
        assert result.meets_target is False  # didn't hit 40% target

        result2 = validate_compression_result(
            original_token_count=1000,
            compressed_token_count=350
        )
        assert result2.meets_target is True
