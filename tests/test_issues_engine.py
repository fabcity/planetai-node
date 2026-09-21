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
from issues import geometry      # noqa: E402

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

    def num(self, key, default):
        # production's app/settings.py:num() reads a string and falls back on anything not a plain
        # digit string; the stub only ever holds ints in tests, so a straight int() is enough here.
        v = self.kw.get(key)
        return int(v) if v is not None else default


def run(data=None, declared="air,heat,land,coast", earth=None, now=NOW):
    return engine.compute(Cur(data if data is not None else FIX), Settings(NODE_ISSUES=declared),
                          DECL, earth=earth, now=now)


EARTH = {"radius_m": 5000, "years": list(range(2017, 2026)), "frames": [2017, 2019, 2022, 2025],
         # the shape packs/earth actually writes, checked against node #1's live /earth on 11 Sep
         "latest": {"year_a": 2024, "year_b": 2025, "share_over_threshold": 0.01192,
                    "hectares_over_threshold": 119.2, "threshold": 0.15, "mean": 0.04345,
                    "computed_at": "2026-09-06T05:34:50Z"},
         # every comparison the pack computed, as /earth's `changes` lists them: the yearly pairs and
         # the one long span. The sentence's "8.5 % since 2017" comes from the longest span that ends
         # in the latest year, and from nowhere else.
         "changes": [{"year_a": 2017, "year_b": 2025, "share_over_threshold": 0.08468},
                     {"year_a": 2023, "year_b": 2024, "share_over_threshold": 0.0101},
                     {"year_a": 2024, "year_b": 2025, "share_over_threshold": 0.01192}],
         "attribution": "AlphaEarth Foundations, Google and Google DeepMind. CC BY 4.0."}

OUT = run(earth=EARTH)

# --- what the sentences add beyond the number ---------------------------------------------------
# Land's history. The latest pair is the number; the longest span is the direction, and a household
# deciding whether the trees behind them are going needs both.
_land_en = OUT["issues"]["land"]["sentence"]["en"]
check("between 2024 and 2025" in _land_en, f"land must say which two years it compared: {_land_en}")
check("8.5 % since 2017" in _land_en, f"land must say how far back the change goes: {_land_en}")
_no_span = run(earth={**EARTH, "changes": [EARTH["changes"][-1]]})["issues"]["land"]["sentence"]["en"]
check("since" not in _no_span and "  " not in _no_span,
      f"with no long span the sentence closes cleanly rather than leaving a gap: {_no_span}")
for loc in I.LOCALES:
    check(OUT["issues"]["land"]["sentence"][loc].count("2017") == 1, f"land.{loc} names the span year once")

# Heat has a direction now, the way air has. Whichever verb the trend picks, the numeral must survive.
_heat_verbs = DECL["heat"]["sentences"]["en"]["verbs"]
check(set(_heat_verbs) == {"rising", "steady", "falling"}, "heat declares all three directions")
check(any(OUT["issues"]["heat"]["sentence"]["en"].startswith(v) for v in _heat_verbs.values()),
      f"heat's sentence opens with one of its verbs: {OUT['issues']['heat']['sentence']['en']}")

# The day's high. A quiet issue used to say "nothing to say"; with 24 hours in hand it says the one
# thing there is to say. The reason carries the value WITH its unit and the hour it landed in.
_quiet = run(data={**FIX, "alerts": [], "actions": []}, declared="air")["issues"]["air"]
check(_quiet["state"] in ("quiet", "notable"), f"with no alerts air is quiet or over the line, not {_quiet['state']}")
check(_quiet["reason"].get("peak") == "17 µg/m³", f"the day's high carries its unit: {_quiet['reason']}")
check(re.fullmatch(r"\d\d:\d\d", _quiet["reason"].get("peak_at") or ""), f"and its hour: {_quiet['reason']}")
check("17 µg/m³" in _quiet["reason_text"]["en"] and _quiet["reason"]["peak_at"] in _quiet["reason_text"]["en"],
      f"the quiet line says the high and when: {_quiet['reason_text']['en']}")
check(engine._peak([1, 2, 3], ["a", "b", "c"], 0, "x") == {}, "fewer than six hours is not a day")
check(engine._peak([None, 4, 9, 2, None, 3, 3, 1, 2], list(range(9)), 1, "°C")["peak"] == "9.0 °C",
      "the high skips the hours that never reported")
