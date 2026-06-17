from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from uuid import UUID
from typing import Optional, Any

_camel = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class EngineContribution(BaseModel):
    model_config = _camel
    tokens_removed: int
    quality_delta: float
    enabled: bool


class EngineBreakdown(BaseModel):
    model_config = _camel
    roi_engine: EngineContribution
    dependency_graph: EngineContribution
    compression: EngineContribution
    contradiction: EngineContribution


class OptimizationMetrics(BaseModel):
    model_config = _camel
    original_tokens: int
    optimized_tokens: int
    token_reduction_pct: float
    cost_original: float
    cost_optimized: float
    bert_score: float
    quality_score: float
    engine_breakdown: EngineBreakdown


class EngineToggles(BaseModel):
    model_config = _camel
    roi_enabled: bool = True
    dependency_enabled: bool = False
    contradiction_enabled: bool = False
    compression_enabled: bool = False


class ChatRequest(BaseModel):
    model_config = _camel
    conversation_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    user_email: Optional[str] = None
    message: str
    model: str
    document_ids: list[UUID] = []
    token_budget: int = 8192
    optimization_enabled: bool = True
    user_api_key: Optional[str] = None
    engine_toggles: Optional[EngineToggles] = None


class ChatResponse(BaseModel):
    model_config = _camel
    message_id: UUID
    conversation_id: Optional[UUID] = None
    content: str
    optimization_run_id: Optional[UUID] = None
    metrics: Optional[OptimizationMetrics] = None


class AggregateMetrics(BaseModel):
    model_config = _camel
    total_runs: int
    avg_token_reduction_pct: float
    avg_bert_score: float
    avg_quality_score: float
    total_cost_saved: float


class ConversationDetail(BaseModel):
    model_config = _camel
    id: UUID
    title: str
    model: str
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None


class ConversationListResponse(BaseModel):
    model_config = _camel
    conversations: list[ConversationDetail]
    total: int
