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

# ---------------------------------------------------------------- schema (init.sql)
import os  # noqa: E402
import sources  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sql = open(os.path.join(ROOT, "init.sql")).read()
check("CREATE TABLE IF NOT EXISTS node_cells (" in sql, "init.sql defines node_cells")
check("INSERT INTO schema_version (version) VALUES ('0.65') ON CONFLICT DO NOTHING;" in sql,
      "init.sql records schema_version 0.65 for node_cells")

# ---------------------------------------------------------------- stamp_local (table cases)
own_set = cells.own(HOME, {n1})
s_home = {"sensor_id": "s-home", "local": True, "lat": pt_home[0], "lon": pt_home[1]}
s_claimed = {"sensor_id": "s-n1", "local": True, "lat": pt_n1[0], "lon": pt_n1[1]}
s_open = {"sensor_id": "s-n2", "local": True, "lat": pt_n2[0], "lon": pt_n2[1]}
s_far = {"sensor_id": "s-far", "local": True, "lat": pt_far[0], "lon": pt_far[1]}
s_theirs = {"sensor_id": "s-theirs", "local": False, "lat": pt_home[0], "lon": pt_home[1]}
s_nopt = {"sensor_id": "s-nopt", "local": True, "lat": None, "lon": None}
out_s = sources.stamp_local([s_home, s_claimed, s_open, s_far, s_theirs, s_nopt], own_set)
check(out_s is not None and len(out_s) == 6, "stamp_local returns the sensor list")
check(s_home["local"] is True, "sensor in home cell stays local")
check(s_claimed["local"] is True, "sensor in claimed neighbour cell stays local")
check(s_open["local"] is False, "sensor in open neighbour cell is narrowed to False")
check(s_far["local"] is False, "sensor outside the ring is narrowed to False")
check(s_theirs["local"] is False, "unclaimed sensor in home cell never becomes local")
check(s_nopt["local"] is True, "sensor with no coordinates keeps its claim")

# Node without coordinates (own_cells is None) leaves every claim alone
s_unset_open = {"sensor_id": "s-u1", "local": True, "lat": pt_n2[0], "lon": pt_n2[1]}
s_unset_theirs = {"sensor_id": "s-u2", "local": False, "lat": pt_home[0], "lon": pt_home[1]}
sources.stamp_local([s_unset_open, s_unset_theirs], None)
check(s_unset_open["local"] is True and s_unset_theirs["local"] is False,
      "stamp_local(..., None) leaves every claim alone when node has no coordinates")

# ---------------------------------------------------------------- adopt and load (fake cursor)
class FakeCur:
    def __init__(self, sensors_rows=None, cells_rows=None):
        self.sensors = list(sensors_rows or [])
        self.cells = dict(cells_rows or {})   # cell -> claimed_by
        self._last = []

    def execute(self, q, params=()):
        u = " ".join(q.split())
        if "SELECT" in u and "FROM node_cells" in u:
            if "WHERE" in u and params:
                c = params[0]
                self._last = [{"cell": c, "claimed_by": self.cells[c]}] if c in self.cells else []
            else:
                self._last = [{"cell": c, "claimed_by": by} for c, by in self.cells.items()]
        elif "SELECT" in u and "FROM sensors" in u:
            self._last = [r for r in self.sensors
                          if r.get("local") and r.get("kind", "sensor") == "sensor"
                          and r.get("lat") is not None and r.get("lon") is not None]
        elif "INSERT INTO node_cells" in u:
            if len(params) == 2:
                cell_id, by = params[0], params[1]
            else:
                cell_id = params[0]
                by = "home" if "'home'" in u else "adopted"
            if "DO UPDATE" in u or cell_id not in self.cells:
                self.cells[cell_id] = by
            self._last = []

    def fetchall(self):
        return list(self._last)

    def fetchone(self):
        return self._last[0] if self._last else None


# Node #1's actual coordinates in HOME (8895a4c843fffff); sc-19236 sits 250 m away across the border in n1 (8895a4c809fffff)
NODE1_LAT, NODE1_LON = -8.8190516, 115.1644423
os.environ["NODE_LAT"] = str(NODE1_LAT)
os.environ["NODE_LON"] = str(NODE1_LON)
sc_cell = cells.cell_of(-8.81983, 115.16657)
check(sc_cell == n1, f"sc-19236 sits in neighbour {n1}, got {sc_cell}")
# A point in n3 (8895a4c847fffff) ~300 m from NODE1: step 45% from NODE1 toward n3's centre
n3_lat, n3_lon = h3.cell_to_latlng(n3)
near_n3 = (NODE1_LAT + 0.45 * (n3_lat - NODE1_LAT), NODE1_LON + 0.45 * (n3_lon - NODE1_LON))
check(cells.cell_of(*near_n3) == n3 and sources.metres(NODE1_LAT, NODE1_LON, *near_n3) < 500,
      "near_n3 is in n3 and within 500 m of node #1")

