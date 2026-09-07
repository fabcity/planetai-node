"""Compare two cached years, pixel by pixel, and write the map and the numbers.  planetai run earth change [A B]

With no years, the two most recent consecutive cached years. Writes change_<A>_<B>.png (north up, a grey ramp,
the node ringed) and change_<A>_<B>.json (mean, median, p95, the share and the hectares above the threshold,
the bounds, the source objects) into out/earth/<node>/.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
import adapter as A                                                              # noqa: E402

# Where "changed" starts. Not a physical constant: it is the one number in this pack chosen rather than
# measured, and it is calibrated on one 10 km square of Bali. For the two consecutive-year pairs at node #1
# it sits at the 99th percentile, so about 1% of a normal year's square is flagged (2023→2024: 0.96%,
# 2024→2025: 1.19%); over the two-year gap 2023→2025 it flags 4.9%. Lower it and a quiet year looks busy:
# 0.05, the threshold the earth-engine pack uses on a different quantity, flags a third of this square.
CHANGED = 0.15

A.require("numpy")

import numpy as np                                                               # noqa: E402

args = [int(a) for a in sys.argv[1:] if a.isdigit()]
cached = A.cached_years()
if len(args) == 2:
    a, b = sorted(args)
elif args:
    print("usage: planetai run earth change [A B]"); sys.exit(1)
else:
    pair = A.latest_pair()
    if not pair:
        print(f"earth: no two consecutive years are cached (have: {', '.join(map(str, cached)) or 'none'}). "
              f"planetai run earth fetch"); sys.exit(1)
    a, b = pair
missing = [y for y in (a, b) if y not in cached]
if missing:
    print(f"earth: {', '.join(map(str, missing))} not cached. planetai run earth fetch {' '.join(map(str, missing))}")
    sys.exit(1)

m = A.meta()
wa, wb = (m.get("windows", {}).get(str(y), {}) for y in (a, b))
if wa.get("px") and wb.get("px") and wa["px"] != wb["px"]:
    print(f"earth: {a} is {wa['px']} px and {b} is {wb['px']} px — re-fetch both with --force"); sys.exit(1)
# meta.json records a window per year for the square the pack currently describes. A year with a file but no window
# was read around a different point, and comparing it with one from here would report the difference between two
# places as change over time.
orphan = [y for y, w in ((a, wa), (b, wb)) if not w.get("bounds")]
if orphan:
    print(f"earth: {', '.join(map(str, orphan))} on disk but not in meta.json for this square — read around another "
          f"point, or fetched by an older version. planetai run earth fetch {' '.join(map(str, orphan))} --force")
    sys.exit(1)

t0 = time.time()
X = np.load(A.year_file(a), mmap_mode="r")
Y = np.load(A.year_file(b), mmap_mode="r")
dist, masked = A.cosine_distance(X, Y)
good = dist[~masked]
if not good.size:
    print("earth: every pixel is masked in one of the two years"); sys.exit(1)

over = float((good > CHANGED).mean())
px_m2 = 100.0                                                                    # 10 m x 10 m
stats = {
    "node": A.node(), "year_a": a, "year_b": b,
    "mean": round(float(good.mean()), 5),
    "median": round(float(np.median(good)), 5),
    "p95": round(float(np.percentile(good, 95)), 5),
    "max": round(float(good.max()), 5),
    "threshold": CHANGED,
    "share_over_threshold": round(over, 5),
    "hectares_over_threshold": round(over * good.size * px_m2 / 10000.0, 1),
    "pixels": int(good.size), "pixels_masked": int(masked.sum()),
    "px": [int(dist.shape[1]), int(dist.shape[0])],
    "metres_per_pixel": 10,
    "crs": wb.get("crs") or wa.get("crs"),
    "bounds": wb.get("bounds") or wa.get("bounds"),
    "lat": m.get("lat"), "lon": m.get("lon"), "radius_m": m.get("radius_m"),
    "clipped": bool(wa.get("clipped") or wb.get("clipped")),
    "tiles": [w.get("object") for w in (wa, wb) if w.get("object")],
    "dataset": A.DATASET, "attribution": A.ATTRIBUTION,
    "computed_at": datetime.now(timezone.utc).isoformat(),
    "png": A.change_file(a, b, "png").name,
}

ix = A.ramp_indices(dist, masked)
rc = (wb.get("node_rc") or wa.get("node_rc"))                                    # recorded north-up by fetch.py
A.draw_marks(ix, (int(rc[0]), int(rc[1])) if rc else None)
stats["node_rc"] = rc
png_bytes = A.write_png(A.change_file(a, b, "png"), ix, {
    "Title": f"Land change {a}-{b}, {A.node()}",
    "Description": f"1 - cosine similarity of annual AlphaEarth embeddings, {a} to {b}. "
                   f"North up, 10 m per pixel, grey ramp 0 to {A.RAMP_CEILING}. Black is no data.",
    "Copyright": A.ATTRIBUTION,
})
A.change_file(a, b, "json").write_text(json.dumps(stats, indent=1))

print(f"earth: {a} → {b} over {stats['px'][0] * 10 / 1000:.1f} x {stats['px'][1] * 10 / 1000:.1f} km, "
      f"{time.time() - t0:.0f}s")
print(f"  mean {stats['mean']:.4f}  median {stats['median']:.4f}  p95 {stats['p95']:.4f}  max {stats['max']:.4f}")
print(f"  above {CHANGED}: {over * 100:.2f}% of the square, {stats['hectares_over_threshold']:.0f} ha")
print(f"  {A.change_file(a, b, 'png').name} ({png_bytes / 1000:.0f} kB)  {A.change_file(a, b, 'json').name}")
print(A.ATTRIBUTION)
