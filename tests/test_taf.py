import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esenboga.taf import TafArchive, parse_taf, taf_vis_range  # noqa: E402

UTC = timezone.utc
LIVE = ("TAF LTAC 282240Z 2900/2924 VRB02KT 9999 SCT040 SCT100 BECMG 2900/2902 4000 BR "
        "PROB30 TEMPO 2903/2906 1200 BCFG BKN005 BECMG 2906/2908 9999 NSW "
        "TEMPO 2911/2915 4000 SHRA FEW025CB BKN030")


def t(d, h, m=0):
    return datetime(2026, 10, d, h, m, tzinfo=UTC)


def test_header_and_groups():
    taf = parse_taf(LIVE, t(28, 22, 40))
    assert taf.issue_time == t(28, 22, 40)
    assert taf.valid_from == t(29, 0) and taf.valid_to == t(30, 0)
    kinds = [g.kind for g in taf.groups]
    assert kinds == ["BASE", "BECMG", "PROB", "BECMG", "TEMPO"]
    assert taf.groups[2].prob == 30 and taf.groups[2].vis_m == 1200


def test_visibility_range_through_the_day():
    taf = parse_taf(LIVE, t(28, 22, 40))
    assert taf_vis_range(taf, t(29, 1)) == (10000, 4000)     # BECMG in transition
    assert taf_vis_range(taf, t(29, 3, 30)) == (4000, 1200)  # PROB30 TEMPO fog patches
    assert taf_vis_range(taf, t(29, 7)) == (4000, 4000)      # improving BECMG in transition
    assert taf_vis_range(taf, t(29, 9)) == (10000, 10000)
    assert taf_vis_range(taf, t(29, 12)) == (10000, 4000)    # TEMPO showers


def test_fm_groups_and_month_wrap():
    taf = parse_taf("TAF LTAC 302240Z 3100/0106 18005KT 9999 SCT030 FM310300 VRB02KT 0800 FG "
                    "VV002 BECMG 3105/3107 0300 FG", datetime(2026, 10, 30, 22, 40, tzinfo=UTC))
    assert taf.valid_to == datetime(2026, 11, 1, 6, tzinfo=UTC)
    assert taf_vis_range(taf, datetime(2026, 10, 31, 4, tzinfo=UTC)) == (800, 800)
    assert taf_vis_range(taf, datetime(2026, 10, 31, 6, tzinfo=UTC)) == (800, 300)
    assert taf_vis_range(taf, datetime(2026, 10, 31, 8, tzinfo=UTC)) == (300, 300)


def test_archive_respects_issue_time():
    a = parse_taf(LIVE, t(28, 22, 40))
    b = parse_taf("TAF LTAC 290440Z 2906/3006 VRB02KT 0500 FG VV001", t(29, 4, 40))
    arch = TafArchive([a, b])
    # valid 07:00, lead 1 h -> cutoff 06:00 -> the 0440Z TAF is available
    assert arch.lookup(t(29, 7), 1)[0] == 500
    # lead 3 h -> cutoff 04:00 -> only the 2240Z TAF had been issued
    assert arch.lookup(t(29, 7), 3)[0] == 4000
    # valid 05:20 lead 0.5 h: latest TAF (0440Z) does not cover 05:20 -> previous one used
    assert arch.lookup(t(29, 5, 20), 0.5)[:2] == (4000, 1200)
    assert math.isnan(arch.lookup(t(27, 5), 1)[0])
