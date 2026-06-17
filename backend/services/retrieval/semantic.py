from typing import List
from uuid import UUID
from core.vector_store import client, COLLECTION_NAME
from models.schemas.chunk import Chunk


class SemanticRetriever:
    async def retrieve(self, query_vector: List[float], document_ids: List[UUID], limit: int = 50) -> List[Chunk]:
        qdrant_filter = None
        if document_ids:
            from qdrant_client.models import Filter, FieldCondition, MatchAny
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchAny(any=[str(d) for d in document_ids]),
                    )
                ]
            )

        results = await client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=limit,
        )

        chunks = []
        for r in results:
            payload = r.payload or {}
            try:
                chunks.append(Chunk(
                    id=UUID(payload["chunk_id"]),
                    content=payload["content"],
                    token_count=payload["token_count"],
                    document_id=UUID(payload["document_id"]),
                    metadata=payload.get("metadata", {}),
                    embedding_score=float(r.score),
                ))
            except (KeyError, ValueError):
                continue
        return chunks
