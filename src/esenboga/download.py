"""Polite downloaders for the open archives used in the study.

* Iowa Environmental Mesonet (IEM) ASOS/METAR archive  -> raw METAR/SPECI text per year
* Ogimet (display_metars2.php, tipo=FT)                -> raw long-TAF text per month
* Ogimet (cgi-bin/getmetar)                             -> METAR/SPECI with report-type prefix

Only the Python standard library is used so the downloads can run before the scientific
environment exists. Every request is cached on disk; re-running skips finished files.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from esenboga.config import RAW_METAR, RAW_TAF, STATION  # noqa: E402

UA = "Mozilla/5.0 (academic research; YMH453 fog nowcasting project)"
IEM_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
OGIMET_DISPLAY = "https://www.ogimet.com/display_metars2.php"
OGIMET_GETMETAR = "https://www.ogimet.com/cgi-bin/getmetar"


def _get(url: str, timeout: int = 180) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------- IEM METAR
def download_iem_year(year: int, station: str = STATION, force: bool = False) -> Path:
    """Download one calendar year of METAR/SPECI text (UTC) from IEM as gzipped CSV."""
    out = RAW_METAR / f"{station}_IEM_{year}.csv.gz"
    if out.exists() and not force:
        return out
    params = [
        ("station", station), ("data", "metar"),
        ("year1", year), ("month1", 1), ("day1", 1),
        ("year2", year + 1), ("month2", 1), ("day2", 1),
        ("tz", "Etc/UTC"), ("format", "onlycomma"), ("latlon", "no"),
        ("missing", "M"), ("trace", "T"), ("direct", "no"),
        ("report_type", 3), ("report_type", 4),
    ]
    url = IEM_URL + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            text = _get(url)
            break
        except (urllib.error.URLError, TimeoutError) as exc:  # transient network issue
            wait = 30 * (attempt + 1)
            print(f"  IEM {year}: {exc!r}; retry in {wait}s", flush=True)
            time.sleep(wait)
    else:
        raise RuntimeError(f"IEM download failed for {year}")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or rows[0][:3] != ["station", "valid", "metar"]:
        raise RuntimeError(f"unexpected IEM payload for {year}: {text[:200]!r}")
    with gzip.open(out, "wt", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print(f"  IEM {year}: {len(rows) - 1} reports -> {out.name}", flush=True)
    return out


# ---------------------------------------------------------------------------- Ogimet
def _ogimet_pre_block(html: str) -> str | None:
    """Return the <pre> payload of an Ogimet page, or None when the page was throttled."""
    m = re.search(r"<pre>(.*?)</pre>", html, re.S | re.I)
    if not m:
        return None
    body = re.sub(r"<[^>]+>", "", m.group(1))
    # A served (non-throttled) answer always contains the query header block.
    return body if "Query made at" in body else None


def download_ogimet_taf_month(year: int, month: int, station: str = STATION,
                              force: bool = False, pause: float = 75.0,
                              max_tries: int = 12) -> Path | None:
    """Download all long TAFs (tipo=FT) issued in one month. Returns None if not served."""
    out = RAW_TAF / f"{station}_TAF_{year:04d}-{month:02d}.txt"
    if out.exists() and not force:
        return out
    # last day of the month
    nxt = date(year + (month == 12), (month % 12) + 1, 1)
    last = (nxt - date.resolution).day
    params = dict(lang="en", lugar=station, tipo="FT", ord="DIR", nil="SI", fmt="txt",
                  ano=year, mes=month, day=1, hora=0, anof=year, mesf=month, dayf=last,
                  horaf=23, minf=59, send="send")
    url = OGIMET_DISPLAY + "?" + urllib.parse.urlencode(params)
    wait = pause
    for attempt in range(max_tries):
        try:
            body = _ogimet_pre_block(_get(url))
        except (urllib.error.URLError, TimeoutError) as exc:
            body = None
            print(f"  TAF {year}-{month:02d}: network error {exc!r}", flush=True)
        if body is not None:
            out.write_text(body, encoding="utf-8")
            n = len(re.findall(r"^\d{12}\s+TAF", body, re.M))
            print(f"  TAF {year}-{month:02d}: {n} TAFs -> {out.name}", flush=True)
            time.sleep(pause)
            return out
        # throttled: exponential back-off capped at 15 minutes
        wait = min(wait * 2, 900.0)
        print(f"  TAF {year}-{month:02d}: throttled (try {attempt + 1}); sleeping {wait:.0f}s",
              flush=True)
        time.sleep(wait)
    return None


def download_ogimet_metar_month(year: int, month: int, station: str = STATION,
                                force: bool = False, pause: float = 20.0) -> Path | None:
    """METAR/SPECI with explicit report type (used to identify SPECIs and fill gaps)."""
    out = RAW_METAR / f"{station}_OGIMET_{year:04d}-{month:02d}.csv.gz"
    if out.exists() and not force:
        return out
    nxt = date(year + (month == 12), (month % 12) + 1, 1)
    last = (nxt - date.resolution).day
    url = (f"{OGIMET_GETMETAR}?icao={station}&begin={year:04d}{month:02d}010000"
           f"&end={year:04d}{month:02d}{last:02d}2359")
    wait = pause
    for attempt in range(10):
        try:
            text = _get(url)
        except (urllib.error.URLError, TimeoutError) as exc:
            text = ""
            print(f"  OGM {year}-{month:02d}: network error {exc!r}", flush=True)
        if text.startswith(station + ","):
            with gzip.open(out, "wt", encoding="utf-8") as fh:
                fh.write(text)
            print(f"  OGM {year}-{month:02d}: {text.count(chr(10))} lines", flush=True)
            time.sleep(pause)
            return out
        if "#" in text[:200] and "No " in text[:400]:   # served but empty month
            out.write_bytes(gzip.compress(b""))
            return out
        wait = min(wait * 2, 900.0)
        print(f"  OGM {year}-{month:02d}: throttled/empty (try {attempt + 1}); sleep {wait:.0f}s",
              flush=True)
        time.sleep(wait)
    return None


def download_awc_taf_recent(days: int = 30, station: str = STATION, pause: float = 0.8) -> Path:
    """TAFs of the last ``days`` days from the NOAA Aviation Weather Center data API
    (its archive keeps 30 days). The TAF in force is requested every hour, which captures
    routine issues and amendments; output uses the Ogimet line format."""
    import json
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    out = RAW_TAF / f"{station}_TAF_AWC_{now:%Y%m%d}.txt"
    seen: dict[str, str] = {}
    t = now - timedelta(days=days) + timedelta(hours=1)
    while t <= now:
        url = (f"https://aviationweather.gov/api/data/taf?ids={station}&format=json"
               f"&date={t:%Y%m%d_%H%M}")
        try:
            for rec in json.loads(_get(url, timeout=60) or "[]"):
                issue = datetime.fromisoformat(rec["issueTime"].replace("Z", "+00:00"))
                seen[f"{issue:%Y%m%d%H%M}|{rec['rawTAF']}"] = rec["rawTAF"]
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            print(f"  AWC {t:%Y-%m-%d %H}Z: {exc!r}", flush=True)
        t += timedelta(hours=1)
        time.sleep(pause)
    lines = [f"{k.split('|')[0]} {raw}" for k, raw in sorted(seen.items())]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  AWC: {len(lines)} distinct TAFs -> {out.name}", flush=True)
    return out


def _months(start: str, end: str):
    y, m = map(int, start.split("-"))
    ye, me = map(int, end.split("-"))
    while (y, m) <= (ye, me):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("what", choices=["iem", "taf", "ogimet-metar", "awc-taf"])
    ap.add_argument("--start", default="2000", help="year (iem) or YYYY-MM (taf/ogimet)")
    ap.add_argument("--end", default=str(date.today().year))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.what == "iem":
        for y in range(int(args.start), int(args.end) + 1):
            download_iem_year(y, force=args.force)
            time.sleep(3)
    elif args.what == "taf":
        for y, m in _months(args.start, args.end):
            download_ogimet_taf_month(y, m, force=args.force)
    elif args.what == "awc-taf":
        download_awc_taf_recent()
    else:
        for y, m in _months(args.start, args.end):
            download_ogimet_metar_month(y, m, force=args.force)


if __name__ == "__main__":
    main()
