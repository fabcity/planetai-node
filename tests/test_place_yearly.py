"""The place pack's yearly building count (packs/place/satellite.py yearly, packs/place/adapter.py satellite_refresh).

Open Buildings Temporal keeps `building_fractional_count` as a fraction of a building on each 0.5 m pixel, and Earth
Engine's pyramid for it is the mean. Google's own example, "How to compute building count for a given AOI", sums at a
coarser scale and multiplies by (scale × 2)² "to recover sum at original 50cm resolution". Until 18 Nov 2026 yearly()
summed at 4 m and multiplied by nothing: node #1 read 128 buildings in the circle where the footprints count 5994.

The Earth Engine below is a town spread evenly over the ground, reduced the way Earth Engine reduces: at a scale of
s metres a pixel carries the mean of the 0.5 m pixels under it, and a sum adds one value for each s × s pixel. Nothing
here reaches Earth Engine or a database."""
import math
import sys
import types
from datetime import datetime, timezone

sys.path.insert(0, "packs/place")
import adapter as place          # noqa: E402
import satellite as S            # noqa: E402

RADIUS = 1000
AREA = math.pi * RADIUS ** 2
TOWN = {2016: (5530.0, 4.1), 2019: (6820.0, 4.4), 2023: (8172.0, 4.8)}      # year: (buildings in the circle, mean height)
EPOCH = {int(datetime(y, 6, 30, 7, tzinfo=timezone.utc).timestamp()): y for y in TOWN}


class Image:
    """`at(s)` is what one pixel holds when the image is read at s metres."""
    def __init__(self, at): self.at = at
    def select(self, band): return Image(lambda s: {band: self.at(s)[band]})
    def _with(self, other, op):
        f = other.at if isinstance(other, Image) else (lambda s: {None: other})
        return Image(lambda s: {k: op(v, next(iter(f(s).values()))) for k, v in self.at(s).items()})
    def multiply(self, other): return self._with(other, lambda a, b: a * b)
    def divide(self, other): return self._with(other, lambda a, b: a / b)
    def gt(self, x): return self._with(x, lambda a, b: float(a > b))
    def updateMask(self, mask): return self                    # the town is built everywhere it is counted
    def reduceRegion(self, reducer, geometry, scale, maxPixels=None):
        px = self.at(scale)
        return Info({k: v * geometry.area / scale ** 2 if reducer == "sum" else v for k, v in px.items()})


class Info:
    def __init__(self, v): self.v = v
    def getInfo(self): return self.v
    def distinct(self): return self


class Collection:
    def __init__(self, epoch=None): self.epoch = epoch
    def filterBounds(self, g): return self
    def filter(self, epoch): return Collection(epoch)
    def aggregate_array(self, prop): return Info(list(EPOCH))
    def mosaic(self):
        n, h = TOWN[EPOCH[self.epoch]]
        per_pixel = n * 0.25 / AREA                             # the band: a building's share on one 0.5 m pixel
        return Image(lambda s: {"building_fractional_count": per_pixel, "building_height": h, "building_presence": 0.9})


ee = types.SimpleNamespace(
    Geometry=types.SimpleNamespace(Point=lambda xy: types.SimpleNamespace(buffer=lambda r: types.SimpleNamespace(area=math.pi * r ** 2))),
    ImageCollection=lambda _id: Collection(),
    Filter=types.SimpleNamespace(eq=lambda prop, v: v),
    Reducer=types.SimpleNamespace(sum=lambda: "sum", mean=lambda: "mean"),
    Image=types.SimpleNamespace(pixelArea=lambda: Image(lambda s: {"area": s ** 2})))

got = S.yearly(ee, -8.82, 115.16, RADIUS)
assert [y for y, _, _ in got] == [2016, 2019, 2023], got
for (year, count, height), (n, h) in zip(got, TOWN.values()):
    assert abs(count - n) < 1, f"{year}: the town has {n:.0f} buildings in the circle and yearly() counted {count:.1f} ({n / count:.0f} times off)"
    assert height == h, (year, height)
print("  yearly: the count is the buildings in the circle, not a sixty-fourth of them")

# A recount has to reach the readings. The node files a reading once (ON CONFLICT DO NOTHING, app/main.py), and the
# series is dated 1 July of each year, so the low rows of a node that ran before the fix would outlive every refresh.
ran = []


class Cur:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, params=None): ran.append((" ".join(sql.split()), params))


class Con:
    commits = 0
    def cursor(self): return Cur()
    def commit(self): Con.commits += 1


sys.modules["satellite"] = types.SimpleNamespace(init_ee=lambda: ee, footprints=lambda ee, con, lat, lon, r: ran.append(("footprints", r)) or (5994, 0.8),
                                                yearly=lambda ee, lat, lon, r: [(2016, 5530.0, 4.1), (2023, 8172.0, None)])
assert place.satellite_refresh(Con(), -8.82, 115.16, RADIUS) == 2
sql = [s for s, _ in ran]
assert sql[0] == "footprints", "the footprints first: the series is read against them"
ups = [(s, p) for s, p in ran if s.startswith("INSERT INTO place_yearly")]
assert [p for _, p in ups] == [(2016, 5530.0, 4.1), (2023, 8172.0, None)] and all("ON CONFLICT (year) DO UPDATE SET buildings=EXCLUDED.buildings" in s for s, _ in ups), ups
gone = [(s, p) for s, p in ran if s.startswith("DELETE FROM readings")]
assert len(gone) == 1 and "sensor_id='place-point'" in gone[0][0] and gone[0][1] == (["sat_buildings_yearly", "sat_height_m_yearly"],), gone
assert Con.commits == 1, "the old rows go and the new count lands in one commit"
print("  recount: place_yearly is rewritten by year and the readings filed from the old count are removed")

# every way a count is fetched goes through that one function: the monthly poll and `planetai run place refresh`
_adapter, _refresh = open("packs/place/adapter.py").read(), open("packs/place/refresh.py").read()
assert "satellite_refresh(con, lat, lon, radius)" in _adapter.split("def fetch(hc):")[1], "the poll does not run the satellite half"
assert "A.satellite_refresh(con, lat, lon, radius)" in _refresh, "`planetai run place refresh` does not run the satellite half"
assert _adapter.count("S.yearly(") == 1, "one place fetches the series"
print("  refresh: the poll and `planetai run place refresh` both recount")
print("place yearly tests pass")
