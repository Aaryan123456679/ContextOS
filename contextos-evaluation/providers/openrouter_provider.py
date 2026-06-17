"""
OpenRouter provider — OpenAI-compatible gateway (base_url
https://openrouter.ai/api/v1) with namespaced model ids, e.g.
  openai/gpt-4o, openai/gpt-4o-mini, anthropic/claude-3.5-sonnet,
  meta-llama/llama-3.3-70b-instruct, deepseek/deepseek-chat
plus free variants (suffix ':free').

Key from OPENROUTER_API_KEY. Includes exponential backoff for rate limits.
"""
import os
import time
from typing import Optional
from .base import LLMProvider, LLMResult

_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider(LLMProvider):
    name = "openrouter"

    def __init__(self, model: str = "openai/gpt-4o-mini", api_key: str = None,
                 base_url: str = _BASE_URL, max_retries: int = 6):
        super().__init__(model)
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
        self.base_url = base_url
        self.max_retries = max_retries
        if not self.api_key:
            raise RuntimeError("Set OPENROUTER_API_KEY for the OpenRouter provider.")

    def complete(self, prompt: str, system: Optional[str] = None,
                 max_tokens: int = 512, temperature: float = 0.0) -> LLMResult:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url,
                        default_headers={"HTTP-Referer": "https://contextos.eval",
                                         "X-Title": "ContextOS-Eval"})
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": prompt}]
        delay, last = 2.0, None
        for _ in range(self.max_retries):
            try:
                t0 = time.time()
                r = client.chat.completions.create(
                    model=self.model, messages=messages,
                    max_tokens=max_tokens, temperature=temperature)
                latency = (time.time() - t0) * 1000
                u = getattr(r, "usage", None)
                return LLMResult(
                    text=(r.choices[0].message.content or ""),
                    prompt_tokens=getattr(u, "prompt_tokens", 0) if u else 0,
                    completion_tokens=getattr(u, "completion_tokens", 0) if u else 0,
                    latency_ms=latency, model=self.model, model_digest=self.model)
            except Exception as e:
                last = e
                if any(s in str(e).lower() for s in ("rate", "429", "timeout", "overload", "503", "502")):
                    time.sleep(delay); delay = min(delay * 2, 60); continue
                raise
        raise RuntimeError(f"OpenRouter call failed after {self.max_retries} retries: {last}")
