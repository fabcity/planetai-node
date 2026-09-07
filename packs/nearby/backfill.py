"""Fetch each ring station's hourly history from the archive.  planetai run nearby backfill [days]

Off by default: BAD_BACKFILL_DAYS=0. This is a large fetch against someone else's server, so it is asked for, not
scheduled. History is for the cards and for reading a week back; the rules run off the last hour and never need it.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import httpx
import psycopg

sys.path.insert(0, "/app")
import sources  # noqa: E402

BASE = "https://baliairdispatch.com/api/v1/measurements"
days = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.getenv("BAD_BACKFILL_DAYS", "0"))
if days <= 0:
    sys.exit("nearby: backfill is off. `planetai run nearby backfill 7`, or set BAD_BACKFILL_DAYS.")

hc = httpx.Client(timeout=120, headers={"user-agent": "planetai-node"})
with psycopg.connect(os.environ["DATABASE_URL"]) as con, con.cursor() as cur:
    cur.execute("SELECT sensor_id FROM sensors WHERE source = 'baliairdispatch' AND NOT local ORDER BY 1")
    ids = [r[0] for r in cur.fetchall()]
    if not ids:
        sys.exit("nearby: no ring stations stored yet. Let the node poll once first.")
    now = datetime.now(timezone.utc)
    total = 0
    for sid in ids:
        station, cursor, n, seen = sid[4:], None, 0, set()
        # Keyset pagination. An hourly row carries pm25, its min and max, and the sample count — and nothing
        # else: pm10, pm1 and pm25_raw are on /latest only, so a backfilled station has PM2.5 history and no
        # more. Verified against the archive on 7 September.
        while True:
            p = {"station": station, "interval": "hourly", "limit": 5000,
                 "from": (now - timedelta(days=days)).strftime("%Y-%m-%d"), "to": now.strftime("%Y-%m-%d")}
            if cursor:
                p["cursor"] = cursor
            d = hc.get(BASE, params=p).json()
            rows = d.get("measurements") or []
            batch = []
            for row in rows:
                ts = sources._iso(row.get("observed_at") or row.get("date"))
                if ts is not None and row.get("pm25") is not None:
                    batch.append((ts, sid, "pm25", float(row["pm25"])))
            if batch:
                cur.executemany("INSERT INTO readings (ts, sensor_id, metric, value) VALUES (%s,%s,%s,%s)"
                                " ON CONFLICT DO NOTHING", batch)
                con.commit(); n += len(batch)
            cursor = d.get("next_cursor")
            # stop on an empty page, on no cursor, and on a cursor that stopped moving — a server that keeps
            # handing back the same one must not spin this loop forever against someone else's machine.
            if not rows or not cursor or cursor in seen:
                break
            seen.add(cursor)
        print(f"  {sid:<26} {n:>7} readings")
        total += n
print(f"\nnearby: {total} readings over {days} days for {len(ids)} stations. Gaps stay gaps; nothing was filled.")
print("Bali Air Dispatch, baliairdispatch.com, and the network named in each row.")
