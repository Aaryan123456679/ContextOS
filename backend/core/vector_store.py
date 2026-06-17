import logging
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance, PayloadSchemaType
from core.config import settings

logger = logging.getLogger("contextos")

QDRANT_URL = settings.QDRANT_URL
QDRANT_API_KEY = settings.QDRANT_KEY

client = AsyncQdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

COLLECTION_NAME = "contextos_chunks"


async def ensure_collection():
    existing = await client.get_collections()
    if COLLECTION_NAME not in [c.name for c in existing.collections]:
        await client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )

    # A payload index on document_id is required to filter searches by document.
    # Creating it is idempotent — ignore "already exists" errors.
    try:
        await client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="document_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
    except Exception as e:
        logger.debug("document_id payload index already present or skipped: %s", e)
