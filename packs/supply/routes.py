"""GET /supply: where this place's water comes from, as its keeper states it, beside the water works on the public map.

Mounted from here by app/packs.py::routers() and answered 404 while the supply pack is off. It reads the pack's
result and stores nothing. The keeper's own tokens, or this machine, get every point and each km from the node.
Anyone else gets each km from the middle of the res-8 cell, whole, and never a point the keeper typed. On a house
the points of mapped works and origins go to the keeper only: a work's position beside a whole-km distance would
place the house.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi import APIRouter, Header, Request

import placewords
import wall
from auth import _shows_private

router = APIRouter()

_spec = importlib.util.spec_from_file_location("planetai_pack_supply_adapter_for_routes", Path(__file__).with_name("adapter.py"))
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)  # type: ignore[union-attr]

KEEPER_CREDIT = "Water supply as stated by the keeper of this node"
HINT = "not stated: set SUPPLY_SOURCES on Set up"
HINT_READ = "not read: see the entries"
MAX_WORKS = 40


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def build(res: dict, mine: bool, community: bool) -> dict:
    """The answer for one caller; a result of any other shape is the empty answer."""
    res = res if isinstance(res, dict) else {}
    centre = None if mine else wall.cell_centre()

    def km(lat, lon):
        if not (_num(lat) and _num(lon)):
            return None
        if mine:
            if not (_num(res.get("lat")) and _num(res.get("lon"))):
                return None
            return round(adapter.osm.km(res["lat"], res["lon"], lat, lon), 1)
        return None if centre is None else round(wall.dist_km(centre, lon, lat))

    sources, stated = [], 0
    for s in res.get("stated") if isinstance(res.get("stated"), list) else []:
        if not isinstance(s, dict):
            continue
        if s.get("problem"):
            if mine:
                sources.append({"entry": s.get("entry"), "problem": s["problem"]})
            continue
        stated += 1
        o = s.get("origin") if isinstance(s.get("origin"), dict) else None
        if o:
            typed = o.get("how") == "stated"
            show = mine or (community and not typed)
            out = {"how": o.get("how"), "name": o.get("name"),
                   "km": km(o.get("lat"), o.get("lon")), "basin": o.get("basin")}
            if show and _num(o.get("lat")) and _num(o.get("lon")):
                out["lat"], out["lon"] = o["lat"], o["lon"]
            o = out
        sources.append({"id": s.get("id"), "name": s.get("name"), "kind": s.get("kind"), "holds": s.get("holds"), "origin": o})

    works = []
    for w in res.get("works") if isinstance(res.get("works"), list) else []:
        if isinstance(w, dict) and _num(w.get("lat")) and _num(w.get("lon")):
            row = {"kind": w.get("kind"), "name": w.get("name"), "operator": w.get("operator"), "km": km(w["lat"], w["lon"])}
            if mine or community:
                row["lat"], row["lon"] = w["lat"], w["lon"]
            works.append(row)
    works.sort(key=lambda w: (w["km"] is None, w["km"] or 0, str(w["name"] or "")))
    works = works[:MAX_WORKS]

    attribution = [a for a in (res.get("attribution") if isinstance(res.get("attribution"), list) else []) if works and isinstance(a, str)]
    if stated:
        attribution.append(KEEPER_CREDIT)
    problems = any(isinstance(s, dict) and s.get("problem") for s in res["stated"]) if isinstance(res.get("stated"), list) else False
    hint = None if stated else (HINT_READ if mine and problems else HINT)
    return {
        "state": ("both" if works else "stated") if stated else ("mapped" if works else "none"),
        "sources": sources, "works": works,
        "counts": res.get("counts") if isinstance(res.get("counts"), dict) else {},
        "radius_km": res.get("radius_km") if _num(res.get("radius_km")) else None,
        "attribution": attribution,
        "fetched_at": res.get("fetched_at") if isinstance(res.get("fetched_at"), str) else None,
        "hint": hint,
    }


@router.get("/supply")
def supply(request: Request, authorization: str = Header("")):
    try:
        res = adapter.result()
    except Exception:
        res = {}
    try:
        return build(res, _shows_private(request, authorization, raw=False), not placewords.is_house())
    except Exception:
        return build({}, False, False)
