"""The node's seven res-8 cells: the cell the node stands in and the six touching it (SPEC_eyes §5, §7 step 4).

A home node grows from one cell to seven by "picked, then held": the keeper claims a neighbour, it shows as `claimed`
until an own sensor reading lands in it in the last 24 h, and then as `held`. `held` is derived on every read, never
stored, so it cannot disagree with the readings.
"""
from __future__ import annotations

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
