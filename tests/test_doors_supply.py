"""Place's Water supply: the figures' row and the report's (doors-place.js :: supplyRow), the map layer's row, marks and
credit (doors-placemap.js :: LAYERS, supplyRows, supplyMarks, creditList), and the Data page's words (doors-data.js).

JSON goes through a temp file, never argv (the 128 KB E2BIG limit on Linux CI).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

fails: list[str] = []


def check(ok, msg):
    if not ok:
        fails.append(msg)


if not shutil.which("node"):
    print("  ✓ doors-supply: node not installed (skipped)")
    sys.exit(0)

WORKS = [{"kind": "reservoir", "name": "Waduk Muara", "operator": "PDAM", "km": 3.2, "lat": -8.8, "lon": 115.2},
         {"kind": "tower", "name": None, "operator": None, "km": 5.0, "lat": -8.81, "lon": 115.21},
         {"kind": "well", "name": "Sumur", "operator": None, "km": 7.0, "lat": -8.82, "lon": 115.22}]
SRC = [{"id": "a", "name": "PDAM Tirta Mangutama", "kind": "piped", "holds": "fails often",
        "origin": {"how": "mapped", "name": "Waduk Muara", "km": 12.0, "basin": "other", "lat": -8.7, "lon": 115.3}},
       {"id": "b", "name": "Water trucks", "kind": "truck", "holds": None,
        "origin": {"how": "stated", "name": None, "km": 0, "basin": "beyond", "lat": -8.6, "lon": 115.1}}]
EVIL = '<img src=x onerror=1>"&'
CASES = {
    "both": {"state": "both", "sources": SRC, "works": WORKS, "counts": {"works": 3}, "radius_km": 25, "attribution": [], "hint": None},
    "none": {"state": "none", "sources": [], "works": [], "counts": {}, "radius_km": 25, "hint": "not stated: set SUPPLY_SOURCES on Set up"},
    "mapped": {"state": "mapped", "sources": [], "works": WORKS, "counts": {"works": 3}, "radius_km": 25},
    "bad": {"state": "none", "sources": [{"entry": "Bad line", "problem": "no kind"}], "works": [], "counts": {}, "radius_km": 25},
    "typed": {"state": "stated", "sources": [{"id": "b", "name": "T", "kind": "truck", "holds": None, "origin": {"how": "stated", "name": None, "km": 4, "basin": None}}],
              "works": [], "counts": {}, "radius_km": 25},
    "wifi": {"state": "mapped", "sources": [], "works": [{k: v for k, v in w.items() if k not in ("lat", "lon")} for w in WORKS], "counts": {"works": 3}, "radius_km": 25},
    "near": {"state": "stated", "sources": [{"id": "a", "name": "Well", "kind": "well", "holds": "steady", "origin": {"how": "stated", "name": None, "km": 0, "basin": "same"}}], "works": [], "counts": {}, "radius_km": 25},
    "report": {"state": "both", "sources": [{"id": "a", "name": "PDAM", "kind": "piped", "holds": None, "origin": {"how": "mapped", "name": "W", "km": 12.3, "basin": "beyond"}},
                                           {"entry": "Bad line", "problem": "no kind"}], "works": [], "counts": {}, "radius_km": 25},
    "nulls": {"state": "both", "sources": [{"id": "a", "name": None, "kind": "well", "holds": None, "origin": None}], "works": WORKS[:1], "counts": {}, "radius_km": None},
    "nullsnone": {"state": "mapped", "sources": [], "works": WORKS, "counts": {}, "radius_km": None},
    "evil": {"state": "both", "sources": [{"id": "a", "name": EVIL, "kind": "well", "holds": None, "origin": None}, {"entry": EVIL, "problem": EVIL}],
             "works": [{"kind": "well", "name": EVIL, "operator": None, "km": 1, "lat": 1, "lon": 1}], "counts": {}, "radius_km": 25},
    "empty": {},
    "off": None,
    "ungasan": {"state": "both", "sources": [{"id": "a", "name": "PDAM", "kind": "piped", "holds": None,
                                             "origin": {"how": "mapped", "name": "Tower", "km": 5.0, "basin": "same", "lat": -8.81, "lon": 115.21}}],
                "works": WORKS, "counts": {}, "radius_km": 25},
}
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp) / "c.json"
    p.write_text(json.dumps(CASES))
    prog = f"""
