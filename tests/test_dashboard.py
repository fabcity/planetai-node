"""The ring's outlier fence, run out of the node that owns it.  PYTHONPATH=app python3 tests/test_dashboard.py

On 8 September node #1's card read "5 to 152 µg/m³": one neighbour was reading 152 while the rest read 5 to 12,
and the axis stretched to fit it until the box was a smear at the left edge. The fence decides which stations are
the neighbourhood and which are their own event.

Tukey's 1.5 x IQR is the usual answer and it fails here — with three stations reading 5, 10 and 152, the 152 IS
the upper quartile. A ring is often three or four stations, so this uses median absolute deviation instead. The
case that matters most is the last one: a real regional event, where every station reads high AND agrees, must
never be pinned away as an outlier.

The fence used to be JavaScript in app/static/index.html, where it trimmed a chart axis and nothing else, and
this suite lifted it out of the page with a regular expression and ran it in node. In Release 1 it moved to the
node as `issues.engine.fenced_median`, where every issue's ring column reads it, so this runs the real function
instead of a copy of the page's copy. The page no longer has a fence and must not grow one back.
"""
import json
import re
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "app"))

from issues.engine import fenced_median   # noqa: E402

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
out = {k: dict(zip(("median", "pinned"), fenced_median(v))) for k, v in CASES.items()}

assert out["node1"]["pinned"] == [152], f"node #1's 152 must be pinned off the ring: {out['node1']}"
# What "the axis ends near the other eight" became once the fence stopped drawing an axis: the number the ring
# column reports is the other seven's, not one dragged upward by the station having its own event. The plain
# mean of these eight is 26.6 and the plain median 9.5; the fenced median is 9, which is the street.
assert out["node1"]["median"] == 9, f"and the street must read as the other seven read: {out['node1']}"
assert out["three_one_wild"]["pinned"] == [152], \
    f"three stations is a normal ring here; the fence must still hold: {out['three_one_wild']}"
assert out["calm"]["pinned"] == [], f"an ordinary ring pins nothing: {out['calm']}"
# The MAD of a ring that agrees exactly is 0, and without the floor the fence would sit on the median itself and
# call every station its own outlier. 8 in, 8 out, nothing pinned.
assert out["identical"]["pinned"] == [] and out["identical"]["median"] == 8, \
    f"a ring that agrees exactly must not fence itself down to nothing: {out['identical']}"
assert out["regional_event"]["pinned"] == [], \
    ("smoke over the whole area must never be pinned away as an outlier — that is the one reading the household "
     f"most needs to see: {out['regional_event']}")

# And the page must not grow the fence back. It draws the ring's shape from what /nearby already answered; a
# median, a MAD or a fence appearing in dashboard.js is the computation walking back into the renderer.
_js = (ROOT / "app/static/dashboard.js").read_text()
_js = re.sub(r"/\*.*?\*/", " ", _js, flags=re.S)
_js = re.sub(r"(?m)^\s*//.*$", " ", _js)
for _word in ("mad", "fence"):
    assert not re.search(rf"\b{_word}\s*=", _js), f"dashboard.js computes a {_word} again — it belongs in the engine"

# A hole in a series must be a hole in the line.
#
# Both charts used to drop the nulls and join what was left, so a sensor that was off from 08:00 to 15:00 was drawn
# as one straight segment bridging the hole. Rendered against the committed fixture with seven hours nulled, the room
# trace ramped for six hours, CROSSED the WHO line the page judges against, and came back down: a threshold crossing
# that never happened, on the chart a household reads to decide whether to open a window. 17 real points were drawn
# as a 17-point line over 24 hours and nothing said which six were invented.
#
# Where a line breaks is drawing, not arithmetic, so `runs` lives in the page — and this lifts it out and runs it,
# the way this suite ran the fence before the fence moved to the engine.
if shutil.which("node"):
    _runs = re.search(r"const runs = \(vals, at\) => \{.*?\n\};", _js, re.S)
    assert _runs, "dashboard.js no longer defines runs() — the charts are joining across nulls again"
    _cases = {
        "a hole in the middle":   [1, 2, None, None, 5, 6],
        "the fixture's own case": [*range(8), *([None] * 7), *range(15, 24)],
        "no hole at all":         [1, 2, 3, 4],
        "one reading alone":      [None, 5, None],
        "nothing at all":         [None, None],
    }
    _prog = (_runs.group(0) + "\nconst at = (v, i) => [i, v];\n"
             + "console.log(JSON.stringify(Object.fromEntries(Object.entries("
             + json.dumps(_cases) + ").map(([k, v]) => [k, runs(v, at).map(r => r.length)]))))")
    _out = json.loads(subprocess.run(["node", "-e", _prog], capture_output=True, text=True, check=True).stdout)
    assert _out["a hole in the middle"] == [2, 2], f"one hole must give two lines, not one: {_out}"
    assert _out["the fixture's own case"] == [8, 9], \
        f"the seven nulled hours must split the day into 8 points and 9, not bridge into 17: {_out}"
    assert _out["no hole at all"] == [4], f"an unbroken day is still one line: {_out}"
    assert _out["one reading alone"] == [1], \
        f"a lone reading between two holes must survive as a run of one — dropping it loses a datum silently: {_out}"
    assert _out["nothing at all"] == [], f"a series with no readings draws nothing: {_out}"

# And a refused page must say so on whichever surface is being drawn.
#
# At SHARE_LEVEL=off — the default, and what every beta tester has — render()'s refused branch wrote
# the node's sentence into #hero and returned. body.wallview hides #hero, and the Network view never
# shows it, so the wall came up as 1920x1080 of nothing and Network as a header over an empty page.
# Both are surfaces nobody is standing at to work out why. A household reads a black shelf screen as
# a dead node, which is the exact thing the renderer's own comment has always forbidden: "a blank page
# would be the node lying about being broken".
#
# This is a static proxy for a rendered check. The real test drives a browser against a node at `off`
# and asserts each view carries the sentence; the suite has no browser and is not getting one for
# this, so it asserts the branch names all three mounts. If the branch is ever rewritten, write the
# rendered version rather than deleting this.
_refused = _js[_js.index("if (snap.refused)"):]
_refused = _refused[:_refused.index("\n  }") + 4]
for _mount in ("hero", "wallbox", "netbody"):
    assert f"'{_mount}'" in _refused or f'"{_mount}"' in _refused, \
        f"the refused branch does not draw into #{_mount} — that view renders blank at SHARE_LEVEL=off"
# and it must not claim a reading it does not have
assert re.search(r"snap\.refused\s*\?\s*''", _js), \
    "the header's provenance pill is computed without asking whether the page was refused; it said `live` over nothing"

print("test_dashboard: the engine's fence holds at three stations, the page has none of its own, "
      "a hole in a series is a hole in the line, and a refused page says so on the wall and the network view")
