"""The engine, replayed against node #1 as it stood on 6 September 2026 at 14:08 UTC.

  · the stack: air room 5.1, ring 7.0 fenced, region 15; heat room 30.8 from four indoor units
  · the fence: one wild station does not become the neighbourhood, and a ring that agrees survives
  · apparent(): per sensor then aggregated, not the other way round, and the two differ here
  · the five states, on eight cases including the two the ρ analysis found
  · the headline: highest state wins, ties go to the declared order
  · every locale renders with every placeholder filled and no brace left over
  · an empty node: every declared issue `none`, with a reason
  · the series line up on one set of buckets

Run: PACKS_DIR=packs PYTHONPATH=app python3 tests/test_issues_engine.py
"""
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
os.environ.setdefault("PACKS_DIR", "packs")
sys.path.insert(0, str(ROOT / "app"))

import issues as I               # noqa: E402
from issues import engine        # noqa: E402

logging.getLogger("planetai.issues").setLevel(logging.ERROR)

FIX = json.loads((ROOT / "app/issues/fixtures/node1-2026-09-06.json").read_text())
NOW = datetime.fromisoformat(FIX["as_of"])
DECL = I.load()
fails = []


def check(ok, msg):
    if not ok:
        fails.append(msg)


# The engine's own snapshot cursor, not a double written for this test: `/issues/fixtures/<name>`
# renders through the same class, so a fixture that replays here is a fixture the route can serve.
Cur = engine.Replay


class Settings:
    def __init__(self, **kw):
        self.kw = kw

    def get(self, key, default=""):
        return self.kw.get(key, default)


def run(data=None, declared="air,heat,land,coast", earth=None, now=NOW):
    return engine.compute(Cur(data if data is not None else FIX), Settings(NODE_ISSUES=declared),
                          DECL, earth=earth, now=now)


EARTH = {"radius_m": 5000, "years": list(range(2017, 2026)), "frames": [2017, 2019, 2022, 2025],
         "latest": {"year_a": 2024, "year_b": 2025, "share_over_threshold": 0.01192,
                    "hectares_over_threshold": 119.2, "computed_at": "2026-09-06T05:34:50Z"},
         "attribution": "AlphaEarth Foundations, Google and Google DeepMind. CC BY 4.0."}

OUT = run(earth=EARTH)

# --- the stack -----------------------------------------------------------------------------------
air = OUT["issues"]["air"]["stack"]
check(round(air["room"]["value"], 1) == 5.1, f"air room is {air['room'] and air['room']['value']}, expected 5.1")
check(air["room"]["n"] == 3, f"air room used {air['room']['n']} sensors, expected 3")
check(air["room"]["provenance"] == "live", f"air room is {air['room']['provenance']}, expected live")
check(round(air["ring"]["value"], 1) == 7.0, f"air ring is {air['ring'] and air['ring']['value']}, expected 7.0")
check(air["ring"]["provenance"] == "partial", "somebody else's sensor is partial, never live")
check(air["region"]["value"] == 15, f"air region is {air['region'] and air['region']['value']}, expected 15")
check(air["region"]["provenance"] == "model", "a model row is `model`")
check(air["yard"] is None, "node #1 has no kit on the wall outside, so the yard column is empty")

heat = OUT["issues"]["heat"]["stack"]
check(heat["room"] is not None and round(heat["room"]["value"], 1) == 30.8,
      f"heat room is {heat['room'] and round(heat['room']['value'], 2)}, expected 30.8")
check(heat["room"]["n"] == 4, f"heat room used {heat['room']['n']} sensors, expected 4")
check(heat["region"] is not None, "heat's region needs temp_model and humidity_model, both on om-point")

# The order of operations is not a detail: on this capture the two answers differ by 0.3 °C.
per_sensor_then_median = round(heat["room"]["value"], 2)
T = {r["sensor_id"]: r["mean_15m"] for r in FIX["stats"]
     if r["metric"] == "temp" and r["local"] and r["indoor"]}
H = {r["sensor_id"]: r["mean_15m"] for r in FIX["stats"]
     if r["metric"] == "humidity" and r["local"] and r["indoor"]}
both = [s for s in T if s in H and T[s] is not None and H[s] is not None]
import statistics  # noqa: E402
median_then_apparent = round(engine.apparent(statistics.median([T[s] for s in both]),
                                             statistics.median([H[s] for s in both])), 2)
