"""Step 7 – publication figures (IEEE style) in English and Turkish.

Requires steps 1-5. Writes results/figures/{en,tr}/*.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from sklearn.metrics import precision_recall_curve

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esenboga.config import HORIZONS, PROCESSED, RESULTS, TABLES  # noqa: E402
from esenboga.plots import (COL_W, MODEL_COLORS, PAGE_W, T, mlabel, save,  # noqa: E402
                            setup_style)

PRED = RESULTS / "predictions"
ML = ["lr", "rf", "xgb", "lgbm", "gru", "lstm"]
MONTHS = {"en": ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"],
          "tr": ["O", "Ş", "M", "N", "M", "H", "T", "A", "E", "E", "K", "A"]}


def load_pred(target: str, h: int) -> pd.DataFrame:
    pred = pd.read_parquet(PRED / f"pred_{target}_{h}h.parquet")
    for c in ("gru", "lstm"):
        f = PRED / f"deep_{c}.parquet"
        if f.exists():
            pred[c] = pd.read_parquet(f, columns=[f"{target}_{h}h"])[f"{target}_{h}h"].reindex(pred.index)
    return pred


# ============================================================================ figures
def fig_climatology(grid, lang):
    obs = grid["vis_m"].notna()
    fog = (grid["vis_m"] < 1000) & obs
    idx = grid.index
    fig, axes = plt.subplots(1, 3, figsize=(PAGE_W, 2.15),
                             gridspec_kw={"width_ratios": [1.35, 1.0, 1.45]})
    # (a) annual fog hours
    yr = idx.year
    hours = fog.groupby(yr).sum() / 2
    cov = obs.groupby(yr).mean()
    full = hours[(hours.index <= 2025)]
    ax = axes[0]
    ax.bar(full.index, full.values, color="#5b7a99", width=0.8)
    ax.axvspan(2010.5, 2020.5, color="#f2c200", alpha=0.18, lw=0)
    ax.text(2015.5, full.max() * 0.98, T(lang, "2011–2020: %d h" % hours.loc[2011:2020].sum(),
                                         "2011–2020: %d sa" % hours.loc[2011:2020].sum()),
            ha="center", va="top", fontsize=6.5)
    ax.set_ylabel(T(lang, "Fog hours (VIS < 1000 m)", "Sisli saat (görüş < 1000 m)"))
    ax.set_title(T(lang, "(a) Annual fog hours", "(a) Yıllık sisli saat"))
    ax.set_xticks([2005, 2010, 2015, 2020, 2025])
    # (b) monthly frequency
    m = idx.month
    rate = fog.groupby(m).sum() / obs.groupby(m).sum() * 100
    ax = axes[1]
    ax.bar(range(1, 13), rate.reindex(range(1, 13)).values, color="#5b7a99")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(MONTHS[lang])
    ax.set_ylabel(T(lang, "Frequency (%)", "Sıklık (%)"))
    ax.set_title(T(lang, "(b) Monthly frequency", "(b) Aylık sıklık"))
    # (c) month x local hour
    hl = (idx.hour + 3) % 24
    tab = pd.DataFrame({"m": m, "h": hl, "fog": fog, "obs": obs})
    piv = (tab.groupby(["m", "h"]).fog.sum() / tab.groupby(["m", "h"]).obs.sum() * 100).unstack()
    order = [9, 10, 11, 12, 1, 2, 3, 4]
    piv = piv.reindex(order)
    ax = axes[2]
    im = ax.imshow(piv.values, aspect="auto", cmap="Blues", origin="upper")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([MONTHS[lang][k - 1] for k in order])
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlabel(T(lang, "Local time (UTC+3)", "Yerel saat (UTC+3)"))
    ax.set_title(T(lang, "(c) Frequency by month and hour (%)", "(c) Aya ve saate göre sıklık (%)"))
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.ax.tick_params(labelsize=6)
    fig.tight_layout()
    return save(fig, "climatology", lang)


def fig_pr_curves(lang):
    fig, axes = plt.subplots(1, 3, figsize=(PAGE_W, 2.35), sharey=True)
    sc = pd.read_csv(TABLES / "scores_all.csv")
    for ax, h in zip(axes, HORIZONS):
        pred = load_pred("fog", h)
        te = pred[pred.split == "test"]
        y = te["y"].to_numpy()
        for mname in ML:
            if mname not in te:
                continue
            p = te[mname].to_numpy()
            ok = ~np.isnan(p)
            pr, rc, _ = precision_recall_curve(y[ok], p[ok])
            row = sc[(sc.target == "fog") & (sc.h == h) & (sc.split == "test") &
                     (sc.season == "all") & (sc.model == mname)]
            ap = row.PR_AUC.iloc[0] if len(row) else np.nan
            ax.plot(rc, pr, color=MODEL_COLORS[mname], lw=1.0,
                    label=f"{mlabel(mname, lang)} ({ap:.2f})")
        for b, mk in (("persistence", "o"), ("trend_prev", "s"), ("trend_worst", "D")):
            row = sc[(sc.target == "fog") & (sc.h == h) & (sc.split == "test") &
                     (sc.season == "all") & (sc.model == b)]
            if len(row):
                ax.plot(row.POD.iloc[0], 1 - row.FAR.iloc[0], mk, color=MODEL_COLORS[b], ms=4.5,
                        label=mlabel(b, lang))
        ax.set_title(T(lang, f"Lead time {h} h", f"Öngörü süresi {h} sa"))
        ax.set_xlabel(T(lang, "Recall (POD)", "Duyarlılık (POD)"))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.02)
        ax.grid(True)
        ax.legend(fontsize=5.3, loc="lower left" if h == HORIZONS[0] else "upper right",
                  frameon=True, framealpha=0.9, edgecolor="none", handlelength=1.4)
    axes[0].set_ylabel(T(lang, "Precision (1 − FAR)", "Kesinlik (1 − FAR)"))
    fig.tight_layout()
    return save(fig, "pr_curves", lang)


def fig_reliability(lang):
    """Single-panel reliability diagram: LightGBM (solid) and GRU (dashed) at 1, 3, 6 h."""
    fig, ax = plt.subplots(figsize=(COL_W, 2.55))
    ax.plot([0, 1], [0, 1], color="0.6", lw=0.8, ls=":")
    colors = {1: "#1f77b4", 3: "#9467bd", 6: "#2ca02c"}
    edges = np.array([0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001])
    for h in HORIZONS:
        pred = load_pred("fog", h)
        te = pred[pred.split == "test"]
        y = te["y"].to_numpy()
        for mname, ls in (("lgbm", "-"), ("gru", "--")):
            if mname not in te:
                continue
            p = te[mname].to_numpy()
            ok = ~np.isnan(p)
            p, yy = p[ok], y[ok]
            b = np.digitize(p, edges) - 1
            xs, ys = [], []
            for k in range(len(edges) - 1):
                sel = b == k
                if sel.sum() >= 15:
                    xs.append(p[sel].mean())
                    ys.append(yy[sel].mean())
            ax.plot(xs, ys, marker="o", ms=2.3, ls=ls, lw=1.0, color=colors[h],
                    label=f"{mlabel(mname, lang)}, {h} {'h' if lang == 'en' else 'sa'}")
    ax.set_xlabel(T(lang, "Forecast probability", "Tahmin olasılığı"))
    ax.set_ylabel(T(lang, "Observed frequency", "Gözlenen sıklık"))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.grid(True)
    ax.legend(frameon=False, loc="upper left", fontsize=6, ncol=2)
    fig.tight_layout()
    return save(fig, "reliability", lang)


def fig_leadtime(lang):
    lc = pd.read_csv(TABLES / "leadtime_curve.csv")
    lc = lc[lc.target == "fog"]
    bs = pd.read_csv(TABLES / "bootstrap_test.csv")
    tr = pd.read_csv(TABLES / "trend_comparison.csv")
    fig, axes = plt.subplots(1, 2, figsize=(COL_W * 1.45, 2.0))
    for ax, metric in zip(axes, ("CSI", "HSS")):
        for name in ("lgbm", "persistence"):
            d = lc[lc.model == name].sort_values("h")
            ax.plot(d.h, d[metric], "o-", ms=3, color=MODEL_COLORS[name], label=mlabel(name, lang))
            b = bs[(bs.target == "fog") & (bs.model == name)].sort_values("h")
            if len(b):
                ax.fill_between(b.h, b[f"{metric}_lo"], b[f"{metric}_hi"], color=MODEL_COLORS[name],
                                alpha=0.15, lw=0)
        for reading, mk in (("trend_prev", "s"), ("trend_worst", "D")):
            d = tr[(tr.split == "test") & (tr.forecast == reading)]
            if len(d):
                ax.plot(d.h, d[metric], mk, color=MODEL_COLORS[reading], ms=4,
                        label=mlabel(reading, lang))
        ax.set_xlabel(T(lang, "Lead time (h)", "Öngörü süresi (sa)"))
        ax.set_title(metric)
        ax.set_xticks(range(1, 7))
        ax.set_ylim(0, 1)
        ax.grid(True)
    axes[0].legend(frameon=False, fontsize=5.8)
    fig.tight_layout()
    return save(fig, "leadtime", lang)


def fig_onset(lang):
    od = pd.read_csv(TABLES / "onset_dissipation.csv")
    fig, axes = plt.subplots(1, 2, figsize=(COL_W * 1.45, 2.0), sharey=True)
    names = [n for n in ("persistence", "lr", "rf", "xgb", "lgbm", "gru", "lstm") if n in od]
    for ax, ev in zip(axes, ("onset", "dissipation")):
        d = od[od.event == ev].sort_values("h")
        w = 0.8 / len(names)
        for k, n in enumerate(names):
            ax.bar(d.h + (k - len(names) / 2 + 0.5) * w, d[n], width=w, color=MODEL_COLORS[n],
                   label=mlabel(n, lang))
        ax.set_xticks(HORIZONS)
        ax.set_xlabel(T(lang, "Lead time (h)", "Öngörü süresi (sa)"))
        ax.set_title(T(lang, "Fog onsets" if ev == "onset" else "Fog dissipations",
                       "Sis başlangıçları" if ev == "onset" else "Sis dağılmaları")
                     + f" (n={int(d.n_events.iloc[0])})")
        ax.set_ylim(0, 1)
        ax.grid(True, axis="y")
    axes[0].set_ylabel(T(lang, "Fraction correctly forecast", "Doğru tahmin oranı"))
    axes[0].legend(frameon=False, fontsize=5.3, ncol=2, loc="upper right")
    fig.tight_layout()
    return save(fig, "onset_dissipation", lang)


def pick_case(grid, pred1):
    te = pred1[pred1.split == "test"]
    fog = (grid["vis_m"] < 1000).astype(int)
    f = fog.reindex(te.index).fillna(0).to_numpy()
    starts = np.flatnonzero(np.diff(np.r_[0, f]) == 1)
    ends = np.flatnonzero(np.diff(np.r_[f, 0]) == -1)
    dur = ends - starts
    k = int(np.argsort(-dur)[min(2, len(dur) - 1)])     # a long, not the most extreme, event
    return te.index[starts[k]], te.index[ends[k]]


def fig_case(grid, lang):
    preds = {h: load_pred("fog", h) for h in HORIZONS}
    t_on, t_off = pick_case(grid, preds[HORIZONS[0]])
    t0, t1 = t_on - pd.Timedelta(hours=12), t_off + pd.Timedelta(hours=8)
    g = grid.loc[t0:t1]
    fig, ax = plt.subplots(figsize=(PAGE_W, 2.2))
    ax.semilogy(g.index, g["vis_m"].clip(lower=50), color="k", lw=1.3,
                label=T(lang, "Observed visibility", "Gözlenen görüş"))
    ax.semilogy(g.index, g["rvr_min_m"], ".", color=MODEL_COLORS["persistence"], ms=0)
    ax.scatter(g.index, g["rvr_min_m"], s=5, color="#e2762b", zorder=3, label="RVR")
    ax.axhline(1000, color="#c8323f", ls="--", lw=0.8)
    ax.set_ylim(50, 12000)
    ax.set_ylabel(T(lang, "Visibility / RVR (m)", "Görüş / RVR (m)"))
    ax2 = ax.twinx()
    ax2.spines["right"].set_visible(True)
    for h, c in zip(HORIZONS, ("#1f77b4", "#9467bd", "#2ca02c")):
        p = preds[h]["lgbm"]
        vt = p.index + pd.Timedelta(hours=h)
        sel = (vt >= t0) & (vt <= t1)
        ax2.plot(vt[sel], p[sel], color=c, lw=1.0,
                 label=T(lang, f"P(fog) issued {h} h before", f"{h} sa önceden P(sis)"))
    ax2.set_ylim(0, 1)
    ax2.set_ylabel(T(lang, "LightGBM probability", "LightGBM olasılığı"))
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=6, ncol=5, loc="upper center",
              bbox_to_anchor=(0.5, 1.2), frameon=False)
    ax.set_xlabel("UTC")
    fig.autofmt_xdate()
    path = save(fig, "case_study", lang)
    (TABLES / "case_study.txt").write_text(f"onset={t_on} end={t_off}\n")
    return path


def fig_rvr_confusion(lang):
    rv = pd.read_csv(TABLES / "rvr_multiclass.csv")
    fig, axes = plt.subplots(1, 3, figsize=(PAGE_W * 0.8, 2.1))
    names = [T(lang, "CAT I+", "CAT I+"), "CAT II", "CAT III"]
    for ax, h in zip(axes, HORIZONS):
        row = rv[(rv.h == h) & (rv.split == "test") & (rv.model == "lgbm")]
        cm = np.array(json.loads(row.confusion.iloc[0]))
        norm = cm / cm.sum(axis=1, keepdims=True)
        ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{cm[i, j]}\n({norm[i, j]:.2f})", ha="center", va="center",
                        fontsize=5.6, color="white" if norm[i, j] > 0.55 else "black")
        ax.set_xticks(range(3))
        ax.set_yticks(range(3))
        ax.set_xticklabels(names, fontsize=6)
        ax.set_yticklabels(names, fontsize=6)
        ax.set_xlabel(T(lang, "Forecast", "Tahmin"))
        ax.set_title(T(lang, f"{h} h (RPSS {row.RPSS.iloc[0]:.2f})", f"{h} sa (RPSS {row.RPSS.iloc[0]:.2f})"))
    axes[0].set_ylabel(T(lang, "Observed", "Gözlem"))
    fig.tight_layout()
    return save(fig, "rvr_confusion", lang)


def fig_architecture(lang):
    fig, ax = plt.subplots(figsize=(PAGE_W, 2.05))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 30)
    ax.axis("off")
    boxes = [
        (1, 16, 15, 11, T(lang, "Archives\nIEM METAR/SPECI\n2005–2026\nOgimet & AWC TAF",
                          "Arşivler\nIEM METAR/SPECI\n2005–2026\nOgimet ve AWC TAF"), "#dbe4ec"),
        (19, 16, 15, 11, T(lang, "Decoder + QC\nvisibility, RVR,\nweather, TREND",
                           "Çözücü + KK\ngörüş, RVR,\nhadise, TREND"), "#dbe4ec"),
        (37, 16, 15, 11, T(lang, "30-min grid\n77 features\n(state, trends,\nmemory, sun)",
                           "30 dk ızgara\n77 öznitelik\n(durum, eğilim,\nbellek, Güneş)"), "#dbe4ec"),
        (55, 16, 17, 11, T(lang, "Models (1/3/6 h)\nLR, RF, XGBoost,\nLightGBM, GRU, LSTM\n+ calibration",
                           "Modeller (1/3/6 sa)\nLR, RF, XGBoost,\nLightGBM, GRU, LSTM\n+ kalibrasyon"), "#f6e7a6"),
        (75, 16, 23, 11, T(lang, "Verification vs\npersistence, TREND, TAF\nPOD/FAR/CSI/HSS,\nBrier, PR-AUC, RPSS",
                           "Doğrulama:\nkalıcılık, TREND, TAF\nPOD/FAR/CSI/HSS,\nBrier, PR-AUC, RPSS"), "#dbe4ec"),
        (55, 1, 17, 11, T(lang, "SHAP explanations\n(TreeSHAP)", "SHAP açıklamaları\n(TreeSHAP)"), "#f6e7a6"),
        (19, 1, 33, 11, T(lang, "Web app: live METAR (AWC/IEM)\n→ same pipeline → probabilities,\nILS outlook, driving factors,\nSQLite log + automatic verification",
                          "Web uygulaması: canlı METAR (AWC/IEM)\n→ aynı işlem hattı → olasılıklar,\nILS görünümü, etkili faktörler,\nSQLite kaydı + otomatik doğrulama"), "#cfe8d6"),
    ]
    for x, y, w, h, text, col in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=0.8",
                                    fc=col, ec="#13233a", lw=0.7))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=6.3)
    arrows = [((16, 21.5), (19, 21.5)), ((34, 21.5), (37, 21.5)), ((52, 21.5), (55, 21.5)),
              ((72, 21.5), (75, 21.5)), ((63.5, 16), (63.5, 12)), ((55, 6.5), (52, 6.5)),
              ((44.5, 16), (44.5, 12))]
    for a, b in arrows:
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=7, lw=0.8, color="#13233a"))
    return save(fig, "architecture", lang)


def main() -> None:
    setup_style()
    grid = pd.read_parquet(PROCESSED / "grid.parquet")
    for lang in ("en", "tr"):
        for fn in (lambda: fig_climatology(grid, lang), lambda: fig_pr_curves(lang),
                   lambda: fig_reliability(lang), lambda: fig_leadtime(lang),
                   lambda: fig_onset(lang), lambda: fig_case(grid, lang),
                   lambda: fig_rvr_confusion(lang), lambda: fig_architecture(lang)):
            try:
                print("wrote", fn())
            except FileNotFoundError as exc:
                print("skipped (missing input):", exc)


if __name__ == "__main__":
    main()
