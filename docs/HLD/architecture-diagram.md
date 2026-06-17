# Architecture Diagrams

## Full System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Vercel)                        │
│                  Next.js 15 · TypeScript · Tailwind              │
│                                                                  │
│  ┌────────────┐  ┌──────────────────┐  ┌───────────────────┐    │
│  │    Chat    │  │  Optimization    │  │   Evaluation      │    │
│  │ Interface  │  │   Dashboard      │  │   Dashboard       │    │
│  └────────────┘  └──────────────────┘  └───────────────────┘    │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTPS / REST
┌──────────────────────────────▼───────────────────────────────────┐
│                     BACKEND (Render Free)                         │
│                     FastAPI · Python 3.11                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    API GATEWAY                           │    │
│  │           Auth · Rate Limiting · CORS                   │    │
│  └──────────────────────────┬────────────────────────────  ┘    │
│                             │                                    │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │               INPUT PROCESSING LAYER                       │  │
│  │  FileParser (PDF/DOCX/TXT/MD/CSV/URL)                     │  │
│  │  Chunker (512 tok, 64 overlap) → Embedder (batch 100)     │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │                                    │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │             QUERY UNDERSTANDING ENGINE                     │  │
│  │  spaCy NER · Intent Classifier · Constraint Extractor     │  │
│  └──────┬──────────────────┬──────────────────────────────── ┘  │
│         │                  │                                    │
│  ┌──────▼──────┐  ┌────────▼──────┐  ┌──────────────────────┐  │
│  │  Semantic   │  │   Keyword     │  │     File / Web       │  │
│  │  Retriever  │  │   Retriever   │  │     Retriever        │  │
│  │  (Qdrant)   │  │    (BM25)     │  │   (optional)         │  │
│  └──────┬──────┘  └────────┬──────┘  └──────────┬───────────┘  │
│         └──────────────────┼──────────────────────┘             │
│                            │ RRF Fusion                         │
│                   Candidate Pool (50–200 chunks)                 │
│                            │                                    │
│         ┌──────────────────┼──────────────────────┐             │
│   [async │gather]          │                      │             │
│  ┌───────▼──────┐  ┌───────▼────────┐  ┌──────────▼─────────┐  │
│  │  Context ROI │  │  Dependency    │  │  Contradiction     │  │
│  │    Engine    │  │  Graph Builder │  │    Detector        │  │
│  │ CrossEncoder │  │ spaCy+NetworkX │  │  NLI deberta-v3    │  │
│  └───────┬──────┘  └───────┬────────┘  └──────────┬─────────┘  │
│          └─────────────────┼──────────────────────┘             │
│                            │                                    │
│               ┌────────────▼────────────┐                       │
│               │      FUSION ENGINE       │                       │
│               │  α·roi + β·entropy       │                       │
│               │  − γ·contradiction       │                       │
│               │  − δ·dependency_redund   │                       │
│               └────────────┬────────────┘                       │
│                            │                                    │
│               ┌────────────▼────────────┐                       │
│               │   TOKEN BUDGET          │                       │
│               │   ALLOCATOR             │                       │
│               │  Greedy 0/1 Knapsack    │                       │
│               └────────────┬────────────┘                       │
│                            │                                    │
│               ┌────────────▼────────────┐                       │
│               │  RECOVERABLE COMPRESSOR  │                       │
│               │  Claude Haiku / GPT-mini │                       │
│               │  + Recovery Pointer Map  │                       │
│               └────────────┬────────────┘                       │
│                            │                                    │
│               ┌────────────▼────────────┐                       │
│               │  MODEL CONTEXT ADAPTER   │                       │
│               │  Claude → XML tags       │                       │
│               │  GPT → prose-first       │                       │
│               │  Gemini → citation-dense │                       │
│               └────────────┬────────────┘                       │
│                            │                                    │
│               ┌────────────▼────────────┐                       │
│               │      LLM GATEWAY        │                       │
│               │  OpenAI / Anthropic /   │                       │
│               │  Gemini / Groq          │                       │
│               └────────────┬────────────┘                       │
│                            │                                    │
│               [background] │  [background]                      │
│  ┌────────────────────┐    │  ┌──────────────────────────────┐  │
│  │ VALIDATION HARNESS │    │  │   SPECULATIVE PREFETCHER    │  │
│  │ Baseline vs Optim  │    │  │   Redis TTL=10min cache     │  │
│  │ BERTScore + Judge  │    │  │   (V2 — deferred)           │  │
│  └────────────────────┘    │  └──────────────────────────────┘  │
└────────────────────────────┼─────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
  ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐
  │   Qdrant    │   │  Supabase    │   │  Upstash Redis   │
  │  Cloud      │   │ PostgreSQL   │   │  (prefetch cache)│
  │  (1GB free) │   │ (500MB free) │   │  (serverless)    │
  └─────────────┘   └──────────────┘   └──────────────────┘
```

---

## Component Interaction Map

```
User Request
    │
    ▼
[QueryUnderstanding] ──→ reformulated_query, intent, entities
    │
    ▼
[HybridRetriever] ──→ candidate_pool (list[ScoredChunk])
    │
    ├──[async]──→ [ROIEngine] ──→ roi_score per chunk
    ├──[async]──→ [DependencyGraph] ──→ pruning_mask per chunk
    └──[async]──→ [ContradictionDetector] ──→ contradiction_flags
    │
    ▼
[FusionEngine] ──→ fusion_score per chunk (combines all signals)
    │
    ▼
[TokenBudgetAllocator] ──→ selected chunk set (≤ budget tokens)
    │
    ▼
[RecoverableCompressor] ──→ {compressed_text, recovery_map}
    │
    ▼
[ModelContextAdapter] ──→ adapted_context (model-specific format)
    │
    ▼
[LLMGateway] ──→ LLM provider ──→ response
    │
    ├──[bg]──→ [ValidationHarness] ──→ validation_result → DB
    └──[bg]──→ [SpeculativePrefetcher] ──→ Redis cache
    │
    ▼
ChatResponse { content, metrics, compression_id }
```

---

## Storage Access Patterns

```
Qdrant Cloud ←→ SemanticRetriever (read), Embedder (write)
Supabase PG  ←→ All routes (read/write users, messages, runs, chunks)
Upstash Redis ←→ SpeculativePrefetcher (write), /api/chat (read on cache hit)
Supabase Stor ←→ FileParser (write), expand_pointer route (read)
```
