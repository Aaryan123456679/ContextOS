# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# ContextOS — single unified image running BOTH the Next.js frontend (:3000)
# and the FastAPI backend (:8000) in one container.
#
#   Build:  docker build -t contextos .
#   Run:    see the run command at the bottom of this file / project notes.
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: build the Next.js frontend ──────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /fe

# Install deps first (better layer caching). The repo uses next15/react19 which
# trip npm's peer resolver, so --legacy-peer-deps is required.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps

# Build-time public config. NEXT_PUBLIC_* values are inlined into the bundle,
# and shell env takes precedence over .env.local, so this points the browser at
# the backend that runs in the SAME container (published on host :8000).
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

COPY frontend/ ./
RUN npm run build

# ── Stage 2: runtime image (Python backend + Node to serve the built frontend)─
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_ENV=production

# System deps:
#   build-essential  → compiling some python wheels
#   psmisc           → provides `fuser` used to free ports 3000/8000
#   libgomp1         → runtime lib needed by torch (sentence-transformers/bert-score)
#   nodejs 20        → to run `next start`
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential curl ca-certificates gnupg psmisc libgomp1 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Backend ──────────────────────────────────────────────────────────────────
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && python -m spacy download en_core_web_sm

COPY backend/ ./backend/

# ── Frontend (copy the already-built app + its node_modules) ──────────────────
COPY --from=frontend-builder /fe/package.json   ./frontend/package.json
COPY --from=frontend-builder /fe/next.config.ts ./frontend/next.config.ts
COPY --from=frontend-builder /fe/node_modules   ./frontend/node_modules
COPY --from=frontend-builder /fe/.next          ./frontend/.next
COPY --from=frontend-builder /fe/public         ./frontend/public
# .env.local carries Clerk keys read by `next start` at runtime (if present)
COPY frontend/.env.local ./frontend/.env.local

# ── Entrypoint ───────────────────────────────────────────────────────────────
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 3000 8000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
