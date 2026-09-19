"""Every paired station, its week, its baseline and the step.  planetai run season window

The summary line runs the pack's own `record` rule, read out of rules.yml, so the headline number cannot
drift from what the report says. The table above it is the same two windows kept per station instead of
reduced to a median, so a person can see which stations the comparison rests on. Nothing here writes.
"""
import os
import sys

import psycopg
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
RECORD = next(r["sql"] for r in yaml.safe_load(open(f"{HERE}/rules.yml")) if r["id"] == "record")

PER_STATION = """
WITH station_day AS (
  SELECT r.sensor_id, date_trunc('day', r.ts) AS d, avg(r.value) AS pm
  FROM readings r JOIN sensors s USING (sensor_id)
  WHERE s.source = 'baliairdispatch' AND NOT s.local AND NOT s.indoor
    AND r.metric = 'pm25' AND r.ts > now() - interval '68 days'
  GROUP BY 1, 2),
wk AS (
  SELECT sensor_id, percentile_cont(0.5) WITHIN GROUP (ORDER BY pm) AS pm, count(*) AS n
  FROM station_day WHERE d > now() - interval '7 days' GROUP BY 1),
base AS (
  SELECT sensor_id, percentile_cont(0.5) WITHIN GROUP (ORDER BY pm) AS pm, count(*) AS n
  FROM station_day WHERE d <= now() - interval '8 days' GROUP BY 1)
SELECT s.name, round(wk.pm::numeric, 1), round(base.pm::numeric, 1),
       round((wk.pm - base.pm)::numeric, 1), wk.n, base.n,
       (wk.n >= 4 AND base.n >= 20) AS paired
FROM wk JOIN base USING (sensor_id) JOIN sensors s USING (sensor_id)
ORDER BY paired DESC, (wk.pm - base.pm) DESC
"""

with psycopg.connect(os.environ["DATABASE_URL"]) as con, con.cursor() as cur:
    cur.execute(PER_STATION)
    rows = cur.fetchall()
    if not rows:
        sys.exit("season: no ring station has both windows yet. This node needs 68 days of the ring — "
                 "`planetai run nearby backfill 90` fetches it from the archive.")
    print(f"  {'station':<28} {'week':>6} {'usual':>6} {'step':>6}  {'days':>9}")
    for name, week, usual, step, wd, bd, paired in rows:
        print(f"  {name[:28]:<28} {week:>6} {usual:>6} {step:>+6}  {wd:>4}/{bd:<4}"
              f"{'' if paired else '  too thin to pair'}")
    cur.execute(RECORD)
    stations, week, usual, step, days = cur.fetchone()
    if not stations:
        sys.exit("\nseason: nothing pairs yet — every station is short of 4 days this week or 20 in the "
                 "baseline. `planetai run nearby backfill 90`.")
    print(f"\nseason: {stations} paired stations. The week reads {week} µg/m³ against {usual} before it, "
          f"a step of {step:+}. Deepest baseline {days} days.")
    print("`turning` speaks at a step of +8 with the week at 20 µg/m³ or worse, over 3 paired stations.")
print("Bali Air Dispatch, baliairdispatch.com, and the network named in each row.")
