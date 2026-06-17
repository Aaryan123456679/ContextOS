# Tech Stack Rationale

Every technology choice is constrained by: free-tier deployability, no self-hosted GPU, M1 MacBook dev, 512MB Render limit.

## Backend — FastAPI + Python 3.11

**Why FastAPI:** async-native, automatic OpenAPI docs, Pydantic integration, fastest Python API framework for I/O-bound workloads.  
**Why Python:** sentence-transformers, spaCy, bert-score, networkx — all Python-native. No equivalent JS ecosystem.  
**Why 3.11:** best async performance, no 3.12 breaking changes in deps yet.

## Frontend — Next.js 15 + TypeScript + TailwindCSS

**Why Next.js:** Server components for SEO, App Router for clean layouts, Vercel-native deployment.  
**Why TypeScript:** Type safety critical for the complex optimization metrics payload.  
**Why Tailwind:** Fastest to build dashboard UI without a component library overhead.

## Vector Store — Qdrant Cloud

**Why Qdrant:** Best free tier (1GB), supports async Python client, native payload filtering for user-scoped retrieval.  
**Why not Pinecone:** Free tier limited to 100k vectors; 1GB Qdrant handles ~500k 1536-dim vectors.  
**Why not Chroma:** No managed cloud free tier; can't self-host on Render free.

## Relational DB — Supabase PostgreSQL

**Why Supabase:** Free PostgreSQL + Auth + Storage in one. Storage needed for recovery pointer source files. Auth needed for API key scoping.  
**Why not PlanetScale:** No free tier persistence after Jan 2024.  
**Why not Railway:** Not reliably free.

## Cache — Upstash Redis

**Why Upstash:** Serverless Redis, no persistent connection needed, compatible with Render free (which sleeps). 10k req/day free.  
**Why Redis:** TTL-based prefetch cache is a natural fit. Standard for ephemeral short-lived data.

## Embeddings — OpenAI text-embedding-3-small

**Why text-embedding-3-small:** Cheapest capable embedding model (~$0.0001/1k tokens), 1536-dim, excellent quality.  
**Why not self-hosted:** No GPU on Render; CPU embedding of 200 chunks would take 30+ seconds.  
**Why not sentence-transformers for embeddings:** Would consume 200MB+ of the 512MB Render limit.

## Reranker — cross-encoder/ms-marco-MiniLM-L-6-v2

**Why cross-encoder:** Best precision for ROI scoring without needing GPT-class inference. Runs on CPU.  
**Why MiniLM-L-6:** 22MB model, ~100ms per 50 pairs on CPU. Fits comfortably in 512MB.

## NLI — cross-encoder/nli-deberta-v3-small

**Why deberta-v3-small:** Best NLI accuracy in the small model category. CPU-compatible.  
**Why not full deberta-v3:** Would push memory over limit.

## NLP — spaCy en_core_web_sm

**Why spaCy:** Best NER pipeline for concept extraction. `en_core_web_sm` is 50MB.  
**Why not NLTK:** spaCy NER is significantly better for named entity extraction.  
**Why not en_core_web_lg:** 750MB — would OOM on Render.

## Compression LLM — Claude Haiku / GPT-4o-mini

**Why not self-hosted:** See Render constraint. No GPU.  
**Why Haiku:** Cheapest Anthropic model with instruction-following quality needed for pointer parsing.  
**Why 4o-mini as fallback:** User may bring OpenAI key only.

## Eval — bert-score

**Why BERTScore:** Gold standard semantic similarity metric for NLG evaluation. F1 score correlates well with human judgment.  
**Why not ROUGE:** ROUGE is lexical, misses semantic equivalence. Not appropriate for compressed context eval.
