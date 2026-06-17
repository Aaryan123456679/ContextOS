import redis.asyncio as redis
from typing import Optional
from core.config import settings

client = redis.from_url(settings.UPSTASH_REDIS_URL, decode_responses=True) if settings.UPSTASH_REDIS_URL else None

async def cache_get(key: str) -> Optional[str]:
    if client is None:
        return None
    return await client.get(key)

async def cache_set(key: str, value: str, ttl: int = 600):
    if client is None:
        return
    await client.setex(key, ttl, value)
