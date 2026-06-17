"""Chunking — reuse the backend's production chunker so eval matches runtime."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

from services.ingestion.chunker import Chunker  # noqa: E402

_chunker = Chunker()


def chunk_text(text: str):
    """Return list of {content, token_count, chunk_index}."""
    return _chunker.chunk_text(text)
