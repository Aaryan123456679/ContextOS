# Troubleshooting — LLM Providers

## OpenAI — 401 Unauthorized

**Symptom:** `openai.AuthenticationError: 401 Incorrect API key`

**Fix:**
1. Verify key starts with `sk-` (not `sk-proj-` from older accounts)
2. Check key hasn't been rotated in OpenAI dashboard
3. Verify `ENCRYPTION_KEY` in `.env` matches the one used when the key was stored

---

## OpenAI — 429 Rate Limit

**Symptom:** `openai.RateLimitError: 429 Too Many Requests`

**Fix:** The LLM Gateway includes exponential backoff. If persisting:
- Check OpenAI usage dashboard for tier limits
- Reduce `BATCH_SIZE` in embedder from 100 to 50
- Add `asyncio.sleep(1)` between compression calls

---

## Anthropic — 529 Overloaded

**Symptom:** `anthropic.InternalServerError: 529`

**Fix:** Claude API overload (usually temporary). The gateway retries once automatically. If persistent, fall back to GPT-4o-mini for compression:

```python
COMPRESSION_MODEL = os.getenv("COMPRESSION_MODEL", "claude-haiku-3")
# Set COMPRESSION_MODEL=gpt-4o-mini in .env to override
```

---

## LLM response is empty or cut off

**Symptom:** `response.content = ""`

**Causes and fixes:**
1. `max_tokens` too low — default is 2048, increase to 4096 for complex queries
2. Prompt exceeds model context limit — check `prompt_tokens` in response usage
3. Content filter triggered — the adapted context contained something that triggered moderation

---

## Recovery pointer parsing fails

**Symptom:** `recovery_map = {}` but compressed_text contains `[PTR:...]` tags

**Fix:** The regex parser expects exact format:
```
[PTR:ptr_01|trigger:...|source:...|summary:...]
```

Check the raw LLM output for malformed tags (missing `|`, wrong bracket type). Add logging:
```python
logger.debug(f"Raw compression output: {raw_output[:500]}")
```

---

## Gemini — Invalid API key

**Symptom:** `google.api_core.exceptions.PermissionDenied: 403`

**Fix:** Gemini API keys are project-scoped. Ensure the key is for the correct GCP project and the Generative AI API is enabled in GCP Console → APIs & Services.

---

## LLM Judge returns non-JSON

**Symptom:** `json.JSONDecodeError` when parsing judge response

**Fix:** Add JSON mode to the judge call (OpenAI supports this):
```python
resp = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[...],
    response_format={"type": "json_object"}
)
```

For Anthropic, add to prompt: `Output ONLY valid JSON. No explanation. No markdown code blocks.`