fleet = [
    {"sensor_id": "sc-home", "lat": NODE1_LAT, "lon": NODE1_LON, "local": True, "kind": "sensor"},
    {"sensor_id": "sc-19236", "lat": -8.81983, "lon": 115.16657, "local": True, "kind": "sensor"},      # 250 m, in n1
    {"sensor_id": "sc-19874", "lat": -8.82008, "lon": 115.16669, "local": True, "kind": "sensor"},      # 273 m, in n1
    {"sensor_id": "sc-19880", "lat": -8.8271, "lon": 115.15709, "local": True, "kind": "sensor"},       # 1207 m, outside ring
    {"sensor_id": "sc-n2-far", "lat": pt_n2[0], "lon": pt_n2[1], "local": True, "kind": "sensor"},      # in n2, > 500 m (1072 m)
    {"sensor_id": "bad-n3", "lat": near_n3[0], "lon": near_n3[1], "local": False, "kind": "sensor"},    # in n3 < 500 m, not local
    {"sensor_id": "peer-n3", "lat": near_n3[0], "lon": near_n3[1], "local": True, "kind": "peer"},      # in n3 < 500 m, peer
    {"sensor_id": "msh-none", "lat": None, "lon": None, "local": True, "kind": "sensor"},               # no point
]

cur = FakeCur(fleet)
claimed = cells.adopt(cur, HOME)
check(claimed == {n1}, f"adopt() returns what it claimed ({{n1}}), got {claimed}")
check(cur.cells == {HOME: "home", n1: "adopted"}, f"adopt() writes (home,'home') and (n1,'adopted'), got {cur.cells}")

# Runs once per home cell: even if a local sensor within 500 m appears in n3 later, adopt() is a no-op
cur.sensors.append({"sensor_id": "sc-n3-late", "lat": near_n3[0], "lon": near_n3[1], "local": True, "kind": "sensor"})
claimed_again = cells.adopt(cur, HOME)
check(claimed_again == set(), f"adopt() runs once per home cell, second call returned {claimed_again}")
check(n3 not in cur.cells, "second adopt() did not claim n3")

# load() adopts on first run when there is no 'home' row for home_cell, then returns own(home_cell, claims)
cur2 = FakeCur(fleet)
loaded = cells.load(cur2, HOME)
check(loaded == {HOME, n1}, f"load() adopts on first call and returns {{HOME, n1}}, got {loaded}")
check(cur2.cells == {HOME: "home", n1: "adopted"}, "load() persisted home and adopted rows")

# Releasing the adopted cell later does not re-adopt, because the (HOME, 'home') row marks adoption as done
del cur2.cells[n1]
check(cells.load(cur2, HOME) == {HOME}, "releasing adopted cell does not trigger re-adoption while 'home' row exists")

# Keeper claims a neighbour; an old claim outside the ring is ignored
cur2.cells[n2] = "keeper"
cur2.cells[far] = "keeper"
check(cells.load(cur2, HOME) == {HOME, n2}, "load() returns home + claimed neighbours, ignoring claims outside the ring")

# Node moves to a new home cell (`moved`, 4 steps away): no 'home' row for `moved` yet, so it adopts again for `moved`
moved = next(c for c in h3.grid_disk(HOME, 4) if c not in h3.grid_disk(HOME, 3))
check(cells.load(cur2, moved) == {moved}, "moving to a new home cell adopts for the new home and ignores non-neighbours")
check(cur2.cells.get(moved) == "home", "new home cell gets its own 'home' row")

# ---------------------------------------------------------------- callers in app/main.py
main_src = open(os.path.join(ROOT, "app/main.py")).read()
poll_block = main_src[main_src.index("def poll_once"):main_src.index("def _store")]
store_block = main_src[main_src.index("def _store"):main_src.index("def mqtt_thread")]
check("cells.load(cur, cells.home(" in poll_block and poll_block.index("cells.load(") < poll_block.index("for name, fn in sources.enabled(hc):"),
      "poll_once loads own_cells once per poll before looping over sources")
check("cells.load(cur, cells.home(" in store_block and store_block.index("cells.load(") < store_block.index("for s in sensors:"),
      "_store loads own_cells once before looping over sensors")

if fails:
    print("\n".join(f"  ✗ {f}" for f in fails))
print("  ✓ cells: ring of seven, 3 outside parent, own, states, held_count, adoptable, stamp_local, adopt, load" if not fails else f"  ✗ {len(fails)} failure(s)")
sys.exit(1 if fails else 0)
