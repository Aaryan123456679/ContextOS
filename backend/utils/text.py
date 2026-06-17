"""Text utility helpers shared across services."""
import re
import tiktoken

_encoder = None


def get_encoder():
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding("cl100k_base")
    return _encoder


def count_tokens(text: str) -> int:
    """Count tokens using the cl100k_base encoding (matches GPT-4 and Claude)."""
    return len(get_encoder().encode(text))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to at most max_tokens tokens, preserving whole words."""
    enc = get_encoder()
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return enc.decode(tokens[:max_tokens])


def clean_text(text: str) -> str:
    """Remove excessive whitespace and non-printable characters."""
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)  # strip control chars
    text = re.sub(r"\n{3,}", "\n\n", text)                            # max 2 consecutive newlines
    text = re.sub(r" {2,}", " ", text)                                # collapse spaces
    return text.strip()


def extract_sentences(text: str) -> list[str]:
    """Split text into sentences using simple regex (no NLTK dependency)."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_text_fixed(text: str, chunk_size: int = 512, overlap: int = 64) -> list[dict]:
    """
    Fixed-size token chunking with overlap.
    Returns list of {content, chunk_index, token_count}.
    """
    enc = get_encoder()
    tokens = enc.encode(text)
    chunks = []
    i = 0
    idx = 0
    while i < len(tokens):
        end = min(i + chunk_size, len(tokens))
        chunk_tokens = tokens[i:end]
        chunks.append({
            "content": enc.decode(chunk_tokens),
            "chunk_index": idx,
            "token_count": len(chunk_tokens),
        })
        i += chunk_size - overlap
        idx += 1
    return chunks
