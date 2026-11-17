"""The Place report's reading (docs/SPEC_place_report.md §11): the facts it may rest on, the rules that write it, the
check a model's text must pass, and the two routes. app/reading.py is imported as it is; the model is a stub and the
database a fake cursor, so nothing here needs Postgres, a network or a model.

Run: PYTHONPATH=app python3 tests/test_reading.py
"""
import json
import re
import sys
from datetime import date

import reading

fails = []


def check(ok, msg):
    if not ok:
        fails.append(msg)


TODAY = date(2026, 11, 17)
# node #1 as it stood on 17 Nov 2026: the place pack's last poll, one stale distance, the surface and the terrain
N1 = {"buildings": (2459.0, "2026-11-14"), "sat_buildings": (5994.0, "2026-11-14"), "osm_building_coverage": (0.41, "2026-11-14"),
      "built_share": (0.076, "2026-11-14"), "green_share": (0.341, "2026-11-14"), "commercial_share": (0.0, "2026-11-14"),
      "businesses_per_km2": (6.048, "2026-11-14"), "roads_km": (58.48, "2026-11-14"),
      "poi_food": (10.0, "2026-11-14"), "poi_retail": (3.0, "2026-11-14"), "poi_education": (0.0, "2026-11-14"),
      "poi_health": (0.0, "2026-11-14"), "poi_worship": (0.0, "2026-11-14"), "poi_lodging": (5.0, "2026-11-14"),
      "poi_services": (1.0, "2026-11-14"), "nearest_health_m": (948.305, "2026-09-06"),
      "lst_delta": (0.58, "2026-11-06"), "terrain_upslope_ha": (0.09, "2026-10-23")}
HYDRO = {"lat": -8.81961234, "lon": 115.16412345, "nearest": {"dist_m": 3555, "dis_av_cms": 0.125},
         "basin": {"level12": {"up_area": 318.6, "sub_area": 318.6}, "level4": {"sub_area": 140534.8}}}
ENERGY = {"grid": "bali", "kind": "estimated", "share": {"low": 0.8419, "high": 0.9908927631259593},
          "sources": [{"name": "GIS Bandara", "km": 4.06, "lat": -8.74, "lon": 115.16}]}
INDEX = {"chosen": "bali", "place": {"name": "Bali", "slug": "bali"}, "read": {"ok": True, "at": "2026-11-16T08:41:54.129Z"},
         "score": {"status_label": "Partial", "cells_measured": 1, "cells_total": 20, "fci": 0.037}}
YEARLY = [(2016, 3105.0), (2019, 4410.0), (2023, 5994.0)]


def n1(**over):
    a = dict(latest=N1, hydro=HYDRO, energy=ENERGY, index=INDEX, labs=[3.4, 21.0, 64.2], air=(12, 45), held=2, yearly=YEARLY, today=TODAY)
    a.update(over)
    return reading.shape(**a)


# ---------------------------------------------------------------- the facts
doc = n1()
F = doc["facts"]
check(F["clinic_km"] == {"v": 1, "at": "2026-09-06"}, f"a distance from the node's point is whole kilometres: {F.get('clinic_km')}")
check(not [k for k in F if k.endswith("_m")], "no fact is in metres from the node's point")
check(F["poi_health"] == {"v": 0, "at": "2026-11-14"}, f"a zero the node holds is held, not missing: {F.get('poi_health')}")
check(F["school_km"] is None and doc["fill"]["school_km"], "a fact the node does not hold is None, with what fills it")
check(F["river_km"]["v"] == 4 and F["basin_km2"]["v"] == 319 and F["bioregion_km2"]["v"] == 140535, f"hydro: {F.get('river_km')}, {F.get('basin_km2')}")
check(F["fossil_low_pct"]["v"] == 84 and F["fossil_high_pct"]["v"] == 99 and F["grid"]["v"] == "Bali", f"energy: {F.get('fossil_low_pct')}")
check(F["index_place"]["v"] == "Bali" and F["index_label"]["v"] == "Partial" and F["index_measured"]["v"] == 1 and F["index_cells"]["v"] == 20, "the Index place")
check(F["labs_50km"]["v"] == 2 and F["lab_km"]["v"] == 3, f"labs: {F.get('labs_50km')}, {F.get('lab_km')}")
check(F["air_days_over"]["v"] == 12 and F["air_days"]["v"] == 45, "the air figure, with 30 measured days or more")
check(n1(air=(12, 20))["facts"]["air_days_over"] is None, "under 30 measured days the node does not state the air figure")
check(F["buildings_then"]["v"] == 3105 and F["buildings_then_year"]["v"] == 2016 and F["cells_held"]["v"] == 2, "the yearly count and the cells")
old = n1(latest={**N1, "green_share": (0.341, "2025-09-01")})
check(old["facts"]["green_share"] is None and "green_share" in old["fill"], "a figure older than 400 days counts as not held")
bare = n1(hydro=None)
check(all(bare["facts"][k] is None for k in ("river_km", "basin_km2", "bioregion_km2")) and bare["fill"]["basin_km2"] == "planetai run hydro fetch",
      "with no hydro every hydro fact is None, and the fill is the pack's own command")
