"""The Wall map's pure half (app/static/doors-wallmap.js): hour lookup, wind and swell motion maths, station features.
Run under node from here; nothing is drawn, so nothing needs a browser."""
import json
import re
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

out = subprocess.run(["node", "-e", """
const W = require('./app/static/doors-wallmap.js');
const segs = W.crestSegments(800, 600, 204, 0), t = W.toward(204);
const st = [{lat: -8.7, lon: 115.2, pm25: [10, null, 40]}, {lat: -8.8, lon: 115.1, pm25: [null, null, null]}];
console.log(JSON.stringify({
  at: [W.atHour([null, null, 3, null], 0), W.atHour([1, null, null], 2), W.atHour([null, null], 1), W.atHour([5, null, 7], 1), W.atHour([1, 2, 3], 1)],
  south: W.toward(180), n350: W.toward(350), unit: Math.hypot(W.toward(37).ux, W.toward(37).uy),
  n: segs.length, t,
  dot: segs.map(([x1, y1, x2, y2]) => (x2 - x1) * t.ux + (y2 - y1) * t.uy),
  len: segs.map(([x1, y1, x2, y2]) => Math.hypot(x2 - x1, y2 - y1)),
  gap: segs.slice(1).map((s, i) => ((s[0] + s[2]) / 2 - (segs[i][0] + segs[i][2]) / 2) * t.ux + ((s[1] + s[3]) / 2 - (segs[i][1] + segs[i][3]) / 2) * t.uy),
  shifted: W.crestSegments(800, 600, 204, 10).map(s => ((s[0] + s[2]) / 2 - 400) * t.ux + ((s[1] + s[3]) / 2 - 300) * t.uy),
  small: W.crestSegments(800, 600, 204, 0, 100).length,
  phase: [W.crestPhase(8.6, 8.6), W.crestPhase(4.3, 8.6), W.crestPhase(4.3, 8.6, 10), W.crestPhase(12.9, 8.6)],
  streak: [W.streak(10), W.streak(0)],
  feat: [0, 1, 2].map(h => W.stationFeatures(st, h, 15)), onWindow: typeof window,
}));
"""], capture_output=True, text=True, check=True)
R = json.loads(out.stdout)

assert R["at"] == [3, 1, None, 5, 2], R["at"]
assert abs(R["south"]["ux"]) < 1e-9 and abs(R["south"]["uy"] + 1) < 1e-9, R["south"]
assert R["n350"]["uy"] > 0.98 and 0 < R["n350"]["ux"] < 0.2, R["n350"]   # from the north, so down the screen, a little right
assert abs(R["unit"] - 1) < 1e-9
print("  wallmap: hours and directions")

assert R["n"] > 10 and all(abs(d) < 1e-9 for d in R["dot"]), "every crest is square to the way the swell goes"
assert all(abs(g - 26) < 1e-9 for g in R["gap"]), R["gap"][:3]
assert all(l >= (800 ** 2 + 600 ** 2) ** .5 - 1e-6 for l in R["len"]), "each line spans the box whatever the angle"
assert R["small"] < R["n"], "wider spacing, fewer crests"
assert any(abs((o - 10) % 26) < 1e-9 or abs((o - 10) % 26 - 26) < 1e-9 for o in R["shifted"]), "phase shifts the lines along the direction"
assert R["phase"][0] == 0 and abs(R["phase"][1] - 13) < 1e-9 and abs(R["phase"][2] - 5) < 1e-9 and abs(R["phase"][3] - 13) < 1e-9, R["phase"]
assert R["streak"] == [{"v": 58, "tail": 35}, {"v": 8, "tail": 10}], R["streak"]
print("  wallmap: crests, phase and streaks")

f0, f1, f2 = R["feat"]
assert f0["type"] == "FeatureCollection" and len(f0["features"]) == 2
p = lambda f, i: f["features"][i]["properties"]
assert (p(f0, 0)["v"], p(f0, 0)["over"]) == (10, False) and (p(f2, 0)["v"], p(f2, 0)["over"]) == (40, True)
assert (p(f1, 0)["v"], p(f1, 0)["over"]) == (-1, False), "a station with no reading is -1 and never over the line"
assert (p(f0, 1)["v"], p(f0, 1)["over"]) == (-1, False)
assert f0["features"][0]["geometry"] == {"type": "Point", "coordinates": [115.2, -8.7]}
assert R["onWindow"] == "undefined"
print("  wallmap: stations as features")

