'use strict';
/* WALLMAP — the Wall's drawing, a living map (R42, 7 Oct 2026; Tomas: the flow by scale "does not work").
   Research: deck.gl's trips and scatterplot examples, mapbox/webgl-wind and earth.nullschool for air moving over a dark
   ground, AQICN's wind-against-PM2.5 study for the story: where the air is dirty, which way it is going, whether the
   house is inside it.

   The node's own dark street map (GET /ground/vector, as Place and Now draw it). Over it:
   - the wind, now: Open-Meteo's field for this hour (GET /ground/wind), a model, drawn as drifting streaks;
   - every station at its point, one disc of one size, that hour's mean of the chosen metric written beside it (GET
     /aggregates, the hourly table); where PM2.5 is over the air line the disc is filled and ringed red (red is a
     stroke, never a fill: the layer, audit items 11 and 29, 16 Oct);
   - the house, one mark (16 Oct, Tomas: no alert or answer rings around it).
   The hours replay: the last 6 (or 24) in 30 s (--motion-replay-loop), one hour a step (WALL_TIME.HOUR_STEP), never
   tweened; the strip under the map says which. A value label that would cover another label or a mark is not drawn.
   Without the token the hourly table, the map and the wind are not this screen's: it draws the 15-minute means now,
   held still, on the land's colour. Under reduced motion it holds the last hour still.
   15 Oct (read from 3 m): every word on it is at the wall's type floor (--wf, read off #wfield's font size); the clock
   shows only while the hours replay, beside the wind; the scale bar and the counts box are gone; the caption under it
   says in words what the red discs mean against the house, at the hour drawn (wallCaption). */
const WALLMAP = { map: null, ov: null, wind: null, stop: null };

/* A wind engine for any map: particles moved by the field's hour, the screen fading behind them (Agafonkin's CPU
   version). ponytail: the Place door keeps its own copy inside doors-placemap.js; merge the two when Place changes. */
function windOn(map, F, hour, colour) {
  const cv = document.createElement('canvas'), x = cv.getContext('2d'), CELL = 18, K = 0.025;
  cv.className = 'windcv'; cv.setAttribute('aria-hidden', 'true'); map.getContainer().appendChild(cv);
  const n = F.n, uv = (s, from) => { const t = (from + 180) * Math.PI / 180; return [s * Math.sin(t), s * Math.cos(t)]; };
  const sample = (lng, lat) => {
    const fy = (lat - F.lats[0]) / (F.lats[n - 1] - F.lats[0]) * (n - 1), fx = (lng - F.lons[0]) / (F.lons[n - 1] - F.lons[0]) * (n - 1);
    if (!(fx >= 0 && fy >= 0 && fx <= n - 1 && fy <= n - 1)) return null;
    const x0 = Math.min(n - 2, Math.floor(fx)), y0 = Math.min(n - 2, Math.floor(fy)), tx = fx - x0, ty = fy - y0;
    const at = (j, i) => { const s = F.speed_kmh[hour][j][i], d = F.from_deg[hour][j][i]; return s == null || d == null ? null : uv(s, d); };
    const c = [at(y0, x0), at(y0, x0 + 1), at(y0 + 1, x0), at(y0 + 1, x0 + 1)];
    if (c.some(v => !v)) return null;
    return [0, 1].map(k => (c[0][k] * (1 - tx) + c[1][k] * tx) * (1 - ty) + (c[2][k] * (1 - tx) + c[3][k] * tx) * ty);
  };
  let w = 0, h = 0, cols = 0, cells = [], parts = [];
  const vel = (px, py) => (px < 0 || py < 0 || px >= w || py >= h) ? null : cells[Math.floor(py / CELL) * cols + Math.floor(px / CELL)];
  const spawn = p => { for (let k = 0; k < 12; k++) { p.x = Math.random() * w; p.y = Math.random() * h; if (vel(p.x, p.y)) break; }
    p.age = Math.floor(Math.random() * 160); p.max = 140 + Math.floor(Math.random() * 140); return p; };
  const resample = () => {
    const el = map.getContainer(), dpr = devicePixelRatio || 1; w = el.clientWidth; h = el.clientHeight;
    cv.width = w * dpr; cv.height = h * dpr; x.setTransform(dpr, 0, 0, dpr, 0, 0);
    cols = Math.ceil(w / CELL); const rows = Math.ceil(h / CELL); cells = new Array(cols * rows);
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const ll = map.unproject([c * CELL + CELL / 2, r * CELL + CELL / 2]), v = sample(ll.lng, ll.lat);
      cells[r * cols + c] = v ? [v[0] * K, -v[1] * K] : null;
    }
    parts = Array.from({ length: Math.min(380, Math.round(w * h / 2200)) }, () => spawn({}));
    x.clearRect(0, 0, w, h);
  };
  const tick = () => {
    x.globalCompositeOperation = 'destination-in'; x.fillStyle = 'rgba(0,0,0,.92)'; x.fillRect(0, 0, w, h);
    x.globalCompositeOperation = 'source-over'; x.strokeStyle = colour; x.lineWidth = 1.2; x.beginPath();
    for (const p of parts) { const v = vel(p.x, p.y); if (!v || ++p.age > p.max) { spawn(p); continue; } x.moveTo(p.x, p.y); p.x += v[0]; p.y += v[1]; x.lineTo(p.x, p.y); }
    x.stroke();
  };
  resample();
  return { resample, tick, remove: () => cv.remove() };
}

