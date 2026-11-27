"""The three rules that exist only to feed a community node's subscribers: air around, heat ahead, rain ahead.

The shape of each rule is checked without a database. Their SQL is then replayed in DuckDB over readings built for
the case (tests/trustdb.py, as test_season does), with now() pinned to the instant being replayed. Two constructs
differ between Postgres and DuckDB and are swapped in the replay only, by a plain string replace:
`json_build_object(` (DuckDB calls it `json_object(`) and the `%(rain_heavy_mm)s` parameter that run_rules binds.

    PYTHONPATH=app python3 tests/test_feed_rules.py
"""
import ast
import contextlib
import datetime as dt
import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tests"))
os.environ.setdefault("PACKS_DIR", str(ROOT / "packs"))
os.environ.setdefault("PACKS_ENABLED", "")

import feeds  # noqa: E402
import packs  # noqa: E402

NEW = {"air-quality/air_unhealthy_around": "air", "forecast/heat_ahead": "heat", "forecast/rain_ahead": "rain"}
LOADED = {r["id"]: r for r in packs.load_rules()}
for rid, feed in NEW.items():
    r = LOADED.get(rid)
    assert r, f"{rid} is not loaded"
    assert r.get("feed_only") is True and r.get("level") == "info" and r.get("cooldown_minutes") == 1440, rid
    assert r["feed"]["name"] == feed and feed in feeds.NAMES, rid
    assert "indoor" not in re.sub(r"NOT (\w+\.)?indoor", "", r["sql"]), f"{rid}: indoor appears other than as NOT indoor"
assert LOADED["forecast/rain_ahead"].get("params") == {"rain_heavy_mm": "RAIN_HEAVY_MM"}
assert not LOADED["forecast/heat_ahead"].get("params") and not LOADED["air-quality/air_unhealthy_around"].get("params")
print("ok  three feed-only rules load")

# ---- run_rules binds `params:` for the rule that declares them, and leaves every other rule's SQL unbound.
src = ROOT / "app" / "main.py"
tree = ast.parse(src.read_text())
code = compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_rules"],
                          type_ignores=[]), "run_rules", "exec")
calls = []


class _NS:
    pass


class _Cur:
    def execute(self, *a): pass
    def fetchone(self): return {"id": 1}


@contextlib.contextmanager
def _db():
    yield type("C", (), {"cursor": lambda self: contextlib.nullcontext(_Cur()),
                         "transaction": lambda self: contextlib.nullcontext()})()


def _run_ro(cur, sql, *params):
    calls.append((sql, params))
    return []


p_packs, p_index, p_settings, p_log = _NS(), _NS(), _NS(), _NS()
p_packs.load_rules = lambda: [{"id": "x/like", "sql": "SELECT 1 WHERE 'ab' LIKE 'a%'", "message": "m"},
                              {"id": "x/bound", "sql": "SELECT %(n)s", "message": "m", "params": {"n": "RAIN_HEAVY_MM"}}]
p_packs.emit = lambda *a: None
p_index.run_ro = _run_ro
p_settings.get = lambda k, d=None: d
p_settings.num = lambda k, d=0: 61 if k == "RAIN_HEAVY_MM" else d
p_settings.defaults = lambda: {}
p_log.warning = p_log.info = lambda *a: None
g = dict(packs=p_packs, index=p_index, settings=p_settings, log=p_log, db=_db, events_pg=_NS(), feeds=_NS(),
         placewords=type("P", (), {"is_house": staticmethod(lambda: False)}), run_report=lambda cur: None,
         notify=lambda *a, **k: None, _quiet=lambda lvl: False, LOCALE=lambda: "en", _local_now=lambda: None)
exec(code, g)
g["run_rules"]()
assert calls == [("SELECT 1 WHERE 'ab' LIKE 'a%'", ()), ("SELECT %(n)s", ({"n": 61},))], calls
print("ok  params bind only where declared")

# ---- a feed_only rule's line goes to the queue and never to Home Assistant (packs.emit "on_alert"); a rule that is
# not feed_only still emits.
EMITS, QUEUED = [], []


class _Fresh:
    """No cooldown row; the alerts INSERT returns an id."""
    def execute(self, sql, *a): self._last = sql
    def fetchone(self): return {"id": 7} if "RETURNING" in self._last else None


@contextlib.contextmanager
def _db2():
    yield type("C", (), {"cursor": lambda self: contextlib.nullcontext(_Fresh()),
                         "transaction": lambda self: contextlib.nullcontext()})()


p_packs.load_rules = lambda: [{"id": "air-quality/around", "sql": "q1", "feed_only": True, "level": "info",
                               "feed": {"name": "air", "en": "{worst}"}},
                              {"id": "x/plain", "sql": "q2", "level": "info", "message": "plain {worst}"}]
