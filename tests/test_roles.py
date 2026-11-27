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

# ---------------------------------------------------------------- a community node asks nobody to act
import asyncio  # noqa: E402
import datetime as dt  # noqa: E402
from types import SimpleNamespace  # noqa: E402
import events_pg  # noqa: E402
import importlib.util  # noqa: E402
import agent_loop  # noqa: E402

os.environ["NODE_KIND"] = "community"
assert main.act_hint(12) == "", "a community node names no way to answer"
os.environ["NODE_KIND"] = "home"
assert main.act_hint(12).endswith("act 12"), "a private node unchanged"

# run_rules reads the bot's buttons once, and only a private node lets them ride
_rr = (ROOT / "app/main.py").read_text().split("def run_rules(")[1].split("\ndef ")[0]
assert _rr.count('"TELEGRAM_BUTTONS"') == 1 and "placewords.is_house()" in _rr.split('"TELEGRAM_BUTTONS"')[1].split("\n")[0], \
    "the rule and event sends must share one buttons switch gated on the role"

# /test-alert on a community node: the message, no line telling anyone how to answer
_sent = []
_real_notify, _real_db = main.notify, main.db
main.notify = lambda lvl, text, **k: _sent.append(text)


class _TaCur:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, *a): pass
    def fetchone(self): return {"id": 41}


class _TaCon(_TaCur):
    def cursor(self): return _TaCur()


main.db = lambda: _TaCon()
os.environ["NODE_KIND"] = "community"
assert client.post("/test-alert", headers=TOK).status_code == 200
assert _sent and "act" not in _sent[-1].split("\n")[-1] and "👉" not in _sent[-1], _sent
os.environ["NODE_KIND"] = "home"
client.post("/test-alert", headers=TOK)
assert "act 41" in _sent[-1], "a private node still says how to answer"
main.notify, main.db = _real_notify, _real_db


# the context behind a message and a card never carries an inside reading on a community node
class _CtxCur:
    def execute(self, *a): pass
    def fetchone(self): return {"inside_temp": 29.31, "inside_pm25": 8.0, "outside_temp": 24.9, "outside_pm25": 10.0,
                                "outside_source": "outside"}


_ev = SimpleNamespace(rooms=set(), where={"yard"}, kind="sustained")
os.environ["NODE_KIND"] = "community"
_c = events_pg.context(_CtxCur(), _ev, dt.datetime(2026, 11, 26, 20))
assert _c["inside_temp"] is None and _c["inside_pm25"] is None and _c["outside_temp"] == 24.9, _c
os.environ["NODE_KIND"] = "home"
assert events_pg.context(_CtxCur(), _ev, dt.datetime(2026, 11, 26, 20))["inside_temp"] == 29.3


# rho on a community node counts its children's households only
class _RhoCur:
    def execute(self, sql, *a): self.sql = sql
    def fetchone(self): return {}
    def fetchall(self): return []


_spec = importlib.util.spec_from_file_location("index_unstubbed", ROOT / "app/index.py")   # the module above is stubbed
_ix = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_ix)
_rc = _RhoCur(); _ix._funnel = lambda *a: {}; _ix._replaced = lambda: []
os.environ["NODE_KIND"] = "community"; _ix.rho(_rc)
assert "self/" not in _rc.sql and "ev/" not in _rc.sql and "child ||" in _rc.sql, _rc.sql
os.environ["NODE_KIND"] = "home"; _ix.rho(_rc)
assert "self/" in _rc.sql and "ev/" in _rc.sql and "child ||" in _rc.sql

# the agent: /act and every answer button get one line on a community node, and nothing is posted
_tg, _posted = [], []
agent_loop.telegram = lambda method, **p: _tg.append((method, p)) or asyncio.sleep(0)
agent_loop._post_answer = lambda *a, **k: _posted.append(a) or asyncio.sleep(0)
agent_loop.node_session = lambda *a, **k: (_ for _ in ()).throw(AssertionError("a community /act reached the node"))
agent_loop.CHATS = lambda: {"1"}
_line = "This is a community node: it sends feeds, and nobody answers its alerts here."
agent_loop.KIND = "community"
assert asyncio.run(agent_loop.act_command(None, "1", "/act 3 opened the windows")) is True
assert _tg == [("sendMessage", {"chat_id": "1", "text": _line})], _tg
for data in ("ev:5:acted", "al:7:good"):
    _tg.clear()
    asyncio.run(agent_loop.handle_callback(None, {"id": "q", "data": data, "message": {"chat": {"id": 1}}}, {}))
    assert _tg == [("answerCallbackQuery", {"callback_query_id": "q", "text": _line})], (data, _tg)
