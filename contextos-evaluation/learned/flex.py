"""
Flexible (regime-invariant) features + cross-regime transfer test.

The raw policy failed to transfer (HotpotQA->MRQA AUC 0.41) because raw features
(roi_score, rank) shift meaning across pool sizes / base rates. Here we derive
*within-instance* features that mean the same thing in any regime:
  - z-scores within the candidate pool (roi/fusion/density)
  - value relative to the pool max
  - gap to the next-ranked chunk (normalized by pool spread)
  - is-top-1 flags, query-concept fraction, log pool size

Then we test cross-REGIME transfer both ways (train MRQA->test HotpotQA and vice
versa) with FLEX vs RAW features. If flex >> raw, the policy is genuinely flexible.

Usage:
    python -m learned.flex
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import contextos_pipeline as cop  # noqa: E402
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score

RAW = cop.FEATURE_COLS
FLEX = ["roi_z", "fusion_z", "density_z", "roi_rel", "fusion_rel2", "roi_gap_next",
        "roi_rank_frac", "is_top1", "is_top2", "qconcept_frac", "log_pool"]


def _z(s):
    sd = s.std()
    return (s - s.mean()) / sd if sd > 1e-9 else s * 0.0


def add_flex(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for _, g in df.groupby("example_id"):
        g = g.copy()
        g["roi_z"] = _z(g["roi_score"])
        g["fusion_z"] = _z(g["fusion_score"])
        g["density_z"] = _z(g["density"])
        mx_roi = g["roi_score"].max() or 1.0
        mx_fus = g["fusion_score"].max() or 1.0
        g["roi_rel"] = g["roi_score"] / mx_roi
        g["fusion_rel2"] = g["fusion_score"] / mx_fus
        sr = g["roi_score"].sort_values(ascending=False).values
        spread = (sr[0] - sr[-1]) if len(sr) > 1 else 1.0
        spread = spread or 1.0
        nxt = {}
        order = g.sort_values("roi_score", ascending=False).reset_index()
        for i, row in order.iterrows():
            below = sr[i + 1] if i + 1 < len(sr) else sr[i]
            nxt[row["index"]] = (row["roi_score"] - below) / spread
        g["roi_gap_next"] = [nxt[idx] for idx in g.index]
        g["roi_rank_frac"] = g["roi_score"].rank(ascending=False, method="first").sub(1) / max(len(g) - 1, 1)
        g["is_top1"] = (g["roi_rank_frac"] == 0).astype(int)
        g["is_top2"] = (g["roi_score"].rank(ascending=False, method="first") <= 2).astype(int)
        g["log_pool"] = np.log1p(len(g))
        out.append(g)
    return pd.concat(out, ignore_index=True)


def transfer(train_df, test_df, cols, label="label"):
    Xtr, ytr = train_df[cols].values, train_df[label].values
    Xte, yte = test_df[cols].values, test_df[label].values
    if len(set(ytr)) < 2 or len(set(yte)) < 2:
        return float("nan")
    m = GradientBoostingClassifier(random_state=42).fit(Xtr, ytr)
    return roc_auc_score(yte, m.predict_proba(Xte)[:, 1])


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="features_hotpot.csv")
    ap.add_argument("--b", default="features_musique.csv")
    ap.add_argument("--na", default="HotpotQA")
    ap.add_argument("--nb", default="MuSiQue")
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    A = add_flex(pd.read_csv(here / args.a))
    B = add_flex(pd.read_csv(here / args.b))

    print(f"{args.na}: {len(A)} chunks {A['label'].mean()*100:.0f}% pos · "
          f"{args.nb}: {len(B)} chunks {B['label'].mean()*100:.0f}% pos\n")
    print("Cross-dataset transfer ROC-AUC (train -> test), both genuine selection sets:\n")
    print(f"{'direction':26}{'RAW':>8}{'FLEX':>8}")
    print("-" * 42)
    for name, tr, te in [(f"{args.na} -> {args.nb}", A, B), (f"{args.nb} -> {args.na}", B, A)]:
        print(f"{name:26}{transfer(tr, te, RAW):>8.3f}{transfer(tr, te, FLEX):>8.3f}")

    both = pd.concat([A.assign(reg="a"), B.assign(reg="b")], ignore_index=True)
    m = GradientBoostingClassifier(random_state=42).fit(both[FLEX].values, both["label"].values)
    print("\nflexible mixed-policy importances:")
    for f, v in sorted(zip(FLEX, m.feature_importances_), key=lambda x: -x[1]):
        print(f"  {f:16} {v:.3f}")


if __name__ == "__main__":
    main()
