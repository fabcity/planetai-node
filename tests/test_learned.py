"""What worked here (docs/SPEC_learn.md step 1): app/learn.py's arithmetic on hours made by hand, its status rules, and
GET /learned's guards. The database is stubbed; the numbers are worked out here so a wrong window shows.

Run: PYTHONPATH=app python3 tests/test_learned.py
"""
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone

import learn

SQL = open("init.sql").read()
SRC = open("app/main.py").read()

# ---------------------------------------------------------------- the table, kept home
m = re.search(r"CREATE TABLE IF NOT EXISTS learnings \((.*?)\n\);", SQL, re.S)
assert m and "PRIMARY KEY (kind, key)" in m.group(1), "one row per learning, replaced, never duplicated"
assert "'too_early','holding','weakening','gone'" in m.group(1), "a learning is marked, never deleted"
assert "REVOKE ALL ON learnings FROM planetai_ro" in SQL, "pack SQL never reads what the house learned"
for road in ("def export", "def push_aggregates", "def aggregates"):
    body = SRC[SRC.index(road):SRC.index("\n\n\n", SRC.index(road))]
    assert "learnings" not in body, f"{road} must never name the learnings table"
assert "DELETE FROM learnings" not in SRC, "nothing deletes a learning"
print("schema: learnings kept home, marked and never deleted")

# ---------------------------------------------------------------- the arithmetic
assert abs(learn.apparent(30, 70) - (30 + 0.33 * (0.7 * 6.105 * 2.718281828 ** (17.27 * 30 / 267.7)) - 4)) < 1e-6, \
    "the Steadman form the heat rules use"
T0 = datetime(2026, 10, 1, 20, tzinfo=timezone.utc)
H = lambda k: T0 + timedelta(hours=k)  # noqa: E731
inside = {H(-1): 40.0, H(1): 20.0, H(2): 10.0}            # before 40, after mean(20, 10) = 15: -25
street = [{H(-1): 30.0, H(1): 25.0, H(2): 25.0}, {H(-1): 10.0, H(1): 15.0, H(2): 15.0}]   # street 20 -> 20: 0
c = learn.case(inside, street, T0, learn.AFTER["pm25"])
assert c == {"at": T0.isoformat(), "before": 40.0, "after": 15.0, "change": -25.0, "street": 0.0}, c
assert learn.case({H(1): 5.0}, street, T0, (1, 2)) is None, "no hour before, no case"
assert learn.case(inside, [], T0, (1, 2))["street"] is None, "no street, only the house's change"
heat = learn.series([{"bucket": H(0), "sensor_id": "k", "metric": "temp", "mean": 30.0},
                     {"bucket": H(0), "sensor_id": "k", "metric": "humidity", "mean": 70.0}])
assert abs(heat[("k", "apparent")][H(0)] - learn.apparent(30, 70)) < 1e-9, "apparent where temp and humidity meet"
print("arithmetic: the hour before, the window after, the street beside, apparent as the rules compute it")

# ---------------------------------------------------------------- the row and its statement
cs = [{"change": -25.0, "street": 0.0}] * 6
row = learn.summarise("air-quality/indoor_pm25_high", "pm25", cs, [{"change": -2.0, "street": -1.0}] * 3, None, True)
assert row["status"] == "holding" and row["n"] == 6 and row["numbers"]["acted"]["change"] == -25.0
assert row["statement"] == ("Acted on 6 times: PM2.5 inside changed -25.0 µg/m³ in the 1–2 h after, while on the street "
                            "it changed +0.0 µg/m³. Left unanswered 3 times: PM2.5 inside changed -2.0 µg/m³ in the "
                            "1–2 h after, while on the street it changed -1.0 µg/m³."), row["statement"]
assert all(str(x) in row["statement"] for x in ("6", "-25.0", "3", "-2.0")), "every number in the sentence is a row number"
early = learn.summarise("heat/heat_stress_now", "apparent", cs[:4], [], None, True)
assert early["status"] == "too_early" and early["statement"] == "Acted on 4 times so far: too early to say.", \
    "under five, a count and no percentage"
flip = learn.summarise("air-quality/indoor_pm25_high", "pm25", [{"change": 3.0, "street": 0.0}] * 6, [], row, True)
assert flip["status"] == "weakening", "it held, and now it goes the other way"
assert learn.summarise("x/old", "pm25", cs, [], row, False)["status"] == "gone", "a rule that cannot fire is gone, kept"
print("rows: holding, too early under five, weakening when it turns, gone when the rule is retired; the sentence is the numbers")