assert not _posted, "a community node records no answer"
agent_loop.KIND = "home"; _tg.clear()
assert asyncio.run(agent_loop.act_command(None, "1", "/act 3")) is True and "What did you do" in _tg[0][1]["text"]
assert asyncio.run(agent_loop.act_command(None, "1", "/stack")) is False
_dn = (ROOT / "app/static/doors-now.js").read_text().split("function decision()")[1].split("\n")[0]
assert "notHouse((D.health || {}).kind)" in _dn and "hidden" in _dn, "the Now door draws no What to do on a community node"
print("ok  community: no act hint, no buttons, no action line, no inside value, rho from its children, the bot says why")

# ---------------------------------------------------------------- fix round 1: no surface asks, no route records an answer
import events_wire  # noqa: E402
from issues import engine as _engine  # noqa: E402

_H = dt.timedelta(hours=1); _NOW = dt.datetime(2026, 11, 26, 12, tzinfo=dt.timezone.utc)
_EVS = [{"id": 1, "issue": "heat", "kind": "sustained", "level": "act", "opened_at": _NOW - 2 * _H, "last_seen_at": _NOW,
         "cleared_at": None, "peak": 35.8, "rooms": [], "places": ["yard"], "action_id": "heat/open_up"}]
_MSGS = [{"event_id": 1, "ts": _NOW - 2 * _H, "sent": True, "action_id": "heat/open_up",
          "text": "Hot for hours.\nOpen up now: outside is 24.9 °C and inside is 29.3 °C."}]
_DECL = {"heat": {"metric": "apparent", "line": {"value": 35.0}}}


def _card(kind, ctx):
    os.environ["NODE_KIND"] = kind
    return events_wire.build("events", _EVS, _MSGS, [], {1: []}, {1: ctx}, _DECL, "en", _NOW, dt.timezone.utc)["open"][0]


for _ctx in ({}, {"usual": None}):          # no context read, and a context with no action of its own
    _c = _card("community", _ctx)
    assert _c["asking"] is False and _c["action"] is None, ("a community card asks nothing, shows no stored action", _c)
assert _card("home", {})["asking"] is True and _card("home", {})["action"]["text"].startswith("Open up"), "private unchanged"

_ev_open = {"id": 1, "asking": True, "opened_at": "2026-11-26T10:00:00+00:00", "kind": "sustained"}
_asks = [{"id": 9, "ts": "2026-11-26T11:00:00+00:00", "current": True, "says": {}, "how": {}}]
os.environ["NODE_KIND"] = "community"
assert _engine._asking(_ev_open, _asks) == [], "an open act event and an open act alert ask nothing of a community"
os.environ["NODE_KIND"] = "home"
assert [a.get("event_id") or a.get("alert_id") for a in _engine._asking(_ev_open, _asks)] == [1, 9]

# POST /actions: every kind of answer is refused on a community node; a decided record and a private node still write
_answered = []
_real_answer, _real_db = events_pg.answer, main.db
events_pg.answer = lambda cur, *a: _answered.append(a)
main.db = lambda: _TaCon()
os.environ["NODE_KIND"] = "community"
for _body in ({"event_id": 3, "stage": "acted"}, {"event_id": 3, "stage": "dismissed"},
              {"alert_id": 41, "stage": "acknowledged"}, {"alert_id": 41, "stage": "acted", "note": "closed windows"},
              {"alert_id": 41, "stage": "dismissed"}, {"alert_id": 41, "choice": "good"}):
    r = client.post("/actions", json=_body, headers=TOK)
    assert r.status_code == 409 and r.json()["detail"] == "This is a community node: it sends feeds, and nobody answers its alerts here.", (_body, r.status_code, r.text)
assert not _answered
assert client.post("/actions", json={"alert_id": 41, "stage": "decided"}, headers=TOK).status_code != 409, \
    "a decided record is not an answer"
os.environ["NODE_KIND"] = "home"
assert client.post("/actions", json={"event_id": 3, "stage": "acted"}, headers=TOK).status_code == 200
assert _answered == [(3, "acted", None, None)], _answered
events_pg.answer, main.db = _real_answer, _real_db

# the agent before its first /health read: the NODE_KIND it was started with
agent_loop.KIND = ""
os.environ["NODE_KIND"] = "community"; assert agent_loop.no_act()
os.environ["NODE_KIND"] = "home"; assert not agent_loop.no_act()
agent_loop.KIND = "community"; assert agent_loop.no_act(), "/health wins once read"
agent_loop.KIND = "home"
print("ok  community: no card or /issues asks, no stored action, POST /actions refuses every answer; private unchanged")

