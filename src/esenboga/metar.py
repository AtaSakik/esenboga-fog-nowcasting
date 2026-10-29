"""METAR / SPECI decoder (WMO FM 15 / ICAO Annex 3) tailored to the needs of the study.

The decoder is deliberately self-contained (regular expressions only) so the identical code
path is used for the 20-year archive and for the live web application.

Decoded quantities
------------------
wind (dir/speed/gust/variability), prevailing and minimum visibility, CAVOK, runway visual
range for every runway, present weather, cloud layers and vertical visibility, temperature,
dew point, QNH, recent weather, and the 2-hour TREND forecast (NOSIG / BECMG / TEMPO with
FM/TL/AT time indicators). Everything after ``RMK`` is ignored.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------- regexes
RE_TIME = re.compile(r"^(\d{2})(\d{2})(\d{2})Z$")
RE_WIND = re.compile(r"^(VRB|\d{3}|///)(\d{2,3}|//)(?:G(\d{2,3}))?(KT|MPS|KMH)$")
RE_WIND_VAR = re.compile(r"^(\d{3})V(\d{3})$")
RE_VIS = re.compile(r"^(\d{4})(NDV)?$")
RE_VIS_DIR = re.compile(r"^(\d{4})(N|NE|E|SE|S|SW|W|NW)$")
RE_VIS_SM = re.compile(r"^(M|P)?(\d+)?(?:(\d)/(\d{1,2}))?SM$")
RE_RVR = re.compile(r"^R(\d{2}[LCR]?)/([PM])?(\d{4})(?:V([PM])?(\d{4}))?(FT)?/?([UDN])?$")
RE_WX = re.compile(
    r"^(\+|-|VC)?(MI|PR|BC|DR|BL|SH|TS|FZ)?"
    r"((?:DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)+)?$")
RE_CLOUD = re.compile(r"^(FEW|SCT|BKN|OVC)(\d{3}|///)(CB|TCU|///)?$")
RE_VV = re.compile(r"^VV(\d{3}|///)$")
RE_TEMP = re.compile(r"^(M?\d{2}|//)/(M?\d{2}|//)?$")
RE_QNH = re.compile(r"^([QA])(\d{4}|////)$")
RE_RECENT = re.compile(r"^RE([A-Z]{2,8})$")
RE_TREND_TIME = re.compile(r"^(FM|TL|AT)(\d{4})$")
# Runway-state groups (EUR/NAT winter contamination reports), e.g. R03R2///95, 532///95,
# R21L220294, 034/0195, R03L/CLRD70 – recognised only so that they are not counted as errors.
RE_RWY_STATE = re.compile(r"^(?:R\d{2}[LCR]?/?|\d{2})[\d/]{6}$|^R\d{2}[LCR]?/CLRD\d{2}$")
# Frequent keying errors in the archive ("NO SIG", "N OSIG", "Q1 015", "Q 1011").
RE_FIX_NOSIG = re.compile(r"\bN ?O ?S ?I ?G\b")
RE_FIX_QNH = re.compile(r"\bQ ?(\d) ?(\d) ?(\d) ?(\d)\b")
# Local "MET REPORT"-style messages that occasionally leak into the METAR feed.
RE_NON_METAR = re.compile(r"\b(TDZ|WIND RWY|VIS RWY|CLD RWY)\b")

CLOUD_OCTAS = {"FEW": 2, "SCT": 4, "BKN": 7, "OVC": 8}
WX_PHENOMENA = ("DZ", "RA", "SN", "SG", "IC", "PL", "GR", "GS", "UP", "BR", "FG", "FU",
                "VA", "DU", "SA", "HZ", "PY", "PO", "SQ", "FC", "SS", "DS")
PRECIP = {"DZ", "RA", "SN", "SG", "IC", "PL", "GR", "GS", "UP"}
TREND_START = {"NOSIG", "BECMG", "TEMPO"}


@dataclass
class TrendGroup:
    kind: str                      # BECMG | TEMPO
    fm: str | None = None          # HHMM
    tl: str | None = None
    at: str | None = None
    vis_m: float | None = None
    cavok: bool = False
    nsw: bool = False
    wx: list[str] = field(default_factory=list)
    ceiling_ft: float | None = None


@dataclass
class Metar:
    raw: str
    station: str | None = None
    obs_time: datetime | None = None
    report_type: str = "METAR"     # METAR | SPECI
    nil: bool = False
    auto: bool = False
    cor: bool = False
    wind_dir: float = math.nan     # deg (NaN when VRB / calm / missing)
    wind_speed_kt: float = math.nan
    wind_gust_kt: float = math.nan
    wind_vrb: bool = False
    wind_var_from: float = math.nan
    wind_var_to: float = math.nan
    vis_m: float = math.nan        # prevailing visibility (10000 for 9999 / CAVOK)
    vis_min_m: float = math.nan    # directional minimum visibility
    cavok: bool = False
    rvr: list[tuple[str, float, str | None, float | None, str | None]] = field(default_factory=list)
    wx: list[str] = field(default_factory=list)
    recent_wx: list[str] = field(default_factory=list)
    clouds: list[tuple[str, float, str | None]] = field(default_factory=list)
    vv_ft: float = math.nan
    nsc: bool = False
    temp_c: float = math.nan
    dewpt_c: float = math.nan
    qnh_hpa: float = math.nan
    nosig: bool = False
    trend: list[TrendGroup] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)
    malformed: bool = False        # not a WMO FM 15 report (e.g. local MET REPORT text)

    # ------------------------------------------------------------------ derived values
    @property
    def rvr_min_m(self) -> float:
        vals = [v for (_rwy, v, _pfx, _vmax, _tend) in self.rvr]
        return min(vals) if vals else math.nan

    @property
    def ceiling_ft(self) -> float:
        """Lowest BKN/OVC layer or vertical visibility (ft); inf when no ceiling."""
        cands = [b for (c, b, _t) in self.clouds if c in ("BKN", "OVC") and not math.isnan(b)]
        if not math.isnan(self.vv_ft):
            cands.append(self.vv_ft)
        return min(cands) if cands else math.inf

    @property
    def lowest_cloud_ft(self) -> float:
        cands = [b for (_c, b, _t) in self.clouds if not math.isnan(b)]
        if not math.isnan(self.vv_ft):
            cands.append(self.vv_ft)
        return min(cands) if cands else math.inf

    @property
    def max_cover_octas(self) -> int:
        cov = [CLOUD_OCTAS[c] for (c, _b, _t) in self.clouds]
        if not math.isnan(self.vv_ft):
            cov.append(8)
        return max(cov) if cov else 0

    def has_wx(self, code: str) -> bool:
        return any(code in w for w in self.wx)


# ---------------------------------------------------------------------------- helpers
def _sm_to_m(tok: str) -> float | None:
    m = RE_VIS_SM.match(tok)
    if not m:
        return None
    whole = float(m.group(2)) if m.group(2) else 0.0
    frac = float(m.group(3)) / float(m.group(4)) if m.group(3) else 0.0
    return (whole + frac) * 1609.344


def _temp(tok: str | None) -> float:
    if tok is None or tok.startswith("//"):
        return math.nan
    return -float(tok[1:]) if tok.startswith("M") else float(tok)


def _cloud_height(code: str) -> float:
    return math.nan if code == "///" else float(int(code) * 100)


def _parse_weather(tok: str) -> str | None:
    """Return a canonical weather token if ``tok`` is a present-weather group."""
    if tok in ("NSW",):
        return None
    m = RE_WX.match(tok)
    if not m or (m.group(3) is None and m.group(2) not in ("TS", "SH")):
        return None
    if not any(p in tok for p in WX_PHENOMENA) and m.group(2) != "TS":
        return None
    return tok


def _resolve_time(ddhhmm: re.Match, ref: datetime | None) -> datetime | None:
    day, hh, mm = (int(ddhhmm.group(i)) for i in (1, 2, 3))
    ref = ref or datetime.now(timezone.utc)
    ref = ref if ref.tzinfo else ref.replace(tzinfo=timezone.utc)
    # choose the month (ref month or previous) that puts the obs closest before ref + 1 day
    for months_back in (0, 1):
        y, mo = ref.year, ref.month - months_back
        if mo == 0:
            y, mo = y - 1, 12
        try:
            t = datetime(y, mo, day, hh % 24, mm, tzinfo=timezone.utc) + timedelta(hours=hh // 24)
        except ValueError:
            continue
        if t <= ref + timedelta(days=1):
            return t
    return None


# ---------------------------------------------------------------------------- decoder
def parse_metar(raw: str, ref_time: datetime | None = None) -> Metar:
    """Decode one METAR/SPECI string. ``ref_time`` disambiguates month/year of DDHHMMZ."""
    text = re.sub(r"\s+", " ", raw.replace("=", " ")).strip()
    rec = Metar(raw=text)
    body, _, _rmk = text.partition(" RMK ")
    if RE_NON_METAR.search(body):
        rec.malformed = True
    body = RE_FIX_QNH.sub(r"Q\1\2\3\4", RE_FIX_NOSIG.sub("NOSIG", body))
    toks = body.split(" ")
    i = 0
    if toks and toks[0] in ("METAR", "SPECI"):
        rec.report_type = toks[0]
        i += 1
    while i < len(toks) and toks[i] in ("COR", "AMD"):
        rec.cor = True
        i += 1
    if i < len(toks) and re.fullmatch(r"[A-Z]{4}", toks[i]):
        rec.station = toks[i]
        i += 1
    if i < len(toks) and (m := RE_TIME.match(toks[i])):
        rec.obs_time = _resolve_time(m, ref_time)
        i += 1
    if i < len(toks) and toks[i] == "NIL":
        rec.nil = True
        return rec

    # ------------------------------------------------------------- main body
    trend_tokens: list[str] = []
    while i < len(toks):
        t = toks[i]
        if t in TREND_START:
            trend_tokens = toks[i:]
            break
        if t == "AUTO":
            rec.auto = True
        elif t == "COR":
            rec.cor = True
        elif (m := RE_WIND.match(t)):
            if m.group(1) == "VRB":
                rec.wind_vrb = True
            elif m.group(1) != "///":
                rec.wind_dir = float(m.group(1))
            if m.group(2) != "//":
                spd = float(m.group(2))
                fac = {"KT": 1.0, "MPS": 1.943844, "KMH": 0.539957}[m.group(4)]
                rec.wind_speed_kt = spd * fac
                if m.group(3):
                    rec.wind_gust_kt = float(m.group(3)) * fac
        elif (m := RE_WIND_VAR.match(t)):
            rec.wind_var_from, rec.wind_var_to = float(m.group(1)), float(m.group(2))
        elif t == "CAVOK":
            rec.cavok = True
            rec.vis_m = 10000.0
        elif (m := RE_VIS.match(t)) and math.isnan(rec.vis_m):
            v = float(m.group(1))
            rec.vis_m = 10000.0 if v >= 9999 else v
        elif (m := RE_VIS_DIR.match(t)):
            rec.vis_min_m = float(m.group(1))
        elif t.endswith("SM") and (v := _sm_to_m(t)) is not None:
            rec.vis_m = min(v, 10000.0)
        elif re.fullmatch(r"\d", t) and i + 1 < len(toks) and toks[i + 1].endswith("SM"):
            # "1 1/2SM": whole miles and fraction split over two tokens
            frac = _sm_to_m(toks[i + 1])
            if frac is not None:
                rec.vis_m = min(float(t) * 1609.344 + frac, 10000.0)
                i += 1
            else:
                rec.unparsed.append(t)
        elif (m := RE_RVR.match(t)):
            val = float(m.group(3))
            vmax = float(m.group(5)) if m.group(5) else None
            if m.group(6) == "FT":
                val *= 0.3048
                vmax = vmax * 0.3048 if vmax else None
            rec.rvr.append((m.group(1), val, m.group(2), vmax, m.group(7)))
        elif (m := RE_CLOUD.match(t)):
            rec.clouds.append((m.group(1), _cloud_height(m.group(2)), m.group(3)))
        elif (m := RE_VV.match(t)):
            rec.vv_ft = _cloud_height(m.group(1))
        elif t in ("NSC", "NCD", "SKC", "CLR"):
            rec.nsc = True
        elif (m := RE_TEMP.match(t)):
            rec.temp_c, rec.dewpt_c = _temp(m.group(1)), _temp(m.group(2))
        elif (m := RE_QNH.match(t)):
            if m.group(2) != "////":
                q = float(m.group(2))
                rec.qnh_hpa = q if m.group(1) == "Q" else q / 100.0 * 33.8639
        elif (m := RE_RECENT.match(t)):
            rec.recent_wx.append(m.group(1))
        elif t == "WS":
            # wind-shear group: "WS R03L" / "WS ALL RWY" -> skip the following token(s)
            if i + 2 < len(toks) and toks[i + 1] == "ALL" and toks[i + 2] == "RWY":
                i += 2
            else:
                i += 1
        elif (w := _parse_weather(t)) is not None:
            rec.wx.append(w)
        elif RE_RWY_STATE.match(t):
            pass  # runway-state group (winter contamination) – not used
        else:
            rec.unparsed.append(t)
        i += 1

    # ------------------------------------------------------------- TREND
    grp: TrendGroup | None = None
    for t in trend_tokens:
        if t == "NOSIG":
            rec.nosig = True
            grp = None
        elif t in ("BECMG", "TEMPO"):
            grp = TrendGroup(kind=t)
            rec.trend.append(grp)
        elif grp is None:
            continue
        elif (m := RE_TREND_TIME.match(t)):
            setattr(grp, m.group(1).lower(), m.group(2))
        elif t == "CAVOK":
            grp.cavok, grp.vis_m = True, 10000.0
        elif t == "NSW":
            grp.nsw = True
        elif (m := RE_VIS.match(t)):
            v = float(m.group(1))
            grp.vis_m = 10000.0 if v >= 9999 else v
        elif (m := RE_CLOUD.match(t)):
            if m.group(1) in ("BKN", "OVC"):
                h = _cloud_height(m.group(2))
                grp.ceiling_ft = h if grp.ceiling_ft is None else min(grp.ceiling_ft, h)
        elif (m := RE_VV.match(t)):
            h = _cloud_height(m.group(1))
            grp.ceiling_ft = h if grp.ceiling_ft is None else min(grp.ceiling_ft, h)
        elif (w := _parse_weather(t)) is not None:
            grp.wx.append(w)
    return rec


# ---------------------------------------------------------------------------- flattening
def relative_humidity(t_c: float, td_c: float) -> float:
    """Relative humidity (%) from the Magnus formula (Alduchov & Eskridge 1996 constants)."""
    if math.isnan(t_c) or math.isnan(td_c):
        return math.nan
    a, b = 17.625, 243.04
    rh = 100.0 * math.exp(a * td_c / (b + td_c) - a * t_c / (b + t_c))
    return min(rh, 100.0)


def flatten(rec: Metar) -> dict:
    """Turn a decoded report into a flat record of numeric/boolean columns."""
    wx = " ".join(rec.wx)
    fog_tokens = [w for w in rec.wx if "FG" in w]
    d = {
        "obs_time": rec.obs_time,
        "report_type": rec.report_type,
        "nil": rec.nil,
        "auto": rec.auto,
        "wind_dir": rec.wind_dir,
        "wind_speed_kt": rec.wind_speed_kt,
        "wind_gust_kt": rec.wind_gust_kt,
        "wind_vrb": rec.wind_vrb,
        "wind_var_range": (
            (rec.wind_var_to - rec.wind_var_from) % 360
            if not math.isnan(rec.wind_var_from) else 0.0),
        "vis_m": rec.vis_m,
        "vis_min_m": rec.vis_min_m,
        "cavok": rec.cavok,
        "rvr_min_m": rec.rvr_min_m,
        "rvr_n": len(rec.rvr),
        "rvr_any_m_prefix": any(p == "M" for (_r, _v, p, _x, _t) in rec.rvr),
        "rvr_tend_down": any(t == "D" for (*_x, t) in rec.rvr),
        "rvr_tend_up": any(t == "U" for (*_x, t) in rec.rvr),
        "ceiling_ft": rec.ceiling_ft,
        "lowest_cloud_ft": rec.lowest_cloud_ft,
        "max_cover_octas": rec.max_cover_octas,
        "vv_ft": rec.vv_ft,
        "n_cloud_layers": len(rec.clouds),
        "cb_tcu": any(t in ("CB", "TCU") for (_c, _b, t) in rec.clouds),
        "temp_c": rec.temp_c,
        "dewpt_c": rec.dewpt_c,
        "qnh_hpa": rec.qnh_hpa,
        "wx": wx,
        "wx_fg": any(w.endswith("FG") and not w.startswith(("MI", "BC", "PR", "VC")) for w in fog_tokens),
        "wx_shallow_fg": any(w.startswith(("MI", "BC", "PR")) for w in fog_tokens),
        "wx_vcfg": any(w.startswith("VC") for w in fog_tokens),
        "wx_fzfg": any("FZFG" in w for w in fog_tokens),
        "wx_br": "BR" in wx,
        "wx_hz": "HZ" in wx or "FU" in wx,
        "wx_dz": "DZ" in wx,
        "wx_ra": "RA" in wx,
        "wx_sn": "SN" in wx or "SG" in wx,
        "wx_precip": any(p in wx for p in PRECIP),
        "wx_ts": "TS" in wx,
        "wx_sh": "SH" in wx,
        "recent_precip": any(any(p in r for p in PRECIP) for r in rec.recent_wx),
        "trend_nosig": rec.nosig,
        "trend_n": len(rec.trend),
        "n_unparsed": len(rec.unparsed),
        "malformed": rec.malformed or len(rec.unparsed) >= 4,
    }
    d["dpd_c"] = d["temp_c"] - d["dewpt_c"]
    d["rh_pct"] = relative_humidity(d["temp_c"], d["dewpt_c"])
    return d


def trend_vis_range(rec: Metar, valid_time: datetime) -> tuple[float, float]:
    """Visibility (m) forecast by the METAR TREND for ``valid_time`` (obs < valid <= obs+2 h).

    Returns ``(prevailing, worst_case)``:

    * NOSIG / no TREND: persistence of the observed visibility for both readings.
    * BECMG: before the change window the old value holds, after it the new one. Inside the
      window (FM..TL, AT, or the whole 2-h period when no time is given) the forecast is the
      *range* [old, new]; the prevailing reading keeps the old value until the change is
      complete, the worst-case reading takes the lower end of the range.
    * TEMPO: ignored by the prevailing reading; the worst-case reading takes the minimum of
      the prevailing value and the TEMPO value inside the TEMPO window.

    This "range" interpretation follows common TAF/TREND verification practice, so the two
    readings bracket the skill of the official forecast.
    """
    vis = rec.vis_m
    if rec.obs_time is None or math.isnan(vis):
        return vis, vis
    period_end = rec.obs_time + timedelta(hours=2)

    def _abs(hhmm: str | None) -> datetime | None:
        if hhmm is None:
            return None
        base = rec.obs_time.replace(minute=0, second=0, microsecond=0)
        t = base.replace(hour=int(hhmm[:2]) % 24, minute=int(hhmm[2:]) % 60)
        if int(hhmm[:2]) == 24 or t < rec.obs_time - timedelta(minutes=30):
            t += timedelta(days=1)
        return t

    prevailing, worst = vis, vis
    for g in rec.trend:
        if g.vis_m is None:
            continue
        if g.at:
            start = end = _abs(g.at)
        else:
            start = _abs(g.fm) or rec.obs_time
            end = _abs(g.tl) or period_end
        if g.kind == "BECMG":
            if valid_time >= end:
                prevailing = worst = g.vis_m
            elif valid_time >= start:          # transition: range [old, new]
                worst = min(prevailing, g.vis_m)
        elif start <= valid_time <= end:       # TEMPO
            worst = min(worst, g.vis_m)
    return prevailing, worst
