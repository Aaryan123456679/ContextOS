"""OpenAI provider (optional, pricing-aware). Used only if OPENAI_API_KEY is set."""
import os
import time
from typing import Optional
from .base import LLMProvider, LLMResult


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini", api_key: str = None):
        super().__init__(model)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def complete(self, prompt: str, system: Optional[str] = None,
                 max_tokens: int = 512, temperature: float = 0.0) -> LLMResult:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": prompt}]
        t0 = time.time()
        r = client.chat.completions.create(model=self.model, messages=messages,
                                           max_tokens=max_tokens, temperature=temperature)
        latency = (time.time() - t0) * 1000
        return LLMResult(text=r.choices[0].message.content or "",
                         prompt_tokens=r.usage.prompt_tokens,
                         completion_tokens=r.usage.completion_tokens,
                         latency_ms=latency, model=self.model, model_digest=self.model)
