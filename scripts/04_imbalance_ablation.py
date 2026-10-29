"""Step 4 – class-imbalance ablation (fog target, 3 h lead time).

Strategies: none | class weighting | SMOTE (Chawla et al. 2002) | random under-sampling,
for logistic regression and LightGBM, each scored with raw and calibrated probabilities.
The strategy is *selected on validation*; test scores are reported for transparency only.
Output: results/tables/imbalance_ablation.csv
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from sklearn.impute import SimpleImputer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esenboga.config import RANDOM_STATE, TABLES  # noqa: E402
from esenboga.data import climatology, fog_season, load_processed, task_frame  # noqa: E402
from esenboga.metrics import best_threshold, categorical_scores, probabilistic_scores  # noqa: E402
from esenboga.models import choose_calibrator, fit_lgbm, make_lr  # noqa: E402

H = 3
LGBM_PARAMS = {"learning_rate": 0.05, "num_leaves": 63, "min_child_samples": 100,
               "feature_fraction": 0.7, "bagging_fraction": 0.8, "bagging_freq": 1,
               "lambda_l2": 1.0}


def main() -> None:
    feats, targ = load_processed()
    X, y, split = task_frame(feats, targ, "fog", H)
    tr, va, te = [(split == s).to_numpy() for s in ("train", "val", "test")]
    Xtr, ytr = X[tr], y[tr].to_numpy()
    Xva, yva, Xte, yte = X[va], y[va].to_numpy(), X[te], y[te].to_numpy()
    clim_va = climatology(X.index[tr], ytr, X.index[va], H)
    clim_te = climatology(X.index[tr], ytr, X.index[te], H)
    g_va = fog_season(X.index[va])
    imp = SimpleImputer(strategy="median").fit(Xtr)
    Xtr_imp = pd.DataFrame(imp.transform(Xtr), columns=X.columns, index=Xtr.index)
    rows = []
    for strategy in ("none", "weighting", "smote", "undersampling"):
        Xs, ys = Xtr, ytr
        if strategy == "smote":
            Xs, ys = SMOTE(sampling_strategy=0.25, random_state=RANDOM_STATE).fit_resample(
                Xtr_imp, ytr)
        elif strategy == "undersampling":
            Xs, ys = RandomUnderSampler(sampling_strategy=0.1,
                                        random_state=RANDOM_STATE).fit_resample(Xtr, ytr)
        for model in ("lr", "lgbm"):
            t0 = time.time()
            if model == "lr":
                m = make_lr(0.1, class_weight="balanced" if strategy == "weighting" else None)
                m.fit(Xs, ys)
                p_va, p_te = m.predict_proba(Xva)[:, 1], m.predict_proba(Xte)[:, 1]
            else:
                spw = (len(ys) - ys.sum()) / ys.sum() if strategy == "weighting" else 1.0
                m, it = fit_lgbm(Xs, ys, Xva, yva, LGBM_PARAMS, scale_pos_weight=spw)
                p_va = m.predict_proba(Xva, num_iteration=it)[:, 1]
                p_te = m.predict_proba(Xte, num_iteration=it)[:, 1]
            cal, _ = choose_calibrator(p_va, yva, g_va)
            for calibrated in (False, True):
                pv = cal.transform(p_va) if calibrated else p_va
                pt = cal.transform(p_te) if calibrated else p_te
                thr = best_threshold(yva, pv, "CSI")
                for part, yy, pp, cl in (("val", yva, pv, clim_va), ("test", yte, pt, clim_te)):
                    ps = probabilistic_scores(yy, pp, cl)
                    cs = categorical_scores(yy, pp >= thr)
                    rows.append({"model": model, "strategy": strategy,
                                 "calibrated": calibrated, "split": part, "threshold": thr,
                                 "PR_AUC": ps["PR_AUC"], "ROC_AUC": ps["ROC_AUC"],
                                 "Brier": ps["Brier"], "BSS": ps["BSS"], "CSI": cs["CSI"],
                                 "POD": cs["POD"], "FAR": cs["FAR"], "HSS": cs["HSS"],
                                 "calibrator": cal.method if calibrated else "none"})
            print(f"{strategy:13s} {model:4s} done ({time.time() - t0:.0f}s)", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(TABLES / "imbalance_ablation.csv", index=False)
    show = df[df.split == "val"].pivot_table(index=["model", "strategy"], columns="calibrated",
                                             values=["PR_AUC", "Brier", "CSI"])
    print(show.round(4).to_string())


if __name__ == "__main__":
    main()
