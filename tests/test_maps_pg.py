"""Place maps on a real database: the two tables, their CHECKs, the cascade and the widened actions stage.

On 4 Nov 2026 the light GIS put place_maps and place_marks in core, with init.sql enabling PostGIS ahead of them.
This holds the schema's own rules where they live, in the database: a mark is a marker, line, area or note, a colour
is 1 to 6, deleting a map takes its drawings with it, and the actions ledger accepts the stage `place`. The routes of app/maps.py are driven through the app: tokens, PostGIS's
own measures, the ledger's one row per minute, a drawing tied to an issue, an agent's map refused, and a shared
map's trip upstream: the warning, one put per change, one delete, the hold on the house, and the parent's read-only copy. Needs a
Postgres with init.sql applied, at RHO_PG_URL (CI's lint job starts one, on the PostGIS image); without it the
suite skips.
Run: RHO_PG_URL=postgresql://planetai:x@127.0.0.1:5432/planetai PYTHONPATH=app PACKS_DIR=packs python3 tests/test_maps_pg.py
"""
import os
import sys

url = os.getenv("RHO_PG_URL")
if not url:
    print("  - maps on a real database skipped (set RHO_PG_URL to a Postgres with init.sql applied)")
    sys.exit(0)
import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

con = psycopg.connect(url, row_factory=dict_row)          # one transaction, rolled back: nothing stays
cur = con.cursor()


def table_exists(name):
    cur.execute("SELECT to_regclass(%s) AS t", (name,))
    return cur.fetchone()["t"] is not None


def count(name):
    cur.execute(f"SELECT count(*) AS n FROM {name}")
    return cur.fetchone()["n"]


def raises(sql, *args):
    """True if the statement is refused by a constraint; a savepoint keeps the outer transaction alive."""
    try:
        with con.transaction():
            cur.execute(sql, args)
    except (psycopg.errors.CheckViolation, psycopg.errors.IntegrityError):
        return True
    return False


assert table_exists("place_maps") and table_exists("place_marks"), "init.sql creates both tables"
assert table_exists("place_maps_unshared"), "init.sql keeps the deletes still owed to the node upstream"
cur.execute("SELECT extname FROM pg_extension WHERE extname = 'postgis'")
assert cur.fetchone(), "init.sql enabled PostGIS"
print("  both tables exist and PostGIS is on")

cur.execute("INSERT INTO place_maps (name) VALUES ('t') RETURNING id")
mid = cur.fetchone()["id"]
cur.execute("SELECT shared, held, from_node, remote_id, pushed_at, push_tried_at FROM place_maps WHERE id = %s", (mid,))
row = cur.fetchone()
assert row == {"shared": False, "held": False, "from_node": None, "remote_id": None, "pushed_at": None, "push_tried_at": None}, row
cur.execute("""INSERT INTO place_marks (map_id, kind, geom) VALUES
  (%s, 'area', ST_GeomFromText('POLYGON((115.167 -8.819,115.168 -8.819,115.168 -8.818,115.167 -8.819))',4326))""", (mid,))
cur.execute("SELECT colour FROM place_marks WHERE map_id = %s", (mid,))
assert cur.fetchone()["colour"] == 1, "colour defaults to 1"
cur.execute("INSERT INTO actions (stage, actor, note, choice) VALUES ('place','t','x','drew')")   # the check allows it
print("  a map, an area on it and a `place` action are accepted")

for bad in ("INSERT INTO place_marks (map_id, kind, geom) VALUES (%s,'circle',ST_Point(0,0,4326))",
            "INSERT INTO place_marks (map_id, kind, geom, colour) VALUES (%s,'marker',ST_Point(0,0,4326),7)",
            "INSERT INTO place_marks (map_id, kind, geom, colour) VALUES (%s,'marker',ST_Point(0,0,4326),0)"):
    assert raises(bad, mid), bad          # kind and colour CHECKs hold
