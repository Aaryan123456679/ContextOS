"""
What actually matters (deterministic, no LLM):

1. Does the HotpotQA-trained policy GENERALIZE — i.e. still identify answer-bearing
   chunks frozen across the 12 MRQA datasets? (overall + per-subset ROC-AUC)
2. The recall<->reduction tradeoff the policy gives at various thresholds (no LLM):
   how many tokens it would cut vs how often it keeps the answer-bearing chunk.
3. Which signals matter cross-dataset: train an MRQA-native policy and compare
   importances to the HotpotQA-trained one.

Usage:
    python -m learned.eval_transfer --policy learned/policy.pkl --features learned/features_mrqa.csv
"""
import argparse
from collections import defaultdict
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import contextos_pipeline as cop  # noqa: E402
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import GroupKFold, cross_val_score
import joblib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="learned/policy.pkl")
    ap.add_argument("--features", default="learned/features_mrqa.csv")
    args = ap.parse_args()

    pol = joblib.load(args.policy)
    feats = pol["features"]
    df = pd.read_csv(args.features)
    X = df[feats].values
    y = df["label"].values
    probs = pol["model"].predict_proba(X)[:, 1]

    print(f"=== HotpotQA-trained policy, FROZEN on MRQA ({len(df)} chunks, "
          f"{y.mean()*100:.1f}% answer-bearing) ===")
    print(f"overall ROC-AUC = {roc_auc_score(y, probs):.3f}   AP = {average_precision_score(y, probs):.3f}\n")
    print(f"{'subset':22}{'chunks':>7}{'pos%':>6}{'AUC':>7}")
    print("-" * 42)
    for sub in sorted(df["subset"].unique()):
        m = df["subset"] == sub
        ys, ps = y[m.values], probs[m.values]
        auc = roc_auc_score(ys, ps) if len(set(ys)) > 1 else float("nan")
        print(f"{sub:22}{m.sum():>7}{100*ys.mean():>6.0f}{auc:>7.3f}")

    # deterministic recall<->reduction tradeoff (group by example)
    print(f"\n=== recall vs token-reduction by threshold (frozen, no LLM) ===")
    df = df.assign(prob=probs)
    print(f"{'thr':>5}{'mean_kept':>11}{'tok_reduction%':>16}{'ans_recall':>12}")
    for thr in (0.15, 0.2, 0.3, 0.5):
        kept_fr, reds, recs = [], [], []
        for _, g in df.groupby("example_id"):
            keep = g["prob"] >= thr
            if keep.sum() == 0:  # min-keep 1 (top prob)
                keep = g["prob"] == g["prob"].max()
            tot_tok = g["token_count"].sum()
            kept_tok = g.loc[keep, "token_count"].sum()
            reds.append(1 - kept_tok / max(tot_tok, 1))
            kept_fr.append(keep.mean())
            pos = g["label"].sum()
            recs.append((g.loc[keep, "label"].sum() / pos) if pos else np.nan)
        print(f"{thr:>5}{np.mean(kept_fr):>11.2f}{100*np.mean(reds):>16.1f}{np.nanmean(recs):>12.3f}")

    # MRQA-native importances (what matters in-domain on MRQA)
    print(f"\n=== MRQA-native policy importances (vs HotpotQA-trained) ===")
    gbm = GradientBoostingClassifier(random_state=42)
    auc = cross_val_score(gbm, X, y, groups=df["example_id"].values,
                          cv=GroupKFold(5), scoring="roc_auc")
    print(f"MRQA-native grouped-CV AUC = {auc.mean():.3f} ± {auc.std():.3f}")
    gbm.fit(X, y)
    hp_imp = dict(zip(feats, pol["model"].feature_importances_))
    mr_imp = dict(zip(feats, gbm.feature_importances_))
    print(f"\n{'feature':20}{'HotpotQA':>10}{'MRQA':>8}")
    for f in sorted(feats, key=lambda k: -mr_imp[k]):
        print(f"{f:20}{hp_imp[f]:>10.3f}{mr_imp[f]:>8.3f}")


if __name__ == "__main__":
    main()