# The fixture's own two clocks: alerts at +08:00, buckets in UTC. The high is printed in the alerts'
# zone, so it sits beside the ask times on the same evening rather than eight hours away.
_z = engine._clock({"alerts": FIX["alerts"]})
check(_z is not None and datetime(2026, 9, 6, 6, 0, tzinfo=timezone.utc).astimezone(_z).hour == 14,
      "the clock is the alerts' zone when NODE_TZ is unset")
check(_quiet["reason"]["peak_at"] == "06:00" or engine._clock({"alerts": []}) is None,
      "with no alert to take a zone from, the bucket prints as it came")
check(engine._reason_text({"code": "no_alert"}, "en") == "quiet",
      "with no high known the quiet line stays short rather than printing empty braces")

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
lr = OUT["issues"]["land"]["stack"]["region"]
check(lr["source"].startswith("this node's own"),
      "land's sentence and stack come from the node's own record, not from Earth Engine's score")
# "1.3 % of the square changed" is not an answer without "changed by more than what".
check("0.15" in lr["source"], f"land's source line must name the threshold: {lr['source']}")
check((lr.get("extra") or {}).get("hectares_over_threshold"),
      "the band needs the hectares without a second request")
for r in OUT["issues"]["land"]["readouts"]:
    check(round(r["value"], r["dp"]) == r["value"],
          f'{r["metric"]} arrives at {r["value"]}, not rounded to its own {r["dp"]} dp — the page draws, '
          f'it does not round')

# 5: with no record, land is `none` — it does not reach for a different measure of the same idea.
# The capture still HOLDS a land_change_score row (observations keeps the latest per source per
# metric forever, and node #1 ran earth-engine before v0.33.1 retired that metric), so this is the
# case where falling back would put a year-old number on the wall as this year's answer.
check(any(o["metric"] == "land_change_score" for o in FIX["observations"]),
      "the capture no longer holds a retired land_change_score row, so this case proves nothing")
no_earth = run(earth=None)
land = no_earth["issues"]["land"]
check(land["stack"]["region"] is None, "with no earth record land's region is empty")
check(land["state"] == "none" and land["reason"]["code"] == "no_source",
      f"with no earth record land is {land['state']}/{land['reason']['code']}, expected none/no_source")
check("earth fetch" in land["sentence"]["en"] or "satellite record" in land["sentence"]["en"],
      f"land must say how to get a record: {land['sentence']['en']}")
check(land["readouts"], "land keeps its built and trees readouts with no change record")
# and the mechanism is gone, not just unused
from issues import _distance_problems  # noqa: E402
check(_distance_problems("x", {"from": "earth", "fallback": {"from": "observations",
                                                            "sensor_id": "ee-point",
                                                            "metrics": ["land_change_score"]}}),
      "the validator must refuse a fallback, or the retired metric comes back in a fork")

# 6: none — no source at all
empty = {"stats": [], "observations": [], "alerts": [], "actions": [], "readings_1h": []}
e = run(empty)
for key in ("air", "heat", "land", "coast"):
    check(e["issues"][key]["state"] == "none", f"on an empty node {key} is {e['issues'][key]['state']}")
    check(e["issues"][key]["reason"]["code"] == "no_source", f"{key} must say why it is none")
    check(e["issues"][key]["sentence"]["en"], f"{key} must still have a sentence with no source")
check(e["order"] == ["air", "heat", "land", "coast"], "an empty node keeps the declared order")

# 6b: an ABSENT table is not an empty one.
#
# Until v0.67 `planetai snapshot` fetched three of the five tables Replay reads -- `actions` and
# `readings_1h` are not endpoints -- and a missing key read as `[]`. So every fixture taken in
# between replayed with no act ledger, no stages, no series and no barcode, and nothing anywhere
# said so. A design round would have measured that as a page bug. Both halves are checked here: that
# an absent table refuses out loud, and that every fixture the route can serve carries all five.
for _missing in [k for _, k in engine.Replay.TABLES]:
    _partial = {k: v for k, v in empty.items() if k != _missing}
    try:
        run(_partial)
        check(False, f"a snapshot carrying no {_missing} replayed silently instead of refusing")
    except LookupError as _exc:
        check(_missing in str(_exc), f"a refusal must name the table it wants, got: {_exc}")

