"""The supply pack's two pure modules, offline: the keeper's statement and the water works on the public map.

Run: PYTHONPATH=/tmp/stub:app python3 tests/test_supply.py
"""
import collections
import os
import importlib.util
import json
import pathlib
import sys

# set before the first import of an app module: app/packs.py reads PACKS_DIR when it is imported
os.environ.update(PACKS_DIR=str(pathlib.Path("packs").resolve()), ADMIN_TOKEN="admin-tok", ACT_TOKEN="act-tok",
                  NODE_LAT="-8.8161", NODE_LON="115.1635", DATABASE_URL="postgresql://unused/never-connected")

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
check(core.slug("Café Ñandú") == "cafe-nandu", "slug folds accents")
check(core.parse_sources("水 | piped | | ")[0]["problem"] == "name", "no Latin letters or digits: no id, so problem name")
check(core.parse_sources("A | piped | fails at times | ")[0]["holds"] == "fails at times", "fails at times is valid")
check(core.parse_sources("A | piped | seasonal | ")[0]["problem"] == "holds", "seasonal is not a holds")
B = core.parse_sources("A | canal | | ; A | piped | | ")
check([b["problem"] for b in B] == ["kind", "duplicate"], "a bad row still claims its name: the later good row is the duplicate")

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
check(kinds["tank"] == 3, "of 42 tanks in the fixture (15 fuel, 3 unknown, 21 untagged), only the 3 tagged water come out")
T = lambda **t: {"type": "node", "lat": -8.8, "lon": 115.2, "tags": t}
H = osm.parse({"elements": [T(man_made="storage_tank", content="fuel", name="f"), T(man_made="storage_tank", name="n"),
                            T(man_made="storage_tank", content="water", name="w"), T(man_made="pipeline", substance="gas", name="g"),
                            T(man_made="pipeline", substance="water", name="p")]})
check(sorted((h["kind"], h["name"]) for h in H) == [("pipeline", "p"), ("tank", "w")], "only the water tank and the water pipeline")
for label, doc in {"a string element": {"elements": ["s"]}, "a non-numeric lat": {"elements": [T(man_made="water_well")| {"lat": "x"}]},
                   "a list man_made": {"elements": [T(man_made=["water_well"])]}, "elements not a list": {"elements": 5}, "not a dict": []}.items():
    try:
        check(osm.parse(doc) == [], f"malformed input is skipped: {label}")
    except Exception as e:
        check(False, f"malformed input raised on {label}: {e!r}")
check(len(osm.parse({"elements": ["s", T(man_made="water_well"), {"lat": "x", "lon": 1, "tags": {"man_made": "water_well"}}]})) == 1, "a good element survives bad ones")
check(abs(osm.km(0, 0, 0, 1) - 111.19) < 0.1, "km")

# the adapter: the statement against the map, offline
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone

A = load("supply_adapter", "packs/supply/adapter.py")
FIXDOC = json.loads(FIX.read_text())


class StubHC:
    def __init__(self, doc, calls=None):
        self.doc, self.calls = doc, calls

    def post(self, url, data=None, **kw):
        if self.calls is not None:
            self.calls.append((url, kw.get("headers")))
        return type("Resp", (), {"raise_for_status": lambda s: None, "json": lambda s: self.doc})()


class FailingHC:
    def __init__(self, calls=None):
        self.calls = calls

    def post(self, url, **kw):
        if self.calls is not None:
            self.calls.append(url)
        raise OSError("overpass is down")


