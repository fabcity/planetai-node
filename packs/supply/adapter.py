"""Where this place's water comes from: the keeper's stated sources, each set beside the water works on the public map.

Reads water works, pumping stations, reservoirs, dams, wells, towers, tanks and pipelines from OpenStreetMap via
Overpass once every SUPPLY_REFRESH_DAYS, and keeps the last read when Overpass does not answer. Every poll it reads
SUPPLY_SOURCES again, gives each source an origin (the point typed, or the nearest work of that name), its distance
from this node and, when the hydro pack holds basins, whether the origin lies in this node's basin.

kind='model', scale='city'. Never an Index cell, never an alert.
"""
from __future__ import annotations

import json
import logging
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import supply_core as core  # noqa: E402  (a path load, see core.sibling)

log = logging.getLogger("planetai.pack.supply")
osm = core.sibling("osm")
SID = "supply-point"
USER_AGENT = "planetai-node/supply (+https://planetai.fab.city)"
ATTRIBUTION = "© OpenStreetMap contributors, ODbL, via Overpass"
HOLDS_RANK = {"steady": 0, "fails at times": 1, "fails often": 2}
RETRY_HOURS = 6        # after a failed read, the map is left alone this long
ALWAYS_KEPT = ("works", "pumping", "reservoir", "dam")
_state = {"warned": False}


def _out() -> Path:
    return Path(os.getenv("PACK_OUT", "/app/out")) / "supply"


def _aoi() -> tuple[float, float, float]:
    return float(os.environ["NODE_LAT"]), float(os.environ["NODE_LON"]), float(os.getenv("SUPPLY_RADIUS_KM") or 25)


def _metres(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    dy = (b_lat - a_lat) * 111320.0
    dx = (b_lon - a_lon) * 111320.0 * math.cos(math.radians((a_lat + b_lat) / 2))
    return math.hypot(dx, dy)


def result() -> dict:
    """What the last fetch kept, or {} when none has run or it ran for a point this node no longer is (as hydro's)."""
    try:
        r = json.loads((_out() / "result.json").read_text())
        lat, lon, km = _aoi()
        if r.get("radius_km") != km or _metres(r["lat"], r["lon"], lat, lon) > max(km * 10.0, 25.0):
            return {}
        return r
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def _works(hc, lat: float, lon: float, km: float, now: datetime) -> tuple[list[dict], str | None]:
    """The works on the public map, from the cache while it is fresh, and from the cache when the read fails."""
    days = max(1, int(os.getenv("SUPPLY_REFRESH_DAYS") or 30))
    cache = _out() / "osm.json"
    saved = None
    try:
        saved = json.loads(cache.read_text())
        if (saved["radius_km"] != km or _metres(saved["lat"], saved["lon"], lat, lon) > max(km * 10.0, 25.0)
                or not isinstance(saved["works"], list)):
            saved = None
    except (OSError, ValueError, KeyError, TypeError):
        saved = None
    if saved:
        try:
            if now - datetime.fromisoformat(saved["fetched_at"]) < timedelta(days=days):
                return saved["works"], saved["fetched_at"]
        except (ValueError, TypeError):
            pass
    tried = _out() / "tried.json"
    try:
        if now - datetime.fromisoformat(json.loads(tried.read_text())["at"]) < timedelta(hours=RETRY_HOURS):
            return (saved["works"], saved["fetched_at"]) if saved else ([], None)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    dlat, dlon = km / 111.32, km / (111.32 * max(math.cos(math.radians(lat)), 0.01))
    q = osm.QUERY.format(s=lat - dlat, w=lon - dlon, n=lat + dlat, e=lon + dlon)
    url = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        r = hc.post(url, data={"data": q}, timeout=120, headers=headers)
        r.raise_for_status()
        works = osm.parse(r.json())
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"fetched_at": now.isoformat(), "lat": lat, "lon": lon, "radius_km": km, "works": works}))
        tried.unlink(missing_ok=True)
        return works, now.isoformat()
    except Exception as exc:  # noqa: BLE001
        log.warning("supply: overpass read failed: %s", exc)
        try:
            tried.parent.mkdir(parents=True, exist_ok=True)
            tried.write_text(json.dumps({"at": now.isoformat()}))
        except OSError:
            pass
        return (saved["works"], saved["fetched_at"]) if saved else ([], None)


def _hydro():
    """hydro's own basins and its point-in-polygon, or (None, {}) when that pack is off or has kept nothing."""
    try:
        import packs  # noqa: PLC0415  the loader reads PACKS_DIR at import

        h = packs.module("hydro", "adapter")
        return h.inside, h.result() or {}
    except Exception as exc:  # noqa: BLE001
        log.info("supply: no hydro basins (%s)", type(exc).__name__)
        return None, {}


def fetch(hc):
    """Contract: (sensors, readings). The statement is read on every poll; the map only when the cache is old."""
    try:
        lat, lon, km = _aoi()
    except (KeyError, ValueError):
        if not _state["warned"]:
            log.info("supply: NODE_LAT and NODE_LON are not set, nothing to do")
            _state["warned"] = True
        return [], []
    now = datetime.now(timezone.utc)
    works, fetched_at = _works(hc, lat, lon, km, now)
    inside, hydro = _hydro()
    stated = []
    for s in core.parse_sources(os.getenv("SUPPLY_SOURCES", "")):
        o = None if s["problem"] else core.resolve(s, works, lat, lon)
        if o:
            o["basin"] = core.basin_of(o["lat"], o["lon"], hydro, inside) if inside else None
        stated.append(dict(s, origin=o))
    counts: dict[str, int] = {}
    for w in works:
        counts[w["kind"]] = counts.get(w["kind"], 0) + 1
    kept = [w for w in works if w["name"] or w["kind"] in ALWAYS_KEPT]
    r = {"lat": lat, "lon": lon, "radius_km": km, "fetched_at": fetched_at, "stated": stated, "works": kept,
         "counts": counts, "attribution": [ATTRIBUTION]}
    try:
        _out().mkdir(parents=True, exist_ok=True)
        (_out() / "result.json").write_text(json.dumps(r))
    except OSError as exc:
        log.warning("supply: could not keep the result: %s", exc)
    good = [s for s in stated if not s["problem"]]
    rows = [(now, SID, "supply_sources", len(good))]
    if good and good[0]["origin"]:
        o = good[0]["origin"]
        rows.append((now, SID, "supply_origin_km", round(osm.km(lat, lon, o["lat"], o["lon"]), 1)))
    if good and good[0]["holds"]:
        rows.append((now, SID, "supply_first_holds", HOLDS_RANK[good[0]["holds"]]))
    meta = {"radius_km": km, "attribution": ATTRIBUTION, "works": len(works), "fetched_at": fetched_at}
    sensor = {"sensor_id": SID, "source": "supply", "name": f"Water supply within {km:g} km (OpenStreetMap)",
              "lat": lat, "lon": lon, "indoor": False, "local": False,
              "kind": "model", "scale": "city", "cadence": "P1D", "meta": meta}
    return [sensor], rows
