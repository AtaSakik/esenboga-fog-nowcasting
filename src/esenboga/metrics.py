"""Probabilistic, categorical and multi-category verification scores.

Contingency table convention (Jolliffe & Stephenson 2012; Wilks 2019)::

                    observed yes   observed no
    forecast yes        a (hit)     b (false alarm)
    forecast no         c (miss)    d (correct negative)

POD = a/(a+c)   FAR = b/(a+b)   CSI = a/(a+b+c)   bias = (a+b)/(a+c)
HSS = 2(ad-bc)/[(a+c)(c+d)+(a+b)(b+d)]           PSS = a/(a+c) - b/(b+d)
ETS = (a-a_r)/(a+b+c-a_r), a_r = (a+b)(a+c)/n
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score, log_loss, roc_auc_score


# ============================================================================ binary
def contingency(y: np.ndarray, yhat: np.ndarray) -> tuple[int, int, int, int]:
    y = np.asarray(y).astype(bool)
    yhat = np.asarray(yhat).astype(bool)
    a = int(np.sum(yhat & y))
    b = int(np.sum(yhat & ~y))
    c = int(np.sum(~yhat & y))
    d = int(np.sum(~yhat & ~y))
    return a, b, c, d


def categorical_scores(y: np.ndarray, yhat: np.ndarray) -> dict:
    a, b, c, d = contingency(y, yhat)
    n = a + b + c + d
    nan = float("nan")
    pod = a / (a + c) if a + c else nan
    far = b / (a + b) if a + b else nan
    csi = a / (a + b + c) if a + b + c else nan
    pofd = b / (b + d) if b + d else nan
    den = (a + c) * (c + d) + (a + b) * (b + d)
    hss = 2.0 * (a * d - b * c) / den if den else nan
    a_r = (a + b) * (a + c) / n if n else nan
    ets = (a - a_r) / (a + b + c - a_r) if n and (a + b + c - a_r) else nan
    f1 = 2 * a / (2 * a + b + c) if (2 * a + b + c) else nan
    return {"hits": a, "false_alarms": b, "misses": c, "correct_neg": d,
            "POD": pod, "FAR": far, "CSI": csi, "POFD": pofd, "HSS": hss,
            "PSS": pod - pofd if not (np.isnan(pod) or np.isnan(pofd)) else nan,
            "ETS": ets, "bias": (a + b) / (a + c) if a + c else nan, "F1": f1}


def brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def brier_decomposition(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> dict:
    """Murphy (1973) decomposition BS = REL - RES + UNC on equally spaced bins."""
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    bins = np.clip((p * n_bins).astype(int), 0, n_bins - 1)
    ybar = y.mean()
    rel = res = 0.0
    for k in range(n_bins):
        m = bins == k
        if m.any():
            nk = m.sum()
            rel += nk * (p[m].mean() - y[m].mean()) ** 2
            res += nk * (y[m].mean() - ybar) ** 2
    n = len(y)
    return {"REL": rel / n, "RES": res / n, "UNC": ybar * (1 - ybar)}


def probabilistic_scores(y: np.ndarray, p: np.ndarray, p_ref: np.ndarray | None = None) -> dict:
    y = np.asarray(y, float)
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    bs = brier(y, p)
    out = {"n": len(y), "base_rate": float(y.mean()), "Brier": bs,
           "LogLoss": float(log_loss(y, p, labels=[0, 1]))}
    if 0 < y.sum() < len(y):
        out["ROC_AUC"] = float(roc_auc_score(y, p))
        out["PR_AUC"] = float(average_precision_score(y, p))
    else:
        out["ROC_AUC"] = out["PR_AUC"] = float("nan")
    if p_ref is not None:
        bs_ref = brier(y, p_ref)
        out["BSS"] = 1.0 - bs / bs_ref if bs_ref > 0 else float("nan")
    out.update(brier_decomposition(y, p))
    return out


def best_threshold(y: np.ndarray, p: np.ndarray, score: str = "CSI",
                   grid: np.ndarray | None = None) -> float:
    """Probability threshold maximising ``score`` (chosen on validation data only)."""
    grid = np.linspace(0.02, 0.9, 89) if grid is None else grid
    vals = [categorical_scores(y, p >= t)[score] for t in grid]
    vals = np.nan_to_num(np.asarray(vals, float), nan=-1)
    return float(grid[int(np.argmax(vals))])


# ============================================================================ ordinal
def rvr_class_probs(p_lt550: np.ndarray, p_lt350: np.ndarray) -> np.ndarray:
    """Frank & Hall (2001) ordinal decomposition -> class probabilities (n, 3).
    Monotonicity P(<350) <= P(<550) is enforced."""
    p550 = np.clip(np.asarray(p_lt550, float), 0, 1)
    p350 = np.minimum(np.clip(np.asarray(p_lt350, float), 0, 1), p550)
    return np.column_stack([1 - p550, p550 - p350, p350])


def rps(y_cls: np.ndarray, probs: np.ndarray) -> float:
    """Ranked probability score (Epstein 1969), averaged, normalised by (K-1)."""
    y_cls = np.asarray(y_cls).astype(int)
    k = probs.shape[1]
    obs = np.zeros_like(probs)
    obs[np.arange(len(y_cls)), y_cls] = 1
    cum_f = np.cumsum(probs, axis=1)
    cum_o = np.cumsum(obs, axis=1)
    return float(np.mean(np.sum((cum_f - cum_o) ** 2, axis=1)) / (k - 1))


def multiclass_scores(y_cls: np.ndarray, probs: np.ndarray, yhat: np.ndarray,
                      probs_ref: np.ndarray | None = None) -> dict:
    y_cls = np.asarray(y_cls).astype(int)
    out = {"RPS": rps(y_cls, probs), "macro_F1": float(f1_score(y_cls, yhat, average="macro",
                                                                  labels=[0, 1, 2], zero_division=0))}
    if probs_ref is not None:
        out["RPSS"] = 1 - out["RPS"] / rps(y_cls, probs_ref)
    cm = pd.crosstab(pd.Series(y_cls, name="obs"), pd.Series(yhat, name="fcst"),
                     dropna=False).reindex(index=[0, 1, 2], columns=[0, 1, 2], fill_value=0)
    out["confusion"] = cm.values.tolist()
    n = cm.values.sum()
    pc = np.trace(cm.values) / n
    pe = float(np.sum(cm.values.sum(0) * cm.values.sum(1))) / n ** 2
    out["HSS_multi"] = (pc - pe) / (1 - pe) if pe < 1 else float("nan")
    for k in (1, 2):   # "at least category k" as a binary event
        out[f"ge{k}"] = categorical_scores(y_cls >= k, yhat >= k)
    return out


# ============================================================================ uncertainty
def block_bootstrap(stat_fn, arrays: list[np.ndarray], blocks: np.ndarray,
                    n_boot: int = 1000, seed: int = 0, alpha: float = 0.05) -> tuple:
    """Moving-block style bootstrap that resamples whole blocks (e.g. days) with replacement,
    preserving the strong serial correlation of half-hourly fog data. Returns (lo, hi, samples)."""
    rng = np.random.default_rng(seed)
    uniq, inv = np.unique(blocks, return_inverse=True)
    idx_by_block = [np.flatnonzero(inv == k) for k in range(len(uniq))]
    samples = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(uniq), len(uniq))
        idx = np.concatenate([idx_by_block[k] for k in pick])
        try:
            samples.append(stat_fn(*[a[idx] for a in arrays]))
        except ValueError:
            continue
    s = np.asarray(samples, float)
    s = s[~np.isnan(s)]
    if not len(s):
        return float("nan"), float("nan"), s
    return float(np.quantile(s, alpha / 2)), float(np.quantile(s, 1 - alpha / 2)), s
