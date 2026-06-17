import asyncio
from typing import List, Optional
from core.config import settings


class Embedder:
    """Embeds text for vector search.

    Prefers OpenAI when an OpenAI key is configured, otherwise falls back to
    Gemini's free embedding model (gemini-embedding-001), requesting 1536-dim
    output so it matches the existing Qdrant collection.
    """

    GEMINI_EMBED_MODEL = "models/gemini-embedding-001"
    EMBED_DIM = 1536  # must match the Qdrant collection dimension

    def __init__(self, api_key: Optional[str] = None):
        self._openai_key = api_key or settings.OPENAI_API_KEY
        self._gemini_key = settings.GEMINI_API_KEY

    async def embed_chunks(
        self,
        chunks: List[str],
        model: str = "text-embedding-3-small",
        task_type: str = "retrieval_document",
    ) -> List[List[float]]:
        if not chunks:
            return []
        if self._openai_key:
            return await self._embed_openai(chunks, model)
        if self._gemini_key:
            # genai.embed_content is blocking → run off the event loop.
            return await asyncio.to_thread(self._embed_gemini, chunks, task_type)
        raise RuntimeError("No embedding key configured (set OPENAI_API_KEY or GEMINI_API_KEY)")

    async def _embed_openai(self, chunks: List[str], model: str) -> List[List[float]]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._openai_key)
        embeddings: List[List[float]] = []
        for i in range(0, len(chunks), 100):
            batch = chunks[i : i + 100]
            response = await client.embeddings.create(input=batch, model=model)
            embeddings.extend([e.embedding for e in response.data])
        return embeddings

    def _embed_gemini(self, chunks: List[str], task_type: str) -> List[List[float]]:
        import google.generativeai as genai

        genai.configure(api_key=self._gemini_key)
        embeddings: List[List[float]] = []
        for i in range(0, len(chunks), 100):
            batch = chunks[i : i + 100]
            result = genai.embed_content(
                model=self.GEMINI_EMBED_MODEL,
                content=batch,
                task_type=task_type,
                output_dimensionality=self.EMBED_DIM,
            )
            emb = result["embedding"]
            # A batch returns a list of vectors; a single string returns one vector.
            if emb and isinstance(emb[0], (list, tuple)):
                embeddings.extend([list(v) for v in emb])
            else:
                embeddings.append(list(emb))
        return embeddings
