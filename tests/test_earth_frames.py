"""The two satellite records are two records, and the route finds the frames a real node has.

node #1 is why this exists. `planetai run earth-engine timelapse` wrote
`out/bayu-2-2016-sentinel-3km.png` when the node was called bayu-2; NODE_NAME is bayu-ungasan now,
and a route that builds the filename from NODE finds nothing at all. The km in the name moves with
the pack's settings too. The year is the only part of that filename this node can be sure of.

Run: PYTHONPATH=app python3 tests/test_earth_frames.py   (needs the app's own deps, like import-check)
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "app"))

tmp = tempfile.mkdtemp()
os.environ.update(PACK_OUT=tmp, DATABASE_URL="postgresql://x:x@127.0.0.1:1/x", NODE_NAME="bayu-ungasan",
                  NODE_CITY="bali", NODE_LAT="-8.8", NODE_LON="115.1", PACKS_DIR=str(ROOT / "packs"))
import main  # noqa: E402

fails = []
out = Path(tmp)
# exactly what node #1 has in out/, old node name and all
for n in ("bayu-2-2016-sentinel-3km.png", "bayu-2-2019-sentinel-3km.png",
          "bayu-2-2022-sentinel-3km.png", "bayu-2-2025-sentinel-3km.png",
          "bayu-2-2012-landsat-2km.png", "bayu-2-2025-landsat-2km.png",
          "bayu-2-timelapse-sentinel.html",          # not a frame
          "change_2024_2025.png", "notes-sentinel-x.png"):
    (out / n).write_bytes(b"\x89PNG")

got = main._sentinel_frames("sentinel")
if sorted(got) != [2016, 2019, 2022, 2025]:
    fails.append(f"sentinel frames found {sorted(got)}, expected [2016, 2019, 2022, 2025]")
if sorted(main._sentinel_frames("landsat")) != [2012, 2025]:
    fails.append(f"landsat frames found {sorted(main._sentinel_frames('landsat'))}, expected [2012, 2025]")
if any("timelapse" in p.name or p.name.startswith("change_") for p in got.values()):
    fails.append("the glob picked up something that is not a frame")

# the whole point: the filename carries the node's OLD name and must still be found
if not all("bayu-2-" in p.name for p in got.values()):
    fails.append("this test no longer exercises the renamed-node case")
if main.NODE != "bayu-ungasan":
    fails.append("NODE is not the new name, so the case above is not being tested")

# The two records stay apart in /earth's body: `frames` is this node's own AlphaEarth layer,
# `imagery` is somebody else's photographs. A page that merged them would be calling a model output
# a photograph.
body = main.earth()
if "imagery" not in body or sorted(body["imagery"]["sentinel"]) != [2016, 2019, 2022, 2025]:
    fails.append(f"/earth must publish which imagery years exist: {body.get('imagery')}")
if body["imagery"]["sentinel"] == body.get("frames"):
    fails.append("the two satellite records must not be the same list")
if not any("Copernicus" in c for c in body["imagery"]["credit"]):
    fails.append("the imagery must carry its credit line")

# the route refuses what it does not have, and says what it does
try:
    main.earth_frame_png(year=1999, source="sentinel")
    fails.append("a year with no frame must 404")
except main.HTTPException as e:
    if "2016" not in str(e.detail):
        fails.append(f"the 404 must name the years this node has: {e.detail}")
try:
    main.earth_frame_png(year=2016, source="sentinel")
except Exception as e:  # noqa: BLE001
    fails.append(f"2016 exists and must be served: {type(e).__name__}")

# with nothing rendered at all, the 404 says which command makes them
for f in out.glob("*sentinel*"):
    f.unlink()
try:
    main.earth_frame_png(year=2016, source="sentinel")
    fails.append("with no frames at all, the route must 404")
except main.HTTPException as e:
    if "earth-engine timelapse" not in str(e.detail):
        fails.append(f"the empty 404 must name the command: {e.detail}")

print("\n".join(f"  x {f}" for f in fails) or
      "  earth frames: the glob finds a renamed node's frames, keeps the two records apart, and "
      "both 404s say what to do")
sys.exit(1 if fails else 0)
