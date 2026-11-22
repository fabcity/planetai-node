"""GET /calibrate: off, the gates, a pair that is shown, a bad entry that costs only itself, a refusal, a station
reference, and that the route only reads.

Run: PACKS_DIR=packs PYTHONPATH=app python3 tests/test_calibrate_routes.py
The mounted module (what app/packs.py::routers() loaded) has `q` and `_now` replaced: the answers come from fake rows
shaped as db.q returns them (a datetime as its ISO string). Nothing here opens a database.
"""
import os
import time
from datetime import datetime, timedelta, timezone

os.environ.update(PACKS_DIR="packs", ADMIN_TOKEN="admin-tok", NODE_LAT="-8.8", NODE_LON="115.1",
                  DATABASE_URL="postgresql://unused/never-connected")
os.environ.pop("NODE_TZ", None)

try:
    from fastapi.testclient import TestClient
except ImportError:
    print("calibrate routes: skipped (pip install -r app/requirements.txt)")
    raise SystemExit(0)

import settings  # noqa: E402
ROWS = {"PACKS_ENABLED": "", "SHARE_LEVEL": "open", "CALIBRATE_PAIRS": ""}
settings._cache = {"at": time.time() + 1e9, "rows": ROWS}

import main  # noqa: E402
import packs  # noqa: E402

RT = packs.ROUTES["calibrate"]
NOW = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)
RT._now = lambda: NOW
SEEN = []
M = 1 / 111320                                   # a degree of latitude is 111320 m: this many degrees is a metre


def sensor(sid, source="own", dm=0.0, lat=-8.8, indoor=False, meta=None):
    return {"sensor_id": sid, "source": source, "name": sid.upper(), "lat": None if lat is None else lat + dm * M,
            "lon": None if lat is None else 115.1, "indoor": indoor, "kind": "sensor", "meta": meta or {}}


DB = {"a": sensor("a"), "b": sensor("b", dm=30), "far": sensor("far", dm=812), "nocoord": sensor("nocoord", lat=None),
      "st": sensor("st", source="baliairdispatch", dm=20, meta={"network": "AQICN", "official": True, "from_index": True}),
      "c": sensor("c", dm=500), "d": sensor("d", dm=520)}
ROLE = [{"source": s, "metric": "pm25", "unit": "µg/m³"} for s in ("own", "baliairdispatch")]
STATS = [{"sensor_id": i, "source": "own", "name": i.upper(), "lat": DB[i]["lat"], "lon": DB[i]["lon"], "indoor": False,
          "metric": "pm25"} for i in ("a", "b", "c", "d")]
X = lambda h: 5 + (h * 7) % 11                   # noqa: E731  a sensor that moves, so a line can be fitted
HOURS = [NOW - timedelta(hours=h) for h in range(1, 30 * 24)]


def q(sql, *args):
    SEEN.append(sql)
    s = " ".join(sql.split())
    if "FROM sensors WHERE sensor_id" in s:
        return [DB[i] for i in args[0] if i in DB]
    if "FROM channel_roles" in s:
        return ROLE
    if "FROM sensors s JOIN stats" in s:
        return STATS
    if "FROM readings_1h" in s:
        ids, _, start, end = args
        assert end <= NOW and (end - start) <= timedelta(days=RT.core.READ_DAYS) + timedelta(seconds=1), (start, end)
        out = []
        for i, t in enumerate(HOURS):
            if start <= t < end:
                v = X(i)
                for sid in ids:
                    out.append({"sensor_id": sid, "bucket": t.isoformat(), "mean": v if sid == ids[0] else 2 + 1.5 * v})
        return out
    raise AssertionError(s)


RT.q = q
c = TestClient(main.app)
H = {"Authorization": "Bearer admin-tok"}
get = lambda: c.get("/calibrate", headers=H)     # noqa: E731

# ---- off: nothing asked
r = get()
assert r.status_code == 200 and r.json() == {"state": "off", "rows": [], "could": []} and SEEN == [], (r.text, SEEN)
print("  a blank key answers off and reads nothing")

