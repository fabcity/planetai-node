"""The report the node writes itself, and the bundle it writes it from.

The fixture below is a real bundle, taken from a node seeded with eight days shaped like node #1: a kitchen that
cooks at six, a porch, a public reference down the road, a radio that stopped talking four days ago, and the
three model points. It is the ruler for everything downstream — the model's rewrite is checked against these
numbers and nothing else — so it is written out here in full rather than generated, and it is read by eye.
"""
import json, os, sys

os.environ.setdefault("DATABASE_URL", "postgresql://x/x")
os.environ.setdefault("NODE_TZ", "Asia/Makassar")
os.environ.setdefault("NODE_NAME", "bayu-2")
sys.path.insert(0, "app")

import report

# ---------------------------------------------------------------- the fixture: a pot on the stove, an hour ago
FIXTURE = {
    "meta": {"node": "bayu-2", "locale": "en", "tz": "Asia/Makassar", "local_time": "18:00",
             "local_date": "2026-09-07", "local_weekday": "Monday", "local_hour": 18,
             "window_hours": 6, "held_hours": 0, "folds_a_held_report": False, "truncated": 0},
    "series": [
        {"sensor_id": "sc-kitchen", "metric": "pm25", "name": "Bayu 2 - Kitchen", "local": True, "indoor": True,
         "kind": "sensor", "start": "2026-09-07T13:00:00+08:00", "end": "2026-09-07T17:00:00+08:00",
         "min": 5.4, "max": 206.3, "mean": 60.1, "n": 20, "trend": "falling", "notability": 12.4,
         "usual": 5.7, "baseline_days": 7},
        {"sensor_id": "sc-kitchen", "metric": "temp", "name": "Bayu 2 - Kitchen", "local": True, "indoor": True,
         "kind": "sensor", "start": "2026-09-07T13:00:00+08:00", "end": "2026-09-07T17:00:00+08:00",
         "min": 29.5, "max": 32.2, "mean": 30.9, "n": 20, "trend": "falling", "notability": -2.37,
         "usual": 31.0, "baseline_days": 7},
        {"sensor_id": "sc-porch", "metric": "pm25", "name": "Bayu 2 - Porch", "local": True, "indoor": False,
         "kind": "sensor", "start": "2026-09-07T13:00:00+08:00", "end": "2026-09-07T17:00:00+08:00",
         "min": 4.5, "max": 7.5, "mean": 5.8, "n": 20, "trend": "steady", "notability": -0.92,
         "usual": 6.0, "baseline_days": 7},
        {"sensor_id": "cams-point", "metric": "pm25_model", "name": "CAMS model point", "local": False,
         "indoor": False, "kind": "model", "start": "2026-09-07T15:00:00+08:00", "end": "2026-09-07T15:00:00+08:00",
         "min": 11.5, "max": 11.5, "mean": 11.5, "n": 1, "trend": "steady", "notability": -0.64,
         "usual": 12.2, "baseline_days": 7},
    ],
    "now": [
        {"sensor_id": "sc-kitchen", "name": "Bayu 2 - Kitchen", "metric": "pm25", "indoor": True, "local": True,
         "kind": "sensor", "last": 16.49, "mean_15m": 17.2, "mean_1h": 17.21, "silent_minutes": 2},
        {"sensor_id": "sc-kitchen", "name": "Bayu 2 - Kitchen", "metric": "temp", "indoor": True, "local": True,
         "kind": "sensor", "last": 29.53, "mean_15m": 29.6, "mean_1h": 29.77, "silent_minutes": 2},
        {"sensor_id": "sc-kitchen", "name": "Bayu 2 - Kitchen", "metric": "humidity", "indoor": True, "local": True,
         "kind": "sensor", "last": 66.12, "mean_15m": 66.4, "mean_1h": 67.91, "silent_minutes": 2},
        {"sensor_id": "sc-porch", "name": "Bayu 2 - Porch", "metric": "pm25", "indoor": False, "local": True,
         "kind": "sensor", "last": 7.27, "mean_15m": 7.1, "mean_1h": 6.45, "silent_minutes": 2},
        {"sensor_id": "bad-pa-1", "name": "Jimbaran PA", "metric": "pm25", "indoor": False, "local": False,
         "kind": "sensor", "last": 8.84, "mean_15m": 8.8, "mean_1h": 8.91, "silent_minutes": 2},
    ],
    "observations": [
        {"group": "satellite_air", "sensor_id": "cams-point", "metric": "pm25_model",
         "means": "PM2.5 the model estimates for the district, µg/m³", "value": 11.46, "day_ago": 12.13,
         "at": "2026-09-07T15:00:00+08:00"},
        {"group": "satellite_air", "sensor_id": "cams-point", "metric": "uv_index", "means": "UV index",
         "value": 7.78, "day_ago": 0.0, "at": "2026-09-07T15:00:00+08:00"},
        {"group": "sea", "sensor_id": "marine-point", "metric": "swell_height_m", "means": "swell height, m",
         "value": 1.87, "day_ago": 2.1, "at": "2026-09-07T15:00:00+08:00"},
        {"group": "weather", "sensor_id": "om-point", "metric": "precipitation", "means": "rain this hour, mm",
         "value": 0.0, "day_ago": 2.4, "at": "2026-09-07T15:00:00+08:00"},
    ],
    "alerts": [
        {"id": 1, "at": "2026-09-07T15:00:00+08:00", "rule": "air-quality/indoor_pm25_high",
         "sensor_id": "sc-kitchen", "level": "act",
         "line": "🏠😷 The air inside at Bayu 2 - Kitchen is unhealthy right now.", "acted": False},
        {"id": 2, "at": "2026-09-07T15:00:00+08:00", "rule": "air-quality/indoor_spike",
         "sensor_id": "sc-kitchen", "level": "warn",
         "line": "📈🏠 Something just changed the air at Bayu 2 - Kitchen.", "acted": False},
    ],
    "open_act": [{"id": 1, "at": "2026-09-07T15:00:00+08:00", "rule": "air-quality/indoor_pm25_high",
                  "sensor_id": "sc-kitchen",
                  "line": "🏠😷 The air inside at Bayu 2 - Kitchen is unhealthy right now."}],
    "sensors_quiet": [{"sensor_id": "msh-quiet", "name": "Garden radio", "silent_minutes": 5821}],
    "rho": {"now": {"window_days": 30, "days_ago": 0, "alerts_act": 2, "acted": 1, "rho": 0.5, "median_minutes": 60},
            "week_ago": {"window_days": 30, "days_ago": 7, "alerts_act": 0, "acted": 0, "rho": None,
                         "median_minutes": None}},
    "previous": None,
    "cells": [{"id": "Governance|Community", "value": 0.5,
               "unit": "rho — share of act-level alerts answered within 24h (30d)", "provenance": "partial",
               "changed": None}],
    "health": {"ok": True, "checks": [{"check": "polled in the last 15 min", "ok": True, "fix": None}]},
}

