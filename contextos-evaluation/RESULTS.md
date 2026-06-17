# ContextOS — Published Evaluation Results

Reproducible results from the evaluation suite. All runs are seeded; data stays local.
Generators: local Ollama (llama3.1:8b / mistral:7b / qwen2.5:7b) for deterministic and
cross-model work; OpenAI `gpt-4o-mini` (via gateway) for the strong-model benchmark.

---

## 1. Token / cost reduction — 10,000 scenarios (deterministic)

Real scraped corpus (arXiv, framework docs, Wikipedia + noise), engines = ROI +
dependency + contradiction. Deterministic metrics on all 10k; LLM-judged subset for quality.

| Metric | Value |
|---|---|
| Token reduction | **mean 56.8% · median 74.5% · p95 80.6% · p99 81.1%** |
| Total tokens saved | **92.7M** (126.3M → 33.7M) |
| Est. cost saved (gpt-4o-mini pricing) | **~$232** |
| Gold-fact retention (recall) | 0.863 |
| Answer similarity (optimized vs full) | mean 0.92 (p05 ≈ 0.851) |
| Quality vs baseline (judged) | Δ ≈ 0.0 (maintained) |

Cuts hardest where there's redundancy: noisy contexts 63.4%, redundant 59%, contradictory 57%.

## 2. Cross-model determinism — 3 model families (300 scenarios each)

Token/cost reduction is computed *before* the LLM, so it's model-independent:

| Model | Token reduction |
|---|---|
| llama3.1:8b | **52.6%** |
| mistral:7b | **52.6%** |
| qwen2.5:7b | **52.6%** |

Identical to the decimal — the savings come from the pipeline, not the model.

## 3. LLM-as-judge bias — self-judge vs independent judge (900 scenarios)

Hand-graded every answer with an independent judge vs the model's own self-judge:

| | Self-judge | Independent judge |
|---|---|---|
| Mean quality | 8.96 | **6.72** |
| % scored ≥9 | 78% | 2% |
| Correlation (r) | — | 0.41 |

Self-judging **inflates by ~2.2 points** and barely correlates with an independent grader —
quantified evidence that self-evaluation overstates quality.

## 4. Beat-SOTA — learned selection vs LLMLingua-2 (n=2,000, matched reduction)

Held-out HotpotQA + MuSiQue (1,000 each), generator `gpt-4o-mini`, **same token budget per
method at each reduction level**. F1 vs gold; 95% bootstrap CIs (10,000 resamples); `*` = paired
difference CI excludes 0 (significant). Baseline (full context) F1 = 0.598.

| Reduction | LLMLingua-2 (SOTA) | **ContextOS learned** | fixed (density) | ours − SOTA |
|---|---|---|---|---|
| 55% | 0.504 [0.485, 0.523] | **0.559 [0.540, 0.579]** | 0.532 | **+0.055 [+0.036, +0.075]** * |
| 70% | 0.410 [0.392, 0.430] | **0.519 [0.499, 0.539]** | 0.467 | **+0.108 [+0.087, +0.129]** * |
| 85% | 0.266 [0.249, 0.284] | **0.441 [0.421, 0.460]** | 0.375 | **+0.174 [+0.153, +0.196]** * |

**ContextOS learned selection significantly outperforms SOTA token-compression across the entire
55–85% reduction frontier, on both datasets, with the margin widening as compression increases.**
Every win is statistically significant (CIs non-overlapping; paired difference > 0). It also beats
the density allocator at every level.

## 5. The learned selection policy

- **Lightweight**: 13 engine signals → GradientBoosting (~777 learned params). Sub-ms inference, no GPU.
- **Flexible**: trained on HotpotQA + MuSiQue union; transfers across them at **ROC-AUC 0.82–0.85**.
- **Signal importance** (what actually matters): ROI cross-encoder dominates; fusion/density/rank next;
  **dependency-graph & contradiction engines contribute ≈ 0** to selection (honest ablation result).
- **In production**: ported to `backend/services/engines/learned_select.py`, gated by `SELECTION_MODE`,
  with automatic fall-back to the density allocator on any error.

## Caveats (honest)
- §4 uses a single generator (`gpt-4o-mini`) and two datasets; n=2,000 makes *these* numbers tight,
  but multi-model / multi-dataset breadth is future work.
- §1's judged subset is small (deterministic metrics cover all 10k); §3 is single-grader.
- The production policy was trained on Wikipedia multi-hop QA; benefit on arbitrary app documents is
  plausible (it leans on domain-agnostic ROI relevance) but not yet validated on production traffic.

## Reproduce
```bash
# beat-SOTA Pareto (matched reduction, with router + cost cap)
../backend/.venv/bin/python -m bench.pareto --dataset mix --limit 2000 \
    --levels 0.55,0.70,0.85 --provider openrouter --model openai/gpt-4o-mini
# 10k deterministic reduction
../backend/.venv/bin/python -m runner --full --judge-subset 46 --run-name milestone
```
Raw CSVs + per-run `comparison.md` live under `results/runs/`.
