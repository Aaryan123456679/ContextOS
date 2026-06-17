"""
xAI Grok provider.

Grok's API is OpenAI-compatible (base_url https://api.x.ai/v1), so we reuse the
OpenAI client. Includes exponential backoff on rate-limit / transient errors,
which the free tier hits quickly. Key from XAI_API_KEY (or GROK_API_KEY).
"""
import os
import time
from typing import Optional
from .base import LLMProvider, LLMResult

_BASE_URL = "https://api.x.ai/v1"


class GrokProvider(LLMProvider):
    name = "grok"

    def __init__(self, model: str = "grok-3-mini", api_key: str = None,
                 base_url: str = _BASE_URL, max_retries: int = 6):
        super().__init__(model)
        self.api_key = api_key or os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")
        self.base_url = base_url
        self.max_retries = max_retries
        if not self.api_key:
            raise RuntimeError("Set XAI_API_KEY (or GROK_API_KEY) for the Grok provider.")

    def complete(self, prompt: str, system: Optional[str] = None,
                 max_tokens: int = 512, temperature: float = 0.0) -> LLMResult:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        messages = ([{"role": "system", "content": system}] if system else []) + \
                   [{"role": "user", "content": prompt}]
        delay = 2.0
        last_err = None
        for attempt in range(self.max_retries):
            try:
                t0 = time.time()
                r = client.chat.completions.create(
                    model=self.model, messages=messages,
                    max_tokens=max_tokens, temperature=temperature)
                latency = (time.time() - t0) * 1000
                u = r.usage
                return LLMResult(
                    text=r.choices[0].message.content or "",
                    prompt_tokens=getattr(u, "prompt_tokens", 0),
                    completion_tokens=getattr(u, "completion_tokens", 0),
                    latency_ms=latency, model=self.model, model_digest=self.model)
            except Exception as e:  # rate limit / transient -> backoff
                last_err = e
                msg = str(e).lower()
                if any(s in msg for s in ("rate", "429", "timeout", "overload", "503", "502")):
                    time.sleep(delay)
                    delay = min(delay * 2, 60)
                    continue
                raise
        raise RuntimeError(f"Grok call failed after {self.max_retries} retries: {last_err}")
