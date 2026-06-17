"""
Generate a research report (Markdown + charts + summary.json) from a results CSV.

Usage:
    python -m analysis.report results/runs/<run_name>
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from analysis.stats import summarize


def _charts(df: pd.DataFrame, out: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return []
    charts = []
    cdir = out / "charts"
    cdir.mkdir(exist_ok=True)
    num = lambda s: pd.to_numeric(s, errors="coerce").dropna()

    # 1. Token reduction distribution
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(num(df["token_reduction_pct"]), bins=40, color="#2563eb")
    ax.set_title("Token reduction (%) distribution"); ax.set_xlabel("% reduction"); ax.set_ylabel("scenarios")
    fig.tight_layout(); p = cdir / "token_reduction_hist.png"; fig.savefig(p, dpi=110); plt.close(fig)
    charts.append(p)

    # 2. Token reduction by query type
    g = df.groupby("query_type")["token_reduction_pct"].apply(lambda s: num(s).mean()).sort_values()
    if len(g):
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.barh(g.index, g.values, color="#16a34a")
        ax.set_title("Mean token reduction by query type"); ax.set_xlabel("% reduction")
        fig.tight_layout(); p = cdir / "reduction_by_query_type.png"; fig.savefig(p, dpi=110); plt.close(fig)
        charts.append(p)

    # 3. Quality: optimized vs baseline (judged only)
    judged = df[df["pass_fail"].isin(["pass", "fail"])]
    if len(judged):
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.scatter(num(judged["baseline_quality_score"]), num(judged["quality_score"]), alpha=0.5, color="#7c3aed")
        lim = [0, 10]; ax.plot(lim, lim, "k--", linewidth=1)
        ax.set_xlim(lim); ax.set_ylim(lim)
        ax.set_xlabel("baseline quality"); ax.set_ylabel("ContextOS quality")
        ax.set_title("Answer quality: ContextOS vs baseline")
        fig.tight_layout(); p = cdir / "quality_vs_baseline.png"; fig.savefig(p, dpi=110); plt.close(fig)
        charts.append(p)

        # 4. Answer similarity distribution
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(num(judged["answer_similarity_score"]), bins=30, color="#ea580c")
        ax.axvline(config.SUCCESS_SIMILARITY, color="k", linestyle="--", label=f"threshold {config.SUCCESS_SIMILARITY}")
        ax.set_title("Answer similarity (optimized vs baseline)"); ax.set_xlabel("BERTScore F1"); ax.legend()
        fig.tight_layout(); p = cdir / "similarity_hist.png"; fig.savefig(p, dpi=110); plt.close(fig)
        charts.append(p)
    return charts


def render_md(summary: dict, manifest: dict, charts) -> str:
    t = summary["token_reduction_pct"]; tot = summary["totals"]
    L = ["# ContextOS Evaluation Report\n"]
    L.append(f"- **Scenarios:** {summary['n_scenarios']:,}  (LLM-judged: {summary['n_judged']:,})")
    if manifest:
        L.append(f"- **Model:** {manifest.get('provider')}/{manifest.get('model')} "
                 f"(`{manifest.get('model_digest','')}`)  ·  engines: {', '.join(manifest.get('engines_enabled', []))}")
        L.append(f"- **Seed:** {manifest.get('seed')}  ·  pricing: {manifest.get('pricing_version')} "
                 f"(ref model {manifest.get('cost_reference_model')})")
    L.append("\n## Headline\n")
    L.append(f"- **Token reduction:** mean **{t['mean']}%**, median {t['median']}%, p95 {t['p95']}%, p99 {t['p99']}%")
    L.append(f"- **Total tokens saved:** {tot['total_tokens_saved']:,} "
             f"({tot['baseline_tokens']:,} → {tot['optimized_tokens']:,})")
    L.append(f"- **Estimated cost saved:** ${tot['total_cost_saved_usd']:,} "
             f"(at {config.COST_REFERENCE_MODEL} pricing)")
    L.append(f"- **Gold-fact retention (recall):** mean {summary['gold_chunk_recall']['mean']}")
    if "quality" in summary:
        q = summary["quality"]
        L.append(f"- **Answer similarity (opt vs full):** mean {q['answer_similarity']['mean']}, p05≈{q['answer_similarity']['min']}")
        L.append(f"- **Quality vs baseline:** ContextOS {q['quality_score']['mean']} vs baseline "
                 f"{q['baseline_quality_score']['mean']} (Δ mean {q['quality_delta_vs_baseline']['mean']})")
        L.append(f"- **Quality maintained (Δ≥0):** {summary['quality_maintained_pct']}% of judged")
        L.append(f"- **Faithfulness:** {q['faithfulness']['mean']}  ·  **Hallucination:** {q['hallucination']['mean']}")
        L.append(f"- **Success criterion pass rate** (red>20% & sim>0.90 & quality≥baseline): "
                 f"**{summary['pass_rate_pct']}%**")
    L.append("\n## Token reduction by query type\n")
    L.append("| Query type | Mean token reduction % |")
    L.append("|---|---|")
    for qt, v in sorted(summary["by_query_type"].items(), key=lambda x: -x[1]):
        L.append(f"| {qt} | {v} |")
    if "by_condition" in summary:
        L.append("\n## By dataset condition\n")
        L.append("| Condition | N | Mean token reduction % |")
        L.append("|---|---|---|")
        for c, d in summary["by_condition"].items():
            L.append(f"| {c} | {d['n']} | {d['mean_token_reduction_pct']} |")
    if charts:
        L.append("\n## Charts\n")
        for p in charts:
            L.append(f"![{p.stem}](charts/{p.name})")
    L.append("\n## Methodology & limitations\n")
    L.append("- Reference-free evaluation on a real scraped corpus (arXiv, framework docs, "
             "Wikipedia + noise). Queries are document-grounded; contradictions are controlled injections.")
    L.append("- Baseline = full retrieved context → LLM. ContextOS = optimized context → LLM (same model).")
    L.append("- Quality is LLM-as-judge (completeness/correctness/clarity/grounding) + answer "
             "similarity to the baseline; faithfulness/hallucination via embedding-gated NLI. No gold "
             "answers, so 'correctness' is judge-relative.")
    L.append("- Deterministic metrics cover all scenarios; LLM-judged metrics cover the judged subset.")
    return "\n".join(L)


def generate(run_dir: str):
    run = Path(run_dir)
    df = pd.read_csv(run / "results.csv")
    manifest = {}
    mf = run / "run_manifest.json"
    if mf.exists():
        manifest = json.loads(mf.read_text())
    summary = summarize(df)
    summary["manifest"] = manifest
    (run / "summary.json").write_text(json.dumps(summary, indent=2))
    charts = _charts(df, run)
    md = render_md(summary, manifest, charts)
    (run / "report.md").write_text(md)
    print(md)
    print(f"\nWrote {run/'report.md'}, summary.json, and {len(charts)} charts.")


if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else str(max(config.RESULTS_DIR.glob("*"), key=lambda p: p.stat().st_mtime)))
