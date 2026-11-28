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
    import wall as W  # noqa: E402
    centre = W.cell_centre()
    check(got["supply_origin_km"] == round(W.dist_km(centre, o["lon"], o["lat"])) and isinstance(got["supply_origin_km"], int),
          "the origin figure is whole km from the middle of the cell, never from the node")
    _cc, W.cell_centre = W.cell_centre, lambda: None
    check("supply_origin_km" not in stated_rows(A.fetch(StubHC(FIXDOC))[1]), "no cell centre, no origin figure")
    W.cell_centre = _cc
    check(o["basin"] is None and R["fetched_at"], "no hydro, no basin")

    calls = []; A.fetch(StubHC(FIXDOC, calls)); check(calls == [], "inside the refresh days, no second read")
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

class BoxHC(StubHC):
    def post(self, url, data=None, **kw):
        self.calls.append(data["data"].split("\n")[0])
        return type("Resp", (), {"raise_for_status": lambda s: None, "json": lambda s: self.doc})()


with tempfile.TemporaryDirectory() as tmp3:
    os.environ["PACK_OUT"] = tmp3
    os.environ["SUPPLY_SOURCES"] = ""
    boxes, cells = [], []
    for la, lo in (("-8.82", "115.15"), ("-8.8203", "115.1503")):
        os.environ["NODE_LAT"], os.environ["NODE_LON"] = la, lo
        cells.append(W.home_cell())
        (pathlib.Path(tmp3) / "supply" / "osm.json").unlink(missing_ok=True)
        A.fetch(BoxHC(FIXDOC, boxes))
    check(cells[0] == cells[1] and len(boxes) == 2 and boxes[0] == boxes[1], "two points in one cell ask the map for the same square")
    c = W.cell_centre()
    check(abs(float(boxes[0].split("bbox:")[1].split(",")[0]) - (c[1] - 25 / 111.32)) < 1e-9,
          "the square is centred on the middle of the cell")

with tempfile.TemporaryDirectory() as tmp2:
    os.environ["PACK_OUT"] = tmp2
    os.environ["NODE_LAT"] = "-8.82"
    os.environ["SUPPLY_SOURCES"] = "Trucks | truck | steady | "
    sn, rn = A.fetch(FailingHC()); Rn = A.result()
    check(len(sn) == 1 and stated_rows(rn) == {"supply_sources": 1, "supply_first_holds": 0} and Rn["works"] == [] and Rn["fetched_at"] is None
          and Rn["stated"][0]["id"] == "trucks", "a failed read with no cache: statement kept, no works, no date, rows still back")

import logging  # noqa: E402

# The node's point never chooses: the works, the sensor's position, the day's stamp, and no cell centre.
with tempfile.TemporaryDirectory() as tmp4:
    os.environ["PACK_OUT"] = tmp4
    os.environ["NODE_LAT"], os.environ["NODE_LON"] = "-8.82", "115.15"
    c = W.cell_centre()
    node = (-8.82, 115.15)
    el = lambda la, lo: {"type": "node", "lat": la, "lon": lo, "tags": {"man_made": "water_works", "name": "Twin Works"}}
    os.environ["SUPPLY_SOURCES"] = "Twin | piped | | Twin Works"
    sn, rn = A.fetch(StubHC({"elements": [el(*node), el(c[1], c[0])]}))
    o = A.result()["stated"][0]["origin"]
    check((o["lat"], o["lon"]) == (c[1], c[0]), f"of two works of one name, the nearest to the middle of the cell is taken: {o}")
    check((sn[0]["lat"], sn[0]["lon"]) == (c[1], c[0]) and (sn[0]["lat"], sn[0]["lon"]) != node,
          "the sensor row stands at the middle of the cell, never at the node's point")
    check((A.result()["lat"], A.result()["lon"]) == node, "the result keeps the node's point for the keeper's km")
    _, rn2 = A.fetch(StubHC({"elements": []}))
    t1, t2 = {t for t, *_ in rn}, {t for t, *_ in rn2}
    midnight = lambda t: t.utcoffset() == timedelta(0) and (t.hour, t.minute, t.second, t.microsecond) == (0, 0, 0, 0)
    check(len(t1) == len(t2) == 1 and all(midnight(t) for t in t1 | t2) and (max(t2) - max(t1)) in (timedelta(0), timedelta(days=1)),
          "each fetch stamps its rows with the start of its UTC day, so two in one day share a stamp")

    # No cell centre: no map read, the cache kept, the statement kept with no km and no basin, a warning once.
    age_cache(31)
    seen = []
    h = logging.Handler(); h.emit = lambda rec: seen.append(rec)
    A.log.addHandler(h); A.log.setLevel(logging.INFO)
    _w, A._wall = A._wall, lambda: None
    A._state["no_centre"] = False
    try:
        nc = []
        os.environ["SUPPLY_SOURCES"] = "Twin | piped | steady | Twin Works; Ours | well | | -8.83, 115.16"
        s0, r0 = A.fetch(StubHC(FIXDOC, nc)); A.fetch(StubHC(FIXDOC, nc)); R0 = A.result()
        check(nc == [], "no cell centre: the map is not read")
        check(len(R0["works"]) == 2 and [x["id"] for x in R0["stated"]] == ["twin", "ours"], "no cell centre: the cached works and the statement are kept")
        check(R0["stated"][0]["origin"] is None and R0["stated"][1]["origin"]["how"] == "stated" and R0["stated"][1]["origin"]["basin"] is None,
              "no cell centre: no named origin is picked, a typed one has no basin")
        check(stated_rows(r0) == {"supply_sources": 2, "supply_first_holds": 0}, "no cell centre: no km row")
        check(s0[0]["lat"] is None and s0[0]["lon"] is None, "no cell centre: the sensor row has no position")
        check(sum("no cell centre" in rec.getMessage() and rec.levelno == logging.WARNING for rec in seen) == 1, "no cell centre: one warning")
        import packs  # noqa: E402
        _m, packs.module = packs.module, lambda *a, **k: None
        seen.clear()
        check(A._hydro() == (None, {}) and A._hydro() == (None, {}), "hydro off: no basins")
        packs.module = _m
        check(sum("hydro" in rec.getMessage() for rec in seen) == 1, f"hydro off: said once, not every poll: {[r.getMessage() for r in seen]}")
    except Exception as e:  # noqa: BLE001
        check(False, f"no cell centre raised: {e!r}")
    finally:
        A._wall = _w
        A.log.removeHandler(h); A.log.setLevel(logging.NOTSET)