assert raises("INSERT INTO place_marks (map_id, kind, geom) VALUES (999999999,'marker',ST_Point(0,0,4326))"), "a mark needs its map"
assert raises("INSERT INTO actions (stage, actor, note) VALUES ('nonsense','t','x')"), "the old stages still guard the ledger"
for stage in ("acknowledged", "acted", "measured", "settings", "decided", "dismissed"):
    cur.execute("INSERT INTO actions (stage, actor, note) VALUES (%s,'t','x')", (stage,))   # none of them was dropped
print("  kind, colour, the map reference and the action stages hold")

cur.execute("INSERT INTO place_maps (name, from_node, remote_id) VALUES ('a', 'n1', 5)")
assert raises("INSERT INTO place_maps (name, from_node, remote_id) VALUES ('b', 'n1', 5)"), "UNIQUE (from_node, remote_id)"
cur.execute("INSERT INTO place_maps (name) VALUES ('c'), ('d')")            # NULLs are drawn-here maps and never collide
print("  a pulled map is unique per node and remote id; maps drawn here are not")

cur.execute("DELETE FROM place_maps WHERE id = %s", (mid,))
cur.execute("SELECT count(*) AS n FROM place_marks WHERE map_id = %s", (mid,))
assert cur.fetchone()["n"] == 0, "deleting a map takes its drawings"
print("  deleting a map deletes its drawings")

con.rollback()

# ---------------------------------------------------------------- the routes (app/maps.py), through the app
# TestClient's peer is "testclient", not loopback: every request here is a client on the house WiFi, so each carries
# a token unless the token is the subject. These requests commit; what they wrote is deleted at the end.
import logging  # noqa: E402
import time  # noqa: E402

logging.disable(logging.WARNING)                         # httpx logs every request at INFO

os.environ.update(DATABASE_URL=url, ADMIN_TOKEN="admin-tok", ACT_TOKEN="act-tok")
import settings  # noqa: E402

SET = {"BACKUP_TOKEN": "backup-tok"}
settings._cache.update(at=time.time() + 1e9, rows=SET)     # the settings table, held still for the test
import main  # noqa: E402 — importing the app starts nothing (main.start)
from fastapi.testclient import TestClient  # noqa: E402

c = TestClient(main.app)
H = {"Authorization": "Bearer admin-tok"}
ac = psycopg.connect(url, row_factory=dict_row, autocommit=True)


def one(sql, *args):
    return ac.execute(sql, args).fetchone()


assert c.get("/place/maps").status_code in (401, 403), "a stranger on the WiFi reads no maps"
assert c.get("/place/maps", headers={"Authorization": "Bearer backup-tok"}).status_code == 401, \
    "the NAS's read token passes SHARE_LEVEL, and it must not draw"
assert c.get("/place/maps", headers={"Authorization": "Bearer act-tok"}).status_code == 200
print("  maps answer the household's tokens only")

r = c.post("/place/maps", json={"name": "  ", "actor": "Tomas"}, headers=H)
assert r.status_code == 422 and r.json()["detail"] == "A map needs a name.", r.text
r = c.post("/place/maps", json={"name": "Garden plan", "owner": "Tomas", "actor": "Tomas"}, headers=H)
assert r.status_code == 200, r.text
mid = r.json()["map"]["id"]
RING = [[115.167, -8.819], [115.168, -8.819], [115.168, -8.818], [115.167, -8.818], [115.167, -8.819]]


def draw(kind, gtype, coords, **props):
    return c.post(f"/place/maps/{mid}/marks", headers=H, json={"type": "Feature", "actor": "Tomas",
                  "properties": {"kind": kind, **props}, "geometry": {"type": gtype, "coordinates": coords}})