# 6c: the digest — simple mode's whole answer, so a brace left in it is the entire page.
#
# Four stages, three languages, twelve sentences, on a node with data and on one with none. The
# empty node matters more than the populated one: that is the node a tester sets up on a Tuesday,
# and "{issues} issues watched here" printed literally is what the page would lead with.
for _case, _d in (("node #1", run()), ("an empty node", e)):
    _dg = _d.get("digest")
    check(isinstance(_dg, dict), f"{_case}: /issues carries no digest")
    for _stage in ("observe", "decide", "act", "measure"):
        for _loc in ("en", "id", "es"):
            _s = (_dg or {}).get(_stage, {}).get(_loc)
            check(isinstance(_s, str), f"{_case}: digest.{_stage}.{_loc} is not a sentence")
            if _case == "node #1":
                check(_s, f"{_case}: digest.{_stage}.{_loc} is empty")
            check("{" not in (_s or "") and "}" not in (_s or ""),
                  f"{_case}: digest.{_stage}.{_loc} has an unfilled placeholder: {_s}")

# The cell area is grouped for the language it is read in. A comma is the DECIMAL mark in Spanish
# and Indonesian, so an English "639,550 m2" reads there as six hundred and thirty-nine point five
# five — the same digits, three orders of magnitude out, in the one sentence that has to be right.
# The number itself depends on where the node stands, so this checks the separator and not a value.
_dec = run()["digest"]["decide"]
_m = re.search(r"([\d,]{5,}) m", _dec["en"])
check(_m is not None and "," in _m.group(1), f"en groups thousands with commas: {_dec['en']}")
if _m:
    _same = _m.group(1).replace(",", ".")
    check(_same in _dec["es"], f"es wants {_same}: {_dec['es']}")
    check(_same in _dec["id"], f"id wants {_same}: {_dec['id']}")

# rho stays out of the digest. It is specified over its own window in docs/SPEC_rho.md and computed
# by app/index.py from a query Replay cannot answer, so a digest that reported one would be a second
# rho over a different window — and two of them disagreeing on one page is worse than one absent.
for _loc in ("en", "id", "es"):
    check("%" not in run()["digest"]["measure"][_loc],
          f"measure reports the ledger, never a rate a reader could take for rho: "
          f"{run()['digest']['measure'][_loc]}")

for _fx in sorted((ROOT / "app/issues/fixtures").glob("*.json")):
    _snap = json.loads(_fx.read_text())
    _absent = [k for _, k in engine.Replay.TABLES if k not in _snap]
    check(not _absent, f"{_fx.name} is served by /issues/fixtures/ but cannot be replayed: "
                       f"it carries no {', '.join(_absent)}. A snapshot that is evidence of the "
                       f"wire rather than a render belongs in docs/design/fixtures/.")

# 7: level on state, the one that MOVED leads; an exact tie goes to the declared order
#
# This asserted "a tie goes to the declared order" for both orders, and on 18 September it started
# failing for the right reason: change became the tie-break inside a state, and in this capture the
# two issues are not actually tied. air moved 0.0714 of its own recent level over the last three
# hours against the three before; heat moved 0.0. So air leads whichever order the household typed,
# which is the whole of what was asked for. The declared order still breaks an EXACT tie, and the
# unit cases at the foot of this file hold it to that with issues built to be equal on both counts.
quiet = json.loads(json.dumps(FIX))
quiet["alerts"], quiet["actions"] = [], []
for declared in ("air,heat", "heat,air"):
    t = run(quiet, declared=declared, earth=EARTH)
    check(t["issues"]["air"]["state"] == t["issues"]["heat"]["state"],
          "this case only tests the tie-break while air and heat are in the same state")
    check(t["issues"]["air"]["moved"] > t["issues"]["heat"]["moved"],
          f"this case needs air to be the one that moved: air {t['issues']['air']['moved']}, "
          f"heat {t['issues']['heat']['moved']}")
    check(t["headline"] == "air",
          f"with NODE_ISSUES={declared}, level on state, the headline is the one that moved: "
          f"got {t['headline']}, expected air")

# 8: an undeclared issue is still shown, greyed, as not watched here
part = run(declared="air,heat", earth=EARTH)
check(part["order"] == ["air", "heat"], f"order is {part['order']}")
check(part["undeclared"] == ["coast", "land"], f"undeclared is {part['undeclared']}")
check(part["issues"]["land"]["state"] == "none" and part["issues"]["land"]["watched"] is False,
      "an undeclared issue is none and not watched")
check(part["issues"]["land"]["reason"]["code"] == "not_watched",
      "and it says that, rather than pretending it has no source")
for loc in I.LOCALES:
    s = part["issues"]["coast"]["sentence"][loc]
    check("watch" in s.lower() or "pantau" in s.lower() or "vigila" in s.lower(),
          f"an unwatched issue's {loc} sentence must say it is not watched, not that there is no "
          f"source — there may well be one: {s}")