def age_tried(hours):
    f = pathlib.Path(os.environ["PACK_OUT"]) / "supply" / "tried.json"
    f.write_text(json.dumps({"at": (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()}))


def age_cache(days):
    f = pathlib.Path(os.environ["PACK_OUT"]) / "supply" / "osm.json"
    d = json.loads(f.read_text())
    d["fetched_at"] = (datetime.fromisoformat(d["fetched_at"]) - timedelta(days=days)).isoformat()
    f.write_text(json.dumps(d))


def stated_rows(rows):
    return {m: v for _, _, m, v in rows}


with tempfile.TemporaryDirectory() as tmp:
    os.environ["PACK_OUT"] = tmp
    os.environ["NODE_LAT"], os.environ["NODE_LON"] = "-8.82", "115.15"
    os.environ["SUPPLY_SOURCES"] = "PDAM Tirta Mangutama | piped | fails often | PDAM Tirta Mangutama; Water trucks | truck | | "
    sensors, rows = A.fetch(StubHC(FIXDOC)); R = A.result()
    pack = re.search(r"^metrics:\s*\[(.*?)\]", open("packs/supply/pack.yaml").read(), re.M).group(1)
    got = stated_rows(rows)
    check(sensors[0]["sensor_id"] == "supply-point" and set(got) == {"supply_sources", "supply_origin_km", "supply_first_holds"}, "the three figures")
    check(got["supply_sources"] == 2 and got["supply_first_holds"] == 2, "two sources, the first fails often")
    o = R["stated"][0]["origin"]
    check(o["how"] == "mapped" and o["name"] == "PDAM Tirta Mangutama" and abs(o["lat"] + 8.799) < 0.01, "the nearest of the two works of that name")
    check(R["stated"][1]["origin"] is None and R["counts"]["works"] == 3, "trucks have no origin; counts by kind")
    check({x.strip() for x in pack.split(",")} == set(got), "pack.yaml lists what fetch writes")
    check(o["basin"] is None and R["fetched_at"], "no hydro, no basin")

    calls = []; A.fetch(StubHC(FIXDOC, calls)); check(calls == [], "inside the refresh days, no second read")
    check(not any("@" in str(c) for c in calls), "no address in a header")
    age_cache(31); old = A.result()["fetched_at"]
    os.environ["SUPPLY_SOURCES"] = "Trucks | truck | | "
    _, rr = A.fetch(FailingHC()); R3 = A.result()
    check(R3["counts"]["works"] == 3 and R3["fetched_at"] == json.loads((pathlib.Path(tmp) / "supply/osm.json").read_text())["fetched_at"]
          and R3["stated"][0]["id"] == "trucks" and R3["fetched_at"] != old and stated_rows(rr) == {"supply_sources": 1},
          "Overpass down: the last works and their old date are kept, the result is rewritten")
    fc = []; A.fetch(FailingHC(fc)); check(fc == [], "after a failed read, no new try for 6 hours")
    age_tried(7); A.fetch(FailingHC(fc)); check(len(fc) == 1, "after 6 hours it tries again")
    os.environ["SUPPLY_SOURCES"] = "PDAM Tirta Mangutama | piped | fails often | PDAM Tirta Mangutama"
    uac = []; (pathlib.Path(tmp) / "supply/tried.json").unlink(); A.fetch(StubHC(FIXDOC, uac))
    check(uac and uac[0][1]["User-Agent"] == "planetai-node/supply (+https://planetai.fab.city)", "the User-Agent, exactly")

    os.environ["NODE_LAT"] = "-8.8201"
    cc = []; A.fetch(StubHC(FIXDOC, cc)); check(cc == [] , "a node a few metres off keeps its cache")
    os.environ["NODE_LAT"] = "-8.82"
    os.environ["SUPPLY_SOURCES"] = "Office | piped | | PDAM Badung"; A.fetch(StubHC(FIXDOC))
    check(A.result()["stated"][0]["origin"] is None, "an office named after the utility is not an origin")
    os.environ["SUPPLY_SOURCES"] = "Our well | well | steady | -8.8201, 115.1502"; A.fetch(StubHC(FIXDOC))
    check(A.result()["stated"][0]["origin"]["how"] == "stated", "a typed point is stated")
    os.environ["SUPPLY_SOURCES"] = "Bad | canal | fails often | ; Tank | rain | | "
    s2, r2 = A.fetch(StubHC(FIXDOC)); R2 = A.result()
    check(R2["stated"][0]["problem"] == "kind" and R2["stated"][0]["origin"] is None and stated_rows(r2) == {"supply_sources": 1},
          "a source with a problem is kept, not counted, and is not the first")
    os.environ["SUPPLY_SOURCES"] = ""; s, r = A.fetch(StubHC(FIXDOC))
    check({m for _, _, m, _ in r} == {"supply_sources"} and r[0][3] == 0 and A.result()["works"], "nothing stated: one row, zero sources, the works still kept")
    check(all(w["name"] or w["kind"] in ("works", "pumping", "reservoir", "dam") for w in A.result()["works"]), "unnamed wells, towers and tanks are only counted")
    os.environ["NODE_LAT"] = "-8.0"
    check(A.result() == {}, "the node moved: nothing kept for here")
    del os.environ["NODE_LAT"]
    check(A.fetch(StubHC(FIXDOC)) == ([], []) and A.result() == {}, "no point: nothing, no raise")

with tempfile.TemporaryDirectory() as tmp2:
    os.environ["PACK_OUT"] = tmp2
    os.environ["NODE_LAT"] = "-8.82"
    os.environ["SUPPLY_SOURCES"] = "Trucks | truck | steady | "
    sn, rn = A.fetch(FailingHC()); Rn = A.result()
    check(len(sn) == 1 and stated_rows(rn) == {"supply_sources": 1, "supply_first_holds": 0} and Rn["works"] == [] and Rn["fetched_at"] is None
          and Rn["stated"][0]["id"] == "trucks", "a failed read with no cache: statement kept, no works, no date, rows still back")

SQ = lambda x0, y0: [[x0, y0], [x0 + 1, y0], [x0 + 1, y0 + 1], [x0, y0 + 1], [x0, y0]]
H = {"basins": {"features": [{"properties": {"here": True}, "geometry": {"type": "Polygon", "coordinates": [SQ(0, 0)]}},
                             {"properties": {}, "geometry": {"type": "MultiPolygon", "coordinates": [[SQ(1, 0)]]}}]}}


def inside(lon, lat, rings):
    return any(r[0][0] <= lon <= r[1][0] and r[0][1] <= lat <= r[2][1] for r in rings)


check(core.basin_of(0.5, 0.5, H, inside) == "same" and core.basin_of(0.5, 1.5, H, inside) == "other"
      and core.basin_of(5.0, 5.0, H, inside) == "beyond" and core.basin_of(0.5, 0.5, {}, inside) is None, "same, other, beyond, and none without hydro")
HY = load("hydro_adapter", "packs/hydro/adapter.py")
sq = lambda x0, y0: [[x0, y0], [x0 + .1, y0], [x0 + .1, y0 + .1], [x0, y0 + .1], [x0, y0]]
HB = {"basins": {"features": [{"type": "Feature", "properties": {"here": True}, "geometry": {"type": "Polygon", "coordinates": [sq(115.1, -8.9)]}},
                              {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [sq(115.2, -8.9)]}}]}}
