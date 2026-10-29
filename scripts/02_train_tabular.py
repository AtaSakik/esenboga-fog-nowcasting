"""Step 2 – train, tune, calibrate the tabular models for every (target, horizon).

Models: logistic regression, random forest, XGBoost (GPU), LightGBM.
Tuning: Optuna on the validation seasons (boosting tuned on the fog target; RVR targets reuse
the fog hyper-parameters of the same horizon). Calibration + CSI-optimal threshold: validation.
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
from esenboga.models import (_lgbm_params, _xgb_params, finalize, fit_lgbm,  # noqa: E402
                             fit_xgb, make_lr, make_rf, tune_boosting)

PRED_DIR = RESULTS / "predictions"
PRED_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", type=int, nargs="+", default=HORIZONS)
    ap.add_argument("--targets", nargs="+", default=["fog", "rvr550", "rvr350"])
    ap.add_argument("--models", nargs="+", default=["lr", "rf", "xgb", "lgbm"])
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
                if name == "lr":
                    best = None
                    for C in (0.01, 0.1, 1.0):
                        m = make_lr(C).fit(Xtr, ytr)
                        ap_ = average_precision_score(yva, m.predict_proba(Xva)[:, 1])
                        if best is None or ap_ > best[0]:
                            best = (ap_, m, {"C": C})
                    _, model, params = best
                    p_va = model.predict_proba(Xva)[:, 1]
                    fm = finalize(name, target, h, feat_cols, model, p_va, yva, g_va, params)
                elif name == "rf":
                    best = None
                    for cfg in ({"min_samples_leaf": 10, "max_features": "sqrt"},
                                {"min_samples_leaf": 30, "max_features": "sqrt"},
                                {"min_samples_leaf": 30, "max_features": 0.3}):
                        m = make_rf(cfg).fit(Xtr, ytr)
                        ap_ = average_precision_score(yva, m.predict_proba(Xva)[:, 1])
                        if best is None or ap_ > best[0]:
                            best = (ap_, m, cfg)
                    _, model, params = best
                    p_va = model.predict_proba(Xva)[:, 1]
                    fm = finalize(name, target, h, feat_cols, model, p_va, yva, g_va, params)
                else:
                    if target == "fog" and key not in tuned:
                        study = tune_boosting(name, Xtr, ytr, Xva, yva, n_trials=args.trials)
                        tuned[key] = study.best_params
                        tuned_path.write_text(json.dumps(tuned, indent=2))
                        log(f"  tuned {key}: AP={study.best_value:.4f} {study.best_params}")
                    params = tuned.get(key) or tuned.get(f"{name}_3h")
                    if name == "lgbm":
                        model, it = fit_lgbm(Xtr, ytr, Xva, yva, _lgbm_params(None, params))
                        p_va = model.predict_proba(Xva, num_iteration=it)[:, 1]
                    else:
                        model, it = fit_xgb(Xtr, ytr, Xva, yva, _xgb_params(None, params))
                        p_va = model.predict_proba(Xva, iteration_range=(0, it))[:, 1]
                    fm = finalize(name, target, h, feat_cols, model, p_va, yva, g_va, params, it)
                pred[f"{name}_raw"] = fm.predict_raw(X)
                pred[name] = fm.calibrator.transform(pred[f"{name}_raw"].to_numpy())
                joblib.dump(fm, MODELS / f"tab_{name}_{target}_{h}h.joblib", compress=3)
                log(f"  {name:5s} val AP={average_precision_score(yva, p_va):.4f} "
                    f"cal={fm.calibrator.method} thr={fm.threshold:.2f} "
                    f"({time.time() - t0:.0f}s)")
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
