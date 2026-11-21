"""GET /predict: this node's own series, forecast, beside how often the forecast beat the repeated day.

Mounted by app/packs.py::routers() and answered 404 while PACKS_ENABLED lists packs and not this one; with
PREDICT_MODEL blank (the pack's switch, blank on every node until `planetai models pull`) it answers state "off" and asks
no container. In no `share:` list, so app/main.py's _share_level answers it only to a node token or this machine. Reads
what the nightly run stored (adapter.py) and asks the models container only whether it is ready; scores are computed
here, on read, and never stored.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter

router = APIRouter()

_spec = importlib.util.spec_from_file_location("planetai_pack_predict_adapter_for_routes", Path(__file__).with_name("adapter.py"))
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)  # type: ignore[union-attr]
core = adapter.core

META_SQL = """SELECT s.sensor_id, c.metric, COALESCE(NULLIF(s.room, ''), s.name, s.sensor_id), s.indoor, c.unit
  FROM sensors s JOIN channel_roles c ON c.source = s.source AND c.role = 'ambient'
  WHERE s.local AND s.kind <> 'peer' AND c.metric NOT LIKE %s"""
BLANK = dict.fromkeys(("low", "high", "model", "naive", "days", "shown"))


def _health():
    try:
        return httpx.get(adapter.MODELS_URL + "/health", timeout=2).json()
    except Exception:  # noqa: BLE001 — a container that is not there is a state, not an error
        return None


def _day(sc: dict, rng) -> dict:
    shown = bool(sc["shown"] and rng)
    low, high = rng if shown else (None, None)
    return {"low": low, "high": high, "model": sc["model"], "naive": sc["naive"], "days": sc["days"], "shown": shown}


def _row(meta, sc, pred, origin, pts):
    """One series. `why` says why nothing is shown: "sparse" when it is old enough for a context and has none (too
    many hours missing, or a sensor gone quiet); "waiting" when it has one and today's forecast is not stored yet;
    "young" with the days it has against the days it needs; "naive-closer" when both days lost."""
    sid, metric, sensor, indoor, unit = meta
    row = {"sensor": sensor, "indoor": bool(indoor), "metric": metric, "unit": unit}
    age = (adapter._now() - min(pts)).days if pts else 0
    if not pred:
        if age < core.MIN_CONTEXT_DAYS:
            why = {"reason": "young", "have": age, "need": core.MIN_DAYS}
        elif core.context(pts, origin) is None:
            why = {"reason": "sparse"}
        else:
            why = {"reason": "waiting"}
        if not sc:
            return {**row, "today": dict(BLANK), "tomorrow": dict(BLANK), "why": why}
    d1, d2 = sc["d1"], sc["d2"]
    row["today"], row["tomorrow"] = _day(d1, core.day_range(pred, origin, 1)), _day(d2, core.day_range(pred, origin, 2))
    if not pred:
        return {**row, "why": why}
    if row["today"]["shown"] or row["tomorrow"]["shown"]:
        why = None
    elif min(d1["days"], d2["days"]) >= core.MIN_SCORED:
        why = {"reason": "naive-closer"}
    else:   # the page reads each day's own count; this is the nearer of the days still short
        why = {"reason": "young", "have": max(d for d in (d1["days"], d2["days"]) if d < core.MIN_SCORED),
               "need": core.MIN_SCORED}
    return {**row, "why": why}


@router.get("/predict")
def predict():
    tz = os.getenv("NODE_TZ") or "UTC"
    today = adapter._now().astimezone(ZoneInfo(tz)).date()
    if not (os.getenv("PREDICT_MODEL") or "").strip():
        return {"state": "off", "model": None, "origin": today.isoformat(), "rows": []}
    h = _health()
    if h is None:
        return {"state": "no-answer", "model": None, "origin": today.isoformat(), "rows": []}
    if not (h.get("ready") and h.get("model")):
        return {"state": "no-model", "model": None, "origin": today.isoformat(), "rows": []}
    rev = h.get("revision") or ""
    mid = f"{h['model']}@{rev}"
    origin = core.origin_utc(today, tz)
    with adapter._cursor() as cur:
        cur.execute(META_SQL, ("fc\\_%",))
        metas = {(m[0], m[1]): m for m in cur.fetchall()}
        sc = adapter.scores(cur, mid, today, tz)
        stored = adapter._stored(cur, mid, today)
        pts = adapter.series(cur, adapter._since(today))
    # a series is a pair that has data: the join above is every metric the sensor's source declares, reported or not
    rows = [_row(m, sc.get(k), stored.get(k, {}).get(today, {}), origin, pts.get(k, {}))
            for k, m in metas.items() if k in sc or pts.get(k)]
    rows.sort(key=lambda r: (r["indoor"], r["sensor"], r["metric"]))
    return {"state": "ok" if rows else "young", "origin": today.isoformat(), "rows": rows,
            "model": {"name": h["model"], "revision": rev[:8], "adapted": False}}
