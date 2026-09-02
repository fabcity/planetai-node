"""Index brick. Two things:
  cells()  → fci-cells-v0 rows this node can honestly compute, each with its provenance state
  rho()    → action latency: how fast an alert became a human action, from the actions table

The cell key is 'Pillar|Scale' (canonical, FCI Observations base). State is live | partial | mock and is never
upgraded here or downstream. Bali's Environmental|Community cell has been empty in the canon; node #1 fills it.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

CITY = os.getenv("NODE_CITY", "bali")
SCALE = os.getenv("NODE_SCALE", "community").capitalize()
WHO_24H = 15.0


def _row(cell: str, value, unit: str, source: str, state: str, note: str = "") -> dict:
    return {"city": CITY, "cell": cell, "value": None if value is None else round(float(value), 3), "unit": unit,
            "source": source, "observed_at": datetime.now(timezone.utc).isoformat(), "state": state, "notes": note}


def cells(cur) -> list[dict]:
    out: list[dict] = []
    env = f"Environmental|{SCALE}"

    # Local (ours) PM2.5, last 24h. live if we have ≥ 12 hourly buckets from our own hardware.
    cur.execute("""SELECT avg(mean) AS m, count(*) AS n, count(DISTINCT sensor_id) AS sensors,
                          bool_or(s.indoor) AS any_indoor
                   FROM readings_1h r JOIN sensors s USING (sensor_id)
                   WHERE s.local AND r.metric='pm25' AND r.bucket > now() - interval '24 hours'""")
    r = cur.fetchone()
    if r and r["n"]:
        state = "live" if r["n"] >= 12 else "partial"
        where = "indoor" if r["any_indoor"] else "outdoor"
        out.append(_row(env, r["m"], f"µg/m³ PM2.5 (24h mean, {where}, local sensors)", "planetai-node", state,
                        f"{r['sensors']} local sensor(s), {r['n']} hourly buckets"))

    # Days over WHO 24h guideline in the last 30 days, local outdoor only (indoor never enters an ambient stat).
    cur.execute("""WITH d AS (
                     SELECT (r.bucket AT TIME ZONE %s)::date AS day, avg(r.mean) AS pm
                     FROM readings_1h r JOIN sensors s USING (sensor_id)
                     WHERE s.local AND NOT s.indoor AND r.metric='pm25' AND r.bucket > now() - interval '30 days'
                     GROUP BY 1 HAVING count(*) >= 12)
                   SELECT count(*) FILTER (WHERE pm > %s) AS over, count(*) AS days FROM d""",
                (os.getenv("NODE_TZ", "UTC"), WHO_24H))
    r = cur.fetchone()
    if r and r["days"]:
        out.append(_row(env, 100.0 * r["over"] / r["days"], "% of days over WHO 24h PM2.5 guideline (30d, local outdoor)",
                        "planetai-node", "live" if r["days"] >= 20 else "partial", f"{r['over']}/{r['days']} days"))

    # Reference (peer observatory) ambient mean — City-scale context, never 'live' because it isn't ours.
    cur.execute("""SELECT avg(mean) AS m, count(DISTINCT sensor_id) AS stations
                   FROM readings_1h r JOIN sensors s USING (sensor_id)
                   WHERE NOT s.local AND NOT s.indoor AND r.metric='pm25' AND r.bucket > now() - interval '24 hours'""")
    r = cur.fetchone()
    if r and r["stations"]:
        out.append(_row("Environmental|City", r["m"], "µg/m³ PM2.5 (24h mean, public reference stations)",
                        "Bali Air Dispatch, baliairdispatch.com (+ upstream networks)", "partial",
                        f"{r['stations']} stations within radius; peer observatory, credited"))

    # Governance|Community: is anyone acting on what the node says. Expressed as ρ (0..1) over 30 days.
    rr = rho(cur)
    if rr["alerts_act"]:
        out.append(_row(f"Governance|{SCALE}", rr["rho"], "ρ — share of act-level alerts acknowledged within 24h (30d)",
                        "planetai-node actions ledger", "partial" if rr["acted"] < 5 else "live",
                        f"{rr['acted']}/{rr['alerts_act']} acted; median detect→act {rr['median_minutes']} min"))
    return out


def rho(cur) -> dict:
    """ρ over the last 30 days: fraction of level='act' alerts that received an 'acknowledged' or 'acted' row within
    24h, plus median detect→act latency in minutes. The address-scale instrument for H0-A."""
    cur.execute("""WITH a AS (SELECT id, ts FROM alerts WHERE level='act' AND ts > now() - interval '30 days'),
                        first_act AS (SELECT alert_id, min(ts) AS t FROM actions WHERE stage IN ('acknowledged','acted') GROUP BY alert_id)
                   SELECT count(a.id) AS alerts_act,
                          count(f.alert_id) FILTER (WHERE f.t - a.ts < interval '24 hours') AS acted,
                          percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM f.t - a.ts)/60) AS median_minutes
                   FROM a LEFT JOIN first_act f ON f.alert_id = a.id""")
    r = cur.fetchone() or {}
    n, acted = int(r.get("alerts_act") or 0), int(r.get("acted") or 0)
    return {"window_days": 30, "alerts_act": n, "acted": acted, "rho": round(acted / n, 3) if n else None,
            "median_minutes": round(float(r["median_minutes"])) if r.get("median_minutes") is not None else None}
