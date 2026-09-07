"""What the ring looks like right now: who is in it, how far, and when each last reported.  planetai run nearby status"""
import os
import sys

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, "/app")
import sources  # noqa: E402

LAT, LON = float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"])
with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as con, con.cursor() as cur:
    cur.execute("""
        SELECT st.name, st.lat, st.lon, round(st.mean_1h::numeric, 1) AS pm, round(st.silent_minutes::numeric) AS silent
        FROM stats st JOIN sensors sn USING (sensor_id)
        WHERE sn.source = 'baliairdispatch' AND NOT st.local AND NOT st.indoor AND st.kind = 'sensor'
          AND st.metric = 'pm25' AND st.mean_1h IS NOT NULL AND st.lat IS NOT NULL
        ORDER BY st.silent_minutes""")
    ring = cur.fetchall()
    cur.execute("""SELECT round(avg(mean_1h)::numeric, 1) AS pm, count(*) AS n FROM stats
                   WHERE local AND NOT indoor AND kind = 'sensor' AND metric = 'pm25' AND mean_1h IS NOT NULL""")
    mine = cur.fetchone()

live = [r for r in ring if r["silent"] is not None and r["silent"] < 120]
print(f"\nThe ring around {os.getenv('NODE_NAME', 'this node')} — {len(live)} of {len(ring)} stations reporting\n")
if not ring:
    print("  No stations stored yet. Is BAD_ENABLED=1? The next poll fetches them.")
for r in ring:
    d = sources.km(LAT, LON, r["lat"], r["lon"])
    age = "quiet" if r["silent"] is None or r["silent"] >= 120 else f"{int(r['silent'])} min ago"
    print(f"  {d:6.2f} km  {str(r['name'])[:44]:<44} {str(r['pm']) + ' ug/m3':>12}  {age}")

if len(live) < 2:
    print("\n  Fewer than two neighbours reporting. This node's readings speak for this address and nothing else.")
elif mine and mine["n"]:
    pms = sorted(r["pm"] for r in live)
    med = pms[len(pms) // 2] if len(pms) % 2 else (pms[len(pms) // 2 - 1] + pms[len(pms) // 2]) / 2
    print(f"\n  Your outdoor sensors: {mine['pm']} ug/m3 over {mine['n']}. The ring's middle: {med} ug/m3.")
else:
    print("\n  No local outdoor sensor, so there is nothing here to compare the ring against.")
print("\nBali Air Dispatch, baliairdispatch.com, and the network named in each row.")
