"""GET /predict: the four states, the row shape, a day that is not shown, and that the route is in no share list.

Run: PYTHONPATH=/tmp/stub:app python3 tests/test_predict_routes.py
`_health`, the adapter's cursor and its reads are replaced with fakes that return what psycopg returns (aware
datetimes, date objects). Nothing here opens a database or asks a container.
"""
import contextlib
import importlib.util
import os
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DATABASE_URL", "postgresql://unused/never-connected")
os.environ.pop("NODE_TZ", None)
spec = importlib.util.spec_from_file_location("predict_routes", os.path.join(ROOT, "packs/predict/routes.py"))
RT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RT)
A, C = RT.adapter, RT.core
UTC = timezone.utc
NOW = datetime(2026, 11, 22, 6, tzinfo=UTC)
TODAY = date(2026, 11, 22)
ORIGIN = C.origin_utc(TODAY, "UTC")
MID = "amazon/chronos-2@29ec3766d36d6f73f0696f85560a422f50e8498c"
HEALTH = {"ready": True, "model": "amazon/chronos-2", "revision": "29ec3766d36d6f73f0696f85560a422f50e8498c", "error": None}
SC = lambda m, n, d, shown: {"model": m, "naive": n, "days": d, "shown": shown}  # noqa: E731


class Cur:
    def __init__(s, meta):
        s.meta = meta

    def execute(s, q, a=()):
        assert "FROM sensors" in " ".join(q.split()), q

    def fetchall(s):
        return s.meta


def serve(meta, health=HEALTH, scores=None, stored=None, series=None):
    @contextlib.contextmanager
    def cursor():
        yield Cur(meta)
    RT._health = lambda: health
    A._cursor, A._now = cursor, lambda: NOW
    A.scores = lambda cur, mid, today, tz: (assert_mid(mid), scores or {})[1]
    A._stored = lambda cur, mid, since: stored or {}
    A.series = lambda cur, since: series or {}
    return RT.predict()


def assert_mid(mid):
    assert mid == MID, mid


day = lambda base, n=24: {ORIGIN + timedelta(hours=h): base + h % 5 for h in range(n)}  # noqa: E731
META = [("bk", "pm25", "Backyard (SCK)", False, "µg/m³"), ("rm", "temp", "Kids", True, "°C"),
        ("bk", "temp", "Backyard (SCK)", False, None), ("new", "pm25", "Roof", False, "µg/m³"),
        ("new", "noise", "Roof", False, None)]          # declared by the source, never reported by this sensor: no row
SCORES = {("bk", "pm25"): {"d1": SC(2.9, 3.7, 28, True), "d2": SC(3.7, 4.6, 27, True)},
          ("rm", "temp"): {"d1": SC(1.0, 0.8, 28, False), "d2": SC(1.2, 0.9, 28, False)},
          ("bk", "temp"): {"d1": SC(1.0, 0.8, 4, False), "d2": SC(1.2, 0.9, 5, False)},
          ("gone", "pm25"): {"d1": SC(1, 2, 30, True), "d2": SC(1, 2, 30, True)}}
STORED = {("bk", "pm25"): {TODAY: {ORIGIN + timedelta(hours=h): 6.1 + (4.9 if h == 5 else 0) for h in range(48)}}}
SERIES = {("new", "pm25"): {NOW - timedelta(days=9, hours=h): 3.0 for h in range(3)}}

j = serve(META, scores=SCORES, stored=STORED, series=SERIES)
assert j["state"] == "ok" and j["origin"] == "2026-11-22", j
assert j["model"] == {"name": "amazon/chronos-2", "revision": "29ec3766", "adapted": False}, j["model"]
assert [(r["sensor"], r["metric"]) for r in j["rows"]] == [("Backyard (SCK)", "pm25"), ("Backyard (SCK)", "temp"),
                                                           ("Roof", "pm25"), ("Kids", "temp")], "outdoor first, then name, metric"
bk, bt, new, kid = j["rows"]
assert bk["indoor"] is False and bk["unit"] == "µg/m³" and bk["why"] is None, bk
assert bk["today"] == {"low": 6.1, "high": 11.0, "model": 2.9, "naive": 3.7, "days": 28, "shown": True}, bk["today"]
assert bk["tomorrow"]["shown"] and bk["tomorrow"]["low"] == 6.1 and bk["tomorrow"]["high"] == 6.1 and bk["tomorrow"]["days"] == 27
assert kid["today"]["shown"] is False and kid["today"]["low"] is None and kid["today"]["high"] is None, kid["today"]
assert kid["today"]["model"] == 1.0 and kid["why"] == {"reason": "naive-closer"}, kid
assert bt["unit"] is None and bt["why"] == {"reason": "young", "have": 5, "need": 7}, bt
assert new["today"] == dict.fromkeys(("low", "high", "model", "naive", "days", "shown")) and new["tomorrow"] == new["today"], new
assert new["why"] == {"reason": "young", "have": 9, "need": 14}, new
assert len(j["rows"]) == 4 and not [r for r in j["rows"] if r["metric"] == "noise"], "a metric with no data is not a series"
assert all("gone" not in r["sensor"] for r in j["rows"]) and j["model"]["adapted"] is False
print("  ok: the rows are the eligible series, the not-shown day has no range, a young one says how young")

# one day shown and one not: no `why`
one = {("bk", "pm25"): {"d1": SC(2, 3, 28, True), "d2": SC(4, 3, 28, False)}}
r = serve(META[:1], scores=one, stored=STORED)["rows"][0]
assert r["why"] is None and r["today"]["shown"] and r["tomorrow"]["low"] is None, r
print("  ok: a series with one day shown has no reason")

# the other three states
assert serve(META, health=None)["state"] == "no-answer"
assert serve(META, health=None)["rows"] == [] and serve(META, health=None)["model"] is None
for h in ({"ready": False, "model": None, "revision": None}, {"ready": True, "model": None, "revision": None}):
    assert serve(META, health=h)["state"] == "no-model", h
y = serve([], scores={})
assert y["state"] == "young" and y["rows"] == [], y
assert serve(META)["state"] == "young" and serve(META)["rows"] == [], "declared but never reported is no series"
y = serve(META, series=SERIES)
assert y["state"] == "ok" and [r["why"]["reason"] for r in y["rows"]] == ["young"], y
print("  ok: no-answer, no-model, young and ok")

# the real _health, with nothing to ask (the stub httpx has only Client, a real one gets refused): None, not an error
os.environ["MODELS_URL"] = "http://127.0.0.1:1"
RT2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(RT2)
assert RT2._health() is None
print("  ok: nothing answering is None, not an error")

import yaml  # noqa: E402
assert "share" not in yaml.safe_load(open(os.path.join(ROOT, "packs/predict/pack.yaml"))), "pack.yaml lists a share path"
print("  ok: /predict is in no share list")
sys.exit(0)
