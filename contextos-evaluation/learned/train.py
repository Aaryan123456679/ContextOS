"""
Train the learned selection policy on per-chunk features (all engine signals).

- Grouped CV by example_id (no leakage) -> honest ROC-AUC.
- Reports feature importances: WHICH parameters actually drive keep/drop.
- Saves the fitted model + feature order to learned/policy.pkl.

Usage:
    python -m learned.train --features learned/features_hotpot.csv
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import contextos_pipeline as cop  # noqa: E402

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GroupKFold, cross_val_score
import joblib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default="learned/features_hotpot.csv")
    ap.add_argument("--out", default="learned/policy.pkl")
    args = ap.parse_args()

    df = pd.read_csv(args.features)
    X = df[cop.FEATURE_COLS].values
    y = df["label"].values
    groups = df["example_id"].values
    print(f"{len(df)} chunks · {y.mean()*100:.1f}% positive · {df['example_id'].nunique()} examples")

    gkf = GroupKFold(n_splits=5)
    # logistic (interpretable) and gradient boosting (capacity)
    logit = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
    gbm = GradientBoostingClassifier(random_state=42)
    for name, mdl in [("logistic", logit), ("grad-boost", gbm)]:
        auc = cross_val_score(mdl, X, y, groups=groups, cv=gkf, scoring="roc_auc")
        print(f"{name:11} grouped-CV ROC-AUC = {auc.mean():.3f} ± {auc.std():.3f}")

    # fit final GBM on all data, report importances
    gbm.fit(X, y)
    imp = sorted(zip(cop.FEATURE_COLS, gbm.feature_importances_), key=lambda x: -x[1])
    print("\nfeature importances (gradient boosting):")
    for f, v in imp:
        print(f"  {f:20} {v:.3f}")
    # logistic coefficients (signed direction) for interpretability
    logit.fit(X, y)
    coefs = logit.named_steps["logisticregression"].coef_[0]
    signed = sorted(zip(cop.FEATURE_COLS, coefs), key=lambda x: -abs(x[1]))
    print("\nlogistic coefficients (standardized; sign = direction of 'keep'):")
    for f, v in signed:
        print(f"  {f:20} {v:+.3f}")

    joblib.dump({"model": gbm, "features": cop.FEATURE_COLS}, args.out)
    Path(args.out).with_suffix(".json").write_text(json.dumps(
        {"features": cop.FEATURE_COLS, "importances": dict(imp)}, indent=2))
    print(f"\nsaved {args.out}")


if __name__ == "__main__":
    main()
