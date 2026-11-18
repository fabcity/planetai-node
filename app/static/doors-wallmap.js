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
  const sun = ro('energy', 'sun_kwh_m2');
  if (W.roofs && sun) base.push(ch('sun', '--d-energy', 'Sun today', [+f(sun.value, 1), 'kWh/m²'], sun.provenance,
    `${f(sun.value, 1)} kWh fell on each square metre today. The roofs are coloured by how much of it they catch.`, 'Open-Meteo, today', ['roofs-sun', 'roofs-mask']));
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

if (typeof window !== 'undefined') Object.assign(window, { atHour, toward, crestSegments, crestPhase, streak, stationFeatures, wallStory, chapterAt });
if (typeof module !== 'undefined') module.exports = { atHour, toward, crestSegments, crestPhase, streak, stationFeatures, wallStory, chapterAt };
