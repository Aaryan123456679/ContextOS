-- ContextOS — Initial Schema
-- Run once in the Supabase SQL editor (Dashboard → SQL Editor → New query).
-- Tables are created in FK-dependency order; safe to re-run (all are IF NOT EXISTS).

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- uuid_generate_v4() fallback

-- ---------------------------------------------------------------------------
-- Helper: auto-update updated_at
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- ---------------------------------------------------------------------------
-- 1. users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT        UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    settings    JSONB       NOT NULL DEFAULT '{}'
);

-- ---------------------------------------------------------------------------
-- 2. api_keys
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_keys (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider    TEXT        NOT NULL,   -- 'openai' | 'anthropic' | 'gemini'
    key_hash    TEXT        NOT NULL,   -- AES-256 encrypted ciphertext
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);

-- ---------------------------------------------------------------------------
-- 3. conversations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT,
    model       TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

DROP TRIGGER IF EXISTS trg_conversations_updated_at ON conversations;
CREATE TRIGGER trg_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- 4. messages
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role             TEXT        NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content          TEXT        NOT NULL,
    token_count      INTEGER,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at     ON messages(conversation_id, created_at);

-- ---------------------------------------------------------------------------
-- 5. documents
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename     TEXT        NOT NULL,
    file_type    TEXT        NOT NULL,
    storage_path TEXT,                  -- Supabase Storage object path
    chunk_count  INTEGER,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);

-- ---------------------------------------------------------------------------
-- 6. chunks
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chunks (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id  UUID        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    qdrant_id    TEXT        NOT NULL,  -- point ID in Qdrant collection
    content      TEXT        NOT NULL,
    token_count  INTEGER     NOT NULL,
    chunk_index  INTEGER     NOT NULL,
    metadata     JSONB       NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_qdrant_id   ON chunks(qdrant_id);

-- ---------------------------------------------------------------------------
-- 7. optimization_runs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS optimization_runs (
    id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id       UUID        REFERENCES conversations(id),  -- nullable: standalone /optimize
    query                 TEXT        NOT NULL,
    original_token_count  INTEGER,
    optimized_token_count INTEGER,
    token_reduction_pct   FLOAT,
    cost_original         FLOAT,
    cost_optimized        FLOAT,
    bert_score            FLOAT,
    quality_score         FLOAT,
    engine_breakdown      JSONB,       -- per-engine attribution
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_opt_runs_conversation_id ON optimization_runs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_opt_runs_created_at      ON optimization_runs(created_at DESC);

-- ---------------------------------------------------------------------------
-- 8. compression_records
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS compression_records (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id           UUID        REFERENCES optimization_runs(id),   -- nullable
    compressed_text  TEXT        NOT NULL,
    recovery_map     JSONB       NOT NULL DEFAULT '{}',  -- {ptr_id: {source_doc, byte_range, trigger, summary}}
    expansion_log    JSONB       NOT NULL DEFAULT '[]',  -- [{ptr_id, expanded_at, expanded_by}]
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_compression_records_run_id ON compression_records(run_id);

-- ---------------------------------------------------------------------------
-- 9. validation_results
-- (Stored async after each chat turn by ValidationHarness background task)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS validation_results (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id           UUID        NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    passed           BOOLEAN     NOT NULL DEFAULT FALSE,
    bert_score_f1    FLOAT,
    quality_delta    FLOAT,
    token_reduction  FLOAT,
    faithfulness     FLOAT,
    reasoning        TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_validation_results_run_id ON validation_results(run_id);

-- ---------------------------------------------------------------------------
-- Seed: demo user
-- chat.py uses this UUID when no user_id is supplied in the request.
-- The FK on conversations.user_id will fail without this row.
-- ---------------------------------------------------------------------------
INSERT INTO users (id, email, settings)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'demo@contextos.dev',
    '{"model": "gpt-4o", "token_budget": 8192}'
)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Row-Level Security
-- Enable RLS on all tables. All writes go through the backend service role,
-- which bypasses RLS. These policies let the anon/authenticated Supabase
-- client read only its own rows if you later add direct client queries.
-- ---------------------------------------------------------------------------
ALTER TABLE users              ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys           ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations      ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages           ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents          ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks             ENABLE ROW LEVEL SECURITY;
ALTER TABLE optimization_runs  ENABLE ROW LEVEL SECURITY;
ALTER TABLE compression_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE validation_results ENABLE ROW LEVEL SECURITY;

-- Service role bypass (backend uses the service key → bypasses RLS automatically).
-- The policies below are for future direct-client access; safe to leave even if unused.

CREATE POLICY IF NOT EXISTS "users: own row"
    ON users FOR ALL USING (auth.uid() = id);

CREATE POLICY IF NOT EXISTS "api_keys: own rows"
    ON api_keys FOR ALL USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "conversations: own rows"
    ON conversations FOR ALL USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "messages: via conversation"
    ON messages FOR ALL USING (
        EXISTS (
            SELECT 1 FROM conversations c
            WHERE c.id = messages.conversation_id
              AND c.user_id = auth.uid()
        )
    );

CREATE POLICY IF NOT EXISTS "documents: own rows"
    ON documents FOR ALL USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "chunks: via document"
    ON chunks FOR ALL USING (
        EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = chunks.document_id
              AND d.user_id = auth.uid()
        )
    );

-- optimization_runs, compression_records, validation_results:
-- no direct user ownership column; backend service role owns these.
-- Grant read access via the conversation link.
CREATE POLICY IF NOT EXISTS "opt_runs: via conversation"
    ON optimization_runs FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM conversations c
            WHERE c.id = optimization_runs.conversation_id
              AND c.user_id = auth.uid()
        )
    );
