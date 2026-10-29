"""Central configuration: paths, station metadata, thresholds and experiment design.

Every script imports from here so that the offline pipeline, the evaluation and the
web application share exactly the same definitions (no train/serve skew).
"""
from __future__ import annotations

from pathlib import Path

# ----------------------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW_METAR = DATA / "raw" / "metar"
RAW_TAF = DATA / "raw" / "taf"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
MODELS = ROOT / "models"
RESULTS = ROOT / "results"
FIGURES = RESULTS / "figures"
TABLES = RESULTS / "tables"
LOGS = ROOT / "logs"

for _p in (RAW_METAR, RAW_TAF, INTERIM, PROCESSED, MODELS, FIGURES, TABLES, LOGS):
    _p.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------- station
STATION = "LTAC"
STATION_NAME = "Ankara Esenboğa International Airport"
LAT = 40.1281          # deg N (aerodrome reference point)
LON = 32.9951          # deg E
ELEVATION_M = 953.0    # m AMSL (field elevation, Ogimet/WMO 17128)

# ----------------------------------------------------------------------------- targets
# Low-visibility event: prevailing horizontal visibility below 1000 m (ICAO fog threshold).
VIS_FOG_M = 1000.0
# ILS-category oriented RVR classes (ICAO Annex 6 / Doc 9365 minima used in the proposal):
#   class 0: RVR >= 550 m   (CAT I operations possible)
#   class 1: 350 <= RVR < 550 m (CAT II required)
#   class 2: RVR < 350 m    (CAT III required)
RVR_CAT_I_M = 550.0
RVR_CAT_II_M = 350.0
RVR_CLASS_NAMES = ["RVR>=550 m (CAT I+)", "350-550 m (CAT II)", "RVR<350 m (CAT III)"]

# Forecast lead times (hours). 1/3/6 h are the proposal's horizons; the full 1..6 h set is
# used for the skill-versus-lead-time curve.
HORIZONS = [1, 3, 6]
HORIZONS_ALL = [1, 2, 3, 4, 5, 6]

# Regular analysis grid: routine METARs at LTAC are issued at HH:20 and HH:50 UTC.
GRID_FREQ = "30min"
GRID_OFFSET = "20min"
MAX_OBS_AGE_MIN = 60   # an observation older than this is considered missing on the grid

# ----------------------------------------------------------------------------- splits
# Strictly chronological, season-aligned (a "fog season" runs July->June so that one
# winter is never split between two sets).
TRAIN_START = "2005-01-01"
TRAIN_END = "2019-07-01"      # exclusive
VALID_END = "2022-07-01"      # exclusive -> validation = 3 fog seasons (2019/20..2021/22)
TEST_END = "2026-07-01"       # exclusive -> test = 4 fog seasons (2022/23..2025/26)
# Everything after TEST_END is the "operational" period used for the live evaluation.

COLD_SEASON_MONTHS = [10, 11, 12, 1, 2, 3]

RANDOM_STATE = 42
