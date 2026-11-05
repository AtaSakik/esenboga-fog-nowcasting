"""Step 9 – greedy ensemble of the trained models (Caruana et al. 2004).

For every (target, horizon) the members are picked on the validation seasons by forward
selection on PR-AUC; the averaged probabilities are calibrated again and get their own
CSI-optimal threshold, both on validation, so the test seasons stay untouched.
Output: models/ens_<target>_<h>h.joblib (weights, calibrator, threshold), evaluated by
05_evaluate.py like every other model. Run after 02_train_tabular.py and 03_train_deep.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esenboga.benchmark import ML, load_task, select_ensemble, weighted_mean  # noqa: E402
from esenboga.config import HORIZONS, MODELS  # noqa: E402
from esenboga.data import fog_season  # noqa: E402
from esenboga.metrics import best_threshold  # noqa: E402
from esenboga.models import choose_calibrator  # noqa: E402


def main() -> None:
    for target in ("fog", "rvr550", "rvr350"):
        for h in HORIZONS:
            out = MODELS / f"ens_{target}_{h}h.joblib"
            out.unlink(missing_ok=True)                    # members only, never an old ensemble
            pred, thr = load_task(target, h)
            members = [m for m in ML if m in thr]
            val = (pred["split"] == "val").to_numpy() & pred[members].notna().all(axis=1).to_numpy()
            y = pred["y"].to_numpy()[val].astype(int)
            weights = select_ensemble({m: pred[m].to_numpy()[val] for m in members}, y)
            raw = weighted_mean(pred, weights)
            cal, _ = choose_calibrator(raw[val], y, fog_season(pred.index[val]))
            threshold = best_threshold(y, cal.transform(raw[val]), "CSI")
            joblib.dump({"weights": weights, "members": members, "calibrator": cal,
                         "threshold": threshold}, out)
            best_single = max(average_precision_score(y, pred[m].to_numpy()[val]) for m in members)
            print(f"{target} {h}h: weights={weights} val AP={average_precision_score(y, raw[val]):.4f} "
                  f"(best single {best_single:.4f}) cal={cal.method} thr={threshold:.2f}", flush=True)


if __name__ == "__main__":
    main()