# ---------------------------------------------------------------- the story: which chapters each scale has
# W is a /wall body (tests/fixtures/wall-node1.json, coarse values, node #1 on 18 Nov 2026) and D the doors' /issues
# on node #1's capture, with the readouts the capture lacks added for the all-present case.
out = subprocess.run(["node", "-e", """
const M = require('./app/static/doors-wallmap.js'), fs = require('fs');
const W0 = JSON.parse(fs.readFileSync('tests/fixtures/wall-node1.json', 'utf8'));
const cap = JSON.parse(fs.readFileSync('app/issues/fixtures/node1-2026-10-06-figures.json', 'utf8')).issues.issues;
const rd = (metric, value, unit, provenance = 'model') => ({ metric, value, unit, provenance });
const mkD = more => { const I = {}; for (const [k, it] of Object.entries(cap)) I[k] = { ...it, line: (it.line || {}).value ?? null }; return { issues: { ...I, ...more } }; };
const D0 = mkD({});
const D1 = mkD({
  heat: { ...cap.heat, line: null, readouts: [rd('lst', 34.2, '°C'), rd('lst_delta', 4.2, '°C'), rd('lst_night', 27.1, '°C')] },
  water: { readouts: [rd('rain_24h_mm', 3.4, 'mm'), rd('terrain_upslope_ha', 1.8, 'ha')] } });
const clone = o => JSON.parse(JSON.stringify(o));
const nul = ks => { const w = clone(W0); ks.forEach(k => w[k] = null); return w; };
const ks = story => story.map(s => s.chapters.map(c => c.k));
const all = ['stations', 'island', 'roofs', 'lab', 'rivers', 'basin', 'river', 'grid', 'change'];
const noWater = nul(['rivers', 'basin', 'river']);
const empty = { ...nul(all), hours: { ...W0.hours } };
const noIsland = nul(['island']);
const noSun = clone(W0); noSun.grid.sun = null;
const noWave = clone(W0); delete noWave.hours.wave_from;
console.log(JSON.stringify({
  full: M.wallStory(W0, D1), cap: ks(M.wallStory(W0, D0)), noWater: ks(M.wallStory(noWater, D1)),
  empty: M.wallStory(empty, { issues: {} }).map(s => [s.k, s.chapters.length, s.res, s.km2]), capOnly: ks(M.wallStory(empty, mkD({}))),
  noIsland: ks(M.wallStory(noIsland, D1))[2], noSun: ks(M.wallStory(noSun, D1))[0], noWave: M.wallStory(noWave, D1)[2].chapters.find(c => c.k === 'sea').says,
  at: [M.chapterAt(23, 4), M.chapterAt(0, 5), M.chapterAt(23, 5), M.chapterAt(5, 4), M.chapterAt(6, 4), M.chapterAt(12, 1), M.chapterAt(24, 3)],
  names: JSON.parse(fs.readFileSync('app/issues/fixtures/node1-2026-10-06-figures.json', 'utf8')).sensors.map(s => s.name.trim()).filter(n => n.length > 3),
  lab: W0.lab.name,
}));
"""], capture_output=True, text=True, check=True)
S = json.loads(out.stdout)

full = S["full"]
CH = lambda s, k: next(c for c in full[s]["chapters"] if c["k"] == k)
assert [x["k"] for x in full] == ["base", "community", "city"] and [x["res"] for x in full] == [8, 7, 6], [x["k"] for x in full]
assert [[c["k"] for c in x["chapters"]] for x in full] == [
    ["air", "built", "sun", "heat", "rain"], ["air", "change", "lab", "rivers"], ["grid", "basin", "sea", "city-air"]]
assert [x["km2"] for x in full] == [4.5, 31.4, 219.4], "the scale's own size, from /wall"
assert not [c for x in full for c in x["chapters"] if c["k"] == "rice"], "no rice chapter: that pack is not on the Wall"
assert all(set(c) >= {"k", "hue", "title", "n", "word", "says", "src", "layers"} for x in full for c in x["chapters"])
assert all(c["hue"].startswith("--") and isinstance(c["layers"], list) and len(c["n"]) == 2 for x in full for c in x["chapters"])
assert all(c["word"] in ("live", "partial", "model", "cached", "example") for x in full for c in x["chapters"]), "one of the five"
print("  story: 5 / 4 / 4 chapters in order, the five words, hues are custom property names")

