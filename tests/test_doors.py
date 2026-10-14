"""The five doors (/?layout=doors): what they read, and that they read only what a screen is given.

buildD() and flowFrom() run in node on node #1's capture (app/issues/fixtures/node1-2026-10-06-figures.json); the
prototype in planetai-design drew from a hand-built copy of the same capture, and these were checked against it
value for value on 7 Oct 2026. Here the checks are the ones that must keep holding: the shapes the doors read, the
token-only parts left empty without the token, and every file the page names served by its NAME.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "app"))
os.environ.setdefault("DATABASE_URL", "postgresql://test@127.0.0.1:1/test")
os.environ.setdefault("PACKS_DIR", str(ROOT / "packs"))      # the replays below need the packs the events engine replaced
STATIC = ROOT / "app" / "static"
FIX = "app/issues/fixtures/node1-2026-10-06-figures.json"

# Every file doors.html names is one the node serves by name (the /static/{name} rule: a name, never a path).
import main  # noqa: E402

html = (STATIC / "doors.html").read_text()
named = re.findall(r'(?:src|href)="/static/([^"]+)"', html)
assert named and all(n in main.COMPANIONS for n in named), [n for n in named if n not in main.COMPANIONS]
for f in STATIC.glob("doors-*.js"):
    assert f.name in main.COMPANIONS, f"{f.name} is shipped but the node does not serve it"
    assert f.name in named, f"{f.name} is served but doors.html never loads it"
js = "".join(f.read_text() for f in STATIC.glob("doors-*.js"))
for asset in re.findall(r"'/static/([\w.-]+)'", js):
    assert asset in main.COMPANIONS, f"a door asks for /static/{asset}, which the node does not serve"
assert "/node/" not in js and "data.json" not in js and "flow.json" not in js, "a door still reads the prototype's capture or proxy"
assert "h3-js" not in html and not re.search(r"\bh3\.\w+\(", js), "the node computes the cells; the page draws them"
print("doors: every file the page names is served by name, and no door reads the prototype's capture")

# / and /?layout=doors serve the doors through the same shell route; ?layout=classic serves the classic dashboard.
from fastapi.testclient import TestClient  # noqa: E402
c = TestClient(main.app)
assert c.get("/").text == html
assert c.get("/", params={"layout": "doors"}).text == html
assert c.get("/", params={"layout": "classic"}).text == (STATIC / "index.html").read_text()
print("doors: / and ?layout=doors is the doors, ?layout=classic the classic dashboard")
# the frozen theme asks for the mono at fonts/…, and every page requested it: that one path answers (14 Oct 2026)
_mono = c.get("/static/fonts/jetbrains-mono-latin.woff2")
assert _mono.status_code == 200 and _mono.headers["content-type"] == "font/woff2", _mono.status_code
assert "url('fonts/jetbrains-mono-latin.woff2')" in (STATIC / "planetai-theme.css").read_text().replace('"', "'")
print("doors: the theme's fonts/jetbrains-mono-latin.woff2 answers 200")
# the unit /issues names for a metric is the unit the node stores it in, which Home Assistant is told too: pressure
# said hPa over kPa values, and the Data door read 99.8 hPa beside the model's 996 (14 Oct 2026)
from issues import engine as _engine  # noqa: E402
_off = {m: (u, _engine.METRICS[m]["unit"]) for m, (u, _) in main.HA_UNITS.items() if u and m in _engine.METRICS and _engine.METRICS[m]["unit"] != u}
assert not _off, _off
print("doors: every metric's unit on the page is the unit the node stores it in")

# the phone page (SPEC_mobile §8.1): the same shell route, every /static name it uses is served, no heavy
# library, and it never writes a setting or stores the admin token
mob = (STATIC / "mobile.html").read_text()
mobjs = (STATIC / "mobile.js").read_text()
assert c.get("/", params={"layout": "mobile"}).text == mob
mnamed = re.findall(r'(?:src|href)="/static/([^"]+)"', mob) + re.findall(r"['\"]/static/([\w.#-]+)['\"]", mobjs)
assert mnamed and all(n.split("#")[0] in main.COMPANIONS for n in mnamed), [n for n in mnamed if n.split("#")[0] not in main.COMPANIONS]
assert not re.search(r'(?:src|href)="/static/(?:maplibre|deck|d3|plot)', mob), "the phone page's shell loads no map or chart library"
assert not re.search(r"deck\.gl|d3\.|plot\.umd", mobjs, re.I), "the phone page fetches MapLibre for its walk, and nothing heavier"
assert "planetai_admin'" not in mobjs.replace("removeItem('planetai_admin')", ""), "the phone page never stores the admin token"
assert not re.search(r"fetch\(\s*['\"]/settings", mobjs), "the phone page reads /settings through loadD (GET) and never calls it"
print("doors: ?layout=mobile is the phone page; it names only served files, loads no map library up front, touches no settings")

# the walk out from the house (SPEC_mobile §11.2): the phone page's middle, one page; mobile.js fetches MapLibre and
# walk.js when it nears the screen. It names no issue: every issue /issues carries is walked, at the scales it has
walkjs = (STATIC / "walk.js").read_text()
assert c.get("/", params={"layout": "walk"}).text == mob, "?layout=walk is the phone page"
assert 'id="walk"' in mob and "/static/walk.js" in mobjs and "/static/maplibre-gl.js" in mobjs
assert not re.search(r"['\"](air|heat|land|coast)['\"]", walkjs), "the walk names no issue; it walks what /issues carries"
print("doors: the walk is the phone page's middle; it loads when reached and names no issue")

# one phone mode (12 Oct 2026): at SHARE_LEVEL=open the walk's map answers without a token, but /geo/cell keeps what
# it says relative to the node for a token, or a phone could find the house asking res 15 cell by cell
assert "/geo/cell" in main._SHARE_OPEN[0] and "/ground/" in main._SHARE_OPEN[1] and "/geo/cell" not in main._SHARE_OFF[0]
from types import SimpleNamespace  # noqa: E402
os.environ.setdefault("NODE_LAT", "-8.819"); os.environ.setdefault("NODE_LON", "115.164")
_rq = lambda t: SimpleNamespace(state=SimpleNamespace(share_trusted=t))  # noqa: E731
_kw = dict(id=None, lat=-8.8, lon=115.17, res=14, children=15, polar=True)
_open, _mine = main.geo_cell(_rq(False), **_kw), main.geo_cell(_rq(True), **_kw)
assert not {"is_node", "cells_from_node", "ring_polar", "children_polar"} & set(_open) and _open["ring"] == _mine["ring"], _open.keys()
assert {"is_node", "cells_from_node", "ring_polar", "children_polar"} <= set(_mine)
print("doors: a phone with no token gets the map and the cells, never where they stand from the house")

# the phone's QR unlock: /settings/phone hands the act token to the admin token only, Set up draws it only unlocked,
# and the phone page keeps #act= and takes it out of the address bar
os.environ["ADMIN_TOKEN"] = "adm"
from fastapi import HTTPException  # noqa: E402
for _a in ("", "Bearer nope"):
    try:
        main.settings_phone(_a); raise AssertionError("/settings/phone answered without the admin token")
    except HTTPException as e:
        assert e.status_code in (401, 403), e.status_code
assert "/settings/phone" not in main._SHARE_OPEN[0] and "qrcode.js" in main.COMPANIONS
_setup = (STATIC / "doors-setup.js").read_text()
assert "(unlocked ? `<div class=\"srow\"><div class=\"sl\"><label>A phone" in _setup and "/static/qrcode.js" in _setup
assert "#act=" in mobjs and "history.replaceState" in mobjs
print("doors: the phone unlocks from a QR code only the admin's Set up can draw")

if not shutil.which("node"):
    print("doors: node is not installed, skipping the loader checks (skipped)")
    sys.exit(0)

prog = """
const fs = require('fs');
const { buildD } = require('./app/static/doors-load.js');
const src = fs.readFileSync('./app/static/doors-flow.js', 'utf8');
const flowFrom = new Function(src.match(/function flowFrom[\\s\\S]*?\\n}\\n/)[0] + '; return flowFrom;')();
const F = JSON.parse(fs.readFileSync('%s', 'utf8'));
const open = { ...F, days: F.issues_days }; delete open.readings_1h; delete open.actions; delete open.alerts;
const full = buildD({ ...F, days: F.issues_days }, 'en'), locked = buildD(open, 'en');
const fl = flowFrom(full), fo = flowFrom(locked);
/* the phone page's subset (SPEC_mobile §8.1): the capture minus the token-only three builds a D whose Now and
   Decide card draw — the engine's words (an old capture falls back to the sentence) and the event's asking+action */
