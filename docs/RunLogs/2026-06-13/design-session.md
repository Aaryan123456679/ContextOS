# Run Log — 2026-06-13 — Initial Design Session

## Goal

Produce all pre-development documentation needed to scaffold ContextOS using an AI agent (Gemini). Specifically: finalize HLD v2, create detailed LLD, create Agent.md with scaffolding instructions, and set up the full docs folder structure.

## Starting State

Only `ContextOS_HLD_v2.md` existed. No code, no LLD, no folder structure.

## Decision Log

### Decision 1: LLD structure — single file vs folder

**Options considered:**
- Option A: Single large `LLD.md` at repo root (easier to read linearly)
- Option B: One LLD file per subsystem in `docs/LLD/` folder (better for deep-dives)

**Chosen:** Hybrid — single `ContextOS_LLD_v1.md` as the primary LLD (for the AI agent to read in one pass), plus per-system detail files in `docs/LLD/` for developers.

**Why:** An AI agent scaffolding the project needs everything in one place to avoid context fragmentation. But humans need per-system detail when debugging a specific engine.

**Trade-off accepted:** Some duplication between root LLD and docs/LLD/ files. Acceptable — docs/LLD/ adds depth, not contradiction.

---

### Decision 2: Agent.md tone — instructions vs specification

**Options considered:**
- Option A: Write Agent.md as a specification (what the system should do)
- Option B: Write Agent.md as explicit instructions (what to build, in what order, why)

**Chosen:** Option B — explicit step-by-step instructions with Gemini-specific prompting strategy.

**Why:** A specification requires the agent to derive its own build order. An instruction document with clear sequencing (bootstrap → core → ingestion → engines → routes → frontend) reduces hallucination and dependency errors in scaffolded code.

**Trade-off accepted:** More prescriptive than a pure spec. If the agent has a better approach, it might be constrained. Acceptable at MVP stage.

---

### Decision 3: Recovery pointer format

**Options considered:**
- Option A: JSON format `{"ptr_id": "...", "trigger": "...", "source": "..."}`
- Option B: Inline tag format `[PTR:ptr_01|trigger:...|source:...|summary:...]`

**Chosen:** Option B — inline tag embedded in compressed text.

**Why:** JSON pointers would require the LLM to output two separate structures (compressed text + JSON map). Inline tags are more natural for an LLM to produce and easier to regex-parse from raw output. They also survive minor model formatting variations better than JSON.

**Trade-off accepted:** Regex parsing is fragile if the model produces malformed tags. Mitigated by strict prompt instructions and fallback to empty recovery_map.

---

### Decision 4: Engine parallelism strategy

**Options considered:**
- Option A: Sequential engine execution (simpler code)
- Option B: asyncio.gather for ROI + Dependency Graph + Contradiction (parallel)

**Chosen:** Option B.

**Why:** These three engines are completely independent (same inputs, different algorithms). Running sequentially wastes ~600–800ms. On Render free tier, every 100ms matters.

**Trade-off accepted:** asyncio.gather means if one engine raises, it cancels the others (unless using `return_exceptions=True`). Use `return_exceptions=True` and handle None results gracefully.

---

### Decision 5: Validation harness timing — synchronous vs background

**Options considered:**
- Option A: Run validation before returning the chat response (user sees validated results)
- Option B: Run validation as a background task (user gets response faster)

**Chosen:** Option B — background task.

**Why:** Validation requires two LLM calls (baseline + LLM judge) plus BERTScore. This adds 3–8 seconds to response time. Unacceptable for a chat UX. Metrics appear in the dashboard after a short delay (~5s).

**Trade-off accepted:** The first response metrics shown to the user are pre-validation (token counts and cost are exact, BERTScore and quality_delta are pending). The dashboard updates when validation completes. UX acceptable.

---

### Decision 6: Speculative prefetcher — MVP vs V2

**Options considered:**
- Option A: Build speculative prefetcher in MVP
- Option B: Defer to V2

**Chosen:** Option B — defer.

**Why:** Speculative prefetcher requires accurate follow-up query prediction. V1 (rule-based templates) produces low-quality predictions that would waste Redis cache space. V2 (LLM-based prediction) adds an extra API call per request. Neither is worth the complexity at MVP stage.

**Trade-off accepted:** Users don't get sub-100ms follow-up responses in MVP. Acceptable — the optimization pipeline itself provides the main value.

## What Was Built

- `ContextOS_LLD_v1.md` — detailed LLD with all schemas, service signatures, data models
- `Agent.md` — AI scaffolding instructions with Gemini-specific prompts
- `docs/HLD/` — README, architecture diagrams, data flow, tech stack rationale
- `docs/LLD/` — README, deep-dives on ROI engine, dependency graph, compression, validation harness
- `docs/Setup/` — local dev, external services, deployment, database migrations
- `docs/Troubleshooting/` — backend setup, LLM providers, deployment
- `docs/SystemExploration/` — engine interactions, performance profile
- `docs/TestDocs/` — testing strategy, evaluation dataset
- `docs/RunLogs/` — this file

## What's Next

1. Read `Agent.md` section 10 (file checklist) and begin scaffolding
2. Start with external services setup (`docs/Setup/external-services.md`)
3. Backend bootstrap (`docs/Setup/local-dev.md`)
4. First real feature: upload pipeline (`POST /api/upload`)
5. Then retrieval, then engines in order

## Lessons Learned

- Writing the LLD forced clarification of several design decisions that were implicit in the HLD (especially: engine parallelism, validation timing, pointer format)
- The Agent.md structure (build order + critical rules + checklist) is the right format for AI-assisted scaffolding — it gives the model guardrails without over-constraining implementation details
- The 512MB Render constraint is the single most constraining factor in the entire architecture — every library choice must be evaluated against memory budget
