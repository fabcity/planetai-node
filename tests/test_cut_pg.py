"""The one-time cut (schema 0.68) on a real database: main.cut_once against init.sql's tables.

Rows of the listed figures written before the cut are gone from `readings` and `readings_1h_done`, rows written after
stay, the sensors' old distance keys and the two sea names are rewritten, and a second run changes nothing. Needs a
Postgres with init.sql applied, at RHO_PG_URL (CI's lint job starts one); without it the suite skips. One
transaction, rolled back: nothing stays.
Run: RHO_PG_URL=postgresql://planetai:x@127.0.0.1:5432/planetai PYTHONPATH=app PACKS_DIR=packs python3 tests/test_cut_pg.py
"""
import os
import sys
import time

url = os.getenv("RHO_PG_URL")
if not url:
    print("  - the cut on a real database skipped (set RHO_PG_URL to a Postgres with init.sql applied)")
    sys.exit(0)
os.environ.setdefault("DATABASE_URL", url)
import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402
import settings  # noqa: E402
settings._cache = {"at": time.time() + 1e9, "rows": {}}
import main  # noqa: E402

con = psycopg.connect(url, row_factory=dict_row)
cur = con.cursor()
cur.execute("DELETE FROM data_cuts WHERE name = 'cell-middle'")      # as before the cut, inside this transaction
SENSORS = [("t-fire", "firms", "NASA FIRMS", None), ("t-place", "openstreetmap", "Around here", None),
           ("t-grid", "energy", "Grid", None),
           ("forecast-bmkg", "forecast-bmkg", "BMKG forecast", '{"attribution": "BMKG", "km_from_node": 0.19, "adm4": "x"}'),
           ("forecast-marine", "forecast-marine", "Open-Meteo Marine forecast, sea cell 5 km off", '{"distance_km": 4.7, "note": "n"}'),
           ("marine-point", "open-meteo-marine", "Sea, 5 km off (-8.79, 115.13)", '{"distance_km": 4.7, "units": {}}'),
           ("hydro-point", "hydro", "Rivers", '{"sentence": "4.9 km to a river", "largest": "23.2 km", "radius_km": 25}'),
           ("bad-x", "baliairdispatch", "Station (IQAir)", '{"km": 3.81, "network": "IQAir"}'),
           ("lab-x", "fablabs-io", "Lab", '{"distance_km": 17.7, "fetched": "2026-11-01T00:00:00+00:00", "slug": "x"}')]
for sid, src, name, meta in SENSORS:
    cur.execute("INSERT INTO sensors (sensor_id, source, name, kind, meta) VALUES (%s, %s, %s, %s, %s::jsonb) "
                "ON CONFLICT (sensor_id) DO UPDATE SET name = EXCLUDED.name, meta = EXCLUDED.meta",
                (sid, src, name, {"lab-x": "facility", "bad-x": "sensor"}.get(sid, "model"), meta))
rows = [("t-fire", "fires_nearest_km", 75.1), ("t-fire", "fires_local_24h", 2.0), ("t-fire", "fire_wind_from_deg", 315.0),
        ("t-place", "nearest_health_m", 948.3), ("t-place", "buildings", 2459.0), ("hydro-point", "river_m", 4980.0),
        ("t-grid", "substation_km", 3.27), ("t-grid", "large_plant_km", 12.0)]
for sid, m, v in rows:
    cur.execute("INSERT INTO readings (ts, sensor_id, metric, value) VALUES (now() - interval '1 day', %s, %s, %s)", (sid, m, v))
    cur.execute("INSERT INTO readings_1h_done (bucket, sensor_id, metric, mean, min, max, n) "
                "VALUES (date_trunc('hour', now() - interval '1 day'), %s, %s, %s, %s, %s, 1)", (sid, m, v, v, v))

assert main.cut_once(cur), "the first run cuts"
mine = "sensor_id IN ('t-fire', 't-place', 't-grid', 'hydro-point')"
cur.execute(f"SELECT sensor_id, metric FROM readings WHERE {mine} ORDER BY 1, 2")
kept = [(r["sensor_id"], r["metric"]) for r in cur.fetchall()]
assert kept == [("t-fire", "fire_wind_from_deg"), ("t-grid", "large_plant_km"), ("t-place", "buildings")], kept
cur.execute(f"SELECT sensor_id, metric FROM readings_1h_done WHERE {mine} ORDER BY 1, 2")
assert [(r["sensor_id"], r["metric"]) for r in cur.fetchall()] == kept, "the hourly means go with them"
cur.execute("SELECT sensor_id, name, meta FROM sensors WHERE sensor_id = ANY(%s)", ([s[0] for s in SENSORS],))
got = {r["sensor_id"]: r for r in cur.fetchall()}
assert got["forecast-bmkg"]["meta"] == {"attribution": "BMKG", "adm4": "x"}, got["forecast-bmkg"]
assert got["forecast-marine"]["meta"] == {"note": "n"} and got["forecast-marine"]["name"] == "Open-Meteo Marine forecast, nearest sea cell"
assert got["marine-point"]["meta"] == {"units": {}} and got["marine-point"]["name"] == "Sea, nearest cell (-8.79, 115.13)", got["marine-point"]
assert got["hydro-point"]["meta"] == {"radius_km": 25}, got["hydro-point"]
assert got["bad-x"]["meta"] == {"network": "IQAir"}, got["bad-x"]
assert got["lab-x"]["meta"] == {"slug": "x"}, "a lab loses its distance and the fetch stamp, so the next poll reads it again"
print("  cut: the listed rows are gone from readings and readings_1h_done, the old distance keys and sea names rewritten")

cur.execute("INSERT INTO readings (ts, sensor_id, metric, value) VALUES (now(), 't-fire', 'fires_nearest_km', 76)")
assert not main.cut_once(cur), "a second run finds the mark"
cur.execute("SELECT count(*) AS n FROM readings WHERE sensor_id = 't-fire' AND metric = 'fires_nearest_km'")
assert cur.fetchone()["n"] == 1, "a row written after the cut stays"
cur.execute("SELECT cut_at <= now() AS ok FROM data_cuts WHERE name = 'cell-middle'")
assert cur.fetchone()["ok"]
con.rollback()
print("  cut: a second run changes nothing; the cut's time is kept in data_cuts")