# A node at minute five: the schema is there, the first poll has not landed, and there is nothing to say.
EMPTY = {
    "meta": {"node": "casa-providencia", "locale": "es", "tz": "America/Santiago", "local_time": "06:03",
             "local_date": "2026-09-07", "local_weekday": "Monday", "local_hour": 6, "window_hours": 6,
             "held_hours": 0, "folds_a_held_report": False, "truncated": 0},
    "series": [], "now": [], "observations": [], "alerts": [], "open_act": [], "sensors_quiet": [],
    "rho": {"now": {"window_days": 30, "days_ago": 0, "alerts_act": 0, "acted": 0, "rho": None,
                    "median_minutes": None},
            "week_ago": {"window_days": 30, "days_ago": 7, "alerts_act": 0, "acted": 0, "rho": None,
                         "median_minutes": None}},
    "previous": None, "cells": [], "health": {"ok": True, "checks": []},
}

# ---------------------------------------------------------------- rising, falling, steady
def tr(metric, first, last, lo=0.0, hi=10.0):
    return report._trend({"metric": metric, "mean_first": first, "mean_last": last, "lo": lo, "hi": hi})

assert tr("pm25", 7, 40) == "rising" and tr("pm25", 40, 7) == "falling"
assert tr("pm25", 7, 9) == "steady", "PM2.5 moves by 3 or it has not moved; the digest has used that since v0.24"
assert tr("pm25", 7, 10.5) == "rising"
assert tr("temp", 29.0, 29.3) == "steady" and tr("temp", 29.0, 29.8) == "rising", "half a degree indoors is a change"
assert tr("humidity", 60, 62) == "steady" and tr("humidity", 60, 64) == "rising"
# a metric with no line of its own gets five per cent of its own range, which at least scales
assert tr("gas_resistance", 100, 100.4, lo=100, hi=110) == "steady"
assert tr("gas_resistance", 100, 101, lo=100, hi=110) == "rising"
# one reading in the window has no halves, and a flat line has no range: neither may divide by zero
assert tr("pm25", None, 12) == "steady" and tr("gas_resistance", 5, 5, lo=5, hi=5) == "steady"
print("a metric moved when it moved further than that metric's own noise")

# ---------------------------------------------------------------- 64 kB, and what goes first
big = json.loads(json.dumps(FIXTURE))
big["series"] = [dict(FIXTURE["series"][0], sensor_id=f"s{i}", notability=round(20 - i * 0.01, 2)) for i in range(400)]
fitted = report._fit(big)
assert len(json.dumps(fitted, default=str).encode()) <= report.MAX_BYTES, "the document must fit what a small rung holds"
assert fitted["meta"]["truncated"] > 0 and fitted["series"], "it drops series, not the whole document"
assert fitted["series"][0]["sensor_id"] == "s0", "the most notable series is the one that stays"
assert len(fitted["series"]) + fitted["meta"]["truncated"] == 400, "truncated must count what actually went"
small = report._fit(json.loads(json.dumps(FIXTURE)))
assert small["meta"]["truncated"] == 0 and len(small["series"]) == len(FIXTURE["series"])
print("a bundle over 64 kB drops its least notable series and says how many")

# ---------------------------------------------------------------- the queries, and the one copy of LABELS
SQL = {k: v for k, v in vars(report).items() if k.endswith("_SQL")}
assert set(SQL) >= {"SERIES_SQL", "NOW_SQL", "OBS_SQL", "ALERTS_SQL", "OPEN_ACT_SQL", "QUIET_SQL"}, sorted(SQL)
for name, sql in SQL.items():
    head = sql.strip().split()[0].upper()
    assert head in ("SELECT", "WITH"), f"{name} starts with {head}"
    for w in ("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "GRANT"):
        assert w not in sql.upper(), f"{name} contains {w}; these run as planetai_ro and read only"
    assert "settings" not in sql.lower(), f"{name} reads settings; planetai_ro cannot, and a report must not"
assert set(report.POINTS) == set(report.LABELS), "POINTS is the LABELS keys, not a second list"
_agent = open("app/agent.py").read()
assert "from report import LABELS" in _agent and "LABELS = {" not in _agent, "one copy of LABELS, in report.py"
for sid, (group, labels) in report.LABELS.items():
    assert group and labels, sid
print("every query reads, none of them can see settings, and LABELS has one home")
