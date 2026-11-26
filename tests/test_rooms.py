"""Rooms in the household's words (Tomas, 14 Oct 2026).

Structural half reads init.sql: the room becomes the sensor's name in the database, whatever writes the row, and the
platform's name is kept. Request half drives PATCH /sensors/{sid} and GET /sensors with the database stubbed.

Run: PYTHONPATH=app python3 tests/test_rooms.py
"""
import logging
import os
import re
import time

SQL = open("init.sql").read()

# ---------------------------------------------------------------- the trigger: one place, every writer
m = re.search(r"CREATE OR REPLACE FUNCTION sensors_room_is_the_name\(\).*?END \$\$;", SQL, re.S)
assert m, "the room is made the name in the database, so a poll, a pack and core all keep it"
body = m.group(0)
assert "NEW.name := NEW.room" in body and "NEW.source_name := NEW.name" in body
assert "TG_OP = 'INSERT' OR NEW.name IS DISTINCT FROM OLD.room" in body, "a rename must not save the old room as the platform's name"
assert "BEFORE INSERT OR UPDATE ON sensors FOR EACH ROW" in SQL and "DROP TRIGGER IF EXISTS sensors_room ON sensors" in SQL
assert SQL.index("ADD COLUMN IF NOT EXISTS room TEXT") < SQL.index("CREATE TRIGGER sensors_room"), "the column exists before the trigger"
print("schema: a room is the sensor's name whatever writes the row; the platform's name is kept")

# ---------------------------------------------------------------- the routes
logging.disable(logging.WARNING)
os.environ.update(ADMIN_TOKEN="admin-tok", ACT_TOKEN="act-tok", NODE_NAME="bayu-2", NODE_LAT="-8.6478291",
                  NODE_LON="115.1385412", DATABASE_URL="postgresql://unused/never-connected")
import settings                                    # noqa: E402
settings._cache = {"at": time.time() + 1e9, "rows": {"SHARE_LEVEL": "open"}}
import main                                       # noqa: E402
from fastapi.testclient import TestClient         # noqa: E402

DONE = []
SENSORS = {"sc-1": {"sensor_id": "sc-1", "name": "Sensor 3", "room": None, "source_name": None}}


class Cur:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, params=()):
        DONE.append((sql, params)); self.params = params
    def fetchone(self):
        if len(self.params) == 1:                       # SELECT name: does the sensor exist, and what was it called
            s = SENSORS.get(self.params[0])
            return {"name": s["name"]} if s else None
        room, _, sid = self.params
        s = SENSORS.get(sid)
        if not s:
            return None
        # what the trigger and the CASE do, in Python: enough to check the route hands them the right values
        s["source_name"] = s["source_name"] or s["name"]
        s["room"], s["name"] = room, room or s["source_name"]
        return dict(s)


class Con:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def cursor(self): return Cur()


main.db = lambda: Con()
c = TestClient(main.app)
ADMIN, ACT = {"Authorization": "Bearer admin-tok"}, {"Authorization": "Bearer act-tok"}
assert c.patch("/sensors/sc-1", json={"room": "Kids"}).status_code in (401, 403)
assert c.patch("/sensors/sc-1", json={"room": "Kids"}, headers=ACT).status_code == 401, "admin only: it renames what the house reads"
r = c.patch("/sensors/sc-1", json={"room": "  Kids  "}, headers=ADMIN)
assert r.status_code == 200 and r.json()["sensor"]["name"] == "Kids" and r.json()["sensor"]["source_name"] == "Sensor 3", r.text
assert any(q.startswith("UPDATE sensors") and p[0] == "Kids" for q, p in DONE), "trimmed before it is stored"
assert DONE[-1] == ("UPDATE alert_events SET rooms = array_replace(rooms, %s, %s) WHERE %s = ANY(rooms)",
                    ("Sensor 3", "Kids", "Sensor 3")), "the rename follows into the event episodes"
assert c.patch("/sensors/sc-1", json={"room": "x" * 80}, headers=ADMIN).json()["sensor"]["room"] == "x" * 40, "forty characters at most"
assert c.patch("/sensors/sc-1", json={"room": 3}, headers=ADMIN).status_code == 422
r = c.patch("/sensors/sc-1", json={"room": None}, headers=ADMIN)
assert r.json()["sensor"]["name"] == "Sensor 3" and DONE[-2][1][0] is None, "null gives the platform's name back"
assert c.patch("/sensors/nope", json={"room": "Kids"}, headers=ADMIN).status_code == 404

ROWS = [{"sensor_id": "sc-1", "source": "smartcitizen", "name": "Kids", "room": "Kids", "source_name": "Sensor 3",
         "lat": -8.81, "lon": 115.16, "indoor": True, "local": True, "custody": True, "kind": "sensor", "scale": "community",
         "cadence": "PT5M", "meta": {}}]