check(per_sensor_then_median != median_then_apparent,
      "this capture no longer distinguishes the two orders of operation, so the test above proves nothing")
check(round(heat["room"]["value"], 2) == 30.82,
      f"per-sensor apparent then median is {round(heat['room']['value'], 2)}, expected 30.82")
check(abs(per_sensor_then_median - median_then_apparent) > 0.2,
      f"the two orders give {per_sensor_then_median} and {median_then_apparent}, which is too close "
      f"for this capture to prove anything about the order of operations")

# --- the fence -----------------------------------------------------------------------------------
# 152 is dropped and the median of what is left is 7.5, not the unfenced 10. That is the point:
# the trimmed median answers "what is the neighbourhood reading", and 5 to 10 is the answer.
med, out = engine.fenced_median([5, 10, 152])
check(med == 7.5 and out == [152], f"a ring of 5, 10, 152 fenced to {med} with {out} outside")
med, out = engine.fenced_median([5, 10, 12])
check(med == 10 and out == [], f"a ring that agrees fenced to {med}, dropping {out}")
med, out = engine.fenced_median([7, 7, 7, 7])
check(med == 7 and out == [], "a ring that agrees exactly must not fence itself down")
check(engine.fenced_median([])[0] is None, "an empty ring has no median")
# Tukey would not catch the 152: with three stations it IS the upper quartile, so 1.5 x IQR sits at
# 152 + 1.5 x 147 and calls nothing odd. That is the whole reason this is a MAD fence.
q1, q3 = 5, 152
check(152 <= q3 + 1.5 * (q3 - q1), "Tukey's fence would keep the 152 — which is why MAD is used")

# Somebody else's kit indoors is in the ring geographically and must never be in the street's number.
check(any(r["metric"] == "pm25" and not r["local"] and r["indoor"] for r in FIX["stats"]),
      "this capture no longer holds a non-local indoor station, so the filter below proves nothing")
# --- the states ----------------------------------------------------------------------------------
# 1 + 2: the two the rho analysis found, on the real capture.
check(OUT["issues"]["heat"]["state"] == "act",
      f"heat is {OUT['issues']['heat']['state']}; #65 is an act ask 60 minutes old, so it is act")
check(OUT["issues"]["heat"]["reason"]["alert_id"] == 65,
      f"heat's reason names alert {OUT['issues']['heat']['reason'].get('alert_id')}, expected 65")
check(OUT["issues"]["air"]["state"] == "notable",
      f"air is {OUT['issues']['air']['state']}; #53 is open but the room came back to 5, so it is notable")
check(OUT["issues"]["air"]["reason"]["code"] == "open_ask_stale",
      f"air's reason is {OUT['issues']['air']['reason']['code']}, expected open_ask_stale")
check(OUT["issues"]["air"]["reason"]["alert_id"] == 53,
      f"air's reason names alert {OUT['issues']['air']['reason'].get('alert_id')}, expected 53")
stale = [a for a in OUT["issues"]["air"]["open_asks"] if a["id"] == 53]
check(stale and stale[0]["current"] is False, "#53 must be listed, open, and not current")

# 3: an open act ask whose room IS over the line stays act however old it is
hot = json.loads(json.dumps(FIX))
for r in hot["stats"]:
    if r["metric"] == "pm25" and r["local"] and r["indoor"]:
        r["mean_15m"] = 60.0
o = run(hot, earth=EARTH)
check(o["issues"]["air"]["state"] == "act",
      f"with the room at 60 and #53 open, air is {o['issues']['air']['state']}, expected act")

# 4: context — land, with a record
check(OUT["issues"]["land"]["state"] == "context",
      f"land is {OUT['issues']['land']['state']}, expected context")
check(round(OUT["issues"]["land"]["stack"]["region"]["value"], 1) == 1.2,
      "land's region is this node's own share_over_threshold as a percentage")
check(OUT["issues"]["land"]["stack"]["region"]["source"].startswith("this node's own"),
      "land's sentence and stack come from the node's own record, not from Earth Engine's score")

