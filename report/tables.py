"""Table specifications for the manuscript, generated directly from the result files.

Each builder returns {"title", "header": [[...]], "rows": [[...]], "widths", "notes",
"left_cols", "rules"}; cells may use the inline markup of build_paper (``**bold**``, ``$x$``).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from esenboga.config import HORIZONS, MODELS, PROCESSED, TABLES  # noqa: E402
from esenboga.labels import FEATURE_GROUPS  # noqa: E402

NAMES = {
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
ML = ["lr", "rf", "xgb", "lgbm", "gru", "lstm"]


def L(lang, en, tr):
    return tr if lang == "tr" else en


def f(x, d=3):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{x:.{d}f}"


def num(x):
    return f"{int(x):,}".replace(",", " ")


def _bold_best(rows, cols, higher_better):
    """Bold the best numeric value of each listed column among ML/baseline rows."""
    for c, hb in zip(cols, higher_better):
        vals = []
        for r in rows:
            try:
                vals.append(float(r[c]))
            except (ValueError, TypeError):
                vals.append(np.nan)
        arr = np.array(vals)
        if np.all(np.isnan(arr)):
            continue
        best = np.nanmax(arr) if hb else np.nanmin(arr)
        for r, v in zip(rows, arr):
            if not np.isnan(v) and np.isclose(v, best):
                r[c] = f"**{r[c]}**"
    return rows


# ============================================================================ builders
def data_summary(lang):
    qc = json.loads((TABLES / "qc_log.json").read_text())
    grid = pd.read_parquet(PROCESSED / "grid.parquet", columns=["vis_m", "rvr_min_m"])
    obs = grid["vis_m"].notna()
    fog = (grid["vis_m"] < 1000) & obs
    f_ = fog.astype(int).to_numpy()
    starts = np.flatnonzero(np.diff(np.r_[0, f_]) == 1)
    ends = np.flatnonzero(np.diff(np.r_[f_, 0]) == -1)
    dur = (ends - starts + 1) / 2
    low = (grid["vis_m"] < 1500) & obs
    rows = [
        [L(lang, "Period (UTC)", "Dönem (UTC)"), "01/2005 – 10/2026"],
        [L(lang, "METAR / SPECI reports (after QC)", "METAR / SPECI rasatı (KK sonrası)"),
         f"{num(qc['by_type']['METAR'])} / {num(qc['by_type']['SPECI'])}"],
        [L(lang, "Sources: IEM / Ogimet (gap filling)", "Kaynak: IEM / Ogimet (boşluk dolgu)"),
         f"{num(qc['by_source']['IEM'])} / {num(qc['by_source']['OGIMET'])}"],
        [L(lang, "Reports removed or corrected by QC", "KK ile çıkarılan/düzeltilen rasat"),
         num(qc["reports_in"] - qc["reports_out"]) + " / " + num(sum(v for k, v in qc.items()
                                                                       if k.startswith(("range_", "spike_"))))],
        [L(lang, "30-min analysis slots (with observation)", "30 dk analiz dilimi (gözlemli)"),
         f"{num(len(grid))} ({100 * obs.mean():.1f}%)"],
        [L(lang, "Slots with VIS < 1000 m (rate)", "Görüş < 1000 m dilimleri (oran)"),
         f"{num(fog.sum())} ({100 * fog.sum() / obs.sum():.2f}%)"],
        [L(lang, "Fog episodes; median / P90 duration", "Sis olayı; medyan / P90 süre"),
         f"{len(dur)}; {np.median(dur):.1f} h / {np.percentile(dur, 90):.1f} h"
         if lang == "en" else f"{len(dur)}; {np.median(dur):.1f} sa / {np.percentile(dur, 90):.1f} sa"],
        [L(lang, "RVR reported when VIS < 1500 m", "Görüş < 1500 m iken RVR raporu"),
         f"{100 * grid['rvr_min_m'][low].notna().mean():.1f}%"],
        [L(lang, "Fog slots with RVR ≤ 350 m", "RVR ≤ 350 m olan sis dilimleri"),
         f"{100 * (grid['rvr_min_m'][fog].fillna(grid['vis_m'][fog]) <= 350).mean():.1f}%"],
    ]
    return {"title": L(lang, "Characteristics of the LTAC data set", "LTAC veri setinin özellikleri"),
            "header": [[L(lang, "Quantity", "Büyüklük"), L(lang, "Value", "Değer")]],
            "rows": rows, "widths": [2.3, 1.6], "left_cols": 1}


def splits(lang):
    targ = pd.read_parquet(PROCESSED / "targets.parquet", columns=["y_fog_0h"])
    from esenboga.data import split_labels
    s = split_labels(targ.index)
    rows = []
    names = {"train": L(lang, "Training", "Eğitim"), "val": L(lang, "Validation", "Doğrulama"),
             "test": L(lang, "Test", "Test"), "live": L(lang, "Operational", "Operasyonel")}
    periods = {"train": "01/2005–06/2019", "val": "07/2019–06/2022",
               "test": "07/2022–06/2026", "live": "07/2026–10/2026"}
    for k in ("train", "val", "test", "live"):
        y = targ["y_fog_0h"][s == k]
        rows.append([names[k], periods[k], num(y.notna().sum()), num(y.sum()),
                     f"{100 * y.mean():.2f}%"])
    return {"title": L(lang, "Chronological data partition", "Kronolojik veri bölümlemesi"),
            "header": [[L(lang, "Set", "Küme"), L(lang, "Period", "Dönem"),
                        L(lang, "Slots", "Dilim"), L(lang, "Fog", "Sis"), L(lang, "Rate", "Oran")]],
            "rows": rows, "widths": [1.0, 1.35, 0.8, 0.6, 0.6], "left_cols": 2}


def features(lang):
    rows = []
    desc = {
        "Current state / Anlık durum": L(lang, "VIS, RVR, T, Td, T−Td, RH, wind (u, v, calm, gust), QNH, ceiling, cloud base and cover, VV",
                                        "Görüş, RVR, T, Td, T−Td, BN, rüzgâr (u, v, sakin, hamle), QNH, tavan, bulut tabanı ve kapalılığı, VV"),
        "Present weather / Hadise": L(lang, "FG, MIFG/BCFG/PRFG, VCFG, FZFG, BR, HZ, DZ, RA, SN, recent precipitation",
                                      "FG, MIFG/BCFG/PRFG, VCFG, FZFG, BR, HZ, DZ, RA, SN, yakın zamanda yağış"),
        "Tendencies / Eğilimler": L(lang, "1/3/6-h changes of T, Td, T−Td, log VIS; RH, wind, QNH (3/12 h), ceiling",
                                    "T, Td, T−Td, log görüşün 1/3/6 sa değişimi; BN, rüzgâr, QNH (3/12 sa), tavan"),
        "Memory / Bellek": L(lang, "cooling since 12-h max, min T−Td, max RH, fog/mist/precip./snow fractions, hours since fog, SPECI age",
                             "12 sa maks.'tan soğuma, min T−Td, maks. BN, sis/pus/yağış/kar oranları, son sisten beri süre, SPECI yaşı"),
        "Calendar & sun / Takvim ve Güneş": L(lang, "hour and day of year (sin/cos), solar elevation, night, time to sunrise / since sunset, and at valid time",
                                              "günün saati ve yılın günü (sin/cos), Güneş yüksekliği, gece, gün doğumuna kalan / batımından beri süre; geçerlilik anında"),
    }
    for g, cols in FEATURE_GROUPS.items():
        name = g.split(" / ")[1] if lang == "tr" else g.split(" / ")[0]
        rows.append([name, str(len(cols)), desc[g]])
    return {"title": L(lang, "Predictor groups (77 features)", "Öznitelik grupları (77 öznitelik)"),
            "header": [[L(lang, "Group", "Grup"), "n", L(lang, "Content", "İçerik")]],
            "rows": rows, "widths": [0.9, 0.25, 2.6], "left_cols": 3}


def main_results(lang, target="fog", split="test", season="all"):
    sc = pd.read_csv(TABLES / "scores_all.csv")
    sc = sc[(sc.target == target) & (sc.split == split) & (sc.season == season)]
    rows, rules = [], []
    cols = ["PR_AUC", "ROC_AUC", "Brier", "BSS", "POD", "FAR", "CSI", "HSS"]
    for h in HORIZONS:
        block = []
        d = sc[sc.h == h]
        for m in ML + ["persistence", "trend_prev", "trend_worst"]:
            r = d[d.model == m]
            if not len(r):
                continue
            r = r.iloc[0]
            is_ml = m in ML
            block.append({"h": f"{h} h" if lang == "en" else f"{h} sa", "m": NAMES[lang][m],
                          "PR_AUC": f(r.PR_AUC) if is_ml else "–",
                          "ROC_AUC": f(r.ROC_AUC) if is_ml else "–",
                          "Brier": f(r.Brier, 4), "BSS": f(r.BSS),
                          "POD": f(r.POD), "FAR": f(r.FAR), "CSI": f(r.CSI), "HSS": f(r.HSS)})
        block = _bold_best(block, cols, [True, True, False, True, True, False, True, True])
        for k, b in enumerate(block):
            rows.append([b["h"] if k == 0 else "", b["m"]] + [b[c] for c in cols])
        rules.append(len(rows))   # header row index offset handled in builder
    rules = [r for r in rules[:-1]]
    return {"title": L(lang, "Verification of the fog (VIS < 1000 m) forecasts on the test seasons 2022/23–2025/26",
                       "Sis (görüş < 1000 m) tahminlerinin 2022/23–2025/26 test sezonlarında doğrulanması"),
            "header": [[L(lang, "Lead", "Süre"), L(lang, "Forecast", "Tahmin"), "PR-AUC", "ROC-AUC",
                        "BS", "BSS", "POD", "FAR", "CSI", "HSS"]],
            "rows": rows, "widths": [0.45, 1.45, 0.62, 0.62, 0.62, 0.58, 0.55, 0.55, 0.55, 0.55],
            "left_cols": 2, "rules": rules,
            "notes": L(lang, "BS: Brier score; BSS relative to the month–hour climatology of the training period. "
                             "Categorical scores use the validation-optimal (maximum-CSI) threshold. Best value per lead time in bold. "
                             "TREND is only defined up to 2 h.",
                       "BS: Brier skoru; BSS, eğitim döneminin ay–saat klimatolojisine göredir. Kategorik skorlar doğrulama "
                       "kümesinde CSI'yı en büyükleyen eşikle hesaplanmıştır. Her öngörü süresindeki en iyi değer kalın yazılmıştır. "
                       "TREND yalnızca 2 saate kadar tanımlıdır.")}


def bootstrap_ci(lang):
    bs = pd.read_csv(TABLES / "bootstrap_test.csv")
    pt = pd.read_csv(TABLES / "paired_tests.csv")
    sc = pd.read_csv(TABLES / "scores_all.csv")
    rows = []
    for h in HORIZONS:
        shown = False
        for m in ("lgbm", "gru", "persistence"):
            b = bs[(bs.target == "fog") & (bs.h == h) & (bs.model == m)]
            s = sc[(sc.target == "fog") & (sc.h == h) & (sc.model == m) & (sc.split == "test") & (sc.season == "all")]
            if not len(b) or not len(s):
                continue
            b, s = b.iloc[0], s.iloc[0]
            sig = ""
            if m != "persistence":
                p = pt[(pt.target == "fog") & (pt.h == h) & (pt.model == m) & (pt.vs == "persistence") & (pt.metric == "CSI")]
                if len(p) and bool(p.significant.iloc[0]):
                    sig = "*" if p.diff_mean.iloc[0] > 0 else "−"
            rows.append([("" if shown else (f"{h} h" if lang == "en" else f"{h} sa")), NAMES[lang][m],
                         f"{f(s.CSI, 2)}{sig} [{f(b.CSI_lo, 2)}, {f(b.CSI_hi, 2)}]",
                         f"{f(s.HSS, 2)} [{f(b.HSS_lo, 2)}, {f(b.HSS_hi, 2)}]",
                         (f"{f(s.PR_AUC, 2)} [{f(b.PR_AUC_lo, 2)}, {f(b.PR_AUC_hi, 2)}]" if m != "persistence" else "–")])
            shown = True
    return {"title": L(lang, "95% day-block bootstrap confidence intervals (test seasons)",
                       "%95 gün-blok bootstrap güven aralıkları (test sezonları)"),
            "header": [[L(lang, "Lead", "Süre"), L(lang, "Forecast", "Tahmin"), "CSI", "HSS", "PR-AUC"]],
            "rows": rows, "widths": [0.34, 0.8, 0.82, 0.75, 0.75], "left_cols": 2,
            "notes": L(lang, "* CSI significantly higher than persistence (paired bootstrap, 2000 resamples of days).",
                       "* CSI kalıcılıktan anlamlı olarak yüksek (eşleştirilmiş bootstrap, günlerin 2000 yeniden örneklemesi).")}


def trend_table(lang):
    tr = pd.read_csv(TABLES / "trend_comparison.csv")
    tr = tr[(tr.split == "test")]
    rows = []
    for h in sorted(tr.h.unique()):
        block = []
        for m in ("lgbm", "gru", "persistence", "trend_prev", "trend_worst"):
            r = tr[(tr.h == h) & (tr.forecast == m)]
            if not len(r):
                continue
            r = r.iloc[0]
            block.append({"h": f"{h} h" if lang == "en" else f"{h} sa", "m": NAMES[lang][m],
                          "POD": f(r.POD), "FAR": f(r.FAR), "CSI": f(r.CSI), "HSS": f(r.HSS)})
        block = _bold_best(block, ["POD", "FAR", "CSI", "HSS"], [True, False, True, True])
        for k, b in enumerate(block):
            rows.append([b["h"] if k == 0 else "", b["m"], b["POD"], b["FAR"], b["CSI"], b["HSS"]])
    n = int(tr.n.iloc[0]) if len(tr) else 0
    ev = int(tr.events.iloc[0]) if len(tr) else 0
    return {"title": L(lang, "ML versus the METAR TREND forecast on identical test cases",
                       "Aynı test örneklerinde ML ile METAR TREND tahmininin karşılaştırılması"),
            "header": [[L(lang, "Lead", "Süre"), L(lang, "Forecast", "Tahmin"), "POD", "FAR", "CSI", "HSS"]],
            "rows": rows, "widths": [0.4, 1.3, 0.55, 0.55, 0.55, 0.55], "left_cols": 2,
            "notes": L(lang, f"{num(n)} forecasts with a decodable TREND ({num(ev)} fog cases at 1 h).",
                       f"Çözümlenebilir TREND içeren {num(n)} tahmin (1 sa için {num(ev)} sis durumu).")}


def taf_table(lang):
    p = TABLES / "taf_comparison.csv"
    tf = pd.read_csv(p) if p.exists() and p.stat().st_size > 5 else pd.DataFrame()
    rows = []
    if len(tf):
        for h in sorted(tf.h.unique()):
            d = tf[tf.h == h]
            part = "test" if (d.split == "test").any() else "live"
            d = d[d.split == part]
            block = []
            for m in ("lgbm", "gru", "persistence", "taf_prev", "taf_worst"):
                r = d[d.forecast == m]
                if len(r):
                    r = r.iloc[0]
                    block.append({"h": f"{h} h" if lang == "en" else f"{h} sa", "m": NAMES[lang][m],
                                  "n": num(r.n), "e": num(r.events), "POD": f(r.POD), "FAR": f(r.FAR),
                                  "CSI": f(r.CSI)})
            block = _bold_best(block, ["POD", "FAR", "CSI"], [True, False, True])
            for k, b in enumerate(block):
                rows.append([b["h"] if k == 0 else "", b["m"], b["n"], b["e"], b["POD"], b["FAR"], b["CSI"]])
    return {"title": L(lang, "ML versus the official TAF (forecasts issued before t)",
                       "ML ile resmî TAF'ın karşılaştırılması (t anından önce yayımlanan tahminler)"),
            "header": [[L(lang, "Lead", "Süre"), L(lang, "Forecast", "Tahmin"), "n", L(lang, "Fog", "Sis"),
                        "POD", "FAR", "CSI"]],
            "rows": rows or [["–", L(lang, "no TAF data", "TAF verisi yok"), "", "", "", "", ""]],
            "widths": [0.4, 1.2, 0.5, 0.4, 0.5, 0.5, 0.5], "left_cols": 2}


SHORT = {"en": {"lr": "LR", "rf": "RF", "xgb": "XGBoost", "lgbm": "LightGBM", "gru": "GRU",
                "lstm": "LSTM", "persistence": "Persistence"},
         "tr": {"lr": "LR", "rf": "RO", "xgb": "XGBoost", "lgbm": "LightGBM", "gru": "GRU",
                "lstm": "LSTM", "persistence": "Kalıcılık"}}


def rvr_table(lang):
    rv = pd.read_csv(TABLES / "rvr_multiclass.csv")
    rv = rv[rv.split == "test"]
    rows, cols = [], ["RPSS", "macro_F1", "HSS_multi", "CSI_ge1", "CSI_ge2"]
    for h in HORIZONS:
        block = []
        for m in ("lr", "rf", "xgb", "lgbm", "gru", "lstm", "persistence"):
            r = rv[(rv.h == h) & (rv.model == m)]
            if not len(r):
                continue
            r = r.iloc[0]
            block.append({"h": f"{h} h" if lang == "en" else f"{h} sa", "m": SHORT[lang][m],
                          **{c: f(r[c]) for c in cols}})
        block = _bold_best(block, cols, [True, True, True, True, True])
        for k, b in enumerate(block):
            rows.append([b["h"] if k == 0 else "", b["m"]] + [b[c] for c in cols])
    return {"title": L(lang, "ILS-category (RVR) forecasts on the test seasons",
                       "Test sezonlarında ILS kategorisi (RVR) tahminleri"),
            "header": [[L(lang, "Lead", "Süre"), L(lang, "Forecast", "Tahmin"), "RPSS",
                        "Macro-F1", "HSS$_{3}$", "CSI$_{≥II}$", "CSI$_{III}$"]],
            "rows": rows, "widths": [0.34, 0.74, 0.47, 0.52, 0.45, 0.48, 0.45], "left_cols": 2,
            "notes": L(lang, "RPSS relative to the month–hour class climatology; HSS$_{3}$: three-category Heidke score. "
                             "CSI$_{≥II}$: RVR < 550 m (CAT II or worse); CSI$_{III}$: RVR < 350 m. "
                             "LR: logistic regression; RF: random forest.",
                       "RPSS, ay–saat sınıf klimatolojisine görelidir; HSS$_{3}$: üç kategorili Heidke skoru. "
                       "CSI$_{≥II}$: RVR < 550 m (CAT II veya daha kötü); CSI$_{III}$: RVR < 350 m. "
                       "LR: lojistik regresyon; RO: rastgele orman.")}


def imbalance(lang):
    d = pd.read_csv(TABLES / "imbalance_ablation.csv")
    strat = {"none": L(lang, "none", "yok"), "weighting": L(lang, "class weights", "sınıf ağırlığı"),
             "smote": "SMOTE", "undersampling": L(lang, "undersampling", "alt örnekleme")}
    rows = []
    for model in ("lr", "lgbm"):
        for s in ("none", "weighting", "smote", "undersampling"):
            raw_v = d[(d.model == model) & (d.strategy == s) & (~d.calibrated) & (d.split == "val")].iloc[0]
            cal_v = d[(d.model == model) & (d.strategy == s) & (d.calibrated) & (d.split == "val")].iloc[0]
            cal_t = d[(d.model == model) & (d.strategy == s) & (d.calibrated) & (d.split == "test")].iloc[0]
            rows.append([NAMES[lang][model] if s == "none" else "", strat[s], f(raw_v.PR_AUC),
                         f(raw_v.Brier, 4), f(cal_v.Brier, 4), f(cal_t.PR_AUC), f(cal_t.CSI)])
    return {"title": L(lang, "Class-imbalance strategies (fog, 3 h)", "Sınıf dengesizliği stratejileri (sis, 3 sa)"),
            "header": [[L(lang, "Model", "Model"), L(lang, "Strategy", "Strateji"), "PR-AUC$_{v}$",
                        "BS$_{v}$ raw" if lang == "en" else "BS$_{v}$ ham", "BS$_{v}$ cal." if lang == "en" else "BS$_{v}$ kal.",
                        "PR-AUC$_{t}$", "CSI$_{t}$"]],
            "rows": rows, "widths": [0.8, 0.9, 0.6, 0.6, 0.6, 0.6, 0.5], "left_cols": 2, "rules": [4],
            "notes": L(lang, "v: validation, t: test. Calibration (none/Platt/isotonic) selected by leave-one-season-out CV.",
                       "v: doğrulama, t: test. Kalibrasyon (yok/Platt/izotonik) bir-sezon-dışarıda çapraz doğrulamayla seçilmiştir.")}


def per_season(lang):
    d = pd.read_csv(TABLES / "per_season.csv")
    d = d[(d.target == "fog") & (d.h == 3)]
    rows = [[r.season, num(r.events), f(r.lgbm_CSI), f(r.gru_CSI) if "gru_CSI" in d else "–",
             f(r.persistence_CSI), f(r.lgbm_PRAUC)] for r in d.itertuples()]
    return {"title": L(lang, "Season-by-season skill at 3 h (test)", "3 sa için sezon bazında beceri (test)"),
            "header": [[L(lang, "Season", "Sezon"), L(lang, "Fog slots", "Sis dilimi"), "CSI LightGBM",
                        "CSI GRU", L(lang, "CSI persist.", "CSI kalıcılık"), "PR-AUC LightGBM"]],
            "rows": rows, "widths": [0.65, 0.6, 0.7, 0.6, 0.7, 0.8], "left_cols": 1}


def hyperparams(lang):
    tuned = json.loads((MODELS / "tuned_params.json").read_text())
    rows = []
    for key in sorted(tuned):
        model, h = key.split("_")
        p = tuned[key]
        if model == "lgbm":
            s = (f"η={p['learning_rate']:.3f}, leaves={p['num_leaves']}, min_child={p['min_child_samples']}, "
                 f"ff={p['feature_fraction']:.2f}, bf={p['bagging_fraction']:.2f}, λ₂={p['lambda_l2']:.3g}")
        else:
            s = (f"η={p['learning_rate']:.3f}, depth={p['max_depth']}, mcw={p['min_child_weight']:.1f}, "
                 f"subsample={p['subsample']:.2f}, colsample={p['colsample_bytree']:.2f}, λ={p['reg_lambda']:.3g}")
        rows.append([NAMES[lang][model], h.replace("h", " h" if lang == "en" else " sa"), s])
    import joblib  # bundles are produced by our own training script
    for cell in ("gru", "lstm"):
        pth = MODELS / f"deep_{cell}.joblib"
        if pth.exists():
            c = joblib.load(pth)["config"]
            rows.append([NAMES[lang][cell], "1/3/6", f"hidden={c['hidden']}, layers=2, dropout={c['dropout']}, "
                                                     f"lr={c['lr']:g}, wd={c['weight_decay']:g}, seq=24×30 min"])
    return {"title": L(lang, "Selected hyper-parameters", "Seçilen hiperparametreler"),
            "header": [[L(lang, "Model", "Model"), L(lang, "Lead", "Süre"), L(lang, "Setting", "Ayar")]],
            "rows": rows, "widths": [0.7, 0.45, 2.8], "left_cols": 3}


def live(lang):
    p = TABLES / "operational.csv"
    rows = []
    if p.exists():
        d = pd.read_csv(p)
        for r in d.itertuples():
            period = r.period.replace("replay", L(lang, "replay", "yeniden oynatma")).replace(
                "live", L(lang, "live", "canlı"))
            rows.append([period, f"{r.h} h" if lang == "en" else f"{r.h} sa", num(r.n), num(r.events),
                         num(r.warnings), f(r.POD), f(r.FAR), f(r.Brier, 4)])
    return {"title": L(lang, "Operational verification after the test period",
                       "Test dönemi sonrası operasyonel doğrulama"),
            "header": [[L(lang, "Period", "Dönem"), L(lang, "Lead", "Süre"), "n", L(lang, "Fog", "Sis"),
                        L(lang, "Warnings", "Uyarı"), "POD", "FAR", "BS"]],
            "rows": rows or [["–"] * 8], "widths": [1.25, 0.4, 0.5, 0.35, 0.5, 0.4, 0.4, 0.5],
            "left_cols": 1,
            "notes": L(lang, "Replay: archived METARs processed with the web-application code; live: forecasts logged "
                             "by the running application and verified automatically.",
                       "Yeniden oynatma: arşiv METAR'ları web uygulamasının koduyla işlenmiştir; canlı: çalışan uygulamanın "
                       "kaydettiği ve otomatik doğruladığı tahminler.")}


BUILDERS = {"data_summary": data_summary, "splits": splits, "features": features,
            "main_results": main_results, "bootstrap_ci": bootstrap_ci, "trend": trend_table,
            "taf": taf_table, "rvr": rvr_table, "imbalance": imbalance, "per_season": per_season,
            "hyperparams": hyperparams, "live": live}


def build(key: str, lang: str) -> dict:
    return BUILDERS[key](lang)
