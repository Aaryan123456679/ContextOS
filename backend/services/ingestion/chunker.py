import tiktoken
from typing import List, Dict


class Chunker:
    DEFAULT_CHUNK_SIZE = 500

    def __init__(self, model_name: str = "gpt-4o", chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = 50):
        self.encoder = tiktoken.encoding_for_model(model_name)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, strategy: str = "recursive") -> List[Dict]:
        """Public entry point. Both 'fixed' and 'recursive' use the same token-based window."""
        return self.chunk_text(text)

    def chunk_text(self, text: str) -> List[Dict]:
        if not text or not text.strip():
            return []

        tokens = self.encoder.encode(text)
        chunks = []
        start = 0
        chunk_idx = 0

        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_content = self.encoder.decode(chunk_tokens)
            chunks.append({
                "content": chunk_content,
                "token_count": len(chunk_tokens),
                "chunk_index": chunk_idx,
            })
            chunk_idx += 1
            if end == len(tokens):
                break
            start += self.chunk_size - self.chunk_overlap

        return chunks