main.q = lambda sql, *a: [dict(x) for x in ROWS]
assert c.get("/sensors", headers=ADMIN).json()[0]["source_name"] == "Sensor 3"
pub = TestClient(main.app, client=("192.168.4.20", 5000)).get("/sensors").json()[0]
assert "room" not in pub and "source_name" not in pub, "which room is which is the household's, not a stranger's"
print("routes: admin names a room, trimmed and capped, null gives the platform's name back; a stranger never reads it")
print("rooms: every check passed")

# ---- a child's sensors, for a reader without the token (Tomas 25 Nov 2026): "a home nearby", never its node's name or
# a kit number (a Smart Citizen kit's page says where it stands), the same in /sensors and /observations; the
# household's own token reads the real ids.
import json  # noqa: E402

_CHILD = {"source": "child", "room": None, "source_name": None, "lat": None, "lon": None, "indoor": False, "local": False,
          "custody": True, "kind": "child", "scale": "home", "cadence": "PT1H", "meta": None,
          "metric": "pm25", "value": 4.0, "ts": "2026-11-25T09:00:00+08:00"}
ROWS = [dict(ROWS[0], metric="pm25", value=3.0, ts="2026-11-25T09:00:00+08:00"),
        dict(_CHILD, sensor_id="ungasan-home/sc-19874", name="ungasan-home/sc-19874"),
        dict(_CHILD, sensor_id="ungasan-home/sc-19236", name="ungasan-home/sc-19236")]
main.q = lambda sql, *a: [dict(x) for x in ROWS]
stranger = TestClient(main.app, client=("192.168.4.20", 5000))
for _p in ("/sensors", "/observations"):
    _b = json.dumps(stranger.get(_p).json())
    assert "ungasan-home" not in _b and "19236" not in _b and "19874" not in _b, (_p, _b[:400])
_S = {r["sensor_id"]: r for r in stranger.get("/sensors").json() if r.get("kind") == "child"}
_O = {r["sensor_id"]: r for r in stranger.get("/observations").json() if r.get("kind") == "child"}
assert set(_S) == set(_O) == {"home-1/outdoor-1", "home-1/outdoor-2"}, (sorted(_S), sorted(_O))
assert _S["home-1/outdoor-1"]["name"] == _O["home-1/outdoor-1"]["name"] == "a home nearby · outdoor 1", _S
assert "ungasan-home/sc-19236" in json.dumps(c.get("/sensors", headers=ADMIN).json()), "the token reads the real ids"
_two = main._child_alias([{"sensor_id": s, "name": s, "kind": "child"} for s in ("b-home/x", "a-home/y", "a-home/z")],
                         ["a-home/y", "a-home/z", "b-home/x"])
assert [(r["sensor_id"], r["name"]) for r in _two] == [("home-2/outdoor-1", "home 2 nearby · outdoor 1"),
                                                       ("home-1/outdoor-1", "home 1 nearby · outdoor 1"),
                                                       ("home-1/outdoor-2", "home 1 nearby · outdoor 2")], _two
print("children: a stranger reads a home nearby, numbered the same in /sensors and /observations; the token reads the ids")

# ---- the same aliases wherever a stranger's answer can carry a child's id (final review, 25 Nov 2026): /export at every
# SHARE_LEVEL, and /readings, /sparks and the rest at open pass through _unhoused, whose pairs now hold the children.
_KIDS = ["ungasan-home/sc-19874", "ungasan-home/sc-19236"]
assert main._child_names(_KIDS) == {"ungasan-home/sc-19236": ("home-1/outdoor-1", "a home nearby · outdoor 1"),
                                    "ungasan-home/sc-19874": ("home-1/outdoor-2", "a home nearby · outdoor 2")}, main._child_names(_KIDS)


class _Cur:
    def __init__(self): self.rows = []
    def execute(self, sql, *a): self.rows = [{"sensor_id": k} for k in _KIDS] if "kind = 'child'" in sql else []
    def fetchall(self): return self.rows
    def __enter__(self): return self
    def __exit__(self, *a): return False


class _Con:
    def cursor(self): return _Cur()
    def __enter__(self): return self
    def __exit__(self, *a): return False


_db0 = main.db
main.db = lambda: _Con()
main._HOUSE.update(at=0.0, map=[])
_pairs = dict(main._house_labels())
assert _pairs.get("ungasan-home/sc-19236") == "home-1/outdoor-1", _pairs
_body = main._unhoused(b'[{"sensor_id": "ungasan-home/sc-19236", "metric": "pm25"}]', "/readings")
assert b"ungasan-home" not in _body and b"home-1/outdoor-1" in _body, _body
main.db = _db0; main._HOUSE.update(at=0.0, map=[])
_name = main._export_namer(_KIDS)
assert _name({"sensor_id": "ungasan-home/sc-19236", "local": False, "indoor": False, "kind": "child"}) == "home-1/outdoor-1"
assert _name({"sensor_id": "bad-sc-1", "local": False, "indoor": False, "kind": "sensor"}) == "bad-sc-1", "a public station keeps its id"
assert _name({"sensor_id": "sc-1", "local": True, "indoor": True, "kind": "sensor"}) == "indoor-1", "the house's own as before"
print("children: /export and every stranger's answer carry a home nearby, never a child's kit id")
