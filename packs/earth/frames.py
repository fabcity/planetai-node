"""One picture of the place per cached year, so the record can be watched.  planetai run earth frames [--refit]

Renders each cached year to year_<YYYY>.png in out/earth/<node>/: the first principal component of the 64
embedding dimensions, mapped to grey through one projection shared by every frame. Dark water, bright land.
The dashboard's card animates them and lets you stop on a year.

These are not photographs. This pack has never downloaded imagery — it holds a model's 64-number description
of every 10 m pixel, and this is that description flattened to one number and drawn. It is a real picture of
real structure, and the greys are an axis, not a colour anyone saw. For actual Landsat and Sentinel-2 frames,
`planetai run earth-engine timelapse` needs an Earth Engine key and downloads pictures.

The projection is fitted once and kept in meta.json. Next year's layer is drawn through the same projection,
so the new frame joins the sequence instead of changing every frame before it. `--refit` redoes it, which
rewrites every frame; do that when the square moves, not when a year arrives.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import adapter as A                                                              # noqa: E402

A.require("numpy")

years = A.cached_years()
if not years:
    print("earth: no year is cached.  planetai run earth fetch"); sys.exit(1)

m = A.meta()
placed = [y for y in years if (m.get("windows", {}).get(str(y), {}) or {}).get("bounds")]
orphans = [y for y in years if y not in placed]
if orphans:
    print(f"earth: skipping {', '.join(map(str, orphans))} — on disk but not in meta.json for this square "
          f"(read around another point). planetai run earth fetch {' '.join(map(str, orphans))} --force")
if not placed:
    print("earth: no cached year belongs to this square."); sys.exit(1)

view, why = m.get("view"), "kept"
if "--refit" in sys.argv[1:] or not view or sorted(view.get("fitted_on", [])) != placed:
    t0 = time.time()
    print(f"earth: fitting one shared view over {len(placed)} year(s) …", flush=True)
    view, why = A.fit_view(placed), f"fitted in {time.time() - t0:.0f}s"
    m["view"] = view
    A.write_meta(m)
    for p in A.cache().glob("year_*.png"):                # every frame must come from the projection in use
        p.unlink()

wrote, total = 0, 0
for y in placed:
    if A.year_png(y).exists():
        continue
    t0 = time.time()
    rc = (m.get("windows", {}).get(str(y), {}) or {}).get("node_rc")
    ix = A.render_year(y, view, (int(rc[0]), int(rc[1])) if rc else None)
    n = A.write_png(A.year_png(y), ix, {
        "Title": f"{y}, {A.node()}",
        "Description": f"AlphaEarth embedding for {y}, first principal component as grey, one projection "
                       f"shared across {placed[0]}-{placed[-1]}. North up, 10 m per pixel. Not a photograph.",
        "Copyright": A.ATTRIBUTION,
    })
    wrote += 1; total += n
    print(f"  {y}: {n / 1000:.0f} kB  {time.time() - t0:.0f}s", flush=True)

kept = len(placed) - wrote
print(f"\nearth: {wrote} frame(s) written{f', {kept} already there' if kept else ''}, "
      f"{total / 1e6:.1f} MB, view {why}")
print(f"  {A.cache()}")
print(f"  {placed[0]}–{placed[-1]}, {len(placed)} year(s). The card animates them; the slider stops on one.")
print(A.ATTRIBUTION)