assert [c["layers"] for c in full[0]["chapters"]] == [["own-air"], ["roofs", "roofs-mask"], ["roofs-sun", "roofs-mask"], ["own-heat"], ["own-water"]]
assert [c["layers"] for c in full[1]["chapters"]] == [["stations"], ["change"], ["lab"], ["rivers"]]
assert [c["layers"] for c in full[2]["chapters"]] == [["grid"], ["basin", "rivers"], [], ["island", "stations"]]
assert [c["fit"] for c in full[2]["chapters"] if "fit" in c] == [[[115.237, -8.716]], full[2]["chapters"][1]["fit"], [[115.178, -8.625]]]
assert len(CH(2, "basin")["fit"]) == 5 and "fit" not in CH(2, "sea") and "fit" not in CH(0, "air")
assert CH(2, "city-air")["official"] == {"lon": 115.178, "lat": -8.625, "label": "Sempidi · government"}, CH(2, "city-air")["official"]
assert CH(0, "air")["n"] == [7.8, "µg/m³"] and CH(0, "air")["word"] == "live" and CH(1, "air")["word"] == "partial"
assert CH(0, "sun")["n"] == [6.4, "kWh/m²"] and "2.0 kW panel" in CH(0, "sun")["says"] and "9.6 kWh" in CH(0, "sun")["says"]
assert CH(0, "built")["n"] == [91, "%"] and CH(0, "heat")["n"] == [34.2, "°C"] and CH(0, "rain")["n"] == [3.4, "mm"]
assert CH(1, "change")["n"] == [129, "ha"] and CH(1, "lab")["n"] == [4, "km"] and CH(1, "rivers")["n"] == [4, "km"]
assert CH(2, "grid")["n"] == [84, "%"] and CH(2, "basin")["n"] == [42, "km²"] and CH(2, "sea")["n"] == [1.7, "m"]
assert CH(2, "city-air")["n"] == [6.7, "µg/m³"] and CH(1, "lab")["word"] == "partial"
print("  story: layer names, fits, the official station's label, the figures")

says = " ".join(c["says"] for x in full for c in x["chapters"])
mine = [n for n in S["names"] if n != S["lab"]]       # the lab is a public place W names itself; no house kit or room is
assert mine and not [n for n in mine if n in says], [n for n in mine if n in says]
assert not re.search(r"\d\.\d+\s*km\b", says), "a distance is a whole km"
assert "Pesanggaran" in CH(2, "grid")["says"] and "12 km" in CH(2, "grid")["says"] and "gas" in CH(2, "grid")["says"]
assert "22 km" in CH(2, "basin")["says"] and "10.6" in CH(2, "basin")["says"] and "4 km" in CH(1, "rivers")["says"]
assert "Fab Lab Bali" in CH(1, "lab")["says"] and "4 km" in CH(1, "lab")["says"] and "2025" in CH(1, "change")["says"]
assert "Sempidi" in CH(2, "city-air")["says"] and "south-west" in CH(2, "sea")["says"]
assert "from the" not in S["noWave"], "no direction hour, no direction said"
print("  story: captions read W in whole km and name no sensor")

assert S["cap"] == [["air", "built", "sun"], ["air", "change", "lab", "rivers"], ["grid", "basin", "sea", "city-air"]], \
    ("the capture holds no heat or water readouts, so those chapters are absent; the sun is W's", S["cap"])
assert S["noWater"] == [["air", "built", "sun", "heat", "rain"], ["air", "change", "lab"], ["grid", "sea", "city-air"]], S["noWater"]
assert S["noIsland"] == ["grid", "basin", "sea"]
assert S["noSun"] == ["air", "built", "heat", "rain"], "the sun is W.grid.sun, and absent with it"
assert S["empty"] == [["base", 0, 8, 4.5], ["community", 0, 7, 31.4], ["city", 0, 6, 219.4]], S["empty"]
assert S["capOnly"] == [["air"], [], ["sea"]], "every /wall block null: only what the doors' own issues hold is left"
print("  story: a missing block drops its chapter, a scale with none still stands")

assert S["at"] == [3, 0, 4, 0, 1, 0, 2], S["at"]
print("  story: chapterAt splits the day evenly and never runs past the last chapter")


