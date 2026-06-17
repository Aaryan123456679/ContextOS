from typing import List, Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from services.retrieval.semantic import SemanticRetriever
from services.retrieval.keyword import KeywordRetriever
from models.schemas.chunk import Chunk

class HybridRetriever:
    def __init__(self, semantic_retriever: SemanticRetriever, keyword_retriever: KeywordRetriever):
        self.semantic = semantic_retriever
        self.keyword = keyword_retriever

    async def retrieve(
        self, 
        query: str, 
        query_vector: List[float], 
        document_ids: List[UUID], 
        db: AsyncSession, 
        limit: int = 50,
        k: int = 60
    ) -> List[Chunk]:
        # Run retrieval in parallel or sequence
        semantic_results = await self.semantic.retrieve(query_vector, document_ids, limit=limit*2)
        keyword_results = await self.keyword.retrieve(query, document_ids, db, limit=limit*2)

        # Reciprocal Rank Fusion
        scores: Dict[UUID, float] = {}
        chunk_map: Dict[UUID, Chunk] = {}

        for rank, chunk in enumerate(semantic_results):
            chunk_map[chunk.id] = chunk
            scores[chunk.id] = scores.get(chunk.id, 0.0) + (1.0 / (rank + k))

        for rank, chunk in enumerate(keyword_results):
            chunk_map[chunk.id] = chunk
            scores[chunk.id] = scores.get(chunk.id, 0.0) + (1.0 / (rank + k))

        # Sort by score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [chunk_map[cid] for cid in sorted_ids[:limit]]
