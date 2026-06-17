"""Answer-to-query relevance via embedding similarity."""
from .similarity import embed_cosine


def relevance(query: str, answer: str) -> float:
    return round(embed_cosine(query, answer), 4)
