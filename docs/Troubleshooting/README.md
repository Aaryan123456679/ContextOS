# Troubleshooting

Organized by subsystem. Each file covers symptoms, root causes, and fixes.

## Contents

| File | Subsystem |
|---|---|
| [backend-setup.md](backend-setup.md) | Python environment, dependency install, startup errors |
| [engines.md](engines.md) | ROI engine, dependency graph, contradiction detector |
| [ingestion.md](ingestion.md) | File parsing, chunking, embedding, Qdrant upsert |
| [retrieval.md](retrieval.md) | Semantic search, BM25, hybrid fusion |
| [compression.md](compression.md) | Recovery pointer parsing, expansion failures |
| [llm-providers.md](llm-providers.md) | API key errors, rate limits, provider outages |
| [validation.md](validation.md) | BERTScore, LLM judge, faithfulness check |
| [frontend.md](frontend.md) | Next.js build errors, API connection, UI issues |
| [deployment.md](deployment.md) | Render cold starts, memory OOM, Vercel build failures |
| [database.md](database.md) | Supabase connection, Qdrant, Redis |

## General Debug Steps

Before opening a specific guide, check these:

1. **Backend logs:** `uvicorn main:app --reload` output in terminal
2. **Frontend errors:** Browser console (F12 → Console)
3. **Render logs:** Dashboard → Web Service → Logs tab
4. **Supabase logs:** Dashboard → Logs → API logs
5. **Qdrant dashboard:** Verify collection exists and has points

## Reporting a Bug

When filing a bug report, include:
- Environment: local / Render / Vercel
- The exact error message (full traceback if Python)
- The request that triggered it (endpoint + payload if safe to share)
- Logs from the relevant service
