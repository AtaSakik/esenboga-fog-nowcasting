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
# xgboost, catboost, interpret, torch and optuna are imported lazily: the operational nowcaster
# only needs LightGBM, which keeps the serverless (GitHub Actions) environment small.

MODEL_NAMES = {"lr": "Logistic Regression", "knn": "Analog (k-NN)", "rf": "Random Forest",
               "xgb": "XGBoost", "lgbm": "LightGBM", "cat": "CatBoost",
               "ebm": "Explainable Boosting", "mlp": "MLP", "gru": "GRU", "lstm": "LSTM",
               "tcn": "TCN", "transformer": "Transformer", "ens": "Ensemble"}


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
    train_seconds: float | None = None      # fit of the selected configuration (not the search)

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


def _cat_params(trial: optuna.Trial | None, fixed: dict | None = None) -> dict:
    if fixed is not None:
        return dict(fixed)
    return {
        "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.15, log=True),
        "depth": trial.suggest_int("depth", 4, 10),
        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 30.0, log=True),
        "random_strength": trial.suggest_float("random_strength", 0.0, 2.0),
        "bagging_temperature": trial.suggest_float("bagging_temperature", 0.0, 1.0),
    }


def fit_cat(Xtr, ytr, Xva, yva, params: dict, scale_pos_weight: float = 1.0):
    """CatBoost (Prokhorenkova et al. 2018) on the GPU; the model is cut back to the best
    validation iteration (use_best_model), so predict_proba needs no iteration argument."""
    from catboost import CatBoostClassifier

    m = CatBoostClassifier(iterations=4000, loss_function="Logloss", eval_metric="PRAUC",
                           task_type="GPU", od_type="Iter", od_wait=150, use_best_model=True,
                           random_seed=RANDOM_STATE, scale_pos_weight=scale_pos_weight,
                           verbose=False, **params)
    m.fit(Xtr, ytr, eval_set=(Xva, yva))
    return m, int(m.get_best_iteration()) + 1


def tune_boosting(kind: str, Xtr, ytr, Xva, yva, n_trials: int = 30, seed: int = RANDOM_STATE):
    """Optuna TPE search maximising validation average precision (PR-AUC)."""
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial):
        if kind == "lgbm":
            m, it = fit_lgbm(Xtr, ytr, Xva, yva, _lgbm_params(trial))
            p = m.predict_proba(Xva, num_iteration=it)[:, 1]
        elif kind == "cat":
            m, it = fit_cat(Xtr, ytr, Xva, yva, _cat_params(trial))
            p = m.predict_proba(Xva)[:, 1]
        else:
            m, it = fit_xgb(Xtr, ytr, Xva, yva, _xgb_params(trial))
            p = m.predict_proba(Xva, iteration_range=(0, it))[:, 1]
        trial.set_user_attr("best_iteration", it)
        return average_precision_score(yva, p)

    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return study


def make_ebm(**params):
    """Explainable Boosting Machine (Lou et al. 2013; Nori et al. 2019): a GAM whose shape
    functions (one per feature, plus the strongest pairwise interactions) are learnt by cyclic
    boosting, so every prediction is an exact sum of readable per-feature contributions."""
    from interpret.glassbox import ExplainableBoostingClassifier

    p = dict(interactions=10, outer_bags=4, max_bins=256, early_stopping_rounds=100,
             n_jobs=-1, random_state=RANDOM_STATE)
    p.update(params)
    return ExplainableBoostingClassifier(**p)


