# Local Development Setup

**Platform:** M1 MacBook Pro · Python 3.12 · Node 20

## Prerequisites

```bash
# Node — must be 18+, recommend 20 via nvm
nvm install 20 && nvm use 20
node --version   # v20.x

# Python 3.12
brew install python@3.12
python3.12 --version
```

---

## Backend

```bash
cd backend

# Virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Dependencies (includes scikit-learn for learned selector, sentence-transformers, etc.)
pip install -r requirements.txt

# spaCy model (dependency graph engine)
python -m spacy download en_core_web_sm

# Configure environment
cp .env.example .env
# Fill in: DATABASE_URL, QDRANT_URL, QDRANT_KEY, GEMINI_API_KEY, ENCRYPTION_KEY
# Optional: OPENAI_API_KEY, ANTHROPIC_API_KEY (only needed if users add those keys)

# Start (port 8001 to match frontend .env.local)
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**Verify:**
```bash
curl http://localhost:8001/health
# {"status": "ok", "timestamp": "..."}
```

### Engine defaults (local)

The following are OFF by default (match production defaults in `render.yaml`):

| Env var | Default | Reason |
|---|---|---|
| `SELECTION_MODE` | `learned` | GBM policy beats density + SOTA |
| `RETRIEVAL_LIMIT` | `24` | Tuned pool size |
| `ENABLE_DEPENDENCY_ENGINE` | `false` | ~0 ablation contribution, +3–5s latency |
| `ENABLE_CONTRADICTION_ENGINE` | `false` | ~0 ablation contribution |
| `COMPRESSION_ENABLED` | `false` | Over-compressed in eval; selection is the optimizer |

Users can override all of these per-request from the engine toggles panel in the UI.

### Model warm-up

On first request, `cross-encoder/ms-marco-MiniLM-L-6-v2` (~22 MB) and `cross-encoder/nli-deberta-v3-small` (~180 MB) download automatically. The server pre-warms them 3 s after startup in a background task so the first user request isn't slow.

---

## Frontend

```bash
cd frontend

npm install

# .env.local is already present with:
#   NEXT_PUBLIC_API_URL=http://localhost:8001
# Update if you're running the backend on a different port.

# Must use Node 20 (Next.js 15 requires node:events which isn't in Node 14)
nvm use 20
npm run dev
# → http://localhost:3000
```

The app redirects `/` and `/chat` to `/chat/{clientId}` where `clientId` is a stable UUID stored in `localStorage` — each browser gets its own conversation history.

---

## Running both together

```bash
# Terminal 1 — backend
cd backend && source .venv/bin/activate && uvicorn main:app --port 8001 --reload

# Terminal 2 — frontend
cd frontend && nvm use 20 && npm run dev
```

---

## Database

Tables are managed in Supabase. See [database-migrations.md](database-migrations.md) for the full schema.

**Quick check** — verify all tables exist:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
-- Expected: api_keys, chunks, compression_records, conversations,
--           documents, messages, optimization_runs, users
```

**Local Qdrant** (optional — skip if using Qdrant Cloud):
```bash
docker run -p 6333:6333 qdrant/qdrant
# Set QDRANT_URL=http://localhost:6333, QDRANT_KEY= (empty) in .env
```

---

## Common issues

| Symptom | Fix |
|---|---|
| `Cannot find module 'node:events'` | Switch to Node 20: `nvm use 20` |
| `[Errno 48] Address already in use` | `lsof -ti :8001 \| xargs kill -9` |
| First request very slow (~30s) | Expected — model warm-up on first load |
| 500 on DELETE conversation | Fixed — delete order: compression_records → validation_results → optimization_runs → messages → conversations |
| Free Gemini quota hit | Add your own Gemini key in the model selector, or try again tomorrow |

See [../Troubleshooting/backend-setup.md](../Troubleshooting/backend-setup.md) for more.