const fs = require('fs'), vm = require('vm'), d3 = require('./app/static/d3.min.js');
const pm = fs.readFileSync('./app/static/doors-placemap.js', 'utf8'), pl = fs.readFileSync('./app/static/doors-place.js', 'utf8'), dd = fs.readFileSync('./app/static/doors-data.js', 'utf8');
const cake = fs.readFileSync('./app/static/doors-cake.js', 'utf8');
const lift = (src, n) => src.match(new RegExp('^function ' + n + '\\\\([\\\\s\\\\S]*?\\\\n}}\\\\n', 'm'))[0];
const cases = JSON.parse(fs.readFileSync({json.dumps(str(p))}, 'utf8')), out = {{ rows: {{}}, layer: {{}}, marks: {{}}, cakeFill: {{}} }};
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({{ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }}[c]));
let tok = false; const EVIL = '<img src=x onerror=1>"&';
const pc = {{ esc, DOORS_TOKEN: () => (tok ? 't' : '') }}; vm.createContext(pc);
vm.runInContext(pl.match(/^const BASIN = .*$/m)[0] + '\\n' + lift(pl, 'supplyRow') + 'this.supplyRow = supplyRow;', pc);
for (const [k, S] of Object.entries(cases)) {{ tok = true; const a = pc.supplyRow(S, true); const r = pc.supplyRow(S); tok = false; out.rows[k] = [a, r, pc.supplyRow(S, true), pc.supplyRow(S)]; }}
for (const [k, S] of Object.entries(cases)) {{
  out.layer[k] = {{}};
  for (const t of [true, false]) {{
    tok = t;
    const c = {{ PM: {{ on: {{ supply: true }}, supply: S, map: null, meta: null }}, SAT_MAX: 15, DOORS_TOKEN: () => (t ? 't' : '') }}; vm.createContext(c);
    vm.runInContext(cake + '\\n' + pm.match(/const LAYERS = \\[[\\s\\S]*?\\n\\];/)[0] + '\\nconst BY = Object.fromEntries(LAYERS.map(l => [l.id, l]));\\n' + lift(pm, 'supplyRows') + lift(pm, 'supplyMarks') + lift(pm, 'supplyDrawn') + lift(pm, 'creditList')
      + lift(pm, 'waterFacts') + pm.match(/^const placeCake = [\\s\\S]*?\\n}}\\) }}\\)\\);/m)[0]
      + 'supplyRows(); this.row = LAYERS.find(l => l.id === "supply"); this.credits = creditList(); this.m = supplyMarks(PM.supply, [115, -8.9]);'
      + 'this.fill = placeCake().flatMap(s => s.rows).find(r => r.name === "Water supply").fill;'
      + 'const fi = (t, v) => `<i>${{esc(t)}}${{v}}</i>`, hi = h => `<u>${{h}}</u>`;'
      + 'this.water = waterFacts(HOSTILE, fi, hi); this.ring = this.m.origins.map(o => waterFacts(o, fi, hi)).join("");', Object.assign(c, {{ esc, HOSTILE: {{ kind: EVIL, name: EVIL, operator: EVIL, km: 2 }} }}));
    out.layer[k][t ? 'tok' : 'bare'] = {{ row: c.row, credits: c.credits, fill: c.fill, water: c.water, ring: c.ring }};
    if (t) {{ out.marks[k] = c.m; out.water = c.water; }}
  }}
}}
/* supplyFrom: a sheet, no token, a token with a cell ring, and neither a ring nor a point */
const from = (PM, D, t) => {{
  const c = {{ PM, D, d3, DOORS_TOKEN: () => (t ? 't' : '') }}; vm.createContext(c);
  vm.runInContext(pm.match(/^const loop = .*$/m)[0] + '\\n' + lift(pm, 'supplyFrom') + 'this.r = supplyFrom();', c); return c.r;
}};
const ring = [ 'c', -8.0, 115.0, -8.0, 115.2, -8.2, 115.2, -8.2, 115.0 ];   /* a cells_ll row: lat, lng pairs, as loop() closes it */
out.from = [from({{ sheet: {{}} }}, {{ point: [1, 2] }}, false), from({{ }}, {{ point: [115.1, -8.1] }}, false), from({{ }}, {{ point: [9, 9], ngeo: {{ c8: {{ ring }} }} }}, true),
  from({{ }}, {{ point: [9, 9] }}, true), from({{ sheet: {{}} }}, {{ point: [9, 9], ngeo: {{ c8: {{ ring }} }} }}, true)];
