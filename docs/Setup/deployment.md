# Deployment

## Backend → Render

Deployment is driven by `render.yaml` at the repo root. Push to `main` and Render auto-deploys.

### First-time setup

1. Render dashboard → **New → Blueprint** → connect the GitHub repo → Render reads `render.yaml` automatically.
2. Set the following **secrets** in the Render dashboard (Environment → Secret Files or individual env vars). Never commit values.

| Key | What it is |
|---|---|
| `GEMINI_API_KEY` | Server-side Gemini key for free-tier users |
| `OPENAI_API_KEY` | Optional — only needed if you want server-side GPT |
| `ANTHROPIC_API_KEY` | Optional — only needed if you want server-side Claude |
| `DATABASE_URL` | Supabase `postgresql+asyncpg://...` connection string |
| `QDRANT_URL` | Qdrant Cloud cluster URL |
| `QDRANT_KEY` | Qdrant Cloud API key |
| `UPSTASH_REDIS_URL` | Upstash Redis REST URL |
| `ENCRYPTION_KEY` | 32-byte hex string (`openssl rand -hex 32`) |

3. After first deploy, set `CORS_ORIGINS` to your Vercel frontend URL (e.g. `https://contextos.vercel.app`).

### Engine defaults on Render

Defined in `render.yaml` — no dashboard changes needed:

```
SELECTION_MODE=learned         # GBM policy (beats SOTA)
RETRIEVAL_LIMIT=24             # tuned pool size
ENABLE_DEPENDENCY_ENGINE=false # ~0 ablation contribution
ENABLE_CONTRADICTION_ENGINE=false
COMPRESSION_ENABLED=false      # selection is the optimizer
```

Users can override all four per-request from the engine toggles panel.

### Cold start prevention

Render free tier sleeps after 15 min of inactivity. Register the health endpoint with a free uptime monitor:

- **UptimeRobot** (free): https://uptimerobot.com → New Monitor → HTTP(s) → `https://your-app.onrender.com/health` → interval **14 minutes**

---

## Frontend → Vercel

1. Vercel dashboard → **New Project** → Import GitHub repo
2. Root Directory: `frontend/`
3. Framework: Next.js (auto-detected)
4. Environment Variables:

```
NEXT_PUBLIC_API_URL          = https://your-backend.onrender.com
NEXT_PUBLIC_SUPABASE_URL     = https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY = eyJ...   # anon key only
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = pk_live_...
CLERK_SECRET_KEY             = sk_live_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL  = /sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL  = /sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL  = /chat
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL  = /chat
```

5. Deploy. Each push to `main` triggers an automatic redeploy.

---

## Deployment checklist

```
[ ] Backend /health returns 200
[ ] Supabase: all 8 tables present (see database-migrations.md)
[ ] Qdrant: contextos_chunks collection exists
[ ] POST /api/upload accepts a PDF → chunk_count > 0
[ ] POST /api/chat returns a response with metrics
[ ] DELETE /api/history/{id} returns {"deleted": true} (not 500)
[ ] Frontend loads at Vercel URL
[ ] /chat redirects to /chat/{clientId}
[ ] Model selector shows free Gemini tier with no key
[ ] Add-model modal unlocks a paid model after entering a key
[ ] Engine toggles panel opens and persists on reload
[ ] Conversation history appears in sidebar after a chat
[ ] Rename conversation saves on blur/enter
[ ] Delete conversation removes it permanently from sidebar
[ ] UptimeRobot pinging /health every 14 min
```

---

## CORS

`render.yaml` sets `CORS_ORIGINS=https://contextos.vercel.app`. For a custom domain or multiple origins, set the value as a comma-separated list and update `core/config.py` parsing accordingly. Local dev uses `*` (open) when `ENVIRONMENT != production`.
