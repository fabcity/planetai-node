"""The predict pack's nightly run: which origins it asks for, what it stores, when it stays quiet.

Run: PYTHONPATH=/tmp/stub:app python3 tests/test_predict_pack.py
A fake hc answers /health and /forecast and counts calls; a dict-backed cur stands where the tables are, and returns
what psycopg returns (aware datetimes, date objects).
"""
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packs", "predict"))
import adapter as A  # noqa: E402
import core as C  # noqa: E402

seen = []                                   # what the adapter logs; keeps the run's output clean
h = logging.Handler(); h.emit = seen.append
logging.getLogger("planetai.predict").addHandler(h)
logging.getLogger("planetai.predict").propagate = False
UTC = timezone.utc
TODAY = date(2026, 11, 21)
NOW = datetime(2026, 11, 21, 6, tzinfo=UTC)
START = datetime(2026, 9, 22, tzinfo=UTC)          # 60 days before today
os.environ.pop("NODE_TZ", None)
os.environ["PREDICT_MODEL"] = "amazon/chronos-bolt-tiny"
MID = "amazon/chronos-bolt-tiny@a0e552de83495b5c28c14c71c374f3e33280b340"


def hours(a, b):
    while a < b:
        yield a
        a += timedelta(hours=1)


class Cur:
    """Tables as dicts, statements answered by their shape. Writes are kept as text for the no-reading check."""
    def __init__(s):
        s.sensors = {"out": ("own", False, "sensor"), "in": ("own", True, "sensor"), "peer": ("own", False, "peer")}
        s.roles = {("own", "pm25"): "ambient", ("own", "temp"): "ambient", ("own", "iaq"): "index",
                   ("own", "fc_temp"): "ambient"}
        s.units = {("own", "pm25"): "µg/m³"}
        s.readings = {}
        for sid, m in [("out", "pm25"), ("in", "temp"), ("peer", "pm25"), ("out", "iaq"), ("out", "fc_temp")]:
            s.readings[(sid, m)] = {t: 10.0 + t.hour % 12 for t in hours(START, NOW)}
        s.pred, s.models, s.writes, s.rows, s.sqls = {}, {}, [], [], []

    def execute(s, q, a=()):
        q = " ".join(q.split())
        s.sqls.append(q)
        if q.startswith(("INSERT", "UPDATE", "DELETE")):
            s.writes.append(q)
        if q.startswith("INSERT INTO models"):
            s.models[a[0]] = a
        elif q.startswith("INSERT INTO predictions"):
            m, sid, met, o, ts, p10, p50, p90 = a
            s.pred.setdefault((m, sid, met, o, ts), (p10, p50, p90))
        elif q.startswith("DELETE FROM predictions"):
            s.pred = {k: v for k, v in s.pred.items() if not k[3] < a[0]}
        elif q.startswith("SELECT 1 FROM predictions"):
            s.rows = [(1,)] if any(k[0] == a[0] and k[3] == a[1] for k in s.pred) else []
        elif q.startswith("SELECT DISTINCT origin"):
            s.rows = [(o,) for o in sorted({k[3] for k in s.pred if k[0] == a[0] and k[3] >= a[1]})]
        elif q.startswith("SELECT sensor_id, metric, origin"):
            s.rows = [(k[1], k[2], k[3], k[4], v[1]) for k, v in s.pred.items() if k[0] == a[0] and k[3] >= a[1]]
        elif "count(*)" in q:
            best = [k for k in s.readings if k[1] == "pm25" and not s.sensors[k[0]][1] and s.sensors[k[0]][2] != "peer"]
            s.rows = [best[0]] if best else []
        elif q.startswith("SELECT r.sensor_id, r.metric, r.bucket"):
            s.rows = [(sid, m, t, v) for (sid, m), pts in sorted(s.readings.items()) for t, v in sorted(pts.items())
                      if s.sensors[sid][2] != "peer" and s.roles.get((s.sensors[sid][0], m)) == "ambient"
                      and not m.startswith("fc_") and a[0] <= t < NOW]
        elif q.startswith("SELECT c.unit"):
            s.rows = [(s.units.get((s.sensors[a[0]][0], "pm25")),)]
        else:
            raise AssertionError(q)

    def fetchall(s): return s.rows
    def fetchone(s): return s.rows[0] if s.rows else None


class R:
    def __init__(s, j): s.j = j
    def raise_for_status(s): pass
    def json(s): return s.j


class HC:
    def __init__(s, model="amazon/chronos-bolt-tiny", rev="a0e552de83495b5c28c14c71c374f3e33280b340", ready=True,
                 fail_post_at=None, down=None):
        s.health = {"ready": ready, "model": model, "revision": rev, "error": None}
        s.posts, s.bodies, s.timeouts, s.fail_post_at, s.down = 0, [], [], fail_post_at, down
    def get(s, url, timeout=None, **kw):
        s.timeouts.append(timeout)
        if s.down:
            raise s.down
        return R(s.health)
    def post(s, url, json=None, timeout=None, **kw):
        s.posts += 1
        s.timeouts.append(timeout)
        if s.fail_post_at == s.posts:
            raise OSError("connection reset")
        s.bodies.append(json)
        return R({"model": "m", "revision": "r", "quantiles": [[[v[-1] - 1, v[-1], v[-1] + 1]] * 48 for v in json["series"]]})


def go(cur, hc, today=TODAY):
    return A.run(cur, hc, today, "UTC")


