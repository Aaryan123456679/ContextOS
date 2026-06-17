# External Services Setup

All external services use free tier. Create accounts before starting local dev.

---

## 1. Supabase (PostgreSQL + Storage + Auth)

**URL:** https://supabase.com  
**Free tier:** 500MB database, 1GB storage, 50k monthly active users

### Steps

1. Create account → New project → name: `contextos`
2. Note your project URL: `https://<project-id>.supabase.co`
3. Settings → API → copy `anon` public key and `service_role` secret key
4. Settings → Database → copy connection string (use "URI" format with `postgresql://`)

### Run Migrations

In Supabase SQL Editor, run tables in this order (from LLD section 2.1):

```sql
-- 1. users
-- 2. api_keys
-- 3. conversations
-- 4. messages
-- 5. documents
-- 6. chunks
-- 7. optimization_runs
-- 8. compression_records
```

Full DDL in `ContextOS_LLD_v1.md` section 2.1.

### Storage Buckets

Create two buckets in Storage:
- `user-documents` — uploaded files (private)
- `recovery-maps` — (not needed; recovery maps stored in DB as JSONB)

---

## 2. Qdrant Cloud (Vector Store)

**URL:** https://cloud.qdrant.io  
**Free tier:** 1 cluster, 1GB storage, ~500k vectors at 1536-dim

### Steps

1. Create account → New cluster → Free tier → Region: US East
2. Wait ~2 minutes for cluster to spin up
3. Dashboard → cluster → Get API Key
4. Note: cluster URL format is `https://<cluster-id>.us-east.aws.cloud.qdrant.io:6333`

### Create Collection

Run this Python script once:
```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY)
client.create_collection(
    "contextos_chunks",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)
print("Collection created:", client.get_collection("contextos_chunks"))
```

---

## 3. Upstash Redis (Cache)

**URL:** https://upstash.com  
**Free tier:** 10,000 requests/day, 256MB max data

### Steps

1. Create account → Create Database → Region: US East 1 → Free plan
2. Details tab → copy REST URL and REST Token
3. Use the `rediss://` (TLS) connection URL format

### Env variable format
```
UPSTASH_REDIS_URL=rediss://default:<token>@<host>.upstash.io:6380
```

---

## 4. OpenAI (Embeddings + Judge LLM)

**URL:** https://platform.openai.com  
**Cost:** ~$0.0001 per 1k tokens (embedding), ~$0.00015/1k input for gpt-4o-mini (judge)

### Steps

1. Create account → API Keys → Create new secret key
2. Add $5 credit minimum (no free tier for new accounts after March 2023)
3. Note key starts with `sk-`

**Models used:**
- Embeddings: `text-embedding-3-small`
- Compression (fallback): `gpt-4o-mini`
- LLM Judge: `gpt-4o-mini`

---

## 5. Anthropic (Optional — Compression LLM)

**URL:** https://console.anthropic.com  
**Cost:** Claude Haiku 3 — $0.00025/1k input tokens

### Steps

1. Create account → API Keys → Create Key
2. Add credit ($5 minimum)

**Model used:** `claude-haiku-3` for recoverable compression

---

## Environment Variables Summary

After all setup, your `.env` should look like:

```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # service_role key
DATABASE_URL=postgresql://postgres:xxxxx@db.xxxxx.supabase.co:5432/postgres

# Qdrant
QDRANT_URL=https://xxxxx.us-east.aws.cloud.qdrant.io:6333
QDRANT_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Upstash Redis
UPSTASH_REDIS_URL=rediss://default:xxxxx@xxxxx.upstash.io:6380

# Encryption
ENCRYPTION_KEY=<64-hex-chars>  # python3 -c "import secrets; print(secrets.token_hex(32))"

# App
ENVIRONMENT=development
```

User-provided LLM API keys are stored encrypted in the `api_keys` table — not in `.env`.