for label, la, lo in (("nan", "nan", 115.2), ("inf", -8.8, "inf"), ("lat out of range", 91, 115.2), ("lon out of range", -8.8, 181)):
    check(osm.parse({"elements": [{"type": "node", "lat": la, "lon": lo, "tags": {"man_made": "water_well"}}]}) == [], f"a point that is {label} is dropped")

SQ = lambda x0, y0: [[x0, y0], [x0 + 1, y0], [x0 + 1, y0 + 1], [x0, y0 + 1], [x0, y0]]
H = {"basins": {"features": [{"properties": {"here": True}, "geometry": {"type": "Polygon", "coordinates": [SQ(0, 0)]}},
                             {"properties": {}, "geometry": {"type": "MultiPolygon", "coordinates": [[SQ(1, 0)]]}}]}}


def inside(lon, lat, rings):
    return any(r[0][0] <= lon <= r[1][0] and r[0][1] <= lat <= r[2][1] for r in rings)


C0 = (0.5, 0.5)   # (lat, lon) of the cell's middle, inside the first basin
check(core.basin_of(0.5, 0.5, H, inside, C0) == "same" and core.basin_of(0.5, 1.5, H, inside, C0) == "other"
      and core.basin_of(5.0, 5.0, H, inside, C0) == "beyond" and core.basin_of(0.5, 0.5, {}, inside, C0) is None, "same, other, beyond, and none without hydro")
check(core.basin_of(0.5, 0.5, H, inside, None) is None, "no cell centre, no basin word")
# A basin edge splits the cell: hydro flags the basin holding the node's point, the middle of the cell is in the other.
C1 = (0.5, 1.5)
check(core.basin_of(0.5, 1.5, H, inside, C1) == "same" and core.basin_of(0.5, 0.5, H, inside, C1) == "other",
      "the basin word follows the middle of the cell, never hydro's flag for the node's point")
HY = load("hydro_adapter", "packs/hydro/adapter.py")
sq = lambda x0, y0: [[x0, y0], [x0 + .1, y0], [x0 + .1, y0 + .1], [x0, y0 + .1], [x0, y0]]
HB = {"basins": {"features": [{"type": "Feature", "properties": {"here": True}, "geometry": {"type": "Polygon", "coordinates": [sq(115.1, -8.9)]}},
                              {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [sq(115.2, -8.9)]}}]}}
