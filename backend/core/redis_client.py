import redis.asyncio as redis
from typing import Optional
from core.config import settings

client = redis.from_url(settings.UPSTASH_REDIS_URL, decode_responses=True)

async def cache_get(key: str) -> Optional[str]:
    return await client.get(key)

async def cache_set(key: str, value: str, ttl: int = 600):
    await client.setex(key, ttl, value)