check(core.basin_of(-8.85, 115.15, HB, HY.inside) == "same" and core.basin_of(-8.85, 115.25, HB, HY.inside) == "other"
      and core.basin_of(-8.0, 114.0, HB, HY.inside) == "beyond", "hydro's own inside on hydro's basins shape")
W2 = [{"kind": "works", "name": "Água Pura", "lat": 0.0, "lon": 0.0}, {"kind": "works", "name": "agua pura", "lat": 5.0, "lon": 5.0},
      {"kind": "tank", "name": "agua pura", "lat": 0.1, "lon": 0.1}]
r = core.resolve({"origin": {"how": "name", "name": "AGUA PURA"}}, W2, 4.0, 4.0)
check(r["how"] == "mapped" and (r["lat"], r["lon"]) == (5.0, 5.0), "case and accents ignored; nearest match; tanks are not origins")

# ── GET /supply: who gets which points ───────────────────────────────────────
import logging
import tempfile
import time

sys.path = [p for p in sys.path if p != "/tmp/stub"]
sys.modules.pop("httpx", None)
logging.disable(logging.WARNING)
import settings  # noqa: E402
ROWS = {"PACKS_ENABLED": "", "SHARE_LEVEL": "open"}
settings._cache = {"at": time.time() + 1e9, "rows": ROWS}
import db  # noqa: E402
import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(main.app)
ADMIN = {"Authorization": "Bearer admin-tok"}
db.q = main.q = lambda sql, *a: []
NODE_LAT, TYPED_LAT, TYPED_LON = -8.8161, -8.8302, 115.1711


def src(i, name, kind, holds, origin=None, problem=None, entry=""):
    return {"entry": entry, "id": i, "name": name, "kind": kind, "holds": holds, "origin": origin, "problem": problem}


