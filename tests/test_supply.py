"""The supply pack's two pure modules, offline: the keeper's statement and the water works on the public map.

Run: PYTHONPATH=/tmp/stub:app python3 tests/test_supply.py
"""
import collections
import importlib.util
import json
import pathlib
import sys

FIX = pathlib.Path("packs/supply/tests/fixtures/overpass-south-bali.json")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


core = load("supply_core", "packs/supply/supply_core.py")
osm = load("supply_osm", "packs/supply/osm.py")
fails = []


def check(cond, name):
    if not cond:
        fails.append(name)


check(core.slug("  PDAM Tirta Mangutama!") == "pdam-tirta-mangutama", "slug")

P = core.parse_sources("PDAM Tirta Mangutama | piped | fails often | PDAM Tirta Mangutama; Water trucks | truck | | ")
check([p["id"] for p in P] == ["pdam-tirta-mangutama", "water-trucks"] and all(p["problem"] is None for p in P), "two sources, in order")
check(P[0]["holds"] == "fails often" and P[0]["origin"] == {"how": "name", "name": "PDAM Tirta Mangutama"}, "a named origin")
check(P[1]["holds"] is None and P[1]["origin"] is None, "blank holds and blank origin are valid")
check(core.parse_sources("Well | well | steady | -8.80, 115.16")[0]["origin"] == {"how": "point", "lat": -8.8, "lon": 115.16}, "a typed point")
bad = {"A | piped": "fields", " | piped | | ": "name", "A | canal | | ": "kind", "A | piped | sometimes | ": "holds",
       "A | piped | | 95.0, 300.0": "origin", "A | piped | | ; A | truck | | ": "duplicate"}
for text, why in bad.items():
    check(core.parse_sources(text)[-1]["problem"] == why and core.parse_sources(text)[-1]["entry"], f"kept with its problem: {why}")
check(core.parse_sources("") == [] and core.parse_sources("  ;  ") == [], "nothing stated is an empty list")

W = osm.parse(json.loads(FIX.read_text()))
kinds = collections.Counter(w["kind"] for w in W)
check(kinds["works"] == 3 and kinds["dam"] == 5 and kinds["well"] == 3 and kinds["tower"] == 3 and kinds["tank"] == 3, "the south Bali read, by kind")
check(kinds["reservoir"] == 4 and any(w["name"] == "Waduk Muara Nusa Dua" for w in W if w["kind"] == "reservoir"), "four reservoirs, Waduk Muara Nusa Dua among them")
check(sum(1 for w in W if w["kind"] == "works" and w["name"] == "PDAM Tirta Mangutama") == 2, "the utility's two works")
check(not any(w["name"] in ("PDAM Badung", "PDAM Kota Denpasar", "Honda") for w in W), "offices and shops are not works")
check(not any(w["kind"] == "tank" and w.get("content") not in (None, "water") for w in W), "fuel tanks are dropped")
check(abs(osm.km(0, 0, 0, 1) - 111.19) < 0.1, "km")

if fails:
    print("FAIL:", *fails, sep="\n  ")
    sys.exit(1)
print("ok")
