"""Which places look like which, in embedding space, across the four pilots.  planetai run earth similar [year] [--out FILE]

For each pilot in presets/, the mean embedding of the square around it, the cosine similarity between every
pair of pilots, and the ten most similar cells inside that pilot's own UTM tile.

The search is regional, not global, and the pack says so wherever the result is shown. One tile is about
82 km on a side. A global search would mean either every tile on the planet, about 370,000 files and half a
petabyte, or a vector index of the whole dataset. We have neither.

Cells are 1.28 km, not 1 km: they are the dataset's own 128x overview pixels, which the bucket's README says
are correctly re-normalised means of the pixels beneath them. Reading those instead of the full tile is the
difference between a few hundred kilobytes and two gigabytes per pilot.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import adapter as A                                                              # noqa: E402

OVERVIEW_FACTOR = 128                                                            # 128 x 10 m = 1.28 km a cell
OVERVIEW_LEVEL = OVERVIEW_FACTOR.bit_length() - 2                                # overviews are 2, 4, 8 ...: 128 is index 6
TOP = 10
PRESETS = Path(os.getenv("PACKS_DIR", "/app/packs")).parent / "presets"
PILOTS = ("bali", "barcelona", "boston", "santiago")

args = sys.argv[1:]
year = next((int(a) for a in args if a.isdigit()), A.YEARS[-1])
out_path = Path(args[args.index("--out") + 1]) if "--out" in args else A.cache() / "alphaearth_similarity.json"

A.require("numpy", "rasterio")

import numpy as np                                                               # noqa: E402
import rasterio                                                                  # noqa: E402
from rasterio.warp import transform as warp_transform                            # noqa: E402


def preset(name: str) -> tuple[float, float]:
    text = (PRESETS / f"{name}.env").read_text()
    v = dict(line.split("=", 1) for line in text.splitlines() if "=" in line and not line.startswith("#"))
    return float(v["NODE_LAT"]), float(v["NODE_LON"])


def unit(v):
    """The README's pyramiding rule: sum the de-quantised vectors, then re-normalise to unit length."""
    n = np.linalg.norm(v, axis=0)
    return v / (n + 1e-9)


print(f"earth: mean embeddings and similarity for {year}, {len(PILOTS)} pilots, "
      f"{OVERVIEW_FACTOR * 10 / 1000:.2f} km cells\n")
sites = []
for name in PILOTS:
    lat, lon = preset(name)
    t0 = time.time()
    tiles = A.resolve(lat, lon)
    row = tiles.get(str(year))
    if not row:
        print(f"  {name}: no {year} tile"); continue
    url = "/vsicurl/" + row["path"].replace("gs://", A.GCS + "/")
    for k, v in A.GDAL_ENV.items():
        os.environ.setdefault(k, v)
    with rasterio.open(url, overview_level=OVERVIEW_LEVEL) as ds:
        assert ds.width == 8192 // OVERVIEW_FACTOR, f"{name}: overview is {ds.width} px, expected {8192 // OVERVIEW_FACTOR}"
        grid = A.dequantize(ds.read())                                           # (64, 64, 64)
        nodata = (ds.read(1) == -128)
        xs, ys = warp_transform("EPSG:4326", ds.crs, [lon], [lat])
        r, c = ds.index(xs[0], ys[0])
        crs = ds.crs
        # the pilot's own vector: the cells within EARTH_RADIUS_M, summed then re-normalised
        half = max(1, int(A.aoi()[2] / (OVERVIEW_FACTOR * 10)))
        block = grid[:, max(0, r - half):r + half + 1, max(0, c - half):c + half + 1]
        mine = unit(block.reshape(64, -1).sum(1))
        flat = unit(grid.reshape(64, -1))
        sim = (flat * mine[:, None]).sum(0).reshape(grid.shape[1], grid.shape[2])
        sim[nodata] = -2.0
        sim[max(0, r - half):r + half + 1, max(0, c - half):c + half + 1] = -2.0  # not itself
        order = np.argsort(sim, axis=None)[::-1][:TOP]
        rows, cols = np.unravel_index(order, sim.shape)
        px, py = ds.xy(rows, cols)
        lons, lats = warp_transform(crs, "EPSG:4326", list(px), list(py))
        matches = [{"lat": round(la, 4), "lon": round(lo, 4), "similarity": round(float(sim[rr, cc]), 4),
                    "km_from_pilot": round(float(np.hypot(px[i] - xs[0], py[i] - ys[0]) / 1000), 1)}
                   for i, (la, lo, rr, cc) in enumerate(zip(lats, lons, rows, cols))]
    sites.append({"key": name, "lat": lat, "lon": lon, "utm_zone": row["utm_zone"], "crs": row["crs"],
                  "tile": row["path"], "vector": [round(float(x), 6) for x in mine],
                  "tile_km": round(8192 * 10 / 1000, 1), "similar": matches})
    print(f"  {name:10} {row['utm_zone']:4} best in tile {matches[0]['similarity']:.3f} at "
          f"{matches[0]['km_from_pilot']:.0f} km  ({time.time() - t0:.0f}s)")

between = []
for i, a in enumerate(sites):
    for b in sites[i + 1:]:
        between.append({"a": a["key"], "b": b["key"],
                        "similarity": round(float(np.dot(a["vector"], b["vector"])), 4)})
print("\n  between pilots:")
for p in sorted(between, key=lambda x: -x["similarity"]):
    print(f"    {p['a']:10} ~ {p['b']:10} {p['similarity']:+.3f}")

doc = {
    "generated": datetime.now(timezone.utc).isoformat(),
    "year": year,
    "dataset": A.DATASET,
    "attribution": A.ATTRIBUTION,
    "cell_km": OVERVIEW_FACTOR * 10 / 1000,
    "tile_km": 8192 * 10 / 1000,
    "search": "regional",
    "search_note": ("Each pilot is compared with every 1.28 km cell of its own UTM tile, about 82 km on a "
                    "side. This is not a global search: that would need every tile on the planet or a vector "
                    "index of the whole dataset, and we have neither."),
    "method": ("Mean of the de-quantised 64-dimension AlphaEarth embeddings over the pilot's square, "
               "re-normalised to unit length, then cosine similarity against the dataset's own 128x overview "
               "cells. Computed on a PLANETAI node from the public COGs, with no Earth Engine account."),
    "pilots": [{k: v for k, v in s.items() if k != "vector"} for s in sites],
    "between": sorted(between, key=lambda x: -x["similarity"]),
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(doc, indent=1))
print(f"\nearth: wrote {out_path} ({out_path.stat().st_size / 1000:.0f} kB)")
print(A.ATTRIBUTION)
