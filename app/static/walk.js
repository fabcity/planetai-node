'use strict';
/* The walk out from the house (SPEC_mobile §11.2). Five steps, house → street → ring → region → planet; the map
   flies out at each and draws that scale's cell heavy, the smaller ones faint inside it. Nothing here names an issue:
   the switch lists every issue /issues carries, in its order, and each issue is read at the scales it has. A scale
   with no reading stays in the walk and says so, so a pack's issue read only by a model starts at the region. */

const SCALES = [{ res: 10, k: 'room' }, { res: 9, k: 'yard' }, { res: 6, k: 'ring' }, { res: 3, k: 'region' }, { res: 1, k: null }];
const PLANET = { en: 'planet', id: 'planet', es: 'planeta' };
/* an issue's metric as a station spells it, where the two differ (heat is felt, a station reads the thermometer) */
const STATION_METRIC = { apparent: 'temp' }, SAID = { temp: 'the thermometer', apparent: 'feels-like' };

/* every issue with a reading at one scale or more, in the engine's order: pure, tests/test_doors.py runs it */
function walkOf(I) {
  return (I.order || Object.keys(I.issues)).map(k => [k, I.issues[k]]).filter(([, a]) => a && a.stack)
    .map(([k, a]) => ({ k, a, at: SCALES.slice(0, 4).map(s => (a.stack[s.k] && a.stack[s.k].value != null ? a.stack[s.k] : null)) }))
    .filter(w => w.at.some(Boolean));
}
if (typeof module !== 'undefined') module.exports = { walkOf };

