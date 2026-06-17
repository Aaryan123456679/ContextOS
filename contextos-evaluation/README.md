# ContextOS Research Evaluation Framework

A research-grade, reproducible suite that measures whether **ContextOS reduces
context size and inference cost while maintaining answer quality** — on real,
publicly-sourced documents and realistic queries. Independent from the main app;
re-runnable as engines evolve. **All data stays local** (no Supabase/cloud).

> 📊 **Published results: [RESULTS.md](RESULTS.md)** — 56.8% mean / 74.5% median token
> reduction on 10k scenarios (model-independent); a **statistically-significant beat-SOTA**
> result (learned selection > LLMLingua-2 across the 55–85% reduction frontier, n=2,000,
> 95% CIs); and a quantified LLM-as-judge self-bias finding.

## TL;DR — run it

```bash
# from contextos-evaluation/  (uses the backend venv which has the engines)
PY=../backend/.venv/bin/python

# 0. one-time: local LLM (free, unlimited)
bash scripts/setup_ollama.sh llama3.1:8b

# 1. build the real corpus (resumable; ~hundreds–1000s of docs)
$PY -m corpus.ingest --target 1500

# 2. build >=10k evaluation scenarios (reproducible, seeded)
$PY -m scenarios.builder --n 10000              # add --no-llm-queries for fast templated queries

# 3a. deterministic metrics on ALL scenarios (token/cost/compression/retrieval/latency) — free
$PY runner.py --full --run-name milestone

# 3b. add LLM-judged metrics on a subset (answers + similarity + faithfulness + judge) — slow, local
$PY runner.py --full --judge-subset 1000 --run-name milestone   # resumable; accumulates over time

# 4. report (markdown + charts + summary.json)
$PY -m analysis.report results/runs/milestone

# 5. ablation: per-engine contribution
$PY ablation.py --limit 50 --run-name ablation
```

## Why this design (the honest constraints)

- **10k × (baseline + optimized + judge) ≈ 30k LLM calls.** On a free Gemini key
  that's impossible; we run the LLM locally via **Ollama** (free, unlimited) but a
  *full* 10k judged pass on an M1 is multi-day. So:
  - **Deterministic metrics** (token reduction, cost, compression ratio, retrieval
    quality, pipeline latency) run on **all** scenarios cheaply.
  - **LLM-judged metrics** run on a configurable **subset** (`--judge-subset`),
    resumable so it accumulates toward 10k across sessions.
- **Provider-agnostic:** `providers/` supports Ollama (default), Gemini, OpenAI,
  Anthropic via one interface — point the judged pass at a paid API to finish 10k fast.

## Pipeline

```
corpus.ingest      real docs → data/corpus/ (manifest + raw text, dedup, sha)
scenarios.builder  query + doc mix (gold + noise + redundancy + contradiction) → data/scenarios.jsonl
pipeline.retrieval local sentence-transformer embeds + retrieves candidate chunks (no cloud vector store)
pipeline.contextos_pipeline  ROI → dependency → contradiction → fusion → token-budget → (compression)
metrics.*          tokens/cost, BERTScore similarity, NLI faithfulness/hallucination, LLM-as-judge quality, relevance
runner.py          baseline (full ctx → LLM) vs ContextOS (optimized → LLM) → results.csv
ablation.py        engine-set matrix → per-engine contribution
analysis.report    stats (p50/p95/p99) + charts + report.md
```

## Engines (mapped to the real implementation)

The original spec named engines that don't exist in the codebase. The ablation
uses the **real** engines in `backend/services/engines/`:

| Spec name | Real engine |
|---|---|
| Attention Utility | ROI cross-encoder (`roi_engine.py`) |
| Contradiction | `contradiction.py` (NLI + topical guard + resolution) |
| (Dependency) | `dependency_graph.py` (chain-aware) |
| Compression | `compression.py` (recoverable, runs on Ollama here) |
| Entropy / Reliability / Personalization | **not implemented** (reported as such) |

Selection (fusion + token-budget) is always on — it's the selection mechanism.
Compression is **off by default** in the headline run because LLM compression
currently over-compresses and degrades answers; the ablation quantifies it.

## Metrics & success criterion

Per scenario (CSV columns): token reduction, cost savings, compression ratio,
gold-chunk recall, pipeline/answer latency, answer similarity (BERTScore),
faithfulness + hallucination (embedding-gated NLI), relevance, LLM-judge quality
(completeness/correctness/clarity/grounding) for both paths.

```
pass = token_reduction_pct > 20  AND  answer_similarity > 0.90  AND  quality >= baseline_quality
```

## Reproducibility

Every run writes `run_manifest.json` (seed, provider, model + digest, pricing
version, engines, top-k). Corpus docs are recorded with source id, url, tokens,
tier, sha256. Scenario building is seeded. Re-running the runner skips completed
`run_id`s.

## Outputs (`results/runs/<name>/`)

`results.csv` (per scenario) · `summary.json` (aggregates incl. p50/p95/p99) ·
`report.md` + `charts/*.png` · `run_manifest.json`.

## Limitations (stated for rigor)

- **Reference-free:** no gold answers (scrape-only), so "correctness" is
  judge-relative and similarity is measured against the baseline answer.
- **Corpus skew:** the default pull is technical-heavy (arXiv); Wikipedia category
  throttling can thin the noise classes. Re-run `corpus.ingest --only wiki` to add more.
- **Local judge:** an 8B local model is a weaker judge than a frontier model; for
  publication-grade quality scores, point the judged pass at a stronger API model.
- **Compression** currently reduces tokens further but degrades answers — kept in
  the ablation, off in the headline.
```
