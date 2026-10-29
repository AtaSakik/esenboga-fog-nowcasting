"""TAF decoder (WMO FM 51 / ICAO Annex 3, DDHH/DDHH validity format) and point-in-time
visibility look-up used to verify the official aerodrome forecasts.

For a valid time ``T`` a TAF yields a *range* of forecast visibilities:

* prevailing reading – base forecast, FM groups and completed BECMG changes;
* worst-case reading – the lower end of the range, i.e. additionally TEMPO / PROB30 / PROB40
  groups active at ``T`` and BECMG groups still in transition.

Fairness rule for a lead time ``h``: only TAFs *issued* at or before ``T - h`` may be used
(the forecaster had no later information), mirroring what the ML model sees.
"""
from __future__ import annotations

import bisect
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .metar import RE_CLOUD, RE_VIS, RE_VV, _cloud_height, _parse_weather

RE_ISSUE = re.compile(r"^(\d{2})(\d{2})(\d{2})Z$")
RE_PERIOD = re.compile(r"^(\d{2})(\d{2})/(\d{2})(\d{2})$")
RE_FM = re.compile(r"^FM(\d{2})(\d{2})(\d{2})$")
RE_PROB = re.compile(r"^PROB(30|40)$")


@dataclass
class TafGroup:
    kind: str                       # BASE | FM | BECMG | TEMPO | PROB
    start: datetime
    end: datetime
    prob: int | None = None
    vis_m: float | None = None
    wx: list[str] = field(default_factory=list)
    ceiling_ft: float | None = None


@dataclass
class Taf:
    raw: str
    issue_time: datetime
    valid_from: datetime
    valid_to: datetime
    amendment: bool = False
    groups: list[TafGroup] = field(default_factory=list)


def _ddhh(day: int, hour: int, ref: datetime) -> datetime:
    """Resolve a DDHH stamp relative to ``ref`` (handles month ends and hour 24)."""
    y, m = ref.year, ref.month
    if day < ref.day - 15:                       # wrapped into next month
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    elif day > ref.day + 15:                     # stamp from the previous month
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    extra = 0
    if hour == 24:
        hour, extra = 0, 1
    try:
        t = datetime(y, m, day, hour, tzinfo=timezone.utc)
    except ValueError:                           # e.g. day 31 in a 30-day month
        t = datetime(y, m, 1, hour, tzinfo=timezone.utc) + timedelta(days=day - 1)
    return t + timedelta(days=extra)


def parse_taf(text: str, ref_time: datetime) -> Taf | None:
    toks = re.sub(r"\s+", " ", text.replace("=", " ")).strip().split(" ")
    i, amd = 0, False
    while i < len(toks) and toks[i] in ("TAF", "AMD", "COR", "RTD"):
        amd |= toks[i] in ("AMD", "COR")
        i += 1
    if i < len(toks) and re.fullmatch(r"[A-Z]{4}", toks[i]):
        i += 1
    if i >= len(toks) or not (m := RE_ISSUE.match(toks[i])):
        return None
    issue = _ddhh(int(m.group(1)), int(m.group(2)), ref_time).replace(minute=int(m.group(3)))
    i += 1
    if i >= len(toks) or toks[i] in ("NIL", "CNL"):
        return None
    if not (m := RE_PERIOD.match(toks[i])):
        return None
    vf = _ddhh(int(m.group(1)), int(m.group(2)), issue)
    vt = _ddhh(int(m.group(3)), int(m.group(4)), issue)
    if vt <= vf:
        vt += timedelta(days=30)
    i += 1
    if i < len(toks) and toks[i] in ("CNL", "NIL"):
        return None
    taf = Taf(raw=" ".join(toks), issue_time=issue, valid_from=vf, valid_to=vt, amendment=amd)
    cur = TafGroup("BASE", vf, vt)
    taf.groups.append(cur)
    pending_prob: int | None = None
    while i < len(toks):
        t = toks[i]
        if (m := RE_PROB.match(t)):
            pending_prob = int(m.group(1))
            nxt = toks[i + 1] if i + 1 < len(toks) else ""
            if nxt != "TEMPO" and (mp := RE_PERIOD.match(nxt)):
                cur = TafGroup("PROB", _ddhh(int(mp.group(1)), int(mp.group(2)), issue),
                               _ddhh(int(mp.group(3)), int(mp.group(4)), issue), prob=pending_prob)
                taf.groups.append(cur)
                pending_prob = None
                i += 1
        elif t in ("BECMG", "TEMPO") and i + 1 < len(toks) and (mp := RE_PERIOD.match(toks[i + 1])):
            kind = "PROB" if (t == "TEMPO" and pending_prob) else t
            cur = TafGroup(kind, _ddhh(int(mp.group(1)), int(mp.group(2)), issue),
                           _ddhh(int(mp.group(3)), int(mp.group(4)), issue), prob=pending_prob)
            taf.groups.append(cur)
            pending_prob = None
            i += 1
        elif (m := RE_FM.match(t)):
            start = _ddhh(int(m.group(1)), int(m.group(2)), issue).replace(minute=int(m.group(3)))
            cur = TafGroup("FM", start, vt)
            taf.groups.append(cur)
        elif t == "CAVOK":
            cur.vis_m = 10000.0
        elif (m := RE_VIS.match(t)):
            v = float(m.group(1))
            cur.vis_m = 10000.0 if v >= 9999 else v
        elif (m := RE_CLOUD.match(t)):
            if m.group(1) in ("BKN", "OVC"):
                h = _cloud_height(m.group(2))
                cur.ceiling_ft = h if cur.ceiling_ft is None else min(cur.ceiling_ft, h)
        elif (m := RE_VV.match(t)):
            cur.ceiling_ft = _cloud_height(m.group(1))
        elif (w := _parse_weather(t)) is not None:
            cur.wx.append(w)
        i += 1
    return taf


