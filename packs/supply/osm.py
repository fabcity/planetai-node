"""Water works on the public map: the Overpass query, its parser, and the distance helper."""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

QUERY = """[out:json][timeout:90][bbox:{s},{w},{n},{e}];
(
  nwr["man_made"~"^(water_works|pumping_station|water_tower|reservoir_covered|water_well|storage_tank|pipeline)$"];
  nwr["landuse"="reservoir"];
  nwr["water"="reservoir"];
  nwr["waterway"="dam"];
);
out tags center;"""

_MAN_MADE = {"water_works": "works", "pumping_station": "pumping", "water_tower": "tower", "reservoir_covered": "reservoir",
             "water_well": "well", "storage_tank": "tank", "pipeline": "pipeline"}


def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km (haversine, R = 6371 km)."""
    p1, p2, dl = radians(lat1), radians(lat2), radians(lon2 - lon1)
    return 6371.0 * 2.0 * asin(sqrt(sin((p2 - p1) / 2.0) ** 2 + cos(p1) * cos(p2) * sin(dl / 2.0) ** 2))


def _kind(tags: dict) -> str | None:
    kind = _MAN_MADE.get(tags.get("man_made"))
    if kind is None:
        if tags.get("landuse") == "reservoir" or tags.get("water") == "reservoir":
            return "reservoir"
        return "dam" if tags.get("waterway") == "dam" else None
    # A fuel tank or a gas pipeline carries the same man_made tag: only water counts.
    if kind == "tank" and tags.get("content") != "water":
        return None
    if kind == "pipeline" and tags.get("substance") != "water":
        return None
    return kind


def parse(doc: dict) -> list[dict]:
    """Water works from an Overpass JSON answer; an element with no point or none of the tags read is dropped."""
    out: list[dict] = []
    for el in (doc or {}).get("elements") or []:
        tags = el.get("tags") or {}
        kind = _kind(tags)
        center = el.get("center") or el
        lat, lon = center.get("lat"), center.get("lon")
        if kind is None or lat is None or lon is None:
            continue
        out.append({"kind": kind, "name": tags.get("name") or tags.get("name:en") or "", "operator": tags.get("operator") or "",
                    "lat": float(lat), "lon": float(lon)})
    return out