check(part["issues"]["coast"]["sentence"]["en"][0].isupper(),
      "and it must be a sentence")
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

# --- the keys the modular dashboard reads ---------------------------------------------------------
body = engine.replay(FIX, Settings(), DECL)

st = body.get("stations")
if not st or len(st) != 14:
    fails.append(f"stations: 14 with coordinates in the fixture, got {len(st or [])}")
else:
    sc = next(s for s in st if s["sensor_id"] == "sc-19849")
    if sc["source"] != "smartcitizen" or sc["url"] != "https://smartcitizen.me/kits/19849":
        fails.append(f"a Smart Citizen kit links to its page: {sc['source']} {sc['url']}")
    if "pm25" not in sc["read"] or sc["read"]["pm25"]["unit"] != "µg/m³":
        fails.append(f"a station's read carries the declared unit: {sc['read'].get('pm25')}")
    bad = next(s for s in st if s["sensor_id"].startswith("bad-"))
    if bad["attribution"] != "Bali Air Dispatch, baliairdispatch.com":
        fails.append("Bali Air Dispatch rows carry the attribution the observatory requires")
    traced = [s["sensor_id"] for s in st if s["series"]]
    if sorted(traced) != ["bad-sc-19774", "sc-19880"]:
        fails.append(f"the fixture has an hourly series for exactly two stations, got {traced}")
    if st != sorted(st, key=lambda s: s["km"]):
        fails.append("stations are ordered by distance")
    band = next((v for s in st for v in s["series"].values() if v), None)
    if not band or band[0].get("min") is None or band[0].get("max") is None or band[0].get("n") is None:
        fails.append(f"readings_1h has min/max/n in the fixture, so a station's series must carry them: {band}")

m = body.get("metrics", {})
if m.get("pm25", {}).get("issue") != "air" or m.get("temp", {}).get("dp") != 1:
    fails.append(f"metrics declare unit, places and issue: {m.get('pm25')} {m.get('temp')}")

a = body.get("asks", {})
if len(a.get("acts", [])) != 21 or len(a.get("actions", [])) != 11 or a.get("levels", {}).get("warn") != 9:
    fails.append(f"asks: 21 acts, 11 actions, 9 warn in the fixture; got {len(a.get('acts', []))}, "
                 f"{len(a.get('actions', []))}, {a.get('levels')}")
if any("\n" in x["text"] or len(x["text"]) > 160 for x in a.get("acts", [])):
    fails.append("an ask's text is its first line, at most 160 characters")

mesh = body.get("mesh")
if not mesh or mesh["gateway"] != "!8f491db0" or mesh["packets"] != 12:
    fails.append(f"mesh: the gateway and its packets come from /health: {mesh}")
if not mesh or not any(r["metric"] == "battery_v" for r in mesh["reads"]):
    fails.append("mesh: the device's own 15-minute means ride with it")

# a snapshot with no mesh and no coordinates in health must not crash — it falls back to mesh=None,
# same as a live node with MQTT_HOST unset, and to a place it does not have
bare = engine.replay({**FIX, "health": {}}, Settings(), DECL)
check(bare.get("mesh") is None, "with no mesh in health, /issues publishes mesh: None, not a crash")
check(bare.get("stations"), "with no coordinates in health, stations still publish")

# ...and every distance on them is UNKNOWN, not a distance from (0, 0).
#
# "did not crash" is all this asserted, and under it the node published every neighbour's distance
# from the point where the equator meets the prime meridian — open water in the Gulf of Guinea — as a
# number, which four surfaces of the dashboard then printed to a household as fact. An unsited node
# knows how far away nothing is.
check(all(st["km"] is None for st in bare["stations"]),
      "unsited, every station's km is None: the node publishes unknown rather than a distance from (0, 0)")
check(all(st.get("read") is not None for st in bare["stations"]),
      "unsited, the readings themselves still publish — it is the distance that is unknown, not the air")
sited_kms = [st["km"] for st in body["stations"]]
check(all(k is not None for k in sited_kms) and sited_kms == sorted(sited_kms),
      f"sited, every station still carries a distance and the list is still nearest first: {sited_kms[:4]}")

