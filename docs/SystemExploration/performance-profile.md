# Performance Profile

Latency breakdown for a typical request on Render free tier (0.1 CPU, 512MB RAM).

**Test conditions:** 200 candidate chunks, 512 tokens each, gpt-4o-mini LLM, 8192 token budget.

## Expected Latency Per Stage

| Stage | Expected (ms) | Notes |
|---|---|---|
| Query Understanding (spaCy) | 50–100 | en_core_web_sm, capped at 10k chars |
| Semantic Retrieval (Qdrant) | 100–200 | Network call to Qdrant Cloud |
| Keyword Retrieval (BM25) | 20–50 | In-memory, fast |
| RRF Fusion | 5–10 | Pure compute |
| ROI Engine (CrossEncoder) | 400–800 | CPU inference, 200 pairs |
| Dependency Graph | 200–500 | spaCy + NetworkX on 200 chunks |
| Contradiction Detector | 200–400 | NLI on 190 pairs (20 chunks pairwise) |
| Fusion + Budget Allocation | 5–10 | Pure compute |
| Compression (API call) | 1000–3000 | Network call to Claude/OpenAI |
| Model Adaptation | 1–5 | String formatting |
| LLM Inference (API call) | 2000–8000 | Depends on model and response length |
| **Total (serial)** | **~4000–13000ms** | |
| **Total (with parallelism)** | **~3500–10000ms** | ROI+Dep+Contra in parallel |

## Optimization Opportunities

**Biggest wins:**
1. ROI + Dependency + Contradiction are already parallelized (800ms saved)
2. Compression call is the second biggest wait — consider skipping for short queries (<1000 tokens selected)
3. LLM inference dominates for long responses — nothing we can do here

**Not worth optimizing:**
- Query Understanding (50ms)
- BM25 (20ms)
- Fusion (5ms)

## Cold Start Additional Latency

First request after Render cold start adds:
- spaCy model load: ~2000ms (50MB, one-time)
- CrossEncoder load: ~3000ms (22MB + tokenizer)
- NLI model load: ~5000ms (180MB)

**Total cold start overhead:** ~10s. Mitigated by pre-warming on startup and UptimeRobot pings.

## Target SLA (MVP)

| Condition | Target |
|---|---|
| Warm instance, typical query | < 8s end-to-end |
| Warm instance, simple query | < 5s end-to-end |
| Cold start | < 20s (acceptable) |
| Streaming enabled | First token < 3s |
