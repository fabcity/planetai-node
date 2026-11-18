"""GET /wall: everything the Wall's map draws, in one read a screen with no token may make.

The Wall walks out from the house through three node sizes (the base node's seven res-8 cells, the community's seven
res-7, the city's seven res-6) and replays the last 24 hours on each. It runs on a kiosk with no token, so this route
is on the SHARE_LEVEL=open list (app/auth.py), and what it returns is held to R25 (_published_position in main.py):
nothing finer than the house's res-8 cell. So every distance is from that cell's centre, in whole km; every point is
a public thing's (a station, a lab, a power plant) at three decimals at most; and nothing is cut around the house's
own point. Where a pack kept something cut around the point, it is either re-cut around the cell's centre (the
rivers, the basin, the roofs) or left out until it is (the land-change image, whose square is centred on the
house to 10 m). docs/superpowers/specs/2026-11-18-wall-scales-map-design.md in planetai-design is the why.

Each block is null when its pack is off or has nothing yet; the route never fails on a missing pack.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import h3
from fastapi import APIRouter, HTTPException

import packs
import settings
from db import db
from issues.engine import day_buckets

router = APIRouter()

SCALES = (("base", 8), ("community", 7), ("city", 6))
FRESH = timedelta(hours=3)          # the island's file, and each station in it
PLANT_KM = 30
HOURS = {"wind_kmh": ("om-point", "wind_speed"), "wind_from": ("om-point", "wind_direction"),
         "wave_from": ("marine-point", "wave_direction"), "swell_m": ("marine-point", "swell_height_m"),
         "swell_s": ("marine-point", "swell_period_s")}


# ---------------------------------------------------------------- pure builders

def _ring(cid: str) -> list:
    """A cell's boundary as [lon, lat] pairs, closed: h3 leaves the first vertex unrepeated."""
    pts = [[round(lng, 6), round(lat, 6)] for lat, lng in h3.cell_to_boundary(cid)]
    return pts + [pts[0]]


def scales(home: str) -> list[dict]:
    """The three node sizes: the seven-cell rule one resolution up each time (the cell holding the house and the six
    touching it), with the node's own cell at each size marked."""
    out = []
    for k, res in SCALES:
        own = h3.cell_to_parent(home, res)
        cells = [own] + sorted(set(h3.grid_disk(own, 1)) - {own})
        out.append({"k": k, "res": res, "km2": round(sum(h3.cell_area(c, unit="km^2") for c in cells), 1),
                    "cells": [{"id": c, "own": c == own, "ring": _ring(c)} for c in cells]})
    return out


def km_from(centre: tuple[float, float], lon: float, lat: float) -> int:
    """Whole km from the cell's centre ((lon, lat)): a decimal of km beside a public point narrows the house."""
    return round(h3.great_circle_distance((centre[1], centre[0]), (lat, lon), unit="km"))


def hourly(rows, buckets, sensor_id: str, metric: str) -> list[float | None]:
    """One value per bucket, None where the hour has no row."""
    got = {r["bucket"]: r["mean"] for r in rows if r["sensor_id"] == sensor_id and r["metric"] == metric}
    return [None if got.get(b) is None else round(float(got[b]), 2) for b in buckets]


def lonlat(x: float, y: float, epsg: int, near: tuple[float, float]) -> list[float]:
    """UTM metres back to [lon, lat], by surface-heat's own forward projection (Snyder) and its local inverse, with one
    Newton step from the first guess: under a centimetre 7 km from `near` (lat, lon). No pyproj on a node."""
    sh = packs.module("surface-heat", on_only=False)
    fwd = sh.projection(epsg)
    p = sh.local_inverse(fwd, *near)(x, y)
    lat, lon = sh.local_inverse(fwd, *p)(x, y)
    return [round(lon, 6), round(lat, 6)]


def _age(ts, now: datetime) -> timedelta | None:
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    return now - (t if t.tzinfo else t.replace(tzinfo=timezone.utc))


def island(doc: dict | None, now: datetime) -> dict | None:
    """packs/bali-air-dispatch's island-wide stations, null when the file is over 3 h old. Its `at` is when it was
    written, not when the stations read, so each item's own `at` is held to the same 3 h."""
    if not doc or (_age(doc.get("at"), now) or FRESH * 2) > FRESH:
        return None
    keep = ("pm25", "at", "network", "official", "place")
    items = [{"lat": round(i["lat"], 3), "lon": round(i["lon"], 3), **{k: i.get(k) for k in keep}}
             for i in doc.get("items") or []
             if i.get("lat") is not None and i.get("lon") is not None and (_age(i.get("at"), now) or FRESH * 2) <= FRESH]
    return {"at": doc["at"], "items": items}


