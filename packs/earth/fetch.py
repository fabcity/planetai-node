"""Download this node's square of the AlphaEarth embeddings, one year per file.  planetai run earth fetch [year ...] [--force]

With no years, every year the dataset has and EARTH_YEARS allows. Measured on node #1 (Bali, 10 km square):
149 s and 64 MB on disk per year, about 103 MB over the wire. Nine years is 576 MB on disk, 925 MB pulled.
An already cached year is skipped unless --force.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import adapter as A                                                              # noqa: E402

A.require("numpy", "rasterio")           # before the index download, not nine years into it

args = [a for a in sys.argv[1:] if not a.startswith("-")]
force = "--force" in sys.argv[1:]
lat, lon, radius = A.aoi()
years = sorted({int(a) for a in args}) if args else A.wanted_years()
bad = [y for y in years if y not in A.YEARS]
if bad:
    print(f"earth: {', '.join(map(str, bad))} is not in the dataset ({A.YEARS[0]}-{A.YEARS[-1]})"); sys.exit(1)

A.cache().mkdir(parents=True, exist_ok=True)
m = A.meta()
tiles = m.get("tiles") or {}
# A cached year is a window of pixels around a point. If the node moved, or the square changed size, every file on
# disk is a picture of somewhere else — and they are named by year alone, so without this they would all be skipped
# as "already cached" and the node would keep comparing the old place.
prev_radius = m.get("radius_m")
d = A.drift(m, lat, lon) if tiles else None
moved = d is not None and d > A.move_tolerance(radius)
resized = bool(tiles) and prev_radius not in (None, radius)
stale_square = moved or resized or (bool(tiles) and d is None)
if not tiles or stale_square:
    counted: dict = {}
    print(f"earth: finding the tiles for {lat}, {lon} (UTM {A.utm_zone(lat, lon)}) in the index …", flush=True)
    t0 = time.time()
    tiles = A.resolve(lat, lon, counted)
    print(f"  index: {counted['index_probes']} range reads + one block, {counted['index_bytes'] / 1e6:.1f} MB, "
          f"{time.time() - t0:.0f}s")
    # a fresh dict on purpose: `windows` belongs to the square that was just abandoned
    m = {"lat": lat, "lon": lon, "radius_m": radius, "utm_zone": A.utm_zone(lat, lon),
         "dataset": A.DATASET, "attribution": A.ATTRIBUTION, "tiles": tiles}
    A.write_meta(m)
elif d:
    # smaller than the tolerance: the cached square still covers this point. Record where the node actually is and
    # how far that is from the centre the pixels were read around, rather than pretending they match.
    m["lat"], m["lon"], m["point_drift_m"] = lat, lon, round(d, 1)
    A.write_meta(m)

if stale_square:
    why = (f"the node moved {d:.0f} m" if moved else
           f"the square changed from {prev_radius} to {radius} m" if resized else
           "the cache does not record which point it was read around")
    on_disk = [y for y in A.cached_years()]
    if on_disk:
        print(f"earth: {why} — every cached year describes the previous square")
    # Years this run re-reads are overwritten below. Years it does not are dropped: leaving them would let
    # `earth change` compare one square against another and report the difference between two places.
    for y in on_disk:
        if y not in years:
            A.year_file(y).unlink()
            print(f"  {y}: removed, it was read around the previous point (planetai run earth fetch {y} to get it back)")
    # The comparisons too: /earth and the dashboard card read every change_*.json in this directory, so a map of the
    # previous square would keep answering for this node until someone ran `earth change` again. The Index cell reads
    # them as well, which is how a node in Barcelona reported a year of Chilean land change.
    for f in sorted(A.cache().glob("change_*")):
        f.unlink()
        print(f"  {f.name}: removed, it compares the previous square (planetai run earth change after this)")

todo = [y for y in years if force or stale_square or not A.year_file(y).exists()]
skipped = [y for y in years if y not in todo]
if skipped:
    print(f"earth: already cached, skipping {', '.join(map(str, skipped))} (--force to re-read)")
if not todo:
    sys.exit(0)
print(f"earth: {len(todo)} year(s) to read, about {len(todo) * 64} MB on disk and {len(todo) * 103} MB pulled")

total_bytes, total_s, failed = 0, 0.0, []
for year in todo:
    row = tiles.get(str(year))
    if not row:
        print(f"  {year}: the index has no tile for this point"); failed.append(year); continue
    name = row["path"].rsplit("/", 1)[-1]
    t0 = time.time()
    try:
        with A.open_cog(row["path"]) as ds:
            w, bounds, clipped, node_rc = A.window_for(ds, lat, lon, radius)
            arr = A.read_window(ds, w)
            crs = str(ds.crs)
            south_up = ds.transform.e > 0
    except Exception as e:                                                       # noqa: BLE001
        print(f"  {year}: {type(e).__name__}: {str(e)[:160]}"); failed.append(year); continue
    import numpy as np
    # These tiles are stored with a positive y pixel size: row 0 is the southern edge. Flip once here so that
    # every .npy on disk is north-up and nothing downstream has to remember which way the file ran.
    if south_up:
        arr = np.ascontiguousarray(arr[:, ::-1, :])
        node_rc = (arr.shape[1] - 1 - node_rc[0], node_rc[1])
    np.save(A.year_file(year), arr)
    n = A.year_file(year).stat().st_size
    dt = time.time() - t0
    total_bytes += n; total_s += dt
    note = "  (clipped to the tile edge)" if clipped else ""
    print(f"  {year}: {arr.shape[2]}x{arr.shape[1]} px, {n / 1e6:.0f} MB, {dt:.0f}s  {name}{note}", flush=True)
    m.setdefault("windows", {})[str(year)] = {"crs": crs, "bounds": bounds, "px": [arr.shape[2], arr.shape[1]],
                                              "clipped": clipped, "north_up": True, "node_rc": list(node_rc), "object": row["path"]}
    A.write_meta(m)

print(f"\nearth: {total_bytes / 1e6:.0f} MB on disk in {total_s:.0f}s. Cached years: "
      f"{', '.join(map(str, A.cached_years())) or 'none'}")
print(A.ATTRIBUTION)
if failed:
    print(f"earth: {len(failed)} year(s) failed: {', '.join(map(str, failed))}"); sys.exit(1)
print("Next: planetai run earth change")
