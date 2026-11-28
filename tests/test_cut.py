"""The one-time cut (schema 0.69): the past rows of the figures a node now measures from the middle of its cell.

main.CUT_MARK and main.CUT_ROWS are replayed on DuckDB: the rows the cut removes from `readings` and `readings_1h_done`,
the rows it keeps and a second run that changes nothing. main.cut_at and main.cut_once on a database with no data_cuts
table, the export's alert text left out before the cut, and the hourly rebuild after it. The sensors half (JSONB) runs
on a real database in tests/test_cut_pg.py.

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

# main.cut_at reads when the cut ran, and None on a database with no cut yet or no data_cuts table at all
from datetime import datetime, timezone  # noqa: E402


class _W:
    """A DuckDB connection as main.db() hands one out: `with db() as con, con.transaction(), con.cursor() as cur`."""
    def __init__(self, c): self.c = c
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def cursor(self): return self
    def transaction(self): return self
    def execute(self, sql, *a): self.c.execute(sql, *a); return self
    def fetchall(self): return self.c.fetchall()


bare = duckdb.connect()                                  # a database older than the data_cuts table
assert main.cut_at(_W(bare)) is None, "no data_cuts table reads as no cut"
c.execute("DELETE FROM data_cuts")
assert main.cut_at(_W(c)) is None, "no cut recorded reads as no cut"
c.execute("INSERT INTO data_cuts (name) VALUES ('cell-middle')")

# the export: an alert raised before the cut travels without its text, one raised after keeps it, and with no cut
# (or no data_cuts table) none does
ALERTS = [{"ts": "2026-11-28T09:00:00+00:00", "rule_id": "fire/fire_near", "level": "info", "sensor_id": "firms-fires", "text": "before"},
          {"ts": "2026-11-28T15:00:00+00:00", "rule_id": "fire/fire_near", "level": "info", "sensor_id": "firms-fires", "text": "after"}]
_ex = (main.db, main.q, main.cut_at, main.index.cells, main.index.rho, main._offers)
main.q = lambda sql, *a: [dict(r) for r in ALERTS] if "FROM alerts" in sql else []
main.index.cells, main.index.rho, main._offers = (lambda cur: []), (lambda cur: None), (lambda: [])
main.db = lambda: _W(bare)
assert [a["text"] for a in main.export("2026-11-28")["alerts"]] == [None, None], "a database with no data_cuts table exports no alert text"
main.cut_at = lambda cur: None
assert [a["text"] for a in main.export("2026-11-28")["alerts"]] == [None, None], "with no cut recorded, no alert text travels"
main.cut_at = lambda cur: datetime(2026, 11, 28, 12, tzinfo=timezone.utc)   # DuckDB would want pytz to hand one back
assert [a["text"] for a in main.export("2026-11-28")["alerts"]] == [None, "after"], "only an alert raised after the cut keeps its text"
main.db, main.q, main.cut_at, main.index.cells, main.index.rho, main._offers = _ex
print("  export: an alert's text travels only when it was raised after the cut, and never from a database without one")

# cut_once on a database with no data_cuts table does nothing, and the poll says so once
import logging  # noqa: E402
assert main.cut_once(_W(bare)) is None and bare.execute("SELECT count(*) FROM information_schema.tables").fetchone()[0] == 0
said = []
_h = logging.Handler(); _h.emit = lambda rec: said.append(rec.getMessage())
main.log.addHandler(_h)
_db, _poll = main.db, main.poll_once
main.db, main.poll_once = (lambda: _W(bare)), (lambda hc: None)
main.state.pop("cut", None); main.state.pop("cut_said", None)
main.poll_sources(); main.poll_sources()
main.db, main.poll_once = _db, _poll
main.log.removeHandler(_h)
assert len([m for m in said if "data_cuts" in m]) == 1, said
print("  cut: a database without the data_cuts table is left as it is, said once")

# the first poll of a process runs it before any adapter writes, once; a database that fails is asked again next poll
ran, polled = [], []


class _Cur:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, *a): ran.append(sql)
    def fetchall(self): return [{"name": "cell-middle"}] if ran[-1] == main.CUT_MARK else [{"n": 1}] if ran[-1] == main.CUT_TABLE else []


class _Con(_Cur):
    def cursor(self): return _Cur()
    def transaction(self): return _Cur()


_db, _poll, _hourly = main.db, main.poll_once, main.refresh_hourly
main.db = lambda: (_ for _ in ()).throw(RuntimeError("down"))
main.poll_once = lambda hc: polled.append(len(ran))
main.refresh_hourly = lambda: ran.append("refresh_hourly")
main.state.pop("cut", None)
main.poll_sources()
assert polled == [0] and not main.state.get("cut"), "a database that is down still lets the poll run, and the cut waits"
main.db = lambda: _Con()
main.poll_sources(); main.poll_sources()
# The hourly means are rebuilt right after the cut, so a mean another thread's refresh read from the old rows a moment
# before does not stay. The DuckDB replay cannot show that race: it needs two connections at once.
assert ran == [main.CUT_TABLE, main.CUT_MARK, *main.CUT_ROWS, *main.CUT_SENSORS, "refresh_hourly"] and polled == [0, len(ran), len(ran)], (ran, polled)
ran.clear(); main.state.pop("cut", None)
_Cur.fetchall = lambda self: [{"n": 1}] if ran[-1] == main.CUT_TABLE else []    # the mark is there: the cut ran before
main.poll_sources()
assert ran == [main.CUT_TABLE, main.CUT_MARK], f"no rebuild when the cut did not run: {ran}"
main.db, main.poll_once, main.refresh_hourly = _db, _poll, _hourly
print("  poll: the cut runs before the first poll's adapters, once a process, and the hourly means are rebuilt after it")
