"""
AINative Studio provider — OpenAI-compatible gateway (base_url
https://api.ainative.studio/api/v1) exposing many models (llama-3.3, qwen3,
deepseek-v3, gpt-4o-mini, gpt-oss, ...). Free-tier keys cover most open/standard
models; some premium models (e.g. claude-sonnet-4.5) require a paid plan.

Key from AINATIVE_API_KEY (or AINATIVE_KEY). Includes exponential backoff for
rate-limit / transient errors.
"""
import os
import time
from typing import Optional
from .base import LLMProvider, LLMResult

_BASE_URL = "https://api.ainative.studio/api/v1"


class AINativeProvider(LLMProvider):
    name = "ainative"

    def __init__(self, model: str = "gpt-4o-mini", api_key: str = None,
                 base_url: str = _BASE_URL, max_retries: int = 6):
        super().__init__(model)
        self.api_key = api_key or os.environ.get("AINATIVE_API_KEY") or os.environ.get("AINATIVE_KEY")
        self.base_url = base_url
        self.max_retries = max_retries
        if not self.api_key:
            raise RuntimeError("Set AINATIVE_API_KEY for the AINative provider.")

    def complete(self, prompt: str, system: Optional[str] = None,
                 max_tokens: int = 512, temperature: float = 0.0) -> LLMResult:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
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
        raise RuntimeError(f"AINative call failed after {self.max_retries} retries: {last}")
