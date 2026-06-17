import time
from services.llm.providers.base import BaseProvider, LLMResponse, TokenUsage

class GeminiProvider(BaseProvider):
    async def complete(
        self,
        prompt: str,
        model: str,
        api_key: str,
        max_tokens: int = 2048,
        temperature: float = 0.0,
        stream: bool = False
    ) -> LLMResponse:
        import google.generativeai as genai
        start_time = time.time()
        
        genai.configure(api_key=api_key)
        # Gemini model naming translation if needed, e.g. "gemini-1.5-flash"
        gemini_model = model
        if not gemini_model.startswith("models/"):
            gemini_model = f"models/{gemini_model}"
            
        g_model = genai.GenerativeModel(gemini_model)
        
        # Call completion (Gemini generate_content is blocking, so run in executor or call it directly)
        # Note: google-generativeai does support generate_content_async
        resp = await g_model.generate_content_async(
            contents=prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
        )
        
        latency = (time.time() - start_time) * 1000

        # `resp.text` raises when a candidate has no text part — e.g. "thinking"
        # models (Gemini 2.5+) that spend the whole token budget reasoning, or
        # safety-blocked responses. Extract defensively instead of crashing.
        content = ""
        try:
            content = resp.text
        except Exception:
            try:
                parts = resp.candidates[0].content.parts
                content = "".join(getattr(p, "text", "") or "" for p in parts)
            except Exception:
                content = ""
        if not content:
            content = (
                "[ContextOS] The model returned no text (it may have hit the output "
                "token limit while reasoning). Try again or use a larger token budget."
            )

        # Estimate token usage as google client doesn't expose usage directly inside return object consistently
        # count_tokens is async in GenerativeModel
        try:
            prompt_tokens_resp = await g_model.count_tokens_async(prompt)
            prompt_tokens = prompt_tokens_resp.total_tokens
            completion_tokens_resp = await g_model.count_tokens_async(content)
            completion_tokens = completion_tokens_resp.total_tokens
        except Exception:
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(content) // 4
            
        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            ),
            model=model,
            latency_ms=latency
        )
