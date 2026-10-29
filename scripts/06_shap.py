"""Step 6 – SHAP explanations of the LightGBM fog models (TreeSHAP, Lundberg et al. 2020).

Explains the raw log-odds output on a test-period sample (all fog cases + random non-fog).
Outputs: results/tables/shap_importance.csv, shap_groups.csv, results/shap_values_<h>h.npz,
figures shap_bar, shap_groups, shap_beeswarm_<h>h, shap_dependence, shap_waterfall (EN/TR).
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esenboga.config import HORIZONS, MODELS, RANDOM_STATE, RESULTS, TABLES  # noqa: E402
from esenboga.data import load_processed, task_frame  # noqa: E402
from esenboga.labels import FEATURE_GROUPS, label  # noqa: E402
from esenboga.plots import COL_W, PAGE_W, T, save, setup_style  # noqa: E402

N_NEG = 6000
TOP = 15


def explain(h: int, feats, targ):
    fm = joblib.load(MODELS / f"tab_lgbm_fog_{h}h.joblib")   # trusted local artefact
    X, y, split = task_frame(feats, targ, "fog", h)
    te = (split == "test").to_numpy()
    Xt, yt = X[te][fm.features], y[te].to_numpy()
    rng = np.random.default_rng(RANDOM_STATE)
    pos = np.flatnonzero(yt == 1)
    neg = rng.choice(np.flatnonzero(yt == 0), size=min(N_NEG, (yt == 0).sum()), replace=False)
    sel = np.sort(np.concatenate([pos, neg]))
    Xs = Xt.iloc[sel]
    explainer = shap.TreeExplainer(fm.model.booster_)
    sv = explainer.shap_values(Xs)
    sv = sv[1] if isinstance(sv, list) else sv
    base = explainer.expected_value
    base = float(base[1] if np.ndim(base) else base)
    np.savez_compressed(RESULTS / f"shap_values_{h}h.npz", shap=sv, X=Xs.to_numpy(),
                        columns=np.array(Xs.columns), y=yt[sel], base=base,
                        time=Xs.index.astype("int64").to_numpy(),
                        p=fm.predict(Xs))
    return Xs, sv, base, yt[sel], fm


def _fmt_value(name: str, x: float) -> str:
    if np.isnan(x):
        return "–"
    if name.startswith(("wx_", "is_", "vt_is_")) or name in ("fog_now", "calm", "cavok", "low_cloud"):
        return "1" if x >= 0.5 else "0"
    if abs(x) >= 100:
        return f"{x:.0f}"
    return f"{x:.1f}"


def local_explanation(row: pd.Series, values: np.ndarray, base: float, p_cal: float,
                      thr: float, lang: str, top: int = 10):
    """Signed SHAP contributions of one forecast (custom, IEEE-sized waterfall summary)."""
    order = np.argsort(-np.abs(values))
    keep, rest = order[:top], order[top:]
    names = [f"{label(row.index[i], lang)} = {_fmt_value(row.index[i], row.iloc[i])}" for i in keep]
    vals = list(values[keep])
    names.append(T(lang, f"{len(rest)} other features", f"Diğer {len(rest)} öznitelik"))
    vals.append(values[rest].sum())
    fig, ax = plt.subplots(figsize=(COL_W, 2.9))
    y = np.arange(len(vals))[::-1]
    ax.barh(y, vals, color=["#c8323f" if v > 0 else "#2a5bd7" for v in vals], height=0.65)
    for yi, v in zip(y, vals):
        ax.text(v + (0.04 if v >= 0 else -0.04), yi, f"{v:+.2f}", va="center",
                ha="left" if v >= 0 else "right", fontsize=6)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=6.2)
    ax.axvline(0, color="k", lw=0.6)
    lim = max(abs(min(vals)), abs(max(vals))) * 1.35
    ax.set_xlim(-lim * 0.35 if min(vals) >= 0 else -lim, lim)
    ax.set_xlabel(T(lang, "SHAP contribution (log-odds)", "SHAP katkısı (log-odds)"))
    ax.text(0.98, 0.42, T(lang, f"E[f(X)] = {base:.2f}\nf(x) = {base + values.sum():.2f}\np = {p_cal:.2f} (τ = {thr:.2f})",
                          f"E[f(X)] = {base:.2f}\nf(x) = {base + values.sum():.2f}\np = {p_cal:.2f} (τ = {thr:.2f})"),
            transform=ax.transAxes, ha="right", va="center", fontsize=6.3,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#b9c4ce", lw=0.5))
    ax.grid(axis="x")
    fig.tight_layout()
    return fig


def beeswarm(Xs: pd.DataFrame, sv: np.ndarray, lang: str, top: int = 12):
    """Compact beeswarm: SHAP value per sample, coloured by the feature's percentile rank."""
    order = np.argsort(-np.abs(sv).mean(axis=0))[:top]
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots(figsize=(COL_W, 3.3))
    for row, j in enumerate(order):
        x = sv[:, j]
        v = Xs.iloc[:, j].to_numpy(dtype=float)
        rank = pd.Series(v).rank(pct=True).to_numpy()
        y = len(order) - 1 - row + rng.normal(0, 0.09, len(x)).clip(-0.3, 0.3)
        sc = ax.scatter(x, y, c=np.nan_to_num(rank, nan=0.5), cmap="coolwarm", s=1.2,
                        alpha=0.55, rasterized=True, vmin=0, vmax=1, lw=0)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([label(Xs.columns[j], lang) for j in order[::-1]], fontsize=6.2)
    ax.axvline(0, color="0.4", lw=0.6)
    ax.set_xlabel(T(lang, "SHAP value (log-odds of fog)", "SHAP değeri (sis log-odds)"))
    cb = fig.colorbar(sc, ax=ax, pad=0.015, fraction=0.05, ticks=[0, 1])
    cb.ax.set_yticklabels([T(lang, "low", "düşük"), T(lang, "high", "yüksek")], fontsize=6)
    cb.set_label(T(lang, "Feature value (rank)", "Öznitelik değeri (sıra)"), fontsize=6.3)
    cb.solids.set_alpha(1)
    ax.grid(axis="x")
    fig.tight_layout()
    return fig