r = draw("area", "Polygon", [RING], label="Rain garden", colour=3)
assert r.status_code == 200, r.text
mark = r.json()["mark"]
kid = mark["id"]
real = one("SELECT ST_Area(geom::geography) AS a FROM place_marks WHERE id = %s", kid)["a"]
assert abs(mark["area_m2"] - real) / real < 0.01 and mark["length_m"] is None, (mark, real)
assert mark["drawn_by"] == "Tomas" and mark["colour"] == 3 and mark["geometry"]["type"] == "Polygon", mark
r = draw("line", "LineString", [[115.167, -8.819], [115.168, -8.819]])
assert r.status_code == 200 and 105 < r.json()["mark"]["length_m"] < 115, r.text      # 0.001° of longitude at 8.8° S
r = draw("area", "Polygon", [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]])
assert r.status_code == 422 and r.json()["detail"] == "That area crosses itself. Draw its corners in order around it."
assert draw("marker", "Point", [115.167, -8.819], colour=7).json()["detail"] == "A colour is a number from 1 to 6."
assert c.post("/place/maps/999999999/marks", headers=H, json={}).status_code == 404
r = draw("marker", "Point", [115.167, -8.819], image=999999999)
assert r.status_code == 404 and r.json()["detail"] == "That picture is not on this node.", r.text
print("  a drawing is stored with PostGIS's own area and length; a crossed area and a seventh colour are refused")

for label in ("Rain garden, west", "Rain garden, west edge"):
    r = c.patch(f"/place/marks/{kid}", json={"label": label, "actor": "Tomas"}, headers=H)
    assert r.status_code == 200 and r.json()["mark"]["label"] == label, r.text
rows = ac.execute("SELECT choice, note FROM actions WHERE stage = 'place' AND right(note, %s) = %s ORDER BY ts",
                  (len(f"(mark {kid})"), f"(mark {kid})")).fetchall()
assert [x["choice"] for x in rows] == ["drew", "changed"], rows
r = c.patch(f"/place/marks/{kid}", json={"geometry": {"type": "Polygon", "coordinates": [RING[:3] + [RING[0]]]},
                                         "actor": "Tomas"}, headers=H)
assert abs(r.json()["mark"]["area_m2"] - real / 2) / real < 0.01, "a new outline is measured again"
print("  the same drawing changed inside a minute is one `changed` row in the ledger; a new outline is measured again")

A = one("INSERT INTO alerts (ts, rule_id, sensor_id, level, text) VALUES (now(), 't', 'sc-1', 'act', 'x') RETURNING id")["id"]
r = c.patch(f"/place/marks/{kid}", json={"issue": {"alert_id": A}, "words": " ", "actor": "Tomas"}, headers=H)
assert r.status_code == 422 and r.json()["detail"] == "Say what you did, in your own words.", r.text
r = c.patch(f"/place/marks/{kid}", json={"issue": {"alert_id": A}, "words": "dug the swale"},
            headers={**H, "X-Agent": "claude"})
assert r.status_code == 403, "only a person ties a drawing to an issue"
r = c.patch(f"/place/marks/{kid}", json={"issue": {"alert_id": A}, "words": "dug the swale", "actor": "Tomas"}, headers=H)
assert r.status_code == 200 and r.json()["mark"]["alert_id"] == A, r.text
acted = lambda: ac.execute("SELECT alert_id, event_id, actor, note FROM actions WHERE stage = 'acted' AND choice = %s",  # noqa: E731
                           (f"place.mark:{kid}",)).fetchall()
