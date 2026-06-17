from typing import List
from core.redis_client import client as redis_client

class SpeculativePrefetcher:
    N_PREDICTIONS = 3
    CACHE_TTL = 600   # 10 minutes in Redis

    def __init__(self, optimization_pipeline=None):
        self.optimization_pipeline = optimization_pipeline

    async def prefetch(self, query: str, conversation_history: List[str]) -> None:
        """Runs in the background (non-blocking)."""
        predicted_queries = await self._predict_follow_ups(query, conversation_history)
        for pq in predicted_queries[:self.N_PREDICTIONS]:
            # Simple query hash
            import hashlib
            q_hash = hashlib.md5(pq.encode()).hexdigest()
            cache_key = f"prefetch:{q_hash}"
            
            # Check redis existence
            exists = await redis_client.get(cache_key)
            if not exists and self.optimization_pipeline:
                # Run optimization pipeline without LLM gateway call (or query mock)
                optimized = await self.optimization_pipeline.run(pq)
                # Store
                import json
                await redis_client.setex(cache_key, self.CACHE_TTL, json.dumps(optimized))

    async def _predict_follow_ups(self, query: str, history: List[str]) -> List[str]:
        # Simple rule-based expansion templates
        templates = {
            "explain": ["risks of {topic}", "{topic} vs alternatives", "how {topic} works internally"],
            "debug": ["how to fix {topic}", "{topic} in production", "prevent {topic}"],
            "general": ["alternatives to {topic}", "best practices for {topic}", "future of {topic}"]
        }
        
        query_lower = query.lower()
        topic = query
        # Very simple topic extraction: take words after first 2 words if query is long
        words = query.split()
        if len(words) > 2:
            topic = " ".join(words[2:])
            
        category = "general"
        if any(w in query_lower for w in ["explain", "what is", "how do"]):
            category = "explain"
        elif any(w in query_lower for w in ["debug", "error", "fail", "fix"]):
            category = "debug"
            
        predictions = []
        for temp in templates[category]:
            predictions.append(temp.format(topic=topic))
        return predictions