# 5: the fallback is named as a different measure
no_earth = run(earth=None)
lr = no_earth["issues"]["land"]["stack"]["region"]
check(lr is not None and lr.get("fallback"), "with no earth record, land falls back and says so")
check(lr["value"] == 0.037, f"the fallback is ee-point's land_change_score, got {lr['value']}")

# 6: none — no source at all
empty = {"stats": [], "observations": [], "alerts": [], "actions": [], "readings_1h": []}
e = run(empty)
for key in ("air", "heat", "land", "coast"):
    check(e["issues"][key]["state"] == "none", f"on an empty node {key} is {e['issues'][key]['state']}")
    check(e["issues"][key]["reason"]["code"] == "no_source", f"{key} must say why it is none")
    check(e["issues"][key]["sentence"]["en"], f"{key} must still have a sentence with no source")
check(e["order"] == ["air", "heat", "land", "coast"], "an empty node keeps the declared order")

# 7: a tie goes to the declared order
quiet = json.loads(json.dumps(FIX))
quiet["alerts"], quiet["actions"] = [], []
for declared, want in (("air,heat", "air"), ("heat,air", "heat")):
    t = run(quiet, declared=declared, earth=EARTH)
    check(t["issues"]["air"]["state"] == t["issues"]["heat"]["state"],
          "this case only tests the tie-break while air and heat are in the same state")
    check(t["headline"] == want,
          f"with NODE_ISSUES={declared} and a tie, the headline is {t['headline']}, expected {want}")

# 8: an undeclared issue is still shown, greyed, as not watched here
part = run(declared="air,heat", earth=EARTH)
check(part["order"] == ["air", "heat"], f"order is {part['order']}")
check(part["undeclared"] == ["coast", "land"], f"undeclared is {part['undeclared']}")
check(part["issues"]["land"]["state"] == "none" and part["issues"]["land"]["watched"] is False,
      "an undeclared issue is none and not watched")
check(part["issues"]["land"]["reason"]["code"] == "not_watched",
      "and it says that, rather than pretending it has no source")
check(part["headline"] == "heat", "the headline only ever comes from the declared issues")

# --- the headline rule ---------------------------------------------------------------------------
check(OUT["headline"] == "heat",
      f"the headline is {OUT['headline']}; heat is act and air only notable, so heat wins even "
      f"though air is declared first")

# --- every locale, every placeholder -------------------------------------------------------------
for key, iss in OUT["issues"].items():
    for loc in I.LOCALES:
        s = iss["sentence"][loc]
        check(s, f"{key}: the {loc} sentence is empty")
        check("{" not in s and "}" not in s, f"{key}: the {loc} sentence has an unfilled brace: {s}")
        check("  " not in s, f"{key}: the {loc} sentence has a gap where a placeholder was: {s}")
        check(not re.search(r"\s[,.]", s), f"{key}: the {loc} sentence has a space before punctuation: {s}")
        check(iss["reason_text"][loc], f"{key}: the {loc} reason is empty")
# every class must render, or a classifier that returns one will put a brace on a wall
for key, d in DECL.items():
    if d["kind"] != "sensed":
        continue
    for cls in I.CLASSES:
        for loc in I.LOCALES:
            st = engine._sentence(dict(d, key=key), OUT["issues"][key]["stack"], "notable",
                                  OUT["issues"][key]["headline"], "steady", loc,
                                  d["compare"], cls)
            check(st and "{" not in st, f"{key}.{cls}.{loc} did not render: {st!r}")

# the numeral is the one the stack carries, formatted to the issue's own dp
check("5 µg/m³" in OUT["issues"]["air"]["sentence"]["en"],
      f"air's numeral is not in its sentence: {OUT['issues']['air']['sentence']['en']}")
check("30.8 °C" in OUT["issues"]["heat"]["sentence"]["en"],
      f"heat's numeral is not in its sentence: {OUT['issues']['heat']['sentence']['en']}")

# --- attribution ---------------------------------------------------------------------------------
check(OUT["issues"]["air"]["attribution"] == "clear",
      f"air is {OUT['issues']['air']['attribution']}; 5 in the room and 7 on the street are both "
      f"under 15, so nothing is being attributed to anywhere")
o = run(hot, earth=EARTH)                                   # room 60, ring 7
check(o["issues"]["air"]["attribution"] == "inside",
      f"with the room at 60 and the street at 7, air is {o['issues']['air']['attribution']}")
