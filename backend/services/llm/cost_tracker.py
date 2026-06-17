from services.llm.providers.base import TokenUsage

COST_PER_1K_TOKENS = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-haiku-3": {"input": 0.00025, "output": 0.00125},
    "gemini-2.5-flash-lite": {"input": 0.0001, "output": 0.0004},
    "gemini-1.5-flash": {"input": 0.00035, "output": 0.00105},
    "gemini": {"input": 0.0001, "output": 0.0004},
}

class CostTracker:
    def __init__(self):
        # We can track session costs if needed
        self.session_cost = 0.0

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        # Normalize model names to key
        model_key = "gpt-4o-mini" # default
        for key in COST_PER_1K_TOKENS:
            if key in model.lower():
                model_key = key
                break
                
        rates = COST_PER_1K_TOKENS.get(model_key)
        input_cost = (prompt_tokens / 1000.0) * rates["input"]
        output_cost = (completion_tokens / 1000.0) * rates["output"]
        return input_cost + output_cost

    async def record(self, model: str, usage: TokenUsage):
        cost = self.calculate_cost(model, usage.prompt_tokens, usage.completion_tokens)
        self.session_cost += cost
