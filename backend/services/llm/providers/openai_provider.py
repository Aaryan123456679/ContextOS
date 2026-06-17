import time
from services.llm.providers.base import BaseProvider, LLMResponse, TokenUsage

class OpenAIProvider(BaseProvider):
    async def complete(
        self,
        prompt: str,
        model: str,
        api_key: str,
        max_tokens: int = 2048,
        temperature: float = 0.0,
        stream: bool = False
    ) -> LLMResponse:
        import openai
        start_time = time.time()
        client = openai.AsyncOpenAI(api_key=api_key)
        
        # Call completion
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream
        )
        
        latency = (time.time() - start_time) * 1000
        
        content = resp.choices[0].message.content or ""
        prompt_tokens = resp.usage.prompt_tokens if resp.usage else 0
        completion_tokens = resp.usage.completion_tokens if resp.usage else 0
        
        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            ),
            model=model,
            latency_ms=latency
        )
