"""
LLMLingua-2 wrapper — the SOTA token-level prompt compressor we build on / beat.

Used two ways in the benchmark:
  - standalone (compress the full context) = SOTA baseline
  - as a post-selection stage (compress the chunks our policy kept) = hybrid

Uses the smaller bert-base-multilingual LLMLingua-2 model (CPU-friendly). Cached.
"""
_PC = None
_MODEL = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"


def _pc():
    global _PC
    if _PC is None:
        from llmlingua import PromptCompressor
        _PC = PromptCompressor(model_name=_MODEL, use_llmlingua2=True, device_map="cpu")
    return _PC


def compress(text: str, rate: float = 0.5, target_token: int = -1) -> str:
    """Return the compressed text. `rate` keeps that fraction of tokens (lower = more
    compression); `target_token` (if >0) overrides rate with an absolute target."""
    if not text or not text.strip():
        return text
    kwargs = {"force_tokens": ["\n", ".", "?", "!", ","]}
    if target_token and target_token > 0:
        kwargs["target_token"] = target_token
    else:
        kwargs["rate"] = rate
    try:
        res = _pc().compress_prompt(text, **kwargs)
        return res.get("compressed_prompt", text) or text
    except Exception:
        return text
