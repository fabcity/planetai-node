"""The earth pack's arithmetic, offline: no bucket, no rasterio, no database.

numpy is imported without a guard on purpose. This pack's only claim is arithmetic, so a run that quietly
prints "skipped" because numpy is missing is worse than a run that fails: it would let the pack ship with the
de-quantisation wrong. If this line fails, install numpy on the dev machine.
Run: PYTHONPATH=/tmp/stub:app python3 tests/test_earth.py
"""
import importlib.util
import json
import os
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import numpy as np

os.environ.setdefault("NODE_LAT", "-8.8271")
os.environ.setdefault("NODE_LON", "115.15709")
os.environ.setdefault("NODE_NAME", "test-node")

spec = importlib.util.spec_from_file_location("earthpack", "packs/earth/adapter.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

# ---------------------------------------------------------------- de-quantisation and the norm
# The bucket's README: divide by 127.5, square, keep the sign. Not a linear scale factor.
assert A.dequantize(np.array([127], dtype=np.int8))[0] == np.float32((127 / 127.5) ** 2)
assert A.dequantize(np.array([-127], dtype=np.int8))[0] == np.float32(-((127 / 127.5) ** 2))
assert A.dequantize(np.array([0], dtype=np.int8))[0] == 0.0
# monotone in the raw value, which is what makes it a usable quantisation at all
raw = np.arange(-127, 128, dtype=np.int8)
assert np.all(np.diff(A.dequantize(raw)) > 0)
# and it stays inside the range the README promises
assert A.dequantize(raw).min() >= -1.0 and A.dequantize(raw).max() <= 1.0

# Round trip: quantise a unit vector the way the dataset does, de-quantise it, and the length comes back to 1
# within the tolerance verify.py enforces on real pixels.
rng = np.random.default_rng(7)
v = rng.normal(size=(64, 500)).astype(np.float32)
v /= np.linalg.norm(v, axis=0)
q = np.clip(np.rint(np.sign(v) * np.sqrt(np.abs(v)) * 127.5), -127, 127).astype(np.int8)
norms = np.linalg.norm(A.dequantize(q), axis=0)
worst = float(np.abs(norms - 1.0).max())
assert worst < 0.01, f"quantisation round trip drifts by {worst}, more than verify.py's 0.01 tolerance"

# ---------------------------------------------------------------- the distance
def stack(vec, h, w):
    return np.repeat(vec[:, None, None], h, 1).repeat(w, 2)

u = v[:, 0] / np.linalg.norm(v[:, 0])
qu = np.clip(np.rint(np.sign(u) * np.sqrt(np.abs(u)) * 127.5), -127, 127).astype(np.int8)
same = stack(qu, 4, 4)
d, masked = A.cosine_distance(same, same)
assert not masked.any()
assert np.allclose(d, 0.0, atol=2e-3), f"a year against itself must be 0, got {d.max()}"

# the opposite vector is distance 2; a right angle is 1
d_opp, _ = A.cosine_distance(same, stack(-qu, 4, 4))
assert abs(float(d_opp.max()) - 2.0) < 2e-3, d_opp.max()
e0 = np.zeros(64, dtype=np.int8); e0[0] = 127
e1 = np.zeros(64, dtype=np.int8); e1[1] = 127
d_perp, _ = A.cosine_distance(stack(e0, 3, 3), stack(e1, 3, 3))
assert abs(float(d_perp.max()) - 1.0) < 2e-3, d_perp.max()

# every distance stays inside [0, 2] even on adversarial input
rand_a = rng.integers(-127, 128, size=(64, 40, 40)).astype(np.int8)
rand_b = rng.integers(-127, 128, size=(64, 40, 40)).astype(np.int8)
d_rand, _ = A.cosine_distance(rand_a, rand_b)
assert float(np.nanmin(d_rand)) >= 0.0 and float(np.nanmax(d_rand)) <= 2.0

# no data is -128 in every channel, it is excluded, and it does not become a number
a = stack(qu, 5, 5).copy(); a[:, 2, 3] = -128
d_m, m_m = A.cosine_distance(a, stack(qu, 5, 5))
assert m_m[2, 3] and m_m.sum() == 1 and np.isnan(d_m[2, 3])

# the band size must not change the answer
d1, _ = A.cosine_distance(rand_a, rand_b, rows=7)
assert np.allclose(np.nan_to_num(d_rand), np.nan_to_num(d1), atol=1e-6)

# ---------------------------------------------------------------- the window, against a known tile
# Node #1: -8.8271, 115.15709 falls in 50S tile x...-0000000000-0000008192, whose pixel origin is
# 254240 E. The measured centre pixel is row 680, col 4306, and a 5000 m radius gave a window at
# col_off 3806, row_off 180, 1000 x 1000. That is the arithmetic below, with no raster and no projection.
r0, c0, r1, c1, clipped = A.window_px(680, 4306, 5000, 8192, 8192)
assert (r0, c0, r1 - r0, c1 - c0) == (180, 3806, 1000, 1000), (r0, c0, r1, c1)
assert not clipped
# and at an edge it clips rather than reading outside the tile
r0, c0, r1, c1, clipped = A.window_px(100, 4306, 5000, 8192, 8192)
assert (r0, r1 - r0) == (0, 600) and clipped
try:
    A.window_px(-900, 4306, 5000, 8192, 8192); raise AssertionError("a square wholly off the tile must raise")
except RuntimeError:
    pass

# ---------------------------------------------------------------- the zone the index is searched by
assert A.utm_zone(-8.8271, 115.15709) == "50S"          # Bali
assert A.utm_zone(41.3874, 2.1686) == "31N"             # Barcelona
assert A.utm_zone(-33.4310, -70.6045) == "19S"          # Santiago
assert A.utm_zone(42.3601, -71.0589) == "19N"           # Boston
assert A.utm_zone(0.0, -180.0) == "1N" and A.utm_zone(-1.0, 179.999) == "60S"
# the index is sorted 1N..60N then 1S..60S; the search depends on that order
assert A._zone_key("1N") < A._zone_key("60N") < A._zone_key("1S") < A._zone_key("50S")

# ---------------------------------------------------------------- the ramp and the PNG
dist = np.array([[0.0, A.RAMP_CEILING / 2, A.RAMP_CEILING, 1.0]], dtype=np.float32)
mask = np.array([[False, False, False, False]])
ix = A.ramp_indices(dist, mask)
assert ix[0, 0] == 1 and ix[0, 2] == 252 and ix[0, 3] == 252, ix     # the ceiling clamps, it does not wrap
assert 120 < int(ix[0, 1]) < 135
assert A.ramp_indices(dist, np.array([[True, False, False, False]]))[0, 0] == A.NODATA_IX

with tempfile.TemporaryDirectory() as tmp:
    png = Path(tmp) / "t.png"
    grid = np.zeros((40, 200), dtype=np.uint8)
    A.draw_marks(grid, (20, 100))
    assert (grid == A.NODE_IX).sum() > 0, "the node ring was not drawn"
    assert (grid == A.RULE_IX).sum() > 0, "the scale bar was not drawn"
    n = A.write_png(png, grid, {"Copyright": A.ATTRIBUTION})
    blob = png.read_bytes()
    assert n == len(blob) and blob[:8] == b"\x89PNG\r\n\x1a\n"
    # walk the chunks: the length, type and CRC of each must agree, and the header must say what we meant
    pos, seen, idat = 8, [], b""
    while pos < len(blob):
        ln = struct.unpack(">I", blob[pos:pos + 4])[0]
        kind = blob[pos + 4:pos + 8]
        data = blob[pos + 8:pos + 8 + ln]
        crc = struct.unpack(">I", blob[pos + 8 + ln:pos + 12 + ln])[0]
        assert crc == zlib.crc32(kind + data) & 0xFFFFFFFF, f"bad CRC on {kind}"
        seen.append(kind.decode())
        if kind == b"IDAT":
            idat += data
        pos += 12 + ln
    assert seen[0] == "IHDR" and seen[-1] == "IEND" and "PLTE" in seen and "tEXt" in seen
    w_, h_, depth, ctype = struct.unpack(">IIBB", blob[16:26])
    assert (w_, h_, depth, ctype) == (200, 40, 8, 3)
    assert A.ATTRIBUTION.encode() in blob, "the attribution must travel inside the PNG"
    # the pixels come back exactly, filter byte and all
    rows = zlib.decompress(idat)
    assert len(rows) == h_ * (w_ + 1)
    back = np.frombuffer(rows, dtype=np.uint8).reshape(h_, w_ + 1)
    assert (back[:, 0] == 0).all() and np.array_equal(back[:, 1:], grid)

# ---------------------------------------------------------------- the cache and the adapter
with tempfile.TemporaryDirectory() as tmp:
    os.environ["PACK_OUT"] = tmp
    assert A.cached_years() == [] and A.latest_pair() is None
    A.cache().mkdir(parents=True)
    for y in (2017, 2020, 2024, 2025):
        np.save(A.year_file(y), np.zeros((2, 2, 2), dtype=np.int8))
    assert A.cached_years() == [2017, 2020, 2024, 2025]
    assert A.latest_pair() == (2024, 2025), "only consecutive years are a year-over-year pair"
    # and when the newest years are not adjacent, the pair is the newest adjacent one, not the newest two
    for y in (2020, 2024, 2025):
        A.year_file(y).unlink()
    for y in (2018, 2023):
        np.save(A.year_file(y), np.zeros((2, 2, 2), dtype=np.int8))
    assert A.cached_years() == [2017, 2018, 2023]
    assert A.latest_pair() == (2017, 2018), "2018 and 2023 are five years apart, not a year-over-year pair"
    A.year_file(2023).unlink(); A.year_file(2018).unlink()
    for y in (2020, 2024, 2025):
        np.save(A.year_file(y), np.zeros((2, 2, 2), dtype=np.int8))
    # an idle pack says nothing rather than raising or inventing a reading
    assert A.fetch(None) == ([], [])
    for a_, b_, mean in ((2024, 2025, 0.041), (2017, 2025, 0.128)):
        A.change_file(a_, b_, "json").write_text(json.dumps(
            {"year_a": a_, "year_b": b_, "mean": mean, "threshold": 0.15, "share_over_threshold": 0.01,
             "hectares_over_threshold": 100.0, "png": f"change_{a_}_{b_}.png", "tiles": ["gs://x"]}))
    sensors, readings = A.fetch(None)
    got = {m: v for _, _, m, v in readings}
    assert sensors[0]["sensor_id"] == "earth-point" and sensors[0]["kind"] == "model"
    assert sensors[0]["scale"] == "city" and sensors[0]["cadence"] == "P1Y" and not sensors[0]["local"]
    assert A.ATTRIBUTION in sensors[0]["meta"]["attribution"]
    assert got["land_change_yoy"] == 0.041 and got["land_change_since_2017"] == 0.128
    assert got["years_cached"] == 4.0
    assert all(ts.year == 2025 for ts, _, _, _ in readings), "an annual reading is stamped in its own year"
    os.environ.pop("PACK_OUT")

# the cell the pack ships must be partial, and must read the metric the adapter writes
import yaml                                                                      # noqa: E402
cells = yaml.safe_load(open("packs/earth/cells.yml"))
assert len(cells) == 1 and cells[0]["cell"] == "Environmental|City"
assert cells[0]["state"] == "partial", "a model's output is never live"
assert "land_change_yoy" in cells[0]["sql"] and "earth-point" in cells[0]["sql"]
manifest = yaml.safe_load(open("packs/earth/pack.yaml"))
assert set(manifest["metrics"]) == {"land_change_yoy", "land_change_since_2017", "years_cached"}
assert manifest["pip"] == ["rasterio", "numpy"] and manifest["scales"] == ["city"]
assert A.ATTRIBUTION == manifest["attribution"]

# ---------------------------------------------------------------- a square that stopped describing this node
# The cached years are named by year alone. Before this, changing NODE_LAT/NODE_LON re-resolved the tiles but every
# cached year was skipped as "already cached", so the node went on comparing the previous square, and verify passed
# because it measured the window's size and never its position.
BALI = (-8.8271, 115.15709)
assert round(A.metres(*BALI, BALI[0] + 0.001, BALI[1])) == 111
assert A.move_tolerance(5000) == 50.0 and A.move_tolerance(1000) == 25.0, "1% of the radius, floor 25 m"
assert A.drift({}, *BALI) is None, "a cache with no point recorded cannot be placed"
assert A.drift({"lat": BALI[0], "lon": BALI[1]}, *BALI) == 0.0
assert round(A.drift({"lat": BALI[0], "lon": BALI[1]}, BALI[0] + 0.002, BALI[1])) == 223
assert A.drift({"lat": 41.4036, "lon": 2.2033}, *BALI) > 1e6

_fetch = open("packs/earth/fetch.py").read()
assert "stale_square = moved or resized" in _fetch, "a moved or resized square must be detected"
assert "force or stale_square or not A.year_file(y).exists()" in _fetch, \
    "a stale square must re-read the cached years, not skip them as already cached"
assert 'prev_radius = m.get("radius_m")' in _fetch, "the previous radius has to be read before meta is replaced"
_verify = open("packs/earth/verify.py").read()
assert "A.drift(m, lat, lon)" in _verify, "verify must place the cache, not only measure it"
assert "A.year_file(y).unlink()" in _fetch, "years the run will not re-read must not survive a moved square"
_change = open("packs/earth/change.py").read()
assert 'orphan = [y for y, w in ((a, wa), (b, wb)) if not w.get("bounds")]' in _change, \
    "change must refuse a year with no window for the current square"

assert 'A.cache().glob("change_*")' in _fetch, "a moved square must not leave its comparison for the card to serve"

print("earth move tests pass")

# ---------------------------------------------------------------- change: its arguments, and --all
# `planetai run earth change --all` used to print an ordinary result for the latest pair: the flag was not a
# digit so it was dropped, and an empty argument list meant "the default". Run the real script and read what
# it does, rather than grepping it for the word --all.
import subprocess
with tempfile.TemporaryDirectory() as tmp:
    env = {**os.environ, "PACK_OUT": tmp, "NODE_NAME": "t", "NODE_LAT": "-8.8271", "NODE_LON": "115.15709",
           "EARTH_RADIUS_M": "5000", "PYTHONPATH": os.getcwd()}
    cache = Path(tmp) / "earth" / "t"; cache.mkdir(parents=True)
    win = {"crs": "EPSG:32750", "bounds": {"west": 0.0, "east": 40.0, "south": 0.0, "north": 40.0},
           "px": [4, 4], "clipped": False, "north_up": True, "node_rc": [2, 2], "object": "gs://x.tiff"}
    rng2 = np.random.default_rng(3)
    for y in (2020, 2021, 2022):
        np.save(cache / f"{y}.npy", rng2.integers(-100, 100, size=(64, 4, 4)).astype(np.int8))
    (cache / "meta.json").write_text(json.dumps(
        {"lat": -8.8271, "lon": 115.15709, "radius_m": 5000, "windows": {str(y): win for y in (2020, 2021, 2022)}}))

    def run(*a):
        return subprocess.run([sys.executable, "packs/earth/change.py", *a], env=env, capture_output=True, text=True)

    for bad in (["--evrything"], ["217", "2022"], ["2021"], ["2020", "2021", "2022"]):
        r = run(*bad)
        assert r.returncode == 1, f"change {' '.join(bad)} must fail, got {r.returncode}: {r.stdout}"
        assert "usage:" in r.stdout, f"change {' '.join(bad)} must print the usage: {r.stdout}"
    assert not list(cache.glob("change_*")), "a rejected argument must not compute anything"

    r = run()                                        # the default is still the latest consecutive pair
    assert r.returncode == 0, r.stdout + r.stderr
    assert {p.name for p in cache.glob("change_*.json")} == {"change_2021_2022.json"}, r.stdout

    r = run("--all")                                 # every consecutive pair, plus the span
    assert r.returncode == 0, r.stdout + r.stderr
    assert {p.name for p in cache.glob("change_*.json")} == {
        "change_2020_2021.json", "change_2021_2022.json", "change_2020_2022.json"}, r.stdout
    assert "the span" in r.stdout and "already computed, skipping 2021→2022" in r.stdout, r.stdout

    before = (cache / "change_2020_2021.json").stat().st_mtime_ns
    assert "already computed" in run("--all").stdout                       # idempotent
    assert (cache / "change_2020_2021.json").stat().st_mtime_ns == before
    assert "already computed" not in run("--all", "--force").stdout        # and --force redoes it
    assert (cache / "change_2020_2021.json").stat().st_mtime_ns != before
print("change: unknown arguments refused, --all walks the history, --force redoes it")

# ---------------------------------------------------------------- the yearly frames
# The projection must be fitted once and reused: refitting when a year arrives would silently redraw every
# earlier frame, and a sequence whose greys move is not a sequence.
with tempfile.TemporaryDirectory() as tmp:
    os.environ["PACK_OUT"] = tmp
    A.cache().mkdir(parents=True)
    rng3 = np.random.default_rng(11)
    for y in (2023, 2024):
        np.save(A.year_file(y), rng3.integers(-100, 100, size=(64, 24, 24)).astype(np.int8))
    view = A.fit_view([2023, 2024])
    assert view["fitted_on"] == [2023, 2024] and len(view["axis"]) == 64 and len(view["breaks"]) == 256
    assert abs(float(np.linalg.norm(view["axis"])) - 1.0) < 1e-5, "the axis is a direction, so unit length"
    assert A.fit_view([2023, 2024])["axis"] == view["axis"], "the same years must give the same axis"
    # The sign of a principal axis is arbitrary; SVD picking one is not a guarantee. The pack fixes it so the
    # projection is left-skewed, which is what keeps water dark and land bright when the fit is redone over a
    # different set of years. Check the property, not that two identical calls agree.
    _v = A.dequantize(np.asarray(np.load(A.year_file(2024), mmap_mode="r")).reshape(64, -1))
    _p = (np.array(view["axis"])[None, :] @ (_v - np.array(view["mean"])[:, None]))[0]
    assert float(((_p - _p.mean()) ** 3).mean()) <= 0, "fit_view must fix the axis sign, not take SVD's"
    ix = A.render_year(2023, view, (12, 12))
    assert ix.shape == (24, 24) and ix.dtype == np.uint8
    assert ix.min() >= 0 and ix.max() <= 254
    # a year drawn through a view fitted without it still renders, and identically each time
    assert np.array_equal(A.render_year(2024, view), A.render_year(2024, view))
    # no-data survives as no-data rather than becoming a grey
    raw = np.load(A.year_file(2023)); raw[:, 3, 4] = -128; np.save(A.year_file(2023), raw)
    assert A.render_year(2023, view)[3, 4] == A.NODATA_IX
    # the year is burnt in, in the rule colour, bottom right
    big = np.zeros((200, 200), dtype=np.uint8)
    A.draw_year(big, 2017)
    assert (big == A.RULE_IX).sum() > 0 and (big[:100, :100] == A.RULE_IX).sum() == 0, "bottom right"
    assert A.year_png(2017).name == "year_2017.png"
    os.environ.pop("PACK_OUT")
print("earth frames: one shared projection, reused, and no-data stays no-data")

print("all earth pack tests pass")
sys.exit(0)
