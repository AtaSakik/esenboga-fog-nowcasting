"""Step 1 – merge archives, decode, quality-control, grid, features and targets.

Outputs
  data/interim/reports_decoded.parquet   one row per METAR/SPECI (QC applied)
  data/processed/grid.parquet            30-min grid state (HH:20/HH:50 UTC)
  data/processed/features.parquet        feature matrix (base features, all grid times)
  data/processed/targets.parquet         targets for lead times 1..6 h
  results/tables/qc_log.json             quality-control statistics
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from esenboga.config import HORIZONS_ALL, INTERIM, PROCESSED, TABLES, TRAIN_START  # noqa: E402
from esenboga.dataset import decode, merge_sources, quality_control  # noqa: E402
from esenboga.features import build_grid, make_features, make_targets  # noqa: E402


def main() -> None:
    t0 = time.time()
    start_year = int(TRAIN_START[:4])
    rep = merge_sources(start_year)
    print(f"merged reports: {len(rep):,} ({rep['source'].value_counts().to_dict()})", flush=True)
    dec = decode(rep)
    print(f"decoded in {time.time() - t0:.0f}s", flush=True)
    clean, qc_log = quality_control(dec)
    qc_log["by_source"] = clean["source"].value_counts().to_dict()
    qc_log["by_type"] = clean["report_type"].value_counts().to_dict()
    clean.to_parquet(INTERIM / "reports_decoded.parquet", index=False)

    grid = build_grid(clean, start=TRAIN_START)
    qc_log["grid_slots"] = len(grid)
    qc_log["grid_slots_with_obs"] = int(grid["vis_m"].notna().sum())
    grid.to_parquet(PROCESSED / "grid.parquet")
    feats = make_features(grid)
    feats.to_parquet(PROCESSED / "features.parquet")
    targ = make_targets(grid, HORIZONS_ALL)
    targ.to_parquet(PROCESSED / "targets.parquet")
    (TABLES / "qc_log.json").write_text(json.dumps(qc_log, indent=2, default=str))
    print(json.dumps(qc_log, indent=2, default=str))
    print(f"features {feats.shape}, targets {targ.shape}; done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