J = json.dumps(doc)
check(not re.search(r"-?\d+\.\d{4,}", J), f"no coordinate, and nothing finer than three decimals, in the facts: {re.findall(r'-?[0-9]+[.][0-9]{4,}', J)[:3]}")
check(not re.search(r"lat|lon|sensor|GIS Bandara", J), "no point, no sensor and no named source in the facts")
check(set(doc["fill"]) == {k for k, v in F.items() if v is None}, "fill names exactly the facts that are missing")
check(reading.say("green_share", 0.341) == "34%" and reading.say("buildings", 2459.0) == "2459" and reading.say("heat_delta_c", 0.58) == "0.6"
      and reading.say("clinic_km", 1) == "1" and reading.say("grid", "Bali") == "Bali", "one formatter turns a fact into text")
empty = reading.shape(latest={}, hydro=None, energy=None, index=None, labs=[], air=None, held=None, yearly=[], today=TODAY)
check(all(v is None for v in empty["facts"].values()) and set(empty["fill"]) == set(empty["facts"]), "a node that holds nothing has every fact None")
print(f"  reading: the facts ({len(F)} keys), whole kilometres, zeros held, stale and missing ones named with what fills them")

# ---------------------------------------------------------------- the rules
NAMES = re.compile(r"mumford|mcharg|papanek|meadows|jacobs", re.I)
R = reading.rules(doc)
sec = {s["id"]: s for s in R["sections"]}
check([s["id"] for s in R["sections"]] == [i for i, _ in reading.SECTIONS] and [s["heading"] for s in R["sections"]] == [h for _, h in reading.SECTIONS],
      "five sections, in the frame's order, with its headings")
check(all(s["lines"] and s["lines"] != [reading.NOTHING] for s in R["sections"]), f"on node #1 every section has something to say: {[(s['id'], len(s['lines'])) for s in R['sections']]}")
street, system = " ".join(sec["street"]["lines"]), " ".join(sec["system"]["lines"])
check("within a kilometre" in street and "as far as the public map goes" in street, f"the street is read within a kilometre, and a thin map is said to be thin: {street}")
check("41%" in system and "What is not drawn is not planned for." in system, f"the system section reads the gap in the map: {system}")
check("in this cell" not in json.dumps(R), "the place pack reads a kilometre round the point, never 'this cell'")
A = R["avenues"]
check(4 <= len(A) <= 6, f"{len(A)} avenues, not four to six")
check(all(a["layer"] in reading.LAYERS and a["action"] in reading.ACTIONS and a["signal"] in reading.SIGNALS for a in A), "every avenue sits in the frame")
check(all(a["title"] and a["first_step"] and re.search(r"\d", a["why"]) for a in A), f"on node #1 every avenue has a first step and rests on a figure: {[a['why'] for a in A if not re.search(chr(92) + 'd', a['why'])]}")
check(any(a["with"] == "the lab about 3 km away" for a in A) and all(a["with"] is None for a in A if a["action"] == "Map and research"), f"an experiment names the lab's distance: {[a['with'] for a in A]}")
check(not NAMES.search(json.dumps(R)), "the reading names nobody")
check(R["blind"] and all(b["what"] and b["command"] for b in R["blind"]) and any("school" in b["what"] for b in R["blind"]), f"what it cannot see, each with what fills it: {R['blind']}")
print(f"  reading: node #1 reads as five sections and {len(A)} avenues, each in the frame, and says what it cannot see")

E = reading.rules(empty)
check(all(s["lines"] == [reading.NOTHING] for s in E["sections"]) and reading.NOTHING == "The node holds nothing yet that speaks to this.", "a section with nothing held says so in one line")
check(len(E["avenues"]) == 4 and all(a["action"] == "Map and research" and a["with"] is None for a in E["avenues"]), f"a node that holds nothing gets four avenues to map and research: {[a['title'] for a in E['avenues']]}")
check(all(any(c in a["first_step"] for c in set(reading.FILL.values())) for a in E["avenues"]), "each of them starts with the command that fills the gap")
check({k for b in E["blind"] for k in b["facts"]} == set(reading.FILL), "everything missing is in the blind list")
check("undefined" not in json.dumps(E) and "None" not in json.dumps(E), "nothing unfilled leaks into the text")
zero = reading.rules(n1(latest={**N1, **{k: (0.0, "2026-11-14") for k in N1 if k.startswith("poi_")}}))
zs = " ".join({s["id"]: s for s in zero["sections"]}["street"]["lines"])
check("0 kinds" not in zs and "house visitors" not in zs and "No shop" in zs, f"a place with nothing drawn says so, and divides by nothing: {zs}")
one = reading.rules(n1(labs=[0.3], hydro={**HYDRO, "nearest": {"dist_m": 300}}))
check("A river runs within a kilometre." in json.dumps(one) and "the lab within a kilometre" in json.dumps(one) and not re.search(r"\b0 km", json.dumps(one)),
      "a distance under a kilometre is said in words, never as 0 km")
