"""The H3 geometry this node publishes: the shapes the dashboard navigates by, computed here so the page never has to.

The node already has h3 (app/ground.py, the presence announce). Nothing here is a capability it gains — only a
shape it publishes. Every function is pure: coordinates, settings and station rows in; JSON-ready dicts out. The
same functions answer for live data and for a fixture replayed at the hour it was captured.

Design provenance: planetai-design/prototypes/dashboard-directions/make-h3.mjs, which computed these for the
Phase 1 drawings with h3-js and checked them against h3geo.org's resolution table and the design repo's
kilometre-cells.json. This is the Python of the same arithmetic; tests/test_issues_geometry.py keeps the two
agreeing.

One vocabulary note. A *distance* — room, yard, ring, region — is custody, not scale (DIRECTIONS_2026-09.md
finding 1). Nothing here maps a distance to a resolution. What is published is the grid itself, and the page
says which custody a reading carries.
"""
from __future__ import annotations

import math

import h3

NAV_MIN, NAV_MAX, NAV_STEPS = 2, 12, 2


def contains(metres: float) -> int:
    """The finest resolution whose cell is at least `metres` across (two edge lengths)."""
    for res in range(15, -1, -1):
        if h3.average_hexagon_edge_length(res, unit="m") * 2 >= metres:
            return res
    return 0


def publication() -> dict:
    """The finest grain a coordinate this node publishes may honestly be drawn at.

    GET /health rounds lat and lon to three decimals (app/main.py), about 110 m at this latitude; a cell narrower
    than that is a claim of precision the node did not make.
    """
    return {"decimals": 3, "metres": 110, "res": contains(110),
            "why": "GET /health rounds lat and lon to three decimals, which is about 110 m — app/main.py"}


def ladder(lat: float, lon: float) -> list[dict]:
    """Every resolution this place can be named at, with what H3 says a cell is there, and the cell it stands in."""
    out = []
    for res in range(0, 14):
        cell = h3.latlng_to_cell(lat, lon, res)
        out.append({
            "res": res, "id": cell,
            "edge_m": round(h3.average_hexagon_edge_length(res, unit="m")),
            "area_m2": round(h3.average_hexagon_area(res, unit="m^2")),
            "cells": h3.get_num_cells(res),
            "own_area_m2": round(h3.cell_area(cell, unit="m^2")),
            "pentagon": h3.is_pentagon(cell),
        })
    return out


def _cell_of(station: dict, res: int) -> str:
    return h3.latlng_to_cell(station["lat"], station["lon"], res)


def plates(lat: float, lon: float, stations: list[dict], res_min: int = NAV_MIN, res_max: int = NAV_MAX,
           steps: int = NAV_STEPS) -> dict:
    """One plate per resolution: the node's cell and `steps` rings around it, with every cell's parent, neighbours,
    size and contents. A page navigates only inside what is published — a child or neighbour outside the plate is a
    count, not a door. A dashboard is not a map of the planet."""
    chain = {res: h3.latlng_to_cell(lat, lon, res) for res in range(res_min, res_max + 1)}
    plates_ = {}
    for res in range(res_min, res_max + 1):
        centre = chain[res]
        ids = h3.grid_disk(centre, steps)
        plates_[res] = {"res": res, "centre": centre, "cells": ids,
                        "cells_ll": [[cid] + [round(v, 6) for pt in h3.cell_to_boundary(cid) for v in pt]
                                     for cid in ids]}
    in_plate = lambda res, cid: res_min <= res <= res_max and cid in plates_[res]["cells"]  # noqa: E731
    cells = {}
    for res in range(res_min, res_max + 1):
        for cid in plates_[res]["cells"]:
            parent = h3.cell_to_parent(cid, res - 1) if res > res_min else None
            kids = h3.cell_to_children(cid, res + 1) if res < res_max else []
            try:
                around = h3.grid_ring(cid, 1)
            except Exception:  # noqa: BLE001 — a pentagon's ring is undefined; the disk minus the centre is the answer
                around = [x for x in h3.grid_disk(cid, 1) if x != cid]
            cells[cid] = {
                "res": res,
                "parent": parent if parent and in_plate(res - 1, parent) else None,
                "parent_outside": bool(parent and not in_plate(res - 1, parent)),
                "children_total": len(kids),
                "children_here": sum(1 for k in kids if in_plate(res + 1, k)),
                "neighbours": [n for n in around if in_plate(res, n)],
                "neighbours_total": len(around),
                "area_m2": round(h3.cell_area(cid, unit="m^2")),
                "edge_m": round(h3.average_hexagon_edge_length(res, unit="m")),
                "pentagon": h3.is_pentagon(cid),
                "sensors": [i for i, s in enumerate(stations) if _cell_of(s, res) == cid],
            }
    return {"res_min": res_min, "res_max": res_max, "steps": steps, "chain": chain,
            "plates": plates_, "cells": cells, "cell_count": len(cells)}


def grain_table(lat: float, lon: float, stations: list[dict], floor_res: int, publication_res: int) -> list[dict]:
    """What every grain is worth: one cell's size, how many cells the stations fall in, and which side of the two
    lines the product already draws it is on."""
    out = []
    for res in range(NAV_MIN, NAV_MAX + 1):
        home = h3.latlng_to_cell(lat, lon, res)
        cells = {_cell_of(s, res) for s in stations}
        mine = [s for s in stations if _cell_of(s, res) == home]
        out.append({
            "res": res, "home": home,
            "area_m2": round(h3.cell_area(home, unit="m^2")),
            "edge_m": round(h3.average_hexagon_edge_length(res, unit="m")),
            "occupied": len(cells),
            "in_my_cell": len(mine),
            "mine_in_my_cell": sum(1 for s in mine if s.get("local")),
            "may_leave": res <= floor_res,
            "finer_than_published": res > publication_res,
        })
    return out


def metres(cid: str, lat: float, lon: float) -> list[float]:
    """A cell's boundary in metres east and south of the node, in the dashboard's own local frame —
    NODE_DASHBOARD_PLAN_SPEC.md rule 1, measured within 0.015 px of geoAzimuthalEqualArea over node #1's plan."""
    k = math.cos(math.radians(lat)) * 111320
    out = []
    for plat, plng in h3.cell_to_boundary(cid):
        out += [round((plng - lon) * k, 1), round(-(plat - lat) * 111320, 1)]
    return out
