"""The H3 geometry the node publishes, checked against the numbers h3geo.org and the design repo already commit.

  · the ladder matches h3geo.org's resolution table: res 2 edge 182,513 m over 5,882 cells; res 8 area 737,328 m²
  · node #1's cells at 7, 8, 9 match planetai-design/assets/h3/kilometre-cells.json exactly
  · a plate is nineteen cells, its centre is the node's cell, and every cell's parent is in the plate above or flagged
  · the grain table: fourteen stations fall in 1 cell at res 4, 9 at res 8; three own sensors share one cell everywhere
  · publication: three decimals is about 110 m, and the resolution that holds it is 10

Run: PYTHONPATH=app python3 tests/test_issues_geometry.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "app"))

try:
    import h3  # noqa: F401
except ImportError:
    print("skipped: h3 is not installed (pip install -r app/requirements.txt)")
    sys.exit(0)

from issues import geometry as G  # noqa: E402

fails = []
snap = json.loads((ROOT / "app/issues/fixtures/node1-2026-09-06.json").read_text())
LAT, LON = snap["health"]["lat"], snap["health"]["lon"]
STATIONS = []
seen = set()
for r in snap["stats"]:
    if r["lat"] is None or r["sensor_id"] in seen:
        continue
    seen.add(r["sensor_id"])
    STATIONS.append({"sensor_id": r["sensor_id"], "lat": r["lat"], "lon": r["lon"], "local": bool(r["local"])})
STATIONS.sort(key=lambda s: (s["lat"], s["lon"]))

# --- the ladder against h3geo.org's table -----------------------------------------------------
L = G.ladder(LAT, LON)
if len(L) != 14 or L[2]["edge_m"] != 182513 or L[2]["cells"] != 5882:
    fails.append(f"res 2 should be 182,513 m over 5,882 cells, got {L[2]}")
if abs(L[8]["area_m2"] - 737328) > 1:
    fails.append(f"res 8 area should be 737,328 m², got {L[8]['area_m2']}")

# --- the design repo's committed cells ---------------------------------------------------------
# kilometre-cells.json's top-level keys are node/cells/res9_covering_kilometre/boundaries/counts, not
# res7/res8/res9 directly (task-1-brief.md's Step 1 draft assumed the latter). The node's res 7/8/9
# cell ids live one level down, under "cells" — that is what is checked here. The h3geo.org table
# assertions above are the ones that pin the arithmetic either way.
KC = ROOT.parent / "planetai-design/assets/h3/kilometre-cells.json"
if KC.exists():
    kc = json.loads(KC.read_text())
    want = {7: (kc.get("cells") or {}).get("res7"), 8: (kc.get("cells") or {}).get("res8"),
            9: (kc.get("cells") or {}).get("res9")}
    for res, cell in want.items():
        if cell and L[res]["id"] != cell:
            fails.append(f"res {res}: {L[res]['id']} != kilometre-cells.json {cell}")

# --- plates ---------------------------------------------------------------------------------------
P = G.plates(LAT, LON, STATIONS)
if sorted(P["plates"]) != list(range(2, 13)):
    fails.append(f"plates should cover 2..12, got {sorted(P['plates'])}")
for res, plate in P["plates"].items():
    if len(plate["cells"]) != 19:
        fails.append(f"plate {res} has {len(plate['cells'])} cells, not 19")
    if plate["centre"] != P["chain"][res]:
        fails.append(f"plate {res} centre is not the node's cell")
    for cid in plate["cells"]:
        c = P["cells"][cid]
        if res > 2 and not (c["parent"] or c["parent_outside"]):
            fails.append(f"{cid} at {res} has neither a parent in the plate above nor the flag")
        if len(c["neighbours"]) > c["neighbours_total"]:
            fails.append(f"{cid} lists more neighbours than it has")
own = [i for i, s in enumerate(STATIONS) if s["local"]]
if P["cells"][P["chain"][8]]["sensors"] != own:
    fails.append(f"the node's res-8 cell should hold exactly the own stations {own}, got {P['cells'][P['chain'][8]]['sensors']}")
if P["cell_count"] != 209:
    fails.append(f"11 plates × 19 cells is 209, got {P['cell_count']}")

# --- the grain table -----------------------------------------------------------------------------
T = {g["res"]: g for g in G.grain_table(LAT, LON, STATIONS, floor_res=6, publication_res=10)}
if T[4]["occupied"] != 1 or T[8]["occupied"] != 9:
    fails.append(f"occupied cells: res 4 {T[4]['occupied']} (want 1), res 8 {T[8]['occupied']} (want 9)")
if any(T[r]["mine_in_my_cell"] != 3 for r in range(2, 13)):
    fails.append("the three own stations carry one coordinate and must share one cell at every resolution")
if not T[6]["may_leave"] or T[7]["may_leave"]:
    fails.append("may_leave is true up to the floor (6) and false past it")
if T[10]["finer_than_published"] or not T[11]["finer_than_published"]:
    fails.append("finer_than_published starts past the publication resolution (10)")

# --- publication ---------------------------------------------------------------------------------
pub = G.publication()
if pub["decimals"] != 3 or pub["metres"] != 110 or pub["res"] != 10:
    fails.append(f"publication should be 3 dp ≈ 110 m → res 10, got {pub}")
if G.contains(110) != 10 or G.contains(10) != 12:
    fails.append(f"contains(110)={G.contains(110)} contains(10)={G.contains(10)}; want 10 and 12")

for f in fails:
    print("FAIL", f)
print("ok" if not fails else f"{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
