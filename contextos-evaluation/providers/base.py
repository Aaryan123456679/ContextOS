"""Common LLM provider interface so the runner is model/vendor-agnostic."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    model: str
    model_digest: str = ""  # version/identity for reproducibility


class LLMProvider:
    name: str = "base"

    def __init__(self, model: str):
        self.model = model

    def complete(self, prompt: str, system: Optional[str] = None,
                 max_tokens: int = 512, temperature: float = 0.0) -> LLMResult:
        raise NotImplementedError

    def model_digest(self) -> str:
        """A stable identifier of the exact model weights/version used."""
        return self.model