# ---- the gates
ROWS["CALIBRATE_PAIRS"] = "a b pm25 2026-10-01"
ROWS["PACKS_ENABLED"] = "forecast"
assert get().status_code == 404, "the pack left out of PACKS_ENABLED is a 404"
ROWS["PACKS_ENABLED"] = ""
assert c.get("/calibrate").status_code in (401, 403), "in no share list: a household on open does not get it"
print("  404 while the pack is left out, and not on any share list")

# ---- one good pair
r = get()
assert r.status_code == 200, r.text
j = r.json()
assert j["state"] == "ok" and len(j["rows"]) == 1, j
row = j["rows"][0]
assert row["shown"] is True and row["why"] is None, row
assert row["corrected"] == round(2 + 1.5 * row["measured"], 2), row
assert row["reference"] == {"id": "b", "name": "B", "own": True, "network": None, "official": None, "from_index": None}
assert row["metres"] == 30 and row["line"]["b"] == 1.5 and row["line"]["a"] == 2.0 and row["unit"] == "µg/m³", row
assert row["sensor"] == {"id": "a", "name": "A"} and row["since"] == "2026-10-01" and row["until"] is None
assert row["checked"]["corrected"] == 0.0 and row["checked"]["measured"] > 0 and row["paired_hours"] > 168, row
assert row["hour"] and row["last_paired"] and j["could"] == [{"a": {"id": "c", "name": "C"}, "b": {"id": "d", "name": "D"},
                                                              "metric": "pm25", "metres": 20}], j["could"]
print("  one good pair: the line, the checks, the corrected number, and one pair that could be named (c and d, not a and b)")

# ---- a bad entry costs only itself
ROWS["CALIBRATE_PAIRS"] = "a b pm25 2026-10-01; nonsense; a b pm25 2026-10-02"
r = get()
rows = r.json()["rows"]
assert r.status_code == 200 and len(rows) == 3, r.text
assert rows[0]["shown"] is True
assert rows[1] == {"entry": "nonsense", "shown": False, "why": {"reason": "malformed", "problem": "fields"}}, rows[1]
assert rows[2] == {"entry": "a b pm25 2026-10-02", "shown": False, "why": {"reason": "malformed", "problem": "duplicate"}}, rows[2]
print("  a malformed entry and a duplicate are rows of their own, in order, and the first still answers")

# ---- a refusal reads no hours
ROWS["CALIBRATE_PAIRS"] = "a far pm25 2026-10-01"
del SEEN[:]
row = get().json()["rows"][0]
assert row["why"] == {"reason": "refused", "test": "apart", "metres": 812} and row["shown"] is False and row["metres"] == 812, row
assert not [s for s in SEEN if "readings_1h" in s], "a refused pair asks for no hours"
print("  sensors 812 m apart are refused before any hour is read")

# ---- a station as the reference, a sensor with no coordinates
ROWS["CALIBRATE_PAIRS"] = "a st pm25 2026-10-01; nocoord b pm25 2026-10-01"
rows = get().json()["rows"]
assert rows[0]["reference"] == {"id": "st", "name": "ST", "own": False, "network": "AQICN", "official": True,
                                "from_index": True}, rows[0]
assert rows[0]["shown"] is True, rows[0]
assert rows[1]["metres"] is None and rows[1]["why"] is None and rows[1]["shown"] is True, rows[1]
print("  a station reference carries its network, and a sensor with no coordinates is accepted")

# ---- the same twice, then off
ROWS["CALIBRATE_PAIRS"] = "a b pm25 2026-10-01"
assert get().json() == get().json(), "worked out on each call, the same each time"
ROWS["CALIBRATE_PAIRS"] = ""
assert get().json() == {"state": "off", "rows": [], "could": []}
print("  the same twice, and off again as soon as the key is blank")

# ---- the route only reads
assert SEEN and all(" ".join(s.split()).startswith("SELECT") for s in SEEN), "a query that is not a SELECT"
print("calibrate routes: every check passed")
