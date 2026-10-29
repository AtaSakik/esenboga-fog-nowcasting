"""Loading the processed matrices and producing chronological splits."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import PROCESSED, TEST_END, TRAIN_END, TRAIN_START, VALID_END
from .features import feature_matrix

TARGETS = {
    "fog": ("y_fog_{h}h", lambda s: s),            # visibility < 1000 m
    "rvr550": ("y_rvr_{h}h", lambda s: (s >= 1).astype(float).where(s.notna())),  # RVR < 550 m
    "rvr350": ("y_rvr_{h}h", lambda s: (s >= 2).astype(float).where(s.notna())),  # RVR < 350 m
}
TARGET_LABELS = {"fog": "VIS < 1000 m", "rvr550": "RVR < 550 m", "rvr350": "RVR < 350 m"}


def load_processed():
    feats = pd.read_parquet(PROCESSED / "features.parquet")
    targ = pd.read_parquet(PROCESSED / "targets.parquet")
    return feats, targ


def split_labels(index: pd.DatetimeIndex) -> pd.Series:
    t = index.tz_convert("UTC") if index.tz is not None else index.tz_localize("UTC")
    lab = np.select(
        [t < pd.Timestamp(TRAIN_START, tz="UTC"), t < pd.Timestamp(TRAIN_END, tz="UTC"),
         t < pd.Timestamp(VALID_END, tz="UTC"), t < pd.Timestamp(TEST_END, tz="UTC")],
        ["pre", "train", "val", "test"], default="live")
    return pd.Series(lab, index=index)


def fog_season(index: pd.DatetimeIndex) -> np.ndarray:
    """Season label = calendar year in which the July->June season starts."""
    return np.where(index.month >= 7, index.year, index.year - 1)


def climatology(index_train: pd.DatetimeIndex, y_train: np.ndarray,
                index_eval: pd.DatetimeIndex, h: int) -> np.ndarray:
    """Reference forecast: P(event | calendar month, UTC hour of the valid time) estimated on
    the training period (used for the Brier skill score)."""
    def key(ix):
        vt = ix + pd.Timedelta(hours=h)
        return vt.month * 100 + vt.hour
    rates = pd.Series(np.asarray(y_train, float)).groupby(key(index_train)).mean()
    return pd.Series(key(index_eval)).map(rates).fillna(float(np.mean(y_train))).to_numpy()


def task_frame(feats: pd.DataFrame, targ: pd.DataFrame, target: str, h: int):
    """Feature matrix, binary target and split for one (target, horizon) task."""
    col, fn = TARGETS[target]
    y = fn(targ[col.format(h=h)])
    X = feature_matrix(None, h, base=feats)
    ok = X["vis_m"].notna() & y.notna()
    X, y = X[ok], y[ok].astype(int)
    return X, y, split_labels(X.index)
