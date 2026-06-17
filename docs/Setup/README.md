# Setup

All setup guides for ContextOS. Follow in order for a fresh installation.

## Contents

| File | What It Sets Up |
|---|---|
| [local-dev.md](local-dev.md) | Full local dev environment (M1 Mac) |
| [external-services.md](external-services.md) | Qdrant Cloud, Supabase, Upstash Redis |
| [deployment.md](deployment.md) | Render (backend) + Vercel (frontend) |
| [api-keys.md](api-keys.md) | LLM provider API keys setup |
| [database-migrations.md](database-migrations.md) | PostgreSQL table creation order |

## Quick Start (30 minutes)

1. [external-services.md](external-services.md) — create accounts and get credentials
2. [local-dev.md](local-dev.md) — install dependencies, configure .env
3. Verify: `uvicorn main:app --reload` and `npm run dev` both run without errors
4. [database-migrations.md](database-migrations.md) — create all tables
5. Upload a test file, send a test chat message
