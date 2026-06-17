# ContextOS Benchmark

A reproducible benchmark that proves two claims at scale:

1. **ContextOS significantly reduces the tokens sent to the LLM.**
2. **Accuracy stays essentially the same** — the chunk that actually answers the
   query is retained, at a rate far above naive truncation using the same budget.

## Why it's designed this way

Sending 10,000 prompts to a real LLM would instantly exhaust the Gemini free-tier
daily quota. But **token reduction and information retention are deterministic** —
they're computed by the engines (ROI cross-encoder, dependency graph, contradiction
NLI, fusion, token-budget allocator) with no LLM call. So we measure those over the
full 10,000 cases, and separately corroborate **answer accuracy** on a small
LLM-scored subset.

## Test categories (each stresses specific engines)

| Category | What it tests | Engine exercised |
|---|---|---|
| `roi` | 1 relevant fact buried among 6–10 irrelevant distractors | ROI cross-encoder ranking |
| `contradiction` | a stale/wrong chunk conflicts with the correct (newer) chunk | Contradiction NLI + resolution |
| `dependency` | answer needs a 2-hop chain; off-topic chunks are concept-disjoint | Dependency graph pruning |
| `compression` | a verbose gold chunk padded with low-information prose | Recoverable compression |
| `mixed` | a blend of the above in one candidate pool | Full pipeline |

Each case ships with ground truth: the gold chunk(s), the gold answer string, and
a token budget that forces the pipeline to select rather than keep everything.

## Metrics

- **Token reduction %** — full candidate pool vs the pipeline-selected context.
- **Gold retention %** — was the answer-bearing chunk kept? (accuracy proxy)
- **Naive gold retention %** — same, but keeping chunks in retrieval order until the
  *same* budget is filled. The gap shows ContextOS's selection is the value-add.
- **Distractor removal %** — fraction of irrelevant chunks dropped.
- **Contradiction flag % / wrong-fact dropped %** — for conflict cases.
- **(LLM subset)** answer accuracy (full vs optimized), BERTScore F1 of the two
  answers, and estimated cost reduction.

## Run it

From the `backend/` directory (use the project venv):

```bash
# 1. Generate the dataset (10,000 cases, reproducible with a fixed seed)
python -m benchmark.generate_dataset --n 10000

# 2a. Quick run (a representative sample, ~minutes)
python -m benchmark.run_benchmark --limit 1000

# 2b. Full definitive run (all 10,000 cases, ~1.5 h on CPU)
python -m benchmark.run_benchmark --full

# 3. (optional) Add real-model accuracy scoring on N cases (uses the Gemini key
#    with model rotation; keep N small to respect the free-tier daily quota)
python -m benchmark.run_benchmark --limit 1000 --llm-subset 20
```

## Output

Written to `benchmark/results/`:

- `report.md` — headline numbers + per-category table (paste this to show others)
- `summary.json` — the same aggregates, machine-readable
- `results.csv` / `results.jsonl` — per-case rows for your own charts/analysis

The run is deterministic (fixed seed + deterministic engines), so anyone can
reproduce the exact numbers.
