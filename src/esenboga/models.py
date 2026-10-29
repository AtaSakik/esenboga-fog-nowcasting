"""Tabular model zoo, hyper-parameter search, imbalance handling and probability calibration."""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import RANDOM_STATE
from .metrics import best_threshold, brier

warnings.filterwarnings("ignore", category=UserWarning)
# xgboost and optuna are imported lazily: the operational nowcaster only needs LightGBM, which
# keeps the serverless (GitHub Actions) environment small.

MODEL_NAMES = {"lr": "Logistic Regression", "rf": "Random Forest", "xgb": "XGBoost",
               "lgbm": "LightGBM", "gru": "GRU", "lstm": "LSTM"}


# ============================================================================ calibration
class Calibrator:
    """Wraps 'none' | 'sigmoid' (Platt 1999) | 'isotonic' (Zadrozny & Elkan 2002)."""

    def __init__(self, method: str = "isotonic"):
        self.method = method
        self.model = None

    def fit(self, p: np.ndarray, y: np.ndarray) -> "Calibrator":
        p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
        if self.method == "isotonic":
            self.model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(p, y)
        elif self.method == "sigmoid":
            z = np.log(p / (1 - p)).reshape(-1, 1)
            self.model = LogisticRegression(C=1e6, max_iter=1000).fit(z, y)
        return self

    def transform(self, p: np.ndarray) -> np.ndarray:
        p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
        if self.method == "isotonic":
            return self.model.predict(p)
        if self.method == "sigmoid":
            return self.model.predict_proba(np.log(p / (1 - p)).reshape(-1, 1))[:, 1]
        return p


def choose_calibrator(p: np.ndarray, y: np.ndarray, groups: np.ndarray) -> tuple[Calibrator, dict]:
    """Leave-one-season-out CV on the validation set to choose the calibration method,
    then refit the winner on the whole validation set."""
    scores = {}
    for method in ("none", "sigmoid", "isotonic"):
        errs, ns = [], []
        for g in np.unique(groups):
            tr, te = groups != g, groups == g
            if y[tr].sum() == 0:
                continue
            cal = Calibrator(method).fit(p[tr], y[tr])
            errs.append(brier(y[te], cal.transform(p[te])) * te.sum())
            ns.append(te.sum())
        scores[method] = float(np.sum(errs) / np.sum(ns))
    best = min(scores, key=scores.get)
    return Calibrator(best).fit(p, y), scores


# ============================================================================ models
def make_lr(C: float = 0.1, class_weight=None) -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(C=C, class_weight=class_weight, max_iter=3000)),
    ])


def make_rf(params: dict | None = None, class_weight=None) -> RandomForestClassifier:
    p = dict(n_estimators=400, max_depth=None, min_samples_leaf=20, max_features="sqrt",
             max_samples=0.5, n_jobs=-1, random_state=RANDOM_STATE, class_weight=class_weight)
    p.update(params or {})
    return RandomForestClassifier(**p)


@dataclass
class FittedModel:
    name: str
    target: str
    horizon: int
    features: list[str]
    model: object
    calibrator: Calibrator
    threshold: float
    params: dict = field(default_factory=dict)
    calib_scores: dict = field(default_factory=dict)
    best_iteration: int | None = None

    def predict_raw(self, X: pd.DataFrame) -> np.ndarray:
        X = X[self.features]
        if self.name == "lgbm":
            return self.model.predict_proba(X, num_iteration=self.best_iteration)[:, 1]
        if self.name == "xgb":
            return self.model.predict_proba(X, iteration_range=(0, self.best_iteration))[:, 1]
        return self.model.predict_proba(X)[:, 1]

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.calibrator.transform(self.predict_raw(X))


# ---------------------------------------------------------------------------- boosting
def _lgbm_params(trial: optuna.Trial | None, fixed: dict | None = None) -> dict:
    if fixed is not None:
        return dict(fixed)
    return {
        "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.1, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 15, 127, log=True),
        "min_child_samples": trial.suggest_int("min_child_samples", 20, 400, log=True),
        "feature_fraction": trial.suggest_float("feature_fraction", 0.4, 1.0),
        "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
        "bagging_freq": 1,
        "lambda_l2": trial.suggest_float("lambda_l2", 1e-3, 30.0, log=True),
        "min_split_gain": trial.suggest_float("min_split_gain", 0.0, 0.5),
    }


def fit_lgbm(Xtr, ytr, Xva, yva, params: dict, scale_pos_weight: float = 1.0):
    m = lgb.LGBMClassifier(n_estimators=4000, objective="binary", random_state=RANDOM_STATE,
                           n_jobs=-1, verbose=-1, scale_pos_weight=scale_pos_weight, **params)
    m.fit(Xtr, ytr, eval_X=(Xva,), eval_y=(yva,), eval_metric="average_precision",
          callbacks=[lgb.early_stopping(150, verbose=False)])
    return m, m.best_iteration_


def _xgb_params(trial: optuna.Trial | None, fixed: dict | None = None) -> dict:
    if fixed is not None:
        return dict(fixed)
    return {
        "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.1, log=True),
        "max_depth": trial.suggest_int("max_depth", 3, 9),
        "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 50.0, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-2, 30.0, log=True),
        "gamma": trial.suggest_float("gamma", 0.0, 2.0),
    }


def fit_xgb(Xtr, ytr, Xva, yva, params: dict, scale_pos_weight: float = 1.0, device="cuda"):
    import xgboost as xgb

    m = xgb.XGBClassifier(n_estimators=4000, objective="binary:logistic", tree_method="hist",
                          device=device, eval_metric="aucpr", early_stopping_rounds=150,
                          random_state=RANDOM_STATE, scale_pos_weight=scale_pos_weight,
                          n_jobs=-1, **params)
    m.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
    return m, int(m.best_iteration) + 1


def tune_boosting(kind: str, Xtr, ytr, Xva, yva, n_trials: int = 30, seed: int = RANDOM_STATE):
    """Optuna TPE search maximising validation average precision (PR-AUC)."""
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial):
        if kind == "lgbm":
            m, it = fit_lgbm(Xtr, ytr, Xva, yva, _lgbm_params(trial))
            p = m.predict_proba(Xva, num_iteration=it)[:, 1]
        else:
            m, it = fit_xgb(Xtr, ytr, Xva, yva, _xgb_params(trial))
            p = m.predict_proba(Xva, iteration_range=(0, it))[:, 1]
        trial.set_user_attr("best_iteration", it)
        return average_precision_score(yva, p)

    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return study


def finalize(name: str, target: str, h: int, features: list[str], model, p_val: np.ndarray,
             y_val: np.ndarray, groups_val: np.ndarray, params: dict,
             best_iteration: int | None = None) -> FittedModel:
    """Choose & fit the calibrator and the CSI-optimal threshold on validation data."""
    cal, cal_scores = choose_calibrator(p_val, y_val, groups_val)
    thr = best_threshold(y_val, cal.transform(p_val), "CSI")
    return FittedModel(name, target, h, features, model, cal, thr, params, cal_scores,
                       best_iteration)
