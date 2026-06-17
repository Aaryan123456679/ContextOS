# Agent.md — ContextOS Project Scaffold Instructions

**Purpose:** This file gives an AI agent (Gemini, Claude, or any capable LLM) everything needed to scaffold the ContextOS project from zero. Follow every section in order. Do not skip steps.

**Reference files (read these first):**
- `ContextOS_HLD_v2.md` — architectural vision and system design
- `ContextOS_LLD_v1.md` — data models, service signatures, schemas, deployment constraints

---

## 0. Before You Start

Read these files completely before generating any code:
1. `ContextOS_HLD_v2.md`
2. `ContextOS_LLD_v1.md`

If you have not read both, stop and read them now.

---

## 1. What You Are Building

**ContextOS** is a context intelligence layer for LLMs. It sits between the user and any LLM provider, optimizing what goes into the context window to maximize answer quality per token.

It is not a chatbot. It is not a RAG library wrapper. It is an optimization and evaluation system.

**Core idea:** instead of sending all retrieved context to an LLM, ContextOS scores each chunk by expected answer quality gain, builds a dependency graph to prune redundant ancestors, detects contradictions, allocates a token budget via knapsack optimization, compresses with recovery pointers, and validates the result against a baseline. Every optimization is measured.

---

## 2. Tech Stack (Non-Negotiable)

| Layer | Technology | Reason |
|---|---|---|
| Backend | Python 3.11 + FastAPI + async | Free tier compatible, fast to build |
| Frontend | Next.js 15 + TypeScript + TailwindCSS | Specified in HLD |
| Vector DB | Qdrant Cloud (free 1GB) | Free, production-grade |
| Relational DB | Supabase PostgreSQL (free 500MB) | Free, includes Auth and Storage |
| Cache | Upstash Redis (serverless free) | Stateless, compatible with Render |
| Embeddings | OpenAI `text-embedding-3-small` | Cheapest capable embedding model |
| Compression LLM | Claude Haiku / GPT-4o-mini | Cheapest capable generation model |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Runs on CPU, fits in 512MB |
| NLI | `cross-encoder/nli-deberta-v3-small` | Contradiction detection, CPU-only |
| NLP | spaCy `en_core_web_sm` | Entity extraction, ~50MB |
| Eval | `bert-score` library | BERTScore F1 metric |
| Deployment | Render (backend) + Vercel (frontend) | Both free tier |

**Do NOT use:**
- Any self-hosted LLM (no VRAM on Render free tier)
- `en_core_web_lg` or any large spaCy model
- GPU-dependent libraries
- Docker Compose for production (Render doesn't support it on free tier)

---

## 3. Project Initialization Order

Execute in this exact order. Each step must succeed before the next.

### Step 1 — Repository Structure

Create the following top-level structure:

```
contextos/
├── backend/
├── frontend/
├── tests/
│   ├── backend/
│   └── frontend/
├── docs/
├── .gitignore
└── README.md
```

### Step 2 — Backend Bootstrap

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn[standard] pydantic pydantic-settings
```

Create `main.py` with a minimal FastAPI app and `/health` endpoint first. Verify it runs:

```bash
uvicorn main:app --reload
curl http://localhost:8000/health  # must return {"status": "ok"}
```

Do not proceed until health check passes.

### Step 3 — Database Setup (Supabase)

Create the following tables in Supabase SQL editor, in this order (respects FK dependencies):

1. `users`
2. `api_keys`
3. `conversations`
4. `messages`
5. `documents`
6. `chunks`
7. `optimization_runs`
8. `compression_records`

Full SQL DDL is in `ContextOS_LLD_v1.md` section 2.1.

After creating tables, verify connectivity:

```python
from supabase import create_client
client = create_client(SUPABASE_URL, SUPABASE_KEY)
print(client.table("users").select("*").limit(1).execute())
```

### Step 4 — Qdrant Setup

```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY)
client.create_collection(
    "contextos_chunks",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)
```

Verify the collection was created in Qdrant Cloud dashboard.

### Step 5 — Environment Configuration

Create `backend/.env` from `backend/.env.example`. Fill in all values:
- `SUPABASE_URL`, `SUPABASE_KEY`, `DATABASE_URL`
- `QDRANT_URL`, `QDRANT_KEY`
- `UPSTASH_REDIS_URL`
- `ENCRYPTION_KEY` — generate with: `python -c "import secrets; print(secrets.token_hex(32))"`

### Step 6 — Frontend Bootstrap

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --src-dir=false
```

