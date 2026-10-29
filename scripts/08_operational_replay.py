"""Step 8 – operational evaluation of the deployed nowcaster (web-app code path).

1. Batch replay over the operational period (after the test set, 2026-07-01 -> now) using the
   archived raw METAR text and the *inference* module of the web application.
2. Parity check: for random issue times the live code path (features rebuilt from only the
   preceding 120 h of reports, exactly as the app does) must reproduce the batch probabilities.
3. Real-time log: verified predictions recorded by the running app (mode='live').
Output: results/tables/operational.csv, results/tables/operational_parity.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from esenboga.config import INTERIM, TABLES, TEST_END, VIS_FOG_M  # noqa: E402
from esenboga.features import feature_matrix  # noqa: E402
from esenboga.inference import HISTORY_H, Nowcaster  # noqa: E402
from esenboga.metrics import brier, categorical_scores  # noqa: E402


def main() -> None:
    nc = Nowcaster()
    rep = pd.read_parquet(INTERIM / "reports_decoded.parquet", columns=["obs_time", "raw", "source",
                                                                         "report_type"])
    start = pd.Timestamp(TEST_END, tz="UTC")
    rep = rep[rep.obs_time >= start - pd.Timedelta(hours=HISTORY_H)].rename(
        columns={"report_type": "type_hint"}).reset_index(drop=True)
    grid, base, _ = nc.features_from_reports(rep[["obs_time", "raw", "source", "type_hint"]])
    present = grid["vis_m"].notna()
    times = base.index[(base.index >= start) & present.to_numpy()]
    rows, preds = [], {}
    for h in nc.fog_horizons:
        fm = nc.models[("fog", h)]
        X = feature_matrix(None, h, base=base.loc[times])
        p = fm.predict(X)
        preds[h] = pd.Series(p, index=times)
        vis_future = grid["vis_m"].shift(-2 * h).reindex(times)
        ok = vis_future.notna().to_numpy()
        y = (vis_future[ok] < VIS_FOG_M).astype(int).to_numpy()
        cs = categorical_scores(y, p[ok] >= fm.threshold)
        rows.append({"period": f"{times[0]:%m/%Y}–{times[-1]:%m/%Y} replay", "h": h, "n": int(ok.sum()),
                     "events": int(y.sum()), "warnings": int((p[ok] >= fm.threshold).sum()),
                     "POD": cs["POD"], "FAR": cs["FAR"], "CSI": cs["CSI"],
                     "Brier": brier(y, p[ok])})
    # ------------------------------------------------------------------ parity check
    rng = np.random.default_rng(7)
    sample = rng.choice(times[times >= times[0] + pd.Timedelta(hours=6)], size=40, replace=False)
    diffs = []
    for t in sample:
        window = rep[(rep.obs_time <= t) & (rep.obs_time > t - pd.Timedelta(hours=HISTORY_H))]
        g2, b2, _ = nc.features_from_reports(window[["obs_time", "raw", "source", "type_hint"]], at=t)
        out = nc.predict_at(b2, t, explain=False)
        for h in nc.fog_horizons:
            diffs.append(abs(out["fog"][h]["p"] - preds[h].loc[t]))
    parity = {"n_checks": len(diffs), "max_abs_diff": float(np.max(diffs)),
              "mean_abs_diff": float(np.mean(diffs))}
    (TABLES / "operational_parity.json").write_text(json.dumps(parity, indent=2))
    # ------------------------------------------------------------------ live log
    try:
        from live_log import LiveLog
        for r in LiveLog().summary():
            if r["mode"] == "live" and r["n"] > 0:
                rows.append({"period": f"{r['first'][:10]}–{r['last'][:10]} live", "h": r["horizon"],
                             "n": r["n"], "events": r["events"],
                             "warnings": r["hits"] + r["false_alarms"], "POD": r["POD"],
                             "FAR": r["FAR"], "CSI": r["CSI"], "Brier": r["Brier"]})
    except Exception as exc:  # the live log is optional
        print("live log unavailable:", exc)
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "operational.csv", index=False)
    print(out.round(3).to_string(index=False))
    print("parity:", parity)


if __name__ == "__main__":
    main()