async function wallMap(o) {
  if (WALLMAP.stop) WALLMAP.stop();
  const F = await flowData(), WIN = WINS.includes(o.win) ? o.win : WINS[0], HS = WALL_TIME.HOUR_STEP(WIN), LOOP = HS * WIN;
  const B = F.buckets, h0 = B.length - WIN, M = WVAR, line = M === 'pm25' ? (D.issues.air || {}).line : null;
  const replay = !!D.raw && !CLOCK.reduced();
  const meanAt = (id, h) => { const s = D.raw && (D.raw.series[id] || {})[M]; const v = s && s[h]; return v ? v[0] : null; };
  const now15 = id => ((D.stats15[id] || {})[M] || [])[0] ?? null;
  const all = D.sensors.filter(s => s.lat != null && s.lon != null && s.kind === 'sensor' && s.source !== 'openstreetmap');
  const pub = all.filter(s => !s.local), house = all.filter(s => s.local);
  const wf = parseFloat(getComputedStyle(o.el).fontSize) || 28, f = wf / 28;      /* the type floor, in pixels, on this screen */
  /* one size per kind of mark, never per value: the value is the figure beside it (more is more signs, not a bigger one) */
  const ST = 8 * f, HOUSE = 11 * f, GAP = 6 * f, over = d => line != null && d.v > line;
  const C = (k, a = 1) => rgba(k, a), mono = 'JetBrains Mono, monospace';

  const base = await window.groundBase('dark');
  o.el.innerHTML = `<div class="wallmap" style="width:${o.size}px;height:${o.size}px"></div><div class="wclock" aria-live="off"></div>`;
  const map = WALLMAP.map = new maplibregl.Map({ container: o.el.firstChild, style: base.style, center: D.point, zoom: 11, interactive: false,
    attributionControl: false, fadeDuration: 0, transformRequest: window.groundRequest });
  map.on('load', () => { for (const l of ['v-road-label', 'v-poi-label']) if (map.getLayer(l)) map.setLayoutProperty(l, 'visibility', 'none');
    if (map.getLayer('v-place-label')) map.setPaintProperty('v-place-label', 'text-opacity', .45); });
  const bb = new maplibregl.LngLatBounds(D.point, D.point); pub.forEach(s => bb.extend([s.lon, s.lat]));
  map.fitBounds(bb, { padding: 70 * f, duration: 0, maxZoom: 14 });
  const ov = WALLMAP.ov = new deck.MapboxOverlay({ interleaved: false, layers: [] }); map.addControl(ov);

  /* the wind: this hour of the model's field, not the replayed hour (the field looks forward; the hours look back) */
  const W = await doorsFetch('/ground/wind').then(r => r.status === 200 ? r.json() : null).catch(() => null);
  let wind = null;
  const windHour = W ? W.times.reduce((b, t, i) => Math.abs(Date.parse(t) - Date.now()) < Math.abs(Date.parse(W.times[b]) - Date.now()) ? i : b, 0) : 0;
  map.once('idle', () => { if (!W) return; wind = WALLMAP.wind = windOn(map, W, windHour, 'rgba(249,245,242,.5)');
    if (CLOCK.reduced()) for (let i = 0; i < 40; i++) wind.tick(); });          /* held still: one frame of streaks, never moving */
  const COMPASS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const windWords = W && W.at_node.speed_kmh[windHour] != null ? `wind ${Math.round(W.at_node.speed_kmh[windHour])} km/h from ${COMPASS[Math.round(W.at_node.from_deg[windHour] / 22.5) % 16]}` : '';

  const hourOfT = t => replay ? Math.min(B.length - 1, h0 + Math.floor(t / HS)) : B.length - 1;
  /* a label is drawn only where it covers no mark and no label already drawn: the house first, then the worst station
     first, so where two stations crowd it is the dirtier one that keeps its figure (16 Oct: they wrote over each other) */
  const px = p => { const q = map.project(p); return [q.x, q.y]; }, hp = px(D.point);
  const hit = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
  const textW = t => String(t).length * wf * .6;                                /* JetBrains Mono: 0.6 em a character */
  const layers = h => {
    const v = s => replay ? meanAt(s.sensor_id, h) : now15(s.sensor_id);
    const pts = pub.map(s => ({ s, p: [s.lon, s.lat], q: px([s.lon, s.lat]), v: v(s) })).filter(d => d.v != null);
    const hv = house.map(v).filter(x => x != null), hmean = hv.length ? d3.mean(hv) : null;
    const discs = pts.map(d => [d.q[0] - ST, d.q[1] - ST, d.q[0] + ST, d.q[1] + ST]);
    /* the house's own words go under it, or over it when under would hide a station */
    const hText = `this house${hmean != null ? ` · ${fmt(hmean, 0)} ${unitOf(M)}` : ''}`, hw = textW(hText) / 2 + 4;
    const hBox = dy => [hp[0] - hw, hp[1] + dy - wf / 2 - 2, hp[0] + hw, hp[1] + dy + wf / 2 + 2];
    const hDy = discs.some(t => hit(t, hBox(HOUSE + wf * .75))) && !discs.some(t => hit(t, hBox(-HOUSE - wf * .75))) ? -HOUSE - wf * .75 : HOUSE + wf * .75;
    const taken = [[hp[0] - HOUSE, hp[1] - HOUSE, hp[0] + HOUSE, hp[1] + HOUSE], hBox(hDy), ...discs];
    const ck = o.el.querySelector('.wclock'), m = map.getContainer().getBoundingClientRect();      /* the clock's words, drawn over the map */
    /* each line of it, not the box: a line wider than .wclock overflows it, and its box would miss the words */
    if (ck && ck.offsetHeight) for (const c of ck.children) { const a = c.getBoundingClientRect(); taken.push([a.left - m.left - 4, a.top - m.top, a.right - m.left + 4, a.bottom - m.top]); }
    const named = [...pts].sort((a, b) => b.v - a.v).filter(d => {
      const x0 = d.q[0] + ST + GAP, box = [x0, d.q[1] - wf / 2, x0 + textW(fmt(d.v, 0)), d.q[1] + wf / 2];
      if (taken.some(t => hit(t, box))) return false; taken.push(box); return true;
    });
    return [
      new deck.ScatterplotLayer({ id: 'st', data: pts, getPosition: d => d.p, radiusUnits: 'pixels', getRadius: ST, stroked: true, filled: true,
        getFillColor: d => over(d) ? C('--ink') : C('--ink', .16), getLineColor: d => over(d) ? C('--signal-worse') : C('--ink', .85),
        lineWidthUnits: 'pixels', getLineWidth: d => over(d) ? 3 : 1.5, updateTriggers: { getFillColor: h, getLineColor: h, getLineWidth: h } }),
      new deck.TextLayer({ id: 'st-v', data: named, characterSet: 'auto', getPosition: d => d.p, getText: d => fmt(d.v, 0), getSize: wf, fontFamily: mono, fontWeight: 600,
        getColor: C('--ink'), getPixelOffset: [ST + GAP, 0], getTextAnchor: 'start', getAlignmentBaseline: 'center', updateTriggers: { getText: h } }),
      new deck.ScatterplotLayer({ id: 'house', data: [D.point], getPosition: d => d, radiusUnits: 'pixels', getRadius: HOUSE, stroked: true, filled: true,
        getFillColor: C('--ink'), getLineColor: C('--ground'), lineWidthUnits: 'pixels', getLineWidth: 2 }),
      new deck.TextLayer({ id: 'house-l', data: [D.point], characterSet: 'auto', getPosition: d => d, getText: () => hText,
        getSize: wf, fontFamily: mono, fontWeight: 600, getColor: C('--ink'), getPixelOffset: [0, hDy], getTextAnchor: 'middle',
        background: true, getBackgroundColor: C('--ground', .85), backgroundPadding: [4, 2], updateTriggers: { getText: h, getPixelOffset: h } }),
    ];
  };

  /* the clock on it, only while the hours replay (the time now is beside the sentence), and the wind */
  const words = h => {
    o.el.querySelector('.wclock').innerHTML = (replay ? `<b>${hhmm(B[h])}</b><span>the last ${WIN} hours, replayed</span>` : '') + (windWords ? `<span>${esc(windWords)}</span>` : '');
    const v = s => replay ? meanAt(s.sensor_id, h) : now15(s.sensor_id);      /* the caption reads the hour the discs show */
    if (o.cap) o.cap.textContent = wallCaption(d3.mean(house.map(v).filter(x => x != null)) ?? null, pub.map(v), line, replay ? `at ${hhmm(B[h])}` : 'now');
    o.time && o.time.querySelectorAll('.h').forEach(x => x.classList.toggle('on', +x.dataset.h === h));
  };
  if (o.time) {
    o.time.innerHTML = `<div class="seg" role="group" aria-label="Window">${WINS.map(w2 => `<button data-w="${w2}" class="${w2 === WIN ? 'on' : ''}">${w2} h</button>`).join('')}</div>`
      + `<button class="play" aria-label="Pause">❚❚</button><div class="hours" style="grid-template-columns:repeat(${WIN},minmax(var(--hmin,0),1fr))">${B.slice(h0).map((b, j) => `<button class="h" data-h="${h0 + j}" title="${hhmm(b)}"><span>${WIN <= 6 || hourOf(b) % 6 === 0 ? hhmm(b) : ''}</span></button>`).join('')}</div>`
      + `<span class="k">${replay ? `${WIN} hours in ${LOOP} s` : D.raw ? 'reduced motion: the last hour, held' : 'the last half hour, held still'}</span>`;
    o.time.querySelectorAll('.seg button').forEach(b => b.onclick = () => +b.dataset.w !== WIN && wallMap({ ...o, win: +b.dataset.w }));
  }
  /* stepped: the map is redrawn only when the replayed hour changes, one hour every HOUR_STEP seconds */
  let tHold = replay ? 0 : LOOP - HS * .5, t0 = performance.now(), paused = !replay, last = 0, shown = -1;
  const draw = t => { const h = hourOfT(t); if (h === shown) return; shown = h; words(h); ov.setProps({ layers: layers(h) }); };
  const tick = now => {
    if (view() !== 'wall') return WALLMAP.stop && WALLMAP.stop();
    if (wind && now - last >= WALL_TIME.WIND_FRAME) { last = now; wind.tick(); }   /* the wind moves even when the hours are paused */
    if (paused) return;
    tHold = ((now - t0) / 1000) % LOOP; draw(tHold);
  };
  const play = () => { paused = false; t0 = performance.now() - tHold * 1000; o.time && (o.time.querySelector('.play').textContent = '❚❚'); };
  const pause = () => { paused = true; o.time && (o.time.querySelector('.play').textContent = '▶'); };
  if (o.time) {
    const pb = o.time.querySelector('.play'); pb.onclick = () => paused ? play() : pause(); if (!replay) { pb.disabled = true; pb.textContent = '▶'; }
    o.time.querySelectorAll('.h').forEach(b => b.onclick = () => { if (!replay) return; tHold = (+b.dataset.h - h0 + .5) * HS; t0 = performance.now() - tHold * 1000; draw(tHold); });
  }
  map.once('idle', () => draw(tHold));
  if (!CLOCK.reduced()) CLOCK.on('wall-map', tick);
  WALLMAP.stop = () => { CLOCK.off('wall-map'); if (wind) wind.remove(); map.remove(); WALLMAP.map = WALLMAP.ov = WALLMAP.wind = WALLMAP.stop = null; };
}