assert acted() == [{"alert_id": A, "event_id": None, "actor": "Tomas", "note": "dug the swale"}], acted()
c.patch(f"/place/marks/{kid}", json={"issue": {"alert_id": A}, "words": "dug the swale, planted vetiver", "actor": "Tomas"}, headers=H)
assert [x["note"] for x in acted()] == ["dug the swale, planted vetiver"], "tying again replaces the row, never a second"
r = c.patch(f"/place/marks/{kid}", json={"issue": None, "actor": "Tomas"}, headers=H)
assert r.status_code == 200 and r.json()["mark"]["alert_id"] is None and acted() == [], "untying deletes the row"
assert c.patch(f"/place/marks/{kid}", json={"issue": {"alert_id": 999999999}, "words": "x"}, headers=H).status_code == 404
E = one("INSERT INTO alert_events (issue, kind, level, opened_at, last_seen_at) VALUES ('heat', 'sustained', 'act', now(), now()) RETURNING id")["id"]
c.patch(f"/place/marks/{kid}", json={"issue": {"event_id": E}, "words": "shaded the west wall", "actor": "Tomas"}, headers=H)
assert acted() == [{"alert_id": None, "event_id": E, "actor": "Tomas", "note": "shaded the west wall"}], acted()
assert c.delete(f"/place/marks/{kid}?actor=Tomas", headers=H).status_code == 200
assert len(acted()) == 1, "deleting the drawing keeps the act: the person did act"
print("  tying: needs the person's words, writes the Done row, untying deletes it, deleting the drawing keeps it")

SET["DECISION_REQUIRED"] = "1"
A2 = one("INSERT INTO alerts (ts, rule_id, sensor_id, level, text) VALUES (now(), 't', 'sc-1', 'act', 'x') RETURNING id")["id"]
k2 = draw("marker", "Point", [115.167, -8.819]).json()["mark"]["id"]
tied = c.patch(f"/place/marks/{k2}", json={"issue": {"alert_id": A2}, "words": "closed the windows", "actor": "Tomas"}, headers=H)
done = c.post("/actions", json={"alert_id": A2, "stage": "acted", "actor": "Tomas", "note": "closed the windows"}, headers=H)
assert tied.status_code == done.status_code == 409 and tied.json()["detail"] == done.json()["detail"], (tied.text, done.text)
assert "DECISION_REQUIRED" in tied.json()["detail"]
SET["DECISION_REQUIRED"] = "0"
print("  where the Done button needs a decision first, tying is refused with the same status and sentence")

AG = one("INSERT INTO place_maps (name, agent) VALUES ('Shade study', 'ask') RETURNING id")["id"]
r = c.patch(f"/place/maps/{AG}", json={"name": "mine now"}, headers=H)
assert r.status_code == 403 and r.json()["detail"] == "This is ask's map.", r.text
assert c.post(f"/place/maps/{AG}/marks", json={"type": "Feature", "properties": {"kind": "marker"},
              "geometry": {"type": "Point", "coordinates": [0, 0]}}, headers=H).json()["detail"] == "This is ask's map."
print("  an agent's map is refused to the household's edits")

r = c.patch(f"/place/maps/{mid}", json={"name": "Garden", "actor": "Tomas"}, headers=H)
assert r.status_code == 200 and r.json()["map"]["name"] == "Garden"
g = c.get("/place/maps", headers=H).json()
assert set(g["palette"]) == {"1", "2", "3", "4", "5", "6"} and g["palette"]["3"].startswith("#"), g["palette"]
m = next(x for x in g["maps"] if x["id"] == mid)
assert set(m) == {"id", "name", "owner", "agent", "shared", "held", "share_error", "from_node", "marks", "updated_at"}, m
assert m["marks"] == 2 and m["owner"] == "Tomas", m
r = c.delete(f"/place/maps/{mid}?confirm=garden", headers=H)
assert r.status_code == 409 and r.json()["detail"] == "Deleting needs the map's name.", r.text
assert c.delete(f"/place/maps/{mid}?confirm=Garden&actor=Tomas", headers=H).status_code == 200
assert one("SELECT count(*) AS n FROM place_marks WHERE map_id = %s", mid)["n"] == 0
assert one("SELECT choice FROM actions WHERE stage = 'place' AND note LIKE %s ORDER BY ts DESC LIMIT 1", f"%(map {mid})")["choice"] == "deleted"
print("  the list carries counts and the palette; deleting a map needs its name and takes its drawings")