# A negative RETICULUM_PRESENCE_RES is a number a keeper can type into Set up. h3.latlng_to_cell
# raises H3ResDomainError on one, and geometry.radio() clamped only the top end — so one bad setting
# took GET /issues down, and with it every surface of the page, over how coarsely this node announces
# itself. app/main.py's own presence path has always clamped both ends.
for _res, _want in ((-1, 0), (99, geometry.FLOOR_RES), (3, 3)):
    g = engine.replay(FIX, Settings(RETICULUM_PRESENCE_RES=_res), DECL)["geometry"]
    check(g is not None and g["radio"]["res"] == _want,
          f"RETICULUM_PRESENCE_RES={_res} must clamp to {_want}, not fail the whole response: "
          f"{None if g is None else g['radio']['res']}")

# --- the geometry the dial turns on --------------------------------------------------------------
g = body.get("geometry")
if not g:
    fails.append("geometry is on the body")
else:
    if g["nav"]["chain"][8] != "8895a4c86bfffff" or g["nav"]["cell_count"] != 209:
        fails.append(f"geometry.nav: node #1's res-8 cell and 209 published cells; got {g['nav']['chain'].get(8)}, {g['nav']['cell_count']}")
    if [c["key"] for c in g["claims"]][0] != "coast":
        fails.append("geometry.claims are widest first")
    if g["radio"]["res"] != 3:
        fails.append("geometry.radio announces at RETICULUM_PRESENCE_RES, 3 under the fixture's settings")
    if g["publication"]["res"] != 10 or g["settings"]["PRESENCE_RES_FLOOR"] != 6:
        fails.append(f"geometry carries the two lines: {g['publication']} {g['settings']}")
    own_cell = g["nav"]["cells"][g["nav"]["chain"][8]]
    if [body["stations"][i]["sensor_id"] for i in own_cell["sensors"]] != ["sc-19849", "sc-19880", "sc-19897"]:
        fails.append("the plate's sensor indices index into the published stations")

print("\n".join(f"  x {f}" for f in fails if f) or
      f"  issues/engine: the stack, the fence, the five states on eight cases, the headline rule, "
      f"attribution in six classes, and {len(OUT['issues']) * len(I.LOCALES)} sentences with every "
      f"placeholder filled — replayed against node #1, 6 Sep 14:08 UTC")
sys.exit(1 if [f for f in fails if f] else 0)


# ---------------------------------------------------------------- the headline, and what moved
# Asked 18 September 2026: lead with the data showing the most significant change. The rule was
# state alone — act, notable, quiet, context, none — with the household's declared order as the only
# tie-break, so two issues saying equally much were separated by alphabet.
#
# State still wins outright. That is the load-bearing half: something that needs doing cannot be
# pushed down the page by something that merely moved a lot. Change is the tie-break INSIDE a state.
from issues.engine import _headline, _moved            # noqa: E402

_DECLARED = ["air", "heat", "land", "coast"]


def _iss(state, moved):
    return {"state": state, "moved": moved}


for _name, _out, _want in [
    ("an act is never demoted by something that merely moved",
     {"air": _iss("notable", 0.90), "heat": _iss("act", 0.0),
      "land": _iss("context", 0.0), "coast": _iss("context", 0.0)}, "heat"),
    ("among equals, the one that moved most leads",
     {"air": _iss("notable", 0.02), "heat": _iss("notable", 0.40),
      "land": _iss("context", 0.0), "coast": _iss("context", 0.0)}, "heat"),
    ("an exact tie still goes to the order this place chose",
     {"air": _iss("notable", 0.20), "heat": _iss("notable", 0.20),
      "land": _iss("context", 0.0), "coast": _iss("context", 0.0)}, "air"),
    ("a big move in a lower state does not outrank a quiet higher one",
     {"air": _iss("notable", 0.0), "heat": _iss("context", 0.99),
      "land": _iss("context", 0.0), "coast": _iss("context", 0.0)}, "air"),
]:
    assert _headline(_out, _DECLARED) == _want, f"headline: {_name}"

# The size is read off the same six buckets the trend verb already uses, relative to the issue's own
# recent level — micrograms and degrees are not comparable quantities, and ranking them against each
# other by absolute magnitude would be arithmetic on a category error.
assert _moved([1, 1, 1, 2, 2, 2]) == 1.0, "a doubling is a move of one"
assert _moved([2, 2, 2, 1, 1, 1]) == 0.5, "a halving is as much news as a doubling, and unsigned"
assert _moved([5] * 6) == 0.0, "a flat run has not moved"
assert _moved([1, 2, 3]) == 0.0, "fewer than six buckets is not a small move, it is no evidence"
assert _moved([]) == 0.0 and _moved(None) == 0.0, "no series at all is not an error here"
print("  the headline leads on state, then on what moved, then on the order this place chose")