const phone = buildD(open, 'en'), pl = phone.issues[phone.lead] || {};
const pev = phone.events.filter(e => !e.cleared_at).map(e => ({ asking: e.asking, action: e.action, message: 'message' in e, seen: 'last_seen_at' in e }));
/* node #1's live table carries forecast rows up to 48 h ahead (7 Oct): the doors' table must stop at the present */
const ahead = buildD({ ...F, days: F.issues_days, readings_1h: F.readings_1h.concat([{ bucket: '2099-01-01T00:00:00+08:00', sensor_id: 'forecast-om', metric: 'fc_cloud', mean: 1, min: 1, max: 1, n: 1 }]) }, 'en');
console.log(JSON.stringify({
  aheadLast: ahead.raw.buckets[ahead.raw.buckets.length - 1], fullLast: full.raw.buckets[full.raw.buckets.length - 1], aheadN: ahead.raw.n.length, fullN: full.raw.n.length,
  order: full.order, lead: full.lead, n: full.buckets.length, issues: Object.keys(full.issues),
  air: full.issues.air, ev: full.events, raw: full.raw && { b: full.raw.buckets.length, ids: Object.keys(full.raw.series).length },
  lockedRaw: locked.raw, lockedNotes: locked.notes, fullNotes: full.notes, lockedActions: locked.actions.length,
  lockedNote: locked.actions.some(a => 'note' in a), stats: Object.keys(full.stats15).length, point: full.point,
  flow: { b: fl.buckets.length, ids: Object.keys(fl.counts).length, alerts: fl.alerts.length, answers: fl.answers.length, counted: fl.counted },
  flowLocked: { b: fo.buckets.length, ids: Object.keys(fo.counts).length, alerts: fo.alerts.length, answers: fo.answers.length, counted: fo.counted },
  phone: { title: pl.title, tagline: pl.tagline, plain: pl.plain, sentence: pl.sentence, pev },
}));
""" % FIX
r = json.loads(subprocess.run(["node"], input=prog, capture_output=True, text=True, check=True).stdout)

# the walk walks every issue with a reading, in the engine's order, at the scales it has: land and coast are read only
# at the region, so their walk starts there; an issue with no reading anywhere is left off the switch
wprog = """const { walkOf } = require('./app/static/walk.js'); const F = JSON.parse(require('fs').readFileSync('%s', 'utf8'));
const I = F.issues; I.issues.empty = { stack: { room: null, yard: null, ring: null, region: { value: null } } }; I.order = I.order.concat('empty', 'gone');
console.log(JSON.stringify(walkOf(I).map(w => [w.k, w.at.map(Boolean)])));""" % FIX
wk = json.loads(subprocess.run(["node"], input=wprog, capture_output=True, text=True, check=True).stdout)
assert [k for k, _ in wk] == ["air", "heat", "land", "coast"], wk
assert dict(wk)["land"] == [False, False, False, True] and dict(wk)["air"] == [True] * 4, wk
print("doors: the walk takes every issue with a reading, in order, each at the scales it has")

# the issues, as the doors read them (/issues for the words, /issues/days for the seven days)
assert r["order"] == ["air", "heat", "land", "coast"] and r["lead"] == "heat" and r["n"] == 168, r["order"]
air = r["air"]
assert air["name"] == "Air" and air["line"] == 15 and air["unit"] == "µg/m³" and air["hero_distance"] == "room"
assert air["sentence"].startswith("Climbing to 8") and air["pix"] == "pix-air" and len(air["usual"]) == 24
assert len(air["series"]["room"]) == 168 and air["series"]["region"] is None and len(air["per_day"]) == 8
assert set(air["stack"]["room"]) == {"value", "provenance", "source"}, "the stack keeps three words, not the node's whole row"
# an event carries its own answer, its action's words and its rooms
assert [e["id"] for e in r["ev"]] == [1, 2, 3]
assert r["ev"][2]["answer"]["stage"] == "acted" and r["ev"][0]["answer"] is None and len(r["ev"][0]["rooms"]) == 3
assert r["ev"][0]["action"].startswith("Open the side where it started")
print("doors: the issues and the events are the node's own words, renamed and never recomputed")

# token-only parts: the hourly table and the household's notes stay on the node for a screen without the token
assert r["raw"] == {"b": 24, "ids": 21} and r["lockedRaw"] is None
assert r["fullNotes"] is True and r["lockedNotes"] is False and r["lockedActions"] > 0 and not r["lockedNote"], \
    "without the token the ledger comes from /issues' asks: stages and actors, never the notes"
assert r["stats"] == 18 and r["point"] == [115.164, -8.819], "the point is /health's, rounded as it gives it"
print("doors: without the token the hourly table is absent and the ledger carries no notes")

# the flow: counts from the hourly table, alerts and answers in its window (matched flow.json exactly on 7 Oct)
assert r["flow"] == {"b": 24, "ids": 21, "alerts": 30, "answers": 7, "counted": True}, r["flow"]
assert r["flowLocked"]["counted"] is False and r["flowLocked"]["ids"] == 0 and r["flowLocked"]["b"] == 24
print("doors: the flow counts what the hourly table counted, and says it did not count without it")
assert r["aheadLast"] == r["fullLast"] and r["aheadN"] == r["fullN"], "a forecast hour ahead of /issues entered the replayed table"
print("doors: the hourly table stops at the hour /issues was computed; forecast rows ahead of it stay out")

# the phone page's D (SPEC_mobile §8.1): the engine's words and the open event's asking and action. This capture
# predates title/tagline on the wire, so the check is the page's own fallback: a title, or the sentence it stands on.
ph = r["phone"]
assert ph["plain"] and (ph["title"] or ph["sentence"]), "the phone's Now has none of the engine's words to draw"
assert ph["pev"] and all(e["asking"] is not None and e["action"] for e in ph["pev"]), \
    "the phone's Decide card needs the event's asking and the live action's words"
assert all(e["message"] and e["seen"] for e in ph["pev"]), "the phone's card reads message.sent and last_seen_at"
print("doors: the phone page's subset builds a D with the words, the asking and the action it draws")

# Data (Tomas, 14 Oct): Images and Things are tables; a card, the whole form, opens only in a dialog
_dj = (STATIC / "doors-data.js").read_text()
_body = lambda name: _dj[_dj.index(f"async function {name}()"):_dj.index("\n}\n", _dj.index(f"async function {name}()"))]  # noqa: E731
assert '<table class="tbl things">' in _body("thingsBlock") and "icard" not in _body("thingsBlock").split("const open")[0], \
    "Things is a table; its form opens in a dialog"
assert '<table class="tbl imgs">' in _body("imagesBlock") and "icard" not in _body("imagesBlock").split("const show")[0], \
    "Images is a table; a card opens in a dialog, one image or all of them"
assert '<table class="tbl species">' in _body("imagesBlock") and "file?w=96" in _body("imagesBlock"), "species a table; thumbnails small"
print("doors: Data's images and things are tables, and a card is a dialog someone opens")
# Fixes from the design review of node #1 (14 Oct 2026). Each check fails if its fix regresses.
# 1. Local time: a UTC string and the node's own offset print the same hour (node #1 showed "as of 11:52" beside
#    "at 19:00"); a string with no offset, or a page with no zone yet, keeps its own clock.
# 3. A screen with no token asks no token-only route: doorsFetch answers a stand-in 403 and never reaches the network.
# 7. The Wall names no sensor, room or kit, and says stale only when the last poll is old.
# A capture as ?fixture= serves it (app/issues/api.py): its issues replayed through today's engine, so a field the engine
# added since the capture (title, tagline, asking) reaches the page as it would from a node.
import tempfile  # noqa: E402
from issues import engine as _engine_r, load as _load_r  # noqa: E402
_TMP = Path(tempfile.mkdtemp())


def replayed(path: str) -> str:
    snap = json.loads(Path(path).read_text())
    snap["issues"] = _engine_r.replay(snap, main.settings, _load_r())
    (_TMP / Path(path).name).write_text(json.dumps(snap, default=str))
    return str(_TMP / Path(path).name)


tprog = r"""
const fs = require('fs'), vm = require('vm');
const L = require('./app/static/doors-load.js');
const tz = 'Asia/Makassar';
const calls = []; globalThis.fetch = p => { calls.push(p); return Promise.resolve(new Response('[]')); };
(async () => {
  const locked = await L.doorsFetch('/things'), cap = await L.doorsFetch('/captures/3/file?w=96'), open = await L.doorsFetch('/stats');
  const core = fs.readFileSync('./app/static/doors-core.js', 'utf8'), pick = n => core.match(new RegExp('^const ' + n + ' = .*$', 'm'))[0];
  const F = JSON.parse(fs.readFileSync('%s', 'utf8')), els = {};
  const ctx = { D: L.buildD({ ...F, days: F.issues_days }, 'en'), VIEWS: {}, $: q => (els[q] ||= {}), out: null };
  vm.createContext(ctx);
  vm.runInContext(['esc', 'fmt', 'plain', 'said', 'num', 'unitOf', 'labelOf'].map(pick).join('\n') + '\n' + fs.readFileSync('./app/static/doors-wall.js', 'utf8')
    + '\nfrags(); out = { frags: $("#wfrag").innerHTML, ask: D.order.map(k => wallAsk(D.issues[k])).join(" "),'
    + ' fresh: wallStale({ last_poll: new Date().toISOString() }), old: wallStale({ last_poll: "2026-10-06T11:19:50+00:00" }), none: wallStale({}) };', ctx);
  const pm = fs.readFileSync('./app/static/doors-placemap.js', 'utf8').match(/function packRows[\s\S]*?\n}\n/)[0];
  vm.runInContext('const LAYERS = [{ id: "index" }, { id: "earth" }];' + pm + 'packRows(); out.pack = LAYERS.map(l => l.none);', ctx);
  console.log(JSON.stringify({
    utc: L.doorsLocal('2026-10-14T11:52:07.1+00:00', tz), z: L.doorsLocal('2026-10-14T11:52:00Z', tz), own: L.doorsLocal('2026-10-14T19:00:00+08:00', tz),
    midnight: L.doorsLocal('2026-10-14T17:30:00+00:00', tz), bare: L.doorsLocal('2026-10-14T11:52:00', tz), notz: L.doorsLocal('2026-10-14T11:52:00+00:00', null),
    locked: locked.status, cap: cap.status, open: open.status, calls, wall: ctx.out }));
})();
""" % replayed(FIX)
t = json.loads(subprocess.run(["node"], input=tprog, capture_output=True, text=True, check=True).stdout)
assert t["utc"] == t["z"] == "2026-10-14T19:52" and t["own"] == "2026-10-14T19:00", t
assert t["midnight"] == "2026-10-15T01:30", "a UTC evening is the node's next morning, day and all"
assert t["bare"] == t["notz"] == "2026-10-14T11:52", "no offset, or no zone: the string's own clock"
print("doors: every time is the node's local time, from a UTC string and from its own offset alike")
assert t["locked"] == t["cap"] == 403 and t["open"] == 200 and t["calls"] == ["/stats"], t
_locked = re.search(r"DOORS_LOCKED = /\^\\/\?\((.+?)\)\\b/", (STATIC / "doors-load.js").read_text()).group(1)
_paths = ["/" + x.replace("\\/", "/") for x in re.split(r"\|(?![^(]*\))", _locked)]
for _p in _paths:
    for _q in ([_p.split("(")[0] + y for y in _p.split("(")[1].rstrip(")").split("|")] if "(" in _p else [_p]):
        _opened = _q in main._SHARE_OPEN[0] or _q.startswith(main._SHARE_OPEN[1])
        assert not _opened or _q == "/alerts", f"{_q} answers a screen without a token at SHARE_LEVEL=open; doorsFetch must ask it"
print("doors: a screen with no token asks no token-only route; with one it asks as before")
_names = {x["name"].strip() for x in json.loads(Path(FIX).read_text())["sensors"] if len(x["name"].strip()) > 3}
_wall = t["wall"]["frags"] + t["wall"]["ask"]
assert t["wall"]["frags"].count("<div>") == 5 and not [n for n in _names if n in _wall], [n for n in _names if n in _wall]
assert "Nothing is asked now." in t["wall"]["ask"], "6 Oct 19:22: a stale alert and an answered event ask nothing now"
assert t["wall"]["old"] and t["wall"]["none"] and not t["wall"]["fresh"], t["wall"]
print("doors: the Wall names no sensor, room or kit, and says stale only when the last poll is old")
# 2. One answer to "is something asked now" (14 Oct): Now's Decide said "No event was open for air" from the events while
#    the Wall showed an open ask from open_asks. Both now read /issues `asking`; run on three captures, they agree.
aprog = r"""
const fs = require('fs'), vm = require('vm');
const L = require('./app/static/doors-load.js');
const core = fs.readFileSync('./app/static/doors-core.js', 'utf8'), now = fs.readFileSync('./app/static/doors-now.js', 'utf8');
const pick = n => core.match(new RegExp('^const ' + n + ' = .*$', 'm'))[0], fn = (src, n) => src.match(new RegExp('function ' + n + '[\\s\\S]*?\\n}\\n'))[0];
const out = {};
for (const [name, path] of Object.entries(JSON.parse(process.argv[1]))) {
  const F = JSON.parse(fs.readFileSync(path, 'utf8')), els = {}, D = L.buildD({ ...F, days: F.issues_days }, 'en');
  D.now = D.buckets.length - 1;
  const ctx = { D, S: { issue: null, i: D.now }, doorsLocal: L.doorsLocal, VIEWS: {}, $: q => (els[q] ||= {}) };
  vm.createContext(ctx);
  vm.runInContext(['esc', 'loc', 'dayOf', 'fmt', 'said', 'num', 'unitOf', 'labelOf', 'NODE', 'sign'].map(pick).join('\n') + '\n'
    + fn(core, 'evAt') + fn(core, 'answerWords') + now.match(/^const ANSWER_STAGE = .*$/m)[0] + '\n' + fn(now, 'decision')
    + fs.readFileSync('./app/static/doors-wall.js', 'utf8').match(/function wallAsk[\s\S]*?\n}\n/)[0], ctx);
  /* the phone's Decide card, its own copy of the helpers (mobile.js says why) */
  const mob = fs.readFileSync('./app/static/mobile.js', 'utf8'), mpick = n => mob.match(new RegExp('^const ' + n + ' = .*$', 'm'))[0];
  const pctx = { D, leadKey: null, doorsLocal: L.doorsLocal, DOORS_TOKEN: () => '' };
  vm.createContext(pctx);
  vm.runInContext(['esc', 'hhmm', 'fmt', 'said', 'ANSWER_STAGE'].map(mpick).join('\n') + '\n' + fn(mob, 'decideHTML'), pctx);
  out[name] = Object.fromEntries(D.order.map(k => {
    ctx.S.issue = k; vm.runInContext('decision()', ctx); pctx.leadKey = k;
    return [k, { wall: vm.runInContext('wallAsk(D.issues[S.issue])', ctx), now: els['#decide'].innerHTML, asking: D.issues[k].asking.length,
                 phone: vm.runInContext('decideHTML(D.issues[leadKey])', pctx) }];
  }));
}
console.log(JSON.stringify(out));
"""
_caps = {n: replayed(f"app/issues/fixtures/node1-{n}.json") for n in ("2026-10-06-figures", "2026-10-06-events", "2026-09-21d")}
_ar = subprocess.run(["node", "-e", aprog, json.dumps(_caps)], capture_output=True, text=True)
assert _ar.returncode == 0, _ar.stderr[-2000:]
a = json.loads(_ar.stdout)
_fg, _ev, _ru = a["2026-10-06-figures"], a["2026-10-06-events"], a["2026-09-21d"]
# 19:22, events: air's only open alert is a stale nearby one, heat's event was answered Done. Nothing is asked, on both.
assert "Nothing is asked now." in _fg["air"]["wall"] and "nothing is asked now" in _fg["air"]["now"], _fg["air"]
assert "No event was open" not in _fg["air"]["now"], "at the live hour Now speaks for the node's asking, not the events alone"
assert "Nothing is asked now." in _fg["heat"]["wall"] and "answered: Done" in _fg["heat"]["now"] and 'class="ans"' not in _fg["heat"]["now"]
# 09:00, events: the danger event asks, and the Wall counts it with the two nearby alerts still true. This capture has
# no /issues/days, so no event row: Now says the node's own words for it rather than "nothing is asked".
assert "3 things are asked of this house." in _ev["air"]["wall"] and "an event open since 07:18 (danger)" in _ev["air"]["now"], _ev["air"]
# 21 Sep, rules: heat's alert is still true and no event stands for it; Now draws the alert, the Wall counts it
assert "One thing is asked of this house." in _ru["heat"]["wall"] and "asked since" in _ru["heat"]["now"] and "Reply /act" in _ru["heat"]["now"], _ru["heat"]
for _cap in a.values():
    for _k, _v in _cap.items():
        assert ("Nothing is asked now." in _v["wall"]) == (_v["asking"] == 0), (_k, _v)
        # the phone says the same: an ask is drawn (the event's card or the node's words), or nothing is asked
        assert ("still open" in _v["phone"] or "data-ev" in _v["phone"]) == (_v["asking"] > 0), (_k, _v["phone"])
assert "Reply /act" in _ru["heat"]["phone"] and "Nothing is asked now." in _fg["air"]["phone"], (_ru["heat"]["phone"], _fg["air"]["phone"])
print("doors: Now's Decide card, the Wall and the phone read one answer to what is asked now, on three captures")
# 6. Place's Index and land-change rows say what the node holds (node #1: 6 of 20, nine years compared), not "nothing"
assert t["wall"]["pack"][0].startswith("6 of 20 hold a value") and "What changed" in t["wall"]["pack"][1], t["wall"]["pack"]
print("doors: Place's Index and land-change rows say what the node holds and where it is drawn")
# 11. A locked part points to where a screen is unlocked, Set up › This screen, never "under Node".
assert "under Node" not in js and "UNLOCK_AT" in _dj, "unlocking lives in Set up › This screen (#setup/screen)"
# 13. Without the token the ledger draws stages and times only (/issues gives no names; test_events_wire holds that).
_led = _dj[_dj.index("function ledgerBlock"):]
assert "if (!DOORS_TOKEN())" in _led and "a.actor" not in _led[:_led.index("return;")], "a locked ledger names nobody"
# 9, 10. The household form is not the head's 20 px bold .who; a cell after a number has its gap on the left.
assert 'class="who"' not in _dj and ".who{" in html, "the household form took the page's .who rule"
assert ".tbl th.n+th:not(.n),.tbl td.n+td:not(.n){padding-left:" in html
# 12. The phone reads either token, as the doors do.
assert "const hasToken = () => !!DOORS_TOKEN();" in mobjs
print("doors: locked parts link to Set up › This screen; a locked ledger names nobody; the phone reads both tokens")
# The diary split (Tomas, 14 Oct 2026): Now says Yesterday and Did it work for the issue on screen, Node keeps the record
# in "What it remembers" as tables with the long text in a dialog, Data keeps a line pointing there. All of it needs the
# admin token: a screen without one asks nothing and is shown nothing but where to unlock; the Wall never reads it.
LEARNED = {"digests": {"day": 9, "week": 1}, "checked": "2026-10-06T00:05:00+00:00", "learnings": [
    {"kind": "worked", "key": "air-quality/events", "issue": "air-quality", "status": "holding", "n": 6, "for_whom": [],
     "statement": "Acted on 6 times: PM2.5 inside changed -4.1 µg/m³ in the 1–2 h after, while on the street it changed +0.3 µg/m³. Left unanswered 3 times: PM2.5 inside changed -0.5 µg/m³.",
     "numbers": {"acted": {"n": 6, "change": -4.1, "street": 0.3}, "unanswered": {"n": 3, "change": -0.5, "street": 0.2}, "after_hours": [1, 2],
                 "unit": "µg/m³", "verdict": "helps", "cases": {
                     "acted": [{"at": "2026-10-06T07:00:00+08:00", "before": 40.2, "after": 12.3, "change": -27.9, "street": 0.4, "note": "closed the windows, purifier on"}],
                     "unanswered": [{"at": "2026-10-05T16:00:00+08:00", "before": 30.0, "after": 28.0, "change": -2.0, "street": 1.0}]}}},
    {"kind": "worked", "key": "heat/events", "issue": "heat", "status": "too_early", "n": 2, "statement": "Acted on 2 times so far: too early to say.",
     "numbers": {"acted": {"n": 2, "change": -0.4, "street": 0.1}, "unanswered": {"n": 0, "change": None, "street": None}, "after_hours": [3, 6], "unit": "°C",
                 "verdict": "too_early", "cases": {"acted": [], "unanswered": []}}},
    {"kind": "usual", "key": "indoor-pm25", "issue": "air", "metric": "pm25", "status": "holding", "scope": "house", "statement": "Usually highest around 07:00.",
     "numbers": {"high_hour": 7, "high": 12.1, "unit": "µg/m³", "by_hour": {}}}]}
DAY = {"q": "", "results": [{"source": "digest", "scale": "day", "period_start": "2026-10-05", "label": "Sunday 5 October 2026",
        "text": "Sunday 5 October 2026. PM2.5 inside averaged 9.1 µg/m³, highest 187.3 µg/m³ (17:00); PM2.5 outside averaged 14.2 µg/m³. 2 alerts (danger 2), 1 acted on. What was done: “closed the windows”.",
        "numbers": {"indoor-pm25": {"mean": 9.1, "max": 187.3, "max_at": "2026-10-05T17:00:00+08:00", "hours": 24},
                    "outdoor-pm25": {"mean": 14.2, "max": 30.0, "max_at": "2026-10-05T18:00:00+08:00", "hours": 24},
                    "alerts": {"danger": {"raised": 2, "acted": 1}}, "notes": 1}}]}
HOUSE = {"people": {}, "choices": {"older": "someone over 65", "under5": "a child under five"}}
rprog = r"""
const fs = require('fs'), vm = require('vm');
const [path, learned, day, house] = JSON.parse(process.argv[1]);
const core = fs.readFileSync('./app/static/doors-core.js', 'utf8'), now = fs.readFileSync('./app/static/doors-now.js', 'utf8'), node = fs.readFileSync('./app/static/doors-node.js', 'utf8');
const pick = n => core.match(new RegExp('^const ' + n + ' = .*$', 'm'))[0], fn = (src, n) => src.match(new RegExp('function ' + n + '[\\s\\S]*?\\n}\\n'))[0];
const calls = [];
globalThis.fetch = (p) => { calls.push(p); const b = p.startsWith('/learned/search') ? day : p === '/learned' ? learned : p === '/household' ? house : {};
  return Promise.resolve(new Response(JSON.stringify(b))); };