# ---------------------------------------------------------------- the downloads
# The node's own point picks the UTM zone: 8.8 S, 115.2 E is zone 50 south (EPSG 32750), central meridian 117 E.
os.environ.update(NODE_NAME="bayu-ungasan", NODE_LAT="-8.8271", NODE_LON="115.15709")
DL = c.post("/place/maps", json={"name": "Rain & Garden / plan", "actor": "Tomas"}, headers=H).json()["map"]["id"]
for kind, gtype, coords, props in (("area", "Polygon", [RING], {"label": "Rain garden", "colour": 3}),
                                   ("line", "LineString", [[115.167, -8.819], [115.168, -8.819]], {}),
                                   ("marker", "Point", [115.167, -8.819], {"label": "Pozo"}),
                                   ("note", "Point", [115.1675, -8.8185], {"note": "Water is here"})):
    assert c.post(f"/place/maps/{DL}/marks", headers=H, json={"type": "Feature", "actor": "Tomas",
                  "properties": {"kind": kind, **props}, "geometry": {"type": gtype, "coordinates": coords}}).status_code == 200

r = c.get(f"/place/maps/{DL}.geojson", headers=H)
assert r.status_code == 200 and r.headers["content-type"].startswith("application/geo+json"), r.headers
assert r.headers["content-disposition"] == f'attachment; filename="bayu-ungasan-rain-garden-plan-{time.strftime("%Y-%m-%d", time.gmtime())}.geojson"', r.headers
fc = r.json()
assert fc["schema"] == "planetai.place.map/v0" and fc["node"] == "bayu-ungasan" and fc["map"] == "Rain & Garden / plan"
assert len(fc["features"]) == 4 and fc["features"][0]["properties"]["area_m2"] > 1000, fc["features"][0]

r = c.get(f"/place/maps/{DL}.kml", headers=H)
assert r.status_code == 200 and r.headers["content-type"].startswith("application/vnd.google-earth.kml+xml")
assert r.headers["content-disposition"].endswith('.kml"')
import xml.etree.ElementTree as ET  # noqa: E402
assert len(ET.fromstring(r.text).findall(".//{http://www.opengis.net/kml/2.2}Placemark")) == 4

r = c.get(f"/place/maps/{DL}.dxf", headers=H)
assert r.status_code == 200 and r.headers["content-disposition"].endswith('.dxf"') and r.text.startswith("999\nEPSG:32750, metres")
assert r.text.count("\nPOLYLINE\n") == 2 and r.text.count("\nPOINT\n") == 2 and r.text.count("\nTEXT\n") == 3
want = one("SELECT ST_X(g) AS x, ST_Y(g) AS y FROM (SELECT ST_Transform(ST_SetSRID(ST_Point(115.167, -8.819), 4326), 32750) AS g) t")
body = r.text.split("\nPOINT\n")[1].split("\n")                 # 8 layer, MARKERS, 62, ACI, 10, x, 20, y …
x, y = float(body[body.index("10") + 1]), float(body[body.index("20") + 1])
assert abs(x - want["x"]) < 0.01 and abs(y - want["y"]) < 0.01, (x, y, want)
assert abs(y - 9.02e6) < 0.05e6 and abs(x - 300000) < 10000, "metres on the node's own zone: 117 E is 500000, this is 1.9 degrees west"
assert c.get(f"/place/maps/{DL}.pdf", headers=H).status_code == 404
assert c.get("/place/maps/999999999.dxf", headers=H).status_code == 404
assert c.get(f"/place/maps/{DL}.dxf").status_code in (401, 403), "a download is the household's alone"
assert c.get(f"/place/maps/{DL}.dxf", headers={"Authorization": "Bearer backup-tok"}).status_code == 401
assert c.get(f"/place/maps/{DL}.dxf", headers=H).status_code == 200      # a second one, inside the minute
assert c.get(f"/place/maps/{DL}.kml?actor=Tomas", headers=H).status_code == 200
assert one("SELECT choice, actor FROM actions WHERE stage = 'place' AND note LIKE %s ORDER BY ts DESC LIMIT 1", f"%(map {DL})") \
    == {"choice": "downloaded:kml", "actor": "Tomas"}
