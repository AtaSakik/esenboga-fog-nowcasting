"""Shared definitions of the model benchmark: the competing forecasts, how their calibrated
probabilities and validation thresholds are loaded, and the greedy ensemble built from them."""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.metrics import average_precision_score

from .config import MODELS, RESULTS

PRED_DIR = RESULTS / "predictions"
TAB = ["lr", "knn", "rf", "xgb", "lgbm", "cat", "ebm", "mlp"]
DEEP = ["gru", "lstm", "tcn", "transformer"]
ENS = ["ens"]
ML = TAB + DEEP + ENS
FAMILY = {"lr": "linear", "knn": "analog", "rf": "trees", "xgb": "trees", "lgbm": "trees",
          "cat": "trees", "ebm": "glass-box", "mlp": "neural", "gru": "neural",
          "lstm": "neural", "tcn": "neural", "transformer": "neural", "ens": "ensemble"}


def weighted_mean(pred: pd.DataFrame, weights: dict[str, float]) -> np.ndarray:
    """Weighted mean of the members' calibrated probabilities, ignoring missing members."""
    num = np.zeros(len(pred))
    den = np.zeros(len(pred))
    for m, w in weights.items():
        p = pred[m].to_numpy(float)
        ok = ~np.isnan(p)
        num[ok] += w * p[ok]
        den[ok] += w
    with np.errstate(invalid="ignore"):
        return np.where(den > 0, num / den, np.nan)


def select_ensemble(probs: dict[str, np.ndarray], y: np.ndarray, rounds: int = 10) -> dict[str, int]:
    """Greedy forward selection with replacement (Caruana et al. 2004): add, one at a time, the
    member whose inclusion most increases the validation PR-AUC of the averaged probabilities;
    stop when no member helps. Returns how often each member was picked (= its weight)."""
    counts: dict[str, int] = {}
    current, best = None, -np.inf
    for _ in range(rounds):
        n = sum(counts.values())
        trials = []
        for m, p in probs.items():
            avg = p if current is None else (current * n + p) / (n + 1)
            trials.append((average_precision_score(y, avg), m, avg))
        score, m, avg = max(trials, key=lambda t: t[0])
        if score <= best + 1e-5:
            break
        best, current = score, avg
        counts[m] = counts.get(m, 0) + 1
    return counts


def load_task(target: str, h: int) -> tuple[pd.DataFrame, dict]:
    """Calibrated probabilities ('<model>'; raw scores in '<model>_raw') and validation-chosen
    thresholds of every model trained for one (target, horizon)."""
    # joblib (pickle) is only used for model files written by our own training scripts
    pred = pd.read_parquet(PRED_DIR / f"pred_{target}_{h}h.parquet")
    thr = {}
    for m in TAB:
        f = MODELS / f"tab_{m}_{target}_{h}h.joblib"
        if f.exists() and m in pred:
            thr[m] = joblib.load(f).threshold
    for c in DEEP:
        f, b = PRED_DIR / f"deep_{c}.parquet", MODELS / f"deep_{c}.joblib"
        key = f"{target}_{h}h"
        if f.exists() and b.exists() and key in pq.read_schema(f).names:
            d = pd.read_parquet(f, columns=[key, key + "_raw"])
            pred[c] = d[key].reindex(pred.index)
            pred[c + "_raw"] = d[key + "_raw"].reindex(pred.index)
            thr[c] = joblib.load(b)["thresholds"][key]
    f = MODELS / f"ens_{target}_{h}h.joblib"
    if f.exists():
        ens = joblib.load(f)
        raw = weighted_mean(pred, ens["weights"])
        pred["ens_raw"] = raw
        pred["ens"] = np.where(np.isnan(raw), np.nan,
                               ens["calibrator"].transform(np.nan_to_num(raw)))
        thr["ens"] = ens["threshold"]
    return pred, thr
