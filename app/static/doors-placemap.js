'use strict';
/* PLACE · the map workbench (R36, 7 Oct 2026). MapLibre draws the base, deck.gl draws the node's data over it.

   REFERENCE LOCK (Refero, docs in the R36 note):
   - Mapbox's cartographic rule: the map is neutral and the data is the only colour. One signal hue, the node's
     --cells blue, for the cell and focus; orange stays the satellite's alone. No second accent.
   - mono's architectural chrome: square corners, 1 px ink rules, tracked mono labels. Nothing rounded, no shadow.
   - Option A, "landscape workbench" (Tomas, 15 Oct 2026, from three reference-locked options): the map full width, the
     layer groups a strip above it (Windy), the scale rail and the tools on the map, labels on leaders to a ruled margin,
     the inspector one line under the map. The layer list is still the legend (a swatch per row, Mapbox Studio).

   SCALE. The H3 resolution drawn follows the zoom: the finest rung whose cell is at least 56 px to an edge on
   screen. The presets fly to the node's own cell at that rung, so a press and a scroll agree. Rungs 6 and coarser
   (cells that may leave the machine) are dotted, as on the node's ladder.

   THE NODE COMPUTES, THE PAGE DRAWS (R36.1, and R40 for every door). No h3-js and no distance here. The grid, the node's cell at each rung,
   the radio cell, the rings, every measured metre and every cell fact are answers from the node's GET /geo/*
   routes, asked with this screen's token (token-only at every SHARE_LEVEL); the plan is the node's own
   GET /place/geojson. Without the token the map says what it is not drawing, and why. */

