"""The area pull: ask the node about any set of cells or any drawn area (spec 2026-11-10, §2).

A selection is covered at res 8 and capped at AREA_CAP cells, refused before covering when the estimate is over, the
way geo.grid refuses past GRID_CAP. Three streams answer it; this file holds the two the node keeps itself:

- own: this node's custody sensors, read only inside the node's own cells. A selection elsewhere reads none of them.
- peers: kind='peer' sensors with a point in the selection. A peer with no point is counted, never guessed into a cell.

All pure here; Task 8 adds the route, resolves a mark_id to its geometry and passes the rows in. h3 stays on the
server: the page sends ids or GeoJSON and draws what comes back.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import h3

import cells as cells_mod

AREA_CAP = 500                                  # res-8 cells one selection may cover, about 370 km²
RES = cells_mod.RES


def _poly_rings(geom) -> list[list[list]]:
    """Every polygon of a GeoJSON Polygon or MultiPolygon as a list of rings, each point checked as [lon, lat]."""
    if not isinstance(geom, dict) or geom.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValueError("polygon must be a GeoJSON Polygon or MultiPolygon.")
    coords = geom.get("coordinates")
    polys = [coords] if geom["type"] == "Polygon" else coords
    if not isinstance(polys, list) or not polys:
        raise ValueError("The polygon has no coordinates.")
    for poly in polys:
        if not isinstance(poly, list) or not poly:
            raise ValueError("The polygon has no rings.")
        for ring in poly:
            if not isinstance(ring, list) or len(ring) < 3:
                raise ValueError("Each ring of the polygon needs at least three points.")
            for p in ring:
                if not (isinstance(p, list | tuple) and len(p) >= 2
                        and all(isinstance(v, int | float) and not isinstance(v, bool) for v in p[:2])
                        and -180 <= p[0] <= 180 and -90 <= p[1] <= 90):
                    raise ValueError("Each point of the polygon must be [longitude, latitude] in degrees.")
    return polys


def _area_m2(polys) -> float:
    """Shoelace on a local flat projection: outer ring minus holes. Good to a few percent at a city's size."""
    total = 0.0
    for poly in polys:
        for i, ring in enumerate(poly):
            k = math.cos(math.radians(sum(p[1] for p in ring) / len(ring))) * 111320
            xy = [(p[0] * k, p[1] * 110574) for p in ring]
            a = abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(xy, xy[1:] + xy[:1]))) / 2
            total += -a if i else a
    return total


def _over_cap() -> ValueError:
    return ValueError(f"That selection covers more than {AREA_CAP} cells at resolution {RES}. Choose a smaller area.")


def cover(sel: dict) -> list[str]:
    """The sorted res-8 cells a selection covers: {"cells": [...]} at res 5 to 10, or {"polygon": GeoJSON}.
    A mark_id is resolved to its polygon by the route before it gets here."""
    keys = [k for k in ("cells", "polygon", "mark_id") if k in (sel or {})]
    if len(keys) != 1:
        raise ValueError("A selection has exactly one of cells, polygon or mark_id.")
    if keys[0] == "mark_id":
        raise ValueError("A mark_id is read from the Place map first; send its polygon here.")
    if keys[0] == "cells":
        ids = sel["cells"]
        if not isinstance(ids, list) or not ids:
            raise ValueError("cells must be a list of H3 ids.")
        ids = set(ids)
        for c in ids:
            if not (isinstance(c, str) and h3.is_valid_cell(c) and 5 <= h3.get_resolution(c) <= 10):
                raise ValueError(f"{c!r} is not an H3 cell at resolution 5 to 10.")
        if sum(h3.cell_to_children_size(c, RES) if h3.get_resolution(c) < RES else 1 for c in ids) > AREA_CAP:
            raise _over_cap()
        out = set()
        for c in ids:
            r = h3.get_resolution(c)
            out |= set(h3.cell_to_children(c, RES)) if r < RES else {h3.cell_to_parent(c, RES)}
    else:
        polys = _poly_rings(sel["polygon"])
        if _area_m2(polys) / h3.average_hexagon_area(RES, unit="m^2") > AREA_CAP:
            raise _over_cap()
        try:
            out = set(h3.geo_to_cells(sel["polygon"], RES))
        except (ValueError, h3.H3BaseException) as e:
            raise ValueError("That polygon is not one H3 can cover.") from e
        if not out:   # an area smaller than a cell: the cells its corners stand in, never nothing
            out = {h3.latlng_to_cell(p[1], p[0], RES) for poly in polys for p in poly[0]}
    if len(out) > AREA_CAP:        # the estimate is a few percent off at the edge
        raise _over_cap()
    return sorted(out)


