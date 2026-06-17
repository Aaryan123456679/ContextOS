"""Aggregate statistics over a results CSV: distributions, percentiles, totals."""
import numpy as np
import pandas as pd


def _num(series):
    return pd.to_numeric(series, errors="coerce").dropna()


def _pctiles(arr):
    if len(arr) == 0:
        return {k: None for k in ("mean", "median", "p50", "p95", "p99", "min", "max")}
    a = np.asarray(arr, dtype=float)
    return {
        "mean": round(float(a.mean()), 3),
        "median": round(float(np.median(a)), 3),
        "p50": round(float(np.percentile(a, 50)), 3),
        "p95": round(float(np.percentile(a, 95)), 3),
        "p99": round(float(np.percentile(a, 99)), 3),
        "min": round(float(a.min()), 3),
        "max": round(float(a.max()), 3),
    }


def summarize(df: pd.DataFrame) -> dict:
    n = len(df)
    judged = df[df["pass_fail"].isin(["pass", "fail"])]
    tok = _num(df["token_reduction_pct"])
    out = {
        "n_scenarios": int(n),
        "n_judged": int(len(judged)),
        "token_reduction_pct": _pctiles(tok),
        "cost_savings_pct": _pctiles(_num(df["cost_savings_pct"])),
        "gold_chunk_recall": _pctiles(_num(df["gold_chunk_recall"])),
        "opt_pipeline_ms": _pctiles(_num(df["opt_pipeline_ms"])),
        "totals": {
            "baseline_tokens": int(_num(df["baseline_tokens"]).sum()),
            "optimized_tokens": int(_num(df["optimized_tokens"]).sum()),
            "baseline_cost_usd": round(float(_num(df["baseline_cost"]).sum()), 4),
            "optimized_cost_usd": round(float(_num(df["optimized_cost"]).sum()), 4),
        },
    }
    out["totals"]["total_tokens_saved"] = out["totals"]["baseline_tokens"] - out["totals"]["optimized_tokens"]
    out["totals"]["total_cost_saved_usd"] = round(
        out["totals"]["baseline_cost_usd"] - out["totals"]["optimized_cost_usd"], 4)

    if len(judged):
        out["quality"] = {
            "answer_similarity": _pctiles(_num(judged["answer_similarity_score"])),
            "faithfulness": _pctiles(_num(judged["faithfulness_score"])),
            "hallucination": _pctiles(_num(judged["hallucination_score"])),
            "relevance": _pctiles(_num(judged["relevance_score"])),
            "quality_score": _pctiles(_num(judged["quality_score"])),
            "baseline_quality_score": _pctiles(_num(judged["baseline_quality_score"])),
        }
        qd = _num(judged["quality_score"]) - _num(judged["baseline_quality_score"])
        out["quality"]["quality_delta_vs_baseline"] = _pctiles(qd)
        out["pass_rate_pct"] = round(100.0 * (judged["pass_fail"] == "pass").mean(), 2)
        out["quality_maintained_pct"] = round(100.0 * (qd >= 0).mean(), 2)

    # Per query-type and per-condition breakdowns (token reduction means)
    out["by_query_type"] = {
        qt: round(float(_num(g["token_reduction_pct"]).mean()), 2)
        for qt, g in df.groupby("query_type")
    }
    for flag in ("contains_noise", "contains_redundancy", "contains_contradictions"):
        grp = df[df[flag].astype(str).isin(["True", "true", "1"])]
        out.setdefault("by_condition", {})[flag] = {
            "n": int(len(grp)),
            "mean_token_reduction_pct": round(float(_num(grp["token_reduction_pct"]).mean()), 2) if len(grp) else None,
        }
    return out
