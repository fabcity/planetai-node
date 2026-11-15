"""The area pull's pure half (app/area.py): a selection covered at res 8 under AREA_CAP, its bbox, and the own and
peers blocks — own readings only inside the node's own cells, peers only where they have a point.

Run: PYTHONPATH=app python3 tests/test_area.py
"""
import sys
from datetime import datetime, timedelta, timezone

import h3

import area
import cells

fails = []


def check(ok, msg):
    if not ok:
        fails.append(msg)


def raises(fn, *a):
    try:
        fn(*a)
    except ValueError as e:
        return str(e)
    return None


HOME = "8895a4c843fffff"
RING = cells.ring(HOME)
N1, N2, N3 = RING[1], RING[2], RING[3]
FAR = next(c for c in h3.grid_disk(HOME, 3) if h3.grid_distance(c, HOME) == 3)

check(area.AREA_CAP == 500, f"AREA_CAP is 500, got {area.AREA_CAP}")

# ---------------------------------------------------------------- cover: cells
check(area.cover({"cells": [N2, HOME, N1, HOME]}) == sorted({HOME, N1, N2}), "res-8 ids come back deduplicated and sorted")
p7 = h3.cell_to_parent(HOME, 7)
check(area.cover({"cells": [p7]}) == sorted(h3.cell_to_children(p7, 8)), "a res-7 id is covered by its 7 res-8 children")
p5 = h3.cell_to_parent(HOME, 5)
check(len(area.cover({"cells": [p5]})) == h3.cell_to_children_size(p5, 8), "a res-5 id is covered at res 8 (343 cells, under the cap)")
kid = h3.cell_to_children(HOME, 10)[0]
check(area.cover({"cells": [kid, h3.cell_to_children(HOME, 9)[0]]}) == [HOME], "finer ids go up to their res-8 parent")
two5 = [p5, next(c for c in h3.grid_disk(p5, 1) if c != p5)]
_real = area.h3.cell_to_children
area.h3.cell_to_children = lambda *a: fails.append("cover() expanded cells past the cap before refusing") or []
check(str(area.AREA_CAP) in (raises(area.cover, {"cells": two5}) or ""), "two res-5 cells (686 res-8) are refused, naming the cap")
area.h3.cell_to_children = _real
check(raises(area.cover, {"cells": [h3.cell_to_parent(HOME, 4)]}) is not None, "res 4 is refused")
check(raises(area.cover, {"cells": [h3.cell_to_children(HOME, 11)[0]]}) is not None, "res 11 is refused")
check(raises(area.cover, {"cells": ["not-a-cell"]}) is not None, "a bad id is refused")
check(raises(area.cover, {"cells": []}) is not None, "an empty cell list is refused")
check(raises(area.cover, {"cells": "8895a4c843fffff"}) is not None, "cells as a string, not a list, is refused")

# ---------------------------------------------------------------- cover: selection shape
check(raises(area.cover, {}) is not None, "a selection with no key is refused")
check(raises(area.cover, {"cells": [HOME], "polygon": {}}) is not None, "a selection with two keys is refused")
check(raises(area.cover, {"mark_id": 3}) is not None, "mark_id reaching cover() unresolved is refused (the route resolves it)")


# ---------------------------------------------------------------- cover: polygon
def square(lat, lon, d):
    return [[lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d]]


LAT, LON = h3.cell_to_latlng(HOME)
poly = {"type": "Polygon", "coordinates": [square(LAT, LON, 0.02)]}
got = area.cover({"polygon": poly})
check(got == sorted(h3.geo_to_cells(poly, 8)) and HOME in got and len(got) > 7, f"a polygon is covered at res 8, got {len(got)}")
multi = {"type": "MultiPolygon", "coordinates": [[square(LAT, LON, 0.01)], [square(LAT + 0.1, LON, 0.01)]]}
gm = area.cover({"polygon": multi})
check(HOME in gm and set(h3.geo_to_cells({"type": "Polygon", "coordinates": [square(LAT + 0.1, LON, 0.01)]}, 8)) <= set(gm),
      "a MultiPolygon covers both parts")
