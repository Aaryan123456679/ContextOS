# Testing Strategy

## Test Pyramid

```
        ┌──────────────┐
        │   E2E Tests  │  10% — Full pipeline, real services
        └──────┬───────┘
      ┌────────┴────────┐
      │ Integration Tests│  30% — Service + DB interactions
      └────────┬─────────┘
    ┌──────────┴──────────┐
    │     Unit Tests       │  60% — Engine logic, schemas, utils
    └─────────────────────┘
```

## Unit Tests

**What they test:** Pure logic with all I/O mocked.  
**Framework:** pytest (backend), Vitest (frontend)  
**Speed:** < 100ms per test  
**External services:** None — all mocked

**Priority targets:**
- ROI Engine scoring logic (normalization, threshold)
- Dependency graph frontier detection
- Contradiction detector resolution logic
- Token budget knapsack correctness
- Compression pointer regex parsing
- Fusion score formula
- Cost calculation (cost_tracker)
- API key encryption/decryption
- Chunker strategies (fixed, sentence, paragraph)

## Integration Tests

**What they test:** Service layer interactions with real external services.  
**Framework:** pytest + pytest-asyncio  
**Speed:** 1–10s per test  
**External services:** Real Supabase + Qdrant (test collection, not production)

**Priority targets:**
- Upload pipeline: file → Qdrant upsert → Supabase chunk records
- Retrieval pipeline: query → Qdrant search → results
- Compression: API call → pointer parsing → DB storage
- Validation harness: baseline vs optimized comparison

**Setup:** Use a dedicated `contextos_test` Qdrant collection and `test_` prefixed Supabase table rows. Clean up in teardown.

## E2E Tests

**What they test:** Full user flows from HTTP request to response.  
**Framework:** pytest (backend E2E), Playwright (frontend E2E)  
**Speed:** 10–60s per test  
**External services:** Real everything including LLM providers (costs tokens)

**Priority flows:**
1. Upload PDF → verify chunk_count > 0
2. Chat with uploaded PDF → verify optimized response + metrics
3. Click recovery pointer → verify expansion returns original text
4. Run side-by-side eval → verify ValidationResult schema

**LLM call cost in E2E:** ~$0.01 per full pipeline E2E test. Run sparingly — not on every commit.

## Frontend Testing

**Framework:** Vitest + React Testing Library + Playwright

**Unit tests:** Component rendering, props handling, store mutations  
**Integration tests:** API client mock → component updates correctly  
**E2E tests:** Full browser flows with Playwright

**Key frontend test cases:**
- MetricsPanel shows correct token reduction percentage
- RecoveryPointerViewer renders clickable [ptr_XX] tags
- FileUploadZone accepts PDF and shows progress
- ModelSelector saves API key (verify it does NOT log to console)
- SideBySide shows correct PASS/FAIL badge based on ValidationResult

## CI Configuration (GitHub Actions)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  backend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r backend/requirements.txt
      - run: python -m spacy download en_core_web_sm
      - run: pytest backend/tests/unit/ -v
        env:
          ENVIRONMENT: test

  frontend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd frontend && npm install && npm run test
```

Integration and E2E tests do NOT run in CI (would require real API keys in secrets — deferred).

## Deployment Gate

Before any deploy to Render/Vercel, the following must pass locally:

```bash
# Must all pass:
pytest tests/backend/unit/ -v               # all unit tests
pytest tests/backend/integration/ -v -k "not llm"  # integration without LLM calls
cd frontend && npm run test                  # all frontend unit tests
cd frontend && npx tsc --noEmit             # TypeScript check
```
