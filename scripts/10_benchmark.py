"""Step 10 – the model benchmark on the test seasons (fog, VIS < 1000 m).

* benchmark_leaderboard.csv  every model x lead time: PR-AUC, BSS, CSI, HSS, SEDI, POD, FAR,
                             the rank on each score and the mean rank
* benchmark_pairwise.csv     every model against the best one of its lead time: paired day-block
                             bootstrap differences of PR-AUC and CSI, two-sided p-values and
                             Holm-adjusted significance (Holm 1979)
* economic_value.csv         relative economic value V(alpha) (Richardson 2000) of every model and
                             reference forecast for cost/loss ratios alpha in (0, 1)
* benchmark_cost.csv         fit time of the selected configuration, prediction time per 10 000
                             rows, model size and how each model can be explained
Run after 05_evaluate.py (it reuses the expert-rule thresholds tuned there).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esenboga.baselines import expert_rule, trend_forecasts, vis_to_event  # noqa: E402
from esenboga.benchmark import DEEP, FAMILY, ML, TAB, load_task  # noqa: E402
from esenboga.config import HORIZONS, MODELS, PROCESSED, TABLES  # noqa: E402
from esenboga.data import climatology, task_frame  # noqa: E402
from esenboga.features import feature_matrix  # noqa: E402
from esenboga.metrics import (brier, categorical_scores, probabilistic_scores,  # noqa: E402
                              relative_value)

RNG = np.random.default_rng(2026)
SCORES = {"PR_AUC": True, "BSS": True, "CSI": True, "HSS": True, "SEDI": True}  # higher = better
ALPHAS = np.round(np.concatenate([np.arange(0.01, 0.1, 0.01), np.arange(0.1, 1.0, 0.05)]), 3)
EXPLAIN = {"lr": "coefficients (built in)", "knn": "the past analog cases (built in)",
           "ebm": "per-feature shape functions (built in)", "rf": "SHAP (post hoc)",
           "xgb": "SHAP (post hoc)", "lgbm": "SHAP (post hoc)", "cat": "SHAP (post hoc)",
           "mlp": "post hoc only", "gru": "post hoc only", "lstm": "post hoc only",
           "tcn": "post hoc only", "transformer": "post hoc only", "ens": "via its members"}


def day_blocks(index: pd.DatetimeIndex, n_boot: int) -> tuple[np.ndarray, list[np.ndarray]]:
    """Day codes of the rows and n_boot resamples of whole days (rows of the picked days)."""
    days = pd.factorize(index.floor("D"))[0]
    rows_by_day = np.split(np.argsort(days, kind="stable"), np.cumsum(np.bincount(days))[:-1])
    picks = [np.concatenate([rows_by_day[k] for k in RNG.integers(0, len(rows_by_day), len(rows_by_day))])
             for _ in range(n_boot)]
    return days, picks


def holm(pvals: list[float]) -> np.ndarray:
    """Holm-Bonferroni adjusted p-values (step-down, monotone)."""
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(p) - rank) * p[i]))
        adj[i] = running
    return adj


def main() -> None:
    feats = pd.read_parquet(PROCESSED / "features.parquet")
    rules = json.loads((TABLES / "expert_rule.json").read_text())
    board, pairs, value = [], [], []
    for h in HORIZONS:
        pred, thr = load_task("fog", h)
        idx, split = pred.index, pred["split"].to_numpy()
        y_all = pred["y"].to_numpy().astype(int)
        models = [m for m in ML if m in thr]
        # test rows on which every model has a forecast (all of them, in practice)
        test = (split == "test") & pred[models].notna().all(axis=1).to_numpy()
        clim = climatology(idx[split == "train"], y_all[split == "train"], idx, h)[test]
        y = y_all[test]
        P = {m: pred[m].to_numpy()[test] for m in models}
        D = {m: P[m] >= thr[m] for m in models}

        # ------------------------------------------------------------- reference forecasts
        Xh = feature_matrix(None, h, base=feats).reindex(idx)
        refs = {"persistence": feats["fog_now"].reindex(idx).to_numpy()[test] == 1,
                "expert_rule": expert_rule(Xh, **rules[f"{h}h"])[test] == 1}
        if h <= 2:
            refs["trend"] = vis_to_event(trend_forecasts(idx, h)["trend_vis_prev"])[test] == 1

        # ------------------------------------------------------------- leaderboard
        for m in models:
            board.append({"h": h, "model": m, "family": FAMILY[m],
                          **{k: v for k, v in probabilistic_scores(y, P[m], clim).items()
                             if k in ("PR_AUC", "ROC_AUC", "BSS", "Brier")},
                          **categorical_scores(y, D[m])})
        for name, yhat in refs.items():
            board.append({"h": h, "model": name, "family": "reference",
                          "Brier": brier(y, yhat.astype(float)),
                          "BSS": 1 - brier(y, yhat.astype(float)) / brier(y, clim),
                          **categorical_scores(y, yhat)})

        # ------------------------------------------------------------- vs the best model
        days, picks = day_blocks(idx[test], 1000)
        best = max(models, key=lambda m: average_precision_score(y, P[m]))
        stats = {m: {"PR_AUC": [], "CSI": []} for m in models}
        for rows in picks:
            yy = y[rows]
            if yy.sum() == 0:
                continue
            for m in models:
                stats[m]["PR_AUC"].append(average_precision_score(yy, P[m][rows]))
                stats[m]["CSI"].append(categorical_scores(yy, D[m][rows])["CSI"])
        rows_h = []
        for m in models:
            if m == best:
                continue
            for metric in ("PR_AUC", "CSI"):
                diff = np.asarray(stats[m][metric]) - np.asarray(stats[best][metric])
                p = 2 * min((diff <= 0).mean(), (diff >= 0).mean())
                rows_h.append({"h": h, "model": m, "vs": best, "metric": metric,
                               "diff_mean": float(diff.mean()),
                               "lo": float(np.quantile(diff, 0.025)),
                               "hi": float(np.quantile(diff, 0.975)), "p": float(min(1.0, p))})
        for metric in ("PR_AUC", "CSI"):
            sub = [r for r in rows_h if r["metric"] == metric]
            for r, pa in zip(sub, holm([r["p"] for r in sub])):
                r["p_holm"] = float(pa)
                r["significant"] = bool(pa < 0.05)
        pairs.extend(rows_h)

        # ------------------------------------------------------------- economic value
        for m in models:
            v = [relative_value(y, P[m] >= a, a) for a in ALPHAS]
            value.extend({"h": h, "model": m, "alpha": a, "V": float(x)} for a, x in zip(ALPHAS, v))
        for name, yhat in refs.items():
            v = relative_value(y, yhat, ALPHAS)
            value.extend({"h": h, "model": name, "alpha": a, "V": float(x)} for a, x in zip(ALPHAS, v))
        print(f"h={h}: best by PR-AUC on test = {best}", flush=True)

    lb = pd.DataFrame(board)
    for h in HORIZONS:
        sel = (lb["h"] == h) & (lb["family"] != "reference")
        for s in SCORES:
            lb.loc[sel, f"rank_{s}"] = lb.loc[sel, s].rank(ascending=False, method="min")
        lb.loc[sel, "mean_rank"] = lb.loc[sel, [f"rank_{s}" for s in SCORES]].mean(axis=1)
    lb.to_csv(TABLES / "benchmark_leaderboard.csv", index=False)
    pd.DataFrame(pairs).to_csv(TABLES / "benchmark_pairwise.csv", index=False)
    pd.DataFrame(value).to_csv(TABLES / "economic_value.csv", index=False)
    cols = ["h", "model", "PR_AUC", "BSS", "CSI", "HSS", "SEDI", "mean_rank"]
    with pd.option_context("display.width", 200):
        print(lb[cols].sort_values(["h", "mean_rank"]).round(3).to_string(index=False))
    cost_table()


def refit_seconds(fm, Xtr, ytr, Xva, yva) -> float:
    """Time to refit the selected configuration of a tabular model once (the refit is discarded),
    so that every technique is timed on the same machine under the same conditions."""
    from esenboga.models import (AnalogKNN, TabularMLP, _cat_params, _lgbm_params, _xgb_params,
                                 fit_cat, fit_lgbm, fit_xgb, make_ebm, make_lr, make_rf)

    t0 = time.perf_counter()
    if fm.name == "lr":
        make_lr(**fm.params).fit(Xtr, ytr)
    elif fm.name == "knn":
        AnalogKNN(fm.params["k"], fm.params["variables"]).fit(Xtr, ytr)
    elif fm.name == "rf":
        make_rf(fm.params).fit(Xtr, ytr)
    elif fm.name == "lgbm":
        fit_lgbm(Xtr, ytr, Xva, yva, _lgbm_params(None, fm.params))
    elif fm.name == "cat":
        fit_cat(Xtr, ytr, Xva, yva, _cat_params(None, fm.params))
    elif fm.name == "ebm":
        make_ebm(**fm.params).fit(Xtr, ytr)
    elif fm.name == "mlp":
        TabularMLP(**fm.params).fit(Xtr, ytr, Xva, yva)
    else:
        fit_xgb(Xtr, ytr, Xva, yva, _xgb_params(None, fm.params))
    return time.perf_counter() - t0


def cost_table() -> None:
    """Fit time of the selected configuration (fog, 3 h for the tabular models; the one
    multi-task network for the sequence models), time to predict 10 000 test rows on this
    machine, model file size and how the model can be explained."""
    from esenboga.data import load_processed

    feats, targ = load_processed()
    X, y, split = task_frame(feats, targ, "fog", 3)
    tr, va = (split == "train").to_numpy(), (split == "val").to_numpy()
    Xs = X[(split == "test").to_numpy()].iloc[:10000]
    rows = []
    for m in TAB:
        f = MODELS / f"tab_{m}_fog_3h.joblib"
        if not f.exists():
            continue
        fm = joblib.load(f)                                        # our own model file
        fit_s = refit_seconds(fm, X[tr], y[tr].to_numpy(), X[va], y[va].to_numpy())
        fm.predict(Xs.iloc[:100])                                  # warm-up (GPU, lazy loading)
        t0 = time.perf_counter()
        fm.predict(Xs)
        rows.append({"model": m, "fit_s": fit_s,
                     "predict_ms_per_10k": 1000 * (time.perf_counter() - t0),
                     "size_mb": f.stat().st_size / 1e6, "explanation": EXPLAIN[m]})
    for c in DEEP:
        f = MODELS / f"deep_{c}.joblib"
        if f.exists():
            rows.append({"model": c, "fit_s": joblib.load(f).get("train_seconds"),
                         "size_mb": f.stat().st_size / 1e6, "explanation": EXPLAIN[c]})
    pd.DataFrame(rows).to_csv(TABLES / "benchmark_cost.csv", index=False)
    print(pd.DataFrame(rows).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