# a garden-sized area off the cell's centre: h3 covers it with nothing, because no cell centre falls inside it
tiny = {"type": "Polygon", "coordinates": [square(LAT + 0.001, LON + 0.001, 0.0003)]}
check(h3.geo_to_cells(tiny, 8) == [], "fixture: the tiny area holds no cell centre")
check(area.cover({"polygon": tiny}) == [HOME], "an area smaller than a cell is covered by the cell it lies in, not by nothing")
huge = {"type": "Polygon", "coordinates": [square(LAT, LON, 0.5)]}
_real = area.h3.geo_to_cells
area.h3.geo_to_cells = lambda *a: fails.append("cover() computed a covering past the cap before refusing") or []
msg = raises(area.cover, {"polygon": huge})
area.h3.geo_to_cells = _real
check(msg is not None and str(area.AREA_CAP) in msg, "a polygon of ~12 000 km² is refused before covering, naming the cap")
for bad, why in [({"type": "Point", "coordinates": [LON, LAT]}, "a Point"),
                 ({"type": "Polygon", "coordinates": [[[LON, LAT], [LON + 0.01, LAT]]]}, "a ring of two points"),
                 ({"type": "Polygon", "coordinates": "x"}, "coordinates as a string"),
                 ({"type": "Polygon", "coordinates": [square(95, LON, 0.01)]}, "a latitude past 90"),
                 ({"type": "Polygon"}, "no coordinates"),
                 ("POLYGON((0 0))", "WKT instead of GeoJSON")]:
    check(raises(area.cover, {"polygon": bad}) is not None, f"{why} is refused")

# ---------------------------------------------------------------- bbox
w, s, e, n = area.bbox([HOME])
pts = h3.cell_to_boundary(HOME)
check((w, s, e, n) == (min(p[1] for p in pts), min(p[0] for p in pts), max(p[1] for p in pts), max(p[0] for p in pts)),
      "bbox is west, south, east, north of the cells' boundaries")
w2, s2, e2, n2 = area.bbox(RING)
check(w2 < w and s2 < s and e2 > e and n2 > n, "the ring's bbox contains the home cell's")
check(raises(area.bbox, []) is not None, "bbox of no cells is refused")

# ---------------------------------------------------------------- summarise
NOW = datetime.now(timezone.utc)


def ago(h):
    return NOW - timedelta(hours=h)


rows = [{"metric": "pm25", "ts": ago(30), "value": 99.0},     # older than 24 h: not in the mean, not the latest
        {"metric": "pm25", "ts": ago(2), "value": 10.0},
        {"metric": "pm25", "ts": ago(1), "value": 20.0},
        {"metric": "pm25", "ts": NOW + timedelta(hours=5), "value": 500.0},   # a forecast row: never a reading
        {"metric": "temp", "ts": ago(48), "value": 31.0}]
sm = area.summarise(rows)
check(set(sm) == {"pm25", "temp"}, f"one entry per metric, got {sorted(sm)}")
check(sm["pm25"]["latest"] == 20.0 and sm["pm25"]["latest_at"] == ago(1).isoformat(), f"latest is the newest past reading: {sm['pm25']}")
check(sm["pm25"]["mean_24h"] == 15.0 and sm["pm25"]["n"] == 2, f"mean_24h over the last 24 h only: {sm['pm25']}")
check(sm["temp"]["latest"] == 31.0 and sm["temp"]["mean_24h"] is None and sm["temp"]["n"] == 0,
      f"nothing in 24 h: the mean stays missing, never 0: {sm['temp']}")
check(area.summarise([]) == {}, "no rows, no metrics")
check("pm1" not in area.summarise([{"metric": "pm1", "ts": NOW + timedelta(hours=1), "value": 3.0}]),
      "a metric with only future rows is absent")
two = area.summarise([{"metric": "pm25", "ts": ago(1), "value": 10.0}, {"metric": "pm25", "ts": ago(1), "value": 30.0}])
check(two["pm25"]["latest"] == 20.0, f"two sensors at the same newest moment: their mean, not whichever came first: {two}")
st = area.summarise([{"metric": "pm25", "ts": ago(1).isoformat(), "value": 7.0}])
check(st["pm25"]["latest"] == 7.0 and st["pm25"]["mean_24h"] == 7.0, "a capture's string timestamp reads like a datetime")
nv = area.summarise([{"metric": "pm25", "ts": ago(1), "value": None}])
check(nv == {}, f"a row with no value is no reading: {nv}")


# ---------------------------------------------------------------- own
def pt(c):
    return h3.cell_to_latlng(c)


