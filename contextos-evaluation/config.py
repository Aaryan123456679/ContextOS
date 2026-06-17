"""
Central configuration for the ContextOS evaluation suite.

This package is independent from the backend app but calls the ContextOS engines
in-process (needed for fast ablation toggling). The path shim below makes
`backend/` importable without installing it.
"""
import os
import sys
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
EVAL_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_ROOT.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"


def _load_backend_env():
    """Importing the engine package pulls core.config (pydantic Settings), which
    requires several env vars. Load backend/.env so those imports validate. The
    Supabase/Qdrant/Redis clients are created lazily and NEVER called here — all
    evaluation data is stored locally on disk (see DATA_DIR), nothing online."""
    env = BACKEND_ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    # Hard defaults so imports succeed even if a key is missing in .env. These
    # clients are created lazily and never called by the eval. A few need a valid
    # URL *scheme* to parse at import (redis/postgres), so give them dummy URLs.
    defaults = {
        "SUPABASE_URL": "https://unused.local",
        "SUPABASE_KEY": "unused-local-eval",
        "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/unused",
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_KEY": "unused-local-eval",
        "UPSTASH_REDIS_URL": "redis://localhost:6379",
        "ENCRYPTION_KEY": "unused-local-eval",
    }
    for k, v in defaults.items():
        os.environ.setdefault(k, v)


_load_backend_env()

# Make the ContextOS engines importable (services.engines.*, models.schemas.*)
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

DATA_DIR = EVAL_ROOT / "data"
CORPUS_DIR = DATA_DIR / "corpus"
CORPUS_RAW = CORPUS_DIR / "raw"
CORPUS_MANIFEST = CORPUS_DIR / "manifest.jsonl"
SCENARIOS_PATH = DATA_DIR / "scenarios.jsonl"
CACHE_DIR = DATA_DIR / "cache"
RESULTS_DIR = EVAL_ROOT / "results" / "runs"

for _d in (DATA_DIR, CORPUS_DIR, CORPUS_RAW, CACHE_DIR, RESULTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ─── Reproducibility ──────────────────────────────────────────────────────────
SEED = 42

# ─── Models / providers ───────────────────────────────────────────────────────
DEFAULT_PROVIDER = "ollama"
# Default local model for an M1 16GB: capable judge, ~5GB, coexists with the
# cross-encoder / NLI / BERTScore models. Override with --model.
DEFAULT_MODEL = "llama3.1:8b"
OLLAMA_HOST = "http://localhost:11434"

# ─── Provider pricing (USD per 1M tokens) for cost estimation ─────────────────
# Local Ollama is $0 but we still report what the same run WOULD cost on hosted
# providers, which is what matters for the "cost savings" claim.
PRICING_VERSION = "2026-06"
PRICING = {
    # ollama local
    "ollama": {"input": 0.0, "output": 0.0},
    # gemini
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    # openai
    "gpt-4o": {"input": 2.50, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    # anthropic
    "claude-3-5-haiku": {"input": 0.80, "output": 4.0},
    "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
}
# When the run uses a free local model, price the "cost savings" as if served by
# this reference hosted model (so cost numbers are meaningful, not all zero).
COST_REFERENCE_MODEL = "gpt-4o-mini"


def price_for(model: str) -> dict:
    key = model.lower()
    for name, rates in PRICING.items():
        if name in key:
            return rates
    return PRICING[COST_REFERENCE_MODEL]


def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str = None) -> float:
    rates = price_for(model or COST_REFERENCE_MODEL)
    return prompt_tokens / 1e6 * rates["input"] + completion_tokens / 1e6 * rates["output"]


# ─── Document size tiers (tokens) ─────────────────────────────────────────────
SIZE_TIERS = {
    "small": (500, 1000),
    "medium": (5000, 20000),
    "large": (50000, 10**9),
}


def size_tier(tokens: int) -> str:
    if tokens < 1000:
        return "small"
    if tokens < 20000:
        return "medium"
    return "large"


# ─── Query categories ─────────────────────────────────────────────────────────
QUERY_TYPES = [
    "factual",
    "multi_hop",
    "long_context_synthesis",
    "contradiction_resolution",
    "comparative",
    "research_open",
]

# ─── Token budget given to the optimizer per scenario ─────────────────────────
DEFAULT_TOKEN_BUDGET = 4096

# ─── Success criteria (per the spec) ──────────────────────────────────────────
SUCCESS_TOKEN_REDUCTION_PCT = 20.0
SUCCESS_SIMILARITY = 0.90  # answer (optimized vs baseline) similarity floor
