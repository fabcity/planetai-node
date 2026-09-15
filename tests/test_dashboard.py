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

# --- the modular page: three files, one contract, ten sections -------------------------------------------------
#
# Rewritten 15 September 2026 with the page. Everything below used to assert the structure of the
# single-renderer page — its #hero, its Figures table, its Arrange mounts — and that page is gone.
# Each finding it was written from is re-made against the page that draws today; nothing was dropped
# because it was inconvenient to re-express.
_h = (ROOT / "app/static/index.html").read_text()
_css = (ROOT / "app/static/dashboard.css").read_text()

for _must in ('src="static/dashboard.js"', 'href="static/dashboard.css"', 'id="page"'):
    assert _must in _h, f"index.html lacks {_must}"
assert "<style" not in _h and "<script>" not in _h, \
    "index.html carries an inline style or script again — the page is three files, not one"

assert "window.PAI = { STAGES, register, render, wall, sections, problems, has }" in _js, \
    "dashboard.js no longer carries the page contract (kit-page.js) verbatim"
for _sec in ("'ground'", "'sensors'", "'satellite'", "'reticulum'", "'meshtastic'", "'hardware'",
             "'claims'", "'grain'", "'asks'", "'measure'"):
    assert f"id: {_sec}" in _js, f"dashboard.js no longer registers the section {_sec}"
assert "async function boot()" in _js and "/issues/fixtures/" in _js, \
    "dashboard.js boots from /issues and can replay a fixture with ?fixture="
# A style written from JavaScript cannot be read without running the page, and two sections used to.
assert "<style" not in _js and "createElement('style')" not in _js, \
    "no JS-injected styles in production: every module's CSS is in dashboard.css"
# Live tiles tell a tile server which square of the planet is being looked at. They are off unless a
# keeper turns them on, and the setting that turns them on is the only thing that may.
assert "tile.openstreetmap.org" not in _js or "MAP_TILES" in _js, \
    "live tiles are no longer gated on the MAP_TILES setting"

# ...and the page must be able to READ that setting. The line above is a string-proximity check: it
# passed for the whole of the branch while `window.SETTINGS.MAP_TILES` was undefined on every load,
# because GET /settings is describe() — {unlocked, runtime: [{key, value, …}], bootstrap: [...]} —
# and never a flat map. So the predicate was permanently false: no tile was ever requested at any
# setting, the two live bases were never offered, and the page printed "live tiles are off on this
# node" to a keeper who had just turned them on. This runs the page's own two functions against the
# real body of that endpoint, which is the only thing that could have caught it.
if shutil.which("node"):
    import settings as _settings          # the same module app/main.py serves GET /settings from

    def _lift(pattern, what):
        m = re.search(pattern, _js, re.S)
        assert m, f"dashboard.js no longer defines {what}"
        return m.group(0)

    _tiles_js = "\n".join((
        _lift(r"const PLAN_FROM = \d+;", "PLAN_FROM"),
        _lift(r"const tilesAllowed = \(res, settings\) =>.*?;", "tilesAllowed()"),
        _lift(r"const MASKED = '[^']*';", "MASKED"),
        _lift(r"function flatSettings\(d\) \{.*?\n\}", "flatSettings()"),
    ))
    _os_backup = {k: os.environ.get(k) for k in ("MAP_TILES", "TELEGRAM_BOT_TOKEN")}
    _bodies = {}
    for _tiles, _unlocked in (("on", False), ("on", True), ("off", False), (None, False)):
        if _tiles is None:
            os.environ.pop("MAP_TILES", None)
        else:
            os.environ["MAP_TILES"] = _tiles
        os.environ["TELEGRAM_BOT_TOKEN"] = "never-printed"   # a secret must stay masked either way
        _settings._cache["at"] = 0.0
        _bodies[f"{_tiles}-{'unlocked' if _unlocked else 'anonymous'}"] = \
            _settings.describe(unlocked=_unlocked, public=_settings.PUBLIC)
    for _k, _v in _os_backup.items():
        os.environ.pop(_k, None) if _v is None else os.environ.__setitem__(_k, _v)
    _settings._cache["at"] = 0.0

    _prog = (_tiles_js + "\nconst B = " + json.dumps(_bodies) + ";\n"
             + "const out = {};\nfor (const [k, body] of Object.entries(B)) {\n"
             + "  const flat = flatSettings(body);\n"
             + "  out[k] = { at8: tilesAllowed(8, flat), at9: tilesAllowed(9, flat),\n"
             + "             value: flat.MAP_TILES === undefined ? null : flat.MAP_TILES,\n"
             + "             secretLeaked: 'TELEGRAM_BOT_TOKEN' in flat,\n"
             + "             rowsKept: Array.isArray(flat.runtime) };\n}\n"
             + "console.log(JSON.stringify(out))")
    _t = json.loads(subprocess.run(["node", "-e", _prog], capture_output=True, text=True, check=True).stdout)

    assert _t["on-anonymous"]["value"] == "on", \
        f"MAP_TILES=on must reach window.SETTINGS unmasked for a reader with no token: {_t['on-anonymous']}"
    assert _t["on-anonymous"]["at8"] is True, \
        f"with MAP_TILES=on the page must offer and fetch tiles at resolution 8: {_t['on-anonymous']}"
    assert _t["on-anonymous"]["at9"] is False, \
        f"from resolution 9 inward the node's own plan fills the frame and sends nothing: {_t['on-anonymous']}"
    assert _t["on-unlocked"]["at8"] is True, "the same must hold with the admin token presented"
    assert _t["off-anonymous"]["at8"] is False and _t["None-anonymous"]["at8"] is False, \
        f"off, and unset, must both refuse a tile at every resolution: {_t}"
    # A masked value is not a value. Reading "•••• set" as a setting is how a secret becomes a switch.
    assert not any(v["secretLeaked"] for v in _t.values()), \
        f"a masked or secret key must not be flattened onto window.SETTINGS: {_t}"
    assert all(v["rowsKept"] for v in _t.values()), \
        "the runtime rows themselves must survive: the Set up pane and readLayout() read them"