# ---- the DOM half: the mount, on a fake MapLibre that records what the map is told ----
# A size changes at hour 0 (the hour before was 23, the widest frame of the size before): the camera makes one 2.6 s glide
# to chapter 0's frame of the new size, never first to its last chapter's frame. A chapter changing inside a size glides
# 1.6 s. Reduced motion turned on while the Wall shows takes the wind and the crests off the clock (CLOCK.on refuses then,
# but keeps a key already on), and destroy() lets the map go.
mount = json.loads(subprocess.run(["node", "-e", r"""
const fs = require('fs'), vm = require('vm');
const W = JSON.parse(fs.readFileSync('./tests/fixtures/wall-node1.json', 'utf8'));
const fits = [], layers = new Set(); let removed = 0;
class FakeMap {
  constructor() { this.ev = {}; FakeMap.last = this; }
  on(e, f) { (this.ev[e] ||= []).push(f); } fire(e) { (this.ev[e] || []).forEach(f => f()); }
  addSource() {} addLayer(l) { layers.add(l.id); } getLayer(id) { return layers.has(id); } addControl() {}
  setLayoutProperty() {} setPaintProperty() {} getSource() { return { setData() {} }; } fitBounds(b, o) { fits.push({ b, d: o.duration }); }
  getCenter() { return { toArray: () => [0, 0] }; } getZoom() { return 10; } querySourceFeatures() { return []; } project() { return { x: 0, y: 0 }; }
  remove() { removed++; }
}
const subs = new Map(); let reduced = false;
const CLOCK = { subs, reduced: () => reduced, on(id, fn) { if (reduced) return false; subs.set(id, fn); return true; }, off(id) { subs.delete(id); } };
const el = { innerHTML: '', firstChild: {}, lastChild: { getContext: () => null }, getBoundingClientRect: () => ({ width: 800, height: 600 }) };
const ctx = { maplibregl: { Map: FakeMap, Marker: class { setLngLat() { return this; } addTo() { return this; } remove() {} }, AttributionControl: class {} },
  CLOCK, view: () => 'wall', performance, devicePixelRatio: 1, console, W, el, location: { origin: 'http://n' },
  D: { issues: { air: { line: 15, series: { room: Array(24).fill(5) } } } },
  getComputedStyle: () => ({ getPropertyValue: () => '#123456' }), document: { createElement: () => ({}) } };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('./app/static/doors-wallmap.js', 'utf8'), ctx);
ctx.story = vm.runInContext(`wallStory(W, { issues: { air: { line: 15, stack: { room: { value: 5, provenance: 'live', n: 3 }, ring: { value: 9, provenance: 'partial', source: 'x' } } },
  land: { readouts: [{ metric: 'built_frac', value: 91, provenance: 'model' }] }, coast: { readouts: [{ metric: 'swell_height_m', value: 1.6, provenance: 'model' }] } } })`, ctx);
const S = ctx.story, M = vm.runInContext('wallMapMount(el, W, story, { vector: true })', ctx);
const box = pts => pts.reduce((b, [x, y]) => [[Math.min(b[0][0], x), Math.min(b[0][1], y)], [Math.max(b[1][0], x), Math.max(b[1][1], y)]], [[180, 90], [-180, -90]]);
const frame = (s, ch) => box([...S[s].cells.flatMap(c => c.ring), ...((ch && ch.fit) || [])]);
const out = {};
M.go(0, true); M.hour(23); FakeMap.last.fire('load');          // a redraw at hour 23: one cut, the base size's last chapter
out.first = fits.splice(0);
M.hour(0); out.chapter = fits.splice(0);                       // the day starts again: a chapter change inside the size
M.go(2); out.goAlone = fits.splice(0);                          // the size changes as the wallTick does it ...
M.hour(0); out.size = fits.splice(0);                           // ... and takes effect at its first hour
out.want = { first: frame(0, S[0].chapters[S[0].chapters.length - 1]), chapter: frame(0, S[0].chapters[0]), size: frame(2, S[2].chapters[0]),
  last2: frame(2, S[2].chapters[S[2].chapters.length - 1]) };
out.fxOn = subs.has('wall-fx');
reduced = true; subs.get('wall-fx')(performance.now()); out.fxReduced = subs.has('wall-fx');   // reduced motion turned on mid-run
reduced = false; M.hour(1); out.fxBack = subs.has('wall-fx');
M.destroy(); out.fxGone = !subs.has('wall-fx'); out.removed = removed;
console.log(JSON.stringify(out));
"""], capture_output=True, text=True, check=True).stdout)
assert len(mount["first"]) == 1 and mount["first"][0]["d"] == 0 and mount["first"][0]["b"] == mount["want"]["first"], mount["first"]
assert len(mount["chapter"]) == 1 and mount["chapter"][0]["d"] == 1600 and mount["chapter"][0]["b"] == mount["want"]["chapter"], mount["chapter"]
assert mount["goAlone"] == [], "go() moved the camera before the size's first hour"
assert len(mount["size"]) == 1 and mount["size"][0]["d"] == 2600 and mount["size"][0]["b"] == mount["want"]["size"] != mount["want"]["last2"], mount["size"]
print("  mount: a size change is one 2.6 s glide to its first chapter's frame; a chapter inside it 1.6 s; a redraw cuts")
assert mount["fxOn"] and not mount["fxReduced"] and mount["fxBack"] and mount["fxGone"] and mount["removed"] == 1, mount
print("  mount: reduced motion turned on mid-run takes the wind and the crests off the clock; destroy lets the map go")