const L = require('./app/static/doors-load.js'), F = JSON.parse(fs.readFileSync(path, 'utf8')), D = L.buildD({ ...F, days: F.issues_days }, 'en');
D.now = D.buckets.length - 1;
const mk = () => ({ innerHTML: '', hidden: false, cls: new Set(), classList: { toggle(c, v) { this._.cls[v ? 'add' : 'delete'](c); } }, querySelectorAll: () => [], querySelector: () => ({}), scrollIntoView() {} });
const run = async (token, issue, hash) => {
  globalThis.localStorage = token ? { getItem: () => 'tok' } : undefined; calls.length = 0;
  const els = {}, dlg = [], $ = q => { if (!els[q]) { els[q] = mk(); els[q].classList._ = els[q]; } return els[q]; };
  const ctx = { D, S: { issue, i: D.now }, doorsLocal: L.doorsLocal, doorsFetch: L.doorsFetch, $, location: { hash }, setTimeout,
    document: { getElementById: () => mk() }, dayStrip: () => '', cardDialog: (t, h) => dlg.push([t, h]), DOORS_AUTH: () => ({}) };
  vm.createContext(ctx);
  vm.runInContext(['esc', 'WD', 'loc', 'dayOf', 'dLabel', 'wdhm', 'fmt', 'said', 'num', 'UNLOCK_AT'].map(pick).join('\n') + '\n' + fn(core, 'answerWords')
    + now.slice(now.indexOf('let NOWL = null;'), now.indexOf('// The things this home keeps'))
    + node.slice(node.indexOf('const LSTATUS'), node.indexOf('/* What comes in, what goes out')), ctx);
  await vm.runInContext('rememberLoad()', ctx);
  const nr = $('#nremember'), out = { hidden: nr.hidden, html: nr.innerHTML, frame: nr.cls.has('decide') };
  for (const k of ['heat', 'land']) { ctx.S.issue = k; vm.runInContext('nowRemember()', ctx); out[k] = $('#nremember').innerHTML; }
  await vm.runInContext('remember()', ctx);
  return { now: out, node: $('#remember').innerHTML, diary: $('#rdiary').innerHTML, worked: $('#rworked').innerHTML, who: $('#rwho').innerHTML, dlg, calls: calls.slice() };
};
(async () => console.log(JSON.stringify({ on: await run(true, 'air', '#node/remember/day/2026-10-05'), off: await run(false, 'air', '#node') })))();
"""
_rr = subprocess.run(["node", "-e", rprog, json.dumps([replayed(FIX), LEARNED, DAY, HOUSE])], capture_output=True, text=True)
assert _rr.returncode == 0, _rr.stderr[-2000:]
rm = json.loads(_rr.stdout)
on, off = rm["on"], rm["off"]
_n = on["now"]["html"]
assert not on["now"]["hidden"] and "<h3>Yesterday</h3>" in _n and "<h3>Did it work</h3>" in _n, _n
assert re.search(r"Yesterday the air inside averaged <span[^>]*>9\.1</span> µg/m³", _n) and "over the WHO line for" in _n and ", worse." in _n, \
    "yesterday's entry in plain words, from its own numbers and the house's hours over the line"
assert "over the WHO line for 1 hour;" in re.sub(r"<[^>]+>", "", _n), "one hour, not one hours"
assert "2 alert" in re.sub(r"<[^>]+>", "", _n) and "#node/remember/day/2026-10-05" in _n, "its alerts, and a link to the whole entry on Node"
_t = re.sub(r"<[^>]+>", "", _n)
assert "The node last asked Tue, 6 Oct at 07:18" in _t and "card above" in on["now"]["heat"] and "Done Tue, 6 Oct at 07:00: “closed the windows, purifier on”" in _t, _t
assert "Inside went from 40.2 to 12.3 µg/m³ in the 1–2 h after; the street +0.4." in _t, "what happened after: the case's own numbers"
assert "It helps here. Acted on 6 times:" in _t and "Left unanswered" not in _t, "the node's verdict, and its statement kept short"
assert "usually worst around 07:00 inside (12.1 µg/m³)" in _t and "who lives here?" in _t and "#node/remember/who" in _n
assert "Too early to say." in on["now"]["heat"] and "Did it work" not in on["now"]["land"], "heat is too early; land never asks"
assert not on["now"]["frame"], "no frame while nothing is asked"
assert "<h3>Yesterday" not in off["now"]["html"] and off["now"]["hidden"] and not [c for c in off["calls"] if "learned" in c or "household" in c], \
    "a screen without the token asks nothing of the house's own and shows nothing on Now"
print("doors: Now says Yesterday and Did it work for the issue on screen, from the node's numbers; nothing without the token")
assert "diary entries kept (9 days, 1 week)" in on["node"] and "never leaves" in on["node"], on["node"][:400]
assert '<table class="tbl diary">' in on["diary"] and "Sunday 5 October 2026" in on["diary"] and "187.3" in on["diary"] and "14.2" in on["diary"]
assert "closed the windows" in on["diary"] and "Against the" not in on["diary"], "what was done, from the entry"
assert on["dlg"] and on["dlg"][0][0] == "Sunday 5 October 2026" and "What was done" in on["dlg"][0][1], "#node/remember/day/<date> opens that entry"
assert '<table class="tbl worked">' in on["worked"] and "every ask about the air" in on["worked"] and "6 · -4.1" in on["worked"] and ">helps<" in on["worked"]
assert "Acted on 6 times" not in on["worked"] and "data-w=" in on["worked"], "the statement and its cases open in a dialog, not in the table"
assert 'data-f="who"' in on["who"] and "a child under five" in on["who"], "the household form lives on Node now"
assert "admin token" in off["node"] and "#setup/screen" in off["node"] and "<table" not in off["node"] and "Sunday" not in off["node"]
print("doors: Node › What it remembers holds the diary and what worked as tables, the text in a dialog; locked, it only says where to unlock")
_dh = html[html.index('data-view="data"'):html.index("<!-- WALL -->")]
assert not re.search(r"d-learned|d-usual|d-diary", _dj + _dh) and "learnedBlock" not in _dj and 'href="#node/remember"' in _dh, \
    "Data no longer holds the diary, what is usual or what worked; it points to Node"
_wall = (STATIC / "doors-wall.js").read_text() + (STATIC / "doors-wallmap.js").read_text()
assert "/learned" not in _wall and "/household" not in _wall, "the Wall never reads the house's learnings"
print("doors: Data points to Node for the diary; the Wall reads none of it")

# The WHO line (Tomas, 14 Oct 2026: "put the WHO line in graphics as reference"): every drawing of PM2.5 draws the
# air's own line, red and dashed (.linep, or the same three attributes on the phone), labelled "WHO 15". Each
# drawing is rendered here on node #1's capture: Now's day (d3, on a twenty-line stand-in for the DOM), Data's
# every source, seven days and usual day, and the phone's walk. Heat keeps its own "line 35.0" and gains no line.
gprog = r"""
const fs = require('fs'), vm = require('vm');
const L = require('./app/static/doors-load.js'), d3 = require('./app/static/d3.min.js');
const F = JSON.parse(fs.readFileSync('%s', 'utf8'));
const core = fs.readFileSync('./app/static/doors-core.js', 'utf8'), pick = n => core.match(new RegExp('^(?:const|function) ' + n + '\\b.*$', 'm'))[0];
const SVG = 'http://www.w3.org/2000/svg', doc = { createElementNS: (ns, t) => new El(t), documentElement: { namespaceURI: SVG }, body: {} };
class El {
  constructor(t) { Object.assign(this, { tagName: t, namespaceURI: SVG, ownerDocument: doc, a: {}, kids: [], textContent: '', parentNode: null,
    style: { setProperty() {}, removeProperty() {}, getPropertyValue: () => '' } }); }
  setAttribute(k, v) { this.a[k] = String(v); } removeAttribute(k) { delete this.a[k]; } getAttribute(k) { return this.a[k]; }
  appendChild(c) { c.parentNode = this; this.kids.push(c); return c; } insertBefore(c) { return this.appendChild(c); }
  removeChild(c) { this.kids = this.kids.filter(x => x !== c); return c; } addEventListener() {}
  querySelectorAll() { const o = [], w = e => e.kids.forEach(c => { o.push(c); w(c); }); w(this); return o; }
  get outerHTML() { return `<${this.tagName}${Object.entries(this.a).map(([k, v]) => ` ${k}="${v}"`).join('')}>${this.textContent}${this.kids.map(c => c.outerHTML).join('')}</${this.tagName}>`; }
}
const els = {}, ctx = { D: L.buildD({ ...F, days: F.issues_days }, 'en'), d3, document: doc, getComputedStyle: () => ({ color: '#000' }),
  doorsLocal: L.doorsLocal, VIEWS: {}, $: q => (els[q] ||= {}), out: {} };