# ---------------------------------------------------------------- the cases from the ledger
now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
t = now - timedelta(days=1)
ALERTS = [
    {"id": 1, "ts": t, "rule_id": "air-quality/indoor_pm25_high", "sensor_id": "in", "acted_at": t + timedelta(minutes=20), "answered": True, "note": "closed the windows"},
    {"id": 2, "ts": t, "rule_id": "air-quality/indoor_pm25_high", "sensor_id": "in", "acted_at": None, "answered": False, "note": None},
    {"id": 3, "ts": t, "rule_id": "air-quality/indoor_pm25_high", "sensor_id": "in", "acted_at": None, "answered": True, "note": None},
    {"id": 4, "ts": now, "rule_id": "air-quality/indoor_pm25_high", "sensor_id": "in", "acted_at": now, "answered": True, "note": ""},
    {"id": 5, "ts": t, "rule_id": "air-quality/retired_rule", "sensor_id": "in", "acted_at": t, "answered": True, "note": "opened"},
    {"id": 6, "ts": t, "rule_id": "nearby/only_here", "sensor_id": "out", "acted_at": t, "answered": True, "note": ""},
    {"id": 7, "ts": t, "rule_id": "indoor_pm25_high", "sensor_id": "in", "acted_at": t, "answered": True, "note": ""}]
READ = [{"bucket": t + timedelta(hours=k), "sensor_id": sid, "metric": "pm25", "mean": v, "indoor": ind}
        for sid, ind, vals in (("in", True, {-1: 40, 1: 20, 2: 10}), ("out", False, {-1: 20, 1: 20, 2: 20}))
        for k, v in vals.items()]
q = lambda sql, *a: ALERTS if "FROM alerts" in sql else [dict(r) for r in READ]  # noqa: E731
rules = [{"id": "air-quality/indoor_pm25_high", "level": "act", "watch": {"metric": "pm25", "over": 35.5}},
         {"id": "heat/heat_stress_now", "level": "act", "watch": {"metric": "apparent", "over": 35}},
         {"id": "nearby/only_here", "level": "act"}, {"id": "air-quality/warn_only", "level": "warn"}]
out = {r["key"]: r for r in learn.learn_worked(q, rules, {"air-quality/indoor_pm25_high", "heat/heat_stress_now"}, {})}
assert set(out) == {"air-quality/indoor_pm25_high", "air-quality/retired_rule"}, \
    f"rules with cases and a metric; a rule with no alerts has no row; no metric, no row: {set(out)}"
aq = out["air-quality/indoor_pm25_high"]["numbers"]
assert aq["acted"]["n"] == 1 and aq["unanswered"]["n"] == 1, "seen-but-not-acted is neither; an open window waits"
assert aq["cases"]["acted"][0]["note"] == "closed the windows" and aq["cases"]["acted"][0]["change"] == -25.0
gone = out["air-quality/retired_rule"]
assert gone["status"] == "gone" and gone["numbers"]["acted"]["n"] == 1 and gone["metric"] == "pm25", \
    "a retired rule keeps what it taught, by its pack's metric"
print("ledger: acted and unanswered from the alerts, an unfinished window waits, notes kept, a retired rule kept as gone")

# ---------------------------------------------------------------- the route
logging.disable(logging.WARNING)
os.environ.update(ADMIN_TOKEN="admin-tok", ACT_TOKEN="act-tok", NODE_LAT="-8.6478291", NODE_LON="115.1385412",
                  DATABASE_URL="postgresql://unused/never-connected")
import settings                                    # noqa: E402
settings._cache = {"at": time.time() + 1e9, "rows": {"SHARE_LEVEL": "open"}}
import main                                       # noqa: E402
from fastapi.testclient import TestClient         # noqa: E402

main.q = lambda sql, *a: [{"kind": "worked", "key": "k", "status": "holding", "statement": "s", "numbers": {}}]
c = TestClient(main.app)
ADMIN = {"Authorization": "Bearer admin-tok"}
assert c.get("/learned").status_code in (401, 403) and c.get("/learned", headers={"Authorization": "Bearer act-tok"}).status_code == 401
assert c.get("/learned", headers=ADMIN).json()["learnings"][0]["statement"] == "s"
settings._cache["rows"]["AGENT_PREFER"] = "private"
assert c.get("/learned", headers={**ADMIN, "X-Agent": "agent"}).status_code == 200, "an agent, models at home: yes"
settings._cache["rows"]["AGENT_PREFER"] = "fallback"
r = c.get("/learned", headers={**ADMIN, "X-Agent": "agent"})
assert r.status_code == 403 and "AGENT_PREFER" in r.json()["detail"], "an agent that may be online: no, and why"
assert c.get("/learned", headers=ADMIN).status_code == 200, "the page is not an agent"
print("route: admin only; an agent only while AGENT_PREFER=private, told why otherwise")
print("learned: every check passed")
