# Evaluation Dataset

Test queries for benchmarking the validation harness. These represent the diversity of real use cases.

## Dataset Categories

### Category 1 — Debugging (stress tests ROI engine)

These queries have documents where most retrieved chunks are irrelevant. ROI engine should prune heavily.

| Query | Document | Expected token reduction |
|---|---|---|
| "Why is my Docker container exiting with code 137?" | Large docker-compose docs + error logs | > 60% |
| "What causes a CORS error in my Next.js API route?" | Full Next.js docs | > 55% |
| "Why is my Kubernetes pod in CrashLoopBackOff?" | Kubernetes docs + deployment YAML | > 65% |

### Category 2 — Factual (stress tests dependency graph)

These queries require specific facts from documents with lots of contextual preamble (ancestors to prune).

| Query | Document | Expected token reduction |
|---|---|---|
| "What is the rate limit for OpenAI's embedding API?" | Full OpenAI API docs | > 50% |
| "What model does Claude Haiku 3 use for reasoning?" | Anthropic docs | > 45% |
| "What is the maximum chunk size for Qdrant free tier?" | Qdrant docs | > 40% |

### Category 3 — Multi-hop (stress tests dependency graph edges)

These queries require connecting information from multiple chunks.

| Query | Document | Challenge |
|---|---|---|
| "How does self-attention enable transformers to handle long sequences?" | ML textbook PDF | Must link attention → sequence handling |
| "Why does gradient vanishing make RNNs worse than transformers?" | Deep learning docs | Must link vanishing gradient → RNN → transformer comparison |

### Category 4 — Contradiction (stress tests contradiction detector)

Documents with deliberately conflicting information.

| Query | Document | Expected behavior |
|---|---|---|
| "What is the max context window of GPT-4 Turbo?" | Mixed-date GPT-4 docs (old=8k, new=128k) | Detect conflict, keep recent |
| "Is Python GIL removed in Python 3.12?" | Mixed Python release notes | Detect conflict, surface both |

### Category 5 — Short queries (edge case)

| Query | Challenge |
|---|---|
| "What?" | Pipeline must handle degenerate input gracefully |
| "Explain" | Incomplete query — intent unclear |
| "Python" | Single-word query — broad retrieval |

## Benchmark Metrics (Pass Criteria)

For the evaluation dataset as a whole:

| Metric | Target |
|---|---|
| Average token reduction | > 40% |
| Average BERTScore F1 | > 0.90 |
| Average quality delta | ≥ 0.0 (never worse than baseline) |
| Pipeline error rate | < 2% (engine failures handled gracefully) |

## Using the Evaluation Dataset

```python
# tests/backend/e2e/test_benchmark.py
import pytest
from datasets import EVAL_DATASET  # list of (query, doc_path, expected_reduction)

@pytest.mark.parametrize("query,doc_path,min_reduction", EVAL_DATASET)
async def test_benchmark(query, doc_path, min_reduction, test_client):
    # upload doc
    upload_resp = await test_client.post("/api/upload", files={"file": open(doc_path, "rb")})
    doc_id = upload_resp.json()["document_id"]

    # run optimization
    chat_resp = await test_client.post("/api/chat", json={
        "message": query,
        "document_ids": [doc_id],
        "model": "gpt-4o-mini",
        "optimization_enabled": True,
    })
    metrics = chat_resp.json()["metrics"]

    assert metrics["token_reduction_pct"] >= min_reduction
    assert metrics["bert_score"] >= 0.90
```