print("  reading: an empty node gets four avenues from its gaps; zeros and short distances read as sentences")

# ---------------------------------------------------------------- a model's text: kept only if its numbers are the node's
ALL = "\n".join(l for s in R["sections"] for l in s["lines"]) + "\n" + "\n".join(a["title"] + " " + a["why"] + " " + a["first_step"] + " " + (a["with"] or "") for a in A)
check(reading.stray_numbers(ALL, doc) == [], f"the rules print every number as the check reads it: {reading.stray_numbers(ALL, doc)}")
for ok_text in ("2,459 buildings are drawn, and 5,994 seen.", "34% of the ground is green", "34 % green", "a share of 0.34", "0.341 of the ground",
                "up from 3105 in 2016", "in 2 of its 7 cells", "three or 4 avenues, 1 to 7 of them", "140,535 km² and 140535 km²", "0.6 °C hotter", "within 50 km"):
    check(reading.stray_numbers(ok_text, doc) == [], f"'{ok_text}' holds only the node's numbers, yet {reading.stray_numbers(ok_text, doc)} strayed")
for bad_text, n in (("35% of the ground is green", "35"), ("about 2,500 buildings", "2500"), ("9 avenues", "9"), ("in 2021 it changed", "2021"), ("0.7 °C hotter", "0.7")):
    got = reading.stray_numbers(bad_text, doc)
    check(got and (n is None or n in got), f"'{bad_text}' strays, and the check said {got}")

GOOD = {"sections": {i: f"A paragraph on {h.lower()}, resting on 34% of green ground and 5,994 buildings." for i, h in reading.SECTIONS},
        "avenues": [{"title": f"Avenue {k}", "why": "84% of the power is burned.", "first_step": "Count ten roofs.", "layer": reading.LAYERS[k],
                     "action": reading.ACTIONS[k % 3], "signal": reading.SIGNALS[k % 3]} for k in range(4)]}
w, why = reading.accept(json.dumps(GOOD), doc)
check(w is not None and why == "" and set(w["sections"]) == {i for i, _ in reading.SECTIONS} and len(w["avenues"]) == 4 and w["avenues"][0]["with"] is None, f"a good answer is kept: {why}")
check(reading.accept("```json\n" + json.dumps(GOOD) + "\n```", doc)[0] is not None, "a fenced answer is kept")
check(reading.accept("Here is the reading:\n" + json.dumps(GOOD) + "\nI hope it helps.", doc)[0] is not None, "prose round the answer is dropped")


def bad(change, want):
    g = json.loads(json.dumps(GOOD)); change(g)
    got, reason = reading.accept(json.dumps(g), doc)
    check(got is None and want in reason, f"expected a refusal saying '{want}', got {reason!r}")
    return reason


reasons = {bad(lambda g: g["sections"].pop("land"), "section"), bad(lambda g: g["sections"].update(extra="x"), "section"),
           bad(lambda g: g["avenues"].pop(), "avenues"), bad(lambda g: g["avenues"].extend(g["avenues"][:3]), "avenues"),
           bad(lambda g: g["avenues"][0].update(layer="Energy"), "layer"), bad(lambda g: g["avenues"][1].update(action="Build"), "action"),
           bad(lambda g: g["sections"].update(land="Half of it, 51%, is green."), "51"),
           bad(lambda g: g["sections"].update(street="As Jane Jacobs would say, the street lives."), "names a person"),
           bad(lambda g: g["avenues"][2].update(why="MUMFORD saw this."), "names a person"),
           bad(lambda g: g["sections"].update(region=""), "empty")}
check(len(reasons) >= 7, f"each kind of refusal says its own reason: {reasons}")
for junk in ("not json", "", "[1, 2]", '{"sections": "x"}', '{"sections": {}, "avenues": null}'):
    got, reason = reading.accept(junk, doc)
    check(got is None and reason, f"{junk!r} is refused with a reason, never an exception")
P = reading.prompt(doc, R)
check(all(h in P for _, h in reading.SECTIONS) and all(x in P for x in reading.LAYERS + reading.ACTIONS + reading.SIGNALS) and "name no person" in P.lower()
      and '"green_share"' in P and "60 to 120 words" in P, "the prompt carries the frame, the facts and the ban on names")
check(len(NAMES.findall(P)) == 5, "the five names live in the prompt, once each, and nowhere else")
print("  reading: a model's text is kept only with the frame's ids, the node's numbers and no person named")

if fails:
    print("\n".join("  x " + f for f in fails))
    sys.exit(1)
print("reading: every check passed")