def sensor(sid, kind, custody, c=None):
    lat, lon = pt(c) if c else (None, None)
    return {"sensor_id": sid, "kind": kind, "custody": custody, "lat": lat, "lon": lon}


SENSORS = [sensor("home-1", "sensor", True, HOME),
           sensor("n1-1", "sensor", True, N1),          # in a held neighbour
           sensor("n3-1", "sensor", True, N3),          # in an open neighbour: never read as own
           sensor("far-1", "sensor", True, FAR),        # local yesterday, far away: not in the ring
           sensor("street-1", "portal", False, HOME),   # a public reference in home: not custody
           sensor("peer-home", "peer", False, HOME),
           sensor("peer-n3", "peer", False, N3),
           sensor("peer-radio", "peer", False),         # a radio peer with only a distance
           sensor("child-a", "child", True),
           sensor("child-b", "child", True),
           sensor("own-nopoint", "sensor", True)]       # an own sensor with no coordinates: never guessed into a cell
READ = [{"sensor_id": sid, "metric": "pm25", "ts": ago(1), "value": v}
        for sid, v in [("home-1", 10.0), ("n1-1", 20.0), ("n3-1", 1000.0), ("far-1", 1000.0), ("street-1", 1000.0),
                       ("peer-home", 40.0), ("peer-n3", 60.0), ("peer-radio", 1000.0), ("child-a", 1000.0),
                       ("own-nopoint", 1000.0)]]
OWN_CELLS = {HOME, N1, N2}

o = area.own(SENSORS, READ, set(RING), OWN_CELLS)
check(o["sensors"] == 2, f"own counts the custody sensors in selection ∩ own cells: home-1 and n1-1, got {o['sensors']}")
check(o["metrics"]["pm25"]["latest"] == 15.0 and o["metrics"]["pm25"]["n"] == 2,
      f"own never reads an open neighbour, a portal, a peer, a child or a sensor with no point: {o['metrics']}")
check(o["children_unplaced"] == 2, f"two children with no cell, got {o['children_unplaced']}")
check(o["cells"] == sorted(OWN_CELLS), f"own names the cells it read: selection ∩ own cells, got {o['cells']}")
o1 = area.own(SENSORS, READ, {N1, N3}, OWN_CELLS)
check(o1["sensors"] == 1 and o1["metrics"]["pm25"]["latest"] == 20.0 and o1["cells"] == [N1],
      f"a selection that only touches one own cell reads only that cell: {o1}")
o0 = area.own(SENSORS, READ, {N3, FAR}, OWN_CELLS)
check(o0["sensors"] == 0 and o0["metrics"] == {} and o0["cells"] == [] and o0.get("why"),
      f"a selection with no own cells gives an empty own block that says so: {o0}")
check("pm25" not in o0["metrics"], "and no number is made up for it")
oe = area.own(SENSORS, READ, {N2}, OWN_CELLS)
check(oe["sensors"] == 0 and oe["metrics"] == {} and oe["cells"] == [N2] and oe.get("why") and oe["why"] != o0["why"],
      f"an own cell with no sensor in it says that, differently: {oe}")
check(not o.get("why"), "a block with numbers carries no 'why'")

# ---------------------------------------------------------------- peers
p = area.peers(SENSORS, READ, set(RING))
check(p["sensors"] == 2 and p["metrics"]["pm25"]["latest"] == 50.0, f"peers in the selection: peer-home and peer-n3: {p}")
check(p["unplaced"] == 1, f"the radio peer with only a distance is unplaced, never guessed into a cell: {p['unplaced']}")
pn = area.peers(SENSORS, READ, {N3})
check(pn["sensors"] == 1 and pn["metrics"]["pm25"]["latest"] == 60.0, f"peers only where they have a point: {pn}")
p0 = area.peers(SENSORS, READ, {FAR})
check(p0["sensors"] == 0 and p0["metrics"] == {} and p0.get("why") and p0["unplaced"] == 1, f"no peers here, said so: {p0}")
check(not p.get("why"), "a peers block with numbers carries no 'why'")

if fails:
    print("\n".join(f"  ✗ {f}" for f in fails))
print("  ✓ area: cover by cells and polygon under AREA_CAP, bbox, summarise, own only in own cells, peers by point" if not fails else f"  ✗ {len(fails)} failure(s)")
sys.exit(1 if fails else 0)
