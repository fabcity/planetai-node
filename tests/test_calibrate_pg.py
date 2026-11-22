"""GET /calibrate on a real database: its four reads meet the real sensors, channel_roles, stats and readings_1h.

Inside one transaction that is rolled back: two sensors 30 m apart and 30 days of hourly readings (the better one is
2 + 1.5 x the other), then the route function itself, with db pointed at that connection. Needs a Postgres with
init.sql applied, at RHO_PG_URL (CI's lint job starts one); without it the suite skips.
Run: RHO_PG_URL=postgresql://planetai:x@127.0.0.1:5432/planetai PYTHONPATH=app PACKS_DIR=packs python3 tests/test_calibrate_pg.py
"""
import contextlib
import importlib.util
import os
import sys
import time

url = os.getenv("RHO_PG_URL")
if not url:
    print("  - calibrate on a real database skipped (set RHO_PG_URL to a Postgres with init.sql applied)")
    sys.exit(0)
import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

sys.path.insert(0, "app")
os.environ.pop("NODE_TZ", None)
os.environ.setdefault("DATABASE_URL", url)
import settings  # noqa: E402
ROWS = {"CALIBRATE_PAIRS": "pg-a pg-b pm25 2026-01-01"}
settings._cache = {"at": time.time() + 1e9, "rows": ROWS}
import db  # noqa: E402

spec = importlib.util.spec_from_file_location("calibrate_routes_pg", "packs/calibrate/routes.py")
RT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RT)

con = psycopg.connect(url, row_factory=dict_row)          # one transaction, rolled back: nothing stays
cur = con.cursor()


db.db = lambda: contextlib.nullcontext(con)
RT.q = db.q
count = lambda: (cur.execute("SELECT count(*) AS n FROM readings"), cur.fetchone()["n"])[1]  # noqa: E731
cur.execute("INSERT INTO channel_roles (source, metric, role, comparable, unit, declared_by) "
            "VALUES ('pg-test', 'pm25', 'ambient', TRUE, 'ug', 'test') ON CONFLICT (source, metric) DO UPDATE "
            "SET role = 'ambient', comparable = TRUE")
for sid, dm in (("pg-a", 0), ("pg-b", 30), ("pg-c", 400), ("pg-d", 410)):
    cur.execute("INSERT INTO sensors (sensor_id, source, name, lat, lon, indoor, local, kind, scale, meta) "
                "VALUES (%s, 'pg-test', %s, -8.8 + %s / 111320.0, 115.1, FALSE, TRUE, 'sensor', 'community', '{}')",
                (sid, sid.upper(), dm))
cur.execute("""INSERT INTO readings (ts, sensor_id, metric, value)
  SELECT now() - make_interval(hours => h), s.sensor_id,
         'pm25', CASE WHEN s.sensor_id = 'pg-b' THEN 2 + 1.5 * (5 + (h * 7) % 11) ELSE 5 + (h * 7) % 11 END
  FROM generate_series(1, 30 * 24) h CROSS JOIN sensors s WHERE s.sensor_id IN ('pg-a', 'pg-b', 'pg-c', 'pg-d')""")

before = count()
j = RT.calibrate()
assert j["state"] == "ok" and len(j["rows"]) == 1, j
row = j["rows"][0]
assert row["shown"] is True and row["why"] is None and row["metres"] == 30, row
assert row["line"]["b"] == 1.5 and row["line"]["a"] == 2.0 and row["reference"]["own"] is True, row
assert row["corrected"] is not None and row["unit"] == "ug", row
assert [(x["a"]["id"], x["b"]["id"]) for x in j["could"]] == [("pg-c", "pg-d")], j["could"]
ROWS["CALIBRATE_PAIRS"] = "pg-c pg-d pm25 2026-01-01"
assert [(x["a"]["id"], x["b"]["id"]) for x in RT.calibrate()["could"]] == [("pg-a", "pg-b")], "the other pair could be named"
assert count() == before, "the route wrote nothing"
con.rollback()
print("calibrate pg: every check passed")
