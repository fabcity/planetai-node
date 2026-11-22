"""The arithmetic of the calibrate pack: pairs, refusals, the line, the days it never saw, the shown rule.

Run: PYTHONPATH=app python3 tests/test_calibrate_core.py
calibrate_core.py is pure (stdlib only), so nothing here needs a database or a network.
"""
import importlib.util
import os
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("calibrate_core", os.path.join(ROOT, "packs", "calibrate", "calibrate_core.py"))
C = importlib.util.module_from_spec(_spec)
sys.modules["calibrate_core"] = C
_spec.loader.exec_module(C)

NOW = datetime(2026, 11, 22, 6, tzinfo=timezone.utc)


def hours(start, days, f):
    return {start + timedelta(hours=i): f(i) for i in range(days)}


def test_all():
    # parse
    P = C.parse_pairs("a b pm25 2026-08-30; c d pm25 2026-07-13 2026-10-20 ;; a z pm25 2026-09-01; e e pm25 2026-09-01; "
                      "f g pm25 soon; h i pm25; j k pm25 2026-12-25; l m pm25 2026-10-01 2026-09-01; n o pm25 2026-09-01 2027-01-01",
                      date(2026, 11, 22))
    assert [p["problem"] for p in P] == [None, None, "duplicate", "same", "date", "fields", "since-in-future", "until-before-since", None]
    assert P[0]["pair"] == C.Pair("a", "b", "pm25", date(2026, 8, 30), None) and P[1]["pair"].until == date(2026, 10, 20)
    assert P[-1]["pair"].until is None, "an until after today is an open pair"
    assert C.parse_pairs("", date(2026, 11, 22)) == [] and C.parse_pairs("  ;  ", date(2026, 11, 22)) == []

    # refuse, in order
    S = {"sensor_id": "a", "source": "smartcitizen", "kind": "sensor", "indoor": False}
    R = {"sensor_id": "b", "source": "smartcitizen", "kind": "sensor", "indoor": False}
    ROLES, ST = {("smartcitizen", "pm25"), ("baliairdispatch", "pm25")}, {"baliairdispatch"}
    ok = lambda **k: C.refuse(P[0]["pair"], k.get("s", S), k.get("r", R), ST, k.get("roles", ROLES), k.get("m", 30.0))
    assert ok() is None and ok(m=None) is None and ok(m=50.0) is None
    assert ok(s=None) == {"test": "unknown", "side": "sensor"} and ok(r=None) == {"test": "unknown", "side": "reference"}
    assert ok(r={**R, "kind": "peer"}) == {"test": "not-a-sensor", "side": "reference"}
    assert ok(s={**S, "source": "baliairdispatch"}) == {"test": "sensor-is-station"}
    assert ok(r={**R, "source": "baliairdispatch"}) is None, "a station may be the reference"
    assert ok(roles={("smartcitizen-direct", "pm25")}) == {"test": "no-channel", "side": "sensor"}
    assert ok(r={**R, "indoor": True}) == {"test": "indoor-outdoor"}
    assert ok(m=50.4) is not None and ok(m=812.3) == {"test": "apart", "metres": 812}

    # a pair that earns it: reference = 2 + 1.5 * sensor for 30 days up to an hour ago
    pair = C.Pair("a", "b", "pm25", date(2026, 10, 1), None)
    x = hours(NOW - timedelta(days=30), 30 * 24, lambda i: 10 + (i * 7) % 13)
    y = {t: 2 + 1.5 * v for t, v in x.items()}
    w = C.work(pair, x, y, NOW, "UTC")
    assert w["shown"] and w["why"] is None and abs(w["line"]["a"] - 2) < 1e-6 and abs(w["line"]["b"] - 1.5) < 1e-6
    assert w["checked"]["days"] == 14 and w["checked"]["corrected"] < 1e-6 < w["checked"]["measured"] and w["paired_hours"] == 720

    # the line changed under it: twice the sensor for 15 days, then equal to it
    y2 = {t: (2 * v if t < NOW - timedelta(days=15) else v) for t, v in x.items()}
    w = C.work(pair, x, y2, NOW, "UTC")
    assert not w["shown"] and w["why"] == {"reason": "measured-closer"}

    # too young, in hours and then in days
    x5 = {t: v for t, v in x.items() if t >= NOW - timedelta(days=5)}
    assert C.work(pair, x5, y, NOW, "UTC")["why"] == {"reason": "young", "hours": 120, "need_hours": 168, "days": 0, "need_days": 7}
    x10 = {t: v for t, v in x.items() if t >= NOW - timedelta(days=10)}
    w = C.work(pair, x10, y, NOW, "UTC")
    assert w["why"]["reason"] == "young" and w["why"]["hours"] == 240 and 0 < w["why"]["days"] < 7 and w["line"] is not None

    # the reference stops: shown on day 6, withdrawn on day 8, the same answer twice
    y_stop = {t: v for t, v in y.items() if t <= NOW - timedelta(days=6)}
    a, b = C.work(pair, x, y_stop, NOW, "UTC"), C.work(pair, x, y_stop, NOW, "UTC")
    assert a == b and a["shown"] and a["last_paired"] == max(y_stop)
    w = C.work(pair, x, y_stop, NOW + timedelta(days=2), "UTC")
    assert not w["shown"] and w["why"] == {"reason": "withdrawn", "since": max(y_stop).date()}

    # since and until cut the hours
    assert C.work(C.Pair("a", "b", "pm25", date(2026, 11, 18), None), x, y, NOW, "UTC")["paired_hours"] == 4 * 24 + 6
    assert C.work(C.Pair("a", "b", "pm25", date(2026, 10, 1), date(2026, 11, 10)), x, y, NOW, "UTC")["why"]["reason"] == "withdrawn"

    # a stuck sensor, and two series that never share an hour
    flat = dict.fromkeys(x, 7.0)
    w = C.work(pair, flat, y, NOW, "UTC")
    assert w["line"] is None and not w["shown"] and w["why"] == {"reason": "flat"}
    assert C.work(pair, x, {t + timedelta(minutes=30): v for t, v in y.items()}, NOW, "UTC")["why"] == {"reason": "no-hours"}
    assert C.work(pair, {}, {}, NOW, "UTC")["why"] == {"reason": "no-hours"}

    # the tenth, and never below zero
    days = [date(2026, 11, 1) + timedelta(days=i) for i in range(10)]
    V = lambda m, c, n=10: C.verdict([(d, m, c) for d in days[:n]], date(2026, 11, 10))
    assert V(1.0, 0.875)[1] is None and V(1.0, 0.9375)[1] == {"reason": "not-a-tenth"} and V(1.0, 1.25)[1] == {"reason": "measured-closer"}
    assert V(1.0, 0.5, 6)[1]["reason"] == "young" and V(1.0, 0.5, 6)[1]["days"] == 6
    old = [(date(2026, 9, 1) + timedelta(days=i), 1.0, 0.1) for i in range(10)]
    assert C.verdict(old, date(2026, 11, 10))[1]["reason"] == "young", "scored days older than 28 days do not count"
    assert C.correct(-4.27, 1.51, 1.0, True) == 0.0 and C.correct(-4.27, 1.51, 1.0, False) < 0


test_all()
print("  ok: pairs, refusals, the line, the days it never saw and the shown rule")
sys.exit(0)
