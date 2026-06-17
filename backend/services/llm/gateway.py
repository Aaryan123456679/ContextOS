import asyncio
from core.exceptions import LLMError, RateLimitError
from services.llm.providers.base import BaseProvider, LLMResponse
from services.llm.providers.openai_provider import OpenAIProvider
from services.llm.providers.anthropic_provider import AnthropicProvider
from services.llm.providers.gemini_provider import GeminiProvider
from services.llm.cost_tracker import CostTracker


def is_quota_error(exc: Exception) -> bool:
    s = str(exc).lower()
    return "429" in s or "quota" in s or "exhausted" in s or "rate limit" in s


class LLMGateway:
    def __init__(self, cost_tracker: CostTracker = None):
        self.cost_tracker = cost_tracker or CostTracker()

    async def complete(
        self,
        prompt: str,
        model: str,
        api_key: str,
        max_tokens: int = 2048,
        temperature: float = 0.0,
        stream: bool = False
    ) -> LLMResponse:
        provider = self._get_provider(model)
        try:
            response = await provider.complete(prompt, model, api_key, max_tokens, temperature, stream)
            await self.cost_tracker.record(model, response.usage)
            return response
        except RateLimitError:
            # Simple backoff
            await asyncio.sleep(2)
            return await self.complete(prompt, model, api_key, max_tokens, temperature, stream)
        except Exception as e:
            raise LLMError(f"Provider {model} failed: {e}")

    async def complete_with_fallback(
        self,
        prompt: str,
        models: list[str],
        api_key: str,
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Try each model in order, rolling over to the next on a quota/429 error.
        Each Gemini model has its own per-day free-tier bucket, so rotation keeps
        working when one is exhausted. Non-quota errors are raised immediately."""
        last_err = None
        for i, model in enumerate(models):
            try:
                return await self.complete(prompt, model, api_key, max_tokens, temperature)
            except Exception as e:
                last_err = e
                if is_quota_error(e) and i < len(models) - 1:
                    continue
                raise
        raise last_err if last_err else LLMError("No models provided")

    def _get_provider(self, model: str) -> BaseProvider:
        model_lower = model.lower()
        if "gpt" in model_lower or "o1" in model_lower:
            return OpenAIProvider()
        elif "claude" in model_lower:
            return AnthropicProvider()
        elif "gemini" in model_lower:
            return GeminiProvider()
        raise ValueError(f"Unknown model: {model}")
