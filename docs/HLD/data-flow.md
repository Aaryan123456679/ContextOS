# Data Flow — End-to-End Request Lifecycle

## Upload Flow

```
User uploads file (PDF/DOCX/TXT/URL)
  │
  POST /api/upload
  │
  ├─ FileParser.parse(file) → raw_text: str
  ├─ Chunker.chunk(raw_text) → chunks: list[ChunkRaw]
  │   └─ each chunk: {content, start_char, end_char, token_count}
  ├─ Embedder.embed_batch(chunks, batch=100) → vectors: list[list[float]]
  ├─ Qdrant.upsert(collection, vectors + payloads)
  ├─ Supabase: INSERT INTO documents ...
  └─ Supabase: INSERT INTO chunks ... (batch)
  │
  Response: { document_id, chunk_count }
```

---

## Chat Flow (Full Pipeline)

```
User sends message + [optional document_ids]
  │
  POST /api/chat
  │
  Step 1 — Query Analysis
  ├─ QueryUnderstanding.analyze(message)
  │   ├─ spaCy NER → entities
  │   ├─ intent classifier → intent ("debug" | "factual" | ...)
  │   ├─ depth estimation → surface | intermediate | deep
  │   └─ query reformulation → cleaner retrieval query
  │
  Step 2 — Retrieval
  ├─ SemanticRetriever.retrieve(reformulated_query)
  │   ├─ Embedder.embed(query) → query_vector
  │   └─ Qdrant.search(query_vector, top_k=50) → semantic_hits
  ├─ KeywordRetriever.retrieve(query, chunks) → keyword_hits (top 30)
  └─ HybridRetriever.fuse(semantic_hits, keyword_hits) → candidate_pool
      └─ Reciprocal Rank Fusion → merged + deduplicated, ~50–200 chunks
  │
  Step 3 — Parallel Engine Scoring [asyncio.gather]
  ├─ ROIEngine.score(query, candidate_pool)
  │   └─ CrossEncoder rerank → roi_score ∈ [0,1] per chunk
  ├─ DependencyGraph.build(query, candidate_pool)
  │   ├─ Extract concepts from query + chunks (spaCy)
  │   ├─ Build directed concept graph (NetworkX)
  │   ├─ BFS backward from target concepts
  │   └─ pruning_mask: {chunk_id: bool} (True = prune)
  └─ ContradictionDetector.detect(candidate_pool[:20])
      ├─ NLI on pairwise chunk combinations (max 20 → 190 pairs)
      └─ contradiction_flags: list[ContradictionFlag]
  │
  Step 4 — Fusion + Allocation
  ├─ FusionEngine.score(chunks, roi, dep, contra)
  │   └─ Utility = α·roi − β·dep_redundancy − γ·contra_risk
  └─ TokenBudgetAllocator.allocate(scored_chunks, budget=8192)
      └─ Greedy knapsack (sort by utility/token, fill budget)
      └─ selected: list[ScoredChunk], total_tokens ≤ budget
  │
  Step 5 — Compression
  ├─ RecoverableCompressor.compress(selected, query)
  │   ├─ Build compression prompt
  │   ├─ Call Claude Haiku / GPT-4o-mini
  │   ├─ Parse [PTR:...] tags → recovery_map
  │   └─ Return {compressed_text, recovery_map, token_counts}
  │
  Step 6 — Model Adaptation
  └─ ModelContextAdapter.adapt(compressed_text, model, query)
      ├─ Claude → XML-tagged format
      ├─ GPT → prose-first, role-framed
      └─ Gemini → citation-anchored
  │
  Step 7 — LLM Inference
  └─ LLMGateway.complete(adapted_context, model, api_key)
      ├─ Route to OpenAI / Anthropic / Gemini provider
      ├─ Record usage (prompt_tokens, completion_tokens)
      └─ Return LLMResponse {content, usage, latency_ms}
  │
  Step 8 — Metrics + Persistence
  ├─ Compute OptimizationMetrics
  │   ├─ token_reduction = 1 - (compressed_tokens / original_tokens)
  │   ├─ cost_reduction = 1 - (optimized_cost / baseline_cost)
  │   └─ engine_breakdown per engine
  ├─ Supabase: INSERT INTO messages (user + assistant)
  ├─ Supabase: INSERT INTO optimization_runs
  └─ Supabase: INSERT INTO compression_records
  │
  Step 9 — Background Tasks (non-blocking)
  ├─ ValidationHarness.evaluate(query, baseline_ctx, optimized_ctx, model)
  │   ├─ Run baseline path (raw top-10 chunks → LLM)
  │   ├─ BERTScore F1 (optimized vs baseline response)
  │   ├─ LLM Judge (GPT-4o-mini rates both 1-10)
  │   ├─ Faithfulness (NLI entailment check)
  │   └─ Supabase: UPDATE optimization_runs SET validation_result
  └─ SpeculativePrefetcher.prefetch(query) [V2]
      ├─ Predict 3 likely follow-up queries
      └─ Redis.setex(prefetch:{hash}, 600, optimized_context)
  │
  Response: ChatResponse {
    message_id, content,
    optimization_run_id,
    metrics: { original_tokens, optimized_tokens, reduction_pct,
               cost_original, cost_optimized, bert_score, quality_score,
               engine_breakdown }
  }
```

---

## Recovery Pointer Expansion Flow

```
User clicks on [ptr_01] in RecoveryPointerViewer
  │
  POST /api/expand/ptr_01 { compression_id: UUID }
  │
  ├─ Fetch compression_record from Supabase
  ├─ Get recovery_map[ptr_01] → {source_doc, byte_range, summary}
  ├─ Fetch original bytes from Supabase Storage (byte_range)
  ├─ Decode → original passage text
  ├─ Log expansion event to expansion_log
  └─ Return { ptr_id, original_text, summary }
```
