import time
from services.llm.providers.base import BaseProvider, LLMResponse, TokenUsage

class AnthropicProvider(BaseProvider):
    async def complete(
        self,
        prompt: str,
        model: str,
        api_key: str,
        max_tokens: int = 2048,
        temperature: float = 0.0,
        stream: bool = False
    ) -> LLMResponse:
        import anthropic
        start_time = time.time()
        client = anthropic.AsyncAnthropic(api_key=api_key)
        
        # Call Anthropic Message creation
        resp = await client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        latency = (time.time() - start_time) * 1000
        content = resp.content[0].text if resp.content else ""
        prompt_tokens = resp.usage.input_tokens if resp.usage else 0
        completion_tokens = resp.usage.output_tokens if resp.usage else 0
        
        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            ),
            model=model,
            latency_ms=latency
        )
