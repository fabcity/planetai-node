'use strict';
/* WALLMAP — the Wall as a satellite map (SPEC wall-scales-map, 18 Nov 2026). Two halves: a pure one that holds the
   numbers (which hour a reading is read at, which way the wind and the swell move on the screen, how a station is
   coloured), and a DOM one that mounts the map and draws the crests and streaks on a canvas over it. Screen y grows
   downward, and a direction is a meteorological "from" bearing in degrees: 0 is from the north, so that wind blows toward
   the south, down the screen. The pure half has no DOM and no D, and is what tests/test_doors_wallmap.py runs. */

/* ---- pure: no DOM ---- */

/* the reading at hour h; with none there, the nearest hour that has one, the earlier hour first on a tie; null if the
   whole day is empty (a gap in a station is shown as a gap, never as the neighbour's number passed off as its own) */
const atHour = (v, h) => {
  for (let d = 0; d < v.length; d++) {
    if (v[h - d] != null) return v[h - d];
    if (v[h + d] != null) return v[h + d];
  }
  return null;
};

/* the unit vector on the screen the air or the water moves along: a "from" bearing turned half a circle, y down */
const toward = fromDeg => {
  const a = (fromDeg + 180) * Math.PI / 180;
  return { ux: Math.sin(a), uy: -Math.cos(a) };
};

/* parallel crest lines [x1, y1, x2, y2] across a w×h box, square to the way the swell goes and `spacingPx` apart; each
   runs the box's whole diagonal so no angle leaves a corner bare, and `phasePx` slides them along the direction */
const crestSegments = (w, h, waveFromDeg, phasePx, spacingPx = 26) => {
  const { ux, uy } = toward(waveFromDeg), cx = w / 2, cy = h / 2, R = Math.hypot(w, h) / 2, out = [];
  for (let o = phasePx % spacingPx - Math.ceil(R / spacingPx) * spacingPx; o <= R; o += spacingPx) {
    const mx = cx + ux * o, my = cy + uy * o;
    out.push([mx + uy * R, my - ux * R, mx - uy * R, my + ux * R]);
  }
  return out;
};

/* how far the crests have travelled in a spacing at time t, so one wave period moves them exactly one spacing and the
   loop has no jump */
const crestPhase = (tSeconds, periodS, spacingPx = 26) => (tSeconds / periodS % 1) * spacingPx;

/* a wind streak's speed in px/s and its tail in px from the wind in km/h; the steps are what reads at a wall's distance */
const streak = kmh => ({ v: 8 + 5 * kmh, tail: 10 + 2.5 * kmh });

/* the stations as GeoJSON at hour h; v is −1 for a gap (the layer draws it grey), over is above the clean-air line */
const stationFeatures = (stations, h, line) => ({ type: 'FeatureCollection', features: stations.map(s => {
  const v = (s.pm25 || [])[h] ?? null;
  return { type: 'Feature', geometry: { type: 'Point', coordinates: [s.lon, s.lat] },
    properties: { v: v ?? -1, over: v != null && v > line } };
}) });

/* ---- the story: which chapters each scale has ---- */

/* The Wall holds a scale for one replayed day and splits that day between the scale's chapters: the chapter on at hour h
   of n chapters (0..n−1; h is 0..23, and the last chapter takes whatever is left) */
const chapterAt = (h, n) => Math.min(n - 1, Math.floor(h / (24 / n)));

const PROVS = ['live', 'partial', 'model', 'cached', 'example'];
const COMPASS = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west'];
const UG = 'µg/m³';

/* The chapters of each scale, in order, each present only when the data it draws is. W is GET /wall (null blocks are
   packs that are off), D the doors' data (issues[k].readouts, issues.air.stack and .line). `layers` are the map layer
   ids Task 6 mounts; `hue` is a CSS custom property name, resolved by the page. A scale with nothing to say still
   stands with chapters: []. Captions are drafts for the voice pass; every distance is W's whole km. */
