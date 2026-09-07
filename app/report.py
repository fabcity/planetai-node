"""What the node knows about the window it is about to report on, and the report it writes from that on its own.

Two things live here, in this order, because the second is the ruler for everything that comes after it:

  bundle(cur, hours)      every number the node has about the last `hours`, as one JSON-able document
  sheet(bundle, locale)   the node's own report, deterministic, six parts, under a hundred words

The sheet is what a household gets on a node with no model anywhere, which is most nodes. When a model is in the
path it is handed the bundle and the sheet, and anything it writes is checked against the numbers in them before
it is allowed out. So the bundle is the only place a number may come from, and the sheet is what the node falls
back to. Neither may need the network: it is all SQL against this node's own tables.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import index
import settings

log = logging.getLogger("planetai.report")

# What the slow sources mean, in words a model or a person can read. Lived in agent.py until the report needed it
# too; one copy, imported from there.
LABELS = {
    "marine-point": ("sea", {"wave_height_m": "wave height, m", "swell_height_m": "swell height, m", "wave_period_s": "wave period, s",
                             "swell_period_s": "swell period, s", "wave_direction": "waves coming from, degrees (0 north, 90 east, 180 south, 270 west)",
                             "sea_surface_temp": "sea surface temperature, °C"}),
    "om-point": ("weather", {"temp_model": "air temperature, °C", "humidity_model": "humidity, %", "pressure_model": "pressure, hPa",
                             "wind_speed": "wind speed, km/h", "wind_direction": "wind coming from, degrees", "precipitation": "rain this hour, mm"}),
    "cams-point": ("satellite_air", {"pm25_model": "PM2.5 the model estimates for the district, µg/m³", "pm10_model": "PM10, µg/m³", "o3": "ozone, µg/m³",
                                     "no2": "nitrogen dioxide, µg/m³", "co": "carbon monoxide, µg/m³", "dust": "dust, µg/m³", "uv_index": "UV index", "aod": "aerosol optical depth"}),
    "place-point": ("place", {"sat_buildings": "buildings the satellite sees within the radius (Google Open Buildings, confidence ≥ 0.65)",
                              "sat_confidence": "mean detection confidence of those (0-1)", "osm_building_coverage": "share of the satellite's buildings that OpenStreetMap has drawn (0-1)",
                              "sat_buildings_yearly": "building count in the latest year of the temporal dataset; use `history` for the 2016-2023 series",
                              "sat_height_m_yearly": "mean building height, m, latest year",
                              "buildings": "buildings within the radius (OpenStreetMap)", "built_share": "share of the ground covered by buildings (0-1)",
                              "commercial_share": "share of buildings that are shops, offices, hotels (0-1)", "businesses_per_km2": "mapped businesses per km²",
                              "poi_food": "places to eat on the map", "poi_retail": "shops and markets on the map", "poi_education": "schools on the map (zero often means unmapped)",
                              "poi_health": "clinics, doctors, pharmacies on the map", "poi_worship": "temples, mosques, churches on the map", "poi_lodging": "hotels, villas, guesthouses on the map",
                              "poi_services": "banks, post, police, fuel on the map", "roads_km": "kilometres of road", "green_share": "share of the ground that is green (0-1)",
                              "nearest_school_m": "walk to the nearest mapped school, m", "nearest_health_m": "walk to the nearest mapped clinic or pharmacy, m",
                              "nearest_market_m": "walk to the nearest mapped market or minimarket, m", "nearest_worship_m": "walk to the nearest place of worship, m"}),
    "ee-point": ("land", {"built_frac": "share of the surrounding km that is built-up (0-1)", "tree_frac": "share that is trees (0-1)", "crop_frac": "share that is crops (0-1)",
                          "water_frac": "share that is water (0-1)", "ndvi_median": "greenness index (NDVI, -1..1)", "night_lights": "night-time light radiance", "land_change_score": "how much the land changed since the year before (0 = none)"}),
}
POINTS = tuple(LABELS)

# How far a metric has to move across the window before the node calls it a change rather than noise. The digest
# has used ±3 for PM2.5 since v0.24; the rest are that rule read across to their own units. A metric with no entry
# gets 5% of its own range in the window, which is a guess that at least scales.
TREND = {"pm25": 3.0, "pm25_raw": 3.0, "pm10": 5.0, "pm1": 2.0, "temp": 0.5, "humidity": 3.0,
         "pressure": 0.3, "noise": 3.0, "light": 50.0, "eco2": 100.0, "tvoc": 50.0, "aqi": 5.0}

# A model with a 4k context is handed this document. 64 kB is what the smallest rung can hold and still answer.
MAX_BYTES = 64 * 1024

# WHO 2021 24-hour guideline and interim target 1. The same two numbers the rules, the digest and the dashboard use.
CLEAN, ACT = 15.0, 35.0


def _tz() -> str:
    return os.getenv("NODE_TZ", "").strip() or "UTC"


def _local_now() -> datetime:
    try:
        return datetime.now(ZoneInfo(_tz()))
    except Exception:  # noqa: BLE001
        return datetime.now(timezone.utc)


SERIES_SQL = """
WITH win AS (
  SELECT r.sensor_id, r.metric, r.bucket, r.mean, r.min AS lo, r.max AS hi, r.n
    FROM readings_1h r
   WHERE r.bucket > now() - make_interval(hours => %(h)s)
), agg AS (
  SELECT sensor_id, metric, min(bucket) AS t0, max(bucket) AS t1,
         min(lo) AS lo, max(hi) AS hi, sum(n)::int AS n,
         sum(mean * n) / nullif(sum(n), 0) AS mean,
         sum(mean * n) FILTER (WHERE bucket <  now() - make_interval(secs => %(half_s)s))
           / nullif(sum(n) FILTER (WHERE bucket <  now() - make_interval(secs => %(half_s)s)), 0) AS mean_first,
         sum(mean * n) FILTER (WHERE bucket >= now() - make_interval(secs => %(half_s)s))
           / nullif(sum(n) FILTER (WHERE bucket >= now() - make_interval(secs => %(half_s)s)), 0) AS mean_last
    FROM win GROUP BY 1, 2
), hrs AS (
  SELECT DISTINCT extract(hour FROM bucket)::int AS h FROM win
), base AS (
  -- the same local hours on each of the previous seven days, one mean per day. The session time zone is NODE_TZ,
  -- so extract(hour) and ::date are already this household's hours and days, not UTC's.
  SELECT r.sensor_id, r.metric, r.bucket::date AS d, sum(r.mean * r.n) / nullif(sum(r.n), 0) AS m
    FROM readings_1h r
   WHERE r.bucket <= now() - make_interval(hours => %(h)s)
     AND r.bucket >  now() - make_interval(hours => %(h)s) - interval '7 days'
     AND extract(hour FROM r.bucket)::int IN (SELECT h FROM hrs)
   GROUP BY 1, 2, 3
), bstat AS (
  SELECT sensor_id, metric, avg(m) AS bmean, stddev_samp(m) AS bsd, count(*)::int AS ndays
    FROM base GROUP BY 1, 2
)
SELECT a.sensor_id, a.metric, a.t0, a.t1, a.lo, a.hi, a.n, a.mean, a.mean_first, a.mean_last,
       s.name, s.local, s.indoor, s.kind, b.ndays, b.bmean,
       CASE WHEN b.ndays >= 3 AND b.bsd > 0 THEN (a.mean - b.bmean) / b.bsd END AS notability
  FROM agg a JOIN sensors s USING (sensor_id) LEFT JOIN bstat b USING (sensor_id, metric)
 ORDER BY abs(coalesce(CASE WHEN b.ndays >= 3 AND b.bsd > 0 THEN (a.mean - b.bmean) / b.bsd END, 0)) DESC,
          a.sensor_id, a.metric
