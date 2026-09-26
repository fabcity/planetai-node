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

def _node(prog):
    """Run a JS program through node, with the program on STDIN and never in argv.

    Linux caps a single argument at 128 KiB (MAX_ARG_STRLEN) and macOS does not, so a program
    that outgrew that limit passed on every dev machine and failed only in CI, with `OSError:
    [Errno 7] Argument list too long: 'node'` and no hint that the size was the reason. It
    failed that way from v0.68. The program is a lifted function plus a JSON blob of settings,
    and the blob grows every time a setting is added, so argv was always going to be outgrown.
    tools/check_ui.py already reads its input this way."""
    r = subprocess.run(["node"], input=prog, capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


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
    _out = _node(_prog)
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
    _t = _node(_prog)

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

    # STATIONS_SHOWN, read the same way and for the same reason. The list draws this node's own
    # hardware plus the nearest N of everybody else's, so the keeper's number has to survive the
    # same trip MAP_TILES did not: GET /settings is describe(), never a flat map, and this runs the
    # page's own capOf() against that endpoint's real body rather than against a map written here.
    #
    # The two that are not about plumbing: a blank value is the default, not "no cap" (a node that
    # has never touched the setting must not get a fourteen-row list), and an unreadable one is the
    # default, not zero and not an empty neighbourhood (a typo in a settings box may not blank the
    # section). 0 alone means every station.
    _cap_js = "\n".join((
        _lift(r"const STATIONS_DEFAULT = \d+;", "STATIONS_DEFAULT"),
        _lift(r"const capOf = \(settings\) =>.*?\n\};", "capOf()"),
        _lift(r"const MASKED = '[^']*';", "MASKED"),
        _lift(r"function flatSettings\(d\) \{.*?\n\}", "flatSettings()"),
    ))
    _sb = os.environ.get("STATIONS_SHOWN")
    _caps = {}
    for _v in ("3", "7", "0", "", "nine"):
        if _v == "":
            os.environ.pop("STATIONS_SHOWN", None)
        else:
            os.environ["STATIONS_SHOWN"] = _v
        _settings._cache["at"] = 0.0
        _caps[_v or "unset"] = _settings.describe(unlocked=False, public=_settings.PUBLIC)
    os.environ.pop("STATIONS_SHOWN", None) if _sb is None else os.environ.__setitem__("STATIONS_SHOWN", _sb)
    _settings._cache["at"] = 0.0

    _c = _node(_cap_js + "\nconst B = " + json.dumps(_caps) + ";\n"
                + "const out = {};\nfor (const [k, body] of Object.entries(B)) "
                + "out[k] = capOf(flatSettings(body));\nconsole.log(JSON.stringify(out))")

    assert _c["3"] == 3 and _c["7"] == 7, f"the keeper's number must reach the page: {_c}"
    assert _c["0"] is None, f"0 lists every station: {_c}"
    assert _c["unset"] == 3, f"a node that never set it lists three, not all fourteen: {_c}"
    assert _c["nine"] == 3, f"an unreadable value is the default, never an empty neighbourhood: {_c}"

# The grain section's flat run is READ OFF the table, never written down.
#
# It shipped as `filter(g => g.occupied === 9)` -- node #1's own flat run as a literal -- and on the
# live node proved on 16 September 2026 (no stations, every row zero) `flat[0].res` threw and the
# whole decide stage printed "grain did not render". A literal that happens to be true of one node
# is the thing this assertion exists to keep out.
assert "g.occupied === 9" not in _js, \
    "the grain section is back on node #1's own occupied count as a literal; it must read the table"
assert "function flatRun(H)" in _js, "the grain section no longer derives its flat run"
if shutil.which("node"):
    _run = _lift(r"function flatRun\(H\) \{.*?\n\}", "flatRun()")
    _tables = {
        # node #1, 6 September: nine cells from resolution 9 inward and never again
        "node1": [{"res": r, "occupied": 1 if r < 4 else 9 if r >= 9 else r} for r in range(2, 13)],
        # a node with no station that carries a coordinate: every row zero, and no finding to make
        "empty": [{"res": r, "occupied": 0} for r in range(2, 13)],
        # a node still splitting cells at the finest stop: no flat run either, for the other reason
        "busy": [{"res": r, "occupied": r} for r in range(2, 13)],
    }
    _f = _node(_run + "\nconst T = " + json.dumps(_tables) + ";\nconst out = {};\n"
                + "for (const [k, grain_table] of Object.entries(T)) "
                + "out[k] = flatRun({ grain_table }).map(r => r.res);\nconsole.log(JSON.stringify(out))")
    assert _f["node1"] == [9, 10, 11, 12], f"the flat run must be the tail that stops changing: {_f}"
    assert _f["empty"] == [], f"every row zero is an empty node, not a finding about grain: {_f}"
    assert _f["busy"] == [], f"a count still changing at the finest stop has no flat run: {_f}"

# NOTHING READS THE URL AT MODULE SCOPE, EXCEPT THE FIXTURE.
#
# `const Q = new URLSearchParams(location.search)` at the top level of the nav module was correct for
# as long as every press reloaded the document: the module ran again and the capture was the new URL.
# When v0.55 made a press a re-render, that line became a snapshot of the query the page was FIRST
# opened with, and where() kept answering with the opening cell and resolution — so the dial and every
# cell link changed the URL and nothing else. Zero requests, five milliseconds, and the same page.
#
# No static check saw it and neither did the visual gate, which measures one render. tests/visual/
# measure.mjs gained a `press` command for the behaviour; this is the rule, which needs no browser.
_load_reads = re.findall(r'^(?:const|let|var)\s+(\w+)\s*=\s*new URLSearchParams\(location\.search\)', _js, re.M)
assert set(_load_reads) <= {"FIXTURE"}, (
    f"{sorted(set(_load_reads) - {'FIXTURE'})} capture(s) location.search at module scope. A press is a "
    "re-render now, so a load-time capture is frozen at whatever the page was opened with and the "
    "control it feeds goes dead. Read it at call time — see query() in dashboard.js.")
assert "const query = () => new URLSearchParams(location.search)" in _js, \
    "query() is gone — where() is reading the URL from somewhere that may be stale"

# SET UP OFFERS WHAT `planetai config` OFFERS — every group, every key, the node's own words.
#
# Both read settings.describe(); the CLI walks its groups and prints every key in each. The pane
# filters the same rows by group — except the packs branch, which rendered a list of pack switches
# and returned, so PACKS_ENABLED and PACKS_ALLOW_CODE existed in the CLI and nowhere in the
# dashboard. A keeper who read one and went looking in the other did not find them.
#
# The group tab is also the node's own word for the group, because that is the word `planetai config`
# prints and a keeper moves between the two surfaces.
import settings as _s                                     # the module both surfaces read
_groups = []
for _r in _s.describe(unlocked=False, public=_s.PUBLIC)["runtime"]:
    if _r["group"] not in _groups:
        _groups.append(_r["group"])
_gm = re.search(r"const GROUPS = \{(.*?)\n\};", _js, re.S)
assert _gm, "the Set up pane no longer declares GROUPS"
_titled = dict(re.findall(r"^\s*(\w+):\s*\['([^']*)'", _gm.group(1), re.M))
for _g in _groups:
    assert _g in _titled, f"the node declares the settings group {_g!r} and the Set up pane has no tab for it"
    assert _titled[_g].lower() == _g.lower(), (
        f"the {_g!r} tab is labelled {_titled[_g]!r}; `planetai config` prints {_g!r}, and the two "
        "menus are meant to read alike")
# No group may render instead of its keys. One early return is allowed and is bootstrap, which is
# read-only by nature; everything else falls through to the row loop.
assert "extra = PACKS.map" in _js and "pane.innerHTML = PACKS.map" not in _js, \
    "the packs group renders switches instead of its own two settings again"
assert "pane.innerHTML = extra + rows.map(r => {" in _js, \
    "a group's keys are no longer rendered after whatever extra that group adds"

# AN UNKNOWN HASH IS AN ANCHOR ON THIS PAGE, NOT A VIEW.
#
# readView() took the hash as the view whatever it said. The lead's own ask line links to
# `#stage-act` — it is what a reader presses when the page says "94 asks open · in 3 Act" — so the
# page routed to a view called `stage-act`, found none, fell through to the branch that draws Set up,
# and rendered a band titled STAGE-ACT with nothing in it. A blank page, reached from the page's own
# link, on a household's node. Every in-page anchor did it: the notes band links back to the section
# each note explains, and so does this one.
#
# Reported by Tomas from node #1 at v0.71, which is the release this fixes.
assert "const VIEW_NAMES = new Set(" in _js, \
    "readView no longer has a list of what a view IS, so any hash is one again"
assert re.search(r"VIEW = \(VIEW_NAMES\.has\(h\) \? h : ''\) \|\| q\.get\('view'\) \|\| 'now'", _js), \
    ("an unknown hash is being taken as a view again — `#stage-act` empties the page, and so does "
     "every link in the notes band")
# Every hash the page itself writes must either name a view or name an element it draws.
_names = set(re.findall(r"'(now|historical|network|wall|arrange|setup)'",
                        re.search(r"const VIEW_NAMES = new Set\(\[(.*?)\]\)", _js, re.S).group(1)))
assert _names == {"now", "historical", "network", "wall", "arrange", "setup"}, \
    f"VIEW_NAMES and the six views have drifted apart: {sorted(_names)}"
# The one literal anchor the page writes is the lead's, and the element it points at is built from
# a template — `id="stage-${key}"` — so there is no literal to grep for. Assert the pair instead:
# the link, and the template that makes its target. The rig checks the live page lands on it.
assert 'href="#stage-act"' in _js, "the lead no longer links to the Act stage"
assert 'id="stage-${key}"' in _js, \
    "the stages no longer carry an id, so the lead's link to #stage-act lands nowhere"
# And an anchor must not throw the page away: same view, so scroll rather than re-render.
assert "if (VIEW === before)" in _js and "scrollIntoView({ block: 'start' })" in _js, \
    ("a hashchange that does not change the view re-renders the whole page, which loses the scroll "
     "position, the open folds and the learn panel for a link to somewhere already on screen")

# THE PAGE KEEPS UP WITH THE NODE, AND SAYS SO WHEN IT CANNOT.
#
# v0.53 ended its boot with `setInterval(refresh, 20000)`. The Phase 2 rewrite did not carry it, and
# for four releases the only repeating timer in this file was the wall stepping its own dial: boot()
# fetched once and the page then showed a `live` pill over figures that had stopped moving when the
# tab opened. Nothing caught it — every check here measures one render, and one render of a frozen
# page looks exactly like one render of a fresh one. These are the assertions that would have.
assert "function refresh()" in _js and "setInterval(refresh, refreshEvery())" in _js, \
    "the page no longer re-fetches on a timer — it will show the readings it booted with, forever"
_bootline = _js[_js.index("boot().then("):]
_bootline = _bootline[:_bootline.index("\n")]
assert "startRefresh()" in _bootline, "boot no longer starts the refresh loop"
assert "route()" in _bootline and "init()" in _bootline, "boot no longer draws the page"

# THE LOADING STATE PLAYS ON THREE THINGS AND A POLL IS NOT ONE OF THEM.
#
# `asking` covers the page. A poll fires every POLL_SECONDS on a page somebody is reading, so an
# overlay on every poll would make a node that is working perfectly look like one that is stuck —
# and it would do it every five minutes, on a wall, unattended. The rule is in prompt 6 and it is one
# line of code away from being broken by accident, so it is asserted here rather than remembered.
assert "ASKING.close()" in _bootline, "the loading state is never taken down after the first paint"
_ask = _js[_js.index("async function refresh()"):_js.index("function redraw(opts)")]
assert "ASKING.open" in _ask, "refresh() never plays the loading state, so a reconnect is silent"
for _line in _ask.splitlines():
    _code = _line.split("//")[0]
    if "ASKING.open" in _code:
        assert "mine" in _code or "STALE" in _code, \
            ("refresh() plays the loading state unconditionally, so it plays on every poll: "
             + _code.strip())
assert "const wasStale = !!window.STALE" in _ask and "mine = wasStale" in _ask, \
    "refresh() no longer decides between a reconnect and a poll before playing the loading state"
# And the header's control is a different function on purpose: if ↻ were refresh() with the overlay
# bolted on, the timer would inherit it the next time somebody edited either one.
assert "async function askAgain()" in _js and "ASKING.open('Asking the node again'" in _js, \
    "the header's re-ask no longer has a function of its own"
# THE FLOOR, AND THE TWO MOMENTS THAT ASK FOR IT.
#
# What the loading state says is the page's account of what it asked of the world — the endpoints and
# the milliseconds each took — and on a fixture the node answers in under a tenth of a second, so
# without a floor nobody ever read it. A reload and the header's ↻ are the two moments a PERSON
# asked to see it; a reconnect is not, because there the page coming back is the thing wanted and a
# delay is only a delay. So exactly those two pass `true`.
assert "ASKING.open('Asking the node', true)" in _js, "a reload no longer holds the loading state"
assert "ASKING.open('Asking the node again', true)" in _js, "the ↻ no longer holds it"
assert re.search(r"ASKING\.open\('The node stopped answering[^)]*\)(?!\s*,\s*true)", _js), \
    "a reconnect now holds the page for the floor, which delays the answer a reader is waiting for"
assert "window.K.msToken('--motion-asking-hold')" in _js, \
    "the floor is no longer read from the layer's own token"
# What it may and may not ask for again. /settings, /earth, /sensors, /cells and the plan do not move
# on the node's poll; re-fetching them every cycle is traffic for no change.
_ref = _js[_js.index("async function refresh()"):_js.index("function redraw(opts)")]
for _route in ("'/issues'", "'/health'"):
    assert _route in _ref, f"refresh() no longer re-reads {_route}"
for _route in ("'/settings'", "'/earth'", "'/sensors'", "'/cells'", "'/place/geojson'"):
    assert _route not in _ref, \
        f"refresh() re-reads {_route} on every poll; it does not change on the node's cadence"
# A fixture is a committed snapshot and cannot change. The measuring rig replays one, so a refresh
# here would also re-fetch underneath a running measurement.
assert "if (FIXTURE || STATE !== 'populated') return;" in _ref, \
    "refresh() no longer refuses to poll a replayed fixture or a synthetic state"
# The cadence is the node's own, not a number typed into the page.
assert "POLL_SECONDS" in _js, "the refresh cadence is no longer read from the node's own poll interval"
# And the one that matters: a failed poll must reach the stamp. Saying `live` over figures nothing is
# refreshing is the fault this whole block exists for.
assert "window.STALE" in _js and "pill('stale'" in _js, \
    "a failed poll no longer reaches the page — the live pill would sit over stale figures again"
assert "the node has not answered for" in _js, \
    "the as-of stamp no longer says how long the node has been silent"

# A POLL DOES NOT ASK A TILE SERVER ANYTHING.
#
# Assigning innerHTML queues an <img> load the instant the markup exists, so a redraw goes to the
# network even for a tile the browser has cached. Measured over CDP while building the refresh loop:
# twelve requests to tiles.maps.eox.at per redraw, none from cache, though the tiles carry max-age of
# a week. At one poll per 300 s that is ~3,500 a day from every open page, each telling that server
# which square of the planet this house is looking at. The rule since Phase 2 is that a press may
# only ever REDUCE what leaves the house; a poll multiplying it by three hundred breaks it from the
# other side. After the gate: 12 on first load, 0 on every poll after.
assert "if (window.KEEP_GROUND) return '';" in _js, \
    "the tile figure no longer refuses to redraw for a data poll — every poll will re-ask the tile server"
assert "if (ground) window.KEEP_GROUND = true;" in _js and "finally { window.KEEP_GROUND = false; }" in _js, \
    "redraw() no longer raises the keep-ground flag across route(), or no longer lowers it after"
# Only a data poll may set it. A press changes the cell or the resolution and MUST draw a new map.
_rd = _js[_js.index("function redraw(opts)"):]
_rd = _rd[:_rd.index("\n}") + 2]
assert "opts && opts.keepGround" in _rd, "redraw() keeps the ground unconditionally — a press would not redraw the map"

# THE RAIL IS NOW'S CONTROL. It was the dial, drawn under every view's header until 18 September,
# where on Network, Historical and Set up nothing on the page answered to it. Arrange keeps it: it
# draws Now's own sections through want(NOW), so taking it away there left seven of them — the
# ground, the station groups, the claims, the grain and the grain line — pointing at a control that
# was not on the page. Renamed to the rail on 21 September when it became the top instrument (design
# log R14); the wall keeps its own dial, which is a different control on a different surface.
assert "VIEW === 'now' || VIEW === 'arrange'" in _js and 'class="railwrap"' in _js, \
    "the rail is no longer drawn for Now and Arrange, or is drawn for every view again"
assert re.search(r"const ref = 'grain-line';", _js), \
    "the rail's link out is back to being chosen per view; only Now draws it now"
# The zones are texture, not hue (design log R14). The cells blue has one meaning — a cell — and a
# 12% wash of it for "may leave this machine" spent it on a second, vanished for a reader who cannot
# separate blue from grey, and went white on a printed plate.
assert not re.search(r"\.rail a\.leaves\s*\{[^}]*--cells", _css), \
    "the rail's may-leave zone is back to a wash of the cells blue; it is a dot screen"
assert re.search(r"\.rail a\.leaves\s*\{[^}]*radial-gradient", _css), \
    "the rail's may-leave zone has lost its texture, so the three zones are two"
assert 'data-component="rail"' in _js and 'data-kind="row"' in _js, \
    "the rail no longer declares itself a component of a card kind the page is held to"
assert 'data-ref="dial"' not in _js, \
    "something still points at a component called dial; on Now it is the rail, and T5 counts orphans"

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
for _v in ("NOW", "NETWORK", "HISTORICAL"):
    assert f"want([...{_v}" in _js or f"want({_v})" in _js, \
        f"the {_v} view no longer goes through want(), so hiding a section has no effect on it"

# A SECTION THE PAGE HAS NEVER HEARD OF HAS TO GO SOMEWHERE.
#
# One registry serves three views through three hardcoded arrays of ids. A pack's section is an id
# this file has never seen — that is the whole point of the contract, and the docstring at the top of
# dashboard.js promises it in as many words. From the Now/Network split until 22 September a
# registered section not typed into one of those arrays was filtered out of all three and drawn
# nowhere: it registered, Set up listed it as `drawing`, and it was on no page. Now is the default
# home for anything the two named lists do not claim, and this is the line that says so.
assert "const homeless = PAI.sections.map(s => s.id).filter(id => !placed.has(id))" in _js, \
    ("a registered section that no view names is filtered out of every view again, so a pack can "
     "register a section and have it drawn nowhere — which is the contract this page publishes")
assert "want([...NOW, ...homeless])" in _js, \
    "Now is no longer the default home for a section no view names"
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

# --- the mode, read the way MAP_TILES was not ------------------------------------------------------------------
#
# UI_MODE decides whether the page draws every section or four sentences, so a page that cannot read
# it opens in the wrong one for every household that set it. That is exactly the MAP_TILES bug forty
# lines up: GET /settings is describe() — {unlocked, runtime: [{key, value, ...}], bootstrap: [...]}
# — never a flat map, and a proximity check would pass while `window.SETTINGS.UI_MODE` was forever
# undefined. So this runs the page's own mode() against that endpoint's real body.
#
# The precedence is the other half: `?mode=` for the rig and for a link one person sends another,
# then this browser's own choice, then what the household set the node to. A reader switching must
# not rewrite the node, and the node must not overrule a reader who has switched.
if shutil.which("node"):
    _mode_js = "\n".join((
        _lift(r"const MODE_KEY = '[^']*';", "MODE_KEY"),
        _lift(r"const MODES = \[.*?\];", "MODES"),
        _lift(r"const isMode = .*?;", "isMode()"),
        _lift(r"const SHORT_VIEW = new Set\(\[.*?\]\);", "SHORT_VIEW"),
        _lift(r"function mode\(view\) \{.*?\n\}", "mode()"),
        _lift(r"function modeRaw\(\) \{.*?\n\}", "modeRaw()"),
    ))
    _mode_bodies = {}
    _mb = os.environ.get("UI_MODE")
    for _v in ("simple", "learn", "", "sideways"):
        os.environ["UI_MODE"] = _v
        _settings._cache["at"] = 0.0
        _mode_bodies[_v or "unset"] = _settings.describe(unlocked=False, public=_settings.PUBLIC)
    os.environ.pop("UI_MODE", None) if _mb is None else os.environ.__setitem__("UI_MODE", _mb)
    _settings._cache["at"] = 0.0

    _cases = {
        # name                 node setting   this browser   the URL
        "node_simple":        ("simple",      None,          ""),
        "node_learn":         ("learn",       None,          ""),
        "node_unset":         ("unset",       None,          ""),
        "node_garbage":       ("sideways",    None,          ""),
        "browser_overrides":  ("simple",      "learn",       ""),
        "url_overrides_both": ("simple",      "learn",       "?mode=advanced"),
        "url_garbage":        ("simple",      None,          "?mode=sideways"),
        "storage_blocked":    ("learn",       "THROW",       ""),
    }
    _prog = (_mode_js + "\nconst B = " + json.dumps(_mode_bodies)
             + ";\nconst C = " + json.dumps(_cases) + ";\nconst out = {};\n"
             + "for (const [name, [setting, mine, search]] of Object.entries(C)) {\n"
             + "  globalThis.window = { SETTINGS: B[setting] };\n"
             + "  globalThis.location = { search };\n"
             + "  globalThis.localStorage = mine === 'THROW'\n"
             + "    ? { getItem() { throw new Error('site data blocked'); } }\n"
             + "    : { getItem: k => (k === MODE_KEY && mine !== null ? mine : null) };\n"
             + "  try { out[name] = mode(); } catch (e) { out[name] = 'THREW: ' + e.message; }\n"
             + "}\nconsole.log(JSON.stringify(out))")
    _m = json.loads(subprocess.run(["node", "-e", _prog], capture_output=True, text=True,
                                   check=True).stdout)

    assert _m["node_simple"] == "simple", \
        f"UI_MODE must reach the page through describe()'s runtime rows, not a flat map: {_m}"
    assert _m["node_learn"] == "learn", f"every value the setting allows must arrive: {_m}"
    # A VIEW WITH NO SHORT ANSWER DRAWS THE FULL ONE, whatever this browser last chose.
    #
    # Simple is the short version of what a view reports, and three views do not report: Set up is a
    # form, Arrange is a mode for moving sections about, and the Wall is already one screen at three
    # metres with no header to put a control in. Before this, a reader who chose Simple on Now and
    # then opened Arrange got the digest, no sections at all, and a bar offering to reorder them.
    # The stored choice is not rewritten — going back to Now restores it — so both halves are here.
    _vprog = (_mode_js + ";\nglobalThis.window = { SETTINGS: { runtime: [] } };\n"
              + "globalThis.location = { search: '' };\n"
              + "globalThis.localStorage = { getItem: k => (k === MODE_KEY ? 'simple' : null) };\n"
              + "const out = {}; for (const v of ['now','historical','network','setup','arrange','wall',undefined])\n"
              + "  out[String(v)] = mode(v);\nconsole.log(JSON.stringify(out))")
    _v = json.loads(subprocess.run(["node", "-e", _vprog], capture_output=True, text=True,
                                   check=True).stdout)
    for _view in ("now", "historical", "network"):
        assert _v[_view] == "simple", \
            f"{_view} reports something, so it must honour a reader's Simple: {_v}"
    for _view in ("setup", "arrange", "wall"):
        assert _v[_view] == "advanced", \
            (f"{_view} has no short answer to give, so Simple must not follow a reader onto it — "
             f"on Arrange it took every section away and left the bar with nothing to arrange: {_v}")
    assert _v["undefined"] == "simple", \
        f"asked without a view, mode() must still answer what this browser chose: {_v}"

    assert _m["node_unset"] == "advanced", \
        f"a node that never set it opens on the whole page, not on four sentences: {_m}"
    assert _m["node_garbage"] == "advanced", \
        f"an unreadable setting is the default, never a blank page: {_m}"
    assert _m["browser_overrides"] == "learn", \
        f"a reader who switched keeps their choice over the node's: {_m}"
    assert _m["url_overrides_both"] == "advanced", \
        f"?mode= is what the rig and a shared link use, and it wins: {_m}"
    assert _m["url_garbage"] == "simple", \
        f"a nonsense ?mode= falls through to the node rather than to the default: {_m}"
    assert _m["storage_blocked"] == "learn", \
        f"a browser with site data blocked still renders; it just cannot remember: {_m}"

# The digest is drawn in simple mode and the node writes it. Both halves matter: a page that
# composed its own four sentences would be the renderer making a claim about the household's data.
assert "function digest(ctx)" in _js, "dashboard.js no longer draws the digest"
assert re.search(r"const d = \(ctx\.S\.issues \|\| \{\}\)\.digest", _js), \
    "the digest is no longer READ from /issues — if the page is composing those sentences, stop"
assert re.search(r"simple && onNow \? digest\(ctx\) : ''", _js), \
    "simple mode no longer draws the digest in place of the sections it hides"
# AND ONLY ON NOW. The digest is four sentences about this hour. It was drawn on every view in
# simple mode, so Historical and Network each answered "what is the air doing right now" under a
# heading about the years and about the network, with no sections under them because none of theirs
# opted into simple: 652 characters, not one about the view the reader had asked for. A short answer
# to the wrong question is worse than a long answer to the right one.
assert re.search(r"const onNow = !opts\.only \|\| opts\.only\.includes\('matrix'\)", _js), \
    "the digest is no longer confined to Now, so the other views answer a question nobody asked"
# Each of the other two names its own short answer instead, which is the section the pack says leads
# that view: the satellite loop on Historical, the network map on Network.
for _sec in ("satellite", "netmap"):
    _blk = _js[_js.index(f"id: '{_sec}'"):]
    assert "level: 'simple'" in _blk[:400], \
        f"{_sec} no longer opts into simple, so its view has no short answer to give"
assert "level: 'advanced'" in _js, \
    "the section contract lost its default level, so every section would vanish in simple mode"

# --- what a node publishes, usable from its own page ------------------------------------------------
# Every band names the routes its data came from, and the shell prints them beside the kicker as
# links. check_ui.py checks each route exists; this checks every section carries some and that the
# shell draws them in their own case rather than inside the shouted kicker text.
_js_raw = (ROOT / "app/static/dashboard.js").read_text()
_heads = re.findall(r"^window\.PAI\.register\(\{(.*?)\n  (?:render|lead|controls|wall|notes)\b", _js_raw,
                    re.S | re.M)
assert len(_heads) == len(re.findall(r"^window\.PAI\.register\(\{", _js_raw, re.M)) >= 24, \
    "a registration the test cannot read the fields of, or fewer than the 24 sections this page draws"
for _h in _heads:
    _sid = re.search(r"\bid:\s*'([^']+)'", _h).group(1)
    _r = re.search(r"\breads:\s*\[([^\]]*)\]", _h)
    assert _r and re.findall(r"'(/[^']*)'", _r.group(1)), f"section '{_sid}' does not say which routes it reads"
assert re.search(r'<span class="routes">\$\{s\.reads\.map\(r => `<a href="\$\{esc\(r\)\}">GET \$\{esc\(r\)\}</a>`\)', _js_raw), \
    "the shell no longer prints a band's routes as links beside its kicker"
assert re.search(r"\.band > \.k \.routes \{[^}]*text-transform: none", (ROOT / "app/static/dashboard.css").read_text()), \
    "a band's routes inherit the kicker's uppercase, and a route uppercased cannot be typed back"

# The ledger's note that said the node had no `decided` stage. It has had one since the Decide card.
assert "ledger-no-decision" not in _js_raw and "No stage for a decision" not in _js_raw, \
    "the ledger's note saying there is no decided stage is back, and it is false"

# The registry band sends a reader to the documentation's "Adding a source". The anchor is what
# tools/build_docs.py makes of that heading; a renamed heading is a link to the top of a page.
_anchor = re.search(r"const ADD_A_SOURCE = 'https://planetai\.fab\.city/docs/sources/#([a-z0-9-]+)';", _js_raw)
assert _anchor, "the registry band no longer links to the documentation's steps for adding a source"
_slug = lambda t: re.sub(r"[\s_-]+", "-", re.sub(r"[^\w\s-]", "", t.lower()).strip())   # build_docs.slugify_for("")
_heads_md = [_slug(h) for h in re.findall(r"^#{2,3} (.+)$", (ROOT / "docs/site/sources.md").read_text(), re.M)]
assert _anchor.group(1) in _heads_md, f"#{_anchor.group(1)} is not a heading of docs/site/sources.md: {_heads_md}"

# A provenance word signs.svg has no symbol for is printed as the word, never as an empty square.
_svg = (ROOT / "app/static/signs.svg").read_text()
_signs = re.search(r"const PROV_SIGNS = new Set\(\[([^\]]*)\]\);", _js_raw)
assert _signs, "pill() no longer says which provenance words the sprite draws"
for _w in re.findall(r"'([a-z]+)'", _signs.group(1)):
    assert f'id="sign-prov-{_w}"' in _svg, f"PROV_SIGNS names {_w}, which signs.svg does not draw"

if shutil.which("node"):
    _pill = _node("\n".join((
        re.search(r"const esc = s => .*?\);\n", _js_raw, re.S).group(0),
        _signs.group(0),
        re.search(r"const pill = \(word, note = ''\) => \{.*?\n\};", _js_raw, re.S).group(0),
        "console.log(JSON.stringify({ stale: pill('stale', 'x'), live: pill('live') }))")))
    assert "<use" not in _pill["stale"] and "stale" in _pill["stale"], \
        f"pill('stale') must print the word with no sign, since signs.svg has none: {_pill['stale']}"
    assert "sign-prov-live" in _pill["live"], f"pill('live') lost its sign: {_pill['live']}"

    # "I did this" and "Record the decision" print what the node said when it refused, word for
    # word. It printed "The node refused it (409)" over a node that had written, in full, what to
    # do first (DECISION_REQUIRED) — the one sentence the person at the screen needed.
    _did = "\n".join((
        re.search(r"async function nodeSaid\(r\) \{.*?\n\}", _js_raw, re.S).group(0),
        re.search(r"async function didThis\(form\) \{.*?\n\}", _js_raw, re.S).group(0),
    ))
    _409 = ("this node is set to DECISION_REQUIRED, so an act needs a decision recorded against the same "
            "alert first. Decide on the dashboard, then record what you did.")
    _cases = {
        "409": [409, {"detail": _409}],
        "400": [400, {"detail": "stage must be acknowledged, acted or decided"}],
        "401": [401, {"detail": "closing a loop from off this machine needs Authorization: Bearer <ACT_TOKEN>"}],
        "403": [403, {"error": "this node is not sharing"}],
        "500": [500, None],
        "422": [422, {"detail": [{"msg": "field required"}]}],
    }
    _t = _node(_did + "\nconst C = " + json.dumps(_cases) + r""";
const auth_ = () => ({}); let said = null; const say = (m, bad) => { said = [m, !!bad]; };
const refresh = async () => {};
const form = { querySelector: () => ({ disabled: false }), getAttribute: () => '7',
  classList: { contains: () => false }, elements: { note: { value: 'shut it' }, actor: { value: 'a' } },
  hidden: false, reset() {} };
(async () => {
  const out = {};
  for (const [k, [status, body]] of Object.entries(C)) {
    globalThis.fetch = async () => ({ status, ok: status < 300,
      json: async () => { if (body === null) throw new Error('no body'); return body; } });
    said = null; await didThis(form); out[k] = said;
  }
  console.log(JSON.stringify(out));
})();""")
    assert _t["409"] == [_409, True], f"a 409 must print the node's own sentence and nothing else: {_t['409']}"
    assert _t["400"] == ["stage must be acknowledged, acted or decided", True], f"so must a 400: {_t['400']}"
    assert _t["401"][0].startswith("closing a loop from off this machine") and "planetai ui" in _t["401"][0], \
        f"a 401 carries its sentence in `detail`, and the page adds where the token comes from: {_t['401']}"
    assert _t["403"][0].startswith("this node is not sharing"), f"the middleware's 403 is `error`: {_t['403']}"
    assert _t["500"] == ["The node refused it (500).", True], f"no body, no invented sentence: {_t['500']}"
    assert _t["422"][0] == "field required (422)", f"a schema refusal's messages, joined: {_t['422']}"

# Set up writes only what somebody changed, and never over a key that moved while it was open.
#
# Node #1, 26 September 2026: AGENT_PREFER was set to `private` over PUT /settings at 18:07. Two saves of
# the agent group from a form drawn before that, made to change AGENT_REMOTE_URL, wrote every field in
# the group back, AGENT_PREFER's stale `strongest` with them, and the ask pane sent a question online.
# This runs the page's own saveSettings() against that morning, with the node's describe() shape.
_setup_fns = [re.search(p, _js_raw, re.S) for p in (
    r"function formValues\(\) \{.*?\n\}", r"function movedSince\(before, after, keys\) \{.*?\n\}",
    r"async function saveSettings\(\) \{.*?\n\}", r"async function loadSetup\(\) \{.*?\n\}")]
assert all(_setup_fns), "Set up no longer defines formValues(), movedSince(), saveSettings() or loadSetup()"
assert "LOADED = formValues();" in _setup_fns[3].group(0), \
    "loadSetup() no longer records what the form was drawn with, so a save cannot tell an edit from a stale value"
if shutil.which("node"):
    _rows = lambda prefer, url="": {"unlocked": True, "runtime": [
        {"key": "AGENT_PREFER", "value": prefer, "set": True, "secret": False},
        {"key": "AGENT_REMOTE_URL", "value": url, "set": bool(url), "secret": False},
        {"key": "AGENT_ONLINE_KEY", "value": "•••• set", "set": True, "secret": True},
        {"key": "QUIET_HOURS", "value": "0", "set": False, "secret": False}]}
    _st = _node("\n".join(g.group(0) for g in _setup_fns[:3]) + "\nconst DRAWN = " + json.dumps(_rows("strongest"))
                + "\nconst NOW = " + json.dumps(_rows("private")) + r""";
const window = { K: { age: m => Math.round(m) + ' min ago' } };
const localStorage = { getItem: () => 'tok' };
let GROUP = 'agent', DESC = DRAWN, LOADED = {}, DIRTY = false, puts = [], said = [], boxes = {};
const f = (key, value, extra = {}) => ({ dataset: { key }, type: 'text', value, classList: { contains: () => false }, ...extra });
let F = [];
const qa = sel => sel === '[data-key]' ? F : [];
const q = sel => sel.startsWith('#err-') ? (boxes[sel.slice(5)] = boxes[sel.slice(5)] || { hidden: true }) : null;
const toast = (m, bad) => said.push([m, !!bad]);
const lock = () => {}, route = () => {};
const loadSetup = () => {};
globalThis.fetch = async (url, o = {}) => {
  if (o.method === 'PUT') { puts.push(JSON.parse(o.body)); return { ok: true, status: 200, json: async () => ({}) }; }
  if (url.startsWith('/actions')) return { ok: true, json: async () => [
    { ts: new Date(Date.now() - 24 * 60000).toISOString(), stage: 'settings', actor: 'mcp', note: 'AGENT_PREFER' }] };
  return { ok: true, json: async () => NOW };
};
const draw = () => {
  F = [f('AGENT_PREFER', 'strongest'), f('AGENT_REMOTE_URL', ''), f('AGENT_ONLINE_KEY', '', { type: 'password' }),
       f('QUIET_HOURS', '', { dataset: { key: 'QUIET_HOURS', bool: '1' } })];
  DESC = DRAWN; LOADED = formValues(); puts = []; said = []; boxes = {};
};
const field = k => F.find(x => x.dataset.key === k);
(async () => {
  const out = {};
  draw(); field('AGENT_REMOTE_URL').value = 'http://laptop.local:11434/v1';
  await saveSettings(); out.incident = puts;
  draw(); await saveSettings(); out.untouched = { puts, said };
  draw(); field('AGENT_ONLINE_KEY').value = 'sk-new';
  await saveSettings(); out.secret = puts;
  draw(); field('AGENT_PREFER').value = 'fallback';
  await saveSettings(); out.clash = { puts: [...puts], box: boxes.AGENT_PREFER, said };
  await saveSettings(); out.again = puts;
  console.log(JSON.stringify(out));
})();""")
    assert _st["incident"] == [{"AGENT_REMOTE_URL": "http://laptop.local:11434/v1"}], \
        f"a save must send the one field that was edited, not the group's stale AGENT_PREFER with it: {_st['incident']}"
    assert _st["untouched"]["puts"] == [] and "Nothing to save" in _st["untouched"]["said"][0][0], \
        f"a save with nothing edited must write nothing, and say so: {_st['untouched']}"
    assert _st["secret"] == [{"AGENT_ONLINE_KEY": "sk-new"}], f"a typed secret is sent, and only it: {_st['secret']}"
    _box = _st["clash"].get("box") or {}
    assert _st["clash"]["puts"] == [] and not _box.get("hidden", True), \
        f"an edited key that moved on the node since the form was drawn must not be written over unseen: {_st['clash']}"
    assert '"private"' in _box["textContent"] and "mcp, 24 min ago" in _box["textContent"], \
        f"the page must say what the node holds now and who changed it, from the ledger: {_box}"
    assert _st["again"] == [{"AGENT_PREFER": "fallback"}], \
        f"a second press, once the keeper has been shown, writes the keeper's value and only it: {_st['again']}"

print("test_dashboard: the engine's fence holds at three stations, the page has none of its own, "
      "a hole in a series is a hole in the line, the page is three files carrying one contract and "
      "ten sections, and a refused page says so on the wall and in the nav")
