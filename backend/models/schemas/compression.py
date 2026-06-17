from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from uuid import UUID
from typing import Tuple, Optional, Any

_camel = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class RecoveryPointer(BaseModel):
    model_config = _camel
    ptr_id: str
    trigger: str
    source_doc: str
    byte_range: Tuple[int, int]
    summary: str


class CompressionResult(BaseModel):
    model_config = _camel
    compression_id: UUID
    compressed_text: str
    original_token_count: int
    compressed_token_count: int
    recovery_map: dict[str, RecoveryPointer]
    expansion_triggers: list[str]


class CompressionRecordResponse(BaseModel):
    model_config = _camel
    id: UUID
    compressed_text: str
    recovery_map: dict
    expansion_log: list
    created_at: Optional[Any] = None


class ExpansionResult(BaseModel):
    model_config = _camel
    ptr_id: str
    original_text: str
    summary: str
    trigger: str
    source_doc: str