"""

OBS_SQL = """
SELECT o.sensor_id, o.metric, o.value, o.ts,
       (SELECT r.value FROM readings r
         WHERE r.sensor_id = o.sensor_id AND r.metric = o.metric AND r.ts <= now() - interval '24 hours'
         ORDER BY r.ts DESC LIMIT 1) AS day_ago
  FROM observations o
 WHERE o.sensor_id = ANY(%(points)s)
 ORDER BY o.sensor_id, o.metric
"""

ALERTS_SQL = """
SELECT a.id, a.ts, a.rule_id, a.sensor_id, a.level, split_part(a.text, E'\\n', 1) AS line,
       EXISTS (SELECT 1 FROM actions x WHERE x.alert_id = a.id) AS acted
  FROM alerts a
 WHERE a.ts > now() - make_interval(hours => %(h)s) AND a.rule_id NOT LIKE 'briefing%%'
 ORDER BY a.ts DESC
"""

OPEN_ACT_SQL = """
SELECT a.id, a.ts, a.rule_id, a.sensor_id, split_part(a.text, E'\\n', 1) AS line
  FROM alerts a
 WHERE a.level = 'act' AND a.ts > now() - interval '24 hours'
   AND NOT EXISTS (SELECT 1 FROM actions x WHERE x.alert_id = a.id)
 ORDER BY a.ts DESC LIMIT 5
