"""IEEE-style plotting helpers with English / Turkish labels.

Column width 3.5 in, page width 7.16 in, Times New Roman, 8-9 pt (IEEE graphics guide).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .config import FIGURES  # noqa: E402

COL_W, PAGE_W = 3.5, 7.16
MODEL_COLORS = {"lr": "#7f7f7f", "rf": "#2ca02c", "xgb": "#9467bd", "lgbm": "#1f77b4",
                "gru": "#ff7f0e", "lstm": "#d62728", "persistence": "#000000",
                "trend_prev": "#8c564b", "trend_worst": "#e377c2", "taf_prev": "#17becf",
                "taf_worst": "#bcbd22", "climatology": "#aaaaaa"}
MODEL_LABELS = {
    "en": {"lr": "Logistic regression", "rf": "Random forest", "xgb": "XGBoost",
           "lgbm": "LightGBM", "gru": "GRU", "lstm": "LSTM", "persistence": "Persistence",
           "trend_prev": "TREND (prevailing)", "trend_worst": "TREND (worst case)",
           "taf_prev": "TAF (prevailing)", "taf_worst": "TAF (worst case)",
           "climatology": "Climatology"},
    "tr": {"lr": "Lojistik regresyon", "rf": "Rastgele orman", "xgb": "XGBoost",
           "lgbm": "LightGBM", "gru": "GRU", "lstm": "LSTM", "persistence": "Kalıcılık",
           "trend_prev": "TREND (hâkim)", "trend_worst": "TREND (en kötü)",
           "taf_prev": "TAF (hâkim)", "taf_worst": "TAF (en kötü)",
           "climatology": "Klimatoloji"},
}


def setup_style() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "legend.fontsize": 7,
        "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.linewidth": 0.6,
        "lines.linewidth": 1.1, "grid.linewidth": 0.4, "grid.alpha": 0.35,
        "savefig.dpi": 400, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
        "axes.spines.top": False, "axes.spines.right": False,
    })


def T(lang: str, en: str, tr: str) -> str:
    return tr if lang == "tr" else en


def mlabel(name: str, lang: str) -> str:
    return MODEL_LABELS[lang].get(name, name)


def save(fig, name: str, lang: str) -> Path:
    out = FIGURES / lang
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.png"
    fig.savefig(path)
    plt.close(fig)
    return path
