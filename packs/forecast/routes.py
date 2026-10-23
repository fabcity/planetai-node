"""GET /forecast: official and model weather for this point, as the forecast pack stores it.

A route of this pack since 23 Oct 2026; until then app/main.py, moved unchanged. The node mounts it from here
(app/packs.py::routers) and answers 404 while this pack is off. `forecast()` is also what the Wall reads
(app/ask.py::wall_reads), so it stays a plain function the route wraps.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Query

from db import q

router = APIRouter()


@router.get("/forecast")
def forecast(hours: int = Query(24, ge=1, le=72)):
    """Official and model weather for this point: where the wind comes from, when rain is expected, and when the
    forecast was issued. Context for reading this node's own air. The node fetches it; it does not predict."""
    who = q("""SELECT sensor_id, name, lat, lon, meta FROM sensors
               WHERE source IN ('forecast-bmkg','forecast-om','forecast-gap') ORDER BY sensor_id""")
    rows = q("""SELECT sensor_id, ts, metric, value FROM readings
                WHERE sensor_id IN ('forecast-bmkg','forecast-om','forecast-gap')
                  AND ts > now() - interval '3 hours' AND ts < now() + make_interval(hours => %s)
                ORDER BY ts, sensor_id, metric""", hours)
    steps: dict = {}
    for r in rows:
        steps.setdefault((str(r["ts"]), r["sensor_id"]), {})[r["metric"]] = r["value"]
    lat, lon = float(os.getenv("NODE_LAT", 0) or 0), float(os.getenv("NODE_LON", 0) or 0)
    out = {"point": {"lat": lat, "lon": lon},
           "sources": [{"sensor_id": w["sensor_id"], "name": w["name"], "lat": w["lat"], "lon": w["lon"],
                        "issued": (w["meta"] or {}).get("issued"), "fetched": (w["meta"] or {}).get("fetched"),
                        "km_from_node": (w["meta"] or {}).get("km_from_node")} for w in who],
           "hours": [{"ts": k[0], "source": k[1], **v} for k, v in sorted(steps.items())],
           "attribution": ["BMKG (Badan Meteorologi, Klimatologi, dan Geofisika), api.bmkg.go.id",
                           "Open-Meteo, open-meteo.com, CC-BY 4.0 (free tier: non-commercial use only)"]}
    # a forecast for somewhere else is still a forecast, but the card has to say so rather than imply this point
    far = [w for w in out["sources"] if (w.get("km_from_node") or 0) > 10]
    out["far_from_node"] = [{"sensor_id": w["sensor_id"], "km": w["km_from_node"]} for w in far] or None
    return out
