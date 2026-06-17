# Recoverable Compression — Detailed Design

## Purpose

Compress selected context to ~40% of original length, but maintain the ability to surgically expand any omitted section on demand. This creates "virtual context windows" — the LLM perceives access to more information than was ever sent.

## Why Not Standard Summarization

Standard summarization is lossy and irreversible. Once a detail is summarized away, there is no way to get it back without re-running retrieval.

ContextOS compression embeds **recovery pointers** directly in the compressed text. Each pointer is a reference to the original passage with enough information to fetch and inject it mid-conversation.

## Recovery Pointer Structure

```json
{
  "ptr_id": "ptr_03",
  "trigger": "user asks for the exact error message or stack trace",
  "source_doc": "docker_logs.txt",
  "byte_range": [1204, 1890],
  "summary": "Full NullPointerException stack trace from container startup"
}
```

**ptr_id:** Unique identifier within the compression. Referenced as `[ptr_03]` in the compressed text.  
**trigger:** Natural language description of when this pointer should be expanded. Used by the frontend and can be checked against follow-up queries.  
**source_doc:** The document in Supabase Storage. Must be the exact path.  
**byte_range:** Character byte range in the original document. Allows exact reconstruction.  
**summary:** One-line description for the RecoveryPointerViewer UI.

## Compression Prompt Design

```
System: You are a lossless context compressor for a RAG system.

User: Compress the following retrieved context for answering this query:
"{query}"

Rules:
1. Target 40% of original length (current: {token_count} tokens → target: {target_tokens})
2. Preserve ALL facts directly relevant to: {query}
3. For omitted sections, embed a recovery pointer inline:
   [PTR:ptr_01|trigger:expand when user asks about X|source:filename.txt:100-200|summary:one line]
4. Output ONLY the compressed text with embedded [PTR:...] markers.
5. Do not summarize — compress. Keep relevant sentences verbatim if needed.
6. Number pointers sequentially: ptr_01, ptr_02, ...

Context:
{context}
```

**Why Claude Haiku / GPT-4o-mini:** Both can follow structured output instructions reliably. GPT-4o-mini is the cheapest option; Haiku is slightly better at instruction following. Either works.

## Pointer Parsing

```python
import re

PTR_PATTERN = r'\[PTR:(\w+)\|trigger:([^|]+)\|source:([^|]+)\|summary:([^\]]+)\]'

def parse_pointers(raw_output: str, original_chunks: list[Chunk]) -> tuple[str, dict]:
    recovery_map = {}
    clean_text = raw_output

    for match in re.finditer(PTR_PATTERN, raw_output):
        ptr_id, trigger, source, summary = match.groups()

        # parse "filename.txt:100-200" → source_doc, byte_range
        parts = source.rsplit(":", 1)
        source_doc = parts[0]
        byte_range = (0, 0)
        if len(parts) == 2:
            try:
                lo, hi = parts[1].split("-")
                byte_range = (int(lo), int(hi))
            except ValueError:
                pass

        recovery_map[ptr_id] = RecoveryPointer(
            ptr_id=ptr_id,
            trigger=trigger.strip(),
            source_doc=source_doc,
            byte_range=byte_range,
            summary=summary.strip()
        )
        # Replace full PTR tag with inline reference
        clean_text = clean_text.replace(match.group(0), f"[{ptr_id}]")

    return clean_text, recovery_map
```

## Expansion Flow

```
User clicks [ptr_03] in RecoveryPointerViewer
  OR
Follow-up query matches a trigger pattern
  │
  POST /api/expand/ptr_03 { compression_id: UUID }
  │
  1. Fetch compression_record from Supabase WHERE id = compression_id
  2. Get recovery_map["ptr_03"] → RecoveryPointer
  3. Fetch Supabase Storage file: storage.download(source_doc)
  4. Slice bytes: content[byte_range[0]:byte_range[1]]
  5. Decode → original passage text
  6. Append to expansion_log: {ptr_id, timestamp, context_query}
  7. Return { ptr_id, original_text, summary, trigger }
```

## Automatic Expansion Detection (V2)

In V2, after receiving the LLM response, analyze it for expansion signals:

```python
def detect_expansion_need(llm_response: str, recovery_map: dict) -> list[str]:
    """
    Check if the LLM response indicates it needed more detail.
    Signals: "I don't have enough detail...", "The logs would help...", etc.
    Match against trigger descriptions in recovery_map.
    """
    signals = []
    for ptr_id, pointer in recovery_map.items():
        if any(keyword in llm_response.lower() for keyword in extract_keywords(pointer.trigger)):
            signals.append(ptr_id)
    return signals
```

## Compression Quality Guarantee

After compression, always verify:
```python
assert compressed_token_count < original_token_count * 0.6  # at most 60% of original
assert len(recovery_map) > 0  # at least one pointer generated
```

If compression ratio is not achieved, flag in the `OptimizationMetrics.compression_note` field but do not fail the request.

## Token Counting

Use tiktoken for consistent token counting matching OpenAI's tokenizer:

```python
import tiktoken

encoder = tiktoken.get_encoding("cl100k_base")  # matches GPT-4 + Claude tokenization

def count_tokens(text: str) -> int:
    return len(encoder.encode(text))
```