# ---------------------------------------------------------------- the doors by role (Data tabs, Readings note, /workbench)
import subprocess  # noqa: E402
_prog = r"""
const fs = require('fs'), vm = require('vm');
const core = fs.readFileSync('./app/static/doors-core.js', 'utf8'), data = fs.readFileSync('./app/static/doors-data.js', 'utf8'), wall = fs.readFileSync('./app/static/doors-wallmap.js', 'utf8');
const pick = (src, n) => src.match(new RegExp('^const ' + n + ' = .*$', 'm'))[0], fn = n => data.match(new RegExp('function ' + n + '\\b[\\s\\S]*?\\n}\n'))[0];
const ctx = { $: () => null }; vm.createContext(ctx);
vm.runInContext(pick(core, 'esc') + '\n' + pick(wall, 'notHouse') + '\n' + data.slice(data.indexOf('const DTABS = {'), data.indexOf('/* an anchor Data used')) + fn('dataTabs') + fn('sensorLine')
  + '\nthis.tabs = dataTabs; this.line = sensorLine;', ctx);
const names = k => Object.fromEntries(Object.entries(ctx.tabs(k)).map(([id, t]) => [id, t[0]]));
console.log(JSON.stringify({ home: names('home'), community: names('community'), district: names('district'), none: names(undefined),
  line: ctx.line({ kind: 'home' }), parent: ctx.line({ kind: 'home', parent: { node: 'bayu-ungasan' } }), com: ctx.line({ kind: 'community' }) }));
"""
_r = subprocess.run(["node", "-e", _prog], capture_output=True, text=True, cwd=ROOT)
assert _r.returncode == 0, _r.stderr
_o = json.loads(_r.stdout)
for _k in ("home", "none"):
    assert "workbench" not in _o[_k] and _o[_k]["home"] == "Home", (_k, _o[_k])
for _k in ("community", "district"):
    assert _o[_k]["workbench"] == "Workbench" and _o[_k]["home"] == "Services", (_k, _o[_k])
_site = 'planetai.fab.city/sensors</a>.'
assert _o["line"].startswith("To set up a new sensor, use your community node’s workbench or <a href=\"https://planetai.fab.city/sensors/\"") and _o["line"].endswith(_site), _o["line"]
assert "use bayu-ungasan’s workbench or" in _o["parent"], _o["parent"]
assert _o["com"] == "", "a community node has the workbench itself"
_ds = (ROOT / "app/static/doors-setup.js").read_text()
assert "b.key === 'NODE_KIND'" in _ds and "<input" not in _ds.split("const boot = ")[1].split("const changed")[0], "Basics shows NODE_KIND as a read-only row, no input"
assert "band.style.display" in (ROOT / "app/static/doors-now.js").read_text().split("function decision()")[1].split("\n")[0]

# /workbench: a private node points to the site; its flasher and firmware answer 404; a community node serves them
os.environ["NODE_KIND"] = "home"
_r = client.get("/workbench", follow_redirects=False)
assert _r.status_code == 308 and _r.headers["location"] == "https://planetai.fab.city/sensors/", (_r.status_code, _r.headers)
assert client.get("/static/vendor/esp-web-tools/esp32-DNPRK0Ay.js").status_code == 404
assert client.get("/static/firmware/bayu/manifest.json").status_code == 404
_calls = []
_real_hc = main.hc
main.hc = SimpleNamespace(get=lambda *a, **k: _calls.append(a))
main.check_firmware(); assert not _calls, "a private node fetches no firmware"
main.hc = _real_hc
os.environ["NODE_KIND"] = "community"
assert client.get("/workbench", follow_redirects=False).status_code == 200
assert client.get("/static/vendor/esp-web-tools/esp32-DNPRK0Ay.js").status_code == 200
os.environ["NODE_KIND"] = "home"
print("ok  roles: the Workbench is a community node's; a private node points to it")

# Set up > Sources names a room for each of the node's own sensors, on either role
_ds = (ROOT / "app/static/doors-setup.js").read_text()
_rows = _ds.split("function sRoomRows()")[1].split("function sRooms(")[0]
assert "s.local && s.kind === 'sensor'" in _rows, "one row per local sensor; a local survey row (things, place-gis) gets none"
assert 'aria-label="Room for ${esc(s.source_name || s.name' in _rows and 'maxlength="40"' in _rows, "the input is labelled with the platform's name"
_put = _ds.split("async function sRoom(ev)")[1].split("\n}")[0]
assert "`/sensors/${encodeURIComponent(sid)}`" in _put and "method: 'PATCH'" in _put and "DOORS_AUTH()" in _put and "room:" in _put and "|| null" in _put, "blank sends room null"
assert "j.detail" in _put, "the route's error text is shown"
assert "g === 'sources' && unlocked ? " in _ds and "sRoomRows()" in _ds.split("g === 'sources' && unlocked")[1][:600], "Sources draws the rows, only for a reader with the token"
print("ok  roles: Sources names a room for each local sensor")

