"""Local Ollama provider — the default for free, unlimited generation + judging."""
import time
import json
import urllib.request
from typing import Optional

from .base import LLMProvider, LLMResult

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, model: str = None, host: str = None):
        super().__init__(model or config.DEFAULT_MODEL)
        self.host = host or config.OLLAMA_HOST
        self._digest = None

    def _post(self, path: str, payload: dict, timeout: float = 600) -> dict:
        req = urllib.request.Request(
            f"{self.host}{path}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())

    def complete(self, prompt: str, system: Optional[str] = None,
                 max_tokens: int = 512, temperature: float = 0.0) -> LLMResult:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            payload["system"] = system
        t0 = time.time()
        data = self._post("/api/generate", payload)
        latency = (time.time() - t0) * 1000
        return LLMResult(
            text=data.get("response", ""),
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            latency_ms=latency,
            model=self.model,
            model_digest=self.model_digest(),
        )

    def model_digest(self) -> str:
        if self._digest is None:
            try:
                data = self._post("/api/show", {"name": self.model}, timeout=30)
                self._digest = (data.get("details", {}) or {}).get("parameter_size", "") + "|" + \
                    (data.get("model_info", {}) or {}).get("general.basename", self.model)
            except Exception:
                self._digest = self.model
        return self._digest

    @staticmethod
    def is_available(host: str = None) -> bool:
        host = host or config.OLLAMA_HOST
        try:
            urllib.request.urlopen(f"{host}/api/tags", timeout=5)
            return True
        except Exception:
            return False