CB = (-8.85, 115.15)
check(core.basin_of(-8.85, 115.15, HB, HY.inside, CB) == "same" and core.basin_of(-8.85, 115.25, HB, HY.inside, CB) == "other"
      and core.basin_of(-8.0, 114.0, HB, HY.inside, CB) == "beyond", "hydro's own inside on hydro's basins shape")
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
adapter_km = A.osm.km


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
    raw = resp.text
    pts = [TYPED_LAT, TYPED_LON, NODE_LAT, 115.1635]
    check(not any(f"{v:.{d}f}" in raw for v in pts for d in (3, 4)) and not any(str(v) in raw for v in pts),
          "neither the typed point nor the node's is anywhere in the answer, at 3, 4 or full digits")
    check("entry" not in resp.text, "no raw entry for a stranger")

    os.environ["NODE_KIND"] = "home"
    j = client.get("/supply").json()
    check(all("lat" not in w for w in j["works"]) and all("lat" not in (s.get("origin") or {}) for s in j["sources"]) and j["works"][0]["km"] is not None,
          "a house's WiFi gets no points")
    ROWS["SHARE_LEVEL"] = "off"
    check(TestClient(main.app, client=("10.0.0.9", 5)).get("/supply").status_code in (401, 403), "a house that does not share answers no stranger")
    ROWS["SHARE_LEVEL"] = "open"
    os.environ.pop("NODE_KIND") if _kind is None else os.environ.__setitem__("NODE_KIND", _kind)

    # a stranger's km come from the cell's middle, the keeper's from the node
    import wall as W  # noqa: E402
    ctr = W.cell_centre()
    probe = next((la, 115.1635) for la in [NODE_LAT + 0.0005 * i for i in range(20, 200)]
                 if round(adapter_km(NODE_LAT, 115.1635, la, 115.1635)) != round(W.dist_km(ctr, 115.1635, la)))
    pl, po = probe
    patch_result(dict(DOC, works=[{"kind": "works", "name": "Probe", "operator": None, "lat": pl, "lon": po}], stated=[]))
    mine_km = client.get("/supply", headers=ADMIN).json()["works"][0]["km"]
    check(mine_km == round(adapter_km(NODE_LAT, 115.1635, pl, po), 1), "the keeper's km is from the node, one decimal")
    os.environ["NODE_KIND"] = "community"
    st_km = client.get("/supply").json()["works"][0]["km"]
    check(st_km == round(W.dist_km(ctr, po, pl)) and st_km != round(adapter_km(NODE_LAT, 115.1635, pl, po)), "a stranger's km is from the cell's middle, whole")
    os.environ.pop("NODE_KIND") if _kind is None else os.environ.__setitem__("NODE_KIND", _kind)

    # the act token is the keeper, X-Agent gets the stranger's view, a community node that does not share answers no stranger
    patch_result(DOC)
    check(client.get("/supply", headers={"Authorization": "Bearer act-tok"}).json()["sources"][2]["origin"]["lat"] == TYPED_LAT, "the act token counts as the keeper")
    ag = client.get("/supply", headers=dict(ADMIN, **{"X-Agent": "bot"})).json()
    check("lat" not in ag["sources"][2]["origin"] and ag["sources"][0]["origin"]["km"] == round(ag["sources"][0]["origin"]["km"]), "X-Agent with the admin token gets the stranger's answer")
    os.environ["NODE_KIND"] = "community"
    ROWS["SHARE_LEVEL"] = "off"
    check(TestClient(main.app, client=("10.0.0.9", 5)).get("/supply").status_code in (401, 403), "a community node that does not share answers no stranger")
    ROWS["SHARE_LEVEL"] = "open"
    os.environ.pop("NODE_KIND") if _kind is None else os.environ.__setitem__("NODE_KIND", _kind)

    # ?reader=1 gives the keeper's own token the stranger's answer, as the printed report asks for it
    patch_result(dict(DOC, stated=DOC["stated"] + [src(None, None, None, None, problem="kind", entry="A | canal | | ")]))
    rd = client.get("/supply?reader=1", headers=ADMIN)
    jr = rd.json()
    check(rd.status_code == 200 and "entry" not in rd.text and "A | canal" not in rd.text, "reader=1: no raw entry, even for the keeper")
    check("lat" not in jr["sources"][2]["origin"] and not any(f"{v:.3f}" in rd.text for v in (TYPED_LAT, TYPED_LON)), "reader=1: no typed point")
    check(jr["sources"][0]["origin"]["km"] == round(W.dist_km(ctr, 115.19, -8.80)) and all(w["km"] == round(w["km"]) for w in jr["works"]),
          "reader=1: whole km from the middle of the cell")
    check("lat" in client.get("/supply", headers=ADMIN).json()["sources"][2]["origin"], "without the flag the keeper still gets every point")

    # every entry bad, for the keeper
    patch_result(dict(DOC, stated=[src(None, None, None, None, problem="kind", entry="A | canal | | ")], works=[]))
    check(client.get("/supply", headers=ADMIN).json()["hint"] == "not read: see the entries", "all entries bad: the keeper is told to see them")
    os.environ["NODE_KIND"] = "community"
    sj = client.get("/supply").json()
    check(sj["hint"].startswith("not stated") and sj["sources"] == [], "a stranger's answer does not change")
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