assert one("SELECT count(*) AS n FROM actions WHERE choice = 'downloaded:dxf' AND note LIKE %s", f"%(map {DL})")["n"] == 1, "two dxf downloads in a minute are one row"
AGD = one("INSERT INTO place_maps (name, agent) VALUES ('Shade', 'ask') RETURNING id")["id"]
assert c.get(f"/place/maps/{AGD}.geojson", headers=H).status_code == 200, "the household may read an agent's map, only not edit it"
ac.execute("DELETE FROM place_maps WHERE id IN (%s, %s)", (DL, AGD))
print("  a map downloads as GeoJSON, KML and DXF, in UTM metres on the node's zone, one ledger row each")

# ---------------------------------------------------------------- sharing upstream (§5)
# The child's posts go to a recorder, never a real node; the same app then plays the parent for /place/maps/received.
import httpx  # noqa: E402
import maps  # noqa: E402

sent, answer, real_post = [], [200], httpx.post


def recorder(url, json=None, headers=None, timeout=None):
    sent.append({"url": url, "body": json, "auth": (headers or {}).get("Authorization")})
    return httpx.Response(answer[0], request=httpx.Request("POST", url))


httpx.post = recorder
WARN = ("Sharing sends every drawing in this map, at its exact place, with its labels, notes and measures, to the node "
        "upstream, where the people holding its token can see it. Press Share again to send it.")
HOUSE = "This drawing sits on the house. Press Share again to send the map with it."
NOT_YET = "The node upstream does not take maps yet."
SH = c.post("/place/maps", json={"name": "Walk to the beach", "actor": "Tomas"}, headers=H).json()["map"]["id"]
share = lambda body, mid=SH: c.patch(f"/place/maps/{mid}", json={"actor": "Tomas", **body}, headers=H)  # noqa: E731
row = lambda mid=SH: one("SELECT shared, held, share_error, push_tried_at, updated_at FROM place_maps WHERE id = %s", mid)  # noqa: E731


def push():
    sent.clear()
    maps.push_maps()
    return [(s["body"]["op"], s["body"]["map_id"]) for s in sent]


r = share({"shared": True, "confirm": "exact"})
assert r.status_code == 409 and r.json()["detail"] == "There is no node upstream to share with. Set PARENT in Set up first.", r.text
assert push() == [], "no PARENT, nothing sent"
SET.update(PARENT_API_URL="http://parent.test", PARENT_TOKEN="kid-tok")
r = share({"shared": True})
assert r.status_code == 409 and r.json()["detail"] == WARN, r.text
assert row()["shared"] is False and push() == [], "the warning sends nothing"
r = share({"shared": True, "confirm": "exact"})
assert r.status_code == 200 and r.json()["map"]["shared"] is True, r.text
assert one("SELECT choice FROM actions WHERE stage = 'place' AND note LIKE %s ORDER BY ts DESC LIMIT 1", f"%(map {SH})")["choice"] == "shared"
print("  sharing needs a node upstream, then a second press after the warning")

SK = c.post(f"/place/maps/{SH}/marks", headers=H, json={"type": "Feature", "actor": "Tomas", "properties": {"kind": "line"},
            "geometry": {"type": "LineString", "coordinates": [[115.167, -8.819], [115.168, -8.819]]}}).json()
assert "warn" not in SK, "a drawing away from the house warns of nothing"
SK = SK["mark"]["id"]
c.patch(f"/place/marks/{SK}", json={"label": "Path", "actor": "Tomas"}, headers=H)
assert push() == [("put", SH)], sent
s = sent[0]
assert s["url"] == "http://parent.test/place/maps/received" and s["auth"] == "Bearer kid-tok", s
assert set(s["body"]) == {"schema", "node", "map_id", "op", "geojson"} and s["body"]["schema"] == "planetai.place.map/v0"
assert s["body"]["node"] == "bayu-ungasan" and s["body"]["geojson"]["map"] == "Walk to the beach"
assert [f["properties"]["label"] for f in s["body"]["geojson"]["features"]] == ["Path"], "both changes in the one put"
assert push() == [], "nothing changed since: nothing sent"
print("  a shared map changed twice goes up once, whole, with the parent's token")

