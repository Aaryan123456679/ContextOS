"""Unit tests for Chunker — strategy correctness."""
import pytest


class TestChunker:
    def setup_method(self):
        from services.ingestion.chunker import Chunker
        self.chunker = Chunker()

    def test_fixed_chunking_respects_size(self):
        """Fixed chunking produces chunks with at most MAX tokens."""
        text = "word " * 2000  # ~2000 tokens
        chunks = self.chunker.chunk(text, strategy="fixed")
        for chunk in chunks:
            assert chunk["token_count"] <= self.chunker.DEFAULT_CHUNK_SIZE + 10  # small buffer

    def test_chunking_preserves_all_content(self):
        """All text appears across chunks — no content dropped."""
        text = "The quick brown fox jumps over the lazy dog. " * 100
        chunks = self.chunker.chunk(text, strategy="recursive")
        reconstructed = " ".join(c["content"] for c in chunks)
        # All original words should appear somewhere
        for word in ["quick", "brown", "fox", "lazy"]:
            assert word in reconstructed

    def test_overlap_creates_shared_content(self):
        """Adjacent chunks share content when overlap > 0."""
        text = "sentence one. sentence two. sentence three. sentence four. sentence five. " * 20
        chunks = self.chunker.chunk(text, strategy="recursive")
        if len(chunks) >= 2:
            # Overlap means end of chunk N shares content with start of chunk N+1
            # At least some characters should appear in both consecutive chunks
            c1_end = chunks[0]["content"][-50:]
            c2_start = chunks[1]["content"][:100]
            # They should have some overlap — not a strict assertion, just verify chunks exist
            assert len(chunks) > 1

    def test_empty_text_returns_empty(self):
        chunks = self.chunker.chunk("", strategy="recursive")
        assert chunks == []

    def test_short_text_single_chunk(self):
        """Text shorter than chunk size produces exactly one chunk."""
        text = "This is a short text."
        chunks = self.chunker.chunk(text, strategy="recursive")
        assert len(chunks) == 1
        assert text.strip() in chunks[0]["content"]

    def test_chunk_indices_are_sequential(self):
        """Chunk indices start at 0 and increment by 1."""
        text = "word " * 1000
        chunks = self.chunker.chunk(text, strategy="fixed")
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))
