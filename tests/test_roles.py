"""The node's role is a bootstrap key: fixed at install, read at start, never a settings row.

    PYTHONPATH=app python3 tests/test_roles.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
os.environ.pop("NODE_KIND", None)

import placewords  # noqa: E402
import settings  # noqa: E402

# the four kinds fold to two roles
for k, want in [("home", "private"), ("business", "private"), ("", "private"),
                ("community", "community"), ("district", "community"), (" Community ", "community")]:
    assert placewords.role(k) == want, (k, placewords.role(k))
os.environ["NODE_KIND"] = "district"
assert placewords.role() == "community" and not placewords.is_house()
os.environ["NODE_KIND"] = "home"
assert placewords.role() == "private" and placewords.is_house()

# NODE_KIND is a bootstrap key, not a runtime one
assert "NODE_KIND" not in settings.RUNTIME
assert not settings.writable("NODE_KIND")
assert settings.BOOTSTRAP_GROUP["NODE_KIND"] == "basics"
os.environ["NODE_KIND"] = "community"
row = next(r for r in settings.describe(unlocked=False)["bootstrap"] if r["key"] == "NODE_KIND")
assert "planetai role private" in row["help"] and "Community node" in row["help"], row

# a stale settings row never wins over the environment
real = settings.get
settings.get = lambda k, d="": "home"
try:
    assert placewords.kind() == "community"
finally:
    settings.get = real

# update moves a stray row into .env and deletes it
src = (ROOT / "update.sh").read_text()
assert "NODE_KIND" in src and "DELETE FROM settings WHERE key = 'NODE_KIND'" in src
print("ok  roles")

# ---------------------------------------------------------------- a community node shows no indoor sensor without a token
# Driven as tests/test_share.py drives it: TestClient's peer is not loopback, so a request with no token is a stranger.
try:
    from fastapi.testclient import TestClient
except ImportError:
    print("roles: request checks skipped (pip install -r app/requirements.txt)")
    raise SystemExit(0)
import json  # noqa: E402
import logging  # noqa: E402
import time  # noqa: E402
logging.disable(logging.WARNING)
os.environ.setdefault("PACKS_DIR", str(ROOT / "packs"))   # the issues' declarations live in the packs
os.environ.update(ADMIN_TOKEN="admin-tok", NODE_LAT="-8.6478291", NODE_LON="115.1385412", NODE_NAME="bayu-2",
                  DATABASE_URL="postgresql://unused/never-connected")
settings._cache = {"at": time.time() + 1e9, "rows": {"SHARE_LEVEL": "open"}}
import main  # noqa: E402

assert main._drop_indoor({"sensors": [{"sensor_id": "sc-1"}, {"sensor_id": "sc-2"}],
                          "stats": {"sc-1": {"pm25": 1}, "sc-2": {}}}, {"sc-1"}) == \
    {"sensors": [{"sensor_id": "sc-2"}], "stats": {"sc-2": {}}}
assert main._drop_indoor([{"a": [{"sensor_id": "sc-1"}]}, 3, "x"], {"sc-1"}) == [{"a": []}, 3, "x"]

_IN = {"sensor_id": "ag-in", "source": "airgradient", "name": "ag-in", "lat": -8.6, "lon": 115.1, "indoor": True,
       "local": True, "custody": True, "kind": "sensor", "scale": "community", "cadence": "PT5M", "meta": None}
_OUT = dict(_IN, sensor_id="ag-out", name="Garden", indoor=False)
_HOURLY = [{"bucket": "2026-11-25T10:00:00+08:00", "sensor_id": s["sensor_id"], "local": True, "indoor": s["indoor"],
            "kind": "sensor", "scale": "community", "metric": "pm25", "mean": 1.0, "min": 1.0, "max": 1.0, "n": 12}
           for s in (_IN, _OUT)]
_ALERTS = [{"ts": "2026-11-25T10:00:00+08:00", "rule_id": "indoor_pm25_high", "level": "act", "text": "Smoke inside",
            "sensor_id": "ag-in", "id": 1, "buttons": None, "acted_at": None},
           {"ts": "2026-11-25T11:00:00+08:00", "rule_id": "outdoor_pm25_high", "level": "act", "text": "Smoke outside",
            "sensor_id": "ag-out", "id": 2, "buttons": None, "acted_at": None}]


def _q(sql, *a):
    if "extract(hour" in sql:
        return [{"hour": 10, "indoor": 5.0, "outdoor": 3.0, "n": 2}]
    if "count(DISTINCT" in sql:
        return [{"days": 1, "first": None, "last": None}]
    if "generate_series" in sql and "AS indoor" in sql:
        return [{"bucket": "2026-11-25T10:00:00+08:00", "indoor": 5.0, "outdoor": 3.0, "model": None}]
    if "FROM readings_1h" in sql:
        return [dict(r) for r in _HOURLY]
    if "FROM readings WHERE" in sql:
        return [{"ts": "2026-11-25T10:00:00+08:00", "value": 1.0}]
    if "FROM reports" in sql:
        return [{"id": 1, "ts": "2026-11-25T10:00:00+08:00", "text": "Kids room smoky at dinner", "sent": True}]
    if "FROM alerts" in sql:
        return [dict(r) for r in _ALERTS]
    return [dict(_IN), dict(_OUT)] if "FROM sensors" in sql else []


main.q = _q


class _Cur:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, *a): self.sql = sql
    def fetchall(self):
        if "local AND indoor" in self.sql:
            return [{"sensor_id": "ag-in", "name": "ag-in", "source_name": None}]
        if "source_name" in self.sql:
            return [{"room": None, "name": s["name"], "source_name": None} for s in (_IN, _OUT)]
        return []


class _Con(_Cur):
    def cursor(self): return _Cur()
    def transaction(self): return _Cur()


main.db = lambda: _Con()
main.index.cells = lambda cur: []
main.index.rho = lambda cur: None
main._offers = lambda: []
client = TestClient(main.app)


def _reset():
    main._INDOOR.update(at=0.0, ids=set()); main._HOUSE.update(at=0.0, map=[])


os.environ["NODE_KIND"] = "community"; _reset()
r = client.get("/sensors")
assert r.status_code == 200 and [s["sensor_id"] for s in r.json()] == ["ag-out"], r.text
assert all(not s.get("indoor") for s in r.json())
assert len(client.get("/sensors", headers={"Authorization": "Bearer admin-tok"}).json()) == 2, "a token reads them all"
assert TestClient(main.app, client=("127.0.0.1", 51000)).get("/sensors").json()[0]["indoor"], "this machine reads them all"
ex = client.get("/export?day=2026-11-25").json()["hourly"]
assert ex and not any(r["sensor"].startswith("indoor-") or r["indoor"] for r in ex), ex
ex = client.get("/export?day=2026-11-25", headers={"Authorization": "Bearer admin-tok"}).json()["hourly"]
assert not any(r["indoor"] for r in ex), "the export travels whoever asked: no indoor row even with a token"

# fix round 1 · every route that answers from indoor sensors, for a stranger on a community node
TOK = {"Authorization": "Bearer admin-tok"}
assert client.get("/history?sensor_id=ag-in&metric=pm25").json() == [], "an indoor sensor's history reads as unknown"
assert client.get("/history?sensor_id=ag-out&metric=pm25").json(), "an outdoor sensor's history still answers"
assert client.get("/history?sensor_id=ag-in&metric=pm25", headers=TOK).json(), "a token reads it"
assert client.get("/series").json()["indoor"] == [None], "the series' indoor side is null"
assert client.get("/series", headers=TOK).json()["indoor"] == [5.0]
assert [h["indoor"] for h in client.get("/shape").json()["hours"]] == [None], "the shape's indoor side is null"
assert client.get("/shape", headers=TOK).json()["hours"][0]["indoor"] == 5.0
assert client.get("/report/latest").json()["text"] is None, "the keeper's report is not public"
assert client.get("/report/latest", headers=TOK).json()["text"]
_raw = TestClient(main.app, raise_server_exceptions=False)
for m, path in (("get", "/ask/status"), ("post", "/ask")):
    r = getattr(_raw, m)(path, **({"json": {"q": "hi"}} if m == "post" else {}))
    assert r.status_code == 403 and "token" in r.json()["error"], (path, r.status_code, r.text)
    assert getattr(_raw, m)(path, headers=TOK, **({"json": {"q": "hi"}} if m == "post" else {})).status_code != 403
al = [a["rule"] for a in client.get("/export?day=2026-11-25", headers=TOK).json()["alerts"]]
assert al == ["outdoor_pm25_high"], f"an indoor sensor's alert left in the export: {al}"
import tempfile  # noqa: E402
from pathlib import Path as _P  # noqa: E402
main.EXPORTS = _P(tempfile.mkdtemp())
(main.EXPORTS / "bayu-2").mkdir()
_old = {"day": "2026-11-20", "hourly": [{"sensor": "indoor-1", "indoor": True, "mean": 9.0},
                                        {"sensor": "outdoor-1", "indoor": False, "mean": 3.0},
                                        {"sensor": "indoor-2", "mean": 8.0}]}
(main.EXPORTS / "bayu-2" / "2026-11-20.json").write_text(json.dumps(_old))
r = client.get("/exports/bayu-2/2026-11-20.json", headers=TOK)
assert [x["sensor"] for x in r.json()["hourly"]] == ["outdoor-1"], r.text
assert "2026-11-20.json" in r.headers.get("content-disposition", ""), r.headers
# /issues: the engine reads no indoor row, so no room place and nothing derived from it
import issues.api as _ia  # noqa: E402
from issues import engine as _eng, load as _load  # noqa: E402
_snap = json.loads((ROOT / "app/issues/fixtures/node1-2026-10-06-figures.json").read_text())
_ids = {r["sensor_id"] for r in _snap["stats"] if r.get("local") and r.get("indoor")}


settings._cache["rows"]["NODE_ISSUES"] = ",".join(_load())


def _rooms(cur):
    out = _eng.compute(cur, settings, _load(), now=datetime.fromisoformat(_snap["as_of"]))
    return [k for k, v in out["issues"].items() if (v.get("stack") or {}).get("room", {}) and
            ((v["stack"].get("room") or {}).get("value") is not None or (v.get("series") or {}).get("room"))]


from datetime import datetime  # noqa: E402
assert _rooms(_eng.Replay(_snap)), "the fixture has a room to hide"
assert not _rooms(_ia._NoIndoor(_eng.Replay(_snap), _ids)), "the room reached a stranger's /issues"
_seen = []
_real_compute, _real_days = _eng.compute, _eng.days
_eng.compute = lambda cur, *a, **k: _seen.append(cur) or {}
_eng.days = lambda cur, *a, **k: _seen.append(cur) or {}
import events_wire  # noqa: E402
_real_live, events_wire.live = events_wire.live, lambda *a, **k: {}
try:
    for path in ("/issues", "/issues/days"):
        _seen.clear(); client.get(path)
        assert _seen and isinstance(_seen[0], _ia._NoIndoor), (path, _seen)
        _seen.clear(); client.get(path, headers=TOK)
        assert _seen and not isinstance(_seen[0], _ia._NoIndoor), path
finally:
    _eng.compute, _eng.days, events_wire.live = _real_compute, _real_days, _real_live
# round 2 · alert events: alert_events carries no sensor column, so an event at the room place, or naming an indoor
# kit, is left out whole for a stranger, open or cleared, in /issues and in /issues/days
from datetime import timedelta, timezone  # noqa: E402
_now = datetime.now(timezone.utc)
_EV = [{"id": 1, "issue": "air", "kind": "smoke", "level": "act", "opened_at": _now - timedelta(hours=1),
        "last_seen_at": _now, "cleared_at": None, "peak": 80.0, "rooms": ["ag-in"], "places": ["room"], "action_id": None},
       {"id": 2, "issue": "air", "kind": "smoke", "level": "act", "opened_at": _now - timedelta(hours=3),
        "last_seen_at": _now - timedelta(hours=2), "cleared_at": _now - timedelta(hours=2), "peak": 60.0,
        "rooms": ["Kids"], "places": ["room"], "action_id": None},
       {"id": 3, "issue": "air", "kind": "haze", "level": "warn", "opened_at": _now - timedelta(hours=1),
        "last_seen_at": _now, "cleared_at": None, "peak": 40.0, "rooms": [], "places": ["yard"], "action_id": None},
       {"id": 4, "issue": "air", "kind": "smoke", "level": "warn", "opened_at": _now - timedelta(hours=1),
        "last_seen_at": _now, "cleared_at": None, "peak": 50.0, "rooms": ["Kids"], "places": ["yard"], "action_id": None}]


class _EvCur(_Cur):
    connection = _Con()
    def fetchall(self):
        if "FROM alert_events" in self.sql:
            return [dict(e) for e in _EV]
        if "FROM sensors WHERE local AND indoor" in self.sql:
            return [{"sensor_id": "ag-in", "name": "Kids", "source_name": None}]
        return super().fetchall()
    def fetchone(self):
        if "current_setting('TimeZone')" in self.sql:
            return {"tz": "Asia/Makassar", "hour": 10}
        return None


class _EvCon(_Con):
    def cursor(self): return _EvCur()


settings._cache["rows"]["ALERT_ENGINE"] = "events"
_db0 = main.db; main.db = lambda: _EvCon(); _reset()
_got = {}
_real_compute = _eng.compute
_eng.compute = lambda cur, *a, **k: _got.update(ev=k.get("events")) or {}
try:
    def _evids(headers=None):
        _got.clear(); client.get("/issues", headers=headers or {})
        ev = _got["ev"] or {}
        assert "error" not in ev, ev
        return sorted(e["id"] for e in (ev.get("open") or []) + (ev.get("recent") or []))
    assert _evids(TOK) == [1, 2, 3, 4], _evids(TOK)
    assert _evids() == [3], f"a room event reached a stranger's /issues: {_evids()}"
    _days = lambda h=None: sorted(e["id"] for e in client.get("/issues/days", headers=h or {}).json()["events"])  # noqa: E731
    assert _days(TOK) == [1, 2, 3, 4], _days(TOK)
    assert _days() == [3], f"a room event reached a stranger's /issues/days: {_days()}"
    assert not {"rooms", "places"} & set(client.get("/issues/days", headers=TOK).json()["events"][0]), \
        "the days events keep their own keys: rooms and places are read for the filter, not sent"
finally:
    _eng.compute = _real_compute; main.db = _db0; settings._cache["rows"].pop("ALERT_ENGINE")
# the wrapper filters every way a row can be read
_w = _ia._NoIndoor(type("C", (), {"rows": [{"sensor_id": "x"}, {"sensor_id": "ag-in"}], "fetchall": lambda s: list(s.rows),
                                  "fetchone": lambda s: s.rows.pop(0) if s.rows else None,
                                  "fetchmany": lambda s, n=1: [s.rows.pop(0) for _ in range(min(n, len(s.rows)))],
                                  "__iter__": lambda s: iter(s.rows)})(), {"ag-in"})
assert _ia._NoIndoor(None, {"ag-in"}, {"Kids"})._in({"rooms": ["Kids"], "places": ["yard"]}), "an event naming an indoor kit"
assert not _ia._NoIndoor(None, {"ag-in"}, {"Kids"})._in({"rooms": ["Garden"], "places": ["yard"]})
assert list(_w) == [{"sensor_id": "x"}] and _w.fetchmany(5) == [{"sensor_id": "x"}], "iteration bypassed the filter"

# fail closed: a community node that has never read its indoor sensors answers a stranger 503
_reset(); _db = main.db
main.db = lambda: (_ for _ in ()).throw(RuntimeError("no database yet"))
r = client.get("/sensors")
assert r.status_code == 503 and "starting" in r.json()["error"], r.text
assert client.get("/sensors", headers=TOK).status_code == 200
assert client.get("/health").status_code == 200, "/health still says the node is up"
os.environ["NODE_KIND"] = "home"
assert client.get("/sensors").status_code == 200, "a private node does not wait for the indoor read"
main.db = _db

os.environ["NODE_KIND"] = "home"; _reset()
assert any(s.get("indoor") for s in client.get("/sensors").json()), "a private node is unchanged"
assert client.get("/history?sensor_id=ag-in&metric=pm25").json() and client.get("/series").json()["indoor"] == [5.0]
assert client.get("/shape").json()["hours"][0]["indoor"] == 5.0 and client.get("/report/latest").json()["text"]
assert _raw.get("/ask/status").status_code != 403
assert len(client.get("/export?day=2026-11-25").json()["alerts"]) == 2
r = client.get("/exports/bayu-2/2026-11-20.json")
assert r.content == (main.EXPORTS / "bayu-2" / "2026-11-20.json").read_bytes(), "a private node serves the file as it is"
_seen.clear(); _eng.compute = lambda cur, *a, **k: _seen.append(cur) or {}
events_wire.live = lambda *a, **k: {}
client.get("/issues")
_eng.compute, events_wire.live = _real_compute, _real_live
assert _seen and not isinstance(_seen[0], _ia._NoIndoor), "a private node's /issues reads every row"
assert any(r["sensor"] == "indoor-1" for r in client.get("/export?day=2026-11-25").json()["hourly"])
print("ok  community: no indoor sensor without a token, none in the export; private unchanged")
