"""Step 2 – train, tune, calibrate the tabular models for every (target, horizon).

Models: logistic regression, analog k-NN, random forest, XGBoost (GPU), LightGBM, CatBoost (GPU),
Explainable Boosting Machine, MLP (GPU).
Tuning: Optuna on the validation seasons (boosting tuned on the fog target; RVR targets reuse
the fog hyper-parameters of the same horizon); small grids for the others, all scored by
validation PR-AUC. Calibration + CSI-optimal threshold: validation.
Outputs: models/tab_<model>_<target>_<h>h.joblib, results/predictions/pred_<target>_<h>h.parquet
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esenboga.config import HORIZONS, MODELS, RESULTS  # noqa: E402
from esenboga.data import fog_season, load_processed, task_frame  # noqa: E402
from esenboga.models import (AnalogKNN, TabularMLP, _cat_params, _lgbm_params,  # noqa: E402
                             _xgb_params, finalize, fit_cat, fit_lgbm, fit_xgb, make_ebm,
                             make_lr, make_rf, tune_boosting)

PRED_DIR = RESULTS / "predictions"
PRED_DIR.mkdir(parents=True, exist_ok=True)
MLP_SEARCH = [  # (hidden, layers, dropout, learning rate)
    {"hidden": 256, "layers": 3, "dropout": 0.2, "lr": 1e-3},
    {"hidden": 512, "layers": 3, "dropout": 0.3, "lr": 5e-4},
    {"hidden": 128, "layers": 2, "dropout": 0.1, "lr": 1e-3},
    {"hidden": 256, "layers": 4, "dropout": 0.3, "lr": 3e-4},
]
KNN_K = (10, 25, 50, 100, 200)
EBM_SEARCH = ({"interactions": 10, "learning_rate": 0.015}, {"interactions": 20, "learning_rate": 0.03})


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", type=int, nargs="+", default=HORIZONS)
    ap.add_argument("--targets", nargs="+", default=["fog", "rvr550", "rvr350"])
    ap.add_argument("--models", nargs="+",
                    default=["lr", "knn", "rf", "xgb", "lgbm", "cat", "ebm", "mlp"])
    ap.add_argument("--trials", type=int, default=30)
    args = ap.parse_args()

    feats, targ = load_processed()
    tuned: dict = {}
    tuned_path = MODELS / "tuned_params.json"
    if tuned_path.exists():
        tuned = json.loads(tuned_path.read_text())

    for h in args.horizons:
        for target in args.targets:
            X, y, split = task_frame(feats, targ, target, h)
            feat_cols = list(X.columns)
            tr, va = (split == "train").to_numpy(), (split == "val").to_numpy()
            Xtr, ytr, Xva, yva = X[tr], y[tr].to_numpy(), X[va], y[va].to_numpy()
            g_va = fog_season(X.index[va])
            log(f"h={h} {target}: train {tr.sum():,} (pos {ytr.mean():.3%}), "
                f"val {va.sum():,} (pos {yva.mean():.3%})")
            pred = pd.DataFrame({"split": split.to_numpy(), "y": y.to_numpy()}, index=X.index)

            for name in args.models:
                t0 = time.time()
                key = f"{name}_{h}h"
                it = None
                if name in ("lr", "rf", "mlp", "ebm"):
                    if name == "lr":
                        grid = [{"C": C} for C in (0.01, 0.1, 1.0)]
                        fit = lambda cfg: make_lr(**cfg).fit(Xtr, ytr)  # noqa: E731
                    elif name == "rf":
                        grid = [{"min_samples_leaf": 10, "max_features": "sqrt"},
                                {"min_samples_leaf": 30, "max_features": "sqrt"},
                                {"min_samples_leaf": 30, "max_features": 0.3}]
                        fit = lambda cfg: make_rf(cfg).fit(Xtr, ytr)  # noqa: E731
                    elif name == "mlp":
                        grid = MLP_SEARCH
                        fit = lambda cfg: TabularMLP(**cfg).fit(Xtr, ytr, Xva, yva)  # noqa: E731
                    else:
                        grid = list(EBM_SEARCH)
                        fit = lambda cfg: make_ebm(**cfg).fit(Xtr, ytr)  # noqa: E731
                    best = None
                    for cfg in grid:
                        t1 = time.time()
                        m = fit(cfg)
                        secs = time.time() - t1
                        ap_ = average_precision_score(yva, m.predict_proba(Xva)[:, 1])
                        if best is None or ap_ > best[0]:
                            best = (ap_, m, cfg, secs)
                    _, model, params, secs = best
                    p_va = model.predict_proba(Xva)[:, 1]
                elif name == "knn":
                    t1 = time.time()
                    model = AnalogKNN().fit(Xtr, ytr)
                    nb = model.neighbours(Xva, max(KNN_K))
                    secs = time.time() - t1
                    aps = {k: average_precision_score(yva, model.labels_[nb[:, :k]].mean(axis=1))
                           for k in KNN_K}
                    model.k = max(aps, key=aps.get)
                    params = {"k": model.k, "variables": model.variables}
                    p_va = model.labels_[nb[:, :model.k]].mean(axis=1)
                else:
                    if target == "fog" and key not in tuned:
                        study = tune_boosting(name, Xtr, ytr, Xva, yva, n_trials=args.trials)
                        tuned[key] = study.best_params
                        tuned_path.write_text(json.dumps(tuned, indent=2))
                        log(f"  tuned {key}: AP={study.best_value:.4f} {study.best_params}")
                    params = tuned.get(key) or tuned.get(f"{name}_3h")
                    t1 = time.time()
                    if name == "lgbm":
                        model, it = fit_lgbm(Xtr, ytr, Xva, yva, _lgbm_params(None, params))
                        p_va = model.predict_proba(Xva, num_iteration=it)[:, 1]
                    elif name == "cat":
                        model, it = fit_cat(Xtr, ytr, Xva, yva, _cat_params(None, params))
                        p_va = model.predict_proba(Xva)[:, 1]
                    else:
                        model, it = fit_xgb(Xtr, ytr, Xva, yva, _xgb_params(None, params))
                        p_va = model.predict_proba(Xva, iteration_range=(0, it))[:, 1]
                    secs = time.time() - t1
                fm = finalize(name, target, h, feat_cols, model, p_va, yva, g_va, params, it)
                fm.train_seconds = secs
                if name == "knn":
                    # an analog search over the training archive would find each training row
                    # itself, so only the independent periods are forecast
                    raw = np.full(len(X), np.nan)
                    raw[~tr] = fm.predict_raw(X[~tr])
                    pred[f"{name}_raw"] = raw
                else:
                    pred[f"{name}_raw"] = fm.predict_raw(X)
                raw = pred[f"{name}_raw"].to_numpy()
                pred[name] = np.where(np.isnan(raw), np.nan, fm.calibrator.transform(np.nan_to_num(raw)))
                joblib.dump(fm, MODELS / f"tab_{name}_{target}_{h}h.joblib", compress=3)
                log(f"  {name:5s} val AP={average_precision_score(yva, p_va):.4f} "
                    f"cal={fm.calibrator.method} thr={fm.threshold:.2f} "
                    f"fit={secs:.0f}s ({time.time() - t0:.0f}s)")
            out = PRED_DIR / f"pred_{target}_{h}h.parquet"
            if out.exists():           # keep columns of models not re-trained in this run
                old = pd.read_parquet(out)
                for c in old.columns:
                    if c not in pred.columns:
                        pred[c] = old[c].reindex(pred.index)
            pred.to_parquet(out)
    log("done")


if __name__ == "__main__":
    main()
