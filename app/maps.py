"""The household's maps on the Place door: named maps, the drawings on them, their rows in the ledger, and a drawing
tied to an issue as the issue's acted step. docs/superpowers/specs/2026-11-04-place-light-gis-design.md §5 and §8.

Every route here is the household's alone, at every SHARE_LEVEL: none is on an allowlist in app/auth.py, and the router
checks the admin or act token itself because the middleware also lets BACKUP_TOKEN through, and a NAS's read token
must not draw or write ρ (the same reason POST /actions checks its own). PostGIS measures every drawing: `length_m`
and `area_m2` come from `geom::geography` on every insert and update, so the page computes no distance.

An agent's own map (`agent` set) is refused to the household's edits in this pull request; agents become writers in
the third (§7). A map received from a child node (`from_node` set) is refused to them always: it is the child's.
Never import app/main.py from here: it starts a second MQTT client.

A shared map goes to the node upstream exactly as drawn (Tomas, 4 Nov: "Exact, with a warning"), by the child's
push, never a pull: push_maps() every minute, and POST /place/maps/received on the parent, the one route here that
answers AGGREGATE_TOKEN and nothing else.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import unicodedata
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import psycopg

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response

import events_pg
import geo
from auth import ACT_TOKEN, AGG_TOKEN, PARENT, PARENT_TOKEN, _bearer_ok, _is_local
from db import NODE_TZ, db

log = logging.getLogger("planetai")


def _household(request: Request, authorization: str = Header("")) -> None:
    if not (_is_local(request) or _bearer_ok(authorization, os.getenv("ADMIN_TOKEN", "").strip(), ACT_TOKEN())):
        raise HTTPException(401, "Maps need the household's token.")


router = APIRouter(dependencies=[Depends(_household)])
received = APIRouter()                                     # a child's writes: AGGREGATE_TOKEN, never the household's

SHARE_WARNING = ("Sharing sends every drawing in this map, at its exact place, with its labels, notes and measures, to "
                 "the node upstream, where the people holding its token can see it. Press Share again to send it.")
NO_PARENT = "There is no node upstream to share with. Set PARENT in Set up first."
ON_HOUSE = "This drawing sits on the house. Press Share again to send the map with it."
NOT_YET = "The node upstream does not take maps yet."
NOT_SENT = "The map did not reach the node upstream. The node tries again in an hour."

# Colour → (hex for the screen, AutoCAD Colour Index for DXF). A drawing stores the number, so this can change without
# a migration. None is the satellite's orange or the cells' blue, and each reads on the satellite and on black.
PALETTE: dict[int, tuple[str, int]] = {
    1: ("#FFFFFF", 7), 2: ("#FFE600", 2), 3: ("#9BFF2E", 70), 4: ("#00E5FF", 4), 5: ("#FF3DCB", 6), 6: ("#FF3B30", 1)}

_TYPE = {"marker": "Point", "note": "Point", "line": "LineString", "area": "Polygon"}
_COORDS = "Every point needs a longitude and a latitude."


# ---------------------------------------------------------------- what a drawing must be

def _pt(p) -> bool:
    return (isinstance(p, (list, tuple)) and len(p) == 2
            and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in p)
            and -180 <= p[0] <= 180 and -90 <= p[1] <= 90)


def _dedupe(pts: list) -> list:
    """A point tapped twice in a row is one point."""
    return [list(p) for i, p in enumerate(pts) if i == 0 or list(p) != list(pts[i - 1])]


def _ring(pts: list) -> list:
    """An area's outline, closed: an outline left open is closed here rather than refused."""
    r = _dedupe(pts)
    return r + [r[0]] if r and r[0] != r[-1] else r


def _orient(a, b, c) -> int:
    v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (v > 0) - (v < 0)


def _on(a, b, c) -> bool:
    """c, collinear with a-b, lies on the segment."""
    return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])


def _meet(p1, p2, p3, p4) -> bool:
    d1, d2, d3, d4 = _orient(p3, p4, p1), _orient(p3, p4, p2), _orient(p1, p2, p3), _orient(p1, p2, p4)
    if d1 * d2 < 0 and d3 * d4 < 0:
        return True
    return ((d1 == 0 and _on(p3, p4, p1)) or (d2 == 0 and _on(p3, p4, p2))
            or (d3 == 0 and _on(p1, p2, p3)) or (d4 == 0 and _on(p1, p2, p4)))


def _crosses(ring: list) -> bool:
    """Any two sides that are not neighbours touch or cross.
    ponytail: O(n²) crossing check, fine below a few hundred corners."""
    pts = ring[:-1]
    n = len(pts)
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue                                   # the last side meets the first at the start: neighbours
            if _meet(pts[i], pts[(i + 1) % n], pts[j], pts[(j + 1) % n]):
                return True
    return False