/* a sheet is handed on: what the supply layer draws there, and its credit, on a community node and on a house */
out.sheet = {{}};
for (const [label, sheet, kind, k] of [['community', {{}}, 'community', 'both'], ['house', {{}}, 'home', 'both'], ['page', null, 'home', 'both'], ['communityTyped', {{}}, 'community', 'typed']]) {{
  const c = {{ PM: {{ on: {{ supply: true }}, supply: cases[k], sheet, map: null, meta: null }}, D: {{ health: {{ kind }}, point: [115.15, -8.82] }}, d3, SAT_MAX: 15,
    DOORS_TOKEN: () => 't', notHouse: x => x === 'community' }};
  vm.createContext(c);
  vm.runInContext(pm.match(/const LAYERS = \\[[\\s\\S]*?\\n\\];/)[0] + '\\n' + lift(pm, 'supplyRows') + lift(pm, 'supplyMarks') + lift(pm, 'supplyDrawn') + lift(pm, 'creditList')
    + 'supplyRows(); this.m = supplyDrawn(PM.supply, PM.sheet, [115, -8.9]); this.credits = creditList();', c);
  out.sheet[label] = {{ m: c.m, credits: c.credits }};
}}
/* placeSupply: where "on the map ↑" takes the map */
out.fly = {{}};
for (const k of ['both', 'ungasan', 'mapped', 'typed', 'none']) {{
  const c = {{ PM: {{ supply: cases[k], map: {{ fitBounds: b => {{ c.got = b; }} }} }}, D: {{ point: [115.15, -8.82] }}, d3, DOORS_TOKEN: () => '',
    setLayer: () => {{}}, fly: z => {{ c.got = 'fly ' + z; }}, CLOCK: {{ reduced: () => true }}, window: {{}} }};
  vm.createContext(c);
  vm.runInContext(pm.match(/^const loop = .*$/m)[0] + '\\n' + lift(pm, 'supplyMarks') + lift(pm, 'supplyFrom') + pm.match(/^window\\.placeSupply = \\(\\) => {{[\\s\\S]*?\\n}};/m)[0] + '\\nwindow.placeSupply();', c);
  out.fly[k] = c.got;
}}
out.data = [/supply_origin_km: 'km'/.test(dd), /supply_sources: 'sources of water stated'/.test(dd), /supply_first_holds: 'how the first source holds \\(0 steady, 2 fails often\\)'/.test(dd),
  /supply_origin_km: 'the first source’s works, from the middle of the cell'/.test(dd)];