def taf_vis_range(taf: Taf, when: datetime) -> tuple[float, float]:
    """(prevailing, worst-case) visibility in metres forecast by ``taf`` for ``when``."""
    base = taf.groups[0]
    prevailing = base.vis_m if base.vis_m is not None else math.nan
    worst = prevailing
    # FM and BECMG change the prevailing state in chronological order
    for g in sorted(taf.groups[1:], key=lambda g: g.start):
        if g.vis_m is None or g.kind in ("TEMPO", "PROB"):
            continue
        if g.kind == "FM" and when >= g.start:
            prevailing = worst = g.vis_m
        elif g.kind == "BECMG":
            if when >= g.end:
                prevailing = worst = g.vis_m
            elif when >= g.start:
                worst = min(prevailing, g.vis_m)
    for g in taf.groups[1:]:
        if g.kind in ("TEMPO", "PROB") and g.vis_m is not None and g.start <= when < g.end:
            worst = min(worst, g.vis_m)
    return prevailing, worst


# ---------------------------------------------------------------------------- archive I/O
def read_ogimet_taf_file(path: Path) -> list[Taf]:
    """Split an Ogimet text dump into individual TAFs (lines start with YYYYMMDDHHmm)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    out, cur, stamp = [], [], None
    for line in text.splitlines():
        m = re.match(r"^(\d{12})\s+(TAF.*)$", line)
        if m:
            if cur:
                out.append((stamp, " ".join(cur)))
            stamp, cur = m.group(1), [m.group(2)]
        elif cur and line.startswith(" "):
            cur.append(line.strip())
    if cur:
        out.append((stamp, " ".join(cur)))
    tafs = []
    for stamp, raw in out:
        ref = datetime.strptime(stamp, "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
        t = parse_taf(raw, ref)
        if t is not None:
            tafs.append(t)
    return tafs


class TafArchive:
    """Fast "latest TAF issued before t that covers T" look-up."""

    def __init__(self, tafs: list[Taf]):
        uniq = {}
        for t in tafs:                             # keep the last copy of duplicate issues
            uniq[(t.issue_time, t.valid_from, t.raw)] = t
        # amendments/corrections sort after the original with the same issue time
        self.tafs = sorted(uniq.values(), key=lambda t: (t.issue_time, t.amendment))
        self.issue_times = [t.issue_time for t in self.tafs]

    def lookup(self, valid_time: datetime, lead_h: float, max_age_h: float = 30.0):
        """Return (prevailing, worst, taf) for the forecast available at valid_time - lead."""
        cutoff = valid_time - timedelta(hours=lead_h)
        k = bisect.bisect_right(self.issue_times, cutoff) - 1
        while k >= 0:
            taf = self.tafs[k]
            if cutoff - taf.issue_time > timedelta(hours=max_age_h):
                break
            if taf.valid_from <= valid_time < taf.valid_to:
                p, w = taf_vis_range(taf, valid_time)
                return p, w, taf
            k -= 1
        return math.nan, math.nan, None
