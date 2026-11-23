"""The predict pack's SQL on a real database: which series it reads, the 29 origins, the hourly gate, GET /predict's rows.

The other predict suites run against fake cursors that ignore the query, so the joins and filters in adapter.py and
routes.py are tested by nothing there. This one makes its own rows (ids and the source start `predict-test`) under a
model that exists only here (`predict-test/model`, through a catalogue of its own), asserts on them, and removes them at
the end; every DELETE and UPDATE names that model or those sensors, and it never truncates. Meant for a Postgres with
init.sql applied and no other local ambient series (a throwaway one, as CI's lint job starts): call counts assume the
series here are the only ones.
Needs a Postgres at RHO_PG_URL; without it the suite skips.
Run: RHO_PG_URL=postgresql://planetai:x@127.0.0.1:5432/planetai PYTHONPATH=app PACKS_DIR=packs python3 tests/test_predict_pg.py
"""
import importlib.util
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

url = os.getenv("RHO_PG_URL")
if not url:
    print("  - predict on a real database skipped (set RHO_PG_URL to a Postgres with init.sql applied)")
    sys.exit(0)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_local = datetime.now(ZoneInfo("Asia/Makassar"))
TZ = "UTC" if _local.hour == 0 and _local.minute < 12 else "Asia/Makassar"      # fetch() stays quiet before 00:10 local
MODEL, REV = "predict-test/model", "predict-test-rev"
MID = f"{MODEL}@{REV}"
os.environ.update(DATABASE_URL=url, NODE_TZ=TZ, PREDICT_MODEL=MODEL)
sys.path.insert(0, os.path.join(ROOT, "packs/predict"))
import psycopg  # noqa: E402
import adapter  # noqa: E402
import logging  # noqa: E402

logging.getLogger("planetai.predict").setLevel(logging.CRITICAL)        # the container-down cases warn, by design
adapter.HERE = tempfile.mkdtemp()                                           # a catalogue with the test model only
with open(os.path.join(adapter.HERE, "models.json"), "w") as f:
    json.dump({MODEL: {"revision": REV, "sha256": "-", "size_mb": 1, "licence": "-", "kind": "bolt"}}, f)

SRC = "predict-test-src"
con = psycopg.connect(url, autocommit=True)
cur = con.cursor()


def clean():
    cur.execute("DELETE FROM predictions WHERE model_id = %s", (MID,))
    cur.execute("DELETE FROM models WHERE model_id = %s", (MID,))
    cur.execute("DELETE FROM readings_1h_done WHERE sensor_id LIKE 'predict-test-%%'", ())
    cur.execute("DELETE FROM channel_roles WHERE source = %s", (SRC,))
    cur.execute("DELETE FROM sensors WHERE sensor_id LIKE 'predict-test-%%'", ())


class R:
    status_code = 200

    def __init__(s, j):
        s.j = j

    def json(s):
        return s.j

    def raise_for_status(s):
        pass


class HC:
    posts = 0
    bad = False             # the last series' rows carry a value Postgres refuses, so its origin's insert fails

    def get(s, url, **kw):
        return R({"ready": True, "model": MODEL, "revision": REV, "error": None})

    def post(s, url, **kw):
        HC.posts += 1
        b = kw["json"]
        assert all(max(x) < 900 for x in b["series"]), "a future-dated row reached a context"
        q = [[[x[-24 + i % 24] - 1, x[-24 + i % 24] + 0.3, x[-24 + i % 24] + 1] for i in range(b["horizon"])] for x in b["series"]]
        if s.bad:
            q[-1][-1] = ["not a number", 1.0, 2.0]
        return R({"model": MODEL, "revision": REV, "quantiles": q})


def stored(origin=None):
    cur.execute("SELECT origin, count(*) FROM predictions WHERE model_id = %s GROUP BY origin", (MID,))
    return {o: n for o, n in cur.fetchall() if origin is None or o == origin}


