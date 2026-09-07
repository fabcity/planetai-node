"""The ring strip's outlier fence, run out of app/static/index.html itself.  python3 tests/test_dashboard.py

On 8 September node #1's card read "5 to 152 µg/m³": one neighbour was reading 152 while the rest read 5 to 12,
and the axis stretched to fit it until the box was a smear at the left edge. The fence decides where the axis
stops and which stations are pinned beyond it.

Tukey's 1.5 x IQR is the usual answer and it fails here — with three stations reading 5, 10 and 152, the 152 IS
the upper quartile. A ring is often three or four stations, so this uses median absolute deviation instead. The
case that matters most is the last one: a real regional event, where every station reads high AND agrees, must
never be pinned away as an outlier.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "app/static/index.html").read_text()

if not shutil.which("node"):
    print("  - dashboard fence check skipped (no node)")
    sys.exit(0)

# the real lines, lifted from the page rather than retyped. If drawRing is rewritten this fails loudly, which is
# the point: the fence is the thing being checked, not a copy of it.
med = re.search(r"^\s*(const med=v=>\{.*?\};)\s*$", html, re.M)
fence = re.search(r"^\s*const pv=seen\.map\(r=>r\.pm25\), m0=med\(pv\);\s*\n"
                  r"\s*(const mad=.*?)\s*\n\s*(const fence=.*?)\s*$", html, re.M | re.S)
assert med and fence, "drawRing's fence could not be found in index.html — was it rewritten?"

harness = f"""
{med.group(1)}
function verdict(pv){{
  const m0 = med(pv);
  {fence.group(1)}
  {fence.group(2)}
  return {{median: m0, fence: fence, pinned: pv.filter(x => x > fence)}};
}}
const cases = JSON.parse(process.argv[1]);
console.log(JSON.stringify(Object.fromEntries(
  Object.entries(cases).map(([k, v]) => [k, verdict(v)]))));
"""

CASES = {
    # node #1's own card, 8 September: one station at 152, the rest ordinary
    "node1": [152, 5, 10, 6, 9, 11, 8, 12],
    # the small ring Tukey cannot handle: with n=3 the wild value is itself the upper quartile
    "three_one_wild": [5, 10, 152],
    "calm": [5, 7, 9, 10, 11, 12],
    "identical": [8, 8, 8, 8],
    # every station high AND agreeing. This is smoke over the whole area — `everywhere`, not an outlier.
    "regional_event": [40, 44, 38, 47, 41, 39],
}
out = json.loads(subprocess.run([shutil.which("node"), "-e", harness, json.dumps(CASES)],
                                capture_output=True, text=True, check=True).stdout)

assert out["node1"]["pinned"] == [152], f"node #1's 152 must be pinned off the scale: {out['node1']}"
assert out["node1"]["fence"] < 25, f"and the axis must end near the other eight, not near 152: {out['node1']}"
assert out["three_one_wild"]["pinned"] == [152], \
    f"three stations is a normal ring here; the fence must still hold: {out['three_one_wild']}"
assert out["calm"]["pinned"] == [], f"an ordinary ring pins nothing: {out['calm']}"
assert out["identical"]["pinned"] == [] and out["identical"]["fence"] > 8, \
    f"a ring that agrees exactly must not collapse the axis onto itself: {out['identical']}"
assert out["regional_event"]["pinned"] == [], \
    ("smoke over the whole area must never be pinned away as an outlier — that is the one reading the household "
     f"most needs to see: {out['regional_event']}")

print("test_dashboard: the ring's axis ends past its neighbours, not past its worst one")
