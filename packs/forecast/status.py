"""The next day as the forecast has it: wind, rain, and how old the forecast is.  planetai run forecast status"""
import os
import sys

import psycopg
from psycopg.rows import dict_row

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as con, con.cursor() as cur:
    cur.execute("""SELECT sensor_id, name, meta FROM sensors
                   WHERE source IN ('forecast-bmkg','forecast-om','forecast-gap') ORDER BY sensor_id""")
    who = cur.fetchall()
    if not who:
        sys.exit("forecast: nothing fetched yet. Is FORECAST_BMKG_ADM4 set? `planetai run forecast verify`")
    cur.execute("""SELECT sensor_id, ts, metric, value FROM readings
                   WHERE sensor_id IN ('forecast-bmkg','forecast-om')
                     AND ts > now() AND ts < now() + interval '24 hours'
                   ORDER BY ts, sensor_id, metric""")
    rows = cur.fetchall()

for s in who:
    m = s["meta"] or {}
    issued = m.get("issued") or (f"fetched {m['fetched'][:16]}" if m.get("fetched") else "issue time unknown")
    where = f" · {m['km_from_node']} km from the node" if m.get("km_from_node") is not None else ""
    print(f"  {s['name']}{where}\n      issued {issued}")

by = {}
for r in rows:
    by.setdefault((r["sensor_id"], r["ts"]), {})[r["metric"]] = r["value"]
print(f"\n  The next 24 hours ({len(by)} steps)\n")
print(f"      {'when':<17} {'source':<15} {'wind':>14}  {'rain':>7}  {'temp':>6}")
for (sid, ts), v in sorted(by.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    d = v.get("fc_wind_direction")
    arrow = COMPASS[int((d % 360) / 22.5 + 0.5) % 16] if d is not None else "?"
    ws = v.get("fc_wind_speed")
    print(f"      {ts:%a %d %b %H:%M}  {sid.replace('forecast-', ''):<15} "
          f"{('from ' + arrow + ' ' + str(round(ws)) + ' km/h') if ws is not None else '–':>14}  "
          f"{(str(v.get('fc_rain', 0)) + ' mm'):>7}  {(str(v.get('fc_temp', '–')) + ' C'):>6}")
print("\nBMKG (api.bmkg.go.id). Open-Meteo (open-meteo.com, CC-BY 4.0) when it is on.")
print("This is context for reading your own air. The node fetches it; it does not predict.")