# The Node door on a community node: the network drawing and the ledger (netGroups, netLayout, netPackets)
_prog = r"""
global.VIEWS = {}; Object.assign(global, require('./app/static/doors-load.js'));
eval(require('fs').readFileSync('./app/static/doors-core.js', 'utf8').match(/^const ago = .*$/m)[0].replace('const ago', 'global.ago'));
const N = require('./app/static/doors-node.js');
const own = [1, 2, 3].map(i => ({ sensor_id: 'sc-' + i, kind: 'sensor', local: true }));
const kids = [1, 2].map(i => ({ sensor_id: 'home-1/outdoor-' + i, kind: 'child', name: 'a home nearby · outdoor ' + i }));
const pub = Array.from({ length: 28 }, (_, i) => ({ sensor_id: 'bad-' + i, kind: 'sensor', local: false }));
const mini = { sensors: [...own, ...kids, ...pub], stats15: { 'home-1/outdoor-1': { pm25: [10, 4] } }, index_cells: [],
  health: { kind: 'community', city: 'Ungasan', mesh: { root_topic: 'msh/x', gateway: '!8f491db0', packets: 40 }, reticulum: { relaying: 0, peers: [] } } };
const fresh = { sensors: [], stats15: {}, index_cells: [], health: { kind: 'community' } };
const g = N.netGroups(mini), f = N.netGroups(fresh), out = [];
const nan = L => [L.node.x, L.node.y, L.H, ...L.items.flatMap(i => [i.x, i.y])].some(v => typeof v !== 'number' || Number.isNaN(v));
const lay = [[g, 900, 360, false], [g, 360, 0, true], [f, 900, 360, false], [f, 360, 0, true]].map(a => N.netLayout(...a));
const fakeSvg = made => ({ querySelectorAll: () => [{ getTotalLength: () => 100, getPointAtLength: () => ({ x: 1, y: 2 }), dataset: { n: '24' } }],
  querySelector: () => ({ appendChild() {} }), ownerDocument: { createElementNS: () => { made.n++; return { setAttribute() {} }; } } });
const made = { n: 0 }; global.matchMedia = () => ({ matches: true }); const still = N.netPackets(fakeSvg(made), 1000);
const moved = { n: 0 }; global.matchMedia = () => ({ matches: false }); N.netPackets(fakeSvg(moved), 1000);
console.log(JSON.stringify({ g, f, nan: lay.map(nan), narrow: lay[1], still: still.length, made: made.n, moved: moved.n }));
"""
_r = subprocess.run(["node", "-e", _prog], capture_output=True, text=True, cwd=ROOT, timeout=60)
assert _r.returncode == 0, _r.stderr
_o = json.loads(_r.stdout)
_in = {x["key"]: x for x in _o["g"]["in"]}; _out = {x["key"]: x for x in _o["g"]["out"]}
assert list(_in) == ["homes", "own", "stations", "mesh"], list(_in)
assert (_in["homes"]["count"], _in["own"]["count"], _in["stations"]["count"], _in["mesh"]["count"]) == (1, 3, 28, 40), _in
assert "2 sensors" in _in["homes"]["sub"] and _in["homes"]["live"] and "!8f491db0" in _in["mesh"]["sub"], _in
assert list(_out) == ["bot", "link", "reticulum", "index"] and _out["reticulum"]["count"] == 0, _out
for _k in ("bot", "link"):
    assert _out[_k]["count"] is None and _out[_k]["sub"] == "not counted yet", _out[_k]
assert [(x["key"], x["count"]) for x in _o["f"]["in"]] == [("own", 0)], _o["f"]
assert [x["key"] for x in _o["f"]["out"]] == ["bot", "link", "index"], _o["f"]
assert not any(_o["nan"]), _o["nan"]
_L = _o["narrow"]; _side = {x["key"]: x for x in _L["items"]}
assert all(x["y"] < _L["node"]["y"] for x in _L["items"] if x["side"] == "in") and all(x["y"] > _L["node"]["y"] for x in _L["items"] if x["side"] == "out"), _L
assert len(_L["items"]) == 8, _L
assert _o["still"] == 0 and _o["made"] == 0 and _o["moved"] > 0, _o
_dn = (ROOT / "app/static/doors-node.js").read_text(); _dh = (ROOT / "app/static/doors.html").read_text()
assert 'id="netview"' in _dh and 'id="ledger-node"' in _dh and "role=\"img\" aria-label=\"${esc(" in _dn, "both sections, and the drawing says its counts"
print("ok  roles: a community Node door draws what comes in and what it serves; reduced motion moves nothing")
