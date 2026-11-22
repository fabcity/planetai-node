"""GET /calibrate: each sensor a keeper put beside a better one, corrected against it while the line is closer.

Mounted by app/packs.py::routers() and answered 404 while PACKS_ENABLED lists packs and not this one; with
CALIBRATE_PAIRS blank (the pack's switch) it answers state "off" and reads nothing. In no `share:` list. Nothing is
stored but that one setting: the line, the checks and the verdict are worked out here, on each call, by
calibrate_core.py. The route only reads.
"""
from __future__ import annotations

import importlib.util
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter

import packs
import settings
import sources
from db import q

router = APIRouter()

_spec = importlib.util.spec_from_file_location("planetai_pack_calibrate_core", Path(__file__).with_name("calibrate_core.py"))
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)  # type: ignore[union-attr]

SENSORS = "SELECT sensor_id, source, name, lat, lon, indoor, kind, meta FROM sensors WHERE sensor_id = ANY(%s)"
ROLES = "SELECT source, metric, unit FROM channel_roles WHERE role = 'ambient' AND comparable"
NEAR = """SELECT DISTINCT s.sensor_id, s.source, s.name, s.lat, s.lon, s.indoor, st.metric
  FROM sensors s JOIN stats st ON st.sensor_id = s.sensor_id
  WHERE s.kind = 'sensor' AND s.lat IS NOT NULL AND s.lon IS NOT NULL"""
HOURLY = """SELECT sensor_id, bucket, mean FROM readings_1h
  WHERE sensor_id = ANY(%s) AND metric = %s AND bucket >= %s AND bucket < %s"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _r(v):
    return None if v is None else round(float(v), 2)


def _midnight(d: date) -> datetime:
    return datetime.combine(d, time(), timezone.utc)


def _metres(a, b):
    if a and b and None not in (a["lat"], a["lon"], b["lat"], b["lon"]):
        return sources.metres(a["lat"], a["lon"], b["lat"], b["lon"])
    return None


def _could(roles, station_sources, taken):
    seen, out = {}, []
    for r in q(NEAR):
        if r["source"] not in station_sources and (r["source"], r["metric"]) in roles:
            seen.setdefault(r["sensor_id"], []).append(r)
    ids = sorted(seen)
    for i, x in enumerate(ids):
        for y in ids[i + 1:]:
            a, b = seen[x][0], seen[y][0]
            m = _metres(a, b)
            both = sorted({r["metric"] for r in seen[x]} & {r["metric"] for r in seen[y]})
            if both and bool(a["indoor"]) == bool(b["indoor"]) and m <= core.MAX_METRES and frozenset((x, y)) not in taken:
                # ponytail: pm25 first because it is the only metric this was measured on; a list per pair if that changes
                metric = "pm25" if "pm25" in both else both[0]
                out.append({"a": {"id": x, "name": a["name"]}, "b": {"id": y, "name": b["name"]}, "metric": metric, "metres": round(m)})
    return out


# ponytail: worked out on every call; hold it for the hour if a node names dozens of pairs
@router.get("/calibrate")
def calibrate():
    text = (settings.get("CALIBRATE_PAIRS", "") or "").strip()
    if not text:
        return {"state": "off", "rows": [], "could": []}
    now, tz = _now(), os.getenv("NODE_TZ") or "UTC"
    entries = core.parse_pairs(text, now.astimezone(ZoneInfo(tz)).date())
    ids = sorted({i for e in entries if e["pair"] for i in (e["pair"].sensor, e["pair"].reference)})
    have = {r["sensor_id"]: r for r in q(SENSORS, ids)} if ids else {}
    roles = {(r["source"], r["metric"]): r["unit"] for r in q(ROLES)}
    station_sources = {p["source"] for p in packs.stations()}
    rows, taken = [], set()
    for e in entries:
        p = e["pair"]
        if p is None:
            rows.append({"entry": e["entry"], "shown": False, "why": {"reason": "malformed", "problem": e["problem"]}})
            continue
        s, ref = have.get(p.sensor), have.get(p.reference)
        taken.add(frozenset((p.sensor, p.reference)))
        metres = _metres(s, ref)
        meta = (ref or {}).get("meta")
        meta = meta if isinstance(meta, dict) else {}
        row = {"entry": e["entry"], "sensor": {"id": p.sensor, "name": (s or {}).get("name")},
               "reference": {"id": p.reference, "name": (ref or {}).get("name"),
                             "own": bool(ref) and ref["source"] not in station_sources,
                             "network": meta.get("network"), "official": meta.get("official"), "from_index": meta.get("from_index")},
               "metric": p.metric, "unit": roles.get((s["source"], p.metric)) if s else None,
               "metres": None if metres is None else round(metres), "since": p.since.isoformat(),
               "until": p.until.isoformat() if p.until else None,
               "measured": None, "corrected": None, "hour": None, "line": None, "paired_hours": 0, "last_paired": None,
               "checked": None, "shown": False, "why": None}
        why = core.refuse(p, s, ref, station_sources, roles, metres)
        if why:
            row["why"] = {"reason": "refused", **why}
            if why["test"] == "no-channel":
                row["why"]["source"] = (s if why["side"] == "sensor" else ref)["source"]
            rows.append(row)
            continue
        # finished hours only: the still-filling one is never read. paired() clips the pairs to until, so the
        # sensor's own newest finished hour is "measured" whatever until says
        end = now.replace(minute=0, second=0, microsecond=0)
        start = max(_midnight(p.since - timedelta(days=1)), end - timedelta(days=core.READ_DAYS))
        x, y = {}, {}
        for h in q(HOURLY, [p.sensor, p.reference], p.metric, start, end):
            if h["mean"] is not None:
                (x if h["sensor_id"] == p.sensor else y)[datetime.fromisoformat(h["bucket"])] = h["mean"]
        w = core.work(p, x, y, now, tz)
        if x:
            newest = max(x)
            row["measured"], row["hour"] = _r(x[newest]), newest.isoformat()
        if w["line"]:
            row["line"] = {"a": _r(w["line"]["a"]), "b": _r(w["line"]["b"]), "hours": w["line"]["hours"]}
        if w["checked"]:
            row["checked"] = {"days": w["checked"]["days"], "measured": _r(w["checked"]["measured"]),
                              "corrected": _r(w["checked"]["corrected"])}
        row.update(paired_hours=w["paired_hours"], shown=w["shown"],
                   last_paired=w["last_paired"].isoformat() if w["last_paired"] else None,
                   why=w["why"] and {k: v.isoformat() if isinstance(v, date) else v for k, v in w["why"].items()})
        if w["shown"] and x:
            row["corrected"] = _r(core.correct(w["line"]["a"], w["line"]["b"], x[max(x)], w["floor0"]))
        rows.append(row)
    return {"state": "ok", "rows": rows, "could": _could(roles, station_sources, taken)}
