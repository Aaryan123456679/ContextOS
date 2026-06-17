from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    SUPABASE_URL: str
    SUPABASE_KEY: str
    DATABASE_URL: str              # Supabase PostgreSQL connection string

    # Vector Store
    QDRANT_URL: str
    QDRANT_KEY: str

    # Cache (optional — only used for speculative prefetching)
    UPSTASH_REDIS_URL: Optional[str] = None

    # Encryption
    ENCRYPTION_KEY: str            # 32-byte AES key for API key encryption

    # LLM API keys (used by backend for embeddings; LLM calls use user-provided keys)
    OPENAI_API_KEY: Optional[str] = None
    # Server-side fallback LLM key — used when a user has not supplied their own.
    GEMINI_API_KEY: Optional[str] = None

    # Context selection: "learned" uses the trained all-signal policy (validated to
    # beat the density allocator + SOTA compression in eval); "fixed" = density allocator.
    # Learned mode falls back to density automatically on any error.
    SELECTION_MODE: str = "learned"

    # LLM compression stage. OFF by default: in evaluation it degraded quality and
    # over-compressed; selection (ROI→fusion→policy) is the optimizer, matching the
    # eval architecture. Set true to re-enable compression.
    COMPRESSION_ENABLED: bool = False

    # Latency controls. The eval ablation showed the dependency-graph and contradiction
    # engines contribute ~0 to selection, and the learned policy leans on ROI/fusion —
    # so both are OFF by default to cut per-request CPU time. RETRIEVAL_LIMIT caps the
    # candidate pool the engines score (smaller = faster).
    ENABLE_DEPENDENCY_ENGINE: bool = False
    ENABLE_CONTRADICTION_ENGINE: bool = False
    RETRIEVAL_LIMIT: int = 24

    # App
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    RENDER_HEALTHCHECK_TOKEN: Optional[str] = None # for /health auth

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
