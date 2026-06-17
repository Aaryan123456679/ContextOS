import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
import models.db  # noqa: F401 — registers ORM models with SQLAlchemy metadata
from api.middleware.logging import logging_middleware
from api.middleware.rate_limit import rate_limit_middleware
from api.middleware.auth import auth_middleware
from api.routes import chat, optimize, upload, metrics, history, compression

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="ContextOS Backend",
    description="Context Intelligence Operating System for LLMs",
    version="1.0.0",
)

# CORS — restrict to known origins in production
# Custom middleware — added first so they are innermost (run after CORS)
app.add_middleware(BaseHTTPMiddleware, dispatch=logging_middleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)
app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)

# CORS must be outermost (added last) so it handles preflight before anything else
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.ENVIRONMENT == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat.router, prefix="/api")
app.include_router(optimize.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(compression.router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.on_event("startup")
async def init_vector_store():
    """Create Qdrant collection if it doesn't exist yet."""
    try:
        from core.vector_store import ensure_collection
        await ensure_collection()
        logging.info("Qdrant collection ready.")
    except Exception as e:
        logging.warning("Qdrant init failed (will retry on first upload): %s", e)


@app.on_event("startup")
async def warm_models():
    """Pre-warm ML models in background so first user request isn't slow."""
    async def _warm():
        await asyncio.sleep(3)  # let app fully start first
        try:
            from services.engines.roi_engine import get_cross_encoder
            get_cross_encoder()
        except Exception as e:
            logging.warning("CrossEncoder warm failed: %s", e)
        try:
            from services.engines.contradiction import get_nli_model
            get_nli_model()
        except Exception as e:
            logging.warning("NLI model warm failed: %s", e)

    asyncio.create_task(_warm())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