const wallStory = (W, D) => {
  const I = D.issues || {}, num = v => typeof v === 'number' && isFinite(v), f = (v, dp = 0) => (+v).toFixed(dp);
  const ro = (k, m) => { const r = ((I[k] || {}).readouts || []).find(x => x.metric === m); return r && num(r.value) ? r : null; };
  const word = p => PROVS.includes(p) ? p : 'model';
  const stack = (I.air || {}).stack || {}, line = (I.air || {}).line;
  const ch = (k, hue, title, n, w, says, src, layers, extra) => ({ k, hue, title, n, word: word(w), says, src, layers, ...extra });
  const base = [], community = [], city = [];

  if (num((stack.room || {}).value)) base.push(ch('air', '--d-air', 'Air', [+f(stack.room.value, 1), UG], stack.room.provenance,
    `Fine dust in the house${num(line) ? `, against the WHO line of ${f(line)} ${UG}` : ''}. The cell takes the hour's colour.`,
    `${(stack.room.n ?? '')} sensors in the house${(stack.yard || {}).n ? ` · ${stack.yard.n} outside` : ''}`.trim(), ['own-air']));
  const built = ro('land', 'built_frac');
  if (W.roofs && built) base.push(ch('built', '--d-ground', 'Buildings', [Math.round(built.value), '%'], built.provenance,
    `${W.roofs.osm_in_cells} roofs are mapped on OpenStreetMap within ${Math.round(W.roofs.mapped_radius_m / 100) * 100} m of this cell, and the ground here is ${f(built.value)} % built.`,
    'OpenStreetMap · built share, Earth Engine', ['roofs', 'roofs-mask']));
  const sun = W.grid && W.grid.sun && num(W.grid.sun.kwh_m2) ? W.grid.sun : null;
  if (W.roofs && sun) base.push(ch('sun', '--d-energy', 'Sun today', [+f(sun.kwh_m2, 1), 'kWh/m²'], 'model',
    `${f(sun.kwh_m2, 1)} kWh fell on each square metre today.${num(sun.panel_kw) && num(sun.roof_kwh) ? ` A ${f(sun.panel_kw, 1)} kW panel on a roof here would make about ${f(sun.roof_kwh, 1)} kWh.` : ''} The roofs are coloured by how much of it they catch.`,
    'Open-Meteo, today', ['roofs-sun', 'roofs-mask']));
  const lst = ro('heat', 'lst'), dl = ro('heat', 'lst_delta'), ln = ro('heat', 'lst_night');
  if (lst) base.push(ch('heat', '--d-heat', 'Ground heat', [+f(lst.value, 1), '°C'], lst.provenance,
    `The ground in this cell at the last clear Landsat pass${dl ? `, ${f(Math.abs(dl.value), 1)} °C ${dl.value < 0 ? 'cooler' : 'hotter'} than the land 1 to 3 km around it` : ''}.`,
    `Landsat${ln ? ` · MODIS at night ${f(ln.value, 1)} °C` : ''}`, ['own-heat']));
  const rain = ro('water', 'rain_24h_mm'), up = ro('water', 'terrain_upslope_ha');
  if (rain) base.push(ch('rain', '--d-water', 'Rain', [+f(rain.value, 1), 'mm'], rain.provenance,
    `${f(rain.value, 1)} mm of rain in 24 hours.${up ? ` ${f(up.value, 1)} ha of ground drains through this cell.` : ''}${W.river ? ` The nearest river is ${W.river.nearest_km} km away.` : ''}`,
    'Copernicus DEM 30 m · forecast', ['own-water']));

  if (num((stack.ring || {}).value) && (W.stations || []).length) community.push(ch('air', '--d-air', 'Air around', [+f(stack.ring.value, 1), UG], stack.ring.provenance,
    `${W.stations.length} stations around, each a dot. Red when its hour is past the line.`, stack.ring.source || '', ['stations']));
  if (W.change && num(W.change.ha)) community.push(ch('change', '--d-ground', 'Land that changed', [Math.round(W.change.ha), 'ha'], 'model',
    `Ground that looked different in ${W.change.b} from ${W.change.a}: cleared, built or flooded. Somebody walking there can say which.`, 'AlphaEarth', ['change']));
  if (W.lab) community.push(ch('lab', '--cells', 'The lab', [W.lab.km, 'km'], 'partial',
    `${W.lab.name}, the nearest fab lab, is ${W.lab.km} km from the house. A lab like it is who would run a community node here.`, 'the node’s record of the lab', ['lab']));
  if (W.rivers && W.river) community.push(ch('rivers', '--d-water', 'Rivers', [W.river.nearest_km, 'km'], 'model',
    `The nearest river is ${W.river.nearest_km} km from the house, carrying ${f(W.river.nearest_m3s, 2)} m³/s on average.`, 'HydroATLAS, CC BY 4.0', ['rivers']));

  const g = W.grid, plant = g && (g.plants || [])[0];
  if (g && num(g.fossil_low_pct)) city.push(ch('grid', '--d-energy', 'Fossil power', [g.fossil_low_pct, '%'], 'model',
    `At least that much of the power here is burnt.${plant ? ` The nearest large plant is ${String(plant.name).replace(/^PLT\w+ /, '')}, ${plant.km} km away, on ${plant.fuel}.` : ''}`,
    'PLN Bali system · OpenStreetMap', ['grid'], plant ? { fit: [[plant.lon, plant.lat]] } : {}));
  const bp = W.basin && W.basin.properties || {};
  if (W.basin) city.push(ch('basin', '--d-water', 'The basin', [bp.up_area ?? bp.sub_area ?? null, 'km²'], 'model',
    `All the ground that drains with this house to the sea.${W.river ? ` The largest river nearby carries ${f(W.river.largest_m3s, 1)} m³/s, ${W.river.largest_km} km from the house.` : ''}`,
    'HydroBASINS level 12', ['basin', 'rivers'], { fit: W.basin.geometry.coordinates[0] }));
  const swell = ro('coast', 'swell_height_m'), period = ro('coast', 'wave_period_s'), sst = ro('coast', 'sea_surface_temp');
  const from = atHour((W.hours || {}).wave_from || [], 23);
  if (swell) city.push(ch('sea', '--d-sea', 'Swell', [+f(swell.value, 1), 'm'], swell.provenance,
    `The waves come${from != null ? ` from the ${COMPASS[Math.round(from / 45) % 8]}` : ''}${period ? `, a crest every ${f(period.value)} s` : ''}, as drawn on the water.${sst ? ` The sea is ${f(sst.value, 1)} °C.` : ''}`,
    'Open-Meteo Marine', []));
  const items = (W.island || {}).items || [], off = items.find(i => i.official && num(i.pm25));
  if (off) city.push(ch('city-air', '--d-air', 'City air', [+f(off.pm25, 1), UG], 'partial',
    `${items.length} stations across the island. The ringed one at ${String(off.place || '').split(' ').pop()} is the government's, read from its air index; the others are people's and businesses' own.`,
    'Bali Air Dispatch · the government station, now', ['island', 'stations'],
    { fit: [[off.lon, off.lat]], official: { lon: off.lon, lat: off.lat, label: `${String(off.place || '').split(' ').pop()} · government` } }));

  const named = [['Base node', 'the house, its cell and the six around it', base], ['Community node', 'what a lab nearby could keep', community],
    ['City node', 'the city around it, and its grid', city]];
  return W.scales.map((s, i) => ({ k: s.k, name: named[i][0], what: named[i][1], res: s.res, km2: s.km2, cells: s.cells, chapters: named[i][2] }));
};

