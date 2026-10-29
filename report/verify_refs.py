"""Verify candidate references against Crossref and emit IEEE-formatted strings.

Every DOI below is resolved through https://api.crossref.org/works/<doi>; the bibliographic
fields are taken from the registry record, not typed by hand. Output: report/refs_crossref.json
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

DOIS = {
    "breiman2001": "10.1023/A:1010933404324",
    "chen2016": "10.1145/2939672.2939785",
    "hochreiter1997": "10.1162/neco.1997.9.8.1735",
    "cho2014": "10.3115/v1/D14-1179",
    "akiba2019": "10.1145/3292500.3330701",
    "cox1958": "10.1111/j.2517-6161.1958.tb00292.x",
    "chawla2002": "10.1613/jair.953",
    "he2009": "10.1109/TKDE.2008.239",
    "saito2015": "10.1371/journal.pone.0118432",
    "davis2006": "10.1145/1143844.1143874",
    "zadrozny2002": "10.1145/775047.775151",
    "niculescu2005": "10.1145/1102351.1102430",
    "frank2001": "10.1007/3-540-44795-4_13",
    "lundberg2020": "10.1038/s42256-019-0138-9",
    "mcgovern2019": "10.1175/BAMS-D-18-0195.1",
    "brier1950": "10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2",
    "murphy1973": "10.1175/1520-0450(1973)012<0595:ANVPOT>2.0.CO;2",
    "heidke1926": "10.1080/20014422.1926.11881138",
    "doswell1990": "10.1175/1520-0434(1990)005<0576:OSMOSI>2.0.CO;2",
    "jolliffe2012": "10.1002/9781119960003",
    "wilks2019": "10.1016/C2017-0-03921-6",
    "epstein1969": "10.1175/1520-0450(1969)008<0985:ASSFPF>2.0.CO;2",
    "kunsch1989": "10.1214/aos/1176347265",
    "wilks1997": "10.1175/1520-0442(1997)010<0065:RHTFAF>2.0.CO;2",
    "kaufman2012": "10.1145/2382577.2382579",
    "alduchov1996": "10.1175/1520-0450(1996)035<0601:IMFAOS>2.0.CO;2",
    "mahringer2008": "10.1002/met.62",
    "kneringer2019": "10.1007/s00024-018-1863-4",
    "dietz2019a": "10.1007/s00024-018-1914-x",
    "dietz2019b": "10.5194/ascmo-5-101-2019",
    "herman2016": "10.1175/WAF-D-15-0108.1",
    "marzban2007": "10.1175/WAF994.1",
    "bremnes2007": "10.1007/s00024-007-0223-6",
    "fabbian2007": "10.1175/WAF980.1",
    "gultepe2007": "10.1007/s00024-007-0211-x",
    "castillo2022": "10.1016/j.atmosres.2022.106157",
    "ortega2023": "10.1016/j.ijforecast.2022.03.009",
    "kamangir2021": "10.1016/j.mlwa.2021.100038",
    "guijo2018": "10.1016/j.atmosres.2018.07.017",
    "zhu2017": "10.4236/acs.2017.73023",
    "haeffelin2010": "10.1175/2009BAMS2671.1",
    "shapley1953": "10.1515/9781400881970-018",
}
UA = "Mozilla/5.0 (reference verification script)"
MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]


def fetch(doi: str) -> dict | None:
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/:()<>;.,")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode("utf-8"))["message"]
    except Exception as exc:  # report and continue
        print("FAILED", doi, exc)
        return None


def initials(given: str) -> str:
    parts = given.replace(".", " ").replace("-", " -").split()
    out = []
    for p in parts:
        if p.startswith("-"):
            out.append("-" + p[1] + ".")
        else:
            out.append(p[0] + ".")
    return " ".join(out).replace(" -", "-")


def ieee(m: dict) -> str:
    authors = m.get("author", [])
    names = []
    for a in authors:
        if "family" in a:
            names.append((initials(a.get("given", "")) + " " + a["family"]).strip())
        elif "name" in a:
            names.append(a["name"])
    if len(names) > 6:
        auth = names[0] + " et al."
    elif len(names) > 2:
        auth = ", ".join(names[:-1]) + ", and " + names[-1]
    else:
        auth = " and ".join(names)
    title = (m.get("title") or [""])[0]
    cont = (m.get("container-title") or [""])
    cont = cont[0] if cont else ""
    issued = m.get("published-print") or m.get("published-online") or m.get("issued")
    dp = issued.get("date-parts", [[None]])[0]
    year = dp[0]
    mon = MONTHS[dp[1] - 1] + " " if len(dp) > 1 and dp[1] else ""
    typ = m.get("type")
    bits = [f"{auth}, “{title},”"]
    if typ in ("book", "monograph", "edited-book"):
        pub = m.get("publisher", "")
        return f"{auth}, {title}. {pub}, {year}, doi: {m['DOI']}."
    if typ == "proceedings-article":
        bits.append(f"in {cont},")
    elif cont:
        bits.append(f"{cont},")
    if m.get("volume"):
        bits.append(f"vol. {m['volume']},")
    if m.get("issue"):
        bits.append(f"no. {m['issue']},")
    if m.get("page"):
        pg = m["page"].replace("-", "–")
        bits.append(f"pp. {pg}," if "–" in pg else f"Art. no. {pg},")
    elif m.get("article-number"):
        bits.append(f"Art. no. {m['article-number']},")
    bits.append(f"{mon}{year}, doi: {m['DOI']}.")
    return " ".join(bits)


def main() -> None:
    out = {}
    for key, doi in DOIS.items():
        m = fetch(doi)
        time.sleep(0.4)
        if m is None:
            out[key] = {"doi": doi, "verified": False}
            continue
        out[key] = {"doi": m["DOI"], "verified": True, "type": m.get("type"),
                    "title": (m.get("title") or [""])[0],
                    "container": (m.get("container-title") or [""])[0] if m.get("container-title") else "",
                    "ieee": ieee(m)}
        print(f"{key}: {out[key]['ieee']}")
    Path(__file__).with_name("refs_crossref.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
