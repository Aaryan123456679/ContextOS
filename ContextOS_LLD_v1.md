# ContextOS — Low Level Design v1.0

**Author:** Aaryan Mahajan  
**Date:** June 2026  
**Status:** Pre-Development Reference  
**Companion:** ContextOS_HLD_v2.md

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Data Models & Schemas](#2-data-models--schemas)
3. [Ingestion Service](#3-ingestion-service)
4. [Query Understanding Engine](#4-query-understanding-engine)
5. [Retrieval Layer](#5-retrieval-layer)
6. [Context ROI Engine](#6-context-roi-engine)
7. [Dependency Graph Builder](#7-dependency-graph-builder)
8. [Contradiction Detector](#8-contradiction-detector)
9. [Token Budget Allocator (Fusion Engine)](#9-token-budget-allocator--fusion-engine)
10. [Recoverable Compression Engine](#10-recoverable-compression-engine)
11. [Model Context Adapter](#11-model-context-adapter)
12. [Speculative Prefetcher](#12-speculative-prefetcher)
13. [LLM Gateway](#13-llm-gateway)
14. [Validation Harness](#14-validation-harness)
15. [API Layer (FastAPI)](#15-api-layer-fastapi)
16. [Frontend Architecture (Next.js)](#16-frontend-architecture-nextjs)
17. [Storage Layer](#17-storage-layer)
18. [Inter-Service Communication](#18-inter-service-communication)
19. [Configuration & Environment](#19-configuration--environment)
20. [Error Handling Strategy](#20-error-handling-strategy)
21. [Deployment Specifics](#21-deployment-specifics)

---

## 1. Project Structure

```
contextos/
├── backend/
│   ├── main.py                          # FastAPI app entry point
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── chat.py                  # POST /api/chat
│   │   │   ├── optimize.py              # POST /api/optimize
│   │   │   ├── validate.py              # POST /api/validate
│   │   │   ├── upload.py                # POST /api/upload
│   │   │   ├── evaluate.py              # POST /api/evaluate
│   │   │   ├── metrics.py               # GET  /api/metrics
│   │   │   ├── history.py               # GET  /api/history
│   │   │   └── compression.py           # GET/POST /api/compression
│   │   ├── middleware/
│   │   │   ├── auth.py
│   │   │   ├── rate_limit.py
│   │   │   └── logging.py
│   │   └── dependencies.py
│   │
│   ├── core/
│   │   ├── config.py                    # Pydantic settings
│   │   ├── database.py                  # SQLAlchemy + Supabase
│   │   ├── redis_client.py              # Upstash Redis
│   │   ├── vector_store.py              # Qdrant client
│   │   └── exceptions.py
│   │
│   ├── models/
│   │   ├── db/
│   │   │   ├── user.py
│   │   │   ├── conversation.py
│   │   │   ├── chunk.py
│   │   │   ├── compression_record.py
│   │   │   └── validation_result.py
│   │   └── schemas/
│   │       ├── chat.py                  # Request/Response Pydantic schemas
│   │       ├── optimize.py
│   │       ├── chunk.py
│   │       ├── compression.py
│   │       └── validation.py
│   │
│   ├── services/
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── parser.py                # File → raw text
│   │   │   ├── chunker.py               # Text → chunks
│   │   │   ├── embedder.py              # Chunks → vectors
│   │   │   └── normalizer.py            # Chunk normalization
│   │   │
│   │   ├── retrieval/
│   │   │   ├── __init__.py
│   │   │   ├── semantic.py              # Qdrant dense retrieval
│   │   │   ├── keyword.py               # BM25 sparse retrieval
│   │   │   └── hybrid.py                # Reciprocal Rank Fusion
│   │   │
│   │   ├── query/
│   │   │   ├── __init__.py
│   │   │   ├── understanding.py         # Intent, entities, domain
│   │   │   └── classifier.py
│   │   │
│   │   ├── engines/
│   │   │   ├── __init__.py
│   │   │   ├── roi_engine.py            # Context ROI scoring
│   │   │   ├── dependency_graph.py      # Minimum knowledge frontier
│   │   │   ├── contradiction.py         # Contradiction detection
│   │   │   ├── token_budget.py          # Knapsack allocation
│   │   │   ├── fusion.py                # Multi-signal fusion
│   │   │   ├── compression.py           # Recoverable compression
│   │   │   ├── model_adapter.py         # Model context translation
│   │   │   └── prefetcher.py            # Speculative prefetch
│   │   │
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── gateway.py               # Unified LLM interface
│   │   │   ├── providers/
│   │   │   │   ├── openai_provider.py
│   │   │   │   ├── anthropic_provider.py
│   │   │   │   ├── gemini_provider.py
│   │   │   │   └── base.py
│   │   │   └── cost_tracker.py
│   │   │
│   │   └── validation/
│   │       ├── __init__.py
│   │       ├── harness.py               # Orchestrates eval
│   │       ├── metrics.py               # BERTScore, NLI, LLM judge
│   │       └── baseline.py              # Baseline (no optimization) path
│   │
│   └── utils/
│       ├── text.py
│       ├── crypto.py                    # API key encryption
│       └── async_helpers.py
│
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   │
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                     # Landing / redirect
│   │   ├── chat/
│   │   │   └── page.tsx
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   ├── evaluate/
│   │   │   └── page.tsx
│   │   └── api/                         # Next.js API routes (thin proxies)
│   │       └── [...]/route.ts
│   │
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── FileUploadZone.tsx
│   │   │   └── ModelSelector.tsx
│   │   ├── dashboard/
│   │   │   ├── MetricsPanel.tsx
│   │   │   ├── EngineBreakdown.tsx
│   │   │   ├── TokenDelta.tsx
│   │   │   └── CostDelta.tsx
│   │   ├── evaluate/
│   │   │   ├── SideBySide.tsx
│   │   │   ├── RecoveryPointerViewer.tsx
│   │   │   └── ValidationBadge.tsx
│   │   └── shared/
│   │       ├── Button.tsx
│   │       ├── Spinner.tsx
│   │       └── StatusBadge.tsx
│   │
│   ├── hooks/
│   │   ├── useChat.ts
│   │   ├── useOptimization.ts
│   │   └── useMetrics.ts
│   │
│   ├── lib/
│   │   ├── api.ts                       # Typed fetch wrappers
│   │   ├── types.ts
│   │   └── utils.ts
│   │
│   └── stores/
│       ├── chatStore.ts                 # Zustand store
│       └── settingsStore.ts
│
└── tests/
    ├── backend/
    │   ├── unit/
    │   ├── integration/
    │   └── e2e/
    └── frontend/
        ├── unit/
        ├── integration/
        └── e2e/
```

---

## 2. Data Models & Schemas

### 2.1 PostgreSQL Tables (Supabase)

#### `users`
```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    settings    JSONB DEFAULT '{}'       -- preferred model, budget, etc.
);
```

#### `api_keys`
```sql
CREATE TABLE api_keys (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    provider     TEXT NOT NULL,          -- 'openai' | 'anthropic' | 'gemini'
    key_hash     TEXT NOT NULL,          -- AES-256 encrypted
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
```

#### `conversations`
```sql
CREATE TABLE conversations (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    title        TEXT,
    model        TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
```

#### `messages`
```sql
CREATE TABLE messages (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role             TEXT NOT NULL,           -- 'user' | 'assistant' | 'system'
    content          TEXT NOT NULL,
    token_count      INTEGER,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
```

#### `documents`
```sql
CREATE TABLE documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    filename     TEXT NOT NULL,
    file_type    TEXT NOT NULL,
    storage_path TEXT,                   -- Supabase Storage path
    chunk_count  INTEGER,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
```

#### `chunks`
```sql
CREATE TABLE chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id  UUID REFERENCES documents(id) ON DELETE CASCADE,
    qdrant_id    TEXT NOT NULL,           -- ID in Qdrant vector store
    content      TEXT NOT NULL,
    token_count  INTEGER NOT NULL,
    chunk_index  INTEGER NOT NULL,
    metadata     JSONB DEFAULT '{}'
);
```

#### `optimization_runs`
```sql
CREATE TABLE optimization_runs (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id       UUID REFERENCES conversations(id),
    query                 TEXT NOT NULL,
    original_token_count  INTEGER,
    optimized_token_count INTEGER,
    token_reduction_pct   FLOAT,
    cost_original         FLOAT,
    cost_optimized        FLOAT,
    bert_score            FLOAT,
    quality_score         FLOAT,
    engine_breakdown      JSONB,          -- per-engine attribution JSON
    created_at            TIMESTAMPTZ DEFAULT NOW()
);
```

#### `compression_records`
```sql
CREATE TABLE compression_records (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id           UUID REFERENCES optimization_runs(id),
    compressed_text  TEXT NOT NULL,
    recovery_map     JSONB NOT NULL,      -- {ptr_id: {source, byte_range, summary, trigger}}
    expansion_log    JSONB DEFAULT '[]',  -- which pointers were expanded and when
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 2.2 Pydantic Schemas (API contracts)

```python
# models/schemas/chat.py

class ChatRequest(BaseModel):
    conversation_id: Optional[UUID]
    message: str
    model: str                  # "gpt-4o" | "claude-3-5-sonnet" | etc.
    document_ids: list[UUID] = []
    token_budget: int = 8192
    optimization_enabled: bool = True
    user_api_key: Optional[str]  # forwarded, never stored raw

class ChatResponse(BaseModel):
    message_id: UUID
    content: str
    optimization_run_id: Optional[UUID]
    metrics: Optional[OptimizationMetrics]

class OptimizationMetrics(BaseModel):
    original_tokens: int
    optimized_tokens: int
    token_reduction_pct: float
    cost_original: float
    cost_optimized: float
    bert_score: float
    quality_score: float
    engine_breakdown: EngineBreakdown

class EngineBreakdown(BaseModel):
    roi_engine: EngineContribution
    dependency_graph: EngineContribution
    compression: EngineContribution
    contradiction: EngineContribution

class EngineContribution(BaseModel):
    tokens_removed: int
    quality_delta: float
    enabled: bool
```

```python
# models/schemas/chunk.py

class Chunk(BaseModel):
    id: UUID
    content: str
    token_count: int
    document_id: UUID
    metadata: dict

class ScoredChunk(BaseModel):
    chunk: Chunk
    roi_score: float          # 0–1
    dependency_pruned: bool   # True = remove this chunk
    contradiction_risk: float # 0–1
    fusion_score: float       # final utility score
    allocated: bool           # True = included in final context
```

```python
# models/schemas/compression.py

class RecoveryPointer(BaseModel):
    ptr_id: str               # "ptr_01", "ptr_02", ...
    trigger: str              # "user asks for exact error"
    source_doc: str
    byte_range: tuple[int, int]
    summary: str

class CompressionResult(BaseModel):
    compression_id: UUID
    compressed_text: str
    original_token_count: int
    compressed_token_count: int
    recovery_map: dict[str, RecoveryPointer]
    expansion_triggers: list[str]
```

---

## 3. Ingestion Service

### 3.1 File Parser (`services/ingestion/parser.py`)

**Supported inputs and libraries:**

| Format | Library | Notes |
|---|---|---|
| PDF | `pdfplumber` | Preserves tables; fallback to `pymupdf` |
| DOCX | `python-docx` | Extracts text + headings |
| TXT / MD | Built-in | Direct read |
| CSV | `pandas` | Row-by-row text generation |
| URL | `httpx` + `trafilatura` | Scrape + clean HTML |

```python
class FileParser:
    def parse(self, file_path: str, file_type: str) -> str:
        """Returns raw text string from any supported file type."""
        ...

    async def parse_url(self, url: str) -> str:
        """Fetches and extracts main content from a URL."""
        ...
```

### 3.2 Chunker (`services/ingestion/chunker.py`)

**Strategy:** Recursive character-based splitting with overlap.

```python
class Chunker:
    DEFAULT_CHUNK_SIZE = 512    # tokens
    DEFAULT_OVERLAP = 64        # tokens

    def chunk(self, text: str, strategy: str = "recursive") -> list[ChunkRaw]:
        """
        Returns list of {content, start_char, end_char} dicts.
        Strategies: 'recursive' | 'sentence' | 'paragraph' | 'fixed'
        """
        ...
```

**Chunking parameters (configurable per document type):**
- Code files: fixed 200-token chunks, no overlap
- Long-form prose: sentence-aware, 512 tokens, 64 overlap
- CSV: row-group chunks, max 20 rows per chunk

### 3.3 Embedder (`services/ingestion/embedder.py`)

```python
class Embedder:
    MODEL = "text-embedding-3-small"   # OpenAI, 1536-dim
    BATCH_SIZE = 100                   # Render constraint — batch to avoid memory spikes

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Calls OpenAI embeddings API in batches of BATCH_SIZE."""
        ...

    async def embed_and_store(self, chunks: list[ChunkRaw], doc_id: UUID) -> list[UUID]:
        """Embeds + upserts into Qdrant. Returns list of Qdrant point IDs."""
        ...
```

**Qdrant collection schema:**
```python
vectors_config = VectorParams(
    size=1536,
    distance=Distance.COSINE
)
payload_schema = {
    "document_id": str,
    "chunk_index": int,
    "content": str,
    "token_count": int,
    "source_type": str,     # "pdf" | "txt" | "url" | ...
}
```

### 3.4 Full Ingestion Flow

```
POST /api/upload
  → FileParser.parse(file)          # raw text
  → Chunker.chunk(text)             # list[ChunkRaw]
  → Embedder.embed_and_store(...)   # upsert to Qdrant + write to chunks table
  → Return { document_id, chunk_count }
```

---

## 4. Query Understanding Engine

### `services/query/understanding.py`

```python
class QueryUnderstanding:
    def analyze(self, query: str) -> QueryAnalysis:
        """
        Returns structured analysis of the user query.
        Uses spaCy for NER, rule-based intent classifier.
        """
        ...

class QueryAnalysis(BaseModel):
    original_query: str
    intent: str               # "factual" | "procedural" | "comparison" | "debug" | "creative"
    entities: list[str]       # named entities
    domain: str               # "engineering" | "science" | "general" | ...
    depth: str                # "surface" | "intermediate" | "deep"
    constraints: list[str]    # extracted constraints (e.g., "in Python", "before 2020")
    reformulated_query: str   # cleaned, expanded query for retrieval
```

**Intent classification rules (V1 — rule-based):**

| Pattern | Intent |
|---|---|
| "why", "explain", "how does" | `factual` |
| "how to", "steps", "guide" | `procedural` |
| "vs", "compare", "difference" | `comparison` |
| "error", "crash", "failing", "bug" | `debug` |

---

## 5. Retrieval Layer

### 5.1 Semantic Retrieval (`services/retrieval/semantic.py`)

```python
class SemanticRetriever:
    TOP_K = 50   # retrieve top 50 candidates

    async def retrieve(self, query: str, collection: str, filters: dict = {}) -> list[ScoredChunk]:
        """
        Embeds query → cosine search in Qdrant → returns top-K chunks with scores.
        """
        query_vector = await self.embedder.embed(query)
        results = await self.qdrant.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=self.TOP_K,
            query_filter=Filter(**filters) if filters else None
        )
        return [ScoredChunk(chunk=..., roi_score=r.score) for r in results]
```

### 5.2 Keyword Retrieval (`services/retrieval/keyword.py`)

```python
class KeywordRetriever:
    """BM25 over in-memory index of chunks for the current document set."""

    def retrieve(self, query: str, chunks: list[Chunk], top_k: int = 30) -> list[ScoredChunk]:
        """Returns BM25-ranked chunks."""
        ...
```

### 5.3 Hybrid Fusion (`services/retrieval/hybrid.py`)

```python
class HybridRetriever:
    """Reciprocal Rank Fusion of semantic + keyword results."""

    RRF_K = 60   # standard RRF constant

    def fuse(self, semantic: list[ScoredChunk], keyword: list[ScoredChunk]) -> list[ScoredChunk]:
        """
        RRF score = Σ 1/(k + rank_i)
        Returns merged list sorted by RRF score, deduplicated by chunk ID.
        """
        ...
```

**Candidate pool target:** 200–500 chunks after fusion (before engine processing).

---

## 6. Context ROI Engine

### `services/engines/roi_engine.py`

**Purpose:** Score each candidate chunk by expected answer quality gain per token.

**MVP Implementation — two-stage:**

Stage 1: Embedding cosine similarity (already computed from retrieval)  
Stage 2: Cross-encoder reranking

```python
class ROIEngine:
    CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(self):
        from sentence_transformers import CrossEncoder
        self.cross_encoder = CrossEncoder(self.CROSS_ENCODER_MODEL)

    def score(self, query: str, chunks: list[Chunk]) -> list[tuple[Chunk, float]]:
        """
        Returns list of (chunk, roi_score) tuples.
        roi_score ∈ [0, 1], normalized across candidate set.
        """
        pairs = [(query, c.content) for c in chunks]
        raw_scores = self.cross_encoder.predict(pairs)
        normalized = self._normalize(raw_scores)
        return list(zip(chunks, normalized))

    def _normalize(self, scores: list[float]) -> list[float]:
        """Min-max normalize to [0, 1]."""
        ...
```

**Render constraint note:** CrossEncoder runs on CPU. For 200 chunks, inference takes ~2–5s on Render free tier. Consider batching and async processing.

**Engine attribution output:**
```python
class ROIAttribution(BaseModel):
    tokens_removed: int      # tokens from chunks with roi_score < threshold
    quality_delta: float     # estimated via validation harness feedback
    threshold_used: float    # dynamic threshold
```

---

## 7. Dependency Graph Builder

### `services/engines/dependency_graph.py`

**Purpose:** Build concept dependency graph, identify minimum knowledge frontier, prune redundant ancestor chunks.

```python
import spacy
import networkx as nx

class DependencyGraphBuilder:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def build(self, query: str, chunks: list[Chunk]) -> DependencyGraph:
        """
        1. Extract target concepts from query.
        2. Extract concepts from each chunk.
        3. Build directed graph where edges represent "requires understanding of".
        4. Find minimum frontier.
        5. Return pruning mask.
        """
        target_concepts = self._extract_concepts(query)
        graph = nx.DiGraph()

        for chunk in chunks:
            chunk_concepts = self._extract_concepts(chunk.content)
            for concept in chunk_concepts:
                graph.add_node(concept, chunk_ids=[chunk.id])
            # add edges based on co-occurrence and ordering heuristics
            self._add_dependency_edges(graph, chunk_concepts)

        frontier = self._find_minimum_frontier(graph, target_concepts)
        pruning_mask = {c.id: c not in frontier for c in chunks}
        return DependencyGraph(graph=graph, frontier=frontier, pruning_mask=pruning_mask)

    def _extract_concepts(self, text: str) -> list[str]:
        """spaCy NER + noun chunk extraction."""
        doc = self.nlp(text[:10000])   # cap at 10k chars for speed
        return [ent.text.lower() for ent in doc.ents] + \
               [chunk.root.lemma_ for chunk in doc.noun_chunks]

    def _find_minimum_frontier(self, graph: nx.DiGraph, targets: list[str]) -> set[str]:
        """
        BFS from target nodes backward through dependency edges.
        Nodes at depth 1 = frontier. Nodes at depth 2+ = redundant ancestors.
        """
        frontier = set()
        for target in targets:
            if target in graph:
                ancestors = nx.ancestors(graph, target)
                direct_predecessors = set(graph.predecessors(target))
                frontier.update(direct_predecessors)
                # everything else in ancestors is prunable
        return frontier
```

**Engine attribution output:**
```python
class DependencyAttribution(BaseModel):
    tokens_removed: int
    pruned_chunk_count: int
    frontier_concept_count: int
    quality_delta: float
```

---

## 8. Contradiction Detector

### `services/engines/contradiction.py`

**Purpose:** Detect factual contradictions between chunks before they reach the LLM.

```python
from sentence_transformers import CrossEncoder

class ContradictionDetector:
    NLI_MODEL = "cross-encoder/nli-deberta-v3-small"
    CONTRADICTION_THRESHOLD = 0.7

    def __init__(self):
        self.nli_model = CrossEncoder(self.NLI_MODEL, num_labels=3)
        # Labels: 0=contradiction, 1=neutral, 2=entailment

    def detect(self, chunks: list[Chunk]) -> list[ContradictionFlag]:
        """
        Pairwise NLI check on top-20 chunks.
        Returns list of flagged contradictions with resolution.
        """
        candidates = chunks[:20]
        flags = []

        for i, c1 in enumerate(candidates):
            for c2 in candidates[i+1:]:
                score = self.nli_model.predict([(c1.content[:512], c2.content[:512])])
                if score[0][0] > self.CONTRADICTION_THRESHOLD:  # contradiction label
                    resolution = self._resolve(c1, c2)
                    flags.append(ContradictionFlag(
                        chunk_a_id=c1.id,
                        chunk_b_id=c2.id,
                        confidence=float(score[0][0]),
                        resolution=resolution,
                        keep_chunk_id=resolution.keep_id
                    ))
        return flags

    def _resolve(self, c1: Chunk, c2: Chunk) -> ContradictionResolution:
        """
        Resolution priority:
        1. More recent (if timestamps in metadata)
        2. Higher source authority score
        3. Surface both with explicit flag
        """
        ...
```

```python
class ContradictionFlag(BaseModel):
    chunk_a_id: UUID
    chunk_b_id: UUID
    confidence: float
    resolution: str      # "keep_a" | "keep_b" | "surface_both"
    keep_chunk_id: Optional[UUID]
```

---

## 9. Token Budget Allocator & Fusion Engine

### `services/engines/token_budget.py`

**Purpose:** Select final context set under token budget using greedy 0/1 knapsack.

```python
class TokenBudgetAllocator:
    def allocate(self, chunks: list[ScoredChunk], budget: int) -> AllocationResult:
        """
        Greedy knapsack: sort by (fusion_score / token_count) DESC.
        Select chunks until budget exhausted.
        O(n log n)
        """
        sorted_chunks = sorted(
            chunks,
            key=lambda c: c.fusion_score / max(c.chunk.token_count, 1),
            reverse=True
        )
        selected = []
        remaining = budget

        for sc in sorted_chunks:
            if sc.chunk.token_count <= remaining:
                selected.append(sc)
                remaining -= sc.chunk.token_count

        return AllocationResult(
            selected=selected,
            total_tokens=budget - remaining,
            budget=budget,
            utilization_pct=(budget - remaining) / budget * 100
        )
```

### `services/engines/fusion.py`

**Purpose:** Combine all engine signals into a single utility score per chunk.

```python
class FusionEngine:
    # Default weights — equal initialization
    WEIGHTS = {
        "roi": 0.35,
        "dependency_redundancy": -0.20,   # negative: redundancy penalizes
        "contradiction_risk": -0.20,       # negative
        "source_reliability": 0.15,
        "recency": 0.10,
    }

    def score(self, chunk: Chunk, signals: ChunkSignals) -> float:
        """
        Utility(chunk) =
          α·roi + β·entropy_reduction + γ·source_reliability
          − δ·contradiction_risk − ε·dependency_redundancy
        """
        score = (
            self.WEIGHTS["roi"] * signals.roi_score
            + self.WEIGHTS["dependency_redundancy"] * (1 if signals.dependency_pruned else 0)
            + self.WEIGHTS["contradiction_risk"] * signals.contradiction_risk
            + self.WEIGHTS["source_reliability"] * signals.source_reliability
        )
        return max(0.0, min(1.0, score))

class ChunkSignals(BaseModel):
    roi_score: float
    dependency_pruned: bool
    contradiction_risk: float
    source_reliability: float = 0.5   # default neutral
```

---

## 10. Recoverable Compression Engine

### `services/engines/compression.py`

**Purpose:** Compress selected context with recovery pointers for surgical expansion.

```python
class RecoverableCompressor:
    COMPRESSION_MODEL = "claude-haiku-3"   # or "gpt-4o-mini" — cheapest capable model
    TARGET_COMPRESSION_RATIO = 0.4         # compress to 40% of original

    async def compress(self, chunks: list[Chunk], query: str) -> CompressionResult:
        """
        1. Concatenate allocated chunks with metadata headers.
        2. Call compression model with structured prompt.
        3. Parse recovery pointers from model output.
        4. Store compression record in DB.
        """
        concatenated = self._concatenate(chunks)
        prompt = self._build_compression_prompt(concatenated, query)
        raw_output = await self.llm.complete(prompt, model=self.COMPRESSION_MODEL)
        result = self._parse_compression_output(raw_output, chunks)
        return result

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

    def _parse_compression_output(self, raw: str, original_chunks: list[Chunk]) -> CompressionResult:
        """Regex-parse [PTR:...] tags from model output into RecoveryPointer objects."""
        import re
        ptr_pattern = r'\[PTR:(\w+)\|trigger:([^|]+)\|source:([^|]+)\|summary:([^\]]+)\]'
        pointers = {}
        clean_text = raw

        for match in re.finditer(ptr_pattern, raw):
            ptr_id, trigger, source, summary = match.groups()
            # parse source:doc.txt:100-200
            source_parts = source.rsplit(":", 1)
            doc_name = source_parts[0]
            byte_range = tuple(map(int, source_parts[1].split("-"))) if len(source_parts) > 1 else (0, 0)

            pointers[ptr_id] = RecoveryPointer(
                ptr_id=ptr_id,
                trigger=trigger,
                source_doc=doc_name,
                byte_range=byte_range,
                summary=summary
            )
            clean_text = clean_text.replace(match.group(0), f"[{ptr_id}]")

        return CompressionResult(
            compressed_text=clean_text,
            recovery_map=pointers,
            original_token_count=sum(c.token_count for c in original_chunks),
            compressed_token_count=self._count_tokens(clean_text)
        )
```

### Pointer Expansion

```python
async def expand_pointer(ptr_id: str, compression_id: UUID) -> str:
    """
    POST /api/expand/{ptr_id}
    Fetch original passage from storage and return full text.
    """
    record = await db.get_compression_record(compression_id)
    pointer = record.recovery_map[ptr_id]
    original_text = await storage.read_bytes(pointer.source_doc, pointer.byte_range)
    # log expansion event
    await db.log_expansion(compression_id, ptr_id)
    return original_text
```

---

## 11. Model Context Adapter

### `services/engines/model_adapter.py`

**Purpose:** Restructure optimized context for the target LLM's known preferences.

```python
class ModelContextAdapter:
    def adapt(self, context: str, model: str, query: str) -> str:
        adapter = self._get_adapter(model)
        return adapter.format(context, query)

    def _get_adapter(self, model: str) -> BaseAdapter:
        if "claude" in model:
            return ClaudeAdapter()
        elif "gpt" in model:
            return GPTAdapter()
        elif "gemini" in model:
            return GeminiAdapter()
        return DefaultAdapter()

class ClaudeAdapter(BaseAdapter):
    def format(self, context: str, query: str) -> str:
        """Wrap in XML tags — Claude processes structured XML context better."""
        return f"""<context>
{context}
</context>

<query>{query}</query>"""

class GPTAdapter(BaseAdapter):
    def format(self, context: str, query: str) -> str:
        """Prose-first, role-framed. GPT-4 handles natural prose well."""
        return f"""You are answering based on the following retrieved information:

{context}

Question: {query}"""

class GeminiAdapter(BaseAdapter):
    def format(self, context: str, query: str) -> str:
        """Citation-dense format — Gemini grounding works best with explicit citations."""
        return f"""[RETRIEVED CONTEXT]
{context}
[END CONTEXT]

Based on the above retrieved context, answer: {query}"""
```

---

## 12. Speculative Prefetcher

### `services/engines/prefetcher.py` (V2 — deferred from MVP)

```python
class SpeculativePrefetcher:
    N_PREDICTIONS = 3
    CACHE_TTL = 600   # 10 minutes in Redis

    async def prefetch(self, query: str, conversation_history: list[str]) -> None:
        """
        Runs entirely in background (asyncio.create_task).
        Does NOT block the response path.
        """
        predicted_queries = await self._predict_follow_ups(query, conversation_history)
        for pq in predicted_queries[:self.N_PREDICTIONS]:
            cache_key = f"prefetch:{hash(pq)}"
            if not await self.redis.exists(cache_key):
                optimized = await self.optimization_pipeline.run(pq)
                await self.redis.setex(cache_key, self.CACHE_TTL, optimized.json())

    async def _predict_follow_ups(self, query: str, history: list[str]) -> list[str]:
        """V1: Rule-based expansion templates. V2: LLM call."""
        # V1 rule-based
        templates = {
            "explain": ["risks of {topic}", "{topic} vs alternatives", "how {topic} works internally"],
            "debug": ["how to fix {error}", "{error} in production", "prevent {error}"],
        }
        ...
```

---

## 13. LLM Gateway

### `services/llm/gateway.py`

**Purpose:** Single interface to all LLM providers. Handles key injection, retry, cost tracking.

```python
class LLMGateway:
    async def complete(
        self,
        prompt: str,
        model: str,
        api_key: str,
        max_tokens: int = 2048,
        temperature: float = 0.0,
        stream: bool = False
    ) -> LLMResponse:
        provider = self._get_provider(model)
        try:
            response = await provider.complete(prompt, model, api_key, max_tokens, temperature, stream)
            await self.cost_tracker.record(model, response.usage)
            return response
        except RateLimitError:
            await asyncio.sleep(2)
            return await self.complete(prompt, model, api_key, max_tokens, temperature, stream)
        except Exception as e:
            raise LLMProviderError(f"Provider {model} failed: {e}")

    def _get_provider(self, model: str) -> BaseProvider:
        if "gpt" in model or "o1" in model:
            return OpenAIProvider()
        elif "claude" in model:
            return AnthropicProvider()
        elif "gemini" in model:
            return GeminiProvider()
        raise ValueError(f"Unknown model: {model}")
```

### Provider Implementations

```python
# providers/openai_provider.py
class OpenAIProvider(BaseProvider):
    async def complete(self, prompt, model, api_key, max_tokens, temperature, stream) -> LLMResponse:
        import openai
        client = openai.AsyncOpenAI(api_key=api_key)
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream
        )
        return LLMResponse(
            content=resp.choices[0].message.content,
            usage=TokenUsage(
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens
            ),
            model=model
        )
```

```python
class LLMResponse(BaseModel):
    content: str
    usage: TokenUsage
    model: str
    latency_ms: Optional[float]

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int

    @property
    def total(self): return self.prompt_tokens + self.completion_tokens
```

### Cost Table

```python
# services/llm/cost_tracker.py
COST_PER_1K_TOKENS = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "claude-haiku-3": {"input": 0.00025, "output": 0.00125},
    "gemini-1.5-flash": {"input": 0.00035, "output": 0.00105},
}
```

---

## 14. Validation Harness

### `services/validation/harness.py`

**Purpose:** Prove that optimized context produces equal-or-better answers at lower cost.

```python
class ValidationHarness:
    BERT_SCORE_THRESHOLD = 0.90
    QUALITY_THRESHOLD_DELTA = 0.0    # optimized must be >= baseline

    async def evaluate(
        self,
        query: str,
        baseline_context: str,
        optimized_context: str,
        model: str,
        api_key: str
    ) -> ValidationResult:
        # Run both paths
        baseline_response = await self.llm.complete(f"{baseline_context}\n\n{query}", model, api_key)
        optimized_response = await self.llm.complete(f"{optimized_context}\n\n{query}", model, api_key)

        # Metrics
        bert = self._bert_score(baseline_response.content, optimized_response.content)
        quality = await self._llm_judge(query, baseline_response.content, optimized_response.content, api_key)
        faithfulness = self._faithfulness(optimized_response.content, optimized_context)

        return ValidationResult(
            passed=bert.f1 >= self.BERT_SCORE_THRESHOLD and quality.delta >= self.QUALITY_THRESHOLD_DELTA,
            bert_score_f1=bert.f1,
            quality_delta=quality.delta,
            faithfulness=faithfulness,
            token_reduction_pct=self._token_reduction(baseline_context, optimized_context),
            cost_reduction_pct=self._cost_reduction(baseline_response.usage, optimized_response.usage, model)
        )

    def _bert_score(self, reference: str, candidate: str) -> BERTScoreResult:
        from bert_score import score as bert_score
        P, R, F1 = bert_score([candidate], [reference], lang="en")
        return BERTScoreResult(precision=float(P), recall=float(R), f1=float(F1))

    async def _llm_judge(self, query: str, baseline: str, optimized: str, api_key: str) -> QualityJudge:
        judge_prompt = f"""You are a quality evaluator. Rate both responses on a 1-10 scale.

Query: {query}

Response A (Baseline):
{baseline}

Response B (Optimized):
{optimized}

Output JSON: {{"score_a": X, "score_b": Y, "reasoning": "..."}}"""
        result = await self.llm.complete(judge_prompt, "gpt-4o-mini", api_key)
        parsed = json.loads(result.content)
        return QualityJudge(
            baseline_score=parsed["score_a"],
            optimized_score=parsed["score_b"],
            delta=parsed["score_b"] - parsed["score_a"]
        )
```

---

## 15. API Layer (FastAPI)

### `main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import chat, optimize, validate, upload, evaluate, metrics, history, compression

app = FastAPI(title="ContextOS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://contextos.vercel.app", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(optimize.router, prefix="/api")
app.include_router(validate.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(evaluate.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(compression.router, prefix="/api")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Route Signatures

```python
# api/routes/chat.py
@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db=Depends(get_db)):
    """
    Full pipeline:
    1. QueryUnderstanding.analyze(req.message)
    2. HybridRetriever.retrieve(query, doc_ids)
    3. ROIEngine.score(query, chunks)
    4. DependencyGraphBuilder.build(query, chunks)
    5. ContradictionDetector.detect(chunks)
    6. FusionEngine.score(chunks, signals)
    7. TokenBudgetAllocator.allocate(chunks, budget)
    8. RecoverableCompressor.compress(selected_chunks, query)
    9. ModelContextAdapter.adapt(compressed, model)
    10. LLMGateway.complete(adapted_context, model, api_key)
    11. ValidationHarness.evaluate(...) [async, post-response]
    12. Store optimization_run record
    """
```

```python
# api/routes/upload.py
@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile, user_id: UUID, db=Depends(get_db)):
    """Parse → Chunk → Embed → Store"""
```

```python
# api/routes/compression.py
@router.get("/compression/{compression_id}", response_model=CompressionRecord)
async def get_compression(compression_id: UUID, db=Depends(get_db)):
    """Return compressed text + recovery map for UI viewer."""

@router.post("/expand/{ptr_id}", response_model=ExpansionResult)
async def expand_pointer(ptr_id: str, compression_id: UUID, db=Depends(get_db)):
    """Expand a recovery pointer — return original passage."""
```

---

## 16. Frontend Architecture (Next.js)

### State Management

```typescript
// stores/chatStore.ts — Zustand
interface ChatStore {
  conversations: Conversation[]
  activeConversation: Conversation | null
  messages: Message[]
  optimizationMetrics: OptimizationMetrics | null
  isLoading: boolean

  sendMessage: (content: string, documentIds: string[]) => Promise<void>
  setActiveConversation: (id: string) => void
  clearMetrics: () => void
}
```

### Key Component Props

```typescript
// components/dashboard/MetricsPanel.tsx
interface MetricsPanelProps {
  metrics: OptimizationMetrics
  isLoading: boolean
}

// components/evaluate/SideBySide.tsx
interface SideBySideProps {
  baselineResponse: string
  optimizedResponse: string
  validationResult: ValidationResult
}

// components/evaluate/RecoveryPointerViewer.tsx
interface RecoveryPointerViewerProps {
  compressionId: string
  compressedText: string
  recoveryMap: Record<string, RecoveryPointer>
  onExpand: (ptrId: string) => Promise<string>
}
```

### API Client

```typescript
// lib/api.ts
const BASE_URL = process.env.NEXT_PUBLIC_API_URL   // Render backend URL

export const api = {
  chat: (req: ChatRequest): Promise<ChatResponse> =>
    post('/api/chat', req),

  upload: (file: File, userId: string): Promise<UploadResponse> => {
    const form = new FormData()
    form.append('file', file)
    form.append('user_id', userId)
    return postForm('/api/upload', form)
  },

  expandPointer: (ptrId: string, compressionId: string): Promise<string> =>
    post(`/api/expand/${ptrId}`, { compression_id: compressionId }),

  getMetrics: (): Promise<AggregateMetrics> =>
    get('/api/metrics'),
}
```

### TypeScript Types

```typescript
// lib/types.ts
interface OptimizationMetrics {
  originalTokens: number
  optimizedTokens: number
  tokenReductionPct: number
  costOriginal: number
  costOptimized: number
  bertScore: number
  qualityScore: number
  engineBreakdown: EngineBreakdown
}

interface EngineBreakdown {
  roiEngine: EngineContribution
  dependencyGraph: EngineContribution
  compression: EngineContribution
  contradiction: EngineContribution
}

interface EngineContribution {
  tokensRemoved: number
  qualityDelta: number
  enabled: boolean
}

interface RecoveryPointer {
  ptrId: string
  trigger: string
  sourceDoc: string
  byteRange: [number, number]
  summary: string
}

interface ValidationResult {
  passed: boolean
  bertScoreF1: number
  qualityDelta: number
  faithfulness: number
  tokenReductionPct: number
  costReductionPct: number
}
```

---

## 17. Storage Layer

### Qdrant Setup

```python
# core/vector_store.py
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance

QDRANT_URL = settings.QDRANT_URL       # Qdrant Cloud free cluster URL
QDRANT_API_KEY = settings.QDRANT_KEY

client = AsyncQdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

COLLECTION_NAME = "contextos_chunks"

async def ensure_collection():
    existing = await client.get_collections()
    if COLLECTION_NAME not in [c.name for c in existing.collections]:
        await client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )
```

### Redis (Upstash)

```python
# core/redis_client.py
import redis.asyncio as redis

# Upstash Redis REST URL — no persistent connection needed
client = redis.from_url(settings.UPSTASH_REDIS_URL, decode_responses=True)

async def cache_get(key: str) -> Optional[str]:
    return await client.get(key)

async def cache_set(key: str, value: str, ttl: int = 600):
    await client.setex(key, ttl, value)
```

### Supabase Storage (uploaded files)

```python
from supabase import create_client

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

async def upload_file(bucket: str, path: str, content: bytes) -> str:
    """Returns public URL of uploaded file."""
    supabase.storage.from_(bucket).upload(path, content)
    return supabase.storage.from_(bucket).get_public_url(path)
```

---

## 18. Inter-Service Communication

All services are in-process (single FastAPI app on Render). Communication is direct Python function calls — no internal HTTP.

**Optimization pipeline call chain:**

```
POST /api/chat
  │
  ├── QueryUnderstanding.analyze(query)
  │     └── returns: QueryAnalysis
  │
  ├── HybridRetriever.retrieve(analysis.reformulated_query, doc_ids)
  │     ├── SemanticRetriever.retrieve()
  │     ├── KeywordRetriever.retrieve()
  │     └── HybridRetriever.fuse()  → candidate_pool: list[ScoredChunk]
  │
  ├── [parallel] ROIEngine.score(query, candidate_pool)
  ├── [parallel] DependencyGraphBuilder.build(query, candidate_pool)
  ├── [parallel] ContradictionDetector.detect(candidate_pool[:20])
  │
  ├── FusionEngine.score(chunks, all_signals)
  ├── TokenBudgetAllocator.allocate(scored_chunks, budget)
  │
  ├── RecoverableCompressor.compress(allocated_chunks, query)
  ├── ModelContextAdapter.adapt(compressed_text, model)
  │
  ├── LLMGateway.complete(adapted_context, model, api_key)
  │     └── returns: LLMResponse
  │
  ├── [background task] ValidationHarness.evaluate(...)
  ├── [background task] SpeculativePrefetcher.prefetch(query)
  │
  └── Return ChatResponse with metrics
```

**Parallel engine execution:**

```python
roi_task = asyncio.create_task(roi_engine.score(query, chunks))
dep_task = asyncio.create_task(dep_graph.build(query, chunks))
contra_task = asyncio.create_task(contradiction.detect(chunks))

roi_result, dep_result, contra_result = await asyncio.gather(roi_task, dep_task, contra_task)
```

---

## 19. Configuration & Environment

### `core/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    SUPABASE_URL: str
    SUPABASE_KEY: str
    DATABASE_URL: str              # Supabase PostgreSQL connection string

    # Vector Store
    QDRANT_URL: str
    QDRANT_KEY: str

    # Cache
    UPSTASH_REDIS_URL: str

    # Encryption
    ENCRYPTION_KEY: str            # 32-byte AES key for API key encryption

    # App
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    RENDER_HEALTHCHECK_TOKEN: str  # for /health auth

    class Config:
        env_file = ".env"

settings = Settings()
```

### `.env.example`

```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
DATABASE_URL=postgresql://postgres:xxx@db.xxx.supabase.co:5432/postgres
QDRANT_URL=https://xxx.qdrant.io:6333
QDRANT_KEY=xxx
UPSTASH_REDIS_URL=rediss://default:xxx@xxx.upstash.io:6380
ENCRYPTION_KEY=<32-random-bytes-base64>
ENVIRONMENT=development
```

### `frontend/.env.example`

```
NEXT_PUBLIC_API_URL=https://contextos.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

---

## 20. Error Handling Strategy

### Backend

```python
# core/exceptions.py
class ContextOSError(Exception): pass
class LLMProviderError(ContextOSError): pass
class VectorStoreError(ContextOSError): pass
class CompressionError(ContextOSError): pass
class ValidationError(ContextOSError): pass

# Global exception handler in main.py
@app.exception_handler(LLMProviderError)
async def llm_error_handler(request, exc):
    return JSONResponse(status_code=503, content={"error": "LLM provider unavailable", "detail": str(exc)})

@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(status_code=422, content={"error": str(exc)})
```

**Engine failure fallback:** If any engine fails at runtime, it is skipped and the pipeline continues with remaining signals. The engine is flagged as `enabled: false` in the response attribution.

```python
async def safe_engine_run(engine_coro) -> Optional[EngineResult]:
    try:
        return await engine_coro
    except Exception as e:
        logger.error(f"Engine failed: {e}")
        return None  # pipeline continues without this engine's signal
```

### Frontend

```typescript
// lib/api.ts
async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new APIError(err.error, res.status)
  }
  return res.json()
}
```

---

## 21. Deployment Specifics

### Render (Backend)

- **Instance type:** Free (512MB RAM, 0.1 CPU)
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Health check:** `GET /health` (keep-alive ping every 14min to prevent cold start)
- **Memory constraints:**
  - CrossEncoder model (~100MB): loaded once at startup
  - spaCy `en_core_web_sm` (~50MB): loaded once at startup
  - Total model footprint: ~200MB — within 512MB limit
  - Never load `en_core_web_lg` or any GPU model

### Vercel (Frontend)

- **Framework:** Next.js 15
- **Build:** `next build`
- **Environment variables:** Set in Vercel dashboard
- **Edge functions:** Not used — all computation on backend
- **Image optimization:** Vercel built-in

### Render Cold Start Mitigation

```python
# Background healthcheck ping service (separate tiny cron or UptimeRobot)
# Pings GET /health every 14 minutes to keep Render instance warm
```

### Package constraints

```toml
# pyproject.toml — keep dependencies minimal for 512MB
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.30"}
pydantic = "^2.8"
pydantic-settings = "^2.4"
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
asyncpg = "^0.29"
qdrant-client = "^1.11"
sentence-transformers = "^3.3"    # CrossEncoder + NLI — biggest dep
openai = "^1.54"
anthropic = "^0.37"
spacy = "^3.8"
pdfplumber = "^0.11"
python-docx = "^1.1"
trafilatura = "^1.12"
bert-score = "^0.3"
redis = {extras = ["asyncio"], version = "^5.1"}
supabase = "^2.9"
httpx = "^0.27"
python-multipart = "^0.0.12"
```

---

*ContextOS LLD v1.0 — June 2026*
