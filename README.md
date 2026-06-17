# ContextOS

**Context Intelligence Operating System for LLMs.**  
ContextOS reduces the tokens you send to an LLM — cutting cost and latency — while keeping answer quality equal to or better than sending the full context.

Live demo: [contextos.vercel.app](https://contextos.vercel.app)

---

## What it does

When you ask a question over a large document set, most of the retrieved context is noise, redundancy, or distraction. ContextOS runs a pipeline of engines that score, rank, and select only the chunks that actually matter — then hands that tight context to the LLM.

The optimizer is a **learned selection policy** (gradient-boosted model, 13 signals) trained on HotpotQA + MuSiQe. It was validated against the current state-of-the-art token compressor in a controlled evaluation:

| Reduction target | LLMLingua-2 (SOTA) | **ContextOS** | Margin |
|---|---|---|---|
| 55% | 0.504 F1 | **0.559 F1** | +0.055 * |
| 70% | 0.410 F1 | **0.519 F1** | +0.108 * |
| 85% | 0.266 F1 | **0.441 F1** | +0.174 * |

*n = 2,000 (HotpotQA + MuSiQue), generator gpt-4o-mini, 95% bootstrap CIs, all differences statistically significant.*  
Full results: [`contextos-evaluation/RESULTS.md`](contextos-evaluation/RESULTS.md)

---

## Pipeline

```
Upload → Chunk → Embed → Qdrant
                              ↓
Query → Hybrid Retrieval (semantic + BM25, pool = 24)
                              ↓
         ROI Engine (cross-encoder relevance scoring)
                              ↓
         Fusion (multi-signal scoring)
                              ↓
         Learned Selection (GBM policy, AUC 0.82–0.85)
                              ↓
         LLM Call (Gemini / GPT / Claude)
```

All engines except ROI are off by default (ablation showed ~0 contribution from dependency-graph and contradiction engines — honest result). Users can toggle any engine per-request from the UI.

---

## Features

- **Free tier** — runs on server-side Gemini, no key required
- **BYO key** — add OpenAI or Anthropic key to unlock GPT/Claude models
- **Per-request engine toggles** — ROI, dependency, contradiction, compression on/off
- **Document upload** — PDF, DOCX, TXT, MD, CSV; removable per-file chips in the UI
- **Conversation history** — rename, delete, persistent per browser
- **B&W minimal UI** — Next.js 15, React 19, Tailwind

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, Tailwind, Zustand |
| Backend | FastAPI, Python 3.12, asyncpg |
| Embeddings | Gemini `text-embedding-004` |
| Vector store | Qdrant Cloud |
| Database | Supabase (PostgreSQL) |
| ML models | `cross-encoder/ms-marco-MiniLM-L-6-v2`, GBM (scikit-learn) |
| Auth | Clerk |
| Deployment | Render (backend), Vercel (frontend) |

---

## Local development

**Requirements:** Python 3.12, Node 20 (`nvm use 20`), Supabase project, Qdrant Cloud cluster.

```bash
# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env   # fill in DATABASE_URL, QDRANT_URL, QDRANT_KEY, GEMINI_API_KEY, ENCRYPTION_KEY
uvicorn main:app --port 8001 --reload

# Frontend (new terminal)
cd frontend
nvm use 20
npm install
# .env.local already has NEXT_PUBLIC_API_URL=http://localhost:8001
npm run dev
```

Visit `http://localhost:3000`.

Full setup guide: [`docs/Setup/local-dev.md`](docs/Setup/local-dev.md)

---

## Deployment

Deployment is driven by `render.yaml`. Push to `main` and Render auto-deploys the backend; Vercel auto-deploys the frontend.

Step-by-step: [`docs/Setup/deployment.md`](docs/Setup/deployment.md)

---

## Evaluation

The research evaluation suite lives in [`contextos-evaluation/`](contextos-evaluation/) — independent of the production backend, fully reproducible.

```bash
cd contextos-evaluation
pip install -r requirements.txt

# Reproduce the beat-SOTA Pareto run (requires OpenRouter key + credits)
python -m bench.pareto --dataset mix --limit 2000 --levels 0.55,0.70,0.85 \
    --provider openrouter --model openai/gpt-4o-mini
```

---

## Project structure

```
backend/                  FastAPI backend
  api/routes/             chat, upload, optimize, history, metrics, compression
  services/engines/       roi_engine, fusion, dependency_graph, contradiction,
                          learned_select, compression, token_budget
  models/                 SQLAlchemy ORM + Pydantic schemas
  core/                   config, database, vector_store

frontend/                 Next.js frontend
  app/                    /chat/[clientId], /evaluate, /dashboard
  components/chat/        ChatWindow, MessageBubble, FileUploadZone,
                          ModelSelector, AddModelModal, EngineToggles,
                          ConversationSidebar
  stores/                 chatStore, settingsStore
  lib/                    api.ts, types.ts, clientId.ts

contextos-evaluation/     Research evaluation suite (independent)
  bench/                  pareto.py — beat-SOTA benchmark
  RESULTS.md              Published evaluation results

docs/
  Setup/                  local-dev, deployment, database-migrations
  Progress/               mvp-checklist, backlog
  LLD/                    per-engine detailed design
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
# ContextOS