before = row()["updated_at"]
n_changed = one("SELECT count(*) AS n FROM actions WHERE choice = 'changed'")["n"]
r = c.patch(f"/place/marks/{SK}", json={"actor": "Tomas"}, headers=H)
assert r.status_code == 200 and r.json()["mark"]["label"] == "Path", r.text
assert row()["updated_at"] == before and one("SELECT count(*) AS n FROM actions WHERE choice = 'changed'")["n"] == n_changed
assert push() == [], "a PATCH that changes nothing writes nothing and resends nothing"
print("  an empty drawing PATCH writes nothing")

answer[0] = 404
c.patch(f"/place/marks/{SK}", json={"note": "low tide only", "actor": "Tomas"}, headers=H)
assert push() == [("put", SH)]
assert row()["shared"] is True and row()["share_error"] == NOT_YET, row()
assert push() == [], "a refused map waits an hour"
ac.execute("UPDATE place_maps SET push_tried_at = now() - interval '61 minutes' WHERE id = %s", (SH,))
answer[0] = 200
assert push() == [("put", SH)] and row()["share_error"] is None, row()
print("  a parent that predates maps is said so; the map stays shared and is tried again after an hour")

r = c.post(f"/place/maps/{SH}/marks", headers=H, json={"type": "Feature", "actor": "Tomas", "properties": {"kind": "marker"},
           "geometry": {"type": "Point", "coordinates": [115.15709, -8.8271]}})          # the node's own point
assert r.status_code == 200 and r.json()["warn"] == HOUSE, r.text
assert row()["held"] is True and push() == [], "a drawing on the house holds the map"
m = next(x for x in c.get("/place/maps", headers=H).json()["maps"] if x["id"] == SH)
assert m["held"] is True and m["share_error"] == HOUSE, m
ac.execute("UPDATE place_maps SET push_tried_at = now() - interval '2 hours' WHERE id = %s", (SH,))
assert push() == [], "the hour's retry never releases a held map"
# The hold is a flag, not the sentence: a row whose words were written by an older release, and a sentence reworded
# since, both stay held.
ac.execute("UPDATE place_maps SET share_error = 'an older wording of the warning' WHERE id = %s", (SH,))
was, maps.ON_HOUSE = maps.ON_HOUSE, "Reworded: this drawing is on the house."
assert push() == [], "a held map stays held whatever its share_error says"
m = next(x for x in c.get("/place/maps", headers=H).json()["maps"] if x["id"] == SH)
assert m["share_error"] == "Reworded: this drawing is on the house.", "the sentence is rendered from the flag"
maps.ON_HOUSE = was
assert share({"shared": True}).json()["detail"] == WARN
r = share({"shared": True, "confirm": "exact"}).json()["map"]
assert r["share_error"] is None and r["held"] is False, r
assert push() == [("put", SH)] and len(sent[0]["body"]["geojson"]["features"]) == 2
print("  a drawing on the house's own cell holds a shared map until Share is pressed again")

r = share({"shared": False})
assert r.status_code == 200 and r.json()["map"]["shared"] is False
assert one("SELECT choice FROM actions WHERE stage = 'place' AND note LIKE %s ORDER BY ts DESC LIMIT 1", f"%(map {SH})")["choice"] == "unshared"
assert push() == [("delete", SH)] and sent[0]["body"]["geojson"] is None, sent
assert push() == [], "one delete"
SD = c.post("/place/maps", json={"name": "Gone soon", "actor": "Tomas"}, headers=H).json()["map"]["id"]
share({"shared": True, "confirm": "exact"}, SD)
assert push() == [("put", SD)]
c.delete(f"/place/maps/{SD}?confirm=Gone soon&actor=Tomas", headers=H)
assert push() == [("delete", SD)] and push() == [], "deleting a shared map sends one delete"
print("  unsharing or deleting a shared map sends one delete")

