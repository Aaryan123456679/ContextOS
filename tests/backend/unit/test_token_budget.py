"""Unit tests for Token Budget Allocator — pure logic, no external calls."""
import pytest
from uuid import uuid4
from dataclasses import dataclass


@dataclass
class MockChunk:
    id: object
    token_count: int
    content: str = "test"

    def __post_init__(self):
        if self.id is None:
            self.id = uuid4()


@dataclass
class MockScoredChunk:
    chunk: MockChunk
    fusion_score: float


class TestTokenBudgetAllocator:
    def _make_chunks(self, specs: list[tuple[float, int]]) -> list[MockScoredChunk]:
        """Create scored chunks from (fusion_score, token_count) pairs."""
        return [
            MockScoredChunk(
                chunk=MockChunk(id=uuid4(), token_count=tokens),
                fusion_score=score
            )
            for score, tokens in specs
        ]

    def test_total_tokens_within_budget(self):
        """Selected chunks never exceed token budget."""
        from services.engines.token_budget import TokenBudgetAllocator
        allocator = TokenBudgetAllocator()
        chunks = self._make_chunks([(0.9, 500), (0.8, 300), (0.7, 400), (0.6, 600)])
        budget = 1000
        result = allocator.allocate(chunks, budget)
        assert result.total_tokens <= budget

    def test_higher_roi_per_token_selected_first(self):
        """Chunk with higher fusion_score/token_count ratio is selected over lower."""
        from services.engines.token_budget import TokenBudgetAllocator
        allocator = TokenBudgetAllocator()

        # Chunk A: score=0.9, tokens=900 → ratio 0.001
        # Chunk B: score=0.5, tokens=100 → ratio 0.005
        # Budget: 200 tokens → only one can fit if we pick greedily by ratio
        chunk_a = MockScoredChunk(chunk=MockChunk(id="a", token_count=900), fusion_score=0.9)
        chunk_b = MockScoredChunk(chunk=MockChunk(id="b", token_count=100), fusion_score=0.5)

        result = allocator.allocate([chunk_a, chunk_b], budget=200)
        selected_ids = [sc.chunk.id for sc in result.selected]
        assert "b" in selected_ids
        assert "a" not in selected_ids

    def test_empty_input(self):
        """Empty chunk list returns empty result."""
        from services.engines.token_budget import TokenBudgetAllocator
        allocator = TokenBudgetAllocator()
        result = allocator.allocate([], budget=8192)
        assert result.selected == []
        assert result.total_tokens == 0

    def test_single_chunk_fits(self):
        """Single chunk within budget is always selected."""
        from services.engines.token_budget import TokenBudgetAllocator
        allocator = TokenBudgetAllocator()
        chunks = self._make_chunks([(0.8, 100)])
        result = allocator.allocate(chunks, budget=200)
        assert len(result.selected) == 1
        assert result.total_tokens == 100

    def test_single_chunk_too_large_excluded(self):
        """Single chunk exceeding budget is excluded."""
        from services.engines.token_budget import TokenBudgetAllocator
        allocator = TokenBudgetAllocator()
        chunks = self._make_chunks([(0.9, 500)])
        result = allocator.allocate(chunks, budget=200)
        assert len(result.selected) == 0

    def test_utilization_pct_correct(self):
        """Utilization percentage is calculated correctly."""
        from services.engines.token_budget import TokenBudgetAllocator
        allocator = TokenBudgetAllocator()
        chunks = self._make_chunks([(0.8, 500)])
        result = allocator.allocate(chunks, budget=1000)
        assert result.utilization_pct == pytest.approx(50.0)
