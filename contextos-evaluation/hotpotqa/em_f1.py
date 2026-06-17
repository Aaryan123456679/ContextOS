"""
Official-style HotpotQA / SQuAD answer normalization and EM / token-F1.

Mirrors the HotpotQA evaluation script: lowercase, strip punctuation, drop
articles, collapse whitespace; EM is exact match of normalized strings, F1 is
token-overlap F1. 'yes'/'no'/'noanswer' compare exactly after normalization.
"""
import re
import string
from collections import Counter


def normalize_answer(s: str) -> str:
    def remove_articles(t):
        return re.sub(r"\b(a|an|the)\b", " ", t)

    def white_space_fix(t):
        return " ".join(t.split())

    def remove_punc(t):
        return "".join(ch for ch in t if ch not in set(string.punctuation))

    def lower(t):
        return t.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s or ""))))


def exact_match(pred: str, gold: str) -> int:
    return int(normalize_answer(pred) == normalize_answer(gold))


def f1(pred: str, gold: str) -> float:
    p_toks = normalize_answer(pred).split()
    g_toks = normalize_answer(gold).split()
    if not p_toks or not g_toks:
        # if either is empty, F1 is 1 only when both empty
        return float(p_toks == g_toks)
    common = Counter(p_toks) & Counter(g_toks)
    same = sum(common.values())
    if same == 0:
        return 0.0
    prec = same / len(p_toks)
    rec = same / len(g_toks)
    return 2 * prec * rec / (prec + rec)


def score(pred: str, gold: str) -> dict:
    return {"em": exact_match(pred, gold), "f1": round(f1(pred, gold), 4)}