vm.createContext(ctx);
vm.runInContext(['esc', 'WD', 'loc', 'dayOf', 'dLabel', 'fmt', 'lineLab', 'plain', 'NODE', 'sign', 'PROV', 'prov', 'said', 'num', 'unitOf', 'labelOf',
  'ISSUES_DRAWN', 'val'].map(pick).join('\n') + '\n' + fs.readFileSync('./app/static/doors-fig.js', 'utf8') + '\n' + fs.readFileSync('./app/static/doors-data.js', 'utf8')
  + `\nD.dates = [...new Set(D.buckets.map(dayOf))]; D.at = {}; D.buckets.forEach((b, i) => { D.at[dayOf(b) + '|' + hourOf(b)] = i; });
   D.now = D.buckets.length - 1; D.sens = Object.fromEntries(D.sensors.map(s => [s.sensor_id, s]));   /* doors-core.js's boot, line for line */
   const S = { i: D.now, issue: 'air' }, day = (k, w) => { const el = document.createElementNS(0, 'svg'); el.id = 'f' + w; el.parentNode = { clientWidth: w };
     dayWeek({ el, issue: k }); return el.outerHTML; };
   const H = Object.fromEntries([...Array(24).keys()].map(h => [h, 4 + h]));
   /* What is usual lives on Node now (doors-node.js usualBlock), which draws each day with this dayStrip, so: */
   sensorsBlock(); issuesBlock();
   out = { day: day('air', 900), narrow: day('air', 400), heat: day('heat', 900), usual: [dayStrip(H, D.issues.air), dayStrip(H, false)],
     sensors: $('#sensors').innerHTML, issues7: $('#issues7').innerHTML.split('<figure').slice(1) };`, ctx);
