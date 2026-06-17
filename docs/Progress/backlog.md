# Backlog — V2 and Beyond

Features deferred from MVP, prioritized by impact.

## V2 — Intelligence Layer (Months 3–4)

### High Priority

| Feature | Why Deferred | Complexity |
|---|---|---|
| Speculative Prefetcher | Needs quality follow-up prediction first | Medium |
| Model Context Adapter — learned weights | Needs validation signal data first | High |
| Audio ingestion (Whisper API) | Not core to thesis | Medium |
| Image context (vision API) | Not core to thesis | Medium |

### Medium Priority

| Feature | Description |
|---|---|
| Automatic pointer expansion | Detect when LLM response signals need for expansion, auto-inject |
| Conversation coherence | Pin expanded pointers for subsequent turns |
| V2 dependency graph (semantic edges) | Replace heuristic edges with NLI entailment |
| User preference learning | Adapt fusion weights per user from feedback |

## V3 — Learned Optimization (Months 5–6)

| Feature | Description |
|---|---|
| Trained ROI scorer | DistilBERT trained on synthetic (query, chunk, quality_delta) data |
| Learned fusion weights | Per-domain weight learning from validation outcomes |
| GitHub retriever | Retrieve from code files and PRs |
| Web retriever | Live web search integration |
| RL from user feedback | Thumbs up/down adjusts future optimization |

## V4 — Platform

| Feature | Description |
|---|---|
| ContextOS API product | Expose optimization pipeline as API for other developers |
| SDK | Python + TypeScript SDK wrapping the API |
| Multi-tenant enterprise | Organization accounts, shared document stores |
| Context market | Retriever bidding via RL (theoretical — Phase 4 in HLD) |

## Known Limitations (Not Bugs)

1. **Compression is best-effort:** If the LLM produces malformed PTR tags, pointers are lost. The compressed text is still usable — just without expansion capability. Flagged in metrics.

2. **Dependency graph is heuristic:** V1 uses co-occurrence and section order as proxy for concept dependency. Will produce false positives (pruning relevant chunks) for unusual document structures.

3. **BERTScore is a proxy:** BERTScore F1 ≥ 0.90 means the responses are semantically similar, not that they are equally correct. The LLM judge catches cases where similar-sounding answers are factually different.

4. **No streaming in MVP:** Chat responses appear all at once. Streaming from LLM providers is supported by all provider SDKs — just not wired in MVP frontend.

5. **API keys stored per user, not per organization:** MVP assumes a single user. Multi-tenant key management is V4.
