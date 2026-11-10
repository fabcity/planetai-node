"""The node's seven res-8 cells: the cell the node stands in and the six touching it (SPEC_eyes §5, §7 step 4).

A home node grows from one cell to seven by "picked, then held": the keeper claims a neighbour, it shows as `claimed`
until an own sensor reading lands in it in the last 24 h, and then as `held`. `held` is derived on every read, never
stored, so it cannot disagree with the readings.
"""
from __future__ import annotations

import os

import h3

from issues import geometry as geo

RES = 8
STATES = ("home", "held", "claimed", "open")


def home(lat: float, lon: float) -> str:
    return h3.latlng_to_cell(float(lat), float(lon), RES)


def ring(home_cell: str) -> list[str]:
    return [home_cell] + sorted(c for c in h3.grid_disk(home_cell, 1) if c != home_cell)


def own(home_cell: str, claims: set[str]) -> set[str]:
    return {home_cell} | (set(claims) & set(ring(home_cell)))


def cell_of(lat: float | None, lon: float | None) -> str | None:
    if lat is None or lon is None:
        return None
    return h3.latlng_to_cell(float(lat), float(lon), RES)


def states(home_cell: str, claims: set[str], seen: set[str]) -> list[dict]:
    out = []
    for c in ring(home_cell):
        if c == home_cell:
            state = "home"
        elif c in claims and c in seen:
            state = "held"
        elif c in claims:
            state = "claimed"
        else:
            state = "open"
        out.append({"cell": c, "state": state, "ring": geo._row(c)})
    return out


def held_count(rows: list[dict]) -> int:
    return sum(1 for r in rows if r["state"] in ("home", "held"))


def adoptable(home_cell: str, local_points: list[tuple[float, float]]) -> set[str]:
    neighbours = set(ring(home_cell)) - {home_cell}
    return {c for lat, lon in local_points if (c := cell_of(lat, lon)) in neighbours}


def _node_point(home_cell: str) -> tuple[float, float]:
    """NODE_LAT/NODE_LON when they fall in home_cell, else the cell's centre. Adoption measures the old 500 m from
    the node's own point: node #1's two Smart Citizen kits are 250 and 273 m from it but 534 and 564 m from its
    cell's centre."""
    try:
        lat, lon = float(os.getenv("NODE_LAT") or "x"), float(os.getenv("NODE_LON") or "x")
        if home(lat, lon) == home_cell:
            return lat, lon
    except ValueError:
        pass
    return h3.cell_to_latlng(home_cell)


def _has_home(cur, home_cell: str) -> bool:
    cur.execute("SELECT cell, claimed_by FROM node_cells WHERE cell = %s", (home_cell,))
    r = cur.fetchone()
    return bool(r) and r["claimed_by"] == "home"


def adopt(cur, home_cell: str, radius_m: float = 500) -> set[str]:
    """Once per home cell: claim every neighbour that holds a sensor local under the old LOCAL_RADIUS_M rule, so
    upgrading drops no sensor out of `local`. The ('home') row it writes marks adoption done for this cell."""
    from sources import metres  # noqa: PLC0415 — sources imports this module for stamp_local
    if _has_home(cur, home_cell):
        return set()
    cur.execute("SELECT lat, lon FROM sensors WHERE local AND kind = 'sensor' AND lat IS NOT NULL AND lon IS NOT NULL")
    nlat, nlon = _node_point(home_cell)
    pts = [(float(r["lat"]), float(r["lon"])) for r in cur.fetchall()
           if metres(nlat, nlon, float(r["lat"]), float(r["lon"])) <= radius_m]
    claimed = adoptable(home_cell, pts)
    cur.execute("INSERT INTO node_cells (cell, claimed_by) VALUES (%s, 'home') "
                "ON CONFLICT (cell) DO UPDATE SET claimed_by = 'home'", (home_cell,))
    for c in sorted(claimed):
        cur.execute("INSERT INTO node_cells (cell, claimed_by) VALUES (%s, 'adopted') ON CONFLICT (cell) DO NOTHING", (c,))
    return claimed


def load(cur, home_cell: str) -> set[str]:
    """The node's own cells: home plus the claimed neighbours, adopting first the first time it stands in home_cell."""
    adopt(cur, home_cell)
    cur.execute("SELECT cell FROM node_cells")
    return own(home_cell, {r["cell"] for r in cur.fetchall()})