p_packs.emit = lambda *a: EMITS.append(a)
p_index.run_ro = lambda cur, sql, *p: [{"sensor_id": "node", "worst": 70}]
p_feeds = _NS()
p_feeds.enqueue = lambda cur, rule, row, sid, now: QUEUED.append(rule["id"])
g.update(packs=p_packs, index=p_index, db=_db2, feeds=p_feeds, json=json, act_hint=lambda i: "",
         buttons=type("B", (), {"normalize": staticmethod(lambda b: None)}))
exec(code, g)
g["run_rules"]()
assert QUEUED == ["air-quality/around"], QUEUED
assert [e[2] for e in EMITS] == ["plain 70"], EMITS
print("ok  a feed_only rule never reaches Home Assistant")

try:
    import trustdb
except ImportError:
    print("  - feed rule replay skipped (pip install duckdb)")
    sys.exit(0)

WITA = dt.timezone(dt.timedelta(hours=8))
RULES = {**trustdb.rules("air-quality"), **trustdb.rules("forecast")}


def replay(rule, rows, who, at, private=(), signed=(), **params):
    r = dict(RULES[rule])
    sql = r["sql"].replace("json_build_object(", "json_object(")
    for k, v in params.items():
        sql = sql.replace(f"%({k})s", str(v))
    r["sql"] = sql
    node = trustdb.Node(rows, who)
    for src in private:                               # a source whose pm25 its pack declares private
        node.con.execute("INSERT INTO channel_roles (source, metric, role, comparable, declared_by) "
                         "VALUES (?, 'pm25', 'private', false, 'core')", (src,))
    for child in signed:                              # a child that signs its pushes is pinned with its node id
        node.con.execute("INSERT INTO children (name, node_id, public_key) VALUES (?, ?, 'k')", (child, "id-" + child))
    out = node.run(r, at)
    for o in out:
        for k in ("month", "worst_at"):
            if isinstance(o.get(k), str):
                o[k] = json.loads(o[k])
    return out


# ---- air around: every outdoor station the node reads, never a model, never a room.
AT = dt.datetime(2026, 11, 27, 10, 0, tzinfo=WITA)


def station(sid, v, indoor=False, kind="sensor", local=False, source="x", ago=0, name=None):
    return ((sid, source, name or f"Station {sid}", -8.8, 115.1, indoor, local, kind),
            [(AT - dt.timedelta(minutes=ago + m), sid, "pm25", float(v)) for m in (5, 20, 40)])


def air(*st, private=(), signed=("home-a",)):
    return replay("air_unhealthy_around", [r for s in st for r in s[1]], [s[0] for s in st], AT, private=private,
                  signed=signed)


def kid(n, v, **kw):
    """A child's station as a parent stores it: id and name are the child's node name and its kit id."""
    return station(f"home-a/sc-{n}", v, kind="child", source="child", name=f"home-a/sc-{n}", **kw)


def both(w):
    return {"en": w, "id": w}


hit = air(station("a", 60), station("b", 70, local=True), station("c", 20), station("m", 200, kind="model"))
assert len(hit) == 1 and hit[0]["sensor_id"] == "node", hit
assert hit[0]["n"] == 3 and hit[0]["over"] == 2 and hit[0]["worst"] == 70 and hit[0]["worst_at"] == both("Station b"), hit
br = air(station("a", 60), station("b", 70, name="TPA Kutuh (Smart Citizen)"), station("c", 20))
assert br[0]["worst_at"] == both("TPA Kutuh"), "a station's trailing bracket is dropped, as the weekly does"
assert air(station("a", 90)) == [], "one station alone is not the air around here"
assert air(station("in", 300, indoor=True), station("a", 10), station("b", 10)) == [], "a room never counts"
assert air(station("p", 300, source="mine"), station("a", 60), station("b", 10), private=["mine"]) == [], \
    "a private reading never counts"
# children arrive as hourly means (kind='child', outside `stats`): they count, a newest bucket within 2 hours
kids = air(kid(1, 60), kid(2, 70), station("a", 20))
assert len(kids) == 1 and kids[0]["n"] == 3 and kids[0]["over"] == 2, kids
# a child's station is never named: the worst is "a neighbour's station", in both languages
assert kids[0]["worst_at"] == {"en": "a neighbour's station", "id": "stasiun tetangga"}, kids
for lang in ("en", "id"):
    text = feeds._fill(LOADED["air-quality/air_unhealthy_around"]["feed"][lang], kids[0])
    assert "home-a" not in text and "sc-2" not in text and "sc-1" not in text, text
    assert ("70 µg/m³ at a neighbour's station" if lang == "en" else "70 µg/m³ di stasiun tetangga") in text, text