if (typeof document !== 'undefined') (async () => {
  const $ = s => document.querySelector(s);
  const get = p => fetch('/' + p, { headers: DOORS_AUTH() }).then(r => (r.ok ? r.json() : null)).catch(() => null);
  /* the walk reads what the phone page reads: whatever this node's SHARE_LEVEL answers, or everything with the token */
  const [I, D, H, N, M] = await Promise.all([get('issues'), get('issues/days?days=1'), get('health'), get('nodes'), get('ground/meta')]);
  if (!I || !H) {
    $('#top').remove();
    $('#chs').innerHTML = '<p class="locked">This node does not share its readings with a phone that is not unlocked. '
      + '<a href="/?layout=mobile#unlock">Unlock this phone</a> first.</p>';
    return;
  }
  /* /ground and /geo/cell answer a phone with no token at SHARE_LEVEL=open; anywhere else the walk goes without the map */
  if (!M) $('#map').insertAdjacentHTML('afterend', '<p class="nomap">This node does not share its map with a phone that is not unlocked.</p>');
  const lang = 'en', L = (I.labels && I.labels[lang]) || {}, W = walkOf(I);
  const word = i => (SCALES[i].k ? L[SCALES[i].k] || SCALES[i].k : PLANET[lang]);
  const edge = r => (I.geometry.ladder.find(x => x.res === r) || {}).edge_m;
  const f = (v, dp) => (v == null ? '—' : (+v).toFixed(dp));
  let K = (W.find(x => x.k === location.hash.slice(1)) || W[0] || {}).k, AT = 0;

  /* the 24 hours of one scale, from /issues/days; [] where the issue keeps no hours there */
  const hours = (k, d) => ((D && D.issues[k] && D.issues[k].series[d]) || []).slice(-24);

  function chart(S, line, band) {
    const Wd = 358, Hh = 120, P = 22, PR = 52, all = S.flatMap(s => s.v).concat(line == null ? [] : [line]).filter(v => v != null);
    if (!all.length) return '';
    const n = S[0].v.length, lo = Math.min(...all), hi = Math.max(...all), pad = (hi - lo || 1) * .08;
    const x = i => P + (Wd - P - PR) * i / (n - 1), y = v => Hh - 14 - (Hh - 28) * (v - lo + pad) / (hi - lo + pad * 2);
    const path = v => v.reduce((a, q, i) => (q == null ? a : a + (i && v[i - 1] != null ? 'L' : 'M') + `${x(i).toFixed(1)},${y(q).toFixed(1)}`), '');
    let g = '';
    if (band) { const [a, b] = band; for (let i = 0; i < n - 1; i++) {
      if ([a[i], b[i], a[i + 1], b[i + 1]].some(q => q == null)) continue;
      g += `<path d="M${x(i)},${y(a[i])}L${x(i + 1)},${y(a[i + 1])}L${x(i + 1)},${y(b[i + 1])}L${x(i)},${y(b[i])}Z" fill="var(${b[i] + b[i + 1] > a[i] + a[i + 1] ? '--warm' : '--cool'})" opacity=".22"/>`; } }
    if (line != null) g += `<line x1="${P}" x2="${Wd - PR}" y1="${y(line)}" y2="${y(line)}" stroke="var(--ink)" stroke-dasharray="3 3"/><text x="${Wd - PR}" y="${y(line) - 4}" text-anchor="end">line ${line}</text>`;
    S.forEach(s => { const li = s.v.length - 1; g += `<path d="${path(s.v)}" fill="none" stroke="${s.c}" stroke-width="2" ${s.dash ? 'stroke-dasharray="2 3"' : ''}/>`;
      if (s.v[li] != null) g += `<circle cx="${x(li)}" cy="${y(s.v[li])}" r="3.5" fill="${s.c}"/><text x="${x(li) + 6}" y="${y(s.v[li]) + 3}" style="fill:${s.c}">${s.label}</text>`; });
    const B = (D && D.buckets.slice(-n)) || [];
    [0, 6, 12, 18].forEach(i => B[i] && (g += `<text x="${x(i)}" y="${Hh}" text-anchor="middle">${B[i].slice(11, 16)}</text>`));
    return `<svg class="g" viewBox="0 0 ${Wd} ${Hh + 4}" role="img" aria-label="the last 24 hours">${g}<text x="${x(n - 1)}" y="${Hh}" text-anchor="middle">now</text></svg>`;
  }

  /* every scale on one axis; the labels go one row each, so two close values never sit on each other */
  function ladder(w) {
    const Wd = 358, P = 16, rows = w.at.map((s, i) => s && { i, v: s.value }).filter(Boolean), line = w.a.line && w.a.line.value;
    const vs = rows.map(r => r.v).concat(line == null ? [] : [line]), lo = Math.min(...vs), hi = Math.max(...vs), pad = (hi - lo || 1) * .06;
    const x = v => P + (Wd - P * 2) * (v - lo + pad) / (hi - lo + pad * 2), dp = w.a.dp ?? 1;
    let g = `<line x1="${P}" x2="${Wd - P}" y1="20" y2="20" stroke="var(--hair)"/>`;
    if (line != null) g += `<line x1="${x(line)}" x2="${x(line)}" y1="6" y2="${28 + rows.length * 18}" stroke="var(--ink)" stroke-dasharray="3 3"/><text x="${x(line) + 4}" y="10">line</text>`;
    rows.sort((a, b) => a.v - b.v).forEach((r, j) => { const yy = 40 + j * 18, on = r.i === AT, X = x(r.v);
      g += `<circle cx="${X}" cy="20" r="${on ? 6 : 4}" fill="var(${on ? '--ink' : '--ground'})" stroke="var(--ink)"/><line x1="${X}" x2="${X}" y1="26" y2="${yy - 4}" stroke="var(--hair)"/>
        <text x="${X}" y="${yy}" text-anchor="${X > Wd - 100 ? 'end' : 'start'}" ${on ? 'style="fill:var(--ink)"' : ''}>${word(r.i)} ${f(r.v, dp)}</text>`; });
    return rows.length > 1 ? `<svg class="g ladder" viewBox="0 0 ${Wd} ${46 + rows.length * 18}">${g}</svg>` : '';
  }

  const metricOf = w => STATION_METRIC[w.a.metric] || w.a.metric;
  const outdoor = w => (I.stations || []).filter(s => !s.indoor && s.read && s.read[metricOf(w)] && s.lat != null);

  /* the stations around, each a dot on one axis, the house marked against them */
  function strip(w) {
    const st = outdoor(w), house = w.at[0] && w.at[0].value;
    if (!st.length) return '';
    const Wd = 358, P = 16, vs = st.map(s => s.read[metricOf(w)].value).concat(house == null ? [] : [house]);
    const lo = Math.min(...vs), hi = Math.max(...vs), pad = (hi - lo || 1) * .06, x = v => P + (Wd - P * 2) * (v - lo + pad) / (hi - lo + pad * 2);
    let g = `<line x1="${P}" x2="${Wd - P}" y1="24" y2="24" stroke="var(--hair)"/><text x="${P}" y="8">${f(lo, 0)}</text><text x="${Wd - P}" y="8" text-anchor="end">${f(hi, 0)}</text>`;
    st.forEach(s => (g += `<circle cx="${x(s.read[metricOf(w)].value)}" cy="24" r="${Math.max(3, 8 - (s.km || 0))}" fill="var(--warm)" opacity=".55"/>`));
    if (house != null) g += `<rect x="${x(house) - 1}" y="10" width="2" height="28" fill="var(--ink)"/><text x="${x(house)}" y="52" text-anchor="middle" style="fill:var(--ink)">${word(0)} ${f(house, w.a.dp ?? 1)}</text>`;
    const felt = metricOf(w) !== w.a.metric ? ` The stations read ${SAID[metricOf(w)] || metricOf(w)}; the ${word(0)} is ${SAID[w.a.metric] || w.a.metric}.` : '';
    return `<svg class="g" viewBox="0 0 ${Wd} 56">${g}</svg><p class="m">${st.length} outdoor stations, the nearer ones drawn bigger.${felt}</p>`;
  }

  function story() {
    const w = W.find(x => x.k === K), a = w.a, u = a.unit || '', dp = a.dp ?? 1, line = a.line && a.line.value;
    const [room, yard, ring] = ['room', 'yard', 'ring'].map(d => hours(K, d));
    const gap = w.at[0] && w.at[1] ? w.at[1].value - w.at[0].value : null;
    const pairs = room.map((v, i) => (v != null && yard[i] != null ? yard[i] - v : null)).filter(v => v != null);
    const nodes = (N && N.nodes) || [];
    const step = [
      { h: 'Inside the house', g: chart([{ v: room, c: 'var(--ink)', label: word(0) }], line), m: 'The last 24 hours.' },
      { h: 'Out on the street', p: gap == null ? '' : `The ${word(1)} reads ${f(Math.abs(gap), dp)} ${u} ${gap > 0 ? 'higher' : 'lower'} than the ${word(0)} now, and read higher in ${pairs.filter(v => v > 0).length} of the last ${pairs.length} hours.`,
        g: chart([{ v: yard, c: 'var(--warm)', label: word(1) }, { v: room, c: 'var(--ink)', label: word(0) }], null, [room, yard]),
        m: pairs.length ? `Red where the ${word(1)} read higher, blue where the ${word(0)} did.` : '' },
      { h: 'The ring around it', g: strip(w) + chart([{ v: ring, c: 'var(--warm)', dash: 1, label: word(2) }, { v: room, c: 'var(--ink)', label: word(0) }]) },
      { h: 'The region', g: ladder(w), m: w.at.filter(Boolean).length < 2 ? '' : line != null ? 'Every scale on one line. The dashed mark is the line this house is held to.' : 'Every scale on one line.' },
      { h: 'The planet', p: `${nodes.length} node${nodes.length === 1 ? '' : 's'} listed in the programme${N && N.read ? `, the list read ${N.read.slice(0, 10)}` : ''}. Each reads its own house the same way, and none of them sends its rooms here.`,
        g: nodes.length ? '<p>' + nodes.map(x => `<b>${x.name}</b> · ${(x.place || '').split(',')[0]}`).join('<br>') + '</p>' : '', m: 'Not listed? <code>planetai hello</code>' }];
    $('#chs').innerHTML = step.map((t, i) => { const s = w.at[i], e = edge(SCALES[i].res);
      return `<section class="ch" data-i="${i}"><div class="k">${word(i)} · res ${SCALES[i].res}${e ? ` · ${Math.round(e * 2).toLocaleString('en')} m across` : ''}</div><h2>${t.h}</h2>`
        + (i < 4 ? (s ? `<div class="big">${f(s.value, dp)}<i>${u}</i></div><p>${s.source || ''}${s.provenance ? `, ${s.provenance}` : ''}.</p>` : `<span class="none">${(a.name && a.name[lang]) || K} is not read at the ${word(i)}</span>`) : '')
        + (t.p && (i > 3 || s) ? `<p>${t.p}</p>` : '') + (s || i > 3 ? t.g || '' : '') + (t.m && (s || i > 3) ? `<p class="m">${t.m}</p>` : '') + '</section>'; }).join('');
    $('#rail').innerHTML = SCALES.map((s, i) => `<a href="#" data-i="${i}"><s></s>${word(i)}<em>${i < 4 ? f(w.at[i] && w.at[i].value, dp) : ''}</em></a>`).join('');
    $('#rail').querySelectorAll('a').forEach(el => (el.onclick = e => { e.preventDefault(); document.querySelectorAll('.ch')[+el.dataset.i].scrollIntoView({ behavior: 'smooth' }); }));
    document.querySelectorAll('.ch').forEach(c => io.observe(c));
    lit();
  }
  const lit = () => $('#rail').querySelectorAll('a').forEach((el, i) => el.classList.toggle('on', i === AT));
  const stationsGeo = () => { const w = W.find(x => x.k === K), m = metricOf(w);
    return { type: 'FeatureCollection', features: outdoor(w).filter(s => (s.km || 0) > 0.5)
      .map(s => ({ type: 'Feature', properties: { t: f(s.read[m].value, 0) }, geometry: { type: 'Point', coordinates: [s.lon, s.lat] } })) }; };

  const lat0 = 156543.03 * Math.cos(H.lat * Math.PI / 180);
  function go(i) {
    AT = i; lit();
    const res = SCALES[i].res, w = W.find(x => x.k === K);
    map.setProjection({ type: i === 4 ? 'globe' : 'mercator' });
    map.setPaintProperty('cells', 'line-width', ['case', ['==', ['get', 'res'], res], 3, 1]);
    map.setPaintProperty('cells', 'line-opacity', ['case', ['==', ['get', 'res'], res], 1, 0.45]);
    map.setLayoutProperty('st', 'visibility', i === 2 || i === 3 ? 'visible' : 'none');
    if (map.getLayer('stt')) map.setLayoutProperty('stt', 'visibility', i === 2 ? 'visible' : 'none');
    map.setLayoutProperty('nd', 'visibility', i === 4 ? 'visible' : 'none');
    /* frame the scale's own cell, clear of the bar on top and the rail at the foot; the planet is the globe */
    const c = cells.find(x => x.properties.res === res);
    if (i === 4 || !c) map.flyTo({ center: [H.lon, H.lat], zoom: i === 4 ? 0.9 : Math.min(18.5, Math.log2(170 * lat0 / (edge(res) * 2))), duration: 1400, essential: true });
    else map.fitBounds(c.geometry.coordinates.reduce((b, p) => b.extend(p), new maplibregl.LngLatBounds(c.geometry.coordinates[0], c.geometry.coordinates[0])),
      { padding: { top: 70, bottom: 24, left: 24, right: 24 }, duration: 1400, essential: true });
    const l = document.querySelector('.ch[data-i="3"] .ladder'); if (l) l.outerHTML = ladder(w);
  }
  const io = new IntersectionObserver(es => es.forEach(e => e.isIntersecting && +e.target.dataset.i !== AT && go(+e.target.dataset.i)), { rootMargin: '-40% 0px -55% 0px' });

  if (!W.length) { $('#chs').innerHTML = '<p class="locked">No issue has a reading yet.</p>'; return; }
  $('#tg').innerHTML = W.map(w => `<button data-k="${w.k}" aria-pressed="${w.k === K}">${(w.a.name && w.a.name[lang]) || w.k}</button>`).join('');
  $('#tg').querySelectorAll('button').forEach(b => (b.onclick = () => { K = b.dataset.k;
    $('#tg').querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
    map.getSource('st').setData(stationsGeo()); story(); start(); }));

  /* the cell this node stands in, at each scale, from the node's own /geo/cell (R25: centres only, never the house) */
  const cells = (await Promise.all(SCALES.slice(0, 4).map(s => get(`geo/cell?lat=${H.lat}&lon=${H.lon}&res=${s.res}`)))).filter(c => c && c.ring)
    .map(c => { const q = []; for (let k = 1; k < c.ring.length; k += 2) q.push([c.ring[k + 1], c.ring[k]]); q.push(q[0]);
      return { type: 'Feature', properties: { res: c.res }, geometry: { type: 'LineString', coordinates: q } }; });
  const V = M && M.layers && M.layers.vector, DR = M && M.layers && M.layers.drone, here = location.origin;
  const map = new maplibregl.Map({ container: 'map', attributionControl: { compact: true }, center: [H.lon, H.lat], zoom: 18, interactive: false,
    transformRequest: url => (url.startsWith(here + '/ground/') ? { url, headers: DOORS_AUTH() } : { url }),
    style: { version: 8, ...(V && V.fonts ? { glyphs: here + '/ground/glyphs/{fontstack}/{range}.pbf' } : {}), sources: {
      ...(V ? { v: { type: 'vector', tiles: [here + '/ground/vector/{z}/{x}/{y}.pbf'], maxzoom: V.maxzoom || 15, attribution: '© OpenStreetMap' } } : {}),
      ...(DR ? { drone: { type: 'raster', tiles: [here + '/ground/drone/{z}/{x}/{y}.png'], tileSize: 256, minzoom: 14, maxzoom: 18, attribution: 'OpenAerialMap CC BY' } } : {}),
      cells: { type: 'geojson', data: { type: 'FeatureCollection', features: cells } },
      st: { type: 'geojson', data: { type: 'FeatureCollection', features: [] } },
      nd: { type: 'geojson', data: { type: 'FeatureCollection', features: ((N && N.nodes) || []).filter(x => x.ll).map(x => ({ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: x.ll } })) } } },
    layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#dfe6ea' } },
      ...(V ? [{ id: 'earth', type: 'fill', source: 'v', 'source-layer': 'earth', paint: { 'fill-color': '#f3efe8' } },
        { id: 'water', type: 'fill', source: 'v', 'source-layer': 'water', paint: { 'fill-color': '#dfe6ea' } },
        { id: 'roads', type: 'line', source: 'v', 'source-layer': 'roads', paint: { 'line-color': '#cfc8bb', 'line-width': 1 } },
        { id: 'bld', type: 'fill', source: 'v', 'source-layer': 'buildings', paint: { 'fill-color': '#e4ded3' } }] : []),
      ...(DR ? [{ id: 'drone', type: 'raster', source: 'drone', paint: { 'raster-opacity': ['interpolate', ['linear'], ['zoom'], 14.5, 0, 15.5, 1] } }] : []),
      ...(V && V.fonts ? [{ id: 'pl', type: 'symbol', source: 'v', 'source-layer': 'places', filter: ['has', 'name'],
        layout: { 'text-field': ['get', 'name'], 'text-font': ['Noto Sans Medium'], 'text-size': 11 }, paint: { 'text-color': '#5F5A54', 'text-halo-color': '#f3efe8', 'text-halo-width': 1.4 } }] : []),
      { id: 'cells', type: 'line', source: 'cells', paint: { 'line-color': '#171717', 'line-width': 1 } },
      { id: 'st', type: 'circle', source: 'st', paint: { 'circle-radius': 9, 'circle-color': '#c8553d', 'circle-opacity': 0.8, 'circle-stroke-color': '#fff', 'circle-stroke-width': 1 } },
      ...(V && V.fonts ? [{ id: 'stt', type: 'symbol', source: 'st', layout: { 'text-field': ['get', 't'], 'text-size': 10, 'text-font': ['Noto Sans Regular'] }, paint: { 'text-color': '#fff' } }] : []),
      { id: 'nd', type: 'circle', source: 'nd', paint: { 'circle-radius': 6, 'circle-color': '#171717', 'circle-stroke-color': '#fff', 'circle-stroke-width': 2 } }] } });
  /* an issue not read at the house starts where it is first read (land and coast: the region) */
  const start = () => { const i = Math.max(0, W.find(x => x.k === K).at.findIndex(Boolean));
    if (i) document.querySelectorAll('.ch')[i].scrollIntoView(); else scrollTo(0, 0); go(i); };
  map.on('load', () => { map.getSource('st').setData(stationsGeo()); story(); start(); window.WALK_READY = true; });
  window.WALK_GO = i => go(i);
})();
