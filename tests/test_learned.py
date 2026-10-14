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
# ---------------------------------------------------------------- what is usual (step 2)
from datetime import date  # noqa: E402
assert learn.theil_sen([1, 2, 3, 100, 5]) == 1.0, "a slope one odd day cannot drag"
WIB = timezone(timedelta(hours=8))
start = datetime(2026, 9, 1, tzinfo=WIB)
hourly = {}
for d in range(28):
    for h in range(24):
        b = start + timedelta(days=d, hours=h)
        hourly[b] = (20.0 if h == 7 else 5.0 if h == 0 else 10.0) + (3.0 if b.isoweekday() >= 6 else 0) + (8.0 if d >= 21 else 0)
today = (start + timedelta(days=27)).date()
u = learn.usual_row("indoor-pm25", hourly, today)
assert u["status"] == "holding" and u["scope"] == "house" and u["numbers"]["high_hour"] == 7 and u["numbers"]["low_hour"] == 0, u["numbers"]
assert "highest around 07:00" in u["statement"] and "lowest around 00:00" in u["statement"], "the hours are the house's local ones"
assert "Weekends run" in u["statement"] and "higher than weekdays" in u["statement"]
assert "above the three weeks before" in u["statement"], "this week is 8 over a steady three weeks"
assert "every 30 days" not in u["statement"], "no trend before 60 days"
assert learn.usual_row("outdoor-pm25", {b: v for b, v in hourly.items() if (today - b.date()).days < 10}, today)["status"] == "too_early"
assert learn.usual_row("indoor-heat", {}, today) is None, "no sensor of that kind, no row"
long = {start + timedelta(days=d, hours=12): 10.0 + d * 0.1 for d in range(90)}
lu = learn.usual_row("outdoor-pm25", long, (start + timedelta(days=89)).date())
assert lu["scope"] == "place" and lu["numbers"]["trend_per_30_days"] == 3.0, lu["numbers"]
rows = [{"bucket": b, "sensor_id": sid, "metric": "pm25", "mean": v, "indoor": ind}
        for b, v in list(hourly.items())[:400] for sid, ind in (("in", True), ("out", False))]
got = {r["key"]: r for r in learn.learn_usual(lambda sql, *a: [dict(r) for r in rows], today)}
assert set(got) == {"indoor-pm25", "outdoor-pm25"} and got["outdoor-pm25"]["scope"] == "place", set(got)
print("usual: the day's highest and lowest hour, weekends, this week against three, a trend after 60 days; inside is house, outside is place")

# ---------------------------------------------------------------- asks that do not fit
mk = lambda n, hour, acted=False, answered=False: [{"hour": hour, "acted": acted, "dismissed": False, "answered": answered or acted}] * n  # noqa: E731
assert learn.asks_row("heat/x", mk(4, 13), True) is None, "under five, nothing to say"
night = learn.asks_row("heat/x", mk(8, 23) + mk(2, 13, acted=True), True)
assert night["numbers"]["unanswered_at_night"] == 8 and "between 22:00 and 06:00" in night["statement"], night["statement"]
assert "Quiet hours do not hold an act-level alert" in night["statement"], "says why quiet hours would not help"
often = learn.asks_row("heat/y", mk(170, 13) + mk(2, 9, acted=True), True)
assert "about 6 times a day" in often["statement"] and "around 13:00" in often["statement"], often["statement"]
fine = learn.asks_row("air/z", mk(6, 13, acted=True) + mk(1, 2), True)
assert fine["numbers"]["suggest"] is None and "change to its rule" not in fine["statement"], "mostly answered: no suggestion"
assert learn.asks_row("air/old", mk(6, 13), False)["status"] == "gone"
SRC2 = open("app/learn.py").read()
assert "UPDATE" not in SRC2 and "INSERT" not in SRC2 and "settings.set" not in SRC2, "learning changes no rule and no setting"
print("asks: a count, the hours, and what would change it, said and never done; nothing under five")
# ---------------------------------------------------------------- digests and search (step 3)
from datetime import date  # noqa: E402,F811
m = re.search(r"CREATE TABLE IF NOT EXISTS digests \((.*?)\n\);", SQL, re.S)
assert m and "PRIMARY KEY (scale, period_start)" in m.group(1) and "to_tsvector('simple'" in m.group(1)
assert "REVOKE ALL ON digests FROM planetai_ro" in SQL and "DELETE FROM digests" not in SRC
for road in ("def export", "def push_aggregates", "def aggregates"):
    body = SRC[SRC.index(road):SRC.index("\n\n\n", SRC.index(road))]
    assert "digests" not in body, f"{road} must never name the digests"