"""

# A sensor silent for three days has no row in `stats` at all (it looks back 24 hours), so "quiet" has to be asked
# of `sensors` and answered by the absence of a fresh row, not by a large silent_minutes.
QUIET_SQL = """
SELECT s.sensor_id, s.name,
       (SELECT round(extract(epoch FROM now() - max(r.ts)) / 60) FROM readings r WHERE r.sensor_id = s.sensor_id) AS silent_minutes
  FROM sensors s
 WHERE s.local
   AND NOT EXISTS (SELECT 1 FROM stats t WHERE t.sensor_id = s.sensor_id AND t.silent_minutes < 180)
 ORDER BY s.sensor_id
"""

# Where every sensor stands right now, from the same view the rules read. The window says what happened; this says
# whether it is over. Part four of the sheet ("the kitchen is back under 35") is this against the rule's threshold.
NOW_SQL = """
SELECT sensor_id, name, metric, indoor, local, kind,
       round(last::numeric, 2) AS last, round(mean_15m::numeric, 2) AS mean_15m,
       round(mean_1h::numeric, 2) AS mean_1h, round(silent_minutes) AS silent_minutes
  FROM stats ORDER BY local DESC, indoor DESC, sensor_id, metric
"""

PREV_SQL = "SELECT id, ts, text, cells, window_hours, held_quiet FROM reports WHERE sent ORDER BY ts DESC LIMIT 1"


def _trend(row: dict) -> str:
    """rising / falling / steady, from the second half of the window against the first."""
    a, b = row.get("mean_first"), row.get("mean_last")
    if a is None or b is None:
        return "steady"
    lo, hi = row.get("lo"), row.get("hi")
    span = (float(hi) - float(lo)) if lo is not None and hi is not None else 0.0
    step = TREND.get(row["metric"], max(span * 0.05, 1e-9))
    d = float(b) - float(a)
    return "rising" if d > step else "falling" if d < -step else "steady"


def _f(v, d=1):
    return None if v is None else round(float(v), d)


def bundle(cur, hours: int, held_hours: int = 0) -> dict:
    """Every number the node has about the last `hours`, as one JSON-able document. SQL only: no source is polled
    and nothing leaves the machine. `held_hours` are the extra hours folded in from a report quiet hours held.

    Read as planetai_ro wherever the pack pattern allows, so a query here cannot write and cannot see `settings`.
    """
    hours = int(hours) + int(held_hours)
    loc = _local_now()
    b: dict = {"meta": {
        "node": os.getenv("NODE_NAME", "node"), "locale": settings.get("ALERT_LOCALE", "en") or "en",
        "tz": _tz(), "local_time": loc.strftime("%H:%M"), "local_date": loc.strftime("%Y-%m-%d"),
        "local_weekday": loc.strftime("%A"), "local_hour": loc.hour,
        "window_hours": hours, "held_hours": int(held_hours), "folds_a_held_report": bool(held_hours),
        "truncated": 0,
    }}

    p = {"h": hours, "half_s": hours * 1800}      # make_interval(hours =>) wants an integer; half the window in seconds does not
    rows = index.run_ro(cur, SERIES_SQL, p)
    b["series"] = [{
        "sensor_id": r["sensor_id"], "metric": r["metric"], "name": r["name"], "local": r["local"],
        "indoor": r["indoor"], "kind": r["kind"],
        "start": r["t0"].isoformat() if r["t0"] else None, "end": r["t1"].isoformat() if r["t1"] else None,
        "min": _f(r["lo"]), "max": _f(r["hi"]), "mean": _f(r["mean"]), "n": r["n"],
        "trend": _trend(r), "notability": _f(r["notability"], 2),
        "usual": _f(r["bmean"]), "baseline_days": r["ndays"] or 0,
    } for r in rows]

    b["observations"] = []
    for r in index.run_ro(cur, OBS_SQL, {"points": list(POINTS)}):
        group, labels = LABELS.get(r["sensor_id"], (r["sensor_id"], {}))
        b["observations"].append({"group": group, "sensor_id": r["sensor_id"], "metric": r["metric"],
                                  "means": labels.get(r["metric"], r["metric"]), "value": _f(r["value"], 2),
                                  "day_ago": _f(r["day_ago"], 2), "at": r["ts"].isoformat() if r["ts"] else None})

    b["now"] = [{"sensor_id": r["sensor_id"], "name": r["name"], "metric": r["metric"], "indoor": r["indoor"],
                 "local": r["local"], "kind": r["kind"], "last": _f(r["last"], 2), "mean_15m": _f(r["mean_15m"], 2),
                 "mean_1h": _f(r["mean_1h"], 2), "silent_minutes": int(r["silent_minutes"]) if r["silent_minutes"] is not None else None}
                for r in index.run_ro(cur, NOW_SQL)]

    b["alerts"] = [{"id": r["id"], "at": r["ts"].isoformat(), "rule": r["rule_id"], "sensor_id": r["sensor_id"],
                    "level": r["level"], "line": r["line"], "acted": r["acted"]}
                   for r in index.run_ro(cur, ALERTS_SQL, p)]
    b["open_act"] = [{"id": r["id"], "at": r["ts"].isoformat(), "rule": r["rule_id"], "sensor_id": r["sensor_id"],
                      "line": r["line"]} for r in index.run_ro(cur, OPEN_ACT_SQL)]
    b["sensors_quiet"] = [{"sensor_id": r["sensor_id"], "name": r["name"],
                           "silent_minutes": int(r["silent_minutes"]) if r["silent_minutes"] is not None else None}
                          for r in index.run_ro(cur, QUIET_SQL)]

    b["rho"] = {"now": index.rho(cur), "week_ago": index.rho(cur, days_ago=7)}

    # the previous report, and the cells it carried, so this one can say which numbers moved
    cur.execute(PREV_SQL)
    prev = cur.fetchone()
    b["previous"] = None if not prev else {"id": prev["id"], "at": prev["ts"].isoformat(), "text": prev["text"],
                                           "window_hours": prev["window_hours"]}
    was = {c["id"]: c.get("value") for c in (prev or {}).get("cells") or []}
    b["cells"] = []
    try:
        for c in index.cells(cur):
            v = c.get("value")
            b["cells"].append({"id": c["cell"], "value": v, "unit": c.get("unit", ""),
                               "provenance": c.get("state", "partial"),
                               "changed": None if c["cell"] not in was else was[c["cell"]] != v})
    except Exception as e:  # noqa: BLE001 — a broken pack cell must not cost the household its report
        log.warning("cells unavailable for the report: %s", e)

    try:
        import agent
        b["health"] = agent.health_check()
    except Exception as e:  # noqa: BLE001
        b["health"] = {"ok": None, "checks": [], "error": type(e).__name__}
        log.warning("health check unavailable for the report: %s", e)

    return _fit(b)


def _fit(b: dict) -> dict:
    """Keep the document under MAX_BYTES by dropping the least notable series first — they are already sorted, so
    the ones that go are the ones the report would not have mentioned. meta.truncated says how many went."""
    while len(json.dumps(b, default=str).encode()) > MAX_BYTES and b.get("series"):
        b["series"].pop()
        b["meta"]["truncated"] += 1
    if b["meta"]["truncated"]:
        log.info("report bundle over %d kB: dropped %d series", MAX_BYTES // 1024, b["meta"]["truncated"])
    return b
