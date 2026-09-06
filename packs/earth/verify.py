"""Check the pack against the dataset and the node, and say which line failed.  planetai run earth verify

Six checks: the libraries import, the bucket answers without credentials, the file is the shape its README
claims, the de-quantised vectors really have unit length, the cached window really is around this node, and
the reading reached the database.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import adapter as A                                                              # noqa: E402

TOLERANCE = 0.01                                                                 # measured spread is 0.002
SAMPLE = 2000
fails = []


def step(n, ok, msg):
    print(f"  {'✓' if ok else '✗'} {n}: {msg}")
    if not ok:
        fails.append(f"{n}: {msg}")


lat, lon, radius = A.aoi()

try:
    import numpy as np
    import rasterio
    step(1, True, f"numpy {np.__version__}, rasterio {rasterio.__version__} (GDAL {rasterio.__gdal_version__})")
except ImportError as e:
    step(1, False, f"{e}. planetai packs install, then planetai restart"); print(f"\n{A.ATTRIBUTION}"); sys.exit(1)

m = A.meta()
tiles = m.get("tiles") or {}
try:
    if not tiles:
        tiles = A.resolve(lat, lon)
    year = max(int(y) for y in tiles)
    obj = tiles[str(year)]["path"]
    step(2, True, f"the index covers this point: {len(tiles)} years, newest {year}")
except Exception as e:                                                           # noqa: BLE001
    step(2, False, f"tile index: {type(e).__name__}: {str(e)[:160]}"); print(f"\n{A.ATTRIBUTION}"); sys.exit(1)

try:
    with A.open_cog(obj) as ds:
        shape_ok = (ds.width, ds.height, ds.count) == (8192, 8192, 64)
        step(3, ds.dtypes[0] == "int8" and ds.nodata == -128 and shape_ok,
             f"{obj.rsplit('/', 1)[-1]}: {ds.width}x{ds.height}, {ds.count} bands, {ds.dtypes[0]}, "
             f"nodata {ds.nodata}, {ds.crs} — the README says 8192x8192, 64, int8, -128")
except Exception as e:                                                           # noqa: BLE001
    step(3, False, f"anonymous read of the bucket failed: {type(e).__name__}: {str(e)[:160]}")

years = A.cached_years()
if years:
    arr = np.load(A.year_file(years[-1]), mmap_mode="r")
    ys, xs = np.nonzero(np.asarray(arr[0]) != -128)
    if ys.size < SAMPLE:
        step(4, False, f"{years[-1]}: only {ys.size} unmasked pixels, fewer than the {SAMPLE} this checks")
    else:
        pick = np.random.default_rng(0).choice(ys.size, SAMPLE, replace=False)
        norms = np.linalg.norm(A.dequantize(np.asarray(arr[:, ys[pick], xs[pick]])), axis=0)
        worst = float(np.abs(norms - 1.0).max())
        step(4, worst <= TOLERANCE,
             f"{SAMPLE} de-quantised vectors from {years[-1]}: worst deviation from unit length {worst:.5f} "
             f"(tolerance {TOLERANCE})")
    w = m.get("windows", {}).get(str(years[-1]), {})
    b = w.get("bounds") or {}
    if b:
        span_km = (b["east"] - b["west"]) / 1000.0, (b["north"] - b["south"]) / 1000.0
        want = 2 * radius / 1000.0
        step(5, w.get("clipped") or abs(span_km[0] - want) < 0.02 and abs(span_km[1] - want) < 0.02,
             f"the cached window is {span_km[0]:.2f} x {span_km[1]:.2f} km in {w.get('crs')}"
             + (" (clipped at the tile edge)" if w.get("clipped") else f", asked for {want:.2f}"))
    else:
        step(5, False, "meta.json has no window bounds — re-run planetai run earth fetch --force")
else:
    step(4, False, "no year is cached yet.  planetai run earth fetch")
    step(5, False, "no window to check")

try:
    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"]) as con, con.cursor() as cur:
        cur.execute("SELECT metric, value FROM observations WHERE sensor_id = 'earth-point' ORDER BY metric")
        rows = cur.fetchall()
    got = ", ".join(f"{r[0]}={float(r[1]):.4f}" for r in rows) if rows else ""
    step(6, bool(rows), got or "earth-point has no readings yet: the pack needs PACKS_ALLOW_CODE=1 and one poll "
                               "after planetai run earth change")
except Exception as e:                                                           # noqa: BLE001
    step(6, False, f"database: {type(e).__name__}: {str(e)[:160]}")

print(f"\n{A.ATTRIBUTION}")
if fails:
    print(f"\nearth: {len(fails)} check(s) failed — {fails[0]}")
    sys.exit(1)
print("\nearth: all checks pass.")
