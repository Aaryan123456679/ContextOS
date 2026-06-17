"""
Reference-free faithfulness & hallucination.

For each claim (answer sentence) we find its best-supporting context sentence by
embedding similarity, then confirm support with NLI on that short pair (NLI is
reliable on sentence pairs but not on a long truncated premise). A claim is
"supported" if the best context sentence entails it OR is near-duplicate.

faithfulness = supported / claims ;  hallucination = unsupported / claims.
"""
import re
import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

_nli = None
_SIM_GATE = 0.45     # only test claims that have a plausibly-related context sentence
_DUP_SIM = 0.80      # near-duplicate ⇒ supported without NLI
_ENTAIL_P = 0.50     # NLI entailment probability threshold


def _nli_model():
    global _nli
    if _nli is None:
        from services.engines.contradiction import get_nli_model
        _nli = get_nli_model()
    return _nli


def _sentences(text: str, lo=15, cap=40):
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > lo][:cap]


def faithfulness_and_hallucination(answer: str, context: str) -> tuple:
    from pipeline.retrieval import _model
    claims = _sentences(answer, lo=15, cap=20)
    ctx_sents = _sentences(context, lo=20, cap=200)
    if not claims:
        return 1.0, 0.0
    if not ctx_sents:
        return 0.0, 1.0

    emb = _model()
    cvecs = emb.encode(ctx_sents, normalize_embeddings=True, show_progress_bar=False)
    qvecs = emb.encode(claims, normalize_embeddings=True, show_progress_bar=False)
    sims = np.asarray(qvecs) @ np.asarray(cvecs).T  # claims × ctx

    # Build NLI pairs only for claims with a plausibly-related sentence.
    nli_pairs, nli_idx = [], []
    best_sent, best_sim = {}, {}
    for i, claim in enumerate(claims):
        j = int(np.argmax(sims[i]))
        best_sent[i] = ctx_sents[j]
        best_sim[i] = float(sims[i][j])
        if best_sim[i] >= _SIM_GATE and best_sim[i] < _DUP_SIM:
            nli_pairs.append((ctx_sents[j], claim))
            nli_idx.append(i)

    entail = {}
    if nli_pairs:
        preds = _nli_model().predict(nli_pairs)
        for k, p in zip(nli_idx, preds):
            e = np.exp(p)
            probs = e / e.sum()
            entail[k] = float(probs[1])  # index 1 = entailment

    supported = 0
    for i in range(len(claims)):
        if best_sim[i] >= _DUP_SIM:
            supported += 1
        elif entail.get(i, 0.0) >= _ENTAIL_P:
            supported += 1
    n = len(claims)
    return round(supported / n, 4), round((n - supported) / n, 4)
