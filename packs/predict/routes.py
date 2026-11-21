"""GET /predict: this node's own series, forecast, beside how often the forecast beat the repeated day.

Mounted by app/packs.py::routers() and answered 404 while the pack is off. In no `share:` list, so app/main.py's
_share_level answers it only to a node token or this machine. Reads what the nightly run stored (adapter.py) and asks
the models container only whether it is ready; scores are computed here, on read, and never stored.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter

router = APIRouter()

_spec = importlib.util.spec_from_file_location("planetai_pack_predict_adapter_for_routes", Path(__file__).with_name("adapter.py"))
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)  # type: ignore[union-attr]
core = sys.modules["core"]

META_SQL = """SELECT s.sensor_id, c.metric, COALESCE(NULLIF(s.room, ''), s.name, s.sensor_id), s.indoor, c.unit
  FROM sensors s JOIN channel_roles c ON c.source = s.source AND c.role = 'ambient'
  WHERE s.local AND s.kind <> 'peer' AND c.metric NOT LIKE %s"""
BLANK = dict.fromkeys(("low", "high", "model", "naive", "days", "shown"))


def _health():
    try:
        return httpx.get(os.getenv("MODELS_URL", "http://models:8080") + "/health", timeout=2).json()
    except Exception:  # noqa: BLE001 — a container that is not there is a state, not an error
        return None


def _day(sc: dict, rng) -> dict:
    shown = bool(sc["shown"])
    low, high = rng if shown and rng else (None, None)
    return {"low": low, "high": high, "model": sc["model"], "naive": sc["naive"], "days": sc["days"], "shown": shown}


def _row(meta, sc, pred, origin, have):
    sid, metric, sensor, indoor, unit = meta
    row = {"sensor": sensor, "indoor": bool(indoor), "metric": metric, "unit": unit}
    if not sc:
        return {**row, "today": dict(BLANK), "tomorrow": dict(BLANK), "why": {"reason": "young", "have": have, "need": core.MIN_DAYS}}
    d1, d2 = sc["d1"], sc["d2"]
    row["today"], row["tomorrow"] = _day(d1, core.day_range(pred, origin, 1)), _day(d2, core.day_range(pred, origin, 2))
    if d1["shown"] or d2["shown"]:
        why = None
    elif min(d1["days"], d2["days"]) >= core.MIN_SCORED:
        why = {"reason": "naive-closer"}
    else:
        why = {"reason": "young", "have": max(d1["days"], d2["days"]), "need": core.MIN_SCORED}
    return {**row, "why": why}


@router.get("/predict")
def predict():
    tz = os.getenv("NODE_TZ") or "UTC"
    today = adapter._now().astimezone(ZoneInfo(tz)).date()
    h = _health()
    if h is None:
        return {"state": "no-answer", "model": None, "origin": today.isoformat(), "rows": []}
    if not (h.get("ready") and h.get("model")):
        return {"state": "no-model", "model": None, "origin": today.isoformat(), "rows": []}
    mid = f"{h['model']}@{h['revision']}"
    origin = core.origin_utc(today, tz)
    with adapter._cursor() as cur:
        cur.execute(META_SQL, ("fc\\_%",))
        metas = {(m[0], m[1]): m for m in cur.fetchall()}
        sc = adapter.scores(cur, mid, today, tz)
        stored = adapter._stored(cur, mid, today)
        pts = adapter.series(cur, adapter._since(today)) if any(k not in sc for k in metas) else {}
    rows = [_row(m, sc.get(k), stored.get(k, {}).get(today, {}), origin,
                 (adapter._now() - min(pts[k])).days if pts.get(k) else 0) for k, m in metas.items()]
    rows.sort(key=lambda r: (r["indoor"], r["sensor"], r["metric"]))
    return {"state": "ok" if rows else "young", "origin": today.isoformat(), "rows": rows,
            "model": {"name": h["model"], "revision": h["revision"][:8], "adapted": False}}
