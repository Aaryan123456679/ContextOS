from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from uuid import UUID
from typing import Optional, List
from models.schemas.chunk import ScoredChunk
from models.schemas.chat import OptimizationMetrics

_camel = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class OptimizeRequest(BaseModel):
    model_config = _camel
    query: str
    document_ids: List[UUID] = []
    token_budget: int = 8192
    model: str = "gpt-4o"


class OptimizeResponse(BaseModel):
    model_config = _camel
    optimized_text: str
    optimization_run_id: UUID
    metrics: OptimizationMetrics
    chunks: List[ScoredChunk]
