"""The one-time cut (schema 0.68): the past rows of the figures a node now measures from the middle of its cell.

main.CUT_MARK, main.CUT_ROWS and main.EXPORT_ALERTS_SQL are replayed on DuckDB: the rows the cut removes from `readings`
and `readings_1h_done`, the rows it keeps, a second run that changes nothing, and the export's alert text left out
before the cut. The sensors half (JSONB) runs on a real database in tests/test_cut_pg.py.

Run: PYTHONPATH=app python3 tests/test_cut.py
"""
import os
import sys
import time

os.environ.setdefault("DATABASE_URL", "postgresql://unused/never-connected")
os.environ.setdefault("PACKS_DIR", "packs")
try:
    import duckdb
except ImportError:
    print("  - the cut's replay skipped (pip install duckdb)")
    sys.exit(0)
import settings  # noqa: E402
settings._cache = {"at": time.time() + 1e9, "rows": {}}
import main  # noqa: E402

GONE = ["nearest_school_m", "nearest_health_m", "nearest_market_m", "nearest_worship_m",
        "fires_nearest_km", "fires_nearest_bearing", "fires_upwind_km", "fires_upwind_bearing",
        "fires_local_24h", "fires_region_24h", "fires_local_upwind", "fires_region_upwind", "frp_local_mw", "frp_region_mw",
        "river_m"]
assert sorted(main.CUT_METRICS) == sorted(GONE), sorted(set(main.CUT_METRICS) ^ set(GONE))
assert sorted(main.CUT_WHOLE) == ["large_plant_km", "substation_km"], main.CUT_WHOLE

c = duckdb.connect()
c.execute("CREATE TABLE data_cuts (name TEXT PRIMARY KEY, cut_at TIMESTAMPTZ NOT NULL DEFAULT now())")
c.execute("CREATE TABLE readings (ts TIMESTAMPTZ, sensor_id TEXT, metric TEXT, value DOUBLE)")
c.execute("CREATE TABLE readings_1h_done (bucket TIMESTAMPTZ, sensor_id TEXT, metric TEXT, mean DOUBLE, min DOUBLE, max DOUBLE, n BIGINT)")
before = [("place-point", m, 948.3) for m in GONE[:4]] + [("firms-fires", m, 75.1) for m in GONE[4:14]] + [
    ("hydro-point", "river_m", 4980.0),
    ("energy-grid", "substation_km", 3.27), ("energy-grid", "large_plant_km", 12.0),   # the second is whole: it stays
    ("place-point", "buildings", 2459.0), ("firms-fires", "fire_wind_from_deg", 315.0),  # not listed: they stay
    ("ag-1", "pm25", 9.1)]
for sid, m, v in before:
    c.execute("INSERT INTO readings VALUES (TIMESTAMPTZ '2026-11-27 10:00:00+00', ?, ?, ?)", [sid, m, v])
    c.execute("INSERT INTO readings_1h_done VALUES (TIMESTAMPTZ '2026-11-27 10:00:00+00', ?, ?, ?, ?, ?, 1)", [sid, m, v, v, v])


def run():
    if not c.execute(main.CUT_MARK).fetchall():
        return False
    for sql in main.CUT_ROWS:
        c.execute(sql)
    return True


assert run(), "the first run cuts"
kept = sorted(c.execute("SELECT sensor_id, metric FROM readings").fetchall())
assert kept == [("ag-1", "pm25"), ("energy-grid", "large_plant_km"), ("firms-fires", "fire_wind_from_deg"),
                ("place-point", "buildings")], kept
assert sorted(c.execute("SELECT sensor_id, metric FROM readings_1h_done").fetchall()) == kept, "the hourly means go with them"
print(f"  cut: {len(before) - len(kept)} rows of the listed figures removed from readings and readings_1h_done, {len(kept)} kept")

# written after the cut, by the code that measures from the middle: a second run finds the mark and removes nothing
c.execute("INSERT INTO readings VALUES (TIMESTAMPTZ '2026-11-29 10:00:00+00', 'firms-fires', 'fires_nearest_km', 76.0)")
c.execute("INSERT INTO readings VALUES (TIMESTAMPTZ '2026-11-29 10:00:00+00', 'energy-grid', 'substation_km', 3.0)")
assert not run(), "the second run must find the mark"
assert c.execute("SELECT count(*) FROM readings").fetchone()[0] == len(kept) + 2, "rows written after the cut stay"
assert c.execute("SELECT count(*) FROM data_cuts").fetchone()[0] == 1
print("  cut: a second run changes nothing, and rows written after it stay")

# the export: an alert raised before the cut travels without its text, one raised after keeps it
c.execute("CREATE TABLE alerts (id BIGINT, ts TIMESTAMPTZ, rule_id TEXT, sensor_id TEXT, level TEXT, text TEXT)")
c.execute("UPDATE data_cuts SET cut_at = TIMESTAMPTZ '2026-11-28 12:00:00+00'")
c.execute("INSERT INTO alerts VALUES (1, TIMESTAMPTZ '2026-11-28 09:00:00+00', 'fire/fire_near', 'firms-fires', 'info', 'before'),"
          " (2, TIMESTAMPTZ '2026-11-28 15:00:00+00', 'fire/fire_near', 'firms-fires', 'info', 'after')")
sql = "SELECT text, after_cut FROM (" + main.EXPORT_ALERTS_SQL.replace("%s::date + 1", "CAST('2026-11-29' AS DATE)").replace(
    "%s::date", "CAST('2026-11-28' AS DATE)") + ") AS x"            # no timestamp comes back: DuckDB would want pytz for it
got = c.execute(sql).fetchall()
assert [t for t, _ in got] == ["before", "after"] and [a for _, a in got] == [False, True], got
c.execute("DELETE FROM data_cuts")
assert all(not r[-1] for r in c.execute(sql).fetchall()), "with no cut recorded, no alert text travels"
print("  export: an alert's text travels only when it was raised after the cut")

# the first poll of a process runs it before any adapter writes, once; a database that fails is asked again next poll
ran, polled = [], []


class _Cur:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, *a): ran.append(sql)
    def fetchall(self): return [{"name": "cell-middle"}] if ran[-1] == main.CUT_MARK else []


class _Con(_Cur):
    def cursor(self): return _Cur()
    def transaction(self): return _Cur()


_db, _poll = main.db, main.poll_once
main.db = lambda: (_ for _ in ()).throw(RuntimeError("down"))
main.poll_once = lambda hc: polled.append(len(ran))
main.state.pop("cut", None)
main.poll_sources()
assert polled == [0] and not main.state.get("cut"), "a database that is down still lets the poll run, and the cut waits"
main.db = lambda: _Con()
main.poll_sources(); main.poll_sources()
assert ran == [main.CUT_MARK, *main.CUT_ROWS, *main.CUT_SENSORS] and polled == [0, len(ran), len(ran)], (ran, polled)
main.db, main.poll_once = _db, _poll
print("  poll: the cut runs before the first poll's adapters, once a process")
