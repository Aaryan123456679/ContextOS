from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from uuid import UUID

_camel = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class Chunk(BaseModel):
    model_config = _camel
    id: UUID
    content: str
    token_count: int
    document_id: UUID
    metadata: dict


class ScoredChunk(BaseModel):
    model_config = _camel
    chunk: Chunk
    roi_score: float
    dependency_pruned: bool
    contradiction_risk: float
    fusion_score: float
    allocated: bool


class UploadResponse(BaseModel):
    model_config = _camel
    document_id: UUID
    filename: str
    chunk_count: int
    message: str
