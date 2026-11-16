"""The Place report's sheet (docs/SPEC_place_report.md §4, §6, §8): the grid in metres, the legend, the house blurred to
its res-10 cell, and no text closer than the res-8 cell. app/static/doors-sheet.js is required as it is, and
doors-placemap.js is booted in node with a map that does nothing and a deck that records its layers, on node #1's capture
(app/issues/fixtures/node1-2026-10-06-figures.json). The capture goes in through stdin, never argv: Linux CI caps argv at
128 KB. Nothing here needs a browser; the print itself is the visual gate's `report` stage."""
import json
import math
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "app/issues/fixtures/node1-2026-10-06-figures.json"

PROG = r"""
const fs = require('fs'), vm = require('vm'), d3 = require('./app/static/d3.min.js');
const L = require('./app/static/doors-load.js');
const F = JSON.parse(fs.readFileSync(0, 'utf8')), D = L.buildD({ ...F, days: F.issues_days }, 'en');
const core = fs.readFileSync('./app/static/doors-core.js', 'utf8'), pick = n => core.match(new RegExp('^const ' + n + ' = .*$', 'm'))[0];
const src = ['doors-cake.js', 'doors-draw.js', 'doors-sheet.js', 'doors-placemap.js'].map(f => fs.readFileSync('./app/static/' + f, 'utf8')).join('\n');
const pm = fs.readFileSync('./app/static/doors-placemap.js', 'utf8');
const HOME = D.geometry.ladder.find(l => l.res === 10).id, AWAY = '8a95a4c84ffffff';
/* node #1's res-8 cell as GET /geo/cell rings it: [id, lat, lng, …], six decimals */
const C8 = ['8895a4c843fffff', -8.812929, 115.160071, -8.817406, 115.159467, -8.82056, 115.16294, -8.819237, 115.167017, -8.814759, 115.167621, -8.811605, 115.164148];
const HOUSE = ['x', -8.8196, 115.1641, -8.8199, 115.1646, -8.8195, 115.1650, -8.8190, 115.1649, -8.8188, 115.1644, -8.8191, 115.1640];
/* the node's answers: which res-10 cell each point is in. sc-19874 and the model stack on the house's point are in the
   house's cell; sc-19236 and the sea model are not */
const cellOf = p => /lat=-8\.820080|lat=-8\.819052/.test(p) ? HOME : AWAY;
const CAPS = [{ id: 1, kind: 'phone', at: [-8.8191, 115.1645], cell: HOME, analysis: { confirmed_by: 'T', findings: [{ scientific: 'Hibiscus rosa-sinensis' }] } },
  { id: 2, kind: 'phone', at: [-8.8150, 115.1700], cell: AWAY, analysis: { confirmed_by: 'T', findings: [{ scientific: 'Plumeria rubra' }] } }];
const noop = () => {};
const el = () => ({ innerHTML: '', textContent: '', hidden: false, style: {}, dataset: {}, kids: [], className: '', attrs: {}, setAttribute(k, v) { this.attrs[k] = v; },
  getAttribute(k) { return this.attrs[k]; }, appendChild(x) { this.kids.push(x); }, append(...x) { this.kids.push(...x); }, querySelector: () => null, querySelectorAll: () => [],
  addEventListener: noop, remove: noop, focus: noop, closest: () => null, contains: () => false, getContext: () => ({ setTransform: noop, clearRect: noop }), clientWidth: 900, clientHeight: 560 });
async function boot(tok) {
  const els = {}, map = el(), shots = [], styles = [];
  let last = [];
  const ask = p => {
    if (!tok && L.DOORS_LOCKED.test(p)) return Promise.resolve(new Response('{}', { status: 403 }));
    const b = p.startsWith('/geo/cell?id=' + HOME) ? { id: HOME, ring: HOUSE } : p.startsWith('/geo/cell?lat=') ? { id: cellOf(p) }
      : p.startsWith('/captures') ? CAPS : p.startsWith('/species') ? { species: [{ name: 'Plumeria rubra', rank: 'SPECIES' }] } : p.startsWith('/place/maps') ? { maps: [], palette: {} } : {};
    return Promise.resolve(new Response(JSON.stringify(b), { status: 200 }));
  };
  const layer = function (props) { return { id: props && props.id, props }; };
  const c = { D, d3, console, Response, URL, doorsLocal: L.doorsLocal, setTimeout, clearTimeout, $: q => (els[q] ||= el()), DOORS_TOKEN: () => (tok ? 't' : ''), DOORS_AUTH: () => ({}),
    doorsFetch: ask, UNLOCK_AT: 'Set up › This screen', sign: id => `<svg data-s="${id}"></svg>`, prov: w => w, lastRaw: () => null, plain: s => s, hhmm: s => s, when: s => s,
    dLabel: s => s, dayOf: s => s, CLOCK: { reduced: () => true, on: noop, off: noop }, view: () => 'place', location: { origin: 'http://node', hash: '#place' }, devicePixelRatio: 1,
    localStorage: { getItem: () => null, setItem: noop }, requestAnimationFrame: f => setTimeout(f, 0),
    document: { documentElement: { dataset: {} }, querySelector: () => null, querySelectorAll: () => [], createElement: () => el(), getElementById: () => null, activeElement: null,
      fullscreenEnabled: true, fullscreenElement: null, addEventListener: noop },
    maplibregl: { ScaleControl: function () {}, Map: function (opts) { return Object.assign(map, { opts, on: noop, once: (t, f) => f(), addControl: noop, getContainer: () => map,
      triggerRepaint: noop, getLayer: () => null, loaded: () => true, resize: noop, setStyle: s => styles.push(s.layers[0].paint['background-color']),
      getCanvas: () => ({ width: 1800, height: 1120, clientWidth: 900, clientHeight: 560, toDataURL: () => { shots.push(last.map(l => ({ id: l.id, data: l.props.data }))); return 'data:image/png;base64,AAAA'; } }),
      touchZoomRotate: { disableRotation: noop }, doubleClickZoom: { enable: noop, disable: noop }, getZoom: () => 14.5, getCenter: () => ({ lng: 115.164, lat: -8.819 }),
      project: ([x, y]) => ({ x: x * 1e4, y: -y * 1e4 }), unproject: ([x, y]) => ({ lng: x / 1e4, lat: -y / 1e4 }), easeTo: noop }); } },
    deck: new Proxy({}, { get: (t, k) => k === 'MapboxOverlay' ? function () { return { _deck: {}, setProps: x => { if (x.layers) last = x.layers; } }; } : layer }) };
  c.window = c; vm.createContext(c);
  vm.runInContext(['esc', 'fmt'].map(pick).join('\n') + '\n' + src + '\nwindow.placeMap()', c);
  await new Promise(r => setTimeout(r, 80));
  c.__PM.on.models = true; c.__PM.on.rings = true;   /* the model stack sits on the house's point; the rings are centred on it */
  const s = await c.placeSheet(true);
  return { s, shot: shots[0] || null, styles, after: { sheet: c.__PM.sheet, ids: last.map(l => l.id) },
    html: c.sheetHTML(D, { ...s, img: s.img ? 'data:image/png;base64,AAAA' : undefined }, C8) };
}
(async () => {
  const S = require('./app/static/doors-sheet.js');
  const LAYERS = eval(pm.match(/const LAYERS = \[[\s\S]*?\n\];/)[0] + '; LAYERS');
  global.cakeSections = require('./app/static/doors-cake.js').cakeSections;
  const grid = [];
  for (let m = 50; m <= 40000; m *= 1.002) for (const [w, h] of [[900, 560], [560, 900], [1440, 640]]) {
    const g = S.gridLines(w, h, m / Math.max(w, h)); grid.push([m, g.step, (w >= h ? g.xs : g.ys).length]);
  }
  const on = { own: true, public: true, wind: false, satonly: true, street: true, mine: true, images: true, rivers: true, terrain: true, species: false };
  console.log(JSON.stringify({ grid, legend: S.sheetLegend(LAYERS, on, 13), legendFar: S.sheetLegend(LAYERS, on, 11), tok: await boot(true), locked: await boot(false),
    point: D.point, version: D.health.version, home: HOME }));
})();
"""

