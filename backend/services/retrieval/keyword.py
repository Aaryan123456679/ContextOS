from typing import List
from uuid import UUID
from rank_bm25 import BM25Okapi
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.db.chunk import Chunk as DbChunk
from models.schemas.chunk import Chunk

class KeywordRetriever:
    async def retrieve(self, query: str, document_ids: List[UUID], db: AsyncSession, limit: int = 50) -> List[Chunk]:
        # Fetch chunks from Database for target document_ids
        stmt = select(DbChunk)
        if document_ids:
            stmt = stmt.where(DbChunk.document_id.in_(document_ids))
        
        result = await db.execute(stmt)
        db_chunks = result.scalars().all()
        
        if not db_chunks:
            return []

        # Tokenize corpus for BM25
        corpus = [c.content.lower().split(" ") for c in db_chunks]
        bm25 = BM25Okapi(corpus)
        
        tokenized_query = query.lower().split(" ")
        scores = bm25.get_scores(tokenized_query)
        
        # Zip, sort and take top limit
        scored_pairs = sorted(zip(db_chunks, scores), key=lambda x: x[1], reverse=True)
        top_pairs = scored_pairs[:limit]

        # When the user explicitly attached documents we keep their chunks even if
        # BM25 scores them 0 (no lexical overlap) — otherwise an attached document
        # would never reach the model unless the question reused its exact words.
        keep_zero_score = bool(document_ids)

        chunks = []
        for db_c, score in top_pairs:
            if score <= 0 and not keep_zero_score:
                continue
            chunks.append(Chunk(
                id=db_c.id,
                content=db_c.content,
                token_count=db_c.token_count,
                document_id=db_c.document_id,
                metadata=db_c.chunk_metadata or {}
            ))
        return chunks