def main() -> None:
    setup_style()
    feats, targ = load_processed()
    imp_rows, grp_rows, store = [], [], {}
    for h in HORIZONS:
        Xs, sv, base, ys, fm = explain(h, feats, targ)
        store[h] = (Xs, sv, base, ys, fm)
        mean_abs = np.abs(sv).mean(axis=0)
        total = mean_abs.sum()
        for c, v in zip(Xs.columns, mean_abs):
            imp_rows.append({"h": h, "feature": c, "mean_abs_shap": v, "share": v / total})
        for g, cols in FEATURE_GROUPS.items():
            k = [Xs.columns.get_loc(c) for c in cols if c in Xs.columns]
            grp_rows.append({"h": h, "group": g, "share": mean_abs[k].sum() / total})
        print(f"h={h}: top features",
              [Xs.columns[i] for i in np.argsort(-mean_abs)[:8]], flush=True)
    imp = pd.DataFrame(imp_rows)
    imp.to_csv(TABLES / "shap_importance.csv", index=False)
    grp = pd.DataFrame(grp_rows)
    grp.to_csv(TABLES / "shap_groups.csv", index=False)

    for lang in ("en", "tr"):
        # ---------------------------------------------------- top-15 bars per horizon
        fig, axes = plt.subplots(1, 3, figsize=(PAGE_W, 3.0), sharex=False)
        for ax, h in zip(axes, HORIZONS):
            d = imp[imp.h == h].nlargest(TOP, "mean_abs_shap").iloc[::-1]
            ax.barh([label(c, lang) for c in d.feature], d.mean_abs_shap, color="#1f77b4")
            ax.set_title(T(lang, f"Lead time {h} h", f"Öngörü süresi {h} sa"))
            ax.set_xlabel(T(lang, "Mean |SHAP| (log-odds)", "Ortalama |SHAP| (log-odds)"))
            ax.tick_params(axis="y", labelsize=6)
            ax.grid(axis="x")
        fig.tight_layout()
        save(fig, "shap_bar", lang)

        # ---------------------------------------------------- group shares
        fig, ax = plt.subplots(figsize=(COL_W, 2.1))
        groups = list(FEATURE_GROUPS)
        left = np.zeros(len(HORIZONS))
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd", "#8c564b"]
        for g, col in zip(groups, colors):
            vals = [grp[(grp.h == h) & (grp.group == g)].share.iloc[0] for h in HORIZONS]
            name = g.split(" / ")[1] if lang == "tr" else g.split(" / ")[0]
            ax.barh([f"{h} h" if lang == "en" else f"{h} sa" for h in HORIZONS], vals,
                    left=left, color=col, label=name)
            left += np.asarray(vals)
        ax.set_xlim(0, 1)
        ax.set_xlabel(T(lang, "Share of total mean |SHAP|", "Toplam ortalama |SHAP| payı"))
        ax.legend(ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.32), frameon=False)
        ax.invert_yaxis()
        save(fig, "shap_groups", lang)

        # ---------------------------------------------------- beeswarm 1 h and 6 h
        for h in (HORIZONS[0], HORIZONS[-1]):
            Xs, sv, base, ys, fm = store[h]
            save(beeswarm(Xs, sv, lang), f"shap_beeswarm_{h}h", lang)

        # ---------------------------------------------------- dependence plots (3 h)
        Xs, sv, base, ys, fm = store[3 if 3 in store else HORIZONS[0]]
        dep = [("dpd_c", "wind_speed_kt"), ("wind_speed_kt", "dpd_c"),
               ("vt_solar_elev", "fog_now"), ("rh_max_6h", "wind_speed_kt")]
        units = {"dpd_c": " (°C)", "wind_speed_kt": " (kt)", "vt_solar_elev": " (°)",
                 "rh_max_6h": " (%)"}
        fig, axes = plt.subplots(1, 4, figsize=(PAGE_W, 1.75))
        for ax, (f, col) in zip(axes.ravel(), dep):
            i = Xs.columns.get_loc(f)
            x = Xs[f].to_numpy()
            c = Xs[col].to_numpy()
            ok = ~np.isnan(x)
            binary = set(np.unique(c[~np.isnan(c)])) <= {0.0, 1.0}
            lo, hi = (0, 1) if binary else (np.nanpercentile(c, 5), np.nanpercentile(c, 95))
            sc = ax.scatter(x[ok], sv[ok, i], c=c[ok], s=2, cmap="coolwarm", alpha=0.6,
                            rasterized=True, vmin=lo, vmax=hi)
            ax.axhline(0, color="k", lw=0.5)
            ax.set_xlabel(label(f, lang) + units.get(f, ""))
            ax.set_ylabel("SHAP")
            if f == "dpd_c":
                ax.set_xlim(-0.5, 12)
            if f == "rh_max_6h":
                ax.set_xlim(40, 101)
            cb = fig.colorbar(sc, ax=ax, pad=0.01)
            if binary:
                cb.set_ticks([0, 1])
            cb.set_label(label(col, lang) + units.get(col, ""), fontsize=6)
            cb.ax.tick_params(labelsize=6)
        fig.tight_layout()
        save(fig, "shap_dependence", lang)

        # ---------------------------------------------------- local explanation
        p = fm.predict(Xs)
        fog_now = Xs["fog_now"].to_numpy()
        cand = np.flatnonzero((ys == 1) & (fog_now == 0) & (p >= fm.threshold))
        k = cand[np.argmax(p[cand])] if len(cand) else int(np.argmax(p))
        fig = local_explanation(Xs.iloc[k], sv[k], base, p[k], fm.threshold, lang)
        save(fig, "shap_waterfall", lang)
        (TABLES / "shap_waterfall_case.txt").write_text(
            f"time={Xs.index[k]} p_cal={p[k]:.3f} threshold={fm.threshold:.2f} "
            f"vis_now={Xs['vis_m'].iloc[k]} dpd={Xs['dpd_c'].iloc[k]} "
            f"wind={Xs['wind_speed_kt'].iloc[k]}\n")
    print(grp.pivot(index="group", columns="h", values="share").round(3))


if __name__ == "__main__":
    main()
