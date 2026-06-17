# Progress

Tracks what is built, what is in progress, and what is left.

## Contents

| File | What It Tracks |
|---|---|
| [mvp-checklist.md](mvp-checklist.md) | All MVP features with status |
| [backlog.md](backlog.md) | V2 and V3 features, prioritized |
| [known-issues.md](known-issues.md) | Bugs and known limitations |

## Current Status

**Phase:** Production-ready (deploy via `render.yaml`)
**Date:** June 2026
**Next milestone:** Multi-user auth via Clerk, production monitoring

## Recent updates (June 2026)

- **Validation subsystem removed** — `validate.py`, `evaluate.py` routes, the
  `services/validation/` directory, and all frontend `ValidationResult` references are
  deleted. The evaluate page now shows the engine breakdown panel only.
- **Per-request engine toggles** — users can enable/disable ROI, dependency/distractor,
  contradiction, and compression from the chat input toolbar. Settings are stored
  client-side (settingsStore), sent in `engine_toggles` on each chat request, and
  applied server-side. Server-side defaults still apply when the frontend doesn't supply
  toggles.
- **Learned context-selection in production** — the all-signal GBM policy validated in
  `contextos-evaluation/` (beats density allocator + SOTA LLMLingua-2 at 55/70/85%
  reduction; see [RESULTS.md](../../contextos-evaluation/RESULTS.md)) is wired into
  `chat`/`optimize` routes via `SELECTION_MODE` (`learned` default, auto-falls-back to
  density).
- **Conversation rename & delete** — `PATCH`/`DELETE /api/history/{id}` + sidebar hover actions.
- **Model gating + API-key modal** — free tier runs on server-side Gemini with no key;
  OpenAI/Anthropic models unlock only after the user adds their key (stored client-side).
- **Published evaluation results** — see `contextos-evaluation/RESULTS.md`.
- **render.yaml updated** — includes all env vars with descriptions; engine toggle
  defaults (ROI on, dependency/contradiction/compression off); retrieval limit; health
  check path.

## Deployment

### Backend (Render)

```bash
# 1. Push to GitHub — autoDeploy is enabled in render.yaml
git push origin main

# 2. In the Render dashboard, set the following secrets (never commit values):
#    GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
#    DATABASE_URL (PostgreSQL connection string)
#    QDRANT_URL, QDRANT_KEY
#    ENCRYPTION_KEY (32-byte hex, generate with: openssl rand -hex 32)
#
# 3. After the first deploy, update CORS_ORIGINS to your Vercel frontend URL.
```

### Frontend (Vercel)

```bash
# Set in Vercel environment variables:
#   NEXT_PUBLIC_API_URL = https://<your-render-service>.onrender.com
#
# Then: vercel --prod
```

### Health check

`GET /health` returns `{"status": "ok", "timestamp": "..."}`. Render probes this path
after each deploy; a non-200 response blocks the deploy.

## Legend

| Symbol | Meaning |
|---|---|
| ✅ | Complete |
| 🔄 | In Progress |
| ⏳ | Not Started |
| ❌ | Blocked |
| 🚫 | Deferred to V2 |
