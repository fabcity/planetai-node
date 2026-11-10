"""The node's seven res-8 cells: home, the six touching it, their states, and which neighbours a fleet adopts.

Run: PYTHONPATH=app python3 tests/test_cells.py
"""
import sys

import h3

import cells
from issues import geometry as geo

fails = []


def check(ok, msg):
    if not ok:
        fails.append(msg)


HOME = "8895a4c843fffff"
PARENT = "8795a4c84ffffff"
LAT, LON = h3.cell_to_latlng(HOME)

check(cells.RES == 8, f"RES is 8, got {cells.RES}")
check(cells.STATES == ("home", "held", "claimed", "open"), f"STATES: {cells.STATES}")
check(cells.home(LAT, LON) == HOME, f"node #1's res-8 cell is {HOME}, got {cells.home(LAT, LON)}")

# ---------------------------------------------------------------- the ring of seven
r = cells.ring(HOME)
check(len(r) == 7 and len(set(r)) == 7, f"a ring has 7 distinct cells, got {len(r)}")
check(r[0] == HOME, f"home is first in ring(), got {r[0]}")
check(r[1:] == sorted(r[1:]), "the six neighbours are sorted after home")
check(set(r) == set(h3.grid_disk(HOME, 1)), "ring() is grid_disk(home, 1)")
outside_parent = [c for c in r[1:] if h3.cell_to_parent(c, 7) != PARENT]
check(h3.cell_to_parent(HOME, 7) == PARENT, f"home's res-7 parent is {PARENT}")
check(len(outside_parent) == 3, f"3 of node #1's 6 neighbours sit outside parent {PARENT}, got {len(outside_parent)}")

# ---------------------------------------------------------------- own and cell_of
n1, n2, n3 = r[1], r[2], r[3]
far = next(c for c in h3.grid_disk(HOME, 2) if c not in r)
check(cells.own(HOME, set()) == {HOME}, "with no claims, own() is {home}")
check(cells.own(HOME, {n1, n2, far}) == {HOME, n1, n2}, "own() keeps claimed neighbours and ignores claims outside the ring")

check(cells.cell_of(LAT, LON) == HOME, "cell_of(lat, lon) returns the res-8 cell")
check(cells.cell_of(None, LON) is None and cells.cell_of(LAT, None) is None and cells.cell_of(None, None) is None,
      "cell_of returns None when a coordinate is missing")

# ---------------------------------------------------------------- states and held_count
rows = cells.states(HOME, {n1, n2, far}, {n1, n3, far})
by_cell = {row["cell"]: row for row in rows}
check([row["cell"] for row in rows] == r, "states() returns one row per ring cell in ring() order")
check(by_cell[HOME]["state"] == "home", f"home cell state is 'home', got {by_cell[HOME]['state']}")
check(by_cell[n1]["state"] == "held", f"claimed + seen is 'held', got {by_cell[n1]['state']}")
check(by_cell[n2]["state"] == "claimed", f"claimed without a 24 h reading is 'claimed', got {by_cell[n2]['state']}")
check(by_cell[n3]["state"] == "open", f"unclaimed neighbour is 'open' even if in seen, got {by_cell[n3]['state']}")
check({row["state"] for row in rows} == set(cells.STATES), "all four states reached")
check(all(row["ring"] == geo._row(row["cell"]) for row in rows), "every row carries geo._row(cell) as 'ring'")

check(cells.held_count(rows) == 2, f"home + 1 held neighbour = 2 of 7, got {cells.held_count(rows)}")
check(cells.held_count(cells.states(HOME, set(), set())) == 1, "home alone counts as 1 held")
check(cells.held_count(cells.states(HOME, set(r[1:]), set(r[1:]))) == 7, "all 6 neighbours claimed and seen = 7 of 7")

# ---------------------------------------------------------------- adoptable
pt_home = h3.cell_to_latlng(HOME)
pt_n1 = h3.cell_to_latlng(n1)
pt_n2 = h3.cell_to_latlng(n2)
pt_far = h3.cell_to_latlng(far)
got_adopt = cells.adoptable(HOME, [(LAT, LON), pt_home, pt_n1, pt_n2, pt_far])
check(got_adopt == {n1, n2}, f"adoptable returns neighbour cells containing points, got {got_adopt}")
check(HOME not in cells.adoptable(HOME, [(LAT, LON), pt_home]), "adoptable never returns home")

if fails:
    print("\n".join(f"  ✗ {f}" for f in fails))
print("  ✓ cells: ring of seven, 3 outside parent, own, states, held_count, adoptable" if not fails else f"  ✗ {len(fails)} failure(s)")
sys.exit(1 if fails else 0)
