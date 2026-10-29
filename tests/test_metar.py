import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esenboga.metar import flatten, parse_metar, relative_humidity, trend_vis_range  # noqa: E402

REF = datetime(2024, 1, 15, 12, tzinfo=timezone.utc)


def test_fog_with_rvr_and_runway_state():
    r = parse_metar("LTAC 110720Z VRB01KT 0400 R03R/0900N R21L/0400U R03L/0650U R21R/0450U "
                    "FZFG OVC002 M05/M06 Q1020 R03R4///95 R03L4///94 NOSIG", REF)
    f = flatten(r)
    assert f["vis_m"] == 400 and f["rvr_min_m"] == 400 and f["rvr_n"] == 4
    assert f["wx_fg"] and f["wx_fzfg"] and not f["wx_shallow_fg"]
    assert f["ceiling_ft"] == 200 and f["temp_c"] == -5 and f["dewpt_c"] == -6
    assert f["qnh_hpa"] == 1020 and f["trend_nosig"] and r.unparsed == []
    assert r.obs_time == datetime(2024, 1, 11, 7, 20, tzinfo=timezone.utc)


def test_wind_variability_and_clouds():
    r = parse_metar("METAR LTAC 282320Z 10004KT 070V130 6000 FEW040 SCT200 09/08 Q1014 NOSIG "
                    "RMK RWY21C 10003KT 060V130", REF)
    f = flatten(r)
    assert (f["wind_dir"], f["wind_speed_kt"], f["wind_var_range"]) == (100, 4, 60)
    assert f["vis_m"] == 6000 and math.isinf(f["ceiling_ft"]) and f["lowest_cloud_ft"] == 4000
    assert f["max_cover_octas"] == 4 and f["rh_pct"] == pytest.approx(93.6, abs=0.5)


def test_keying_errors_are_repaired():
    r = parse_metar("LTAC 090650Z 00000KT 0400 R03R/1500U R21L/0400N FG SCT010 00/M00 Q1 029 "
                    "BECMG 3000 BR", REF)
    assert r.qnh_hpa == 1029 and r.unparsed == []
    r2 = parse_metar("LTAC 152220Z 01007KT 5000 BR FEW005 03/02 Q1012 RERA NO SIG", REF)
    assert r2.nosig and r2.recent_wx == ["RA"] and r2.unparsed == []


def test_cavok_nil_vv_and_rvr_prefixes():
    assert parse_metar("LTAC 100020Z 08004KT CAVOK M05/M08 Q1015 NOSIG", REF).vis_m == 10000
    assert parse_metar("LTAC 010000Z NIL", REF).nil
    r = parse_metar("LTAC 120350Z 00000KT 0100 R03R/P2000 R21L/M0050 R03L/0600V1000U FG VV001 "
                    "M03/M03 Q1030 NOSIG", REF)
    assert r.rvr_min_m == 50 and r.vv_ft == 100 and r.ceiling_ft == 100 and r.max_cover_octas == 8


def test_shallow_fog_and_mist_are_not_fog():
    f = flatten(parse_metar("LTAC 120450Z 00000KT 2500 BCFG BR NSC M02/M03 Q1030 NOSIG", REF))
    assert not f["wx_fg"] and f["wx_shallow_fg"] and f["wx_br"]


def test_snow_and_precip_flags():
    f = flatten(parse_metar("LTAC 010050Z 02012KT 1800 +SN SCT005 BKN030 OVC080 M02/M03 Q1003 "
                            "535/ //95 NOSIG", REF))
    assert f["wx_sn"] and f["wx_precip"] and f["ceiling_ft"] == 3000


def test_trend_becmg_without_time_is_a_range():
    r = parse_metar("LTAC 090650Z 00000KT 0400 R03R/1500U FG SCT010 00/M00 Q1029 BECMG 3000 BR",
                    datetime(2024, 1, 9, 12, tzinfo=timezone.utc))
    t = r.obs_time
    assert trend_vis_range(r, t.replace(hour=7, minute=50)) == (400, 400)   # inside window
    assert trend_vis_range(r, t.replace(hour=8, minute=50)) == (3000, 3000)  # completed


def test_trend_tempo_and_becmg_tl():
    r = parse_metar("LTAC 090450Z 36003KT 3300 -SN BR FEW006 BKN030 OVC080 00/00 Q1004 "
                    "TEMPO FM0600 TL0700 1200 SN", datetime(2024, 1, 9, 12, tzinfo=timezone.utc))
    t = r.obs_time
    assert trend_vis_range(r, t.replace(hour=5, minute=50)) == (3300, 3300)
    assert trend_vis_range(r, t.replace(hour=6, minute=30)) == (3300, 1200)
    r2 = parse_metar("LTAC 050020Z 20012KT 3300 SN BR SCT004 BKN029 OVC080 01/00 Q1006 "
                     "BECMG TL0100 VRB02KT 8000 NSW", datetime(2015, 1, 5, 12, tzinfo=timezone.utc))
    assert trend_vis_range(r2, r2.obs_time.replace(hour=1, minute=20)) == (8000, 8000)
    assert trend_vis_range(r2, r2.obs_time.replace(hour=0, minute=50)) == (3300, 3300)


def test_relative_humidity():
    assert relative_humidity(10, 10) == pytest.approx(100)
    assert relative_humidity(20, 10) == pytest.approx(52.5, abs=0.5)


def test_local_report_is_flagged_malformed():
    f = flatten(parse_metar("LTAC 150150Z WIND RWY 03R TDZ 210/2KT END 170/1KT VIS RWY 03R TDZ "
                            "5KM END 5KM", REF))
    assert f["malformed"]