def water(r: dict, frame: tuple, centre: tuple[float, float], inside, square=None) -> tuple:
    """(rivers, basin, river) from the hydro pack's result. The pack cut its square around the house and measured
    every reach from it (`dist_m`), so the reaches are re-chosen by the city frame, which lies inside that square
    and depends only on the cells, and measured again from the cell's centre. The basin is the one holding the
    centre, never the one holding the house: a basin edge through the cell would say which side the house is on."""
    if not r or not (r.get("rivers") or {}).get("features"):
        return None, None, None
    w, s, e, n = frame
    if square:          # a square smaller than the frame would show its own edge, and that edge is round the house
        sw, ss, se, sn = square(r["lat"], r["lon"], r["radius_km"])
        if not (sw <= w and ss <= s and e <= se and n <= sn):
            return None, None, None
    reaches = [f for f in r["rivers"]["features"]
               if any(w <= x <= e and s <= y <= n for x, y in f["geometry"]["coordinates"])]
    rivers = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"m3s": f["properties"].get("dis_av_cms"), "order": f["properties"].get("ord_stra")},
         "geometry": f["geometry"]} for f in reaches]}
    basin = next(({"type": "Feature", "geometry": f["geometry"],
                   "properties": {k: f["properties"].get(k) for k in ("sub_area", "up_area")}}
                  for f in (r.get("basins") or {}).get("features") or []
                  if inside(centre[0], centre[1], f["geometry"]["coordinates"])), None)
    river = None
    if reaches:
        from_c = [(min(h3.great_circle_distance((centre[1], centre[0]), (y, x), unit="km")
                       for x, y in _dense(f["geometry"]["coordinates"])), f["properties"].get("dis_av_cms") or 0)
                  for f in reaches]
        near, big = min(from_c), max(from_c, key=lambda t: t[1])
        river = {"nearest_km": round(near[0]), "nearest_m3s": near[1], "largest_km": round(big[0]), "largest_m3s": big[1]}
    return rivers, basin, river


def _dense(pts: list, step: float = 0.002) -> list:
    """A line's vertices with points every ~200 m between them, so the nearest point on a long straight reach is
    not missed. ponytail: point sampling, whole km is all it has to be right to."""
    out = [pts[0]]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        k = max(1, int(max(abs(x2 - x1), abs(y2 - y1)) / step))
        out += [(x1 + (x2 - x1) * i / k, y1 + (y2 - y1) * i / k) for i in range(1, k + 1)]
    return out


def grid(raw: dict, centre: tuple[float, float]) -> dict | None:
    """The energy pack's raw result, measured again from the cell's centre: its `km` is from the house, to 10 m."""
    if not raw:
        return None
    src = [s for s in raw.get("sources") or [] if isinstance(s, dict) and s.get("lat") is not None and s.get("lon") is not None]
    subs = sorted(km_from(centre, s["lon"], s["lat"]) for s in src if s.get("kind") == "substation")
    plants = sorted(({"name": s.get("name"), "fuel": s.get("fuel"), "mw": s.get("mw"), "lat": round(s["lat"], 3),
                      "lon": round(s["lon"], 3), "km": km_from(centre, s["lon"], s["lat"])}
                     for s in src if s.get("kind") == "plant" and (s.get("mw") or 0) >= 1),
                    key=lambda p: p["km"])
    low = (raw.get("share") or {}).get("low")
    return {"fossil_low_pct": None if low is None else round(low * 100), "substation_km": subs[0] if subs else None,
            "plants": [p for p in plants if p["km"] <= PLANT_KM]}


def change(earth, near: tuple[float, float]) -> dict | None:
    """The newest land-change pair's Wall image (packs/earth writes change_<A>_<B>_wall.png), placed by the crop the
    earth pack records for it under `wall` in the pair's stats: {bounds (UTM, the stats' crs), ha}. Never by the
    stats' own `bounds`: that square is centred on the house's pixel, so its corners give the house to 10 m, and its
    hectares count the same square. Null until both the image and its crop exist."""
    cs = earth.changes() if earth else []
    if not cs:
        return None
    c = ([x for x in cs if x.get("year_b", 0) - x.get("year_a", 0) == 1] or cs)[-1]
    a, b, crop = c.get("year_a"), c.get("year_b"), c.get("wall") or {}
    bb = crop.get("bounds")
    if not bb or not earth.change_file(a, b, "png").with_name(f"change_{a}_{b}_wall.png").is_file():
        return None
    epsg = int(str(c.get("crs", "")).rsplit(":", 1)[-1])
    corners = [lonlat(bb[x], bb[y], epsg, near) for x, y in
               (("west", "north"), ("east", "north"), ("east", "south"), ("west", "south"))]
    return {"a": a, "b": b, "ha": crop.get("ha"), "corners": corners, "png": "/earth/wall.png"}