Verify it runs:
```bash
npm run dev
# visit http://localhost:3000
```

---

## 4. Backend — Build Order

Build in this order. Each service depends on the previous.

### 4.1 Core Infrastructure (build first)

Files to create:
- `core/config.py` — Pydantic Settings, loads from .env
- `core/database.py` — SQLAlchemy async engine + session factory
- `core/vector_store.py` — Qdrant async client + ensure_collection()
- `core/redis_client.py` — Upstash Redis async client
- `core/exceptions.py` — Custom exception hierarchy

Test: import each module, no errors.

### 4.2 Data Models

Files to create:
- `models/db/*.py` — SQLAlchemy ORM models (match DDL in LLD section 2.1)
- `models/schemas/*.py` — Pydantic schemas (match LLD section 2.2 exactly)

All Pydantic models must use `model_config = ConfigDict(from_attributes=True)` for ORM compatibility.

### 4.3 Ingestion Service

Files to create in order:
1. `services/ingestion/parser.py` — FileParser class
2. `services/ingestion/chunker.py` — Chunker class  
3. `services/ingestion/embedder.py` — Embedder class (batches of 100)
4. `services/ingestion/normalizer.py` — token counting, metadata normalization

Install dependencies:
```bash
pip install pdfplumber python-docx trafilatura openai tiktoken
```

Test each class independently before wiring the API route.

### 4.4 Retrieval Layer

Files to create:
1. `services/retrieval/semantic.py` — SemanticRetriever (Qdrant dense search)
2. `services/retrieval/keyword.py` — KeywordRetriever (rank_bm25 library)
3. `services/retrieval/hybrid.py` — HybridRetriever (RRF fusion)

```bash
pip install rank-bm25
```

### 4.5 Query Understanding

File to create: `services/query/understanding.py`

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

### 4.6 Engines (build in this order)

Each engine is independent — build and test each before moving on:

1. **ROI Engine** (`services/engines/roi_engine.py`)
   ```bash
   pip install sentence-transformers
   ```
   Test: instantiate CrossEncoder, run `.predict()` on sample pairs.

2. **Dependency Graph** (`services/engines/dependency_graph.py`)
   ```bash
   pip install networkx
   ```
   Test: build a small graph, verify frontier detection.

3. **Contradiction Detector** (`services/engines/contradiction.py`)
   Uses `sentence-transformers` (already installed). Test: detect obvious contradiction between two sentences.

4. **Token Budget Allocator** (`services/engines/token_budget.py`)
   Pure Python, no new dependencies. Test: greedy knapsack with known inputs.

5. **Fusion Engine** (`services/engines/fusion.py`)
   Pure Python. Test: scoring formula produces values in [0, 1].

6. **Recoverable Compressor** (`services/engines/compression.py`)
   Requires LLM Gateway (build that first — see 4.7).

7. **Model Context Adapter** (`services/engines/model_adapter.py`)
   Pure Python, no dependencies. Test: format same context for claude/gpt/gemini, verify different output structure.

### 4.7 LLM Gateway

Files to create:
- `services/llm/gateway.py`
- `services/llm/providers/base.py`
- `services/llm/providers/openai_provider.py`
- `services/llm/providers/anthropic_provider.py`
- `services/llm/providers/gemini_provider.py`
- `services/llm/cost_tracker.py`

```bash
pip install openai anthropic google-generativeai
```

Test: make a live call to each provider with a test API key. Verify `LLMResponse` is returned correctly.

### 4.8 Validation Harness

Files to create:
- `services/validation/harness.py`
- `services/validation/metrics.py`
- `services/validation/baseline.py`

```bash
pip install bert-score
```

Test: run `ValidationHarness.evaluate()` with two identical texts. Expect BERTScore F1 = 1.0.

### 4.9 API Routes

Wire all services into FastAPI routes. Build in this order:

