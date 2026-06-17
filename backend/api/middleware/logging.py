import time
import logging
from fastapi import Request

logger = logging.getLogger("contextos")


async def logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d  %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response
