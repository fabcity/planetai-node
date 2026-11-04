"""The household's maps on the Place door: named maps, the drawings on them, their rows in the ledger, and a drawing
tied to an issue as the issue's acted step. docs/superpowers/specs/2026-11-04-place-light-gis-design.md §5 and §8.

Every route here is the household's alone, at every SHARE_LEVEL: none is on an allowlist in app/auth.py, and the router
checks the admin or act token itself because the middleware also lets BACKUP_TOKEN through, and a NAS's read token
must not draw or write ρ (the same reason POST /actions checks its own). PostGIS measures every drawing: `length_m`
and `area_m2` come from `geom::geography` on every insert and update, so the page computes no distance.

An agent's own map (`agent` set) is refused to the household's edits in this pull request; agents become writers in
the third (§7). Never import app/main.py from here: it starts a second MQTT client.
"""
from __future__ import annotations

import json
import math
import os
from contextlib import contextmanager

import psycopg

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

import events_pg
from auth import ACT_TOKEN, _bearer_ok, _is_local
from db import db


def _household(request: Request, authorization: str = Header("")) -> None:
    if not (_is_local(request) or _bearer_ok(authorization, os.getenv("ADMIN_TOKEN", "").strip(), ACT_TOKEN())):
        raise HTTPException(401, "Maps need the household's token.")


router = APIRouter(dependencies=[Depends(_household)])

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

_MAP = """SELECT p.id, p.name, p.owner, p.agent, p.shared, p.share_error, p.from_node, p.updated_at,
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
    cur.execute("SELECT id, name, agent FROM place_maps WHERE id = %s", (map_id,))
    m = cur.fetchone()
    if not m:
        raise HTTPException(404, "No such map.")
    if m["agent"]:
        raise HTTPException(403, f"This is {m['agent']}'s map.")
    return m


def _mark(cur, mark_id: int) -> dict:
    """The drawing with its map's name, if the household may edit it."""
    cur.execute("""SELECT k.id, k.kind, k.label, k.map_id, p.name, p.agent FROM place_marks k
                   JOIN place_maps p ON p.id = k.map_id WHERE k.id = %s""", (mark_id,))
    k = cur.fetchone()
    if not k:
        raise HTTPException(404, "No such drawing.")
    if k["agent"]:
        raise HTTPException(403, f"This is {k['agent']}'s map.")
    return k


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
        return {"maps": cur.fetchall(), "palette": {str(k): h for k, (h, _) in PALETTE.items()}}


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
        return {"map": _one(cur, _MAP + " WHERE p.id = %s", mid)}


@router.patch("/place/maps/{map_id}")
def map_edit(map_id: int, body: dict, request: Request):
    """{"name"?, "owner"?, "actor"} → {"map": …}. Sharing joins this route with the fourth task."""
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
        return {"map": _one(cur, _MAP + " WHERE p.id = %s", map_id)}


@router.delete("/place/maps/{map_id}")
def map_delete(map_id: int, request: Request, confirm: str = Query(""), actor: str = Query("")):
    """?confirm=<the map's name>&actor=<who>. The map goes with every drawing on it."""
    with db() as con, con.transaction(), con.cursor() as cur:
        m = _map(cur, map_id)
        if confirm != m["name"]:
            raise HTTPException(409, "Deleting needs the map's name.")
        cur.execute("DELETE FROM place_maps WHERE id = %s", (map_id,))
        ledger(cur, _actor(request, {"actor": actor}), "deleted", m["name"], f"map:{map_id}")
    return {"ok": True}


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
        return {"mark": _one(cur, _MARK + " WHERE id = %s", kid)}


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
        return {"mark": _one(cur, _MARK + " WHERE id = %s", mark_id)}


@router.delete("/place/marks/{mark_id}")
def mark_delete(mark_id: int, request: Request, actor: str = Query("")):
    """?actor=<who>. An act it was tied to stays in the ledger."""
    with db() as con, con.transaction(), con.cursor() as cur:
        k = _mark(cur, mark_id)
        cur.execute("DELETE FROM place_marks WHERE id = %s", (mark_id,))
        cur.execute("UPDATE place_maps SET updated_at = now() WHERE id = %s", (k["map_id"],))
        ledger(cur, _actor(request, {"actor": actor}), "deleted", f"{k['label'] or k['kind']} on {k['name']}", f"mark:{mark_id}")
    return {"ok": True}