1. `POST /api/upload` — ingestion pipeline
2. `POST /api/optimize` — standalone optimization (no LLM call)
3. `POST /api/chat` — full pipeline
4. `GET /api/compression/{id}` — fetch compression record
5. `POST /api/expand/{ptr_id}` — expand pointer
6. `POST /api/validate` — standalone validation
7. `POST /api/evaluate` — side-by-side eval
8. `GET /api/metrics` — aggregate metrics
9. `GET /api/history` — conversation history

Add middleware last:
- `api/middleware/auth.py` — API key validation
- `api/middleware/rate_limit.py` — simple in-memory rate limiter (slowapi)
- `api/middleware/logging.py` — request/response logging

---

## 5. Frontend — Build Order

### 5.1 Foundation

1. Install dependencies:
   ```bash
   npm install zustand @tanstack/react-query axios
   ```

2. Create `lib/types.ts` — all TypeScript interfaces (from LLD section 16)
3. Create `lib/api.ts` — typed fetch wrappers for all backend endpoints
4. Create `stores/chatStore.ts` — Zustand store
5. Create `stores/settingsStore.ts` — model selection, API keys, budget

### 5.2 Shared Components

Build these before page-level components:
- `components/shared/Button.tsx`
- `components/shared/Spinner.tsx`
- `components/shared/StatusBadge.tsx`

### 5.3 Chat Interface

1. `components/chat/ModelSelector.tsx` — dropdown for model selection + API key input
2. `components/chat/FileUploadZone.tsx` — drag-drop + click-to-upload
3. `components/chat/MessageBubble.tsx` — user/assistant messages with metadata
4. `components/chat/ChatWindow.tsx` — assembles the above
5. `app/chat/page.tsx` — wraps ChatWindow

### 5.4 Dashboard

1. `components/dashboard/TokenDelta.tsx` — before/after token count with percentage
2. `components/dashboard/CostDelta.tsx` — before/after cost with percentage
3. `components/dashboard/EngineBreakdown.tsx` — per-engine attribution bars
4. `components/dashboard/MetricsPanel.tsx` — assembles all dashboard components
5. `app/dashboard/page.tsx`

### 5.5 Evaluation View

1. `components/evaluate/ValidationBadge.tsx` — PASS/FAIL with metric values
2. `components/evaluate/RecoveryPointerViewer.tsx` — inline expansion of [PTR:...] references
3. `components/evaluate/SideBySide.tsx` — baseline vs optimized response comparison
4. `app/evaluate/page.tsx`

### 5.6 Hooks

- `hooks/useChat.ts` — wraps chatStore, handles streaming if applicable
- `hooks/useOptimization.ts` — polls optimization_run status
- `hooks/useMetrics.ts` — fetches aggregate metrics

---

## 6. Critical Implementation Rules

These are non-negotiable constraints derived from the deployment environment.

### 6.1 Memory Budget (Render 512MB)

- Load CrossEncoder and spaCy models **once at startup** using module-level singletons
- Do NOT reload models per request
- Do NOT use `en_core_web_lg` — use `en_core_web_sm` only
- Cap NLI contradiction check to top 20 chunks — pairwise on 200 chunks is O(n²) and will OOM
- Batch embedding calls: max 100 chunks per OpenAI API call
- Do NOT load both CrossEncoder models simultaneously if memory is tight — lazy-load the NLI model

```python
# services/engines/roi_engine.py — correct pattern
_cross_encoder = None

def get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder
```

### 6.2 Async Throughout

Every service that does I/O must be async:
- All database calls: `await db.execute(...)`
- All vector store calls: use `AsyncQdrantClient`
- All LLM calls: use async provider methods
- All Redis calls: use `redis.asyncio`

Synchronous CPU-bound work (CrossEncoder inference) is acceptable — do not wrap in `asyncio.to_thread` for MVP unless profiling shows it blocks the event loop for > 100ms.

### 6.3 Parallel Engine Execution

The three engines (ROI, Dependency Graph, Contradiction) must run in parallel:

```python
roi_task = asyncio.create_task(roi_engine.score(query, chunks))
dep_task = asyncio.create_task(dep_graph.build(query, chunks))
contra_task = asyncio.create_task(contradiction.detect(chunks))
roi_result, dep_result, contra_result = await asyncio.gather(roi_task, dep_task, contra_task)
```