out = subprocess.run(["node", "-e", PROG], input=FIX.read_text(), capture_output=True, text=True, cwd=ROOT)
assert out.returncode == 0, out.stderr[-3000:]
R = json.loads(out.stdout)

# the grid: a round step with five to eight lines on the longer side, from 50 m to 40 km across, either way up
bad = [g for g in R["grid"] if not 5 <= g[2] <= 8]
assert not bad, f"{len(bad)} widths give a grid of other than five to eight lines, e.g. {bad[:4]}"
steps = {g[1] for g in R["grid"]}
assert all(round(s / 10 ** math.floor(math.log10(s)), 6) in (1, 2, 2.5, 5) for s in steps), sorted(steps)
print(f"  report: the grid gives five to eight lines on the longer side at every width from 50 m to 40 km ({len(steps)} round steps)")

# the legend: the layers on and in view, under their cake section, in the cake's order, each with its source
assert R["legend"] == [
    {"name": "microclimate", "rows": [{"name": "Outdoor kit", "src": "this house"}, {"name": "Stations", "src": "nearby"}]},
    {"name": "built", "rows": [{"name": "Satellite only", "src": "satellite"}]},
    {"name": "water", "rows": [{"name": "Rivers", "src": "HydroRIVERS"}]},
    {"name": "ground", "rows": [{"name": "Terrain", "src": "GLO-30"}]},
    {"name": "frame", "rows": [{"name": "Node cell", "src": "H3"}, {"name": "Street map", "src": "OSM"}, {"name": "Images", "src": "this house"}]},
], R["legend"]
assert [s["name"] for s in R["legendFar"]] == ["microclimate", "water", "ground", "frame"], "a layer out of its zoom is not in the legend"
print("  report: the legend lists the layers on, under their section of the cake, in its order, with their sources")

