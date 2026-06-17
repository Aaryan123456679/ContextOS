# MVP Checklist

**Status as of June 2026 — production-ready.**

## Documentation ✅

- [x] HLD v2.0 complete
- [x] LLD v1.0 complete (validation harness doc removed — feature deleted)
- [x] docs/ folder structure complete
- [x] Evaluation results published (`contextos-evaluation/RESULTS.md`)

---

## Infrastructure ✅

- [x] External services created (Supabase, Qdrant Cloud, Upstash Redis)
- [x] Backend Python environment (`.venv`, Python 3.12)
- [x] Frontend Node environment (Node 20, Next.js 15)
- [x] `.env` / `.env.local` configured
- [x] Database tables created (see `database-migrations.md`)
- [x] Qdrant collection created and indexed
- [x] Health check endpoint working (`GET /health`)

---

## Backend — Core ✅

- [x] `core/config.py` — Pydantic settings with engine toggle flags
- [x] `core/database.py` — SQLAlchemy async engine (asyncpg)
- [x] `core/vector_store.py` — Qdrant async client
- [x] `core/exceptions.py` — custom exception hierarchy

---

## Backend — Data Models ✅

- [x] SQLAlchemy ORM models (users, api_keys, conversations, messages, documents, chunks, optimization_runs, compression_records)
- [x] Pydantic schemas (chat, chunk, compression, optimize) — validation schema removed

---

## Backend — Ingestion ✅

- [x] `FileParser` — PDF (Docling), DOCX, TXT, MD, CSV
- [x] `Chunker` — recursive / sentence / paragraph strategies
- [x] `Embedder` — batch 100, Gemini `text-embedding-004`
- [x] `POST /api/upload` — end-to-end

---

## Backend — Retrieval ✅

- [x] `SemanticRetriever` — Qdrant dense search
- [x] `KeywordRetriever` — BM25
- [x] `HybridRetriever` — RRF fusion
- [x] Retrieval pool size: `RETRIEVAL_LIMIT=24` (tuned default)

---

## Backend — Engines ✅

- [x] `ROIEngine` — CrossEncoder reranking (dominant selection signal)
- [x] `DependencyGraphBuilder` — frontier detection, pruning mask (OFF by default — ablation showed ~0 contribution)
- [x] `ContradictionDetector` — NLI pairwise (OFF by default — ~0 contribution)
- [x] `FusionEngine` — weighted multi-signal scoring
- [x] `TokenBudgetAllocator` — greedy knapsack (density fallback)
- [x] `LearnedSelector` — GBM 13-signal policy (AUC 0.82–0.85, beats SOTA)
- [x] `RecoverableCompressor` — LLM compression (OFF by default)
- [x] `ModelContextAdapter` — Claude/GPT/Gemini prompt formatting
- [x] **Per-request engine toggles** — frontend settings panel → `engine_toggles` in ChatRequest → server applies overrides over defaults

---

## Backend — LLM Gateway ✅

- [x] `GeminiProvider` — async, free-tier rotation (highest-limit model first)
- [x] `OpenAIProvider` — async (user key required)
- [x] `AnthropicProvider` — async (user key required)
- [x] `CostTracker` — per-request cost calculation
- [x] Retry + quota-rotation logic for free Gemini tier

---

## Backend — API Routes ✅

- [x] `POST /api/chat` — full pipeline with per-request engine toggles
- [x] `POST /api/upload` — file ingestion
- [x] `POST /api/optimize` — standalone optimization
- [x] `GET /api/metrics` — aggregate metrics
- [x] `GET /api/history` — conversation list (per user)
- [x] `PATCH /api/history/{id}` — rename conversation
- [x] `DELETE /api/history/{id}` — delete conversation + all dependent rows
- [x] `GET /api/history/{id}/messages` — load conversation messages
- [x] `GET /api/compression/{id}` — fetch recovery map
- [x] Auth middleware (placeholder — permissive, ready for JWT)
- [x] Rate limiting middleware
- [x] CORS configured
- [x] ~~`POST /api/validate`~~ — removed
- [x] ~~`POST /api/evaluate`~~ — removed

---

## Frontend ✅

- [x] Next.js 15 / React 19 project
- [x] `lib/types.ts` — all TypeScript interfaces (ValidationResult removed)
- [x] `lib/api.ts` — typed API client (evaluate() removed)
- [x] `lib/clientId.ts` — stable per-browser UUID for anonymous sessions
- [x] `stores/chatStore.ts` — Zustand, conversation CRUD
- [x] `stores/settingsStore.ts` — model + key + engine toggles
- [x] `components/chat/ChatWindow.tsx` — doc chips, engine toggles button
- [x] `components/chat/EngineToggles.tsx` — toggle panel (ROI / dependency / contradiction / compression)
- [x] `components/chat/FileUploadZone.tsx` — paperclip icon upload (ChatGPT style)
- [x] `components/chat/ModelSelector.tsx` — shows only unlocked models
- [x] `components/chat/AddModelModal.tsx` — pick model → add provider key → unlock
- [x] `components/chat/ConversationSidebar.tsx` — history, rename, delete
- [x] `components/dashboard/EngineBreakdown.tsx`
- [x] `components/evaluate/SideBySide.tsx` — simplified (no ValidationBadge)
- [x] `components/evaluate/RecoveryPointerViewer.tsx`
- [x] ~~`components/evaluate/ValidationBadge.tsx`~~ — removed
- [x] `app/chat/page.tsx` → redirects to `/chat/{clientId}`
- [x] `app/chat/[clientId]/page.tsx` — dynamic per-client route
- [x] B&W theme (brand palette = grayscale)

---

## Testing ⏳

- [ ] Playwright E2E suite (needs rewrite for new routes + engine toggles)
- [ ] Unit tests for engines
- [ ] TypeScript strict-mode clean compile

---

## Deployment ✅ (config ready)

- [x] `render.yaml` — all env vars documented, engine defaults set
- [x] Backend `Dockerfile` present
- [x] CORS configured for production
- [ ] Backend live on Render (pending first push)
- [ ] Frontend live on Vercel (pending first push)
- [ ] UptimeRobot ping configured

---

## Research Validation ✅

- [x] Beat-SOTA: ContextOS learned selection > LLMLingua-2 at 55/70/85% reduction (n=2,000, gpt-4o-mini, 95% bootstrap CI, all significant)
- [x] Cross-dataset AUC 0.82–0.85 (HotpotQA ↔ MuSiQue)
- [x] Learned policy ported to production (`services/engines/learned_select.py`)
- [x] Results published in `contextos-evaluation/RESULTS.md`