### 6.4 Background Tasks

Validation and prefetch must NOT block the response:

```python
from fastapi import BackgroundTasks

@router.post("/chat")
async def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    response = await run_pipeline(req)
    background_tasks.add_task(validation_harness.evaluate, ...)  # non-blocking
    background_tasks.add_task(prefetcher.prefetch, ...)           # non-blocking
    return response
```

### 6.5 Engine Failure Isolation

Wrap each engine call in `safe_engine_run`:

```python
async def safe_engine_run(coro, engine_name: str):
    try:
        return await coro
    except Exception as e:
        logger.error(f"{engine_name} failed: {e}")
        return None  # pipeline continues, engine marked disabled in response
```

### 6.6 API Key Security

Never store raw API keys. Encrypt with AES-256 before storage:

```python
from cryptography.fernet import Fernet

def encrypt_key(raw_key: str, encryption_key: bytes) -> str:
    f = Fernet(encryption_key)
    return f.encrypt(raw_key.encode()).decode()

def decrypt_key(encrypted: str, encryption_key: bytes) -> str:
    f = Fernet(encryption_key)
    return f.decrypt(encrypted.encode()).decode()
```

### 6.7 Cold Start Prevention

Add a `/health` endpoint that returns immediately. Configure an external ping (UptimeRobot, BetterUptime, or a Vercel cron job) to hit it every 14 minutes.

```python
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
```

---

## 7. Data Flow — Full Request Lifecycle

This is the exact sequence for `POST /api/chat`. Implement it in this order within the route handler.

```
1. Validate request schema (FastAPI auto-validates via Pydantic)
2. QueryUnderstanding.analyze(req.message)
   → QueryAnalysis (intent, entities, reformulated_query)

3. HybridRetriever.retrieve(analysis.reformulated_query, req.document_ids)
   → candidate_pool: list[ScoredChunk], ~50–200 items

4. [PARALLEL] await asyncio.gather(
     roi_engine.score(query, candidate_pool),
     dep_graph.build(query, candidate_pool),
     contradiction.detect(candidate_pool[:20])
   )

5. FusionEngine.score(candidate_pool, roi_result, dep_result, contra_result)
   → list[ScoredChunk] with fusion_score

6. TokenBudgetAllocator.allocate(scored_chunks, req.token_budget)
   → AllocationResult with selected chunks

7. RecoverableCompressor.compress(allocation.selected, query)
   → CompressionResult (compressed_text, recovery_map)

8. ModelContextAdapter.adapt(compressed_text, req.model, query)
   → adapted_context: str

9. LLMGateway.complete(adapted_context, req.model, api_key)
   → LLMResponse (content, usage, latency)

10. Compute metrics:
    - token_reduction = 1 - (compressed_tokens / original_tokens)
    - cost_reduction via cost_tracker
    - Assemble OptimizationMetrics

11. Persist to DB:
    - messages record (user + assistant)
    - optimization_run record
    - compression_record (link to run)

12. [BACKGROUND] ValidationHarness.evaluate(...)
13. [BACKGROUND] SpeculativePrefetcher.prefetch(query)

14. Return ChatResponse {
      message_id, content, optimization_run_id, metrics
    }
```

---

## 8. Validation Harness — Implementation Notes

The validation harness is the scientific backbone. Build it correctly.

**Baseline path (no optimization):**
```python
class BaselineRunner:
    async def run(self, query: str, raw_chunks: list[Chunk], model: str, api_key: str) -> LLMResponse:
        """Concatenate top chunks up to token budget, send raw to LLM."""
        context = "\n\n".join(c.content for c in raw_chunks[:10])  # naive top-10
        return await self.llm.complete(f"{context}\n\n{query}", model, api_key)
```

**BERTScore:**
```python
from bert_score import score as bert_score

def compute_bert_score(reference: str, candidate: str) -> float:
    _, _, F1 = bert_score([candidate], [reference], lang="en", rescale_with_baseline=True)
    return float(F1[0])
```

