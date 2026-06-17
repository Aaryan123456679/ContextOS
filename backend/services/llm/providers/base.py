from pydantic import BaseModel, ConfigDict
from typing import Optional

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    model_config = ConfigDict(from_attributes=True)

class LLMResponse(BaseModel):
    content: str
    usage: TokenUsage
    model: str
    latency_ms: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class BaseProvider:
    async def complete(
        self,
        prompt: str,
        model: str,
        api_key: str,
        max_tokens: int = 2048,
        temperature: float = 0.0,
        stream: bool = False
    ) -> LLMResponse:
        raise NotImplementedError()
