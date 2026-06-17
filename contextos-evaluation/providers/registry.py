"""Provider factory — selects the LLM backend by name."""
from .base import LLMProvider


def get_provider(name: str = "ollama", model: str = None, **kwargs) -> LLMProvider:
    name = (name or "ollama").lower()
    if name == "ollama":
        from .ollama_provider import OllamaProvider
        return OllamaProvider(model=model, **kwargs)
    if name == "gemini":
        from .gemini_provider import GeminiProvider
        return GeminiProvider(model=model, **kwargs)
    if name == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(model=model or "gpt-4o-mini", **kwargs)
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(model=model or "claude-3-5-haiku-latest", **kwargs)
    if name in ("grok", "xai"):
        from .grok_provider import GrokProvider
        return GrokProvider(model=model or "grok-3-mini", **kwargs)
    if name in ("ainative", "ai-native"):
        from .ainative_provider import AINativeProvider
        return AINativeProvider(model=model or "gpt-4o-mini", **kwargs)
    if name in ("openrouter", "or"):
        from .openrouter_provider import OpenRouterProvider
        return OpenRouterProvider(model=model or "openai/gpt-4o-mini", **kwargs)
    raise ValueError(f"Unknown provider: {name}")
