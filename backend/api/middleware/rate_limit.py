import time
from collections import defaultdict
from fastapi import Request, HTTPException

# Simple in-memory token-bucket per IP.
# Render free tier: single process, so this is sufficient.
_buckets: dict[str, list[float]] = defaultdict(list)

WINDOW_SECONDS = 60
MAX_REQUESTS = 60  # 60 req/min per IP


async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - WINDOW_SECONDS

    # Evict timestamps outside the window
    _buckets[ip] = [t for t in _buckets[ip] if t > window_start]

    if len(_buckets[ip]) >= MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in a minute.")

    _buckets[ip].append(now)
    return await call_next(request)
