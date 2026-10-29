# Reproduce the whole study end to end (Windows PowerShell).
# Usage:  .\run_all.ps1            (assumes the virtual environment below exists)
$ErrorActionPreference = "Stop"
$py = "$env:USERPROFILE\.venvs\esenboga\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

& $py src/esenboga/download.py iem --start 2005 --end 2026          # METAR/SPECI archive (IEM)
& $py src/esenboga/download.py ogimet-metar --start 2005-01 --end 2012-12   # gap filling
& $py src/esenboga/download.py awc-taf                                # last 30 days of TAFs
& $py scripts/01_prepare_data.py          # decode, QC, grid, features, targets
& $py -m pytest tests -q                  # parser, TAF, solar geometry, leakage tests
& $py scripts/04_imbalance_ablation.py    # class-imbalance strategies (fog, 3 h)
& $py scripts/02_train_tabular.py         # LR, RF, XGBoost, LightGBM (1/3/6 h, 3 targets)
& $py scripts/02_train_tabular.py --horizons 2 4 5 --targets fog --models lgbm --trials 15
& $py scripts/03_train_deep.py            # multi-task GRU / LSTM
& $py scripts/05_evaluate.py              # verification, bootstrap, TREND/TAF comparison
& $py scripts/06_shap.py                  # explainability
& $py scripts/07_figures.py               # figures (EN/TR)
& $py scripts/08_operational_replay.py    # operational period + parity check
& $py report/build_paper.py               # IEEE manuscript (EN/TR, DOCX + PDF)