# axe found nothing on any view or state, and these are the findings that had to hold for that.
#
# The page had no h1 at all (a <b> carried the node's name, so page-has-heading-one fired on every
# view in every state, and the wall has no header so it needed its own); a table that scrolls inside
# its own box could not be reached by keyboard; and --dim, at about 4:1 on paper, carried the small
# text that says where a number came from.
assert re.search(r'<h1 class="brand">', _js), "the node's name is not the page's h1 again"
assert re.search(r'<h1 class="vh">', _js), "the wall has no heading of its own; its header is display:none"
assert 'class="tblwrap" tabindex="0"' in _js, "the grain table cannot be scrolled from a keyboard again"
for _sel in (".readrow .who .m {", ".cellhead .n {", "[data-kind=\"readout\"] .src {"):
    _rule = _css[_css.index(_sel):_css.index("}", _css.index(_sel))]
    assert "--dim" not in _rule, f"{_sel.strip(' {')} is back on --dim, which is about 4:1 on paper"

# Arrange must actually arrange, and the view must be in the URL.
#
# Two of these shipped together on the page this replaces and each was invisible until somebody tried
# the mode: the ✕ silently did nothing on five of the nine bands, because render() skipped a hidden
# id and left the mount holding its last content; and the restore menu was markup only — `#arr-restore`
# appeared once in index.html and was never referenced, so a hidden band could only come back via
# Default, which discards every other choice. Both assertions point at the ported code.
#
# `want()` is where a hidden section goes: the view's own list is filtered before anything is drawn,
# so a hidden section is never emitted at all and cannot be left holding anything. Red if the filter
# goes, or if the view stops going through it.
assert "view.filter(id => !(LAYOUT.hidden || []).includes(id))" in _js, \
    "a section hidden in Arrange is no longer filtered out before the page is drawn — ✕ does nothing"
assert "only: want(NOW)" in _js and "only: want(NETWORK)" in _js, \
    "a view no longer goes through want(), so hiding a section has no effect on it"
# and the restore menu must be read, not just drawn. Red if fillRestore stops filling it or the
# change handler stops putting the section back.
assert "arr-restore" in _js, "the restore menu is markup nobody reads again; a hidden section cannot come back"
assert "function fillRestore()" in _js and "LAYOUT.hidden = (LAYOUT.hidden || []).filter(x => x !== id)" in _js, \
    "the restore menu no longer puts a hidden section back"

# The view must be in the URL, and it must get there without scrolling the page to an element.
assert "history.pushState" in _js, "the view is not in the URL: refresh, back and a shared link all land on Now"
assert not re.search(r"location\.hash\s*=", _js), \
    "assigning location.hash jumps to that element, which eats the scroll restore — use pushState"

# Every entry point into the token path must be listened for. They were drawn and dead once: the
# three cases below lived in the old page's global click listener, and the pane came across without
# them — so unlock() and saveSettings() were defined and unreachable, the gate never opened, and
# PAI_SETTINGS.set() could only ever throw for want of a token nothing could store.
for _case in ("ev.target.id === 'btn-unlock'", "ev.target.id === 'btn-save'",
              "ev.target.closest('[data-reveal]')"):
    assert _case in _js, f"the Set up pane has no handler for {_case} — the button is drawn and dead"

# And the page must read the household's language rather than pinning itself to English.
assert "(S.health || {}).locale" in _js, \
    "initKit no longer reads the locale off /health — the page is back to English on every node"

# And a refused page must say so on whichever surface is being drawn.
#
# At SHARE_LEVEL=off — the default, and what every beta tester has — the page gets 403 on /issues and
# nothing else. /health still answers, so the node's name and the nav are still there and the
# household's own sentence about why is drawn on the view they are standing on, the WALL included: a
# black shelf screen is read as a dead node, and "a blank page would be the node lying about being
# broken" is the renderer's own rule.
_refused = _js[_js.index("function drawRefused()"):]
_refused = _refused[:_refused.index("\n}") + 2]
for _mount in ("wallbox", "wrap"):
    assert f'"{_mount}' in _refused or f"class=\"{_mount}" in _refused, \
        f"the refused branch does not draw into .{_mount} — that view renders blank at SHARE_LEVEL=off"
assert "chrome(" in _refused, "a refused reader cannot reach the other views: the nav is not drawn"
# and the page must not claim a reading it does not have: the provenance word follows the fixture,
# and a refused page never reaches the lead at all.
assert re.search(r"S\.fixture \? pill\('cached'", _js), \
    "the lead's provenance pill no longer follows whether this is a fixture; it said `live` over a snapshot"

print("test_dashboard: the engine's fence holds at three stations, the page has none of its own, "
      "a hole in a series is a hole in the line, the page is three files carrying one contract and "
      "ten sections, and a refused page says so on the wall and in the nav")