out.notyet = pl.includes('Production and trade · Soil · Forecast') && !pl.includes('Water and soil');
console.log(JSON.stringify(out));
"""
    _p = subprocess.run(["node"], input=prog, capture_output=True, text=True)
    if _p.returncode:
        print(_p.stderr[-1500:]); sys.exit(1)
    r = json.loads(_p.stdout)

import re

strip = lambda h: re.sub(r"<[^>]+>", "", h)
page, rep = r["rows"]["both"][:2]
check('data-k="supply"' in page and "PDAM Tirta Mangutama, piped, fails often, from 12 km away, in another basin" in page and "Water trucks, truck" in page
      and page.index("PDAM") < page.index("Water trucks"), f"both sources, in order: {page}")
check('id="psupplygo"' in page and "psupplygo" not in rep, "the map link only on the page, never on the report")
none = r["rows"]["none"][0]
check("not stated" in none and "SUPPLY_SOURCES" in none and not re.search(r"\b0\b", strip(none)) and "psupplygo" not in none, f"not stated: {none}")
check("3 water works drawn within 25 km" in r["rows"]["mapped"][0] and "not stated" in r["rows"]["mapped"][0], "mapped only")
check("Bad line: not read (no kind)" in r["rows"]["bad"][0], "an entry that did not parse is said")
check(r["rows"]["empty"] == ["", "", "", ""], "an answer with no state draws no row")
check("psupplygo" not in r["rows"]["wifi"][0] and "psupplygo" not in r["rows"]["typed"][0], "no link where nothing is drawn")
check(not any(c in page for c in ("—", "undefined", "null")), f"no dash or stray word: {page}")
trucks = re.sub(r"\s+", " ", strip(page))
check("from 12 km away" in trucks and "outside the basins" not in trucks, "only the first source is said in full")
check("Well, well, steady, within a kilometre, in the same basin" in r["rows"]["near"][0], r["rows"]["near"][0])
L = {k: v["tok"] for k, v in r["layer"].items()}
row = L["both"]["row"]
check(row["on"] is False and row["cake"] == "built" and row["pack"] == "supply" and not row["empty"], f"the layer is there, off, in the built row: {row}")
check("water supply: © OpenStreetMap contributors, ODbL, via Overpass" in L["both"]["credits"], "drawn and credited")
check(not any("water supply" in c for c in L["none"]["credits"]) and L["none"]["row"]["empty"], "nothing drawn, no credit")
check(L["wifi"]["row"]["locked"] and L["wifi"]["row"]["empty"], "works with no points: token-only")
check(L["typed"]["row"]["empty"] and not L["typed"]["row"].get("locked") and L["typed"]["row"]["why"] == "set SUPPLY_SOURCES on Set up", "a typed origin with no point draws nothing")
M = r["marks"]
check(len(M["both"]["works"]) == 3 and [o["name"] for o in M["both"]["origins"]] == ["Water trucks (stated)"] and M["both"]["line"] == [[115, -8.9], [115.3, -8.7]], f"marks: {M['both']}")
check(M["typed"]["origins"] == [] and M["typed"]["line"] is None and M["wifi"]["works"] == [], "a point not given is not drawn")
check(all(r["data"]) and r["notyet"], f"the Data words and the not-yet row: {r['data']} {r['notyet']}")

# a typed origin comes with no name: its ring is labelled with the source's, and "null" is printed nowhere
for k in ("both", "typed", "near"):
    check("null" not in json.dumps(M[k]["origins"]) and "null" not in r["rows"][k][0] and "null" not in r["layer"][k]["tok"]["ring"], f"no null for a typed origin: {k}")
check("Water trucks (stated)" in r["layer"]["both"]["tok"]["ring"], f"the inspector names the ring by its source: {r['layer']['both']['tok']['ring']}")
# the pack is off: the keeper is told how to turn it on, anyone else and the report only that it is not yet there
off = r["layer"]["off"]
check(off["tok"]["row"]["why"] == "add supply to PACKS_ENABLED" and off["bare"]["row"]["why"] == "not yet", f"pack off, by reader: {off}")
check(off["tok"]["fill"] == off["bare"]["fill"] == "not yet" and "planetai run" not in json.dumps(off), f"pack off, the report: {off}")
# the inspector's km: from this node for the keeper, from the middle of the cell for anyone else
wl = r["layer"]["both"]
check("from this node" in wl["tok"]["water"] and "middle of the cell" not in wl["tok"]["water"], f"keeper's km label: {wl['tok']['water']}")
check("from the middle of the cell" in wl["bare"]["water"] and "from this node" not in wl["bare"]["water"], f"reader's km label: {wl['bare']['water']}")
# on the map: to the first source's origin when it has a point, else the first work with one, else the cell
fl = r["fly"]
check(fl["ungasan"] == [[115.15, -8.82], [115.21, -8.81]], f"to the first origin, mapped at the second-nearest work: {fl['ungasan']}")
check(fl["both"] == [[115.15, -8.82], [115.3, -8.7]], f"to the first source's mapped origin, not a later stated ring: {fl['both']}")
check(fl["mapped"] == [[115.15, -8.82], [115.2, -8.8]] and fl["typed"] == "fly 8" and fl["none"] == "fly 8", f"else the first work, else the cell: {fl}")
# the printed report asks for the stranger's answer; the page's own row asks plainly
pls = (ROOT / "app/static/doors-place.js").read_text()
rep_fn = re.search(r"^function report\(again\) \{[\s\S]*?\n\}\n", pls, re.M).group(0)
sup_fn = re.search(r"^async function supply\(\) \{[\s\S]*?\n\}\n", pls, re.M).group(0)
check("get('/supply?reader=1')" in rep_fn and "'/supply'" not in rep_fn, "the report fetches /supply?reader=1")
check("doorsFetch('/supply')" in sup_fn, "the page's row fetches /supply")

# a printed sheet draws what a reader with no token is given, whoever prints
sh = r["sheet"]
typed_pt = lambda m: any((x["lat"], x["lon"]) == (-8.6, 115.1) for x in m["works"] + m["origins"])
cm = sh["community"]["m"]
check(len(cm["works"]) == 4 and any((x["lat"], x["lon"]) == (-8.7, 115.3) for x in cm["works"]) and cm["origins"] == [] and cm["line"] is None and not typed_pt(cm),
      f"a sheet on a community node: the works and the mapped origin as marks, no ring, no line, no typed point: {cm}")
check("water supply: © OpenStreetMap contributors, ODbL, via Overpass" in sh["community"]["credits"], "a community sheet with works credits the map")
hm = sh["house"]["m"]
check(hm["works"] == [] and hm["origins"] == [] and hm["line"] is None and not any("water supply" in c for c in sh["house"]["credits"]),
      f"a sheet on a house: no supply marks and no credit: {sh['house']}")
pg = sh["page"]["m"]
check([o["name"] for o in pg["origins"]] == ["Water trucks (stated)"] and len(pg["works"]) == 3 and pg["line"] == [[115, -8.9], [115.3, -8.7]],
      f"off a sheet with a token, unchanged: {pg}")
check(not any("water supply" in c for c in sh["communityTyped"]["credits"]), "a sheet with nothing drawn does not credit the map")

# a report is handed on: whole km and no keeper's entries; the page keeps 12.3 and the entry
pg, rp = r["rows"]["report"][:2]
check("from 12.3 km away" in pg and "Bad line: not read (no kind)" in pg, f"the page: {pg}")
check("from 12 km away" in rp and "12.3" not in rp and "Bad line" not in rp and "not read" not in rp, f"the report: {rp}")
check("outside the basins this node holds" in pg and "outside the basins this node holds" in rp, "the beyond basin words")
# the setting's name is the keeper's: with a token on the page, never for a reader with none, never on the report
for k in ("none", "mapped"):
    tp, trep, bp, brep = r["rows"][k]
    check("SUPPLY_SOURCES" in tp and "not stated" in tp, f"keeper's page says the setting: {tp}")
    check("SUPPLY_SOURCES" not in bp and "not stated" in bp and "SUPPLY_SOURCES" not in trep and "SUPPLY_SOURCES" not in brep and "not stated" in trep, f"no token or report: {bp} {trep}")
check("<small></small>" in r["rows"]["none"][2], "no token: no small words at all when nothing is mapped")
check("3 water works drawn within 25 km" in r["rows"]["mapped"][2], "no token: the works count stays")
lay = r["layer"]["none"]
check(lay["tok"]["row"]["why"] == "set SUPPLY_SOURCES on Set up" and lay["bare"]["row"]["why"] == "not stated", f"the layer's why by reader: {lay}")
check(all(lay[t]["fill"] == "not stated" for t in lay), f"the report's table never prints the setting: {lay}")
# nulls
nl = r["rows"]["nulls"][0]
check("null" not in nl and "undefined" not in nl and "well" in nl and ", well" not in nl, f"a null name prints nothing: {nl}")
nn = r["rows"]["nullsnone"][0]
check("3 water works drawn" in strip(nn) and "within" not in strip(nn) and "null" not in nn, f"a null radius says no radius: {nn}")
# hostile strings stay escaped, in the row and in the inspector
raw = "<img"
for k in ("evil",):
    for h in r["rows"][k][:3] + [r["water"]]:
        check(raw not in h, f"a raw <img got into: {h}")
ev = r["rows"]["evil"][0]
check("&lt;img src=x onerror=1&gt;&quot;&amp;" in ev and "not read (&lt;img" in ev, f"escaped forms in the row: {ev}")
check("&lt;img src=x onerror=1&gt;&quot;&amp;" in r["water"], f"escaped forms in the inspector: {r['water']}")
# where the line starts
f = r["from"]
check(f[0] is None and f[1] == [115.1, -8.1] and f[3] is None and f[4] is None, f"supplyFrom: sheet, no token, no ring: {f}")
check(f[2] is not None and abs(f[2][0] - 115.1) < 1e-9 and abs(f[2][1] + 8.1) < 1e-9, f"with a token the mean of the cell ring, not the node's point: {f[2]}")

if fails:
    print("\n".join(f"  ✗ {f}" for f in fails))
else:
    print("  ✓ doors-supply: the figures' row, the report's row, the map layer, its credit, and the Data words")
sys.exit(1 if fails else 0)
