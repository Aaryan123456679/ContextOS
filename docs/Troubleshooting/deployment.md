# Troubleshooting — Deployment

## Render — Build fails: spaCy download

**Symptom:** Build fails at `python -m spacy download en_core_web_sm`

**Fix:** Render build step runs as shell command. Ensure the build command is:
```
pip install -r requirements.txt && python -m spacy download en_core_web_sm
```

Not as two separate commands (they run in the same shell).

---

## Render — OOM (Out of Memory) kill

**Symptom:** Render logs show `Killed` with no other message, or `signal: killed (SIGKILL)`

**Root cause:** Total memory exceeded 512MB.

**Diagnosis:**
```python
# Add to /health endpoint temporarily
import psutil, os
proc = psutil.Process(os.getpid())
return {"status": "ok", "memory_mb": proc.memory_info().rss / 1024 / 1024}
```

**Fixes:**
1. Verify `en_core_web_sm` not `_lg` (50MB vs 750MB)
2. Verify models are singletons — `get_cross_encoder()` not `CrossEncoder(...)` per request
3. Cap contradiction detection to 20 chunks, not all chunks
4. If still OOM, disable NLI model temporarily: set `DISABLE_CONTRADICTION=true` env var

---

## Render — Cold start (service sleeps)

**Symptom:** First request takes 30–60 seconds after idle

**Fix:** Ensure UptimeRobot is pinging `/health` every 14 minutes. Check UptimeRobot dashboard for failed pings.

Also ensure the `/health` endpoint is lightweight — no DB calls:
```python
@app.get("/health")
async def health():
    return {"status": "ok"}  # no DB queries here
```

---

## Render — Environment variable not found

**Symptom:** `KeyError: 'QDRANT_URL'` in startup

**Fix:** Add the variable in Render dashboard → Environment → Add Environment Variable. Render does not read `.env` files — variables must be set in the dashboard.

---

## Vercel — Build fails: TypeScript errors

**Symptom:** Vercel build log shows type errors that didn't appear locally

**Fix:** Vercel runs `next build` which does full type checking. Locally you may have been using `--turbo` mode which skips some checks. Fix all TypeScript errors:
```bash
cd frontend
npx tsc --noEmit  # mirrors what Vercel runs
```

---

## Vercel — API calls fail with CORS error

**Symptom:** Browser console: `Access-Control-Allow-Origin missing`

**Fix:** The backend CORS middleware must include the Vercel deployment URL. Update `main.py`:
```python
allow_origins=[
    "https://your-app.vercel.app",
    "https://your-custom-domain.com",
    "http://localhost:3000",
]
```

Redeploy backend after updating.

---

## Vercel — NEXT_PUBLIC env vars not available at runtime

**Symptom:** `process.env.NEXT_PUBLIC_API_URL` is `undefined` in browser

**Fix:** Variables starting with `NEXT_PUBLIC_` must be set in Vercel dashboard → Settings → Environment Variables. They are baked into the build — not available from `.env.local` in production.

---

## Frontend can't reach backend

**Symptom:** All API calls return `Failed to fetch` or `ERR_CONNECTION_REFUSED`

**Checklist:**
1. `NEXT_PUBLIC_API_URL` is set to the Render URL (not localhost)
2. Render service is not sleeping (visit it directly to wake it)
3. CORS is configured on backend for the Vercel domain
4. Render logs show no startup errors