def _inner_m(home: str, radius_m: float) -> int:
    """The radius round the cell's centre that a disc of `radius_m` round the house always covers, wherever in the
    cell the house is. The place pack's roofs stop at PLACE_RADIUS_M from the house, so a count over the seven cells
    would change with where the house stands in its cell; this one cannot."""
    c = h3.cell_to_latlng(home)
    return int(radius_m - max(h3.great_circle_distance(c, v, unit="m") for v in h3.cell_to_boundary(home)))


# ---------------------------------------------------------------- the route

_BUCKETS = "SELECT DISTINCT bucket FROM readings_1h WHERE bucket > now() - interval '24 hours'"
_STATIONS = ("SELECT sensor_id, lat, lon FROM sensors WHERE kind = 'sensor' AND NOT local AND NOT indoor "
             "ORDER BY sensor_id")
_HOURLY = ("SELECT h.bucket, h.sensor_id, h.metric, h.mean FROM readings_1h h "
           "WHERE h.bucket > now() - interval '24 hours' AND h.sensor_id = ANY(%s) AND h.metric = ANY(%s)")
_LABS = "SELECT name, lat, lon FROM sensors WHERE kind = 'facility' AND lat IS NOT NULL AND lon IS NOT NULL"
_ROOFS = ("SELECT count(*) AS n FROM place_features WHERE kind = 'building' AND "
          "ST_DWithin(ST_Centroid(geom)::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)")


@router.get("/wall")
def wall():
    """What the Wall's map draws (docs/site/wall.md): the three sizes, the 24 hours /issues draws, the air stations
    around and across the island, the roofs, the lab, the water, the grid and the land that changed."""
    lat, lon = float(os.getenv("NODE_LAT", 0) or 0), float(os.getenv("NODE_LON", 0) or 0)
    if not (lat or lon):
        raise HTTPException(409, "this node has no NODE_LAT and NODE_LON yet, so there is no place to draw")
    home = h3.latlng_to_cell(lat, lon, 8)
    clat, clon = h3.cell_to_latlng(home)
    centre = (clon, clat)
    now = datetime.now(timezone.utc)
    sc = scales(home)
    city = [p for c in sc[-1]["cells"] for p in c["ring"]]
    frame = (min(p[0] for p in city), min(p[1] for p in city), max(p[0] for p in city), max(p[1] for p in city))
    on = {m["id"] for m in packs.manifests()}

    roofs = lab = None
    with db() as con, con.cursor() as cur:
        cur.execute(_BUCKETS)
        buckets = day_buckets([r["bucket"] for r in cur.fetchall()], now)
        cur.execute(_STATIONS)
        found = [s for s in cur.fetchall() if s["lat"] is not None and s["lon"] is not None]
        cur.execute(_HOURLY, ([s["sensor_id"] for s in found] + ["om-point", "marine-point"],
                              ["pm25"] + [m for _, m in HOURS.values()]))
        rows = cur.fetchall()
        if "make" in on:
            cur.execute(_LABS)
            labs = sorted(cur.fetchall(), key=lambda r: km_from(centre, r["lon"], r["lat"]))
            if labs:
                lab = {"name": labs[0]["name"], "lat": round(labs[0]["lat"], 3), "lon": round(labs[0]["lon"], 3),
                       "km": km_from(centre, labs[0]["lon"], labs[0]["lat"])}
        r_m = _inner_m(home, float(settings.get("PLACE_RADIUS_M", "1000") or 1000))
        if "place" in on and r_m > 0:
            try:
                cur.execute(_ROOFS, (clon, clat, r_m))
                got = cur.fetchall()
                roofs = {"osm_in_cells": int(got[0]["n"]), "mapped_radius_m": r_m} if got else None
            except Exception:  # noqa: BLE001 — the place pack has not made its table yet
                roofs = None

    out_dir = Path(os.getenv("PACK_OUT", "/app/out"))
    try:
        isl = json.loads((out_dir / "wall" / "island.json").read_text()) if "bali-air-dispatch" in on else None
    except (OSError, ValueError):
        isl = None
    hydro, energy, earth = packs.module("hydro"), packs.module("energy"), packs.module("earth")
    rivers, basin, river = water(hydro.result(), frame, centre, hydro.inside, hydro.square) if hydro else (None, None, None)
    return {
        "home": home, "centre": [round(clon, 5), round(clat, 5)], "scales": sc,
        "hours": {"buckets": [b.isoformat() if hasattr(b, "isoformat") else b for b in buckets],
                  **{k: hourly(rows, buckets, sid, m) for k, (sid, m) in HOURS.items()}},
        "stations": [{"lat": round(s["lat"], 3), "lon": round(s["lon"], 3), "pm25": hourly(rows, buckets, s["sensor_id"], "pm25")}
                     for s in found],
        "island": island(isl, now), "roofs": roofs, "lab": lab,
        "rivers": rivers, "basin": basin, "river": river,
        "grid": grid(energy.result(), centre) if energy else None,
        "change": change(earth, (clat, clon)),
    }