T = R["tok"]
shot = {l["id"]: l["data"] for l in T["shot"]}
house = R["home"]
assert "node" not in shot and shot.get("house") == [{"ring": [[115.1641, -8.8196], [115.1646, -8.8199], [115.165, -8.8195], [115.1649, -8.819], [115.1644, -8.8188], [115.164, -8.8191], [115.1641, -8.8196]]}], \
    ("on the sheet the house is its res-10 cell, filled, and not the ring at its point", shot.get("house"), list(shot))
assert [s["sensor_id"] for s in shot["own"]] == ["sc-19236"], ("no kit inside the house's res-10 cell is a point", shot["own"])
assert [c["id"] for c in shot["images"]] == [2] and [d["c"]["id"] for d in shot["species"]] == [2], "no image inside the house's cell is a point, nor its species"
assert all(g["ss"][0]["sensor_id"] == "marine-point" for g in shot["models"]) and shot["models"], ("the model stack on the house's point is left off", shot["models"])
assert "rings" not in shot and "measure" not in shot, "nothing drawn round the house's point"
assert T["styles"] == ["#DCE2E6", "#0E1012"] and T["after"]["sheet"] is None and "node" in T["after"]["ids"] and "house" not in T["after"]["ids"], \
    ("Paper draws the light palette for the picture, then the screen is black again and draws as before", T["styles"], T["after"])
assert [s["name"] for s in T["s"]["legend"]][:1] == ["microclimate"] and "Rings" not in json.dumps(T["s"]["legend"]), "the rings are not drawn on the sheet, so not in its legend"
print("  report: the sheet's layers hold no kit, model or image point inside the house's res-10 cell, only the cell, and the screen comes back")

# no text on the sheet holds the house's point, with the token, where /health gives this screen the point itself
lon, lat = R["point"]
html = T["html"]
for v in (lat, lon):
    for t in {f"{v}", f"{v:.3f}", f"{v:.4f}"}:
        assert t not in html, f"the sheet says {t}, the house's point"
assert "-8.8161, 115.1635" in html and "cell 8895a4c843fffff" in html and "Cell, res" in html, "the coordinates line is the res-8 cell's centre and id"
assert f"Made on PLANETAI {R['version']}" in html and "Natural Earth" in html, "the credits and the version"
assert re.search(r"\d+(\.\d+)? km across · grid \d", html), "the sheet's width and grid step"
print("  report: no text on the sheet is closer than the res-8 cell; the coordinates are its centre")

X = R["locked"]
assert X["shot"] is None and "img" not in X["s"] and "stays on this house’s own screens" in X["html"] and "<svg" not in X["html"], \
    ("without the token no picture is taken and the node's sentence stands where the map would be", X["html"][:300])
for v in (lat, lon):
    assert f"{v}" not in X["html"]
print("  report: without the token the sheet has no map, only the node's sentence")