class Down:
    gets = 0

    def get(s, url, **kw):
        Down.gets += 1
        raise ConnectionError("refused")


clean()
try:
    for sid, name, room, indoor, local, kind in [("predict-test-out", "Yard (test)", None, False, True, "sensor"),
                                                 ("predict-test-in", "Indoor kit (test)", "Kids (test)", True, True, "sensor"),
                                                 ("predict-test-new", "New kit", "Studio (test)", True, True, "sensor"),
                                                 ("predict-test-peer", "Neighbour", None, False, True, "peer"),
                                                 ("predict-test-far", "Far", None, False, False, "sensor")]:
        cur.execute("INSERT INTO sensors (sensor_id, source, name, room, lat, lon, indoor, local, kind) "
                    "VALUES (%s, %s, %s, %s, -8.8, 115.1, %s, %s, %s)", (sid, SRC, name, room, indoor, local, kind))
    for metric, role, unit in (("pm25", "ambient", "µg/m³"), ("temp", "ambient", "°C"), ("noise", "ambient", "dB"),
                               ("bme_iaq", "index", None), ("fc_temp", "ambient", "°C")):
        cur.execute("INSERT INTO channel_roles (source, metric, role, unit, declared_by) VALUES (%s, %s, %s, %s, 'test')",
                    (SRC, metric, role, unit))
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    rows = []
    for h in range(1, 60 * 24 + 1):
        ts = now - timedelta(hours=h)
        v = 10 + 4 * math.sin(ts.hour / 24 * 2 * math.pi) + (ts.day % 5)
        for sid in ("predict-test-out", "predict-test-in", "predict-test-peer", "predict-test-far"):
            for metric in ("pm25", "temp", "bme_iaq", "fc_temp"):
                rows.append((ts, sid, metric, v))
        if h <= 9 * 24:
            rows.append((ts, "predict-test-new", "pm25", v))          # nine days old; `noise` it never reported
    rows.append((now + timedelta(hours=30), "predict-test-out", "pm25", 999.0))      # a forecast row, dated ahead
    cur.executemany("INSERT INTO readings_1h_done (bucket, sensor_id, metric, mean, min, max, n) VALUES (%s, %s, %s, %s, %s, %s, 12)",
                    [(a, b, c, d, d, d) for a, b, c, d in rows])
    today = datetime.now(ZoneInfo(TZ)).date()

    # what series() reads: not a peer, not a far sensor, not an index metric, not fc_, not a row dated ahead
    ser = {k for k in adapter.series(cur, adapter._since(today)) if k[0].startswith("predict-test-")}
    assert ser == {("predict-test-out", "pm25"), ("predict-test-out", "temp"), ("predict-test-in", "pm25"),
                   ("predict-test-in", "temp"), ("predict-test-new", "pm25")}, ser
    print("  ok: series() leaves out a peer, a non-local sensor, an index metric, an fc_ metric and a future-dated row")

    # 60 days: today's origin and the 28 before it, once
    r = adapter.run(cur, HC(), today, TZ)
    assert r["state"] == "ok" and r["model_id"] == MID and r["filled"] == 29 and HC.posts == 29, (r, HC.posts)
    r2 = adapter.run(cur, HC(), today, TZ)
    assert r2["filled"] == 0 and HC.posts == 29, (r2, HC.posts)
    print("  ok: run makes 29 forecast calls on 60 days of data and a second run makes none")

    # the hourly gate, with the container down
    whole = stored()
    assert len(whole) == 29 and whole[today] >= 5 * 48 and all(n % 48 == 0 for n in whole.values()), whole
    print("  ok: every stored origin is whole: 48 hours for each series that had a context")

    # an insert that fails half-way leaves nothing for that origin: one transaction per origin
    cur.execute("DELETE FROM predictions WHERE model_id = %s AND origin = %s", (MID, today))
    h = HC()
    h.bad = True
    failed = False
    try:
        adapter.run(cur, h, today, TZ)
    except Exception:  # noqa: BLE001 — psycopg refuses the text in a real column
        failed = True
    assert failed and stored(today) == {}, "a cut origin left part of its rows"
    print("  ok: an origin whose insert fails stores none of its rows")

    # the time budget: a fetch stops between origins, clears last_try, and the next polls finish the job
    cur.execute("DELETE FROM predictions WHERE model_id = %s AND origin > %s", (MID, today - timedelta(days=5)))
    cur.execute("UPDATE models SET last_try = NULL WHERE model_id = %s", (MID,))
    calls = HC.posts
    adapter._clock = lambda: (HC.posts - calls) * 40.0                # each forecast call takes 40 s
    first = adapter.fetch(HC())
    assert first == ([], []) and HC.posts - calls == 2 and len(stored()) == 26, (HC.posts - calls, len(stored()))
    cur.execute("SELECT last_try FROM models WHERE model_id = %s", (MID,))
    assert cur.fetchone()[0] is None, "a cut fetch leaves last_try clear for the next poll"
    out = adapter.fetch(HC())
    while out == ([], []):
        out = adapter.fetch(HC())
    assert out[0][0]["sensor_id"] == "predict" and stored() == whole, stored()
    cur.execute("SELECT last_try FROM models WHERE model_id = %s", (MID,))
    assert cur.fetchone()[0] is not None, "the run that finished keeps last_try"
    import time  # noqa: E402
    adapter._clock = time.monotonic
    print("  ok: the budget cuts a fetch between origins; the next polls carry on and only the last returns the line")

    cur.execute("DELETE FROM predictions WHERE model_id = %s AND origin = %s", (MID, today))
    cur.execute("UPDATE models SET last_try = NULL WHERE model_id = %s", (MID,))
    d = Down()
    assert adapter.fetch(d) == ([], []) and Down.gets == 1, Down.gets
    adapter.fetch(d)
    assert Down.gets == 1, "a second fetch within the hour made another call"
    cur.execute("UPDATE models SET last_try = now() - interval '61 minutes' WHERE model_id = %s", (MID,))
    adapter.fetch(d)
    assert Down.gets == 2, Down.gets
    print("  ok: with the container down, fetch asks once, then not again within the hour, then once after 61 minutes")

    # GET /predict, real SQL
    adapter.run(cur, HC(), today, TZ)
    spec = importlib.util.spec_from_file_location("predict_routes_pg", os.path.join(ROOT, "packs/predict/routes.py"))
    routes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(routes)
    routes._health = lambda: {"ready": True, "model": MODEL, "revision": REV, "error": None}
    j = routes.predict()
    mine = {(r["sensor"], r["metric"]): r for r in j["rows"] if r["sensor"] in ("Yard (test)", "Kids (test)", "Studio (test)")}
    assert j["state"] == "ok" and set(mine) == {("Yard (test)", "pm25"), ("Yard (test)", "temp"), ("Kids (test)", "pm25"), ("Kids (test)", "temp"),
                                                ("Studio (test)", "pm25")}, sorted(mine)
    assert not [k for k in mine if k[1] in ("noise", "bme_iaq", "fc_temp")], "a metric with no data got a row"
    assert mine[("Yard (test)", "pm25")]["unit"] == "µg/m³" and mine[("Kids (test)", "pm25")]["indoor"] is True
    new = mine[("Studio (test)", "pm25")]
    # nine days is enough for a context (7), so it has forecasts, but only a few origins to score: young against the 7
    assert new["why"]["reason"] == "young" and new["why"]["need"] == 7 and 0 < new["why"]["have"] < 7 and not new["today"]["shown"], new
    assert mine[("Yard (test)", "pm25")]["today"]["days"] > 0, "a series with predictions carries its scores"
    print("  ok: GET /predict has a row for each metric with data, none for one the sensor never reported, and the nine-day series is young")
finally:
    clean()
    con.close()
sys.exit(0)
