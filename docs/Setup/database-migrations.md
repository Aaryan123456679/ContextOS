# Database Migrations

All tables live in Supabase (PostgreSQL). Run in the order listed — foreign key dependency order.

## Migration 001 — users

```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    settings    JSONB DEFAULT '{}'
);
```

## Migration 002 — api_keys

```sql
CREATE TABLE api_keys (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    provider     TEXT NOT NULL CHECK (provider IN ('openai', 'anthropic', 'gemini')),
    key_hash     TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
```

## Migration 003 — conversations

```sql
CREATE TABLE conversations (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    title        TEXT,
    model        TEXT NOT NULL,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_conversations_user ON conversations(user_id);
```

## Migration 004 — messages

```sql
CREATE TABLE messages (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role             TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content          TEXT NOT NULL,
    token_count      INTEGER,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
```

## Migration 005 — documents

```sql
CREATE TABLE documents (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    filename     TEXT NOT NULL,
    file_type    TEXT NOT NULL,
    storage_path TEXT,
    chunk_count  INTEGER DEFAULT 0,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_documents_user ON documents(user_id);
```

## Migration 006 — chunks

```sql
CREATE TABLE chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id  UUID REFERENCES documents(id) ON DELETE CASCADE,
    qdrant_id    TEXT NOT NULL,
    content      TEXT NOT NULL,
    token_count  INTEGER NOT NULL,
    chunk_index  INTEGER NOT NULL,
    metadata     JSONB DEFAULT '{}'
);
CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_chunks_qdrant ON chunks(qdrant_id);
```

## Migration 007 — optimization_runs

```sql
CREATE TABLE optimization_runs (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id       UUID REFERENCES conversations(id),
    query                 TEXT NOT NULL,
    original_token_count  INTEGER,
    optimized_token_count INTEGER,
    token_reduction_pct   FLOAT,
    cost_original         FLOAT,
    cost_optimized        FLOAT,
    bert_score            FLOAT,
    quality_score         FLOAT,
    engine_breakdown      JSONB DEFAULT '{}',
    created_at            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_runs_conversation ON optimization_runs(conversation_id);
CREATE INDEX idx_runs_created ON optimization_runs(created_at DESC);
```

## Migration 008 — compression_records

```sql
CREATE TABLE compression_records (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id           UUID REFERENCES optimization_runs(id) ON DELETE CASCADE,
    compressed_text  TEXT NOT NULL,
    recovery_map     JSONB NOT NULL DEFAULT '{}',
    expansion_log    JSONB NOT NULL DEFAULT '[]',
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_compression_run ON compression_records(run_id);
```

---

## Verification

After all migrations:

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

Expected: `api_keys, chunks, compression_records, conversations, documents, messages, optimization_runs, users`

---

## Delete dependency order

The `DELETE /api/history/{id}` route clears rows in this order to satisfy FK constraints:

```
compression_records  (FK → optimization_runs)
validation_results   (FK → optimization_runs, if table exists from old schema)
optimization_runs    (FK → conversations)
messages             (FK → conversations)
conversations
```

---

## Rollback (development only)

```sql
DROP TABLE IF EXISTS
    compression_records,
    optimization_runs,
    chunks,
    documents,
    messages,
    conversations,
    api_keys,
    users
CASCADE;
```
