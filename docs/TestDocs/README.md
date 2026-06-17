# Test Documentation

## Testing Philosophy

Every optimization must be measurable. This applies to testing too — tests must verify behavior, not just "it ran without error."

## Contents

| File | Topic |
|---|---|
| [testing-strategy.md](testing-strategy.md) | Overall test strategy, test pyramid, coverage targets |
| [backend-test-plan.md](backend-test-plan.md) | All backend test cases with expected inputs/outputs |
| [frontend-test-plan.md](frontend-test-plan.md) | All frontend test cases |
| [evaluation-dataset.md](evaluation-dataset.md) | Query/document pairs for validation harness benchmarking |
| [regression-suite.md](regression-suite.md) | Regression tests that must pass before any deploy |

## Test Environments

| Environment | Purpose | External Services |
|---|---|---|
| Unit (local) | Pure logic tests | Mocked |
| Integration (local) | Service interactions | Real Supabase + Qdrant |
| E2E (local/CI) | Full pipeline | Real services + real LLM |
| CI (GitHub Actions) | Automated on PR | Unit + Integration only |

## Running All Tests

```bash
# Backend
cd backend
pytest tests/backend/unit/ -v --tb=short
pytest tests/backend/integration/ -v --tb=short
pytest tests/backend/e2e/ -v --tb=short -k "not slow"

# Frontend
cd frontend
npm run test          # Vitest unit tests
npm run test:e2e      # Playwright e2e
```

## Coverage Targets (MVP)

| Layer | Target Coverage |
|---|---|
| Engine logic | > 85% |
| API routes | > 70% |
| Frontend components | > 60% |
| E2E happy path | 100% of main flows |