**LLM Judge prompt (use cheapest model — gpt-4o-mini):**
```
System: You are an objective answer quality evaluator.
User:
Query: {query}

Response A: {baseline_response}
Response B: {optimized_response}

Rate each response from 1-10 on:
- Accuracy (does it correctly answer the query?)
- Completeness (does it cover all aspects?)
- Conciseness (no unnecessary content?)

Output valid JSON only:
{"score_a": <int>, "score_b": <int>, "reasoning": "<one sentence>"}
```

**Pass/fail thresholds:**
```python
PASS_CRITERIA = {
    "bert_score_f1": 0.90,     # semantic similarity to baseline
    "quality_delta": 0.0,      # optimized must be >= baseline quality
    "token_reduction": 0.20,   # must save at least 20% tokens
    "faithfulness": 0.85,      # NLI entailment of response vs context
}
```

---

## 9. Testing Requirements

See `tests/` directory for test files. Required coverage before any feature is considered complete:

### Backend Tests (pytest + pytest-asyncio)

| Test | File | Type |
|---|---|---|
| File parsing (PDF, DOCX, TXT) | `tests/backend/unit/test_parser.py` | Unit |
| Chunking strategies | `tests/backend/unit/test_chunker.py` | Unit |
| Embedding + Qdrant upsert | `tests/backend/integration/test_embedder.py` | Integration |
| ROI scoring correctness | `tests/backend/unit/test_roi_engine.py` | Unit |
| Dependency graph frontier detection | `tests/backend/unit/test_dependency_graph.py` | Unit |
| Contradiction detection TP/FP rate | `tests/backend/unit/test_contradiction.py` | Unit |
| Knapsack allocation optimality | `tests/backend/unit/test_token_budget.py` | Unit |
| Compression pointer parsing | `tests/backend/unit/test_compression.py` | Unit |
| Full pipeline (upload → chat) | `tests/backend/e2e/test_full_pipeline.py` | E2E |
| Validation harness pass/fail | `tests/backend/integration/test_validation.py` | Integration |

### Frontend Tests (Vitest + React Testing Library)

| Test | File | Type |
|---|---|---|
| MetricsPanel renders correctly | `tests/frontend/unit/MetricsPanel.test.tsx` | Unit |
| RecoveryPointerViewer expansion | `tests/frontend/unit/RecoveryPointerViewer.test.tsx` | Unit |
| FileUploadZone drag-drop | `tests/frontend/unit/FileUploadZone.test.tsx` | Unit |
| Chat send → response flow | `tests/frontend/integration/chat.test.tsx` | Integration |
| API client error handling | `tests/frontend/unit/api.test.ts` | Unit |

---

## 10. File Generation Checklist

Use this as a scaffold checklist. Check off each file as you create it.

### Backend

```
[ ] main.py
[ ] pyproject.toml / requirements.txt
[ ] Dockerfile
[ ] .env.example
[ ] core/config.py
[ ] core/database.py
[ ] core/vector_store.py
[ ] core/redis_client.py
[ ] core/exceptions.py
[ ] models/db/user.py
[ ] models/db/conversation.py
[ ] models/db/chunk.py
[ ] models/db/compression_record.py
[ ] models/db/validation_result.py
[ ] models/schemas/chat.py
[ ] models/schemas/optimize.py
[ ] models/schemas/chunk.py
[ ] models/schemas/compression.py
[ ] models/schemas/validation.py
[ ] services/ingestion/parser.py
[ ] services/ingestion/chunker.py
[ ] services/ingestion/embedder.py
[ ] services/ingestion/normalizer.py
[ ] services/retrieval/semantic.py
[ ] services/retrieval/keyword.py
[ ] services/retrieval/hybrid.py
[ ] services/query/understanding.py
[ ] services/engines/roi_engine.py
[ ] services/engines/dependency_graph.py
[ ] services/engines/contradiction.py
[ ] services/engines/token_budget.py
[ ] services/engines/fusion.py
[ ] services/engines/compression.py
[ ] services/engines/model_adapter.py
[ ] services/engines/prefetcher.py
[ ] services/llm/gateway.py
[ ] services/llm/providers/base.py
[ ] services/llm/providers/openai_provider.py
[ ] services/llm/providers/anthropic_provider.py
[ ] services/llm/providers/gemini_provider.py
[ ] services/llm/cost_tracker.py
[ ] services/validation/harness.py
[ ] services/validation/metrics.py
[ ] services/validation/baseline.py
[ ] api/routes/chat.py
[ ] api/routes/optimize.py
[ ] api/routes/validate.py
[ ] api/routes/upload.py
[ ] api/routes/evaluate.py
[ ] api/routes/metrics.py
[ ] api/routes/history.py
[ ] api/routes/compression.py
[ ] api/middleware/auth.py
[ ] api/middleware/rate_limit.py
[ ] api/middleware/logging.py
[ ] api/dependencies.py
[ ] utils/text.py
[ ] utils/crypto.py
[ ] utils/async_helpers.py
```