/* the walk, the phone's: its whole script on a stand-in page, for the air and for the heat */
const walk = hash => new Promise(done => {
  const E = {}, el = q => (E[q] ||= { innerHTML: '', querySelectorAll: () => [], insertAdjacentHTML() {}, remove() {} });
  const json = { '/issues': F.issues, '/issues/days?days=1': F.issues_days, '/health': F.health };
  const map = { on: (e, f) => e === 'load' && f(), getSource: () => ({ setData() {} }), getLayer: () => null, setProjection() {}, setPaintProperty() {},
    setLayoutProperty() {}, flyTo() {}, fitBounds() {} };
  const w = { doorsFetch: p => Promise.resolve(json[p] ? { ok: true, json: () => json[p] } : { ok: false }), DOORS_AUTH: () => ({}), innerHeight: 800,
    location: { hash, origin: 'http://node' }, maplibregl: { Map: function () { return map; } }, IntersectionObserver: function () { this.observe = () => {}; },
    document: { querySelector: el, querySelectorAll: () => [], addEventListener() {} } };
  w.window = w; vm.createContext(w); vm.runInContext(fs.readFileSync('./app/static/walk.js', 'utf8'), w);
  setTimeout(() => done({ ready: w.WALK_READY, chs: el('#chs').innerHTML }), 50);
});
Promise.all([walk('#air'), walk('#heat')]).then(([air, heat]) => console.log(JSON.stringify({ ...ctx.out, walk: air, walkHeat: heat })));
""" % FIX
w = json.loads(subprocess.run(["node"], input=gprog, capture_output=True, text=True, check=True).stdout)
LINEP = 'stroke="var(--signal-worse)" stroke-width="1.5" stroke-dasharray="6 4"'
for name in ("day", "narrow"):
    assert w[name].count('class="linep"') == 1 and ">WHO 15<" in w[name], f"Now's day ({name}) draws no labelled WHO line"
assert ">line 35.0<" in w["heat"] and "WHO" not in w["heat"], "heat's line keeps its own name: it is this place's, not the WHO's"
assert w["sensors"].count('class="linep"') == w["sensors"].count('class="srow"') == w["sensors"].count(">WHO 15<") > 3, \
    "Data's every source, last 24 hours: a labelled WHO line in every row"
air7 = [f for f in w["issues7"] if f.startswith(' class="sm"><figcaption><b><span class="said">Air')]
assert len(air7) == 3 and all('class="linep"' in f and ">WHO 15<" in f for f in air7), "Data's seven days: each air drawing labels its line"
assert 'class="linep"' in w["usual"][0] and ">WHO 15<" in w["usual"][0], "What is usual: the PM2.5 day draws the WHO line"
assert "linep" not in w["usual"][1], "What is usual: the heat day draws no air line"
assert w["walk"]["ready"] and w["walk"]["chs"].count(LINEP) == w["walk"]["chs"].count(">WHO 15<") == 5, \
    "the walk: the house, the street, the stations, the ring and the region each draw the labelled WHO line"
assert w["walkHeat"]["chs"].count(LINEP) == 2 and "WHO" not in w["walkHeat"]["chs"], "the walk's heat keeps its two lines, named its own"
print("doors: every PM2.5 drawing draws the air's own line, red and dashed, labelled WHO 15; heat keeps its own")
# every verdict learn.py can give has words on Now and on Node (the voice pass added `worse`, 14 Oct)
import importlib, sys as _sys                                       # noqa: E402,E401
_sys.path.insert(0, "app"); _learn = importlib.import_module("learn")
_nowjs, _nodejs = (STATIC / "doors-now.js").read_text(), (STATIC / "doors-node.js").read_text()
for _v in set(_learn.VERDICT_WORDS) - {"gone"}:
    assert re.search(rf"const VERDICT = {{[^}}]*\b{_v}:", _nowjs), f"Now has no words for the verdict {_v}"
for _v in _learn.VERDICT_WORDS:
    assert re.search(rf"const VERDICT_W = {{[^}}]*\b{_v}:", _nodejs), f"Node has no words for the verdict {_v}"
print("all doors checks passed")