def check_feature(feature: dict) -> str | None:
    """The sentence a drawing is refused with, or None. Its kind says which geometry it must be."""
    props = feature.get("properties") if isinstance(feature, dict) else None
    kind = props.get("kind") if isinstance(props, dict) else None
    if kind not in _TYPE:
        return "A drawing is a marker, a line, an area or a note."
    geom = feature.get("geometry")
    gtype, c = (geom.get("type"), geom.get("coordinates")) if isinstance(geom, dict) else (None, None)
    if kind in ("marker", "note"):
        if gtype != "Point":
            return f"A {kind} is one point."
        return None if _pt(c) else _COORDS
    if kind == "line":
        if gtype != "LineString" or not isinstance(c, list):
            return "A line needs two points or more."
        if not all(_pt(p) for p in c):
            return _COORDS
        return None if len(_dedupe(c)) >= 2 else "A line needs two points or more."
    if gtype != "Polygon" or not isinstance(c, list) or not c or not isinstance(c[0], list):
        return "An area needs three corners or more."
    if len(c) > 1:
        return "An area is one outline, with no holes."
    if not all(_pt(p) for p in c[0]):
        return _COORDS
    ring = _ring(c[0])
    if len(ring) < 4 or len({tuple(p) for p in ring}) < 3:
        return "An area needs three corners or more."
    return "That area crosses itself. Draw its corners in order around it." if _crosses(ring) else None


def _geometry(kind: str, geom: dict) -> str:
    """The checked geometry as stored: repeats dropped, an area's outline closed."""
    c = geom["coordinates"]
    if kind == "line":
        c = _dedupe(c)
    elif kind == "area":
        c = [_ring(c[0])]
    return json.dumps({"type": _TYPE[kind], "coordinates": c})


def _text(x, n: int) -> str | None:
    return (str(x).strip()[:n] or None) if x is not None else None


def _fields(src: dict) -> dict:
    """The columns a drawing's form may set, only those present: label, note, colour, image."""
    out = {}
    if "label" in src:
        out["label"] = _text(src["label"], 80)
    if "note" in src:
        out["note"] = _text(src["note"], 500)
    if "colour" in src:
        c = src["colour"]
        if isinstance(c, bool) or c not in PALETTE:
            raise HTTPException(422, "A colour is a number from 1 to 6.")
        out["colour"] = c
    if "image" in src:
        i = src["image"]
        if i is not None and (isinstance(i, bool) or not isinstance(i, int)):
            raise HTTPException(422, "An image is a picture's number on this node.")
        out["capture_id"] = i
    return out


# ---------------------------------------------------------------- downloads

_SCHEMA = "planetai.place.map/v0"
_DXF_LAYER = {"marker": "MARKERS", "line": "LINES", "area": "AREAS", "note": "NOTES"}
_TEXT_H = 1.5                                              # metres: a label on a garden plan


def feature_collection(map_row: dict, marks: list[dict], node: str) -> dict:
    """The map as GeoJSON in WGS84: the same shape the page draws, and what a pull from another node reads back.
    `image` is the picture's capture id and never a file."""
    def props(m):
        at = m.get("updated_at")
        return {"kind": m["kind"], "label": m.get("label"), "note": m.get("note"), "colour": m["colour"],
                "colour_hex": PALETTE[m["colour"]][0], "length_m": m.get("length_m"), "area_m2": m.get("area_m2"),
                "image": m.get("capture_id"), "drawn_by": m.get("drawn_by"), "updated_at": at.isoformat() if at else None}
    return {"type": "FeatureCollection", "schema": _SCHEMA, "map": map_row["name"], "owner": map_row.get("owner"),
            "node": node, "features": [{"type": "Feature", "properties": props(m), "geometry": m["geometry"]} for m in marks]}


