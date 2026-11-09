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

if fails:
    print("\n".join(f"  ✗ {f}" for f in fails))
    sys.exit(1)
print("  ✓ energy: grids and OSM sources")
sys.exit(0)