### Frontend

```
[ ] package.json
[ ] next.config.ts
[ ] tsconfig.json
[ ] tailwind.config.ts
[ ] .env.example
[ ] app/layout.tsx
[ ] app/page.tsx
[ ] app/chat/page.tsx
[ ] app/dashboard/page.tsx
[ ] app/evaluate/page.tsx
[ ] components/chat/ChatWindow.tsx
[ ] components/chat/MessageBubble.tsx
[ ] components/chat/FileUploadZone.tsx
[ ] components/chat/ModelSelector.tsx
[ ] components/dashboard/MetricsPanel.tsx
[ ] components/dashboard/EngineBreakdown.tsx
[ ] components/dashboard/TokenDelta.tsx
[ ] components/dashboard/CostDelta.tsx
[ ] components/evaluate/SideBySide.tsx
[ ] components/evaluate/RecoveryPointerViewer.tsx
[ ] components/evaluate/ValidationBadge.tsx
[ ] components/shared/Button.tsx
[ ] components/shared/Spinner.tsx
[ ] components/shared/StatusBadge.tsx
[ ] hooks/useChat.ts
[ ] hooks/useOptimization.ts
[ ] hooks/useMetrics.ts
[ ] lib/api.ts
[ ] lib/types.ts
[ ] lib/utils.ts
[ ] stores/chatStore.ts
[ ] stores/settingsStore.ts
```

---

## 11. What Makes This Different — Remind Yourself Often

When generating code, keep these principles in mind. They are the reason this project exists.

1. **The objective is answer quality gain per token, not retrieval similarity.** Every scoring function should reflect this. ROI score is not a similarity score.

2. **Every optimization must be measurable.** The validation harness is not optional. Every run should produce a `ValidationResult`.

3. **Engines are independent and failure-safe.** One engine failing must not crash the pipeline. The response should note which engines were disabled.

4. **Compression is reversible.** Recovery pointers must have enough information to reconstruct the original passage exactly. The `byte_range` and `source_doc` in every pointer are mandatory.

5. **The system works on the free tier.** Do not introduce dependencies that require GPU, more than 512MB RAM, or persistent disk on the backend.

---

## 12. Suggested Gemini Prompting Strategy

If you are using Gemini to generate the scaffold, prompt it in this order:

**Prompt 1:**
> "Read ContextOS_LLD_v1.md completely. Then generate the full `core/` directory: config.py, database.py, vector_store.py, redis_client.py, exceptions.py. Use the exact class and attribute names from the LLD. No placeholders."

**Prompt 2:**
> "Generate all Pydantic schemas in `models/schemas/` exactly as specified in ContextOS_LLD_v1.md section 2.2. Include all fields, types, and nested models."

**Prompt 3:**
> "Generate `services/ingestion/` — parser.py, chunker.py, embedder.py, normalizer.py. Use pdfplumber for PDF, python-docx for DOCX, trafilatura for URLs. Batch embedding calls to max 100 per request."

**Prompt 4 (repeat for each engine):**
> "Generate `services/engines/roi_engine.py` exactly as specified in ContextOS_LLD_v1.md section 6. Use module-level singleton for the CrossEncoder to avoid reloading it per request."

**Prompt 5:**
> "Generate `api/routes/chat.py` implementing the full pipeline sequence from Agent.md section 7. Use BackgroundTasks for validation and prefetch. Use asyncio.gather for parallel engine execution."

**Prompt 6:**
> "Generate the full Next.js frontend: all components, stores, hooks, and lib files from Agent.md section 5. Use the TypeScript interfaces from ContextOS_LLD_v1.md section 16 exactly."

---

*Agent.md — ContextOS v1.0 — June 2026*