DOC = {"lat": NODE_LAT, "lon": 115.1635, "radius_km": 25, "fetched_at": "2026-11-28T00:00:00+00:00",
       "stated": [src("pdam", "PDAM", "piped", "fails at times", {"how": "mapped", "name": "IPA Ungasan", "lat": -8.80, "lon": 115.19, "basin": "same"}),
                  src("truck", "Truck", "truck", "fails often", None),
                  src("our-well", "Our well", "well", "steady", {"how": "stated", "name": "Our well", "lat": TYPED_LAT, "lon": TYPED_LON, "basin": "same"})],
       "works": [{"kind": "works", "name": "Zeta", "operator": None, "lat": -8.70, "lon": 115.30},
                 {"kind": "works", "name": "IPA Ungasan", "operator": "PDAM", "lat": -8.80, "lon": 115.19}],
       "counts": {"works": 2}, "attribution": ["© OpenStreetMap contributors, ODbL, via Overpass"]}
with tempfile.TemporaryDirectory() as tmp:
    os.environ["PACK_OUT"] = tmp
    os.environ["NODE_LAT"], os.environ["NODE_LON"] = "-8.8161", "115.1635"
    os.makedirs(tmp + "/supply")

    def patch_result(doc):
        pathlib.Path(tmp, "supply", "result.json").write_text(json.dumps(doc))

    patch_result(DOC)
    r = client.get("/supply", headers=ADMIN).json()
    check(r["state"] == "both" and r["sources"][2]["origin"]["lat"] == TYPED_LAT and isinstance(r["sources"][0]["origin"]["km"], float)
          and r["radius_km"] == 25, "the keeper sees every point, km from the node")
    check(r["works"][0]["name"] == "IPA Ungasan" and r["attribution"][-1] == "Water supply as stated by the keeper of this node", "nearest first; both credits")

    _kind = os.environ.get("NODE_KIND")
    os.environ["NODE_KIND"] = "community"
    main._INDOOR.update(at=1.0, ids=set(), names=set())
    resp = client.get("/supply")
    j = resp.json()
    check(resp.status_code == 200 and "lat" not in j["sources"][2]["origin"] and j["sources"][2]["origin"]["km"] == round(j["sources"][2]["origin"]["km"]),
          "a stranger never gets a typed point, and km are whole")
    check("lat" in j["sources"][0]["origin"] and "lat" in j["works"][0], "a stranger on a community node gets the points of mapped works")
    check(str(TYPED_LAT) not in resp.text and str(NODE_LAT) not in resp.text, "neither the typed point nor the node's is anywhere in the answer")
    check("entry" not in resp.text, "no raw entry for a stranger")

    os.environ["NODE_KIND"] = "home"
    j = client.get("/supply").json()
    check(all("lat" not in w for w in j["works"]) and all("lat" not in (s.get("origin") or {}) for s in j["sources"]) and j["works"][0]["km"] is not None,
          "a house's WiFi gets no points")
    ROWS["SHARE_LEVEL"] = "off"
    check(TestClient(main.app, client=("10.0.0.9", 5)).get("/supply").status_code in (401, 403), "a house that does not share answers no stranger")
    ROWS["SHARE_LEVEL"] = "open"
    os.environ.pop("NODE_KIND") if _kind is None else os.environ.__setitem__("NODE_KIND", _kind)

    patch_result({})
    j = client.get("/supply", headers=ADMIN).json()
    check(j["state"] == "none" and j["sources"] == [] and j["hint"].startswith("not stated"), "nothing stated, nothing mapped")
    patch_result(dict(DOC, stated=[src(None, None, None, None, problem="kind", entry="A | canal | | ")] + DOC["stated"][:1], works=[]))
    j = client.get("/supply", headers=ADMIN).json()
    check(j["sources"][0] == {"entry": "A | canal | | ", "problem": "kind"} and j["state"] == "stated" and j["works"] == [], "a bad entry is a row with its problem")
    patch_result(dict(DOC, stated=[]))
    check(client.get("/supply", headers=ADMIN).json()["state"] == "mapped", "works only is mapped")
    patch_result({"stated": "x", "works": [3, None, {"lat": "a"}], "counts": 5})
    resp = client.get("/supply", headers=ADMIN)
    check(resp.status_code == 200 and resp.json()["state"] == "none", "a result of an unexpected shape is the none answer")


if fails:
    print("FAIL:", *fails, sep="\n  ")
    sys.exit(1)
print("ok")
