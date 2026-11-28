"""The keeper's statement of where this place's water comes from, parsed into one entry per source."""
from __future__ import annotations

import importlib.util
import re
import sys
import unicodedata
from pathlib import Path

KINDS = ("piped", "truck", "well", "spring", "rain", "bottled")
HOLDS = ("steady", "fails at times", "fails often")
NAMED_KINDS = ("works", "pumping", "reservoir", "dam", "well", "tower")


def sibling(name: str):
    """A file of this pack, loaded under its own name: packs share bare names like `osm`, so a plain import could meet another pack's."""
    key = f"supply_{name}"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, Path(__file__).with_name(f"{name}.py"))
        sys.modules[key] = mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return sys.modules[key]


def slug(name: str) -> str:
    folded = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")


def _origin(text: str):
    """A point, a name, None for blank, or False when it looks like a point but is out of range."""
    if not text:
        return None
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", text)
    if not m:
        return {"how": "name", "name": text}
    lat, lon = float(m.group(1)), float(m.group(2))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return False
    return {"how": "point", "lat": lat, "lon": lon}


def parse_sources(text: str) -> list[dict]:
    """`name | kind | holds | origin`, entries separated by `;`. A bad entry is kept with its problem, never dropped."""
    out: list[dict] = []
    seen: set[str] = set()
    for raw in (text or "").split(";"):
        if not raw.strip():
            continue
        parts = [p.strip() for p in raw.split("|")]
        e = {"entry": raw.strip(), "id": "", "name": "", "kind": "", "holds": None, "origin": None, "problem": None}
        if len(parts) != 4:
            e["problem"] = "fields"
        else:
            name, kind, holds, origin = parts
            e.update(name=name, kind=kind, id=slug(name))
            o = _origin(origin)
            if not e["id"]:
                e["problem"] = "name"
            elif kind not in KINDS:
                e["problem"] = "kind"
            elif holds and holds not in HOLDS:
                e["problem"] = "holds"
            elif o is False:
                e["problem"] = "origin"
            elif e["id"] in seen:
                e["problem"] = "duplicate"
            else:
                e["holds"], e["origin"] = holds or None, o
            if e["id"]:
                seen.add(e["id"])
        out.append(e)
    return out


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).casefold().strip()


def resolve(source: dict, works: list[dict], lat: float, lon: float) -> dict | None:
    """Where a source comes from: the point the keeper typed, or the nearest water work on the map that has the name they gave."""
    o = source.get("origin")
    if not o:
        return None
    if o["how"] == "point":
        return {"how": "stated", "name": None, "lat": o["lat"], "lon": o["lon"]}
    want = _fold(o["name"])
    km = sibling("osm").km
    hits = [w for w in works if w.get("kind") in NAMED_KINDS and w.get("name") and _fold(w["name"]) == want]
    if not hits:
        return None
    w = min(hits, key=lambda w: km(lat, lon, w["lat"], w["lon"]))
    return {"how": "mapped", "name": w["name"], "lat": w["lat"], "lon": w["lon"]}


def _rings(geometry: dict) -> list:
    c = (geometry or {}).get("coordinates") or []
    if (geometry or {}).get("type") == "MultiPolygon":
        return [ring for poly in c for ring in poly]
    return list(c)


def basin_of(lat: float, lon: float, hydro: dict, inside, centre) -> str | None:
    """`same` inside the level-12 basin holding the middle of the node's cell (`centre`, as lat, lon), `other` inside
    another basin hydro holds, `beyond` outside them all. None with no basins or no centre: a basin edge through the
    cell would otherwise say which side of it the node is on."""
    feats = ((hydro or {}).get("basins") or {}).get("features") or []
    if not feats or not centre:
        return None
    rings = [_rings(f.get("geometry")) for f in feats]
    home = next((r for r in rings if inside(centre[1], centre[0], r)), None)
    if home is not None and inside(lon, lat, home):
        return "same"
    return "other" if any(inside(lon, lat, r) for r in rings) else "beyond"