street = json.loads(json.dumps(FIX))
for r in street["stats"]:
    if r["metric"] == "pm25" and not r["local"] and not r["indoor"]:
        r["mean_15m"] = 90.0
o = run(street, earth=EARTH)
check(o["issues"]["air"]["attribution"] == "outside_worse",
      f"with the street at 90 and the room at 5, air is {o['issues']['air']['attribution']}")
both_bad = json.loads(json.dumps(FIX))
for r in both_bad["stats"]:
    if r["metric"] == "pm25" and not r["indoor"]:
        r["mean_15m"] = 80.0
    if r["metric"] == "pm25" and r["local"] and r["indoor"]:
        r["mean_15m"] = 80.0
o = run(both_bad, earth=EARTH)
check(o["issues"]["air"]["attribution"] == "everywhere",
      f"with everything at 80, air is {o['issues']['air']['attribution']}")
check(engine._classify({"room": None, "ring": {"value": 9}}, {"value": 15}, {"mode": "ratio", "margin": 1.5})
      == "unknown", "with no room reading there is nothing to attribute")

# degrees must not compare by ratio: 30 against 20 is ten degrees, not half again as hot
check(engine._worse(30, 20, {"mode": "difference", "margin": 2}) == "over", "30 is over 20 by 10 degrees")
check(engine._worse(21, 20, {"mode": "difference", "margin": 2}) == "level", "one degree apart is level")
check(engine._worse(21, 20, {"mode": "ratio", "margin": 1.5}) == "level", "21 and 20 are level by ratio too")
check(engine._worse(31, 20, {"mode": "ratio", "margin": 1.5}) == "over", "31 is over 20 by ratio")

# --- the series ----------------------------------------------------------------------------------
ser = OUT["issues"]["air"]["series"]
check(len(OUT["buckets"] if "buckets" in OUT else OUT["issues"]["air"]["buckets"]) == 24,
      "the series is 24 buckets")
check(ser["room"] == [5, 5, 4.5, 4.5, 5, 6, 9, 7, 5, 4.5, 4.5, 5, 5.5, 6, 8, 17, 12, 6, 5, 4.5, 4.5, 5, 5, 5],
      f"air's room series does not reproduce the transcribed chart: {ser['room']}")
check(ser["ring"] and len(ser["ring"]) == 24, "air's ring series is 24 long")
check(ser["region"] is None, "a model row has no per-sensor hourly series, so region is empty")
check(all(v is None or isinstance(v, float) for v in ser["room"]), "series values are numbers or None")

# --- provenance ----------------------------------------------------------------------------------
prov = {r["figure"]: r for r in OUT["issues"]["air"]["provenance"]}
for want in ("air.room", "air.ring", "air.region", "air.line"):
    check(want in prov, f"{want} has no provenance row, so the Figures band cannot draw it")
check(prov["air.line"]["source"].startswith("WHO 2021"), "the line names its source")
check({r["provenance"] for r in OUT["issues"]["land"]["provenance"]} <= {"model", "partial", "reference"},
      "land's figures carry only words the layer knows")

# --- an eighth issue costs no query ---------------------------------------------------------------
class Counting(engine.Replay):
    def __init__(self, data):
        super().__init__(data)
        self.n = 0

    def execute(self, sql, args=()):
        self.n += 1
        super().execute(sql, args)


c = Counting(FIX)
engine.compute(c, Settings(NODE_ISSUES="air,heat,land,coast"), DECL, earth=EARTH, now=NOW)
check(c.n == 5, f"the engine ran {c.n} queries for four issues; it must read each table once")
c = Counting(FIX)
engine.compute(c, Settings(NODE_ISSUES="air"), DECL, earth=EARTH, now=NOW)
check(c.n == 5, f"the engine ran {c.n} queries for one issue; the reads are not per-issue")

print("\n".join(f"  x {f}" for f in fails if f) or
      f"  issues/engine: the stack, the fence, the five states on eight cases, the headline rule, "
      f"attribution in six classes, and {len(OUT['issues']) * len(I.LOCALES)} sentences with every "
      f"placeholder filled — replayed against node #1, 6 Sep 14:08 UTC")
sys.exit(1 if [f for f in fails if f] else 0)
