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
        "origin": {"how": "stated", "name": "Quarry spring", "km": 0, "basin": "beyond", "lat": -8.6, "lon": 115.1}}]
CASES = {
    "both": {"state": "both", "sources": SRC, "works": WORKS, "counts": {"works": 3}, "radius_km": 25, "attribution": [], "hint": None},
    "none": {"state": "none", "sources": [], "works": [], "counts": {}, "radius_km": 25, "hint": "not stated: set SUPPLY_SOURCES on Set up"},
    "mapped": {"state": "mapped", "sources": [], "works": WORKS, "counts": {"works": 3}, "radius_km": 25},
    "bad": {"state": "none", "sources": [{"entry": "Bad line", "problem": "no kind"}], "works": [], "counts": {}, "radius_km": 25},
    "typed": {"state": "stated", "sources": [{"id": "b", "name": "T", "kind": "truck", "holds": None, "origin": {"how": "stated", "name": "X", "km": 4, "basin": None}}],
              "works": [], "counts": {}, "radius_km": 25},
    "wifi": {"state": "mapped", "sources": [], "works": [{k: v for k, v in w.items() if k not in ("lat", "lon")} for w in WORKS], "counts": {"works": 3}, "radius_km": 25},
    "near": {"state": "stated", "sources": [{"id": "a", "name": "Well", "kind": "well", "holds": "steady", "origin": {"how": "stated", "name": "W", "km": 0, "basin": "same"}}], "works": [], "counts": {}, "radius_km": 25},
    "empty": {},
}
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp) / "c.json"
    p.write_text(json.dumps(CASES))
    prog = f"""
const fs = require('fs'), vm = require('vm');
const pm = fs.readFileSync('./app/static/doors-placemap.js', 'utf8'), pl = fs.readFileSync('./app/static/doors-place.js', 'utf8'), dd = fs.readFileSync('./app/static/doors-data.js', 'utf8');
const lift = (src, n) => src.match(new RegExp('^function ' + n + '\\\\([\\\\s\\\\S]*?\\\\n}}\\\\n', 'm'))[0];
const cases = JSON.parse(fs.readFileSync({json.dumps(str(p))}, 'utf8')), out = {{ rows: {{}}, layer: {{}}, marks: {{}} }};
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({{ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }}[c]));
const pc = {{ esc }}; vm.createContext(pc);
vm.runInContext('const BASIN = ' + pl.match(/^const BASIN = .*$/m)[0].replace(/^const BASIN = /, '') + '\\n' + lift(pl, 'supplyRow') + 'this.supplyRow = supplyRow;', pc);
for (const [k, S] of Object.entries(cases)) out.rows[k] = [pc.supplyRow(S, true), pc.supplyRow(S)];
for (const [k, S] of Object.entries(cases)) {{
  const c = {{ PM: {{ on: {{ supply: true }}, supply: S, map: null, meta: null }}, SAT_MAX: 15 }}; vm.createContext(c);
  vm.runInContext(pm.match(/const LAYERS = \\[[\\s\\S]*?\\n\\];/)[0] + '\\n' + lift(pm, 'supplyRows') + lift(pm, 'supplyMarks') + lift(pm, 'creditList')
    + 'supplyRows(); this.row = LAYERS.find(l => l.id === "supply"); this.credits = creditList(); this.m = supplyMarks(PM.supply, [115, -8.9]);', c);
  out.layer[k] = {{ row: c.row, credits: c.credits }}; out.marks[k] = c.m;
}}
out.data = [/supply_origin_km: 'km'/.test(dd), /supply_sources: 'sources of water stated'/.test(dd), /supply_first_holds: 'how the first source holds \\(0 steady, 2 fails often\\)'/.test(dd)];
out.notyet = pl.includes('Production and trade · Soil · Forecast') && !pl.includes('Water and soil');
console.log(JSON.stringify(out));
"""
    r = json.loads(subprocess.run(["node"], input=prog, capture_output=True, text=True, check=True).stdout)

import re

strip = lambda h: re.sub(r"<[^>]+>", "", h)
page, rep = r["rows"]["both"]
check('data-k="supply"' in page and "PDAM Tirta Mangutama, piped, fails often, from 12 km away, in another basin" in page and "Water trucks, truck" in page
      and page.index("PDAM") < page.index("Water trucks"), f"both sources, in order: {page}")
check('id="psupplygo"' in page and "psupplygo" not in rep, "the map link only on the page, never on the report")
none = r["rows"]["none"][0]
check("not stated" in none and "SUPPLY_SOURCES" in none and not re.search(r"\b0\b", strip(none)) and "psupplygo" not in none, f"not stated: {none}")
check("3 water works drawn within 25 km" in r["rows"]["mapped"][0] and "not stated" in r["rows"]["mapped"][0], "mapped only")
check("Bad line: not read (no kind)" in r["rows"]["bad"][0], "an entry that did not parse is said")
check(r["rows"]["empty"] == ["", ""], "an answer with no state draws no row")
check("psupplygo" not in r["rows"]["wifi"][0] and "psupplygo" not in r["rows"]["typed"][0], "no link where nothing is drawn")
check(not any(c in page for c in ("—", "undefined", "null")), f"no dash or stray word: {page}")
trucks = re.sub(r"\s+", " ", strip(page))
check("from 12 km away" in trucks and "outside the basins" not in trucks, "only the first source is said in full")
check("Well, well, steady, within a kilometre, in the same basin" in r["rows"]["near"][0], r["rows"]["near"][0])
L = r["layer"]
row = L["both"]["row"]
check(row["on"] is False and row["cake"] == "built" and row["pack"] == "supply" and not row["empty"], f"the layer is there, off, in the built row: {row}")
check("water supply: © OpenStreetMap contributors, ODbL, via Overpass" in L["both"]["credits"], "drawn and credited")
check(not any("water supply" in c for c in L["none"]["credits"]) and L["none"]["row"]["empty"], "nothing drawn, no credit")
check(L["wifi"]["row"]["locked"] and L["wifi"]["row"]["empty"], "works with no points: token-only")
check(L["typed"]["row"]["empty"] and not L["typed"]["row"].get("locked") and L["typed"]["row"]["why"] == "set SUPPLY_SOURCES on Set up", "a typed origin with no point draws nothing")
M = r["marks"]
check(len(M["both"]["works"]) == 3 and [o["name"] for o in M["both"]["origins"]] == ["Quarry spring (stated)"] and M["both"]["line"] == [[115, -8.9], [115.3, -8.7]], f"marks: {M['both']}")
check(M["typed"]["origins"] == [] and M["typed"]["line"] is None and M["wifi"]["works"] == [], "a point not given is not drawn")
check(all(r["data"]) and r["notyet"], f"the Data words and the not-yet row: {r['data']} {r['notyet']}")

if fails:
    print("\n".join(f"  ✗ {f}" for f in fails))
else:
    print("  ✓ doors-supply: the figures' row, the report's row, the map layer, its credit, and the Data words")
sys.exit(1 if fails else 0)
