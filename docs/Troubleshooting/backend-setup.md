# Troubleshooting — Backend Setup

## spaCy model not found

**Symptom:** `OSError: [E050] Can't find model 'en_core_web_sm'`

**Fix:**
```bash
source .venv/bin/activate
python -m spacy download en_core_web_sm
```

**Why it happens:** spaCy models are not installed via pip — they are downloaded separately. Must be run inside the same virtualenv.

---

## sentence-transformers download fails

**Symptom:** `ConnectionError` or `TimeoutError` when CrossEncoder loads

**Fix:** The model downloads from HuggingFace on first use. If HuggingFace is blocked:
```bash
HF_ENDPOINT=https://hf-mirror.com python -m uvicorn main:app --reload
```

Or manually download and set `TRANSFORMERS_CACHE` env var to a local path.

---

## Pydantic v2 validation errors

**Symptom:** `ValidationError: 1 validation error for X — model_fields_set`

**Why:** Pydantic v2 strict mode rejects unexpected fields.

**Fix:** Add to all schemas:
```python
model_config = ConfigDict(extra="ignore")
```

---

## asyncpg connection refused

**Symptom:** `asyncpg.exceptions.ConnectionRefusedError` on startup

**Fix:** Check `DATABASE_URL` in `.env`. Supabase requires SSL:
```
DATABASE_URL=postgresql+asyncpg://postgres:<password>@db.<project>.supabase.co:5432/postgres?ssl=require
```

Note the `+asyncpg` dialect suffix and `?ssl=require`.

---

## Qdrant 401 Unauthorized

**Symptom:** `qdrant_client.http.exceptions.UnexpectedResponse: 401`

**Fix:** Verify `QDRANT_KEY` is correct. Qdrant Cloud API keys expire if not used for 90 days — regenerate in the Qdrant Cloud dashboard.

---

## Port already in use

**Symptom:** `ERROR: [Errno 48] Address already in use`

**Fix:**
```bash
lsof -i :8000 | grep LISTEN
kill -9 <PID>
```

---

## Memory error during model load (local)

**Symptom:** Python process killed with signal 9 (OOM)

**Fix on M1 Mac:** Models should fit easily in 16GB. Check if another process is consuming memory:
```bash
top -o MEM
```

If on Render (512MB): verify only `en_core_web_sm` is used (not `_lg`), and models are singletons not reloaded per request.

---

## BERTScore import error

**Symptom:** `ImportError: cannot import name 'score' from 'bert_score'`

**Fix:**
```bash
pip install bert-score
# If conflict with torch version:
pip install bert-score --no-deps
pip install torch==2.2.0 transformers==4.40.0
```