def bbox(cells: list[str]) -> tuple[float, float, float, float]:
    """west, south, east, north of the cells' boundaries."""
    # ponytail: no antimeridian handling; a selection across 180° gets a box round the world. Split it if one ever does.
    pts = [p for c in cells for p in h3.cell_to_boundary(c)]
    if not pts:
        raise ValueError("No cells, no box.")
    return min(p[1] for p in pts), min(p[0] for p in pts), max(p[1] for p in pts), max(p[0] for p in pts)


def _ts(v) -> datetime:
    t = datetime.fromisoformat(v) if isinstance(v, str) else v
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def summarise(rows: list[dict]) -> dict:
    """Per metric: the newest past reading (the mean of the sensors at that moment) and the mean over the last 24 h.
    A row timestamped in the future is a forecast, not a reading. No reading in 24 h: mean_24h is None, n is 0."""
    now = datetime.now(timezone.utc)
    by: dict[str, list[tuple[datetime, float]]] = {}
    for r in rows:
        if r.get("value") is None:
            continue
        t = _ts(r["ts"])
        if t <= now:
            by.setdefault(r["metric"], []).append((t, float(r["value"])))
    out = {}
    for m, xs in by.items():
        last = max(t for t, _ in xs)
        at = [v for t, v in xs if t == last]
        day = [v for t, v in xs if t > now - timedelta(hours=24)]
        out[m] = {"latest": sum(at) / len(at), "latest_at": last.isoformat(),
                  "mean_24h": sum(day) / len(day) if day else None, "n": len(day)}
    return out


def _placed(s: dict) -> str | None:
    return cells_mod.cell_of(s.get("lat"), s.get("lon"))


def _read(sensors: list[dict], readings: list[dict]) -> dict:
    ids = {s["sensor_id"] for s in sensors}
    return summarise([r for r in readings if r["sensor_id"] in ids])


def own(sensors, readings, selection: set[str], own_cells: set[str]) -> dict:
    """This node's custody sensors whose cell is in selection ∩ own_cells. A child (no point on the aggregates wire)
    is counted in children_unplaced; any custody sensor with no point is never guessed into a cell."""
    mine = set(selection) & set(own_cells)
    here = [s for s in sensors if s.get("custody") and s.get("kind") != "child" and _placed(s) in mine]
    out = {"cells": sorted(mine), "sensors": len(here), "metrics": _read(here, readings),
           "children_unplaced": sum(1 for s in sensors if s.get("custody") and s.get("kind") == "child"
                                    and _placed(s) is None)}
    if not mine:
        out["why"] = "None of these cells is the node's own, so none of its readings are read here."
    elif not out["metrics"]:
        out["why"] = "No sensor of this node has a reading in these cells."
    return out


def peers(sensors, readings, selection: set[str]) -> dict:
    """kind='peer' sensors with a point in the selection. A peer with only a distance (radio) is counted as unplaced."""
    ps = [s for s in sensors if s.get("kind") == "peer"]
    here = [s for s in ps if _placed(s) in selection]
    out = {"sensors": len(here), "metrics": _read(here, readings), "unplaced": sum(1 for s in ps if _placed(s) is None)}
    if not out["metrics"]:
        out["why"] = "No neighbouring node has a reading in these cells."
    return out