(function () {
const PM = { map: null, overlay: null, theme: null, res: 8, tool: 'inspect', measure: [], hover: null, pick: null,
  on: {}, alpha: {}, gopen: null, plan: null, land: null };

/* ---------------------------------------------------------------- the palette, by register */
const PAL = {
  light: { sea: '#DCE2E6', land: '#F1EFEB', green: '#E1E6DB', road: '#FFFFFF', casing: '#D5D1CA', bldg: '#CFCBC4',
    coast: '#B9B4AC', built: '#E9E6E1', sand: '#EEE9DE', farm: '#ECEDE5', label: '#5F5A54', lhalo: '#F1EFEB', major: '#FFFFFF', path: '#B9B4AC', ink: [23, 23, 23], mute: [95, 90, 84], cells: [32, 56, 141], sat: [219, 114, 0], halo: [241, 239, 235] },
  dark: { sea: '#0E1012', land: '#17191D', green: '#1A201C', road: '#30353D', casing: '#17191D', bldg: '#2B2E34',
    coast: '#3A3F47', built: '#1C1F23', sand: '#1E1F1C', farm: '#191C19', label: '#A3A19F', lhalo: '#17191D', major: '#3C424B', path: '#3A3F47', ink: [249, 245, 242], mute: [163, 161, 159], cells: [127, 165, 232], sat: [255, 147, 30], halo: [23, 25, 29] },
};
const P = () => PAL[PM.theme === 'dark' ? 'dark' : 'light'];

/* ---------------------------------------------------------------- scales: named rungs of the ladder */
const SCALES = [[10, 'Street'], [9, 'Block'], [8, 'Cell'], [7, 'Village'], [6, 'District'], [4, 'Island'], [3, 'Radio']];
const EDGE = r => (D.geometry.ladder.find(l => l.res === r) || {}).edge_m || 1;
const mPerPx = z => 40075016.686 * Math.cos(D.point[1] * Math.PI / 180) / (512 * 2 ** z);
const resFor = z => { for (let r = 12; r >= 2; r--) if (EDGE(r) / mPerPx(z) >= 56) return r; return 2; };
const mayLeave = r => r <= 6;

/* ---------------------------------------------------------------- the layer registry: one row per layer, by pack.
   A pack that grows a layer adds one entry here. `empty` is a layer the pack would draw and cannot yet: the row
   stays, says so in the node's words, and cannot be switched on.
   FIVE ON (Tomas, 15 Oct): the street, the node's cell, its own sensors, the public stations and the images; every other
   row starts off, and a group with nothing on starts collapsed with its count. A row with `parent` sits under it and
   is counted with it. The street map carries its names: one row, not two. */
const LAYERS = [
  { id: 'street', group: 'Base', pack: 'place', name: 'Street map', sub: 'OpenStreetMap, with its names, kept on this node', sw: 'fill-land', on: true, still: true },
  { id: 'imagery', group: 'Base', pack: 'earth-engine', name: 'Satellite, 10 m', sub: 'Sentinel-2, composited by this node', sw: 'fill-photo', on: false, need: 'imagery' },
  { id: 'drone', group: 'Base', pack: 'place', name: 'Drone imagery', sub: 'OpenAerialMap, where somebody flew', sw: 'fill-photo', on: false, need: 'drone', minz: 13 },
  { id: 'grid', group: 'Grid', pack: 'core', name: 'H3 cells at this scale', sub: 'dotted where a cell may leave', sw: 'line-grid', on: false },
  { id: 'mine', group: 'Grid', pack: 'core', name: 'The cell it stands in', sub: 'at the resolution in view', sw: 'fill-cell', on: true },
  { id: 'radio', group: 'Grid', pack: 'reticulum', name: 'What leaves by radio', sub: 'the res-3 cell it announces', sw: 'line-dot', on: false, maxz: 10 },
  { id: 'own', group: 'Readings', pack: 'core', name: 'This house’s stations', sub: 'filled', sw: 'pt-own', on: true },
  { id: 'public', group: 'Readings', pack: 'nearby', name: 'Public stations', sub: 'hollow · display only, never alert', sw: 'pt-pub', on: true },
  { id: 'models', group: 'Readings', pack: 'core', name: 'Model points', sub: 'sea, air, land, weather', sw: 'pt-model', on: false },
  { id: 'rings', group: 'Readings', pack: 'nearby', name: 'Distance rings', sub: '2, 5 and 15 km', sw: 'line-ring', on: false },
  /* the household's own images (SPEC_eyes step 1) and the species somebody here confirmed in them (SPEC_species §4),
     token-only: GET /captures, GET /species. GBIF's open records are a count per species (the table below the map),
     never points, so nothing hollow is drawn for them. */
  { id: 'images', group: 'Images', pack: 'core', name: 'Images', sub: 'what the household added', sw: 'pt-img', on: true },
  { id: 'species', group: 'Images', pack: 'core', name: 'Species confirmed here', sub: 'at the image’s point', sw: 'pt-sp', on: true, parent: 'images' },
  { id: 'satonly', group: 'Packs', pack: 'place', name: 'Only the satellite knows', sub: 'buildings missing from OSM', sw: 'fill-sat', on: false, minz: 12.5 },
  { id: 'wind', group: 'Packs', pack: 'forecast', name: 'Wind, moving', sub: 'Open-Meteo field round the node', sw: 'pt-wind', on: false, need: 'wind', still: true },
  { id: 'labs', group: 'Packs', pack: 'make', name: 'Places to make', sub: 'from fablabs.io', sw: 'pt-lab', on: false },
  /* no shape on this map, whatever the node holds: the change is a picture in UTM metres with its own words burned in
     (Place › What changed draws it), and the Index's cells are a table of themes, not places. packRows() says which. */
  { id: 'earth', group: 'Packs', pack: 'earth', name: 'Land change raster', sub: 'AlphaEarth, year on year', sw: 'fill-photo', empty: true },
  { id: 'index', group: 'Packs', pack: 'index', name: 'Fab City Index cells', sub: 'the 20 cells for this place', sw: 'fill-cell', empty: true },
  { id: 'peers', group: 'Packs', pack: 'reticulum', name: 'Nodes heard nearby', sub: 'their announced cells', sw: 'line-dot', empty: true },
];
LAYERS.forEach(l => { PM.on[l.id] = !!l.on && !l.empty; PM.alpha[l.id] = 1; });
const ON = () => LAYERS.filter(l => PM.on[l.id] && !l.parent).length;   // the header's count and the phone's button
/* a species as a row says it: genus and epithet, without the author GBIF appends */
const short = t => String(t.name || '').split(' ').slice(0, t.rank === 'GENUS' ? 1 : 2).join(' ');
/* every confirmed living finding, at its image's point (the node's `at`); a model's guess is not one */
const speciesMarks = () => (PM.caps || []).filter(c => c.analysis && c.analysis.confirmed_by)
  .flatMap(c => (c.analysis.findings || []).filter(f => f.taxon || f.scientific).map(f => ({ c, t: f.taxon ? short(f.taxon) : f.scientific })));
/* after GET /captures and /species: none is a row that says so; a screen without the token is told why */
function imageRows() {
  const im = LAYERS.find(l => l.id === 'images'), sp = LAYERS.find(l => l.id === 'species'), C = PM.caps || [], S = (PM.species || {}).species || [];
  const kinds = d3.rollups(C, v => v.length, c => c.kind).map(([k, v]) => `${v} ${(KIND[k] || k).toLowerCase()}`).join(', ');
  im.locked = sp.locked = !PM.caps; im.empty = !C.length; sp.empty = !S.length;
  im.none = 'none yet · + Add an image, above the map'; sp.none = 'none confirmed yet · confirm what an image shows in Data › Images';
  im.sub = `${C.length} · ${kinds}`;
  sp.sub = `${S.length} confirmed · ${S.slice(0, 2).map(short).join(', ')}${S.length > 2 ? ', …' : ''}`;
  PM.on.images = !im.empty; PM.on.species = !sp.empty;
}

/* ---------------------------------------------------------------- asking the node */
const API = '/';
const ask = p => doorsFetch(API + p).then(async r => {
  if (r.ok) return r.json();
  const b = await r.json().catch(() => ({}));
  throw new Error(typeof b.detail === 'string' ? b.detail : `GET /${p.split('?')[0]} answered ${r.status}`);
});
const lngLat = s => [s.lon, s.lat];
/* a cells_ll row, [id, lat, lng, lat, lng, …], as the closed [lng, lat] ring deck.gl draws: a reorder, not a computation */
const loop = row => { const r = []; for (let i = 1; i < row.length; i += 2) r.push([row[i + 1], row[i]]); r.push(r[0]); return r; };
const fmtM = m => m >= 1000 ? `${(m / 1000).toFixed(m >= 10000 ? 1 : 2)} km` : `${Math.round(m)} m`;
const CELLS = new Map();
const cellFacts = id => { if (!CELLS.has(id)) CELLS.set(id, ask(`geo/cell?id=${id}`)); return CELLS.get(id); };
const cellAt = (lon, lat, r) => ask(`geo/cell?lat=${lat.toFixed(6)}&lon=${lon.toFixed(6)}&res=${r}`);
const fromNode = (lon, lat) => ask(`geo/measure?from_node=true&path=${lon},${lat}`).then(m => m.total_m);
/* one fact, one figure, one unit (Tomas, 15 Oct: "0.64 km²" beside "64.0 ha"): an area is always km², as the lede says it */
const area = m2 => `${(m2 / 1e6).toFixed(m2 >= 1e8 ? 0 : m2 >= 1e5 ? 2 : 3)} km²`;

/* The grid in view, asked again whenever the view settles. A slow answer for an old view is dropped. */
let GRID = null, GSEQ = 0, RINGS = null, RADIO = null;
async function loadGrid() {
  const b = PM.map.getBounds(), seq = ++GSEQ;
  const box = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()].map(v => v.toFixed(5)).join(',');
  try {
    const g = await ask(`geo/grid?res=${PM.res}&bbox=${box}`);
    if (seq !== GSEQ) return;
    GRID = { res: g.res, edge_m: g.edge_m, node: g.node[0], nodeRing: loop(g.node), cells: g.cells_ll.map(r => ({ id: r[0], path: loop(r) })) };
    offline(null);
  } catch (e) { if (seq === GSEQ) { GRID = null; offline(e.message); } }
  redraw(); if (!PM.pick && !MEASURING()) facts();
}
/* Said once, on the map, when the node does not answer: what is missing and why, never a blank grid. */
function offline(why) {
  PM.offline = why;
  let n = document.querySelector('.nonode');
  if (!why) { if (n) n.remove(); return; }
  if (!n) { n = document.createElement('p'); n.className = 'nonode'; (PM.map ? PM.map.getContainer() : $('#map')).appendChild(n); }
  n.textContent = 'This map is locked on this screen, because together its layers say where the house is. Unlock this screen in Set up › This screen to draw it.';
  n.title = why;
}

/* ---------------------------------------------------------------- the base style: everything from the node's disk */
/* GET /ground/* (planetai-node): OpenStreetMap vector tiles cut from Protomaps' build, the label fonts, this node's
   own Sentinel-2 composite and any OpenAerialMap drone mosaic, fetched once by `planetai run place basemap` and
   `planetai run earth-engine basemap`. Nothing here asks a tile server. Without the vector tiles the plan from
   /place/geojson draws instead, as before. Rasters sit over the street map and under the names: a hybrid. */
const GREEN = ['park', 'wood', 'forest', 'garden', 'grass', 'grassland', 'scrub', 'nature_reserve', 'golf_course', 'cemetery', 'meadow', 'national_park', 'protected_area', 'recreation_ground', 'village_green', 'pitch', 'playground'];
const BUILT = ['industrial', 'commercial', 'retail', 'university', 'school', 'college', 'hospital', 'military', 'railway', 'airfield', 'aerodrome', 'runway', 'pedestrian', 'parking', 'platform'];
const SAND = ['beach', 'sand', 'bare_rock', 'scree'];
function style() {
  const p = P(), k = v => ['==', ['get', 'kind'], v], any = l => ['in', ['get', 'kind'], ['literal', l]], G = PM.ground || {}, V = !!G.vector;
  const W = (lo, hi) => ['interpolate', ['exponential', 1.6], ['zoom'], 12, lo, 18, hi];
  /* one zoom curve per kind: MapLibre wants the zoom outermost and the kind inside each stop */
  const WK = (h, m, n) => ['interpolate', ['exponential', 1.6], ['zoom'], 12, ['match', ['get', 'kind'], 'highway', h[0], 'major_road', m[0], n[0]],
    18, ['match', ['get', 'kind'], 'highway', h[1], 'major_road', m[1], n[1]]];
  const sources = { land: { type: 'geojson', data: PM.land },
    plan: { type: 'geojson', data: PM.plan || { type: 'FeatureCollection', features: [] } } };
  if (V) sources.v = { type: 'vector', tiles: [location.origin + API + 'ground/vector/{z}/{x}/{y}.pbf'], minzoom: 0, maxzoom: 15 };
  if (G.imagery) sources.imagery = { type: 'raster', tiles: [location.origin + API + 'ground/imagery/{z}/{x}/{y}.png'], tileSize: 256, minzoom: 8, maxzoom: 15 };
  if (G.drone) sources.drone = { type: 'raster', tiles: [location.origin + API + 'ground/drone/{z}/{x}/{y}.png'], tileSize: 256, minzoom: 14, maxzoom: 18 };
  const L = [
    { id: 'sea', type: 'background', paint: { 'background-color': p.sea } },
    { id: 'land-fill', type: 'fill', source: 'land', paint: { 'fill-color': p.land } },
    { id: 'land-edge', type: 'line', source: 'land', maxzoom: V ? 9 : 24, paint: { 'line-color': p.coast, 'line-width': 0.8 } },
  ];
  if (V) L.push(
    { id: 'v-earth', type: 'fill', source: 'v', 'source-layer': 'earth', filter: k('earth'), paint: { 'fill-color': p.land } },
    { id: 'v-farm', type: 'fill', source: 'v', 'source-layer': 'landuse', filter: any(['farmland', 'farm', 'orchard', 'vineyard', 'allotments']), paint: { 'fill-color': p.farm } },
    { id: 'v-green', type: 'fill', source: 'v', 'source-layer': 'landuse', filter: any(GREEN), paint: { 'fill-color': p.green } },
    { id: 'v-built', type: 'fill', source: 'v', 'source-layer': 'landuse', filter: any(BUILT), paint: { 'fill-color': p.built } },
    { id: 'v-sand', type: 'fill', source: 'v', 'source-layer': 'landuse', filter: any(SAND), paint: { 'fill-color': p.sand } },
    { id: 'v-water', type: 'fill', source: 'v', 'source-layer': 'water', filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': p.sea } },
    { id: 'v-stream', type: 'line', source: 'v', 'source-layer': 'water', filter: ['==', ['geometry-type'], 'LineString'], minzoom: 12, paint: { 'line-color': p.sea, 'line-width': W(0.6, 3) } },
    { id: 'v-coast', type: 'line', source: 'v', 'source-layer': 'water', filter: ['==', ['geometry-type'], 'Polygon'], minzoom: 9, paint: { 'line-color': p.coast, 'line-width': 0.6 } },
    { id: 'v-path', type: 'line', source: 'v', 'source-layer': 'roads', filter: any(['path', 'other']), minzoom: 14, paint: { 'line-color': p.path, 'line-width': 0.8, 'line-dasharray': [2, 1.5] } },
    { id: 'v-casing', type: 'line', source: 'v', 'source-layer': 'roads', filter: any(['minor_road', 'major_road', 'highway']), minzoom: 12, layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': p.casing, 'line-width': WK([2.4, 22], [1.8, 18], [0.9, 13]) } },
    { id: 'v-road', type: 'line', source: 'v', 'source-layer': 'roads', filter: any(['minor_road', 'major_road', 'highway']), layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ['match', ['get', 'kind'], 'minor_road', p.road, p.major], 'line-width': WK([1.6, 19], [1.1, 15], [0.5, 10.5]) } },
    { id: 'v-bldg', type: 'fill', source: 'v', 'source-layer': 'buildings', minzoom: 13, paint: { 'fill-color': p.bldg, 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 13, 0, 14, 1] } });
  else L.push(
    { id: 'plan-green', type: 'fill', source: 'plan', filter: k('green'), minzoom: 12, paint: { 'fill-color': p.green } },
    { id: 'plan-casing', type: 'line', source: 'plan', filter: k('road'), minzoom: 12, layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': p.casing, 'line-width': W(1.2, 14) } },
    { id: 'plan-road', type: 'line', source: 'plan', filter: k('road'), minzoom: 12, layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': p.road, 'line-width': W(0.6, 11) } },
    { id: 'plan-bldg', type: 'fill', source: 'plan', filter: k('building'), minzoom: 12.5, paint: { 'fill-color': p.bldg, 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 12.5, 0, 13.5, 1] } });
  if (G.imagery) L.push({ id: 'imagery', type: 'raster', source: 'imagery', layout: { visibility: 'none' }, paint: { 'raster-fade-duration': 0 } });
  if (G.drone) L.push({ id: 'drone', type: 'raster', source: 'drone', minzoom: 13, layout: { visibility: 'none' }, paint: { 'raster-fade-duration': 0 } });
  L.push({ id: 'plan-sat', type: 'fill', source: 'plan', filter: k('sat'), minzoom: 12.5,
    paint: { 'fill-color': `rgb(${p.sat})`, 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 12.5, 0, 13.5, 0.75] } });
  if (V && G.glyphs) {
    const txt = (size, color = p.label) => ({ 'text-color': color, 'text-halo-color': p.lhalo, 'text-halo-width': 1.4 });
    L.push(
      { id: 'v-road-label', type: 'symbol', source: 'v', 'source-layer': 'roads', minzoom: 14.5, filter: ['has', 'name'],
        layout: { 'symbol-placement': 'line', 'text-field': ['get', 'name'], 'text-font': ['Noto Sans Regular'], 'text-size': 10.5, 'text-letter-spacing': 0.02 }, paint: txt() },
      { id: 'v-poi-label', type: 'symbol', source: 'v', 'source-layer': 'pois', minzoom: 16, filter: ['has', 'name'],
        layout: { 'text-field': ['get', 'name'], 'text-font': ['Noto Sans Italic'], 'text-size': 10, 'text-max-width': 8 }, paint: txt() },
      { id: 'v-place-label', type: 'symbol', source: 'v', 'source-layer': 'places', filter: ['has', 'name'],
        layout: { 'text-field': ['get', 'name'], 'text-font': ['Noto Sans Medium'], 'text-max-width': 7, 'text-letter-spacing': 0.04,
          'text-transform': ['match', ['get', 'kind'], ['region', 'country'], 'uppercase', 'none'],
          'text-size': ['match', ['get', 'kind'], 'country', 13, 'region', 12, 'locality', 12.5, 11] }, paint: txt(12, p.ink ? `rgb(${p.ink})` : p.label) });
  }
  return { version: 8, glyphs: location.origin + API + 'ground/glyphs/{fontstack}/{range}.pbf', sources, layers: L };
}
/* which base style layers each registry row owns */
const OWNS = { street: ['land-fill', 'land-edge', 'v-earth', 'v-farm', 'v-green', 'v-built', 'v-sand', 'v-water', 'v-stream', 'v-coast', 'v-path', 'v-casing', 'v-road', 'v-bldg', 'plan-green', 'plan-casing', 'plan-road', 'plan-bldg',
    'v-road-label', 'v-poi-label', 'v-place-label'],
  imagery: ['imagery'], drone: ['drone'], satonly: ['plan-sat'] };
function applyBase() {
  if (!PM.map) return;
  for (const [id, ls] of Object.entries(OWNS)) for (const l of ls) {
    if (!PM.map.getLayer(l)) continue;
    PM.map.setLayoutProperty(l, 'visibility', PM.on[id] ? 'visible' : 'none');
    const t = PM.map.getLayer(l).type;
    if (t === 'raster') PM.map.setPaintProperty(l, 'raster-opacity', PM.alpha[id]);
    if (l === 'plan-sat') PM.map.setPaintProperty(l, 'fill-opacity', ['interpolate', ['linear'], ['zoom'], 12.5, 0, 13.5, 0.75 * PM.alpha[id]]);
  }
}
/* What the node holds of its own map, and the credit each layer owes (ODbL, CC BY, Copernicus). */
function groundRows() {
  const m = (PM.meta && PM.meta.layers) || {}, mb = b => b ? `${(b / 1e6).toFixed(1)} MB` : '', G = PM.ground || {};
  /* no /ground/meta at all is this screen being refused it, not a node without a map: say which */
  const locked = !PM.meta;
  const set = (id, sub, empty, why) => { const l = LAYERS.find(x => x.id === id); if (sub) l.sub = sub; l.empty = !!empty; l.why = why; l.locked = locked && !!empty; if (empty) PM.on[id] = false; };
  set('street', G.vector ? `OpenStreetMap ${(m.vector || {}).build ? `build ${m.vector.build.slice(0, 8)}` : ''} · ${mb((m.vector || {}).bytes)} on this node` : locked ? 'token-only · unlock this screen in Set up › This screen' : 'the plan from /place/geojson; no street map on this node yet');
  const im = m.imagery || {};
  set('imagery', G.imagery ? `Sentinel-2, ${im.passes} passes, ${(im.from || '').slice(0, 7)} to ${(im.to || '').slice(0, 7)} · ${mb(im.bytes)}` : null, !G.imagery, 'planetai run earth-engine basemap');
  const dr = m.drone || {}, ms = dr.mosaics || [];
  const W = PM.wind;
  set('wind', W ? `Open-Meteo, ${W.n * W.n} points over ${W.km * 2} km, hourly · read ${hhmm(W.fetched)}` : null, !W,
    'FORECAST_OPENMETEO=1, then planetai run forecast windfield');
  set('drone', G.drone && ms.length ? `${ms.map(x => `${x.provider}, ${Math.round(x.gsd_m * 100)} cm, ${x.date}`).join(' · ')} · ${mb(dr.bytes)}` : null, !G.drone, 'planetai run place basemap --only drone');
}
/* The two rows above that cannot draw: from what the page already holds, where the node's answer is instead of "the pack
   has nothing here yet", which said so beside 6 of 20 Index values and a working What changed (14 Oct). */
function packRows() {
  const ix = LAYERS.find(l => l.id === 'index'), ea = LAYERS.find(l => l.id === 'earth');
  const nI = new Set(D.index_cells.map(c => c.cell)).size, nE = ((D.earth || {}).changes || []).length;
  ix.none = nI ? `${nI} of 20 hold a value · a table, not a shape: <a href="#node/cells">Node › Index cells</a>` : null;
  ea.none = nE ? `${nE} comparison${nE === 1 ? '' : 's'} · a count, not a shape: What changed, above the map` : null;
}
function credits() {
  const m = (PM.meta && PM.meta.layers) || {}, c = [];
  if (PM.on.street && PM.ground && PM.ground.vector) c.push('© OpenStreetMap contributors · Protomaps');
  if (PM.on.imagery && m.imagery) c.push(m.imagery.attribution);
  if (PM.on.drone && m.drone) c.push((m.drone.mosaics || []).map(x => `${x.provider} via OpenAerialMap, CC BY 4.0`).join(' · '));
  if (PM.on.wind && PM.wind) c.push('wind: Open-Meteo, CC BY 4.0');
  c.push('Natural Earth');
  const el = $('#mapcredit'); if (el) el.textContent = c.join(' · ');
}

/* ---------------------------------------------------------------- the data, drawn by deck.gl */
function layers() {
  const p = P(), Dk = deck, a = id => PM.alpha[id], z = PM.map.getZoom(), r = PM.res, A = (c, o) => [...c, Math.round(o * 255)];
  const vis = l => PM.on[l.id] && (l.minz == null || z >= l.minz) && (l.maxz == null || z <= l.maxz);
  const L = Object.fromEntries(LAYERS.map(l => [l.id, vis(l)]));
  const px = { lineWidthUnits: 'pixels', radiusUnits: 'pixels', widthUnits: 'pixels' }, out = [];   // PathLayer reads widthUnits
  const dashed = new Dk.PathStyleExtension({ dash: true });
  const S = D.sensors.filter(s => s.lat != null);
  const G = GRID, gr = G ? G.res : r;

  if (L.rings && RINGS) {
    out.push(new Dk.PathLayer({ id: 'rings', data: RINGS, getPath: d => d.path, ...px,
      getColor: A(p.ink, .45 * a('rings')), getWidth: 1, extensions: [dashed], getDashArray: [4, 4] }));
    out.push(new Dk.TextLayer({ characterSet: 'auto', id: 'rings-l', data: RINGS.map(x => ({ t: `${x.km} km`, p: x.path[0] })), getPosition: d => d.p, getText: d => d.t,
      getSize: 11, fontFamily: 'JetBrains Mono, monospace', getColor: A(p.mute, a('rings')), getPixelOffset: [0, -9], background: true, getBackgroundColor: A(p.halo, .9), backgroundPadding: [3, 1] }));
  }
  if (L.radio && RADIO) {
    out.push(new Dk.PathLayer({ id: 'radio', data: [RADIO], getPath: d => d.path, ...px, pickable: true,
      getColor: A(p.ink, .7 * a('radio')), getWidth: 1.5, extensions: [dashed], getDashArray: [1, 4], _kind: 'radio' }));
  }
  if (L.grid && G) {
    const cells = G.cells.filter(c => c.id !== G.node);
    /* over a photograph the grid is drawn light on a dark edge, as the svg ground draws hairlines over tiles */
    const photo = (PM.on.imagery && PM.ground.imagery && z >= 8) || (PM.on.drone && PM.ground.drone && z >= 13);
    const gc = photo ? A([255, 255, 255], .8 * a('grid')) : A(p.ink, (z >= 12.5 ? .3 : .22) * a('grid'));
    if (photo) out.push(new Dk.PathLayer({ id: 'grid-edge', data: cells, getPath: d => d.path, ...px, getColor: [0, 0, 0, Math.round(90 * a('grid'))], getWidth: 2.6 }));
    /* solid and dotted are two layers, not one with a switched extension: deck.gl cannot swap a layer's shader */
    out.push(mayLeave(gr)
      ? new Dk.PathLayer({ id: 'grid-dot', data: cells, getPath: d => d.path, ...px, pickable: true, autoHighlight: true, highlightColor: A(p.cells, .35),
        getColor: gc, getWidth: 1.2, extensions: [dashed], getDashArray: [1.5, 3] })
      : new Dk.PolygonLayer({ id: 'grid', data: cells, getPolygon: d => d.path, ...px, pickable: true, autoHighlight: true, highlightColor: A(p.cells, .06),
        filled: true, getFillColor: [0, 0, 0, 0], getLineColor: gc, getLineWidth: 1 }));
  }
  if (L.mine && G) {
    out.push(new Dk.PolygonLayer({ id: 'mine', data: [{ id: G.node, ring: G.nodeRing }], getPolygon: d => d.ring, ...px, pickable: true,
      filled: true, getFillColor: A(p.cells, .12 * a('mine')), getLineColor: A(p.cells, a('mine')), getLineWidth: mayLeave(gr) ? 0 : 2.5 }));
    if (mayLeave(gr)) out.push(new Dk.PathLayer({ id: 'mine-dot', data: [{ path: G.nodeRing }], getPath: d => d.path, ...px,
      getColor: A(p.cells, a('mine')), getWidth: 2.5, extensions: [dashed], getDashArray: [2, 2.5] }));
  }
  if (L.models) {
    const M = S.filter(s => s.kind === 'model' || s.kind === 'map');
    /* every model point sits on the node's point except the sea's: one square for the stack, one for the sea */
    const groups = d3.groups(M, s => `${s.lat.toFixed(4)},${s.lon.toFixed(4)}`).map(([, ss]) => ({ ss, p: lngLat(ss[0]) }));
    out.push(new Dk.TextLayer({ characterSet: 'auto', id: 'models', data: groups, getPosition: d => d.p, getText: () => '◇', getSize: 18, pickable: true,
      fontFamily: 'JetBrains Mono, monospace', getColor: A(p.ink, a('models')), getPixelOffset: d => d.ss.length > 1 ? [14, -14] : [0, 0] }));
  }
  if (L.labs) {
    const F = S.filter(s => s.kind === 'facility');
    out.push(new Dk.TextLayer({ characterSet: 'auto', id: 'labs', data: F, getPosition: lngLat, getText: () => '△', getSize: 16, pickable: true,
      fontFamily: 'JetBrains Mono, monospace', getColor: A(p.ink, a('labs')) }));
    out.push(new Dk.TextLayer({ characterSet: 'auto', id: 'labs-l', data: F, getPosition: lngLat, getText: s => s.name, getSize: 11, fontFamily: 'Figtree, sans-serif',
      getColor: A(p.ink, .8 * a('labs')), getTextAnchor: 'start', getPixelOffset: [12, 0], background: true, getBackgroundColor: A(p.halo, .85), backgroundPadding: [3, 1] }));
  }
  if (L.images && PM.caps) {
    out.push(new Dk.TextLayer({ characterSet: 'auto', id: 'images', data: PM.caps, getPosition: c => [c.at[1], c.at[0]],
      getText: () => '■', getSize: 14, pickable: true, fontFamily: 'JetBrains Mono, monospace', getColor: A(p.ink, a('images')),
      background: true, getBackgroundColor: A(p.halo, .9 * a('images')), backgroundPadding: [1, 1] }));
  }
  /* a species somebody here confirmed: filled, at its image's point; named in the margin, never beside it (option A) */
  if (L.species && PM.caps) {
    out.push(new Dk.TextLayer({ characterSet: 'auto', id: 'species', data: speciesMarks(), getPosition: d => [d.c.at[1], d.c.at[0]], getText: () => '◆', getSize: 15,
      pickable: true, fontFamily: 'JetBrains Mono, monospace', getColor: A(p.ink, a('species')), getPixelOffset: [0, -13] }));
  }
  const st = S.filter(s => s.kind === 'sensor');
  if (L.public) {
    out.push(new Dk.ScatterplotLayer({ id: 'public', data: st.filter(s => !s.local), getPosition: lngLat, ...px, pickable: true, autoHighlight: true,
      highlightColor: A(p.cells, 1), stroked: true, filled: true, getRadius: 4.5, getFillColor: A(p.halo, a('public')),
      getLineColor: A(p.ink, a('public')), getLineWidth: 1.4 }));
  }
  if (L.own) {
    out.push(new Dk.ScatterplotLayer({ id: 'own', data: st.filter(s => s.local), getPosition: lngLat, ...px, pickable: true, autoHighlight: true,
      highlightColor: A(p.cells, 1), stroked: true, filled: true, getRadius: 5, getFillColor: A(p.ink, a('own')),
      getLineColor: A(p.halo, a('own')), getLineWidth: 1.5 }));
  }
  /* the node itself, always: a ring, not a dot, because /health publishes its cell's centre to strangers */
  out.push(new Dk.ScatterplotLayer({ id: 'node', data: [{ p: D.point }], getPosition: d => d.p, ...px, stroked: true, filled: false,
    getRadius: 9, getLineColor: A(p.cells, 1), getLineWidth: 2 }));
  /* named in the margin, "This house · 0 m", on a leader: labels never sit on the house (Tomas, 15 Oct, option A) */
  if (PM.measure.length) {
    const path = PM.measure.concat(PM.hover && PM.tool === 'measure' ? [PM.hover] : []);
    /* each placed leg labelled with the node's own metres for it; the leg to the cursor is drawn, not measured */
    const legs = (PM.measured && PM.measured.points === PM.measure.length) ? PM.measured.legs_m : [];
    const lab = PM.measure.map((q, i) => ({ q, t: i ? (legs[i - 1] != null ? fmtM(legs[i - 1]) : '…') : PM.from ? '' : 'start' })).filter(d => d.t);
    out.push(new Dk.PathLayer({ id: 'measure', data: [{ path }], getPath: d => d.path, ...px, getColor: A(p.cells, 1), getWidth: 2, extensions: [dashed], getDashArray: [6, 3] }));
    out.push(new Dk.ScatterplotLayer({ id: 'measure-v', data: PM.measure, getPosition: q => q, ...px, getRadius: 3.5, getFillColor: A(p.halo, 1), stroked: true, getLineColor: A(p.cells, 1), getLineWidth: 2 }));
    out.push(new Dk.TextLayer({ characterSet: 'auto', id: 'measure-l', data: lab, getPosition: d => d.q, getText: d => d.t, getSize: 11, fontFamily: 'JetBrains Mono, monospace',
      getColor: A(p.ink, 1), getPixelOffset: [0, -14], background: true, getBackgroundColor: A(p.halo, .95), backgroundPadding: [4, 2] }));
  }
  return out;
}
const redraw = () => { if (PM.flat) flat(); else if (PM.overlay) PM.overlay.setProps({ layers: layers() }); margin(); };

/* ---------------------------------------------------------------- the margin (option A, Tomas 15 Oct 2026)
   Labels never sit on the house. Every mark in view of the house, its stations, images and species, the public stations
   and the model points, leaves the map on a thin leader to a ruled row in the right-hand margin: its sign, its name and
   its distance, ordered as the marks sit, top to bottom. Public stations off the map sit on its edge with their distance.
   Every metre is the node's: GET /nearby for the public stations, GET /geo/measure?each for the rest (token-only).
   Without the token the house's own rows say withheld, in the place they would stand. On a phone the margin is the list
   Around the house, under the map, with no leaders. */
const WH = '<svg class="wh" width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><rect x="1.5" y="1.5" width="11" height="11"/><path d="M3 11L11 3"/></svg>';
const DIST = new Map();   // the node's metres from its own point, by mark
let NEAR = new Map(), MSEQ = 0;
function measureFrom(ms) {
  const need = ms.filter(m => m.key && !DIST.has(m.key)).slice(0, 199);
  if (!need.length || !DOORS_TOKEN()) return;
  need.forEach(m => DIST.set(m.key, null));
  ask(`geo/measure?from_node=true&each=true&path=${need.map(m => m.ll.map(v => v.toFixed(6)).join(',')).join(';')}`)
    .then(r => { r.each.forEach((e, i) => DIST.set(need[i].key, e.m)); margin(); }).catch(() => need.forEach(m => DIST.delete(m.key)));
}
function marks() {
  const st = D.sensors.filter(s => s.lat != null), on = id => PM.on[id] && (!PM.flat || FLAT.includes(id)), out = [];
  const nm = s => plain(s.name || s.sensor_id);
  out.push({ house: true, name: 'This house', ll: D.point, sw: 'house', m: 0 });
  if (on('own')) st.filter(s => s.kind === 'sensor' && s.local).forEach(s => out.push({ pick: { kind: 'station', s }, name: nm(s), ll: lngLat(s), sw: 'pt-own', key: s.sensor_id, own: true }));
  if (on('public')) st.filter(s => s.kind === 'sensor' && !s.local).forEach(s => out.push({ pick: { kind: 'station', s }, name: nm(s), ll: lngLat(s), sw: 'pt-pub', key: s.sensor_id, pub: true,
    m: NEAR.has(s.sensor_id) ? NEAR.get(s.sensor_id) * 1000 : undefined }));
  if (on('models')) d3.groups(st.filter(s => s.kind === 'model' || s.kind === 'map'), s => `${s.lat.toFixed(4)},${s.lon.toFixed(4)}`)
    .forEach(([k, ss]) => out.push({ pick: { kind: 'model', ss, p: lngLat(ss[0]) }, name: ss.length > 1 ? `Model points, ${ss.length}` : nm(ss[0]), ll: lngLat(ss[0]), sw: 'pt-model', key: 'm' + k }));
  if (on('images') && PM.caps) PM.caps.forEach(c => out.push({ pick: { kind: 'image', c }, name: `${KIND[c.kind] || c.kind} image`, ll: [c.at[1], c.at[0]], sw: 'pt-img', key: 'c' + c.id }));
  if (on('species') && PM.caps) speciesMarks().forEach(x => out.push({ pick: { kind: 'image', c: x.c }, name: x.t, ll: [x.c.at[1], x.c.at[0]], sw: 'pt-sp', key: 'c' + x.c.id, dy: -13 }));
  return out;
}
function margin() {
  const el = $('#pmargin'); if (!el) return;
  const seq = ++MSEQ, tok = !!DOORS_TOKEN(), map = PM.map, box = map && map.getContainer(), W = box ? box.clientWidth : 0, H = box ? box.clientHeight : 0;
  const all = marks().map(m => { const q = map ? map.project(m.ll) : null; return { ...m, x: q ? q.x : null, y: q ? q.y + (m.dy || 0) : null }; });
  const inView = m => m.x == null || (m.x >= 0 && m.x <= W && m.y >= 0 && m.y <= H);
  /* without the token the house's own stations stand at its published cell centre: their names and places are the household's */
  let rows = all.filter(m => inView(m) && !(m.own && !tok));
  const hy = all[0].y;
  if (!tok) rows.push({ held: 'This house’s stations', y: hy }, ...(PM.caps ? [] : [{ held: 'Images and species', y: hy }]));
  measureFrom(rows.filter(m => !m.house && !m.pub && !m.held));
  const far = m => m.held || m.house ? 0 : m.x == null ? (m.m ?? DIST.get(m.key) ?? 1e9) : Math.hypot(m.x - all[0].x, m.y - all[0].y);
  const MAX = 12, more = rows.length > MAX ? rows.length - (MAX - 1) : 0;
  if (more) rows = rows.sort((a, b) => far(a) - far(b)).slice(0, MAX - 1);
  rows.sort((a, b) => (a.y ?? far(a)) - (b.y ?? far(b)) || (a.held ? -1 : 0));
  const dist = m => m.house ? '0 m' : m.m != null ? fmtM(m.m) : DIST.get(m.key) != null ? fmtM(DIST.get(m.key)) : tok ? '…' : '—';
  el.innerHTML = `<div class="k mhd">At the house · by position</div><h2 class="mhp">Around the house</h2>`
    + rows.map((m, i) => m.held ? `<div class="mr held">${WH}<span>${esc(m.held)}</span><b>withheld</b></div>`
      : `<button class="mr" data-i="${i}">${m.house ? sign('sign-house') : `<i class="sw ${m.sw}" aria-hidden="true"></i>`}<span class="said">${esc(m.name)}</span><b>${dist(m)}</b></button>`).join('')
    + (more ? `<div class="mr"><i></i><span>+ ${more} more, further from the house</span><b></b></div>` : '')
    + `<p class="fine">${tok ? 'Metres from the node’s own point, by the node (GET /geo/measure, /nearby).' : 'Where the house’s things are is the household’s, so distances here are from the cell’s centre. Unlock this screen in ' + UNLOCK_AT + '.'}</p>`;
  document.querySelectorAll('#pmargin button.mr').forEach(b => b.onclick = () => {
    const m = rows[+b.dataset.i]; PM.pick = m.pick || null; if (PM.map) popup(PM.pick); facts();
  });
  /* the leaders, desk only (the phone hides them): mark → the map's right edge at the row's height → the row */
  const ld = $('#pleads'), ed = $('#pedges');
  if (!ld || !ld.getBoundingClientRect || !map) { if (ld) ld.innerHTML = ''; if (ed) ed.innerHTML = ''; return; }
  requestAnimationFrame(() => {
    if (seq !== MSEQ) return;
    const o = ld.getBoundingClientRect();
    ld.innerHTML = [...document.querySelectorAll('#pmargin button.mr')].map(b => {
      const m = rows[+b.dataset.i], r = b.getBoundingClientRect(), ty = (r.top + r.bottom) / 2 - o.top, rx = r.left - o.left;
      return m.x == null ? '' : `<polyline points="${m.x.toFixed(1)},${m.y.toFixed(1)} ${W - 30},${ty.toFixed(1)} ${(rx - 4).toFixed(1)},${ty.toFixed(1)}"/>`;
    }).join('');
  });
  /* public stations off the map: a hollow mark on the edge, pointing at them, with the node's distance; the nearest six */
  /* inset from the tools' side: their column stands on the left at a desk, on the right on a phone */
  const cx = W / 2, cy = H / 2, I = 26, phone = matchMedia('(max-width:700px)').matches, IL = phone ? I : 72, IR = phone ? 72 : I;
  ed.setAttribute('viewBox', `0 0 ${W} ${H}`);
  ed.innerHTML = all.filter(m => m.pub && !inView(m) && m.m != null).sort((a, b) => a.m - b.m).slice(0, 6).map(m => {
    const dx = m.x - cx, dy = m.y - cy, t = Math.min(dx > 0 ? (W - IR - cx) / dx : dx < 0 ? (IL - cx) / dx : 1e9, dy > 0 ? (H - I - cy) / dy : dy < 0 ? (I - cy) / dy : 1e9);
    const ex = cx + dx * t, ey = cy + dy * t, a = Math.atan2(dy, dx) * 180 / Math.PI;
    return `<circle class="pub" cx="${ex.toFixed(1)}" cy="${ey.toFixed(1)}" r="4.5"/><path d="M8,-4L13,0L8,4" transform="translate(${ex.toFixed(1)},${ey.toFixed(1)}) rotate(${a.toFixed(0)})"/>`
      + `<text x="${(ex + (ex > cx ? -12 : 12)).toFixed(1)}" y="${(ey + (ey > cy ? -10 : 18)).toFixed(1)}" text-anchor="${ex > cx ? 'end' : 'start'}">${fmtM(m.m)}</text>`;
  }).join('');
}

/* ---------------------------------------------------------------- the strip: layers as legend (option A, 15 Oct)
   Five group buttons above the map, each opening its rows in a drop-down over the map; the base map's state at the
   strip's right. The rows are the legend as before: a swatch, the pack that drew it, its opacity. */
function baseWords() {
  if (!PM.meta) return `${WH}<small>street map withheld</small>`;
  const m = PM.meta.layers || {}, G = PM.ground || {}, b = (m.vector || {}).build;
  const on = [PM.on.street && (G.vector ? `street map${b ? ` · OSM build ${b.slice(0, 8)}` : ''}` : 'the plan'), PM.on.imagery && 'satellite', PM.on.drone && 'drone'].filter(Boolean);
  return `<small>${on.join(' + ') || 'no base map'}</small>${on.length ? prov('cached') : ''}`;
}
function panel() {
  const groups = d3.groups(LAYERS, l => l.group), z = PM.map ? PM.map.getZoom() : 0, G = PM.gopen;
  const row = l => {
    const hidden = PM.on[l.id] && !PM.flat && ((l.minz != null && z < l.minz) || (l.maxz != null && z > l.maxz));
    const off = l.empty || (PM.flat && !FLAT.includes(l.id));
    const why = PM.flat && !FLAT.includes(l.id) ? 'drawn on the live map only' : l.locked ? `${WH}withheld · unlock this screen in ${UNLOCK_AT}` : l.none ? l.none : `The ${l.pack} pack has nothing here yet${l.why ? ` · <code>${esc(l.why)}</code>` : ''}`;
    return `<div class="ly ${off ? 'empty' : ''} ${PM.on[l.id] ? 'on' : ''} ${l.parent ? 'sub' : ''}" data-l="${l.id}">`
      + `<label><input type="checkbox" ${PM.on[l.id] ? 'checked' : ''} ${off ? 'disabled' : ''} aria-label="${esc(l.name)}">`
      + `<i class="sw ${l.sw}" aria-hidden="true"></i><span class="nm">${esc(l.name)}<small>${off ? why : esc(l.sub)}${hidden ? ` · ${l.minz != null && z < l.minz ? 'zoom in to see' : 'zoom out to see'}` : ''}</small></span>`
      + `<span class="pk">${esc(l.pack)}</span></label>`
      + (l.id === 'wind' && PM.on.wind && PM.wind ? `<label class="whr"><span>now</span><input type="range" min="0" max="${PM.wind.times.length - 1 - nowIdx()}" step="1" value="${PM.windStep}" aria-label="Hours ahead"><b>${PM.windStep ? `+${PM.windStep} h` : 'now'}</b></label>` : '')
      + (off || l.still || PM.flat ? '' : `<input class="op" type="range" min="0" max="1" step="0.05" value="${PM.alpha[l.id]}" aria-label="${esc(l.name)} opacity" ${PM.on[l.id] ? '' : 'disabled'}>`)
      + `</div>`;
  };
  $('#layers').innerHTML = `<div class="lystrip"><span class="lyn">Layers <small>${ON()} of ${LAYERS.filter(l => !l.empty && !l.parent).length}</small></span>`
    + groups.map(([g, ls]) => `<button data-g="${g}" aria-expanded="${G === g}" aria-controls="lydrop">${g} <small>${ls.filter(l => PM.on[l.id]).length}/${ls.length}${G === g ? ' ▾' : ''}</small></button>`).join('')
    + `<span class="base">${baseWords()}</span></div>`
    + `<div class="lydrop" id="lydrop"${G ? '' : ' hidden'}>${G ? (groups.find(([g]) => g === G) || [0, []])[1].map(row).join('') : ''}</div>`;
  const drop = document.getElementById && document.getElementById('lydrop');
  if (drop && PM.dropX != null) drop.style.left = PM.dropX + 'px';
  document.querySelectorAll('#layers .lystrip button').forEach(b => b.onclick = () => {
    const strip = b.parentNode, wrap = strip.parentNode;
    PM.gopen = PM.gopen === b.dataset.g ? null : b.dataset.g;
    PM.dropX = Math.max(0, Math.min(b.offsetLeft - strip.scrollLeft, wrap.clientWidth - 340));
    panel();
  });
  document.querySelectorAll('#layers .ly').forEach(row => {
    const id = row.dataset.l, cb = row.querySelector('input[type=checkbox]'), op = row.querySelector('.op');
    cb.onchange = () => { PM.on[id] = cb.checked; applyBase(); redraw(); panel(); credits(); windSync(); facts(); };
    const wh = row.querySelector('.whr input');
    if (wh) wh.oninput = () => { PM.windStep = +wh.value; row.querySelector('.whr b').textContent = PM.windStep ? `+${PM.windStep} h` : 'now'; windResample(); facts(); };
    if (op) op.oninput = () => { PM.alpha[id] = +op.value; applyBase(); redraw(); };
  });
}
/* the drop-down closes on a press outside the strip, and on Esc */
document.addEventListener('click', e => { if (PM.gopen && e.target.isConnected && !e.target.closest('#layers')) { PM.gopen = null; panel(); } });
document.addEventListener('keydown', e => { if (e.key === 'Escape' && PM.gopen) { PM.gopen = null; panel(); } });

/* ---------------------------------------------------------------- the scale selector and the tools */
function chrome() {
  $('#mapbar').innerHTML = `<div class="scales" role="group" aria-label="Scale">${SCALES.map(([r, n]) =>
    `<button data-r="${r}" class="${r === PM.res ? 'on' : ''} ${mayLeave(r) ? 'leave' : ''}" title="${esc(`${n}: resolution ${r}, about ${fmtM(EDGE(r))} to an edge${mayLeave(r) ? ' · coarse enough to leave the machine' : ''}`)}"><b>${n}</b><span>${r}</span></button>`).join('')}</div>`;
  document.querySelectorAll('.scales button').forEach(b => b.onclick = () => fly(+b.dataset.r));
}
async function fly(r) {
  let c; try { c = await cellAt(D.point[0], D.point[1], r); } catch (e) { offline(e.message); return; }
  const bb = loop(c.ring).reduce((m, [x, y]) => [Math.min(m[0], x), Math.min(m[1], y), Math.max(m[2], x), Math.max(m[3], y)], [180, 90, -180, -90]);
  /* the zoom resFor() reads back as r: the rung's edge midway (geometrically) between 56 px, where r begins, and
     where r + 1 would take over. fitBounds with padding refused to move on any landscape map and landed a rung off
     elsewhere, so a button and a scroll now share one rule, whatever the map's shape. */
  const px = 56 * Math.sqrt(EDGE(r) / EDGE(r + 1));
  PM.map.easeTo({ center: [(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2], zoom: Math.log2(px * mPerPx(0) / EDGE(r)),
    duration: CLOCK.reduced() ? 0 : 700 });
}
/* The tools (Tomas, 15 Oct): 44 px targets, the active one says its word, measuring ends on Done (a double click still
   does), and the house is one tap away: From the house measures from the node's own point to the next tap. */
const MEASURING = () => PM.tool === 'measure' || PM.tool === 'from';
function tools() {
  const el = document.createElement('div'); el.className = 'tools';
  const T = [['in', '+', 'Zoom in'], ['out', '−', 'Zoom out'], ['fit', '⌖', 'Back to this node’s cell'], ['inspect', '↖', 'Inspect: tap a feature', 'Inspect'],
    ['measure', '⟷', 'Measure: tap points, then Done', 'Measure'], ['from', '⌂', 'Distance from the house: tap a point', 'From the house'], ['png', '⤓', 'Save this view as a PNG']];
  el.innerHTML = T.map(([k, g, t, w]) => `<button data-t="${k}" title="${t}" aria-label="${t}" class="${k === PM.tool ? 'on' : ''}"><span class="g" aria-hidden="true">${g}</span>${w ? `<span class="w">${w}</span>` : ''}</button>`).join('')
    + `<button class="done" data-t="done" hidden>Done</button>`;
  PM.setTool = k => {
    PM.tool = k; PM.hover = null;
    if (MEASURING()) { PM.measure = []; PM.measured = null; PM.from = k === 'from'; }
    el.querySelectorAll('button[data-t]').forEach(b => b.classList.toggle('on', b.dataset.t === PM.tool));
    el.querySelector('.done').hidden = !MEASURING();
    PM.map.getCanvas().style.cursor = MEASURING() ? 'crosshair' : ''; redraw(); facts();
  };
  el.onclick = e => {
    const k = e.target.closest('button')?.dataset.t; if (!k) return;
    if (k === 'in') PM.map.zoomIn(); else if (k === 'out') PM.map.zoomOut(); else if (k === 'fit') fly(8);
    else if (k === 'png') { const a = document.createElement('a'); a.download = `place-res${PM.res}.png`; PM.map.triggerRepaint(); PM.map.once('render', () => { a.href = PM.map.getCanvas().toDataURL('image/png'); a.click(); }); }
    else if (k === 'done') PM.setTool('inspect');
    else PM.setTool(k);
  };
  PM.map.getContainer().appendChild(el);
}

/* ---------------------------------------------------------------- the inspector: one line under the map (option A)
   In view, the node's own cell as the lede says it; a mark, a margin row or a cell pressed says its facts in the same
   line, with the longer card on the map (popup()). Every figure is the node's answer: GET /geo/cell, /geo/measure. */
let FSEQ = 0;
async function facts() {
  const seq = ++FSEQ, o = PM.pick, r = PM.res, el = $('#facts');
  const row = (t, v) => `<span class="fi"><small>${esc(t)}</small><b>${v}</b></span>`, hint = h => `<span class="hint">${h}</span>`;
  const put = h => { if (seq === FSEQ) el.innerHTML = h; };
  try {
    const m = PM.measured && PM.measured.points === PM.measure.length && PM.measure.length > 1 ? PM.measured : null;
    if (PM.tool === 'from') {
      put(`<span class="k">From the house</span><b>${m ? fmtM(m.total_m) : '—'}</b>` + hint('tap any point: the node measures it from its own point (GET /geo/measure) · Done when you have it'));
    } else if (PM.tool === 'measure') {
      put(`<span class="k">Measure</span><b>${m ? fmtM(m.total_m) : '—'}</b>` + row('points', PM.measure.length) + hint('tap to add a point, Done to finish, Esc to clear · great-circle, by the node'));
    } else if (o && o.kind === 'station') {
      const s = o.s, v = lastRaw(s.sensor_id, 'pm25');
      const head = `<span class="k">${s.local ? 'This house’s station' : 'Public station'}</span><b class="said">${esc(plain(s.name || s.sensor_id))}</b>`;
      const pm = row('PM2.5, last hour', v == null ? '<span class="gap">not heard</span>' : `${fmt(v, 1)} µg/m³ ${prov(s.local ? 'live' : 'partial')}`);
      const tail = hint(s.local ? 'in this node’s custody: it counts toward the cell' : 'display only: never drives an alert here');
      put(head + pm + tail);
      if (!DOORS_TOKEN()) return;
      const [d, c] = await Promise.all([fromNode(s.lon, s.lat), cellAt(s.lon, s.lat, r)]);
      put(head + row('from this node', fmtM(d)) + pm + row('cell at res ' + r, c.id) + tail);
    } else if (o && o.kind === 'model') {
      put(`<span class="k">Model points here · ${o.ss.length}</span>` + o.ss.map(x => `<span class="said">${esc(x.name)}</span>`).join('') + prov('model') + hint('a model is partial, whatever its quality'));
    } else if (o && o.kind === 'cell') {
      put(`<span class="k">Cell</span><b>${esc(o.id)}</b>`);
      const c = await cellFacts(o.id);
      put(`<span class="k">Cell · res ${c.res}</span><b>${c.id}</b>` + row('area', area(c.area_m2)) + row('edge', fmtM(c.edge_m))
        + (c.parent ? row('parent', c.parent) : '') + row('this node’s cell', c.is_node ? 'yes' : c.cells_from_node == null ? 'no' : `no · ${c.cells_from_node} cells away`)
        + (c.may_leave ? hint('coarse enough to leave the machine') : ''));
    } else if (o && o.kind === 'image') {
      const c = o.c, head = `<span class="k">Image · ${esc(KIND[c.kind] || c.kind)}</span><b class="said">${esc(c.note || 'no note')}</b>`
        + row('taken', esc(when(c.ts))) + row('by', `<span class="said">${esc(c.actor || '—')}</span>`) + row('cell, res 10', esc(c.cell))
        + row('in the seven cells', c.outside ? 'no · outside' : 'yes');
      put(head);
      put(head + row('from this node', fmtM(await fromNode(c.at[1], c.at[0]))) + hint('kept on this node, cleaned of EXIF and GPS'));
    } else if (o && o.kind === 'lab') {
      const head = `<span class="k">Place to make</span><b class="said">${esc(o.s.name)}</b>`;
      put(head + hint('from fablabs.io, a directory: shown, never counted'));
      put(head + row('from this node', fmtM(await fromNode(o.s.lon, o.s.lat))) + hint('from fablabs.io, a directory: shown, never counted'));
    } else {
      /* the node's own cell, as the lede says it: its edge and its own area, not the resolution's average */
      const h = D.health, own = (D.geometry.ladder.find(l => l.res === h.cell.res) || {}).own_area_m2;
      put(`<span class="k">In view</span><b>${esc(h.cell.id)}</b><span>res ${r} in view · cell res ${h.cell.res}</span>`
        + `<span>${h.cell.edge_m} m edge</span>${own ? `<span>${area(own)}</span>` : ''}`
        + `<span>${ON()} of ${LAYERS.filter(l => !l.empty && !l.parent).length} layers on</span>`
        + (m ? row(PM.from ? 'from the house' : 'measured', fmtM(m.total_m)) : '') + windWords()
        + (PM.offline ? `<span class="gap">the grid is locked on this screen</span>` : '') + hint('tap any mark or margin row to inspect it'));
    }
  } catch (e) { offline(e.message); put(`<span class="k">Inspect</span>` + hint(`the node did not answer: ${esc(e.message)}`)); }
}

/* ---------------------------------------------------------------- the wind, moving */
/* The forecast pack's field (GET /ground/wind): Open-Meteo's 10 m wind at 8 × 8 points over ±30 km, hourly for a day,
   and the node's own point beside it. Particles drift through it, as Bali Air Dispatch draws its 64 points over the
   island. Between four of the node's points the page blends them (bilinear, by east and north components), the way a
   map resamples a raster: the values are the node's, the blend is the drawing. Outside the square nothing moves,
   because the field says nothing there. One clock, stopped off the door; under reduced motion, still arrows. */
const WIND = { cv: null, ctx: null, cells: null, cell: 18, parts: [], moving: false, on: false };
PM.windStep = 0;
const COMPASS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
function nowIdx() {
  const F = PM.wind; if (!F) return 0;
  let best = 0; F.times.forEach((t, i) => { if (Math.abs(Date.parse(t) - Date.now()) < Math.abs(Date.parse(F.times[best]) - Date.now())) best = i; });
  return best;
}
const windHour = () => Math.min(nowIdx() + PM.windStep, PM.wind.times.length - 1);
function windWords() {
  const F = PM.wind; if (!F || !PM.on.wind) return '';
  const h = windHour(), s = F.at_node.speed_kmh[h], d = F.at_node.from_deg[h];
  if (s == null || d == null) return '';
  return `<span class="wind">wind ${Math.round(s)} km/h from ${COMPASS[Math.round(d / 22.5) % 16]} · ${hhmm(F.times[h])}${PM.windStep ? ` · +${PM.windStep} h` : ''}</span>`;
}
/* east and north components, km/h, of the wind going TO (from + 180) */
const uv = (s, from) => { const t = (from + 180) * Math.PI / 180; return [s * Math.sin(t), s * Math.cos(t)]; };
function sample(lng, lat, h) {
  const F = PM.wind, n = F.n, fy = (lat - F.lats[0]) / (F.lats[n - 1] - F.lats[0]) * (n - 1), fx = (lng - F.lons[0]) / (F.lons[n - 1] - F.lons[0]) * (n - 1);
  if (!(fx >= 0 && fy >= 0 && fx <= n - 1 && fy <= n - 1)) return null;
  const x0 = Math.min(n - 2, Math.floor(fx)), y0 = Math.min(n - 2, Math.floor(fy)), tx = fx - x0, ty = fy - y0;
  const at = (j, i) => { const s = F.speed_kmh[h][j][i], d = F.from_deg[h][j][i]; return s == null || d == null ? null : uv(s, d); };
  const c = [at(y0, x0), at(y0, x0 + 1), at(y0 + 1, x0), at(y0 + 1, x0 + 1)];
  if (c.some(v => !v)) return null;
  return [0, 1].map(k => (c[0][k] * (1 - tx) + c[1][k] * tx) * (1 - ty) + (c[2][k] * (1 - tx) + c[3][k] * tx) * ty);
}
function windResample() {
  if (!WIND.cv || !PM.wind) return;
  const el = PM.map.getContainer(), w = el.clientWidth, h = el.clientHeight, dpr = devicePixelRatio || 1, C = WIND.cell, hr = windHour();
  WIND.cv.width = w * dpr; WIND.cv.height = h * dpr; WIND.ctx.setTransform(dpr, 0, 0, dpr, 0, 0); WIND.w = w; WIND.h = h;
  const cols = Math.ceil(w / C), rows = Math.ceil(h / C), K = 0.025;           // px per frame for each km/h: 14 km/h drifts about 21 px a second
  WIND.cols = cols; WIND.cells = new Array(cols * rows);
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const ll = PM.map.unproject([c * C + C / 2, r * C + C / 2]), v = sample(ll.lng, ll.lat, hr);
    WIND.cells[r * cols + c] = v ? [v[0] * K, -v[1] * K, Math.hypot(v[0], v[1])] : null;
  }
  WIND.parts = Array.from({ length: Math.min(700, Math.round(w * h / 1000)) }, () => spawn({}));   // sparse: a field to read, not a texture
  WIND.ctx.clearRect(0, 0, w, h);
  if (CLOCK.reduced()) still();
}
const vel = (x, y) => (x < 0 || y < 0 || x >= WIND.w || y >= WIND.h) ? null : WIND.cells[Math.floor(y / WIND.cell) * WIND.cols + Math.floor(x / WIND.cell)];
function spawn(p) {
  for (let k = 0; k < 12; k++) { p.x = Math.random() * WIND.w; p.y = Math.random() * WIND.h; if (vel(p.x, p.y)) break; }
  p.age = Math.floor(Math.random() * 160); p.max = 120 + Math.floor(Math.random() * 120); return p;   // slower, so each lives longer
}
const ink = a => { const photo = (PM.on.imagery && PM.ground.imagery) || (PM.on.drone && PM.ground.drone && PM.map.getZoom() >= 13);
  return PM.theme === 'dark' || photo ? `rgba(249,245,242,${a})` : `rgba(23,23,23,${a})`; };
function tick() {
  if (view() !== 'place' || !PM.on.wind || !PM.wind) { CLOCK.off('place-wind'); WIND.on = false; return; }
  if (WIND.moving || !WIND.cells) return;
  const x = WIND.ctx;
  x.globalCompositeOperation = 'destination-in'; x.fillStyle = 'rgba(0,0,0,.95)'; x.fillRect(0, 0, WIND.w, WIND.h);
  x.globalCompositeOperation = 'source-over'; x.strokeStyle = ink(.5); x.lineWidth = 1.1; x.beginPath();
  for (const p of WIND.parts) {
    const v = vel(p.x, p.y);
    if (!v || ++p.age > p.max) { spawn(p); continue; }
    x.moveTo(p.x, p.y); p.x += v[0]; p.y += v[1]; x.lineTo(p.x, p.y);
  }
  x.stroke();
}
/* reduced motion: one still arrow per 54 px, its length the speed, pointing where the wind goes */
function still() {
  const x = WIND.ctx, S = 54; x.clearRect(0, 0, WIND.w, WIND.h); x.strokeStyle = ink(.55); x.lineWidth = 1.2;
  for (let py = S / 2; py < WIND.h; py += S) for (let px = S / 2; px < WIND.w; px += S) {
    const v = vel(px, py); if (!v) continue;
    const L = Math.min(22, 4 + v[2] * .9), a = Math.atan2(v[1], v[0]), ex = px + Math.cos(a) * L / 2, ey = py + Math.sin(a) * L / 2;
    x.beginPath(); x.moveTo(px - Math.cos(a) * L / 2, py - Math.sin(a) * L / 2); x.lineTo(ex, ey);
    x.lineTo(ex - Math.cos(a - .5) * 5, ey - Math.sin(a - .5) * 5); x.moveTo(ex, ey); x.lineTo(ex - Math.cos(a + .5) * 5, ey - Math.sin(a + .5) * 5); x.stroke();
  }
}
function windSync() {
  if (!WIND.cv) return;
  const want = !!(PM.on.wind && PM.wind && view() === 'place');
  WIND.cv.hidden = !want;
  if (!want) { CLOCK.off('place-wind'); WIND.on = false; return; }
  if (!WIND.cells) windResample();
  if (CLOCK.reduced()) { still(); return; }
  if (!WIND.on) WIND.on = CLOCK.on('place-wind', tick);
}

/* ---------------------------------------------------------------- a dot, named where it stands */
/* Every dot answers a click with what it is, in a card on the map, and the way to its readings in Data. The
   inspector on the right keeps the longer facts. */
const DOTS = ['own', 'public', 'models', 'labs', 'images', 'species'];
const KIND = { phone: 'Phone', camera: 'Fixed camera', microscope: 'Microscope', drone: 'Drone', balloon: 'Balloon or kite' };
/* an image answers the token only, so it is fetched as a blob: an <img src> cannot carry the header */
const imgBlob = id => doorsFetch(`/captures/${id}/file`).then(r => (r.ok ? r.blob() : null)).catch(() => null);
let POP = null;
function popup(o) {
  if (POP) { POP.remove(); POP = null; }
  if (!o || o.kind === 'cell') return;
  let at, h;
  if (o.kind === 'station') {
    const s = o.s, v = lastRaw(s.sensor_id, 'pm25');
    at = [s.lon, s.lat];
    h = `<div class="k">${s.local ? 'This house’s station' : 'Public station · display only'}</div><b class="said">${esc(plain(s.name || s.sensor_id))}</b>`
      + `<span class="mono">${esc(s.source || '')}${s.indoor ? ' · inside' : ''}</span>`
      + `<span>${v == null ? '<span class="gap">not heard this hour</span>' : `PM2.5 ${fmt(v, 1)} µg/m³ ${prov(s.local ? 'live' : 'partial')}`}</span>`
      + `<a href="#data/${encodeURIComponent(s.sensor_id)}">Its readings in Data →</a>`;
  } else if (o.kind === 'model') {
    at = o.p;
    h = `<div class="k">Model points · ${o.ss.length}</div>` + o.ss.map(x => `<span class="said">${esc(x.name)}</span>`).join('')
      + `<span>${prov('model')} a model is partial, whatever its quality</span><a href="#data/models">The models in Data →</a>`;
  } else if (o.kind === 'image') {
    const c = o.c; at = [c.at[1], c.at[0]];
    h = `<div class="k">Image · ${esc(KIND[c.kind] || c.kind)}</div><img class="pmimg" alt="${esc(c.note || KIND[c.kind] || 'an image')}">`
      + (c.note ? `<b>${esc(c.note)}</b>` : '') + (c.analysis ? `<span>${esc(c.analysis.summary || '')} <i>(${c.analysis.confirmed_by ? 'confirmed' : 'model'})</i></span>` : '') + `<span class="mono">${esc(when(c.ts))}${c.actor ? ' · ' + esc(c.actor) : ''}</span>`
      + `<span class="mono">${esc(c.cell)}${c.lat == null ? ' · no point, its cell' : ''}</span><a href="#data/d-images">Its details in Data →</a>`;
    imgBlob(c.id).then(b => { const el = POP && POP.getElement().querySelector('.pmimg'); if (b && el) { el.src = URL.createObjectURL(b); el.onload = () => URL.revokeObjectURL(el.src); } });
  } else if (o.kind === 'lab') {
    at = [o.s.lon, o.s.lat];
    h = `<div class="k">Place to make</div><b>${esc(o.s.name)}</b><span class="mono">listed on fablabs.io · shown, never counted</span>`;
  }
  POP = new maplibregl.Popup({ closeButton: true, closeOnClick: false, offset: 12, maxWidth: '260px', className: 'pmpop' })
    .setLngLat(at).setHTML(h).addTo(PM.map);
  POP.on('close', () => { POP = null; });
}

/* ---------------------------------------------------------------- without WebGL */
/* A browser or a kiosk with no WebGL threw at new maplibregl.Map and drew nothing, not even the list or the facts
   (Tomas's review, 15 Oct). Now the same answers are drawn still, the way Node draws its cell: the node's cell and its
   res-6 parent's cells (D.ngeo), the rings (GET /geo/rings), the stations, the images and the house, projected, never
   tiled. Without the token only the stations and the house: the cells and the rings place the node. */
const FLAT = ['grid', 'mine', 'own', 'public', 'rings', 'images', 'species'];
function flat() {
  const el = $('#map'), W = el.clientWidth || 600, H = el.clientHeight || W, NG = D.ngeo, on = id => PM.on[id];
  const st = D.sensors.filter(s => s.kind === 'sensor' && s.lat != null), five = RINGS && RINGS.find(r => r.km === 5);
  let pts = five && on('rings') ? five.path : NG ? loop(NG.c6.ring) : st.filter(s => s.local).map(lngLat).concat([D.point]);
  if (pts.length < 2) pts = [D.point, [D.point[0] + .02, D.point[1] + .02]];
  const pr = d3.geoMercator().fitExtent([[60, 60], [W - 60, H - 60]], { type: 'MultiPoint', coordinates: pts });
  const xy = q => pr(q).map(v => v.toFixed(1)), d = ring => 'M' + ring.map(q => xy(q).join(',')).join('L') + 'Z';
  const T = (q, t, cls, dy = 0) => { const [x, y] = xy(q); return `<text x="${x}" y="${+y + dy}" class="${cls}">${esc(t)}</text>`; };
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" class="geo flatmap" role="img" aria-label="The node’s cell, the stations and the rings, drawn still">`;
  if (NG && on('grid')) s += NG.c6.children_ll.filter(k => k[0] !== NG.c8.id).map(k => `<path d="${d(loop(k))}" class="hex"/>`).join('');
  if (NG && on('mine')) s += `<path d="${d(loop(NG.c8.ring))}" class="mine"/>`;
  if (RINGS && on('rings')) s += RINGS.map(r => `<path d="${d(r.path)}" class="ringl"/>` + T(r.path[0], `${r.km} km`, 'rl', -4)).join('');
  if (on('public')) s += st.filter(x => !x.local).map(x => { const [cx, cy] = xy(lngLat(x)); return `<circle cx="${cx}" cy="${cy}" r="4.5" class="st"/>`; }).join('');
  if (on('own')) s += st.filter(x => x.local).map(x => { const [cx, cy] = xy(lngLat(x)); return `<circle cx="${cx}" cy="${cy}" r="5" class="st in"/>`; }).join('');
  if (PM.caps && on('images')) s += PM.caps.map(c => T([c.at[1], c.at[0]], '■', 'gl')).join('');
  if (PM.caps && on('species')) s += speciesMarks().map(m => T([m.c.at[1], m.c.at[0]], '◆', 'gl', -13)).join('');
  const [hx, hy] = xy(D.point);
  s += `<circle cx="${hx}" cy="${hy}" r="9" class="house"/></svg>`;   // named in the margin, never on the point
  el.innerHTML = s + `<p class="flatnote">${esc(PM.flat)}</p>`;
  if (PM.offline) offline(PM.offline);
}

/* ---------------------------------------------------------------- mount once; later calls re-skin */
async function placeMap() {
  const theme = document.documentElement.dataset.theme || 'light';
  if (PM.flat) { flat(); panel(); facts(); margin(); return; }
  if (PM.map) {
    if (theme !== PM.theme) { PM.theme = theme; PM.map.setStyle(style()); PM.map.once('styledata', () => { applyBase(); redraw(); }); }
    PM.map.resize(); chrome(); panel(); facts(); windSync(); return;
  }
  PM.theme = theme;
  /* The plan is the node's own GET /place/geojson, centred where the node stands. Only when the node has none is the
     design kit's copy drawn, and the layer row says it is 1.2 km off. */
  PM.meta = await ask('ground/meta').catch(() => null);
  PM.wind = await doorsFetch(API + 'ground/wind').then(r => r.status === 200 ? r.json() : null).catch(() => null);
  PM.ground = (PM.meta && PM.meta.on_disk) || {};
  groundRows(); packRows();
  NEAR = new Map(((await doorsFetch('/nearby').then(r => (r.ok ? r.json() : null)).catch(() => null)) || {}).ring?.map(x => [x.sensor_id, x.km]) || []);
  [PM.caps, PM.species] = await Promise.all([ask('captures?limit=500').catch(() => null), ask('species').catch(() => null)]); imageRows();
  const nodePlan = await ask('place/geojson').then(g => (g.features || []).length ? g : null).catch(() => null);
  PM.land = { type: 'FeatureCollection', features: [] }; PM.plan = nodePlan;
  if (!nodePlan && !PM.ground.vector && PM.meta) LAYERS.find(l => l.id === 'street').sub = 'the node sent no plan and holds no street map';
  const el = $('#map'); el.innerHTML = '';
  panel();   /* the list first: the map takes its height, so it must be at its height before the map is centred */
  let map;
  try { map = PM.map = new maplibregl.Map({ container: el, style: style(), center: D.point, zoom: 13.6, minZoom: 5, maxZoom: 18.5,
    dragRotate: false, pitchWithRotate: false, touchPitch: false, maxPitch: 0, attributionControl: false, fadeDuration: 0, canvasContextAttributes: { preserveDrawingBuffer: true },
    /* the one guard that keeps the promise: nothing but this page's own origin is ever asked for a tile */
    transformRequest: url => (url.startsWith(location.origin + '/ground/') ? { url, headers: DOORS_AUTH() }
      : url.startsWith(location.origin) || url.startsWith('blob:') ? { url } : { url: 'data:,' }) }); } catch (e) {
    /* no WebGL here: the still drawing, and the list and the facts as always */
    PM.map = null; PM.res = 8;
    if (D.ngeo) GRID = { res: 8, edge_m: EDGE(8), node: D.ngeo.c8.id, nodeRing: loop(D.ngeo.c8.ring), cells: [] };
    console.warn('Place: no live map', e);
    PM.flat = `This browser gave the map no WebGL, so the node’s answers are drawn still: its cell, the stations, the rings and the images. Panning, the scales and measuring need the live map.`;
    flat(); panel(); facts(); credits(); margin();
    if (!D.ngeo) offline(D.ngeoErr || 'no token');
    ask('geo/rings?km=2,5,15').then(x => { RINGS = x.rings.map(g => ({ km: g.km, path: g.ring.map(([la, ln]) => [ln, la]) })); flat(); }).catch(() => {});
    return;
  }
  map.touchZoomRotate.disableRotation();
  map.addControl(new maplibregl.ScaleControl({ maxWidth: 110, unit: 'metric' }), 'bottom-right');
  PM.overlay = new deck.MapboxOverlay({ interleaved: true, layers: [], pickingRadius: 8,
    onHover: info => { PM.hoverDot = !!(info.object && DOTS.includes(info.layer.id)); },
    /* deck.gl owns the cursor in interleaved mode: a dot says it can be clicked, the measure tool keeps its cross */
    getCursor: ({ isDragging }) => isDragging ? 'grabbing' : MEASURING() ? 'crosshair' : PM.hoverDot ? 'pointer' : 'grab',
    onClick: info => {
      if (MEASURING()) return;
      const o = info.object, id = info.layer && info.layer.id;
      PM.pick = !o ? null : (id === 'own' || id === 'public') ? { kind: 'station', s: o } : id === 'models' ? { kind: 'model', ss: o.ss, p: o.p }
        : id === 'labs' ? { kind: 'lab', s: o } : id === 'images' ? { kind: 'image', c: o } : id === 'species' ? { kind: 'image', c: o.c } : (id === 'grid' || id === 'grid-dot' || id === 'mine' || id === 'radio') ? { kind: 'cell', id: o.id } : null;
      popup(PM.pick); facts();
    } });
  map.addControl(PM.overlay);
  tools();
  WIND.cv = document.createElement('canvas'); WIND.cv.className = 'windcv'; WIND.cv.setAttribute('aria-hidden', 'true');
  WIND.ctx = WIND.cv.getContext('2d'); map.getContainer().appendChild(WIND.cv);
  map.on('movestart', () => { const l = $('#pleads'); if (l) l.innerHTML = ''; WIND.moving = true; if (WIND.ctx) WIND.ctx.clearRect(0, 0, WIND.w || 0, WIND.h || 0); });
  map.on('moveend', () => { WIND.moving = false; windResample(); windSync(); });
  map.on('resize', () => { windResample(); margin(); });
  map.on('load', () => {
    applyBase(); PM.res = resFor(map.getZoom()); redraw(); chrome(); panel(); facts(); loadGrid(); credits(); windResample(); windSync();
    ask('geo/rings?km=2,5,15').then(x => { RINGS = x.rings.map(g => ({ km: g.km, path: g.ring.map(([la, ln]) => [ln, la]) })); redraw(); }).catch(() => {});
    cellFacts(D.geometry.radio.mine).then(c => { RADIO = { id: c.id, path: loop(c.ring) }; redraw(); }).catch(() => {});
  });
  map.on('moveend', () => { const r = resFor(map.getZoom()); if (r !== PM.res) { PM.res = r; chrome(); } redraw(); panel(); loadGrid(); });
  map.on('mousemove', e => { const ll = [e.lngLat.lng, e.lngLat.lat]; if (PM.tool === 'measure' && PM.measure.length) { PM.hover = ll; redraw(); } });
  map.on('click', e => {
    if (PM.tool === 'from') {
      const q = [e.lngLat.lng, e.lngLat.lat]; PM.measure = [D.point, q]; PM.measured = null; redraw(); facts();
      fromNode(q[0], q[1]).then(d => { if (PM.measure[1] === q) { PM.measured = { points: 2, legs_m: [d], total_m: d }; redraw(); facts(); } }).catch(x => offline(x.message));
      return;
    }
    if (PM.tool !== 'measure') return;
    PM.measure.push([e.lngLat.lng, e.lngLat.lat]); redraw(); facts();
    if (PM.measure.length > 1) {
      const pts = PM.measure.slice();
      ask(`geo/measure?path=${pts.map(q => q.map(v => v.toFixed(6)).join(',')).join(';')}`)
        .then(m => { if (pts.length === PM.measure.length) { PM.measured = m; redraw(); facts(); } }).catch(e => offline(e.message));
    }
  });
  map.on('dblclick', e => { if (!MEASURING()) return; e.preventDefault(); PM.setTool('inspect'); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && PM.measure.length) { PM.measure = []; PM.measured = null; PM.hover = null; redraw(); facts(); } });
}
window.placeMap = placeMap; window.__PM = PM;   // for the rig
/* the Images panel added one: ask again, so its kind's row and its square appear */
window.placeImagesChanged = async () => { if (!PM.map && !PM.flat) return; [PM.caps, PM.species] = await Promise.all([ask('captures?limit=500').catch(() => null), ask('species').catch(() => null)]); imageRows(); panel(); redraw(); };
/* The same base for the doors' other maps (Now's "around this house"): the node's own street map and names when this
   screen may have them; without them only the land's colour, never a tile from anywhere else. */
window.groundBase = async theme => {
  if (!PM.meta) { PM.meta = await ask('ground/meta').catch(() => null); PM.ground = (PM.meta && PM.meta.on_disk) || {}; }
  PM.land = PM.land || { type: 'FeatureCollection', features: [] };
  const keep = PM.theme; PM.theme = theme; const s = style(), p = P(); PM.theme = keep;
  s.layers = s.layers.filter(l => !['imagery', 'drone', 'plan-sat'].includes(l.id));
  if (!PM.ground.vector) s.layers[0].paint['background-color'] = p.land;
  return { style: s, palette: p, street: !!PM.ground.vector };
};
window.groundRequest = url => (url.startsWith(location.origin + '/ground/') ? { url, headers: DOORS_AUTH() }
  : url.startsWith(location.origin) || url.startsWith('blob:') ? { url } : { url: 'data:,' });
})();