def to_kml(fc: dict) -> str:
    """KML 2.2 for Google Earth and QGIS. Each Placemark carries the drawing's colour (KML wants aabbggrr).
    ponytail: geometry is written here from the GeoJSON rather than read back from ST_AsKML; the three shapes are
    the same coordinates, and the pure function stays testable without a database."""
    ns = "http://www.opengis.net/kml/2.2"
    ET.register_namespace("", ns)
    q = lambda t: f"{{{ns}}}{t}"                           # noqa: E731
    clean = lambda t: re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(t))   # noqa: E731 — XML 1.0 refuses these
    root = ET.Element(q("kml"))
    doc = ET.SubElement(root, q("Document"))
    ET.SubElement(doc, q("name")).text = clean(fc["map"])
    for f in fc["features"]:
        p, g = f["properties"], f["geometry"]
        pm = ET.SubElement(doc, q("Placemark"))
        ET.SubElement(pm, q("name")).text = clean(p["label"] or p["kind"])
        if p["note"]:
            ET.SubElement(pm, q("description")).text = clean(p["note"])
        h = p["colour_hex"]
        kc = "ff" + h[5:7] + h[3:5] + h[1:3]
        st = ET.SubElement(pm, q("Style"))
        for tag in ("IconStyle", "LineStyle", "PolyStyle"):
            ET.SubElement(ET.SubElement(st, q(tag)), q("color")).text = kc
        c = g["coordinates"]
        line = lambda pts: " ".join(",".join(map(str, pt)) for pt in pts)   # noqa: E731
        if g["type"] == "Point":
            ET.SubElement(ET.SubElement(pm, q("Point")), q("coordinates")).text = line([c])
        elif g["type"] == "LineString":
            ET.SubElement(ET.SubElement(pm, q("LineString")), q("coordinates")).text = line(c)
        else:
            ring = ET.SubElement(ET.SubElement(ET.SubElement(pm, q("Polygon")), q("outerBoundaryIs")), q("LinearRing"))
            ET.SubElement(ring, q("coordinates")).text = line(c[0])
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def utm_epsg(lon: float, lat: float) -> int:
    """The WGS84 UTM zone a point lies in: 326zz north of the equator, 327zz south."""
    zone = min(60, max(1, int((lon + 180) // 6) + 1))
    return (32600 if lat >= 0 else 32700) + zone


def to_dxf(features_xy: list[dict], epsg: int) -> str:
    """AutoCAD R12 DXF, hand-written: every CAD reads it. Each item is {kind, label, note, colour, xy}, `xy` the
    drawing's vertices already in metres of `epsg`, which the first comment line says. Non-ASCII text is written the
    way AutoCAD writes it (\\U+00F1), because R12 has no encoding."""
    def txt(t):
        return "".join(ch if ord(ch) < 128 else f"\\U+{ord(ch):04X}" for ch in " ".join(str(t).split()))
    out = [999, f"EPSG:{epsg}, metres", 0, "SECTION", 2, "HEADER", 9, "$ACADVER", 1, "AC1009", 0, "ENDSEC",
           0, "SECTION", 2, "TABLES", 0, "TABLE", 2, "LTYPE", 70, 1, 0, "LTYPE", 2, "CONTINUOUS", 70, 0, 3, "Solid line",
           72, 65, 73, 0, 40, 0.0, 0, "ENDTAB", 0, "TABLE", 2, "LAYER", 70, len(_DXF_LAYER)]
    for name in _DXF_LAYER.values():
        out += [0, "LAYER", 2, name, 70, 0, 62, 7, 6, "CONTINUOUS"]
    out += [0, "ENDTAB", 0, "ENDSEC", 0, "SECTION", 2, "ENTITIES"]
    xyz = lambda x, y: [10, f"{x:.3f}", 20, f"{y:.3f}", 30, 0]   # noqa: E731
    for f in features_xy:
        layer, aci, pts = _DXF_LAYER[f["kind"]], PALETTE[f["colour"]][1], f["xy"]
        head = [8, layer, 62, aci]
        if f["kind"] in ("marker", "note"):
            out += [0, "POINT", *head, *xyz(*pts[0])]
        else:
            out += [0, "POLYLINE", *head, 66, 1, *xyz(0, 0), 70, 1 if f["kind"] == "area" else 0]
            for x, y in pts:
                out += [0, "VERTEX", 8, layer, *xyz(x, y)]
            out += [0, "SEQEND", 8, layer]
        x, y = pts[0]
        for t in (f.get("label"), f.get("note")):
            if t and txt(t):
                out += [0, "TEXT", 8, _DXF_LAYER["note"], 62, aci, *xyz(x, y), 40, _TEXT_H, 1, txt(t)]
                y -= _TEXT_H * 1.5                         # a note sits under its label
    out += [0, "ENDSEC", 0, "EOF"]
    return "\n".join(map(str, out)) + "\n"


# ---------------------------------------------------------------- the ledger and the issue

def ledger(cur, actor: str, verb: str, note: str, key: str) -> None:
    """One `place` row in the actions ledger. The same person doing the same thing to the same drawing within a minute
    is one row: its time and note move on. `key` (`mark:12`, `map:3`) ends the note as `(mark 12)`."""
    tail = f" ({key.replace(':', ' ', 1)})"
    text = note[:500 - len(tail)] + tail
    # ponytail: two writes in the same instant could both miss the update and insert twice; harmless in a ledger
    cur.execute("""UPDATE actions SET ts = now(), note = %s WHERE ctid = (
                     SELECT ctid FROM actions WHERE stage = 'place' AND actor = %s AND choice = %s
                        AND right(note, %s) = %s AND ts > now() - interval '60 seconds' ORDER BY ts DESC LIMIT 1)""",
                (text, actor, verb, len(tail), tail))
    if not cur.rowcount:
        cur.execute("INSERT INTO actions (stage, actor, note, choice) VALUES ('place', %s, %s, %s)", (actor, text, verb))


def tie(cur, mark_id: int, issue: dict | None, words: str, actor: str) -> None:
    """A drawing as an issue's acted step (§8): the row the Done button writes, with `choice = 'place.mark:<id>'` and the
    person's own words. Written here, not through POST /actions, whose choice check would refuse it. `issue` is
    `{"alert_id": A}` or `{"event_id": E}`, the way the Done button on that issue carries it; None unties, deleting the
    row. Tying again replaces it. Deleting the drawing keeps it, because the person did act."""
    choice = f"place.mark:{mark_id}"
    cur.execute("DELETE FROM actions WHERE stage = 'acted' AND choice = %s", (choice,))
    alert_id = event_id = None
    if issue is not None:
        words = str(words or "").strip()
        if not words:
            raise HTTPException(422, "Say what you did, in your own words.")
        ok = (isinstance(issue, dict) and len(issue) == 1 and next(iter(issue)) in ("alert_id", "event_id")
              and isinstance(next(iter(issue.values())), int) and not isinstance(next(iter(issue.values())), bool))
        if not ok:
            raise HTTPException(422, 'Tie a drawing to one issue: {"alert_id": …} or {"event_id": …}.')
        (key, iid), = issue.items()
        if key == "alert_id":
            cur.execute("SELECT 1 FROM alerts WHERE id = %s", (iid,))
            if not cur.fetchone():
                raise HTTPException(404, "no such alert")
            if refusal := events_pg.decision_first(cur, iid):
                raise HTTPException(409, refusal)
            alert_id = iid
        else:
            cur.execute("SELECT 1 FROM alert_events WHERE id = %s", (iid,))
            if not cur.fetchone():
                raise HTTPException(404, "no such event")
            event_id = iid
        cur.execute("INSERT INTO actions (alert_id, event_id, stage, actor, note, choice) VALUES (%s,%s,'acted',%s,%s,%s)",
                    (alert_id, event_id, actor, words[:500], choice))
    cur.execute("UPDATE place_marks SET alert_id = %s, event_id = %s WHERE id = %s", (alert_id, event_id, mark_id))


# ---------------------------------------------------------------- reads and guards

_MAP = """SELECT p.id, p.name, p.owner, p.agent, p.shared, p.held, p.share_error, p.from_node, p.updated_at,
                 (SELECT count(*) FROM place_marks k WHERE k.map_id = p.id)::int AS marks
            FROM place_maps p"""
_MARK = """SELECT id, map_id, kind, colour, label, note, capture_id, length_m, area_m2, drawn_by, alert_id, event_id,
                  updated_at, ST_AsGeoJSON(geom)::json AS geometry FROM place_marks"""
# Measured from the geometry the row ends with; `g.geom` is the new one, NULL when the geometry did not change.
_MEASURE = """length_m = CASE WHEN m.kind = 'line' THEN ST_Length(COALESCE(g.geom, m.geom)::geography) END,
              area_m2 = CASE WHEN m.kind = 'area' THEN ST_Area(COALESCE(g.geom, m.geom)::geography) END"""


def _actor(request: Request, body: dict) -> str:
    """The page's `planetai_actor`, or an agent's X-Agent, which wins."""
    return str(request.headers.get("x-agent") or body.get("actor") or "")[:80]


def _map(cur, map_id: int) -> dict:
    """The map, if the household may edit it."""
    cur.execute("SELECT id, name, agent, from_node, shared FROM place_maps WHERE id = %s", (map_id,))
    m = cur.fetchone()
    if not m:
        raise HTTPException(404, "No such map.")
    _yours(m)
    return m


def _mark(cur, mark_id: int) -> dict:
    """The drawing with its map's name, if the household may edit it."""
    cur.execute("""SELECT k.id, k.kind, k.label, k.map_id, p.name, p.agent, p.from_node, p.shared FROM place_marks k
                   JOIN place_maps p ON p.id = k.map_id WHERE k.id = %s""", (mark_id,))
    k = cur.fetchone()
    if not k:
        raise HTTPException(404, "No such drawing.")
    _yours(k)
    return k


def _yours(m: dict) -> None:
    if m["agent"]:
        raise HTTPException(403, f"This is {m['agent']}'s map.")
    if m["from_node"]:
        raise HTTPException(403, f"This map came from {m['from_node']}; it is read-only here.")


def _house_hold(cur, shared: bool, map_id: int, mark_id: int) -> dict:
    """A drawing on the house's own res-10 cell holds a shared map: nothing goes up until Share is pressed again (§5).
    The hold is the `held` flag, which push_maps() never sends past; the sentence is only what the page shows.
    {"warn": …} or {}."""
    try:
        house = geo.home_cell(10) if shared else None
    except HTTPException:
        house = None                                       # a node with no point has no house to warn about
    if not house:
        return {}
    import h3  # noqa: PLC0415
    ring = [[lng, lat] for lat, lng in h3.cell_to_boundary(house)]
    cur.execute("SELECT ST_Intersects(geom, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)) AS on_house FROM place_marks WHERE id = %s",
                (json.dumps({"type": "Polygon", "coordinates": [ring + ring[:1]]}), mark_id))
    if not cur.fetchone()["on_house"]:
        return {}
    cur.execute("UPDATE place_maps SET held = true WHERE id = %s", (map_id,))
    return {"warn": ON_HOUSE}


def _shown(m: dict) -> dict:
    """A map as the page reads it: a held map says why in `share_error`, in today's words."""
    if m["held"]:
        m["share_error"] = ON_HOUSE
    return m


@contextmanager
def _image_here():
    """The picture a drawing names must be on this node. The foreign key decides, so this module reads no picture
    table: in step 1 that table is main.py's alone, and a test holds it there."""
    try:
        yield
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(404, "That picture is not on this node.") from None


def _one(cur, sql: str, id_: int) -> dict:
    cur.execute(sql, (id_,))
    return cur.fetchone()


# ---------------------------------------------------------------- maps

@router.get("/place/maps")
def maps_():
    """The maps, each with how many drawings it holds, and the palette the drawings' colour numbers mean."""
    with db() as con, con.cursor() as cur:
        cur.execute(_MAP + " ORDER BY p.updated_at DESC, p.id DESC")
        return {"maps": [_shown(m) for m in cur.fetchall()], "palette": {str(k): h for k, (h, _) in PALETTE.items()}}


@router.post("/place/maps")
def map_new(body: dict, request: Request):
    """{"name": "Garden plan", "owner": "Tomas"?, "actor": "Tomas"} → {"map": …}."""
    name = _text(body.get("name"), 80)
    if not name:
        raise HTTPException(422, "A map needs a name.")
    with db() as con, con.transaction(), con.cursor() as cur:
        cur.execute("INSERT INTO place_maps (name, owner) VALUES (%s, %s) RETURNING id", (name, _text(body.get("owner"), 80)))
        mid = cur.fetchone()["id"]
        ledger(cur, _actor(request, body), "drew", name, f"map:{mid}")
        return {"map": _shown(_one(cur, _MAP + " WHERE p.id = %s", mid))}


@router.patch("/place/maps/{map_id}")
def map_edit(map_id: int, body: dict, request: Request):
    """{"name"?, "owner"?, "shared"?, "confirm"?, "actor"} → {"map": …}. `"shared": true` needs a node upstream and
    `"confirm": "exact"`, which the page sends on the second press, after the warning; without it, 409 and the warning.
    It also releases a map a drawing on the house held. `"shared": false` owes the node upstream one delete."""
    sets = {}
    if "name" in body:
        sets["name"] = _text(body["name"], 80)
        if not sets["name"]:
            raise HTTPException(422, "A map needs a name.")
    if "owner" in body:
        sets["owner"] = _text(body["owner"], 80)
    with db() as con, con.transaction(), con.cursor() as cur:
        m = _map(cur, map_id)
        if sets:
            cur.execute(f"UPDATE place_maps SET {''.join(f'{k} = %({k})s, ' for k in sets)}updated_at = now() WHERE id = %(id)s",
                        {**sets, "id": map_id})
            ledger(cur, _actor(request, body), "changed", sets.get("name", m["name"]), f"map:{map_id}")
        if body.get("shared") is True:
            if not PARENT():
                raise HTTPException(409, NO_PARENT)
            if body.get("confirm") != "exact":
                raise HTTPException(409, SHARE_WARNING)
            # pushed_at cleared: the next push sends it whole, whatever the parent had before
            cur.execute("""UPDATE place_maps SET shared = true, held = false, shared_at = now(), share_error = NULL,
                             pushed_at = NULL, push_tried_at = NULL WHERE id = %s""", (map_id,))
            cur.execute("DELETE FROM place_maps_unshared WHERE map_id = %s", (map_id,))
            ledger(cur, _actor(request, body), "shared", sets.get("name", m["name"]), f"map:{map_id}")
        elif body.get("shared") is False and m["shared"]:
            _owe_delete(cur, map_id)
            cur.execute("""UPDATE place_maps SET shared = false, held = false, share_error = NULL, pushed_at = NULL,
                             push_tried_at = NULL WHERE id = %s""", (map_id,))
            ledger(cur, _actor(request, body), "unshared", sets.get("name", m["name"]), f"map:{map_id}")
        return {"map": _shown(_one(cur, _MAP + " WHERE p.id = %s", map_id))}


def _owe_delete(cur, map_id: int) -> None:
    cur.execute("INSERT INTO place_maps_unshared (map_id) VALUES (%s) ON CONFLICT (map_id) DO UPDATE SET tried_at = NULL",
                (map_id,))


@router.delete("/place/maps/{map_id}")
def map_delete(map_id: int, request: Request, confirm: str = Query(""), actor: str = Query("")):
    """?confirm=<the map's name>&actor=<who>. The map goes with every drawing on it."""
    with db() as con, con.transaction(), con.cursor() as cur:
        m = _map(cur, map_id)
        if confirm != m["name"]:
            raise HTTPException(409, "Deleting needs the map's name.")
        if m["shared"]:
            _owe_delete(cur, map_id)
        cur.execute("DELETE FROM place_maps WHERE id = %s", (map_id,))
        ledger(cur, _actor(request, {"actor": actor}), "deleted", m["name"], f"map:{map_id}")
    return {"ok": True}


_MIME = {"geojson": "application/geo+json", "kml": "application/vnd.google-earth.kml+xml", "dxf": "image/vnd.dxf"}


def _slug(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


@router.get("/place/maps/{map_id:int}.{ext}")
def map_download(map_id: int, ext: str, request: Request, actor: str = Query("")):
    """.geojson, .kml or .dxf of a map, as a file named <node>-<map>-<date>. DXF is in the metres of the UTM zone the
    node stands in, so it opens in a CAD at a scale. Any map may be read, an agent's too; each download is a ledger row."""
    if ext not in _MIME:
        raise HTTPException(404, "A map downloads as .geojson, .kml or .dxf.")
    node = os.getenv("NODE_NAME", "node")
    with db() as con, con.transaction(), con.cursor() as cur:
        cur.execute("SELECT id, name, owner FROM place_maps WHERE id = %s", (map_id,))
        m = cur.fetchone()
        if not m:
            raise HTTPException(404, "No such map.")
        if ext == "dxf":
            lat, lon = float(os.getenv("NODE_LAT", 0) or 0), float(os.getenv("NODE_LON", 0) or 0)
            if not (lat or lon):
                raise HTTPException(409, "This node has no NODE_LAT and NODE_LON yet, so there is no UTM zone to draw in.")
            epsg = utm_epsg(lon, lat)
            cur.execute("""SELECT kind, colour, label, note, ST_AsGeoJSON(ST_Transform(geom, %s))::json AS g
                             FROM place_marks WHERE map_id = %s ORDER BY id""", (epsg, map_id))
            vertices = {"Point": lambda c: [c], "LineString": lambda c: c, "Polygon": lambda c: c[0]}
            body = to_dxf([{**r, "xy": vertices[r["g"]["type"]](r["g"]["coordinates"])} for r in cur.fetchall()], epsg)
        else:
            cur.execute(_MARK + " WHERE map_id = %s ORDER BY id", (map_id,))
            fc = feature_collection(m, cur.fetchall(), node)
            body = json.dumps(fc) if ext == "geojson" else to_kml(fc)
        ledger(cur, _actor(request, {"actor": actor}), f"downloaded:{ext}", m["name"], f"map:{map_id}")
    day = datetime.now(ZoneInfo(NODE_TZ)).strftime("%Y-%m-%d")
    return Response(body, media_type=_MIME[ext], headers={
        "Content-Disposition": f'attachment; filename="{_slug(node) or "node"}-{_slug(m["name"]) or "map"}-{day}.{ext}"'})


# ---------------------------------------------------------------- drawings

@router.post("/place/maps/{map_id}/marks")
def mark_new(map_id: int, body: dict, request: Request):
    """A GeoJSON Feature, its `properties` {kind, label?, note?, colour?, image?}, and `actor` beside them → {"mark": …}."""
    with db() as con, con.transaction(), con.cursor() as cur:
        m = _map(cur, map_id)
        if refusal := check_feature(body):
            raise HTTPException(422, refusal)
        kind = body["properties"]["kind"]
        f = {"colour": 1, "label": None, "note": None, "capture_id": None, **_fields(body["properties"])}
        actor = _actor(request, body)
        with _image_here():
            cur.execute("""WITH g AS (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%(g)s::text), 4326) AS geom)
                           INSERT INTO place_marks (map_id, kind, geom, colour, label, note, capture_id, drawn_by, length_m, area_m2)
                           SELECT %(map)s, %(kind)s, geom, %(colour)s, %(label)s, %(note)s, %(capture_id)s, %(actor)s,
                                  CASE WHEN %(kind)s = 'line' THEN ST_Length(geom::geography) END,
                                  CASE WHEN %(kind)s = 'area' THEN ST_Area(geom::geography) END
                             FROM g RETURNING id""",
                        {**f, "g": _geometry(kind, body["geometry"]), "map": map_id, "kind": kind, "actor": actor or None})
        kid = cur.fetchone()["id"]
        cur.execute("UPDATE place_maps SET updated_at = now() WHERE id = %s", (map_id,))
        ledger(cur, actor, "drew", f"{f['label'] or kind} on {m['name']}", f"mark:{kid}")
        return {"mark": _one(cur, _MARK + " WHERE id = %s", kid), **_house_hold(cur, m["shared"], map_id, kid)}


@router.patch("/place/marks/{mark_id}")
def mark_edit(mark_id: int, body: dict, request: Request):
    """{"geometry"?, "label"?, "note"?, "colour"?, "image"?, "issue"?, "words"?, "actor"} → {"mark": …}.
    `issue` ties the drawing to an open issue ({"alert_id": A} or {"event_id": E}, with `words`), null unties it."""
    with db() as con, con.transaction(), con.cursor() as cur:
        k = _mark(cur, mark_id)
        f = _fields(body)
        g = None
        if "geometry" in body:
            if refusal := check_feature({"properties": {"kind": k["kind"]}, "geometry": body["geometry"]}):
                raise HTTPException(422, refusal)
            g = _geometry(k["kind"], body["geometry"])
        actor = _actor(request, body)
        if not f and g is None and "issue" not in body:
            return {"mark": _one(cur, _MARK + " WHERE id = %s", mark_id)}    # nothing to change: no row, no resend
        if "issue" in body:
            if request.headers.get("x-agent"):
                raise HTTPException(403, "Only a person ties a drawing to an issue.")   # §8: an agent's suggestion is kept first
            tie(cur, mark_id, body["issue"], body.get("words"), actor)
        with _image_here():
            cur.execute(f"""UPDATE place_marks m SET {''.join(f'{c} = %({c})s, ' for c in f)}geom = COALESCE(g.geom, m.geom),
                              {_MEASURE}, updated_at = now()
                              FROM (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%(g)s::text), 4326) AS geom) g WHERE m.id = %(id)s""",
                        {**f, "g": g, "id": mark_id})
        cur.execute("UPDATE place_maps SET updated_at = now() WHERE id = %s", (k["map_id"],))
        ledger(cur, actor, "changed", f"{f.get('label') or k['label'] or k['kind']} on {k['name']}", f"mark:{mark_id}")
        return {"mark": _one(cur, _MARK + " WHERE id = %s", mark_id),
                **(_house_hold(cur, k["shared"], k["map_id"], mark_id) if g else {})}


@router.delete("/place/marks/{mark_id}")
def mark_delete(mark_id: int, request: Request, actor: str = Query("")):
    """?actor=<who>. An act it was tied to stays in the ledger."""
    with db() as con, con.transaction(), con.cursor() as cur:
        k = _mark(cur, mark_id)
        cur.execute("DELETE FROM place_marks WHERE id = %s", (mark_id,))
        cur.execute("UPDATE place_maps SET updated_at = now() WHERE id = %s", (k["map_id"],))
        ledger(cur, _actor(request, {"actor": actor}), "deleted", f"{k['label'] or k['kind']} on {k['name']}", f"mark:{mark_id}")
    return {"ok": True}


# ---------------------------------------------------------------- sharing upstream (§5)

def push_maps() -> None:
    """Child side, every minute: each shared map changed since it last went up is sent whole (`put`), and each map
    unshared or deleted since is sent as a `delete`. Two changes inside a minute are one put. A failed send keeps the
    map shared, says why in `share_error` and waits an hour; a 404 is a parent from before maps. A map a drawing on the
    house holds is never sent until the household presses Share again."""
    if not PARENT():          # the function, not the setting: a bare PARENT is always truthy
        return
    node = os.getenv("NODE_NAME", "node")
    with db() as con, con.transaction(), con.cursor() as cur:
        # one snapshot: a drawing on the house and the hold it writes are seen together or not at all
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        cur.execute("SELECT map_id FROM place_maps_unshared WHERE tried_at IS NULL OR tried_at < now() - interval '1 hour'")
        out = [(r["map_id"], "delete", None, None) for r in cur.fetchall()]
        cur.execute("""SELECT id, name, owner, updated_at FROM place_maps
                        WHERE shared AND NOT held AND from_node IS NULL AND (pushed_at IS NULL OR updated_at > pushed_at)
                          AND (share_error IS NULL OR push_tried_at < now() - interval '1 hour')""")
        for m in cur.fetchall():
            cur.execute(_MARK + " WHERE map_id = %s ORDER BY id", (m["id"],))
            out.append((m["id"], "put", feature_collection(m, cur.fetchall(), node), m["updated_at"]))
    for map_id, op, fc, snap in out:
        try:
            r = httpx.post(f"{PARENT()}/place/maps/received",
                           json={"schema": _SCHEMA, "node": node, "map_id": map_id, "op": op, "geojson": fc},
                           headers={"Authorization": f"Bearer {PARENT_TOKEN()}"} if PARENT_TOKEN() else {}, timeout=30)
            if r.status_code != 404:
                r.raise_for_status()
            error = NOT_YET if r.status_code == 404 else None
        except Exception as e:  # noqa: BLE001
            log.warning("map %s %s to parent failed: %s", map_id, op, e)
            error = NOT_SENT
        with db() as con, con.cursor() as cur:
            if op == "delete" and error == NOT_SENT:
                cur.execute("UPDATE place_maps_unshared SET tried_at = now() WHERE map_id = %s", (map_id,))
            elif op == "delete":                           # sent, or a parent with no maps to delete it from
                cur.execute("DELETE FROM place_maps_unshared WHERE map_id = %s", (map_id,))
            else:
                # pushed_at is the snapshot's own time, so a change made while this was in flight goes next minute;
                # `held` is not touched, so a hold written meanwhile stays a hold
                cur.execute("""UPDATE place_maps SET push_tried_at = now(), share_error = %(err)s,
                                 pushed_at = CASE WHEN %(err)s::text IS NULL THEN %(snap)s ELSE pushed_at END
                                WHERE id = %(id)s AND shared""", {"err": error, "snap": snap, "id": map_id})


@received.post("/place/maps/received")
def map_received(body: dict, authorization: str = Header("")):
    """Parent side. {schema, node, map_id, op: "put" | "delete", geojson}: a child's shared map, kept whole under
    (from_node, remote_id) and read-only here. A put replaces every drawing; a delete removes the map. Measures are
    PostGIS's own again; a picture's number is the child's and means nothing here, so it is dropped."""
    if not AGG_TOKEN():
        raise HTTPException(403, "this node accepts no children: set AGGREGATE_TOKEN in .env and give it to them")
    if not _bearer_ok(authorization, AGG_TOKEN()):
        raise HTTPException(401, "bad or missing Authorization: Bearer <AGGREGATE_TOKEN>")
    child, rid, op = _text(body.get("node"), 80), body.get("map_id"), body.get("op")
    if not child or isinstance(rid, bool) or not isinstance(rid, int) or op not in ("put", "delete"):
        raise HTTPException(422, "A shared map says its node, its map_id and put or delete.")
    with db() as con, con.transaction(), con.cursor() as cur:
        if op == "delete":
            cur.execute("DELETE FROM place_maps WHERE from_node = %s AND remote_id = %s", (child, rid))
            return {"ok": True}
        fc = body.get("geojson") if isinstance(body.get("geojson"), dict) else {}
        feats = fc.get("features") if isinstance(fc.get("features"), list) else []
        for f in feats:
            if refusal := check_feature(f):
                raise HTTPException(422, refusal)
        cur.execute("""INSERT INTO place_maps (name, owner, from_node, remote_id) VALUES (%s, %s, %s, %s)
                       ON CONFLICT (from_node, remote_id) DO UPDATE SET name = EXCLUDED.name, owner = EXCLUDED.owner,
                                                                        updated_at = now()
                       RETURNING id""", (_text(fc.get("map"), 80) or "map", _text(fc.get("owner"), 80), child, rid))
        mid = cur.fetchone()["id"]
        cur.execute("DELETE FROM place_marks WHERE map_id = %s", (mid,))
        for f in feats:
            p, kind = f["properties"], f["properties"]["kind"]
            colour = p.get("colour") if p.get("colour") in PALETTE and not isinstance(p.get("colour"), bool) else 1
            cur.execute("""WITH g AS (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%(g)s::text), 4326) AS geom)
                           INSERT INTO place_marks (map_id, kind, geom, colour, label, note, drawn_by, length_m, area_m2)
                           SELECT %(map)s, %(kind)s, geom, %(colour)s, %(label)s, %(note)s, %(by)s,
                                  CASE WHEN %(kind)s = 'line' THEN ST_Length(geom::geography) END,
                                  CASE WHEN %(kind)s = 'area' THEN ST_Area(geom::geography) END FROM g""",
                        {"g": _geometry(kind, f["geometry"]), "map": mid, "kind": kind, "colour": colour,
                         "label": _text(p.get("label"), 80), "note": _text(p.get("note"), 500), "by": _text(p.get("drawn_by"), 80)})
    return {"ok": True, "marks": len(feats)}


def daily_readings() -> None:
    """Hourly, once a local day: how many drawings the household has made and how much ground they cover, on the
    node's own `place-gis` survey sensor. Both are `private` (config/channels.yml), so no road out of the house carries
    them. The reading's time is the start of the node's local day (the session runs in NODE_TZ), so a later call the
    same day updates that row and a duplicate is impossible. An agent's map and a child's are not the household's."""
    with db() as con, con.transaction(), con.cursor() as cur:
        cur.execute("""INSERT INTO sensors (sensor_id, source, name, kind, local, indoor, cadence)
                       VALUES ('place-gis', 'place', 'What this home has drawn', 'survey', TRUE, FALSE, 'P1D')
                       ON CONFLICT (sensor_id) DO NOTHING""")
        cur.execute("""SELECT count(*) AS marks, coalesce(sum(k.area_m2), 0) AS marked_area_m2
                         FROM place_marks k JOIN place_maps m ON m.id = k.map_id
                        WHERE m.agent IS NULL AND m.from_node IS NULL""")
        n = cur.fetchone()
        for metric in ("marks", "marked_area_m2"):
            cur.execute("INSERT INTO readings (ts, sensor_id, metric, value) VALUES (date_trunc('day', now()), 'place-gis', %s, %s) "
                        "ON CONFLICT (sensor_id, metric, ts) DO UPDATE SET value = EXCLUDED.value", (metric, float(n[metric])))
