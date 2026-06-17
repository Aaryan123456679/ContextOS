from typing import List, Any
from pydantic import BaseModel, ConfigDict


class AllocationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    selected: List[Any]
    total_tokens: int
    budget: int
    utilization_pct: float


class TokenBudgetAllocator:
    def allocate(self, chunks: List[Any], budget: int) -> AllocationResult:
        sorted_chunks = sorted(
            chunks,
            key=lambda c: c.fusion_score / max(c.chunk.token_count, 1),
            reverse=True,
        )
        selected = []
        remaining = budget

        for sc in sorted_chunks:
            if sc.chunk.token_count <= remaining:
                selected.append(sc)
                remaining -= sc.chunk.token_count

        total_tokens = budget - remaining
        utilization_pct = (total_tokens / budget * 100) if budget > 0 else 0.0

        return AllocationResult(
            selected=selected,
            total_tokens=total_tokens,
            budget=budget,
            utilization_pct=utilization_pct,
        )
