"""The energy pack's grid lookup, OSM parser, mix and daily series, offline: no network, no database.

Run: PYTHONPATH=/tmp/stub:app python3 tests/test_energy.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "packs/energy/tests/fixtures"
sys.path.insert(0, str(ROOT / "packs/energy"))

import grids as G  # noqa: E402
import mix as M  # noqa: E402
import osm as O  # noqa: E402

fails: list[str] = []


def check(ok, msg):
    if not ok:
        fails.append(msg)


# ---------------------------------------------------------------- grids and OSM
g = G.load()
# Node #1's point is the centre of its public H3 cell 8895a4c843fffff, never the house.
check(G.grid_for(-8.8161, 115.1635, g)["id"] == "bali", "node #1's cell is on the Bali grid")
check(G.grid_for(39.9493, 4.0500, g)["id"] == "balearic", "mahon1 is on the Balearic grid")
check(G.grid_for(41.39, 2.17, g) is None, "Barcelona is on no grid in grids.yml: no figure, no fallback")
check(G.ring_for(39.9493, 4.0500, G.grid_for(39.9493, 4.0500, g)) == "city", "mahon1 sits in Menorca's city ring")
check(G.ring_for(-8.1975, 114.8536, G.grid_for(-8.8161, 115.1635, g)) == "region",
      "Celukan Bawang sits in Bali's region ring")
check("out tags center;" in O.QUERY.format(s=-8.9, w=114.4, n=-8.0, e=115.7), "QUERY formats s, w, n, e")
check(O.mw("380 MW") == 380.0 and O.mw("100 kW") == 0.1 and O.mw("1,5 MW") == 1.5, "MW units")
check(O.mw("yes") is None and O.mw(None) is None, "no capacity is None, never 0")
bali = O.parse(json.load(open(FIX / "overpass-bali-2026-11-08.json")))
plants = [s for s in bali if s["kind"] == "plant"]
check(len(plants) == 19, f"19 plants in Bali on 8 Nov, got {len(plants)}")
check(any(s["kind"] == "cable_head" and "Gilimanuk" in s["name"] for s in bali), "the Java cable head is a cable_head")
n = O.near(bali, -8.816082625619444, 115.16354382246635)
check(n[0]["name"] == "GIS Pecatu" and abs(n[0]["km"] - 2.4) < 0.1, "nearest is GIS Pecatu, 2.4 km")
big = next(s for s in n if s["kind"] == "plant" and (s["mw"] or 0) >= 100)
check("Pesanggaran" in big["name"] and abs(big["km"] - 12.0) < 0.2, "nearest large plant is Pesanggaran, 12 km")
men = O.parse(json.load(open(FIX / "overpass-menorca-2026-11-08.json")))
check(any(s["fuel"] == "oil" and s["mw"] == 270.0 and s["fossil"] for s in men), "Maó's oil plant, 270 MW, fossil")
check(sum(1 for s in men if s["kind"] == "plant" and s["fuel"] == "solar" and s["mw"] is None and s["fossil"] is False) == 4,
      "Menorca's four solar plants with output=yes stay listed with mw=None")
unk = O.parse({"elements": [{"type": "node", "lat": 0.0, "lon": 0.0,
                             "tags": {"power": "plant", "plant:source": "nuclear"}}]})
gen = O.parse({"elements": [{"type": "node", "lat": 0.0, "lon": 0.0,
                             "tags": {"power": "generator", "generator:source": "wind",
                                      "generator:output:electricity": "2 MW"}}]})
check(gen[0]["kind"] == "generator", "a generator is listed apart, so a plant's MW is never counted twice")
check(unk[0]["fuel"] is None and unk[0]["fossil"] is None, "unlisted fuel has fossil=None")

# ---------------------------------------------------------------- Bali's range (mix.py)
g_syn = {
    "polygon": [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]],
    "rings": {"city": [[0, 0], [0, 5], [5, 5], [5, 0], [0, 0]]},
    "capacity_factors": {"coal": 0.6, "solar": 0.2},
    "links": [{"rated_mw": 100, "fossil_share": 0.8, "ring": "beyond"}],
    "demand_mw": 400,
}
src = [
    {"kind": "plant", "fuel": "coal", "fossil": True, "mw": 300, "lat": 2, "lon": 2},
    {"kind": "plant", "fuel": "solar", "fossil": False, "mw": 100, "lat": 7, "lon": 7},
    {"kind": "plant", "fuel": "coal", "fossil": True, "mw": None, "lat": 3, "lon": 3},
    {"kind": "generator", "fuel": "solar", "fossil": False, "mw": 500, "lat": 2, "lon": 2},
]
e = M.estimate(src, g_syn)
check(abs(e["island"] - 180 / 200) < 1e-9, "island share is 180 of 200 MW-weighted (generators and null MW excluded)")
check(abs(e["import_max"] - 0.25) < 1e-9, "100 MW cable against 400 MW demand")
check(abs(e["low"] - 0.875) < 1e-9 and abs(e["high"] - 0.9) < 1e-9, "range 87.5–90%")
check(abs(e["mid"] - 0.8875) < 1e-9 and e["method"] == "capacity-factors" and e["kind"] == "estimated",
      "mid, method and kind")
check(abs(sum(e["split"].values()) - 1) < 1e-9, "the ring split sums to one")
g2 = dict(g_syn, demand_mw=None)
e2 = M.estimate(src, g2)
check(e2["import_max"] is None and e2["mid"] is None and e2["split"]["beyond"] is None,
      "an unknown cable rating gives no import share and no midpoint, never a guess")
check(abs(e2["low"] - 0.8) < 1e-9 and abs(e2["high"] - 0.9) < 1e-9,
      "unknown rating: the range runs from the island (90%) to the cable's own share (80%)")
g3 = dict(g_syn, links=[{"rated_mw": 100, "fossil_share": None, "ring": "beyond"}])
check(M.estimate(src, g3)["low"] is None, "a link with no known mix gives no figure")
e_empty = M.estimate([], g_syn)
check(e_empty["low"] is None and e_empty["island"] is None, "no known plants gives None, never 0 or 1")
e_bali = M.estimate(bali, G.grid_for(-8.8161, 115.1635, g))
check(e_bali["low"] is not None and 0.80 < e_bali["low"] < e_bali["high"] <= 1,
      f"node #1 Bali range sanity, got {e_bali['low']}–{e_bali['high']}")

if fails:
    print("\n".join(f"  ✗ {f}" for f in fails))
    sys.exit(1)
print("  ✓ energy: grids, OSM sources, and Bali's range")
sys.exit(0)
