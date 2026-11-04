"""Place maps without a database: what a drawing must be before it is stored, and the palette the server holds.

A drawing arrives as a GeoJSON Feature from the page, an agent or curl, and app/maps.py refuses one that is not what
its kind says, in a sentence the page shows as it is. The route-level half, against Postgres, is
tests/test_maps_pg.py. Run: PYTHONPATH=app python3 tests/test_maps.py
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://unused/never-connected")   # db.py opens nothing at import
from maps import PALETTE, check_feature  # noqa: E402


def feature(kind, gtype, coords):
    return {"type": "Feature", "properties": {"kind": kind}, "geometry": {"type": gtype, "coordinates": coords}}


def area(ring):
    return feature("area", "Polygon", [ring])


def marker(lon, lat):
    return feature("marker", "Point", [lon, lat])


assert check_feature(feature("line", "LineString", [[115.1, -8.8]])) == "A line needs two points or more."
assert check_feature(feature("line", "LineString", [[115.1, -8.8], [115.1, -8.8]])) == "A line needs two points or more."
assert check_feature(feature("line", "LineString", [[115.1, -8.8], [115.2, -8.8]])) is None
assert check_feature(area([[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]])) == "That area crosses itself. Draw its corners in order around it."
assert check_feature(area([[0, 0], [1, 0], [0, 0]])) == "An area needs three corners or more."
assert check_feature(area([[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]])) is None
assert check_feature(area([[0, 0], [1, 0], [1, 1], [0, 1]])) is None, "an outline left open is closed, not refused"
assert check_feature(area([[0, 0], [1, 0], [1, 0], [1, 1], [0, 0]])) is None, "a corner tapped twice is one corner"
print("  lines and areas: point counts, and an area that crosses itself")

assert check_feature(marker(115.167, -8.819)) is None
assert check_feature(feature("note", "Point", [115.167, -8.819])) is None
assert check_feature(feature("marker", "LineString", [[0, 0], [1, 1]])) == "A marker is one point."
assert check_feature(feature("note", "Polygon", [[[0, 0], [1, 0], [1, 1], [0, 0]]])) == "A note is one point."
assert check_feature(feature("circle", "Point", [0, 0])) == "A drawing is a marker, a line, an area or a note."
for bad in (marker(200, 0), marker(0, -91), marker("115", -8.8), marker(float("nan"), 0), feature("marker", "Point", [1]),
            feature("line", "LineString", [[0, 0], [True, 1]])):
    assert check_feature(bad) == "Every point needs a longitude and a latitude.", bad
for bad in (None, [], {"type": "Feature"}, {"type": "Feature", "properties": {"kind": "line"}, "geometry": None}):
    assert isinstance(check_feature(bad), str), bad          # refused in words, never a 500
print("  markers and notes are one point; kinds, coordinates and shapes that are not GeoJSON are refused in words")

assert set(PALETTE) == {1, 2, 3, 4, 5, 6} and all(h.startswith("#") and 1 <= aci <= 255 for h, aci in PALETTE.values())
assert len({h.lower() for h, _ in PALETTE.values()}) == 6 and len({a for _, a in PALETTE.values()}) == 6
print("  six colours, each a hex for the screen and an ACI number for DXF")
print("maps: every check passed")
sys.exit(0)
