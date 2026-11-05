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
MODEL_COLORS = {"lr": "#7f7f7f", "knn": "#bcbd22", "rf": "#2ca02c", "xgb": "#9467bd",
                "lgbm": "#1f77b4", "cat": "#17becf", "ebm": "#8c564b", "mlp": "#e377c2",
                "gru": "#ff7f0e", "lstm": "#d62728", "tcn": "#f2a541", "transformer": "#a83279",
                "ens": "#13233a", "persistence": "#000000", "expert_rule": "#6b8e23",
                "trend": "#8c564b", "trend_prev": "#8c564b", "trend_worst": "#e377c2",
                "taf_prev": "#17becf", "taf_worst": "#bcbd22", "climatology": "#aaaaaa"}
MODEL_LABELS = {
    "en": {"lr": "Logistic regression", "knn": "Analog (k-NN)", "rf": "Random forest",
           "xgb": "XGBoost", "lgbm": "LightGBM", "cat": "CatBoost", "ebm": "EBM",
           "mlp": "MLP", "gru": "GRU", "lstm": "LSTM", "tcn": "TCN",
           "transformer": "Transformer", "ens": "Ensemble", "persistence": "Persistence",
           "expert_rule": "Forecaster's rule", "trend": "TREND",
           "trend_prev": "TREND (prevailing)", "trend_worst": "TREND (worst case)",
           "taf_prev": "TAF (prevailing)", "taf_worst": "TAF (worst case)",
           "climatology": "Climatology"},
    "tr": {"lr": "Lojistik regresyon", "knn": "Analog (k-NN)", "rf": "Rastgele orman",
           "xgb": "XGBoost", "lgbm": "LightGBM", "cat": "CatBoost", "ebm": "EBM",
           "mlp": "MLP", "gru": "GRU", "lstm": "LSTM", "tcn": "TCN",
           "transformer": "Transformer", "ens": "Topluluk", "persistence": "Kalıcılık",
           "expert_rule": "Tahminci kuralı", "trend": "TREND",
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
