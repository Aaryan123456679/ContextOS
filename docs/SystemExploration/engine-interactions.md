# Engine Interactions

This document tracks known interactions between engines — cases where one engine's output affects another's behavior in non-obvious ways.

---

## ROI Engine × Token Budget Allocator

**Interaction:** ROI scores directly determine which chunks the allocator selects.

**Key insight:** If ROI scores are all similar (e.g., all chunks score 0.85–0.90), the allocator effectively becomes a FIFO selector (first chunks in the candidate pool win). This happens when the query is broad and all retrieved chunks are genuinely relevant.

**Mitigation:** The allocator sorts by `fusion_score / token_count` not `roi_score / token_count`. So a chunk with roi=0.88 but 512 tokens loses to a chunk with roi=0.85 but 100 tokens. This is intentional — token efficiency matters.

---

## Dependency Graph × ROI Engine

**Interaction:** A chunk can have high ROI score but be flagged as a redundant ancestor by the dependency graph. The fusion engine must handle this tension.

**Current resolution:** Dependency redundancy penalty (−0.20 weight) reduces fusion score. A chunk with roi=0.85 that is a redundant ancestor gets:
```
fusion_score ≈ 0.35*0.85 + (-0.20)*1.0 = 0.298 − 0.200 = 0.098
```

This effectively prunes it unless roi is very high (>0.95).

**Edge case:** What if the "redundant" chunk also contains the answer? This can happen for shallow questions where the ancestor IS the relevant content. Monitor via validation harness — if faithfulness drops for short factual queries, the dependency graph penalty is too aggressive.

---

## Contradiction Detector × Fusion Engine

**Interaction:** When two chunks contradict, one is penalized with `contradiction_risk = confidence_score`. The other receives `contradiction_risk = 0`.

**Key insight:** The detector resolves by keeping the more authoritative chunk. But authority is currently estimated by source type and recency — not by ground truth. If resolution is wrong, the correct answer is excluded.

**Mitigation in V2:** Surface both chunks when contradiction confidence < 0.85, let the LLM see both with an explicit note: "These sources disagree on X."

---

## Compression × Recovery Pointer Expansion

**Interaction:** Expanding a pointer mid-conversation changes the context for subsequent turns, but the original optimization_run is immutable.

**Current behavior:** Expansion is returned to the frontend for display only. The next chat turn retrieves fresh context from the original pipeline. Expanded passages are NOT injected into the system prompt automatically.

**V2 plan:** Track which pointers were expanded in the conversation history. On next turn, pin those chunks (bypass ROI filtering) to maintain conversational coherence.

---

## Model Adapter × Compression Output

**Interaction:** The model adapter receives already-compressed text with embedded `[ptr_XX]` references. These references appear verbatim in the LLM's prompt.

**Observation:** Claude handles `[ptr_01]` references naturally — it understands them as placeholders. GPT-4 sometimes tries to "explain" what ptr_01 means. Gemini ignores them.

**Current fix:** Claude adapter wraps PTR references:
```xml
<context>
The following context contains [ptr_XX] references to expandable sections.
{compressed_text}
</context>
```

GPT adapter adds a system note: `Note: [ptr_XX] markers indicate expandable sections — treat them as footnote references.`
