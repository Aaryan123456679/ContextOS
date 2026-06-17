class BaseAdapter:
    def format(self, context: str, query: str) -> str:
        raise NotImplementedError()

class ClaudeAdapter(BaseAdapter):
    def format(self, context: str, query: str) -> str:
        """Wrap in XML tags — Claude processes structured XML context better."""
        return f"""<context>
{context}
</context>

<query>{query}</query>"""

class GPTAdapter(BaseAdapter):
    def format(self, context: str, query: str) -> str:
        """Prose-first, role-framed. GPT-4 handles natural prose well."""
        return f"""You are answering based on the following retrieved information:

{context}

Question: {query}"""

class GeminiAdapter(BaseAdapter):
    def format(self, context: str, query: str) -> str:
        """Citation-dense format — Gemini grounding works best with explicit citations."""
        return f"""[RETRIEVED CONTEXT]
{context}
[END CONTEXT]

Based on the above retrieved context, answer: {query}"""

class DefaultAdapter(BaseAdapter):
    def format(self, context: str, query: str) -> str:
        return f"Context:\n{context}\n\nQuestion: {query}"

class ModelContextAdapter:
    def adapt(self, context: str, model: str, query: str) -> str:
        adapter = self._get_adapter(model)
        return adapter.format(context, query)

    def _get_adapter(self, model: str) -> BaseAdapter:
        model_lower = model.lower()
        if "claude" in model_lower:
            return ClaudeAdapter()
        elif "gpt" in model_lower:
            return GPTAdapter()
        elif "gemini" in model_lower:
            return GeminiAdapter()
        return DefaultAdapter()
