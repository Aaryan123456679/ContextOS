import re
import uuid
import logging
import tiktoken
from dataclasses import dataclass
from typing import List, Dict, Tuple
from models.schemas.chunk import Chunk
from models.schemas.compression import CompressionResult, RecoveryPointer

logger = logging.getLogger("contextos")

_PTR_PATTERN = r'\[PTR:(\w+)\|trigger:([^|]+)\|source:([^|]+)\|summary:([^\]]+)\]'
TARGET_COMPRESSION_RATIO = 0.40  # compressed text must be ≤ 40% of original token count


@dataclass
class ValidationCheckResult:
    meets_target: bool


def parse_pointers(raw_output: str, original_chunks: list) -> Tuple[str, Dict[str, RecoveryPointer]]:
    """Parse PTR tags from LLM compression output. Returns (clean_text, recovery_map)."""
    pointers: Dict[str, RecoveryPointer] = {}
    clean_text = raw_output

    for match in re.finditer(_PTR_PATTERN, raw_output):
        ptr_id, trigger, source, summary = match.groups()
        source_parts = source.rsplit(":", 1)
        doc_name = source_parts[0]

        byte_range = (0, 0)
        if len(source_parts) > 1:
            try:
                byte_range = tuple(map(int, source_parts[1].split("-")))
            except ValueError:
                pass

        pointers[ptr_id] = RecoveryPointer(
            ptr_id=ptr_id,
            trigger=trigger,
            source_doc=doc_name,
            byte_range=byte_range,
            summary=summary,
        )
        clean_text = clean_text.replace(match.group(0), f"[{ptr_id}]")

    return clean_text, pointers


def validate_compression_result(original_token_count: int, compressed_token_count: int) -> ValidationCheckResult:
    """Check whether compression achieved the target ratio (≤ 40% of original)."""
    if original_token_count == 0:
        return ValidationCheckResult(meets_target=True)
    ratio = compressed_token_count / original_token_count
    return ValidationCheckResult(meets_target=ratio <= TARGET_COMPRESSION_RATIO)


class RecoverableCompressor:
    COMPRESSION_MODEL = "gpt-4o-mini"

    def __init__(self, llm_gateway=None):
        self.llm_gateway = llm_gateway
        self.encoder = tiktoken.encoding_for_model("gpt-4o-mini")

    async def compress(self, chunks: List[Chunk], query: str, api_key: str = None, model: str = None, fallback_models: List[str] = None) -> CompressionResult:
        if not chunks:
            return CompressionResult(
                compression_id=uuid.uuid4(),
                compressed_text="",
                original_token_count=0,
                compressed_token_count=0,
                recovery_map={},
                expansion_triggers=[],
            )

        concatenated = self._concatenate(chunks)
        prompt = self._build_compression_prompt(concatenated, query)

        _has_key = self.llm_gateway and api_key and api_key != "mock-key"
        models = fallback_models or [model or self.COMPRESSION_MODEL]
        raw_output = ""
        if _has_key:
            try:
                response = await self.llm_gateway.complete_with_fallback(prompt, models, api_key)
                raw_output = response.content
            except Exception as e:
                logger.warning("Compression LLM call failed (models=%s): %s", models, e)
                raw_output = ""
        if not raw_output:
            # Fallback when the compression LLM is unavailable (no key / quota /
            # error): keep the ACTUAL source content so the document still reaches
            # the answering model. (A placeholder here would drop all context.)
            raw_output = concatenated

        return self._build_result(raw_output, chunks)

    def _concatenate(self, chunks: List[Chunk]) -> str:
        parts = []
        for c in chunks:
            doc_name = c.metadata.get("source", "document")
            parts.append(f"--- SOURCE: {doc_name} ---\n{c.content}")
        return "\n\n".join(parts)

    def _build_compression_prompt(self, context: str, query: str) -> str:
        return f"""Compress the following context for a RAG system answering the query:
"{query}"

Instructions:
1. Compress to ~40% of original length
2. Preserve all facts directly relevant to the query
3. For each omitted section, output a recovery pointer in this format:
   [PTR:ptr_01|trigger:user asks about X|source:doc.txt:100-200|summary:one line]
4. Output ONLY the compressed text with embedded recovery pointers.

Context to compress:
{context}"""

    def _build_result(self, raw: str, original_chunks: List[Chunk]) -> CompressionResult:
        clean_text, pointers = parse_pointers(raw, original_chunks)
        # Measure original and compressed with the SAME tokenizer over comparable
        # text: the "original" is the full concatenated context that would be sent
        # without compression. (Using the chunker's stored token_count here instead
        # made the no-op fallback look like it *expanded* the context, because the
        # "--- SOURCE ---" framing tokens were only counted on the compressed side.)
        original_tokens = len(self.encoder.encode(self._concatenate(original_chunks)))
        compressed_tokens = len(self.encoder.encode(clean_text))
        triggers = [p.trigger for p in pointers.values()]

        return CompressionResult(
            compression_id=uuid.uuid4(),
            compressed_text=clean_text,
            original_token_count=original_tokens,
            compressed_token_count=compressed_tokens,
            recovery_map=pointers,
            expansion_triggers=triggers,
        )
