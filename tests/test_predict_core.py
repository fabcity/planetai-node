"""The arithmetic of the predict pack: origins, context, errors, the shown rule, the Next days line.

Run: PYTHONPATH=app python3 tests/test_predict_core.py
predict_core.py is pure (stdlib only), so nothing here needs a database, a model or a network.
"""
import os
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packs", "predict"))
import predict_core as C  # noqa: E402

UTC = timezone.utc
ORIGIN = datetime(2026, 11, 21, 16, tzinfo=UTC)


def series(hours, end=ORIGIN, f=lambda i: float(i % 24)):
    """`hours` hourly points ending the hour before `end`."""
    return {end - timedelta(hours=hours - i): f(i) for i in range(hours)}


def test_origin_is_local_midnight():
    assert C.origin_utc(date(2026, 11, 22), "Asia/Makassar") == datetime(2026, 11, 21, 16, tzinfo=UTC)
    assert C.origin_utc(date(2026, 10, 25), "Europe/Madrid") == datetime(2026, 10, 24, 22, tzinfo=UTC)


def test_context_interpolates_and_caps():
    pts = series(10 * 24, f=lambda i: float(i))
    del pts[ORIGIN - timedelta(hours=5)], pts[ORIGIN - timedelta(hours=4)], pts[ORIGIN - timedelta(hours=3)]
    pts[ORIGIN - timedelta(hours=6)], pts[ORIGIN - timedelta(hours=2)] = 0.0, 4.0
    ctx = C.context(pts, ORIGIN)
    assert ctx is not None and len(ctx) == 240 and ctx[-6:-1] == [0.0, 1.0, 2.0, 3.0, 4.0], ctx[-6:]
    assert len(C.context(series(5000), ORIGIN)) == C.CONTEXT_HOURS == 4096


def test_context_refuses_the_young_and_the_sparse():
    assert C.context(series(6 * 24), ORIGIN) is None
    long = series(20 * 24)
    for i, t in enumerate(sorted(long)[-14 * 24:]):
        if i % 5 == 0:
            del long[t]                       # 80% present in the last 14 days
    assert C.context(long, ORIGIN) is None
    full = series(14 * 24)
    first = min(full)
    got = [d for d in range(14) if C.context(full, first + timedelta(days=d)) is not None]
    assert got == list(range(7, 14)), got     # seven origins, the last one on the series' fourteenth day


def test_context_refuses_a_sensor_gone_quiet():
    pts = series(20 * 24)
    for h in range(1, 7):
        del pts[ORIGIN - timedelta(hours=h)]   # the last 6 hours before the origin unmeasured
    assert C.context(pts, ORIGIN) is None, "a silent sensor is not forecast from a flat line"
    pts[ORIGIN - timedelta(hours=6)] = 1.0
    assert C.context(pts, ORIGIN) is not None, "one measured hour in the last six is enough"


def test_silent_days_are_not_scored():
    pred = {ORIGIN + timedelta(hours=h): 1.0 for h in range(48)}
    truth = {ORIGIN + timedelta(hours=h): 1.0 for h in range(24)}
    truth.update({ORIGIN - timedelta(hours=h): 1.0 for h in range(1, 25)})
    e = C.day_errors(pred, truth, ORIGIN)
    assert e["d1"] is not None and e["d2"] is None, e
    six = [(1.0, 5.0, 24)] * 6
    assert C.score(six)["shown"] is False and C.score(six)["days"] == 6


def test_shown_only_when_strictly_closer():
    assert C.score([(3.0, 3.0, 24)] * 7)["shown"] is False
    s = C.score([(2.9, 3.0, 24)] * 7)
    assert s["shown"] is True and s["days"] == 7 and abs(s["model"] - 2.9) < 1e-9 and abs(s["naive"] - 3.0) < 1e-9
    assert C.score([]) == {"model": None, "naive": None, "days": 0, "shown": False}, "no scored day has no error, never 0.0"
    assert C.score([None, None]) == C.score([])


def test_a_day_needs_twelve_hours():
    assert C.score([(1.0, 2.0, 11)] * 10)["days"] == 0, "a day with 11 measured hours is not scored"
    assert C.score([(1.0, 2.0, 12)] * 10)["days"] == 10


def test_scores_take_the_last_28_days():
    s = C.score([(9.0, 1.0, 24)] * 8 + [(1.0, 2.0, 24)] * 28)
    assert s["days"] == 28 and s["model"] == 1.0 and s["shown"], s


def test_naive_is_the_last_measured_day():
    before = {ORIGIN - timedelta(hours=24 - h): 10.0 + h for h in range(24)}    # clock hour h of the day before
    truth = dict(before)
    truth.update({ORIGIN + timedelta(hours=h): 10.0 + h % 24 + 2 for h in range(48)})
    pred = {ORIGIN + timedelta(hours=h): 10.0 + h % 24 + 1 for h in range(48)}
    e = C.day_errors(pred, truth, ORIGIN)
    assert e["d1"] == (1.0, 2.0, 24), e["d1"]
    assert e["d2"] == (1.0, 2.0, 24), e["d2"]
    del truth[ORIGIN - timedelta(hours=24)]      # hour 0 of the naive day is missing: it and its pair are dropped
    assert C.day_errors(pred, truth, ORIGIN)["d1"][2] == 23


def test_day_range():
    pred = {ORIGIN + timedelta(hours=h): float(h) for h in range(48)}
    assert C.day_range(pred, ORIGIN, 1) == (0.0, 23.0) and C.day_range(pred, ORIGIN, 2) == (24.0, 47.0)
    assert C.day_range({}, ORIGIN, 1) is None


def test_ahead_meta():
    sc = {"model": 3.2, "naive": 4.1, "days": 28, "shown": True}
    m = C.ahead_meta(date(2026, 11, 21), (5.6, 11.2), "µg/m³", sc)
    assert m == {"fetched": "2026-11-21",
                 "ahead_en_d1": "PM2.5 outside: 6–11 µg/m³ (modelled here, off by 3 on average over 28 days)",
                 "ahead_es_d1": "PM2.5 fuera: 6–11 µg/m³ (modelado aquí, error medio de 3 en 28 días)",
                 "ahead_id_d1": "PM2.5 di luar: 6–11 µg/m³ (dimodelkan di sini, rata-rata meleset 3 dalam 28 hari)"}, m
    small = C.ahead_meta(date(2026, 11, 21), (5.6, 11.2), "µg/m³", {**sc, "model": 0.44, "days": 9})
    assert small["ahead_en_d1"].endswith("(modelled here, off by 0.4 on average over 9 days)"), small
    assert C.ahead_meta(date(2026, 11, 21), None, "µg/m³", sc) == {"fetched": "2026-11-21"}
    assert C.ahead_meta(date(2026, 11, 21), (5.6, 11.2), "µg/m³", None) == {"fetched": "2026-11-21"}, "no line without its error"
    wide = C.ahead_meta(date(2026, 11, 21), (1234.5, 98765.4), "µg/m³", {**sc, "model": 12345.6})
    assert all(len(v) <= 160 for k, v in wide.items() if k.startswith("ahead_")), "Next days cuts at 160 characters"


for _n, _f in list(globals().items()):
    if _n.startswith("test_"):
        _f()
print("  ok: origins, context, errors, the shown rule and the Next days line")
sys.exit(0)