# ---------------------------------------------------------------------------- neural network
def _torch_device():
    import torch

    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class TabularMLP:
    """Feed-forward network on the tabular features (PyTorch), early-stopped on validation
    PR-AUC. Median imputation and standardisation use the training period only; the weights are
    kept as NumPy arrays so that the fitted object pickles and loads without a GPU."""

    def __init__(self, hidden: int = 256, layers: int = 3, dropout: float = 0.2,
                 lr: float = 1e-3, weight_decay: float = 1e-4, epochs: int = 40,
                 patience: int = 6, batch: int = 1024, seed: int = RANDOM_STATE):
        self.hidden, self.layers, self.dropout = hidden, layers, dropout
        self.lr, self.weight_decay, self.epochs = lr, weight_decay, epochs
        self.patience, self.batch, self.seed = patience, batch, seed

    def _net(self, n_in: int):
        from torch import nn

        blocks, d = [], n_in
        for _ in range(self.layers):
            blocks += [nn.Linear(d, self.hidden), nn.BatchNorm1d(self.hidden), nn.SiLU(),
                       nn.Dropout(self.dropout)]
            d = self.hidden
        return nn.Sequential(*blocks, nn.Linear(d, 1))

    def _prep(self, X: pd.DataFrame) -> np.ndarray:
        A = X.to_numpy(np.float32, copy=True)
        A = np.where(np.isnan(A), self.median_, A)
        return np.clip((A - self.mean_) / self.std_, -6, 6).astype(np.float32)

    def _logits(self, net, A: np.ndarray, device) -> np.ndarray:
        import torch

        net.eval()
        with torch.no_grad():
            return np.concatenate([
                net(torch.as_tensor(A[k:k + 8192], device=device)).squeeze(1).float().cpu().numpy()
                for k in range(0, len(A), 8192)])

    def fit(self, Xtr: pd.DataFrame, ytr, Xva: pd.DataFrame, yva) -> "TabularMLP":
        import torch

        torch.manual_seed(self.seed)
        rng = np.random.default_rng(self.seed)
        device = _torch_device()
        raw = Xtr.to_numpy(np.float32)
        self.median_ = np.nan_to_num(np.nanmedian(raw, axis=0))
        filled = np.where(np.isnan(raw), self.median_, raw)
        self.mean_, self.std_ = filled.mean(0), filled.std(0) + 1e-6
        A, B = self._prep(Xtr), self._prep(Xva)
        ytr, yva = np.asarray(ytr, np.float32), np.asarray(yva)
        net = self._net(A.shape[1]).to(device)
        opt = torch.optim.AdamW(net.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        pos = float(ytr.mean())
        bce = torch.nn.BCEWithLogitsLoss(
            pos_weight=torch.tensor(np.sqrt((1 - pos) / max(pos, 1e-4)), device=device))
        At, yt = torch.as_tensor(A, device=device), torch.as_tensor(ytr, device=device)
        best, best_state, bad = -1.0, None, 0
        for _ in range(self.epochs):
            net.train()
            perm = torch.as_tensor(rng.permutation(len(A)), device=device)
            for k in range(0, len(perm), self.batch):
                b = perm[k:k + self.batch]
                if len(b) < 2:          # BatchNorm needs at least two rows
                    continue
                loss = bce(net(At[b]).squeeze(1), yt[b])
                opt.zero_grad(set_to_none=True)
                loss.backward()
                opt.step()
            score = average_precision_score(yva, self._logits(net, B, device))
            if score > best + 1e-4:
                best, bad = score, 0
                best_state = {k: v.detach().cpu().numpy().copy() for k, v in net.state_dict().items()}
            else:
                bad += 1
                if bad >= self.patience:
                    break
        self.state_, self.best_score_ = best_state, best
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        import torch

        device = _torch_device()
        net = self._net(len(self.mean_))
        net.load_state_dict({k: torch.as_tensor(v) for k, v in self.state_.items()})
        p = 1 / (1 + np.exp(-self._logits(net.to(device), self._prep(X), device)))
        return np.column_stack([1 - p, p])


# ---------------------------------------------------------------------------- analogs
ANALOG_VARS = ["log_vis", "dpd_c", "rh_pct", "wind_speed_kt", "temp_c", "T_minus_max12h",
               "log_ceiling_ft", "fog_frac_6h", "dlogvis_1h", "ddpd_3h", "vt_solar_elev",
               "doy_sin", "doy_cos"]


class AnalogKNN:
    """Analog forecast (k nearest neighbours; cf. Hansen 2007): the event probability is the
    fraction of the k most similar situations of the training archive in which the event
    occurred h hours later. Similarity is the Euclidean distance between standardised values of
    a few physically meaningful predictors, so every forecast can be explained by its analogs."""

    def __init__(self, k: int = 50, variables: list[str] | None = None, chunk: int = 1024):
        self.k, self.variables, self.chunk = k, list(variables or ANALOG_VARS), chunk

    def _prep(self, X: pd.DataFrame) -> np.ndarray:
        A = X[self.variables].to_numpy(np.float32, copy=True)
        A = np.where(np.isnan(A), self.median_, A)
        return ((A - self.mean_) / self.std_).astype(np.float32)

    def fit(self, X: pd.DataFrame, y) -> "AnalogKNN":
        raw = X[self.variables].to_numpy(np.float32)
        self.median_ = np.nan_to_num(np.nanmedian(raw, axis=0))
        filled = np.where(np.isnan(raw), self.median_, raw)
        self.mean_, self.std_ = filled.mean(0), filled.std(0) + 1e-6
        self.archive_ = self._prep(X)
        self.labels_ = np.asarray(y, np.float32)
        return self

    def neighbours(self, X: pd.DataFrame, k: int) -> np.ndarray:
        """Archive positions of the k nearest analogs of every row of X, nearest first."""
        import torch

        device = _torch_device()
        arch = torch.as_tensor(self.archive_, device=device)
        Q = self._prep(X)
        out = []
        for s in range(0, len(Q), self.chunk):
            d = torch.cdist(torch.as_tensor(Q[s:s + self.chunk], device=device), arch)
            out.append(d.topk(k, dim=1, largest=False).indices.cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, k), int)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        p = self.labels_[self.neighbours(X, self.k)].mean(axis=1)
        return np.column_stack([1 - p, p])


def finalize(name: str, target: str, h: int, features: list[str], model, p_val: np.ndarray,
             y_val: np.ndarray, groups_val: np.ndarray, params: dict,
             best_iteration: int | None = None) -> FittedModel:
    """Choose & fit the calibrator and the CSI-optimal threshold on validation data."""
    cal, cal_scores = choose_calibrator(p_val, y_val, groups_val)
    thr = best_threshold(y_val, cal.transform(p_val), "CSI")
    return FittedModel(name, target, h, features, model, cal, thr, params, cal_scores,
                       best_iteration)