ps = learn.periods(date(2026, 9, 29), date(2026, 10, 14))
by = {k: [p[1] for p in ps if p[0] == k] for k in learn.SCALES}
assert len(by["day"]) == 15 and by["day"][-1] == date(2026, 10, 13), "every completed day, never today"
assert by["week"] == [date(2026, 9, 28), date(2026, 10, 5)], "Monday to Sunday, only finished weeks"
assert by["month"] == [date(2026, 9, 1)] and by["year"] == [], "September is done, October is not"
assert learn.label("day", date(2026, 10, 13)) == "Tuesday 13 October 2026" and learn.label("week", date(2026, 10, 5)) == "Week of 5 October 2026"
B = lambda d, h: datetime(2026, 10, d, h, tzinfo=WIB)  # noqa: E731
G = {"indoor-pm25": {B(13, 7): 30.0, B(13, 8): 10.0}, "outdoor-pm25": {B(13, 6): 40.0, B(12, 6): 99.0}}
dg = learn.digest("day", date(2026, 10, 13), date(2026, 10, 14), G,
                  [{"rule_id": "heat/heat_stress_now", "acted": True}, {"rule_id": "heat/heat_stress_now", "acted": False}],
                  [{"note": "closed the windows"}, {"note": "closed the windows"}, {"note": "purifier on"}],
                  {"indoor-pm25": {"mean": 15.0}, "outdoor-pm25": {"mean": 40.0}})
t = dg["text"]
assert t.startswith("Tuesday 13 October 2026. PM2.5 inside averaged 20.0 µg/m³, highest 30.0 µg/m³ (07:00)"), t
assert "PM2.5 outside averaged 40.0" in t and "99" not in t, "only the period's own hours"
assert "2 alerts (heat_stress_now 2), 1 acted on." in t
assert "\u201cclosed the windows\u201d \u00d72; \u201cpurifier on\u201d" in t, "each note once, with how many times"
assert "Against the day before: PM2.5 inside +5.0." in t, "a change under 0.1 is not said"
assert "feels-like" not in t, "a group with no readings is not invented"
empty = learn.digest("week", date(2026, 9, 28), date(2026, 10, 5), {}, [], [], None)
assert empty["text"] == "Week of 28 September 2026. No readings from this house's own sensors."
assert learn.search_terms("was this October smokier?") == "was | this | october | smokier"
assert learn.search_terms("a & b | c:* !! ') ;") == "", "nothing of tsquery's own syntax gets through"
assert learn.search_terms("asap ok") == "asap", "words of three letters or more"
LOG = []
main.q = lambda sql, *a: (LOG.append((sql, a)), [])[1]
settings._cache["rows"]["AGENT_PREFER"] = "private"
assert c.get("/learned/search?q=smoke", headers=ADMIN).status_code == 200
assert "to_tsquery('simple', %s)" in LOG[-1][0] and LOG[-1][1][0] == "smoke", "the words go as a parameter"
c.get("/learned/search?scale=month", headers=ADMIN)
assert "ORDER BY period_start DESC" in LOG[-1][0] and "to_tsquery" not in LOG[-1][0], "no words: the newest entries"
assert c.get("/learned/search?scale=decade", headers=ADMIN).status_code == 422
assert c.get("/learned/search?q=x").status_code in (401, 403)
settings._cache["rows"]["AGENT_PREFER"] = "fallback"
assert c.get("/learned/search?q=smoke", headers={**ADMIN, "X-Agent": "agent"}).status_code == 403
print("digests: completed days, weeks, months and years only; the period's own hours; notes once with a count; search by words as a parameter, guarded")
print("learned: every check passed")