assert air(kid(1, 300, indoor=True), station("a", 60), station("b", 10)) == [], "a child's room never counts"
assert air(kid(1, 300, ago=180), station("a", 60), station("b", 10)) == [], "a child's bucket 3 hours old does not count"
assert air(kid(1, 300), station("a", 60), station("b", 10), private=["child"]) == [], \
    "a child's reading on a private channel never counts"
# an unsigned child is an older one, which did not send `indoor`: its stations were stored outdoor, so none counts
assert air(kid(1, 300), kid(2, 300), station("a", 10), signed=()) == [], "an unsigned child's stations never count"
print("ok  air around")


# ---- heat ahead: tomorrow's highest feels-like against the last 30 days of the node's own forecasts.
def feel(ta, rh, ws_kmh):
    e = rh / 100 * 6.105 * math.exp(17.27 * ta / (237.7 + ta))
    return ta + 0.33 * e - 0.70 * ws_kmh / 3.6 - 4.00


def ta_for(target, rh=70, ws=7.2):
    lo, hi = 0.0, 60.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if feel(mid, rh, ws) < target else (lo, mid)
    return lo


FC = [("forecast-om", "forecast-om", "Open-Meteo", -8.8, 115.1, False, False, "model"),
      ("forecast-bmkg", "forecast-bmkg", "BMKG", -8.8, 115.1, False, False, "model")]
TODAY = dt.datetime(2026, 11, 27, tzinfo=WITA)


def hour_rows(day, hour, top):
    ts = TODAY + dt.timedelta(days=day, hours=hour)
    ta = ta_for(top)
    return [(ts, sid, m, v) for sid in ("forecast-om", "forecast-bmkg")
            for m, v in (("fc_temp", ta), ("fc_humidity", 70.0), ("fc_wind_speed", 7.2))]


def heat_rows(past_days):
    rows = []
    for d in range(-past_days, 0):
        rows += hour_rows(d, 14, 33 + (d % 3)) + hour_rows(d, 6, 27)
    return rows + hour_rows(1, 14, 38) + hour_rows(1, 6, 28) + hour_rows(1, 17, 36)


hit = replay("heat_ahead", heat_rows(30), FC, TODAY + dt.timedelta(hours=7))
assert len(hit) == 1 and hit[0]["at"] == 38 and hit[0]["hour"] == "14:00", hit
assert hit[0]["month"] == {"en": "November", "id": "November"}, hit
assert replay("heat_ahead", heat_rows(30), FC, TODAY + dt.timedelta(hours=11)) == [], "only between 06:00 and 09:00"
assert replay("heat_ahead", heat_rows(10), FC, TODAY + dt.timedelta(hours=7)) == [], "under 20 past days, nothing"
print("ok  heat ahead")

# ---- rain ahead: the wettest forecast point's next 24 hours against RAIN_HEAVY_MM.
NOW = TODAY + dt.timedelta(hours=9)
PTS = [("forecast-om", "forecast-om", "Open-Meteo", -8.8, 115.1, False, False, "model"),
       ("forecast-om-2", "forecast-om", "Open-Meteo 2", -8.7, 115.2, False, False, "model")]


def rain(top):
    rows = [(NOW + dt.timedelta(hours=h), "forecast-om", "fc_rain", 1.0) for h in range(1, 13)]   # 12 mm
    rows += [(NOW + dt.timedelta(hours=h), "forecast-om-2", "fc_rain", v)
             for h, v in ((2, 1.0), (5, top - 4.0), (6, 3.0))]
    rows += [(NOW + dt.timedelta(hours=30), "forecast-om-2", "fc_rain", 90.0)]                    # past the 24 hours
    return rows


hit = replay("rain_ahead", rain(61), PTS, NOW, rain_heavy_mm=50)
assert len(hit) == 1 and hit[0]["mm"] == 61 and hit[0]["from"] == "14:00", hit
assert replay("rain_ahead", rain(49), PTS, NOW, rain_heavy_mm=50) == [], "49 mm is under the line"
print("ok  rain ahead")

row = {"worst": 70, "worst_at": both("Station b"), "over": 2, "n": 3, "at": 38, "hour": "14:00",
       "month": {"en": "November", "id": "November"}, "mm": 61, "from": "14:00"}
for rid in NEW:
    for lang in ("en", "id"):
        assert "{" not in LOADED[rid]["feed"][lang].format(**row), (rid, lang)
print("feed rules: air around, heat ahead and rain ahead fire on their cases and stay quiet on the rest")
