"""Gemini provider (optional) — uses the free key with model rotation on quota."""
import os
import time
from typing import Optional

from .base import LLMProvider, LLMResult

_FALLBACK_MODELS = [
    "gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite", "gemini-flash-latest",
]


def _quota(e) -> bool:
    s = str(e).lower()
    return "429" in s or "quota" in s or "exhausted" in s or "rate limit" in s


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, model: str = None, api_key: str = None):
        super().__init__(model or _FALLBACK_MODELS[0])
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            try:
                import config
                from core.config import settings  # backend
                self.api_key = settings.GEMINI_API_KEY
            except Exception:
                pass

    def complete(self, prompt: str, system: Optional[str] = None,
                 max_tokens: int = 512, temperature: float = 0.0) -> LLMResult:
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        models = [self.model] + [m for m in _FALLBACK_MODELS if m != self.model]
        last = None
        for m in models:
            try:
                gm = genai.GenerativeModel(f"models/{m}", system_instruction=system)
                t0 = time.time()
                r = gm.generate_content(prompt, generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens, temperature=temperature))
                latency = (time.time() - t0) * 1000
                try:
                    text = r.text
                except Exception:
                    text = "".join(getattr(p, "text", "") or "" for p in r.candidates[0].content.parts)
                usage = getattr(r, "usage_metadata", None)
                pt = getattr(usage, "prompt_token_count", len(prompt) // 4) if usage else len(prompt) // 4
                ct = getattr(usage, "candidates_token_count", len(text) // 4) if usage else len(text) // 4
                return LLMResult(text=text, prompt_tokens=pt, completion_tokens=ct,
                                 latency_ms=latency, model=m, model_digest=m)
            except Exception as e:
                last = e
                if _quota(e):
                    continue
                raise
        raise last