def origins(cur, m=MID):
    return {k[3] for k in cur.pred if k[0] == m}


def with_node(cur, f):
    """fetch() against the fake: its own cursor and clock."""
    import contextlib
    A._cursor = contextlib.contextmanager(lambda: (yield cur))
    A._now = lambda: NOW
    return f()


# first run: today and the 28 days before it, one call each, every call carrying both eligible series
cur, hc = Cur(), HC()
r = go(cur, hc)
assert r == {"state": "ok", "model_id": MID, "filled": 29}, r
assert hc.posts == 29 and len(origins(cur)) == 29 and min(origins(cur)) == TODAY - timedelta(days=28)
assert all(len(b["series"]) == 2 and b["horizon"] == 48 for b in hc.bodies)
assert hc.timeouts[0] == 5 and set(hc.timeouts[1:]) == {120}
assert len(cur.pred) == 29 * 2 * 48 and (MID, "in", "temp", TODAY, datetime(2026, 11, 21, 0, tzinfo=UTC)) in cur.pred
print("  ok: first run backfills 29 origins")

# second run the same day: nothing to ask
n = len(cur.pred)
assert go(cur, hc)["filled"] == 0 and hc.posts == 29 and len(cur.pred) == n
print("  ok: second run same day does nothing")

# a failure on the 10th call ends fetch quietly; the next run makes the 20 that are left, oldest first kept
cur, hc = Cur(), HC(fail_post_at=10)
assert with_node(cur, lambda: A.fetch(hc)) == ([], []) and len(origins(cur)) == 9
os.environ["NODE_TZ"] = "UTC"
hc2 = HC()
assert go(cur, hc2)["filled"] == 20 and hc2.posts == 20 and len(origins(cur)) == 29
print("  ok: backfill resumes")

# container down: quiet, nothing written
cur, hc = Cur(), HC(down=ConnectionError("refused"))
seen.clear()
assert with_node(cur, lambda: A.fetch(hc)) == ([], []) and not cur.pred and not cur.models
assert all(x.levelno <= logging.WARNING for x in seen)
assert go(cur, hc)["state"] == "no-answer"
print("  ok: container down is quiet")

# not ready
cur, hc = Cur(), HC(ready=False)
assert go(cur, hc) == {"state": "no-model", "model_id": None, "filled": 0} and not cur.pred
print("  ok: no model says so")

# a second model backfills for itself and leaves the first alone
cur = Cur()
go(cur, HC())
hc = HC(model="amazon/chronos-2", rev="29ec")
assert go(cur, hc)["filled"] == 29 and hc.posts == 29
assert len(origins(cur)) == 29 and len(origins(cur, "amazon/chronos-2@29ec")) == 29
print("  ok: new model starts its own rows")

# older than 35 days goes, the rest stays
cur = Cur()
old = (MID, "out", "pm25", TODAY - timedelta(days=36), datetime(2026, 10, 16, tzinfo=UTC))
edge = (MID, "out", "pm25", TODAY - timedelta(days=35), datetime(2026, 10, 17, tzinfo=UTC))
cur.pred[old] = cur.pred[edge] = (None, 1.0, None)
go(cur, HC())
assert old not in cur.pred and edge in cur.pred
print("  ok: prunes after 35 days")

# peers, index-role and fc_ metrics never reach the model
cur, hc = Cur(), HC()
assert sorted({(k[1], k[2]) for k in cur.pred}) == [] and go(cur, hc)["state"] == "ok"
assert {(k[1], k[2]) for k in cur.pred} == {("out", "pm25"), ("in", "temp")}
assert all(len(b["series"]) == 2 for b in hc.bodies)
q = [x for x in cur.sqls if x.startswith("SELECT r.sensor_id, r.metric, r.bucket")][0]
assert "role = 'ambient'" in q and "<> 'peer'" in q and "fc" in q and "s.local" in q and "r.bucket < now()" in q
print("  ok: peers and non-ambient are left out")

# nothing written to a reading table; fetch hands the core no readings
cur, hc = Cur(), HC()
out = with_node(cur, lambda: A.fetch(hc))
assert out[1] == [] and out[0][0]["sensor_id"] == "predict" and out[0][0]["lat"] is None and out[0][0]["kind"] == "model"
assert cur.writes and not [w for w in cur.writes if any(t in w for t in ("readings", "observations", "readings_1h_done"))]
assert with_node(cur, lambda: A.fetch(hc)) == ([], [])          # the next poll: today is there, no call
assert hc.posts == 29
print("  ok: writes no reading")

# the line: only `fetched` unless tomorrow is shown; with it, tomorrow's range
cur, hc = Cur(), HC()
sc = {("out", "pm25"): {"d1": C.score([]), "d2": C.score([])}}
A.scores = lambda *a: sc
out = with_node(cur, lambda: A.fetch(hc))
assert out[0][0]["meta"] == {"fetched": "2026-11-21"}, out[0][0]["meta"]
sc[("out", "pm25")]["d2"] = {"model": 1.0, "naive": 2.0, "days": 20, "shown": True}
cur = Cur()
out = with_node(cur, lambda: A.fetch(HC()))
meta = out[0][0]["meta"]
assert meta["fetched"] == "2026-11-21" and "µg/m³" in meta["ahead_en_d1"] and "PM2.5 outside" in meta["ahead_en_d1"], meta
print("  ok: line only when tomorrow is shown")

print("  ok: predict pack")
sys.exit(0)