/* ---- DOM: the map, and the wind and the swell over it ---- */

/* wallMapMount(el, W, story, G): the Wall's own MapLibre map in `el`, walking `story` (wallStory's scales). G is
   /ground/meta's on_disk: the satellite when the node holds it, dimmed; else the node's own streets, dark. Returns
   { go(s, cut), hour(h), destroy() }, or null on a screen that cannot draw a map (no MapLibre, no WebGL), where the Wall
   writes so in its place. Every layer id below is a name a chapter lists in `layers`; a chapter shows its own and hides
   every other. A canvas over the map draws the wind and the crests at the replayed hour, on the clock's 'wall-fx' key. */
function wallMapMount(el, W, story, G = {}) {
  if (typeof maplibregl === 'undefined') return null;
  el.innerHTML = '<div class="wml"></div><canvas class="wfx" aria-hidden="true"></canvas>';
  const cs = getComputedStyle(el), hue = k => cs.getPropertyValue(k).trim() || '#888';   /* the hues are #wallv's (finding 4: --cells is set there) */
  const C = { air: hue('--d-air'), heat: hue('--d-heat'), water: hue('--d-water'), sea: hue('--d-sea'), wind: hue('--d-wind'), energy: hue('--d-energy'),
    ground: hue('--d-ground'), cells: hue('--cells'), ink: hue('--ink'), red: hue('--signal-worse') };
  /* the streets when there is no satellite: doors-placemap.js PAL.dark's sea, land and road (Place's palette sits in its closure) */
  const DARK = { sea: '#0E1012', land: '#17191D', road: '#30353D' };
  const FC = features => ({ type: 'FeatureCollection', features }), F = (geometry, properties = {}) => ({ type: 'Feature', geometry, properties });
  const box = pts => pts.reduce((b, [x, y]) => [[Math.min(b[0][0], x), Math.min(b[0][1], y)], [Math.max(b[1][0], x), Math.max(b[1][1], y)]], [[180, 90], [-180, -90]]);
  const air = (D.issues || {}).air || {}, line = air.line, room = ((air.series || {}).room || []).slice(-24), Hr = W.hours || {};
  const tiles = k => [`${location.origin}/ground/${k}/{z}/{x}/{y}.${k === 'vector' ? 'pbf' : 'png'}`];
  const sources = {}, base = [{ id: 'bg', type: 'background', paint: { 'background-color': G.imagery ? '#000' : DARK.sea } }];
  if (G.vector) sources.v = { type: 'vector', tiles: tiles('vector'), minzoom: 0, maxzoom: 15 };
  if (G.imagery) {
    sources.sat = { type: 'raster', tiles: tiles('imagery'), tileSize: 256, minzoom: 8, maxzoom: 15 };
    base.push({ id: 'sat', type: 'raster', source: 'sat', paint: { 'raster-brightness-max': .62, 'raster-saturation': -.35, 'raster-fade-duration': 0 } });
  } else if (G.vector) base.push({ id: 'v-earth', type: 'fill', source: 'v', 'source-layer': 'earth', paint: { 'fill-color': DARK.land } },
    { id: 'v-road', type: 'line', source: 'v', 'source-layer': 'roads', paint: { 'line-color': DARK.road, 'line-width': 1 } });
  /* the sea, never drawn: the clip for the crests */
  if (G.vector) base.push({ id: 'water', type: 'fill', source: 'v', 'source-layer': 'water', paint: { 'fill-color': '#000', 'fill-opacity': 0 } });
  let map;
  try {
    map = new maplibregl.Map({ container: el.firstChild, style: { version: 8, sources, layers: base }, interactive: false, fadeDuration: 0, attributionControl: false,
      bounds: box(story[0].cells.flatMap(c => c.ring)), fitBoundsOptions: { padding: 40 },
      /* nothing but this page's own origin is ever asked for a tile or an image */
      transformRequest: url => (url.startsWith(location.origin) ? { url } : { url: 'data:,' }) });
  } catch (e) { console.warn('Wall: no map', e); return null; }
  /* the credit at the top right: the bottom corners hold the chapter's words and the sizes */
  map.addControl(new maplibregl.AttributionControl({ compact: false, customAttribution: [G.vector && '© OpenStreetMap', G.imagery && 'Copernicus Sentinel-2'].filter(Boolean).join(' · ') }), 'top-right');

  const ALL = ['own-air', 'roofs', 'roofs-mask', 'roofs-sun', 'own-heat', 'own-water', 'stations', 'change', 'lab', 'rivers', 'grid', 'basin', 'island'];
  const EXTRA = { grid: ['grid-line'], basin: ['basin-line'] };
  const T = { s: 0, h: 0, ci: null, cut: true }, cv = el.lastChild, ctx = cv.getContext('2d');
  let ready = false, offi = null;
  map.on('load', () => {
    const add = (id, data) => map.addSource(id, { type: 'geojson', data }), L = l => map.addLayer(l);
    const pt = (lon, lat) => F({ type: 'Point', coordinates: [lon, lat] });
    add('own', FC([F({ type: 'Polygon', coordinates: [story[0].cells.find(c => c.own).ring] })]));
    L({ id: 'own-air', type: 'fill', source: 'own', paint: { 'fill-color': C.air, 'fill-opacity': .3 } });
    L({ id: 'own-heat', type: 'fill', source: 'own', paint: { 'fill-color': C.heat, 'fill-opacity': .3 } });
    L({ id: 'own-water', type: 'fill', source: 'own', paint: { 'fill-color': C.water, 'fill-opacity': .25 } });
    if (G.vector) {
      L({ id: 'roofs', type: 'fill', source: 'v', 'source-layer': 'buildings', paint: { 'fill-color': C.ground, 'fill-opacity': .6 } });
      L({ id: 'roofs-sun', type: 'fill', source: 'v', 'source-layer': 'buildings', paint: { 'fill-color': C.energy, 'fill-opacity': .8 } });
    }
    /* everything outside the base node's seven cells, dimmed: the roofs are counted inside them */
    add('mask', FC([F({ type: 'Polygon', coordinates: [[[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]], ...story[0].cells.map(c => c.ring)] })]));
    L({ id: 'roofs-mask', type: 'fill', source: 'mask', paint: { 'fill-color': '#000', 'fill-opacity': .55 } });
    if (W.change) {
      map.addSource('change', { type: 'image', url: location.origin + W.change.png, coordinates: W.change.corners });   /* its own corners, never the node's point */
      L({ id: 'change', type: 'raster', source: 'change', paint: { 'raster-opacity': .95, 'raster-fade-duration': 0 } });
    }
    if (W.basin) {
      add('basin', W.basin);
      L({ id: 'basin', type: 'fill', source: 'basin', paint: { 'fill-color': C.water, 'fill-opacity': .22 } });
      L({ id: 'basin-line', type: 'line', source: 'basin', paint: { 'line-color': C.water, 'line-width': 2, 'line-dasharray': [3, 2] } });
    }
    if (W.rivers) { add('rivers', W.rivers); L({ id: 'rivers', type: 'line', source: 'rivers', paint: { 'line-color': C.water, 'line-width': ['interpolate', ['linear'], ['coalesce', ['get', 'order'], 1], 1, 1.5, 4, 4] } }); }
    const plants = (W.grid || {}).plants || [];
    if (plants.length) {   /* the line starts at the cell's centre, never the house */
      add('grid', FC([...plants.map(p => pt(p.lon, p.lat)), F({ type: 'LineString', coordinates: [W.centre, [plants[0].lon, plants[0].lat]] }, { flow: 1 })]));
      L({ id: 'grid-line', type: 'line', source: 'grid', filter: ['has', 'flow'], paint: { 'line-color': C.energy, 'line-width': 1.5, 'line-dasharray': [1, 2] } });
      L({ id: 'grid', type: 'circle', source: 'grid', filter: ['!', ['has', 'flow']], paint: { 'circle-radius': 9, 'circle-color': C.energy } });
    }
    if (W.lab) { add('lab', FC([pt(W.lab.lon, W.lab.lat)])); L({ id: 'lab', type: 'circle', source: 'lab', paint: { 'circle-radius': 8, 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-width': 2.5, 'circle-stroke-color': C.cells } }); }
    const lit = ['case', ['==', ['get', 'v'], -1], C.ink, ['get', 'over'], C.red, C.air];
    add('stations', stationFeatures(W.stations || [], 0, line));
    L({ id: 'stations', type: 'circle', source: 'stations', paint: { 'circle-radius': 8, 'circle-color': lit, 'circle-opacity': ['case', ['==', ['get', 'v'], -1], .25, .95],
      'circle-stroke-color': '#000', 'circle-stroke-width': 1 } });
    if (W.island) {   /* the island's stations as they read now: they have no day on the node, so they do not replay */
      add('island', FC(W.island.items.map(i => F({ type: 'Point', coordinates: [i.lon, i.lat] }, { v: i.pm25 ?? -1, over: i.pm25 != null && line != null && i.pm25 > line, off: !!i.official }))));
      L({ id: 'island', type: 'circle', source: 'island', paint: { 'circle-radius': ['case', ['get', 'off'], 9, 6], 'circle-color': lit, 'circle-opacity': .9,
        'circle-stroke-color': ['case', ['get', 'off'], C.cells, '#000'], 'circle-stroke-width': ['case', ['get', 'off'], 3, 1] } });
    }
    /* the cells, lightly: the size on screen at a hairline, the ones inside it fainter, the house's own cell the only blue */
    for (let s = story.length - 1; s >= 0; s--) {
      add('c' + s, FC(story[s].cells.map(c => F({ type: 'Polygon', coordinates: [c.ring] }))));
      L({ id: 'c' + s, type: 'line', source: 'c' + s, paint: { 'line-color': C.ink, 'line-width': 1, 'line-opacity': 0 } });
    }
    L({ id: 'c-own', type: 'line', source: 'own', paint: { 'line-color': C.cells, 'line-width': 2 } });
    ready = true; apply();
  });
  /* the camera: a size's cells, widened to what the chapter draws (the plant, the basin, the government's station) */
  function place(S, ch, scale) {
    const b = box([...S.cells.flatMap(c => c.ring), ...((ch && ch.fit) || [])]);
    map.fitBounds(b, { padding: 40, duration: T.cut || CLOCK.reduced() ? 0 : scale ? 2600 : 1600, essential: true }); T.cut = false;
  }
  function apply() {
    if (!ready) return;
    const S = story[T.s], n = S ? S.chapters.length : 0, ci = n ? chapterAt(T.h, n) : -1, ch = ci >= 0 ? S.chapters[ci] : null, on = ch ? ch.layers : [];
    for (const l of ALL) for (const id of [l, ...(EXTRA[l] || [])]) if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', on.includes(l) ? 'visible' : 'none');
    story.forEach((_, k) => map.setPaintProperty('c' + k, 'line-opacity', k === T.s ? .5 : k < T.s ? .2 : 0));
    map.getSource('stations').setData(stationFeatures(W.stations || [], T.h, line));
    map.setPaintProperty('own-air', 'fill-color', room[T.h] != null && line != null && room[T.h] > line ? C.red : C.air);
    if (ch && ch.official) {
      if (!offi) { const m = document.createElement('div'); m.className = 'woffi'; m.textContent = ch.official.label; offi = new maplibregl.Marker({ element: m, anchor: 'left', offset: [14, 0] }).setLngLat([ch.official.lon, ch.official.lat]); }
      offi.addTo(map);
    } else if (offi) offi.remove();
    if (S && ci !== T.ci) { const scale = T.ci === null; T.ci = ci; place(S, ch, scale); }
  }

  /* THE WIND AND THE SWELL at the replayed hour: streaks over the whole map where the wind goes, faster with its speed;
     crests on the sea only, square to where the waves go, one passing every swell period. Hidden when the hour has no
     direction, speed, height or period: toward(null) would read as from the north. */
  const SP = 26, FX = { parts: [], phase: 0, last: 0, w: 0, h: 0, dpr: 1, sea: null, at: '' };
  const fxSize = () => { const r = el.getBoundingClientRect(); FX.dpr = devicePixelRatio || 1; FX.w = r.width; FX.h = r.height; cv.width = r.width * FX.dpr; cv.height = r.height * FX.dpr; FX.parts = []; };
  function seaPath() {   /* the sea's outline in screen pixels, rebuilt whenever the camera moved */
    const key = map.getCenter().toArray().join() + map.getZoom();
    if (key === FX.at && FX.sea) return FX.sea;
    const p = new Path2D();
    if (map.getSource('v')) for (const f of map.querySourceFeatures('v', { sourceLayer: 'water' })) {
      const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.type === 'MultiPolygon' ? f.geometry.coordinates : [];
      for (const poly of polys) for (const rg of poly) rg.forEach(([x, y], i) => { const q = map.project([x, y]); i ? p.lineTo(q.x, q.y) : p.moveTo(q.x, q.y); });
    }
    FX.sea = p; FX.at = key; return p;
  }
  function fxDraw(now, still) {
    if (!ctx || !FX.w) return;
    const dt = Math.min(.05, (now - (FX.last || now)) / 1000); FX.last = now;
    ctx.setTransform(FX.dpr, 0, 0, FX.dpr, 0, 0); ctx.clearRect(0, 0, FX.w, FX.h);
    const h = T.h, S = story[T.s], ch = S && S.chapters.length ? S.chapters[chapterAt(h, S.chapters.length)] : null;
    const wd = atHour(Hr.wave_from || [], h), sw = atHour(Hr.swell_m || [], h), per = atHour(Hr.swell_s || [], h);
    if (wd != null && sw != null && per) {
      if (!still) FX.phase = (FX.phase + dt / per * SP) % SP;   /* integrated, so a new period at the next hour does not jump */
      ctx.save(); ctx.clip(seaPath()); ctx.strokeStyle = C.sea; ctx.globalAlpha = ch && ch.k === 'sea' ? .7 : .28; ctx.lineWidth = .7 + sw * .5;
      ctx.beginPath(); for (const [x1, y1, x2, y2] of crestSegments(FX.w, FX.h, wd, FX.phase, SP)) { ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); }
      ctx.stroke(); ctx.restore();
    }
    const dr = atHour(Hr.wind_from || [], h), ws = atHour(Hr.wind_kmh || [], h);
    if (dr != null && ws != null) {
      const { ux, uy } = toward(dr), { v, tail } = streak(ws);
      if (!FX.parts.length) FX.parts = [...Array(260)].map(() => ({ x: Math.random() * FX.w, y: Math.random() * FX.h, a: Math.random() * 4 }));
      ctx.strokeStyle = C.wind; ctx.lineWidth = 2; ctx.lineCap = 'round';
      for (const q of FX.parts) {
        if (!still) { q.x += ux * v * dt; q.y += uy * v * dt; q.a += dt; }
        if (q.a > 4 || q.x < -20 || q.y < -20 || q.x > FX.w + 20 || q.y > FX.h + 20) Object.assign(q, { x: Math.random() * FX.w, y: Math.random() * FX.h, a: 0 });
        ctx.globalAlpha = .7 * Math.min(1, q.a, 4 - q.a);
        ctx.beginPath(); ctx.moveTo(q.x, q.y); ctx.lineTo(q.x - ux * tail, q.y - uy * tail); ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }
  /* off the Wall, or reduced motion turned on while it runs (CLOCK.on refuses then, but keeps a key already on): off,
     and under reduced motion one still frame */
  const fx = now => { if (view() !== 'wall') return CLOCK.off('wall-fx'); if (CLOCK.reduced()) { CLOCK.off('wall-fx'); return fxDraw(now, true); } fxDraw(now, false); };
  const still = () => { if (CLOCK.reduced()) fxDraw(performance.now(), true); };
  fxSize(); map.on('resize', () => { fxSize(); still(); }); map.on('idle', still);
  return {
    /* a new size takes effect at the next hour(h): one camera move, to the chapter of that hour, never first to the
       chapter of the hour before (a size changes at hour 0, and the hour before was 23, the widest frame) */
    go(s, cut) { T.s = s; T.ci = null; T.cut = !!cut; },
    hour(h) { T.h = h; apply(); if (!CLOCK.on('wall-fx', fx)) fxDraw(performance.now(), true); },   /* CLOCK.on refuses under reduced motion: one still frame */
    destroy() { CLOCK.off('wall-fx'); if (offi) offi.remove(); map.remove(); },
  };
}

if (typeof window !== 'undefined') Object.assign(window, { atHour, toward, crestSegments, crestPhase, streak, stationFeatures, wallStory, chapterAt });
if (typeof module !== 'undefined') module.exports = { atHour, toward, crestSegments, crestPhase, streak, stationFeatures, wallStory, chapterAt };
