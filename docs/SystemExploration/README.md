# System Exploration

Deep-dive notes on how the system behaves in practice — observations, edge cases, performance characteristics, and system-level behaviors discovered through experimentation.

## Contents

| File | Topic |
|---|---|
| [engine-interactions.md](engine-interactions.md) | How engines affect each other's output |
| [context-pipeline-behavior.md](context-pipeline-behavior.md) | Pipeline behavior across different query types |
| [performance-profile.md](performance-profile.md) | Latency breakdown per engine on Render free tier |
| [query-type-analysis.md](query-type-analysis.md) | How different query intents affect optimization |
| [model-specific-observations.md](model-specific-observations.md) | Claude vs GPT vs Gemini response quality differences |

## How to Use This Folder

When you discover something non-obvious about the system — a pattern, an edge case, an unexpected interaction — document it here. Each file grows over time as you run experiments.

Format for each observation:
```markdown
## [Date] — [Short title]

**Observed:** what you saw
**Query used:** the actual test query
**Why it happens:** your hypothesis
**Impact:** does this affect pipeline design?
**Action taken:** code change, config change, or "deferred to V2"
```
