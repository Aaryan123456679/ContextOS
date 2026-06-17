import uuid
import logging
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_db
from models.schemas.chunk import UploadResponse
from services.ingestion.parser import FileParser
from services.ingestion.chunker import Chunker
from services.ingestion.embedder import Embedder
from services.ingestion.normalizer import Normalizer
from core.vector_store import client as qdrant_client, COLLECTION_NAME, ensure_collection

logger = logging.getLogger("contextos")

router = APIRouter()

parser = FileParser()
chunker = Chunker()
embedder = Embedder()
normalizer = Normalizer()


@router.post("/upload", response_model=UploadResponse)
async def upload(
    user_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content_bytes = await file.read()
    filename = file.filename or "unknown"

    # Parse → normalize → chunk
    raw_text = parser.parse(filename, content_bytes)
    cleaned_text = normalizer.normalize_text(raw_text)
    chunks = chunker.chunk_text(cleaned_text)

    if not chunks:
        return UploadResponse(
            document_id=uuid.uuid4(),
            filename=filename,
            chunk_count=0,
            message="File parsed but contained no text.",
        )

    # Embed (with zero-vector fallback when no OpenAI key configured)
    chunk_contents = [c["content"] for c in chunks]
    try:
        embeddings = await embedder.embed_chunks(chunk_contents)
    except Exception as e:
        logger.warning("Embedding failed (%s), using zero vectors", e)
        embeddings = [[0.0] * 1536 for _ in chunks]

    # Persist document record to DB
    doc_id = uuid.uuid4()
    file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
    try:
        await db.execute(
            text("""
                INSERT INTO users (id, email, created_at)
                VALUES (:user_id, :email, NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            {"user_id": str(user_id), "email": f"{user_id}@contextos.local"},
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.warning("User upsert failed (%s), continuing", e)

    try:
        await db.execute(
            text("""
                INSERT INTO documents (id, user_id, filename, file_type, chunk_count, created_at)
                VALUES (:id, :user_id, :filename, :file_type, :chunk_count, NOW())
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": str(doc_id),
                "user_id": str(user_id),
                "filename": filename,
                "file_type": file_ext,
                "chunk_count": len(chunks),
            },
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.warning("Document DB insert failed (%s), continuing", e)

    # Upsert vectors to Qdrant
    try:
        from qdrant_client.models import PointStruct
        await ensure_collection()

        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = uuid.uuid4()
            points.append(
                PointStruct(
                    id=str(chunk_id),
                    vector=embedding,
                    payload={
                        "chunk_id": str(chunk_id),
                        "document_id": str(doc_id),
                        "content": chunk["content"],
                        "token_count": chunk["token_count"],
                        "chunk_index": chunk["chunk_index"],
                        "metadata": {"source": filename, "file_type": file_ext},
                    },
                )
            )

        # Upsert in batches of 100
        for batch_start in range(0, len(points), 100):
            await qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=points[batch_start : batch_start + 100],
            )

        # Persist chunk records to DB
        try:
            for i, (chunk, point) in enumerate(zip(chunks, points)):
                await db.execute(
                    text("""
                        INSERT INTO chunks (id, document_id, qdrant_id, content, token_count, chunk_index, metadata)
                        VALUES (:id, :doc_id, :qdrant_id, :content, :token_count, :chunk_index, CAST(:metadata AS jsonb))
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": point.id,
                        "doc_id": str(doc_id),
                        "qdrant_id": point.id,
                        "content": chunk["content"],
                        "token_count": chunk["token_count"],
                        "chunk_index": chunk["chunk_index"],
                        "metadata": '{"source": "' + filename + '"}',
                    },
                )
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.warning("Chunk DB insert failed (%s), vectors still stored in Qdrant", e)

    except Exception as e:
        logger.error("Qdrant upsert failed: %s", e)

    return UploadResponse(
        document_id=doc_id,
        filename=filename,
        chunk_count=len(chunks),
        message=f"Ingested {len(chunks)} chunks from '{filename}'.",
    )