# The same app as the parent: AGGREGATE_TOKEN is what its children hold.
SET["AGGREGATE_TOKEN"] = "agg-tok"
AGG = {"Authorization": "Bearer agg-tok"}
FEAT = lambda label, x: {"type": "Feature", "properties": {"kind": "marker", "label": label, "colour": 2, "image": 41},  # noqa: E731
                         "geometry": {"type": "Point", "coordinates": [x, -8.8]}}
doc = {"schema": "planetai.place.map/v0", "node": "kid", "map_id": 7, "op": "put",
       "geojson": {"type": "FeatureCollection", "map": "Kid's garden", "owner": "Ana", "features": [FEAT("a", 115.1), FEAT("b", 115.2)]}}
recv = lambda d, h=AGG: c.post("/place/maps/received", json=d, headers=h)  # noqa: E731
assert recv(doc, H).status_code == 401, "a household token is not a child's"
assert recv(doc, {}).status_code == 401
assert recv({**doc, "geojson": {**doc["geojson"], "features": [{"type": "Feature", "properties": {"kind": "line"},
            "geometry": {"type": "Point", "coordinates": [0, 0]}}]}}).status_code == 422
r = recv(doc)
assert r.status_code == 200, r.text
RV = one("SELECT id, name, owner FROM place_maps WHERE from_node = 'kid' AND remote_id = 7")
assert RV["name"] == "Kid's garden" and RV["owner"] == "Ana", RV
assert one("SELECT count(*) AS n FROM place_marks WHERE map_id = %s AND capture_id IS NULL", RV["id"])["n"] == 2, \
    "the child's picture numbers mean nothing here"
r = recv({**doc, "geojson": {**doc["geojson"], "features": [FEAT("c", 115.3)]}})
assert r.status_code == 200 and one("SELECT id FROM place_maps WHERE from_node = 'kid' AND remote_id = 7")["id"] == RV["id"]
assert [x["label"] for x in ac.execute("SELECT label FROM place_marks WHERE map_id = %s", (RV["id"],)).fetchall()] == ["c"]
m = next(x for x in c.get("/place/maps", headers=H).json()["maps"] if x["id"] == RV["id"])
assert m["from_node"] == "kid" and m["marks"] == 1, m
RO = "This map came from kid; it is read-only here."
assert share({"name": "mine"}, RV["id"]).json() == {"detail": RO}
assert share({"name": "mine"}, RV["id"]).status_code == 403
assert c.post(f"/place/maps/{RV['id']}/marks", json=FEAT("d", 115.4), headers=H).json()["detail"] == RO
RK = one("SELECT id FROM place_marks WHERE map_id = %s", RV["id"])["id"]
assert c.patch(f"/place/marks/{RK}", json={"label": "x"}, headers=H).json()["detail"] == RO
assert c.get(f"/place/maps/{RV['id']}.geojson", headers=H).status_code == 200, "a received map downloads"
assert recv({**doc, "op": "delete", "geojson": None}).status_code == 200
assert one("SELECT count(*) AS n FROM place_maps WHERE from_node = 'kid'")["n"] == 0
httpx.post = real_post
print("  the parent keeps a child's map whole, read-only, and lets it go on delete")

ac.execute("DELETE FROM place_maps WHERE id = %s", (SH,))
ac.execute("DELETE FROM actions WHERE stage = 'place' OR choice LIKE 'place.mark:%%' OR alert_id IN (%s, %s)", (A, A2))
ac.execute("DELETE FROM place_maps WHERE id IN (%s, %s)", (mid, AG))
ac.execute("DELETE FROM alerts WHERE id IN (%s, %s)", (A, A2))
ac.execute("DELETE FROM alert_events WHERE id = %s", (E,))
print("maps: every check passed")
sys.exit(0)
