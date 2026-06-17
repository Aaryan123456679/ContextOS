"""Anthropic provider (optional, pricing-aware). Used only if ANTHROPIC_API_KEY is set."""
import os
import time
from typing import Optional
from .base import LLMProvider, LLMResult


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str = "claude-3-5-haiku-latest", api_key: str = None):
        super().__init__(model)
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    def complete(self, prompt: str, system: Optional[str] = None,
                 max_tokens: int = 512, temperature: float = 0.0) -> LLMResult:
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        t0 = time.time()
        r = client.messages.create(
            model=self.model, max_tokens=max_tokens, temperature=temperature,
            system=system or "", messages=[{"role": "user", "content": prompt}])
        latency = (time.time() - t0) * 1000
        text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        return LLMResult(text=text, prompt_tokens=r.usage.input_tokens,
                         completion_tokens=r.usage.output_tokens,
                         latency_ms=latency, model=self.model, model_digest=self.model)
