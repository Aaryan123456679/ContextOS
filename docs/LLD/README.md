# LLD — Low Level Design

This folder contains per-system detailed design documents. Each file covers one service or subsystem: its inputs, outputs, internal logic, data structures, failure modes, and interaction with other services.

## Contents

| File | System | Complexity |
|---|---|---|
| [01-ingestion.md](01-ingestion.md) | File parsing, chunking, embedding | Medium |
| [02-retrieval.md](02-retrieval.md) | Semantic + keyword + hybrid retrieval | Medium |
| [03-query-understanding.md](03-query-understanding.md) | Intent, NER, reformulation | Low |
| [04-roi-engine.md](04-roi-engine.md) | Context ROI scoring (cross-encoder) | High |
| [05-dependency-graph.md](05-dependency-graph.md) | Minimum knowledge frontier | High |
| [06-contradiction-detector.md](06-contradiction-detector.md) | NLI-based contradiction detection | Medium |
| [07-fusion-token-budget.md](07-fusion-token-budget.md) | Score fusion + knapsack allocation | Medium |
| [08-compression.md](08-compression.md) | Recoverable compression + pointers | High |
| [09-model-adapter.md](09-model-adapter.md) | Model-specific context formatting | Low |
| [10-llm-gateway.md](10-llm-gateway.md) | Unified LLM provider interface | Medium |
| [12-api-routes.md](12-api-routes.md) | All FastAPI route signatures | Medium |
| [13-frontend.md](13-frontend.md) | Component tree, state, hooks | Medium |
| [14-storage.md](14-storage.md) | Qdrant, Supabase, Redis, Storage | Medium |

## Source of Truth

The primary LLD document is `ContextOS_LLD_v1.md` at the repository root. Files here expand on specific subsystems with additional diagrams, edge cases, and implementation notes.
