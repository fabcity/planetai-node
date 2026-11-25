'use strict';
/* DATA — every raw reading this node holds, drawn. One metric at a time; every sensor that reads it is one ruled row
   (Zendesk status rows, Square devices), all on one scale capped at the 98th percentile so one spike cannot flatten
   the rest; a reading above the cap is printed.

   PLAN, phase 4b (15 Oct 2026; Tomas: "tables by default, cards only as pop-ups"). Data was one scroll of nine
   sections, 21,900 px at 1440 and 36,600 px on a phone. It becomes Set up's own pattern: one pane at a time, routed
   #data/<tab>, Set up's .snav list as the tab bar (sticky; on a phone a strip of 44 px targets that wraps rather than
   clipping "MODELS AND SATELL" and scrolling away).
     readings  the kinds of reading, every source over 24 h, every issue over seven days, hours over the line
     models    the models and the satellite as ONE table: a row per source, a unit column, "hourly" for PT1H, and
               none of the node's own counters (years cached, forecast lead hours). The model-only kinds left the
               kinds grid, where they were empty tiles over a table that held their values.
     home      images, species, things: tables, and a card only in a dialog
     ledger    every decision: a run of the same answer is one row (decided ×10), day and time on one line, who
               in words (not gui or local-model/telegram), a stage filter; without a token the time and the stage only
     api       every route, one line each
   The Index cells table moved to Node, under the flow that already counts them (#node/cells). Every anchor Data
   had still lands: DOLD names the tab that holds the old section, DNODE the Node part that holds what moved. */
let METRIC = 'pm25';
/* Names and units are the node's own words (GET /issues → metrics); a metric the node has no word for keeps its key. */
const MNAME0 = { pm25: 'PM2.5', pm10: 'PM10', pm1: 'PM1', temp: 'temperature', humidity: 'humidity', pressure: 'pressure', gas_resistance: 'gas resistance',
  bme_iaq: 'indoor air index', noise: 'noise', light: 'light', aqi: 'AQI (US EPA)', pm25_raw: 'PM2.5 uncorrected', wind_speed: 'wind', precipitation: 'rain' };
const MNAME = new Proxy({}, { get: (_, m) => labelOf(m), has: (_, m) => m in MNAME0 });

/* THE INDEX (R45, 7 Oct 2026; inside the node's layer, on Set up's grid). Every kind of
   reading this house holds, as a table of specimens by family: each tile its short symbol in the mono, the node's
   own name, the unit, how many sources read it, the median of their 15-minute means now (GET /stats, open), and,
   with the token, the 24-hour trace of the hourly medians (GET /aggregates). Press one to draw every source.
   A kind only models read is not a tile: its values are in the Models and satellite tab's table. */
const FAMILY = [
  ['Air', ['pm25', 'pm10', 'pm1', 'pm25_raw', 'pm25_sen5x', 'pm10_sen5x', 'pm1_sen5x', 'pm25_hm3301', 'pm10_hm3301', 'pm1_hm3301',
    'pm25_pms5003', 'pm10_pms5003', 'pm1_pms5003', 'aqi', 'bme_iaq', 'iaq', 'gas_resistance', 'o3', 'no2', 'co', 'dust', 'aod', 'pm25_model', 'pm10_model']],
  ['Weather', ['temp', 'humidity', 'pressure', 'wind_speed', 'wind_direction', 'precipitation', 'uv_index', 'temp_model', 'humidity_model', 'pressure_model']],
  ['Sound and light', ['noise', 'light']],
  ['Sea', ['sea_surface_temp', 'wave_height_m', 'wave_period_s', 'wave_direction', 'swell_height_m', 'swell_period_s']],
  ['Radio', ['lora_util_pct', 'lora_channel_pct']]];
/* a word for a key the node has no label for; the node's own label (GET /issues → metrics) always wins */
/* a second particle sensor in the same box (packs/smartcitizen): the box's PM2.5 is the sensor it always was, this is the other */
const WORD = { pm25_raw: 'PM2.5, uncorrected',
  pm25_sen5x: 'PM2.5, the box’s SEN5X', pm10_sen5x: 'PM10, the box’s SEN5X', pm1_sen5x: 'PM1, the box’s SEN5X',
  pm25_hm3301: 'PM2.5, the box’s HM-3301', pm10_hm3301: 'PM10, the box’s HM-3301', pm1_hm3301: 'PM1, the box’s HM-3301',
  pm25_pms5003: 'PM2.5, the box’s PMS5003', pm10_pms5003: 'PM10, the box’s PMS5003', pm1_pms5003: 'PM1, the box’s PMS5003',
  bme_iaq: 'indoor air index', iaq: 'indoor air index', gas_resistance: 'gas resistance', o3: 'ozone',
  no2: 'nitrogen dioxide', co: 'carbon monoxide', dust: 'dust', aod: 'aerosol optical depth', pm25_model: 'PM2.5, modelled', pm10_model: 'PM10, modelled',
  temp_model: 'temperature, modelled', humidity_model: 'humidity, modelled', pressure_model: 'pressure, modelled', uv_index: 'UV index',
  sea_surface_temp: 'sea surface', wave_height_m: 'wave height', wave_period_s: 'wave period', wave_direction: 'wave direction',
  swell_height_m: 'swell height', swell_period_s: 'swell period', lora_util_pct: 'LoRa airtime', lora_channel_pct: 'LoRa channel use' };
const mWord = m => (D.metrics[m] || {}).label || WORD[m] || labelOf(m);
const SYM = { pm25: 'PM2.5', pm10: 'PM10', pm1: 'PM1', pm25_raw: 'PM2.5ʳ',
  pm25_sen5x: 'PM2.5²', pm10_sen5x: 'PM10²', pm1_sen5x: 'PM1²', pm25_hm3301: 'PM2.5²', pm10_hm3301: 'PM10²', pm1_hm3301: 'PM1²',
  pm25_pms5003: 'PM2.5²', pm10_pms5003: 'PM10²', pm1_pms5003: 'PM1²',
  aqi: 'AQI', bme_iaq: 'IAQ', iaq: 'IAQ', gas_resistance: 'Ω', o3: 'O₃', no2: 'NO₂', co: 'CO',
  dust: 'Dst', aod: 'AOD', pm25_model: 'PM2.5ᵐ', pm10_model: 'PM10ᵐ', temp: 'T', humidity: 'RH', pressure: 'P', wind_speed: 'W', wind_direction: 'Dir',
  precipitation: 'R', uv_index: 'UV', temp_model: 'Tᵐ', humidity_model: 'RHᵐ', pressure_model: 'Pᵐ', noise: 'dB', light: 'lx', sea_surface_temp: 'SST',
  wave_height_m: 'Hs', wave_period_s: 'Tp', wave_direction: 'Dw', swell_height_m: 'Sw', swell_period_s: 'Ts', lora_util_pct: 'LoRa', lora_channel_pct: 'Ch' };
/* the tabs: [the words on the tab, the sections it shows, what it draws] — a tab draws only its own sections */
const DTABS = {
  readings: ['Readings', ['d-readings', 'issues7', 'perday'], () => { const h2 = $('#d-readings h2'); if (h2) h2.textContent = asHouse('What this house reads'); metricTiles(); sensorsBlock(); issuesBlock(); perdayBlock(); }],
  report: ['Report', ['d-report'], () => reportBlock()],
  models: ['Models and satellite', ['models', 'predict', 'calibrate'], () => { modelsBlock(); predictBlock(); calibrateBlock(); }],
  home: ['Home', ['d-images', 'd-things'], () => { imagesBlock(); thingsBlock(); }],
  ledger: ['Ledger', ['ledger', 'dnote'], () => ledgerBlock()],
  api: ['API', ['api'], () => apiBlock()],
  workbench: ['Workbench', ['d-workbench'], () => workbenchBlock()] };
/* an anchor Data used to have: the tab that holds that section now; and what moved to Node, with Node's own anchor */
const DOLD = { calibrate: 'models', 'd-readings': 'readings', metrics: 'readings', sensors: 'readings', issues7: 'readings', perday: 'readings', 'd-images': 'home', 'd-things': 'home' };
const DNODE = { cells: 'cells', 'd-learned': 'remember', 'd-usual': 'remember', 'd-diary': 'remember' };
/* #data/<tab> opens a tab; #data/<old section> its tab, at the section; #data/<sensor-id> (a dot on Place) the
   readings on a metric that station reads, at its row, or the models when it is a model */
function dataRoute(hash) {
  const seg = decodeURIComponent((hash.split('/')[1] || '').split('?')[0]), s = (D.sens || {})[seg];   /* #data/report?… keeps its state after the ? */
  if (DTABS[seg]) return { tab: seg };
  if (DNODE[seg]) return { node: DNODE[seg] };
  if (DOLD[seg]) return { tab: DOLD[seg], el: seg };
  if (s) return ['model', 'map'].includes(s.kind) ? { tab: 'models', el: 'models' } : { tab: 'readings', sensor: seg };
  return { tab: 'readings' };
}

let FOCUSED = '';
VIEWS.data = function () {
  const r = dataRoute(location.hash);
  if (r.node) { location.replace('#node/' + r.node); return; }
  const S2 = D.raw ? D.raw.series : {}, FOCUS = r.sensor || '';
  if (FOCUS && FOCUS !== FOCUSED && S2[FOCUS] && !S2[FOCUS][METRIC]) {
    const has = Object.keys(S2[FOCUS]); METRIC = has.includes('pm25') ? 'pm25' : (FAMILY.flatMap(f => f[1]).find(m => has.includes(m)) || has[0] || METRIC);
  }
  const total = Object.values(S2).reduce((a, m) => a + Object.values(m).reduce((b, arr) => b + arr.filter(Boolean).length, 0), 0);
  $('#datahead').innerHTML = `<div class="k">Data · everything this node holds, as it reads it</div><h1>Every reading, drawn.</h1>
    <p class="lede">${D.raw ? `${total.toLocaleString('en')} hourly values from ${Object.keys(S2).length} sources over the last 24 hours` : 'The hourly values with the token'}, seven days of every issue at every distance, ${D.observations.length} model and satellite values and ${D.actions.length} decisions. Today’s open export, CC BY 4.0: <a class="mono" href="/export?day=${dayOf(D.buckets[D.now])}">GET /export?day=${dayOf(D.buckets[D.now])}</a>.</p>`;
  $('#dnav').innerHTML = Object.entries(DTABS).map(([id, [t]]) => `<a href="#data/${id}" data-t="${id}"${id === r.tab ? ' class="on" aria-current="page"' : ''}>${t}</a>`).join('');
  for (const [id, [, secs]] of Object.entries(DTABS)) for (const sec of secs) { const el = document.getElementById(sec); if (el) el.hidden = id !== r.tab; }
  DTABS[r.tab][2]();
  // a tab named in the link lands on the tab bar: the board sits above it (Field Synthesizer variation)
  const go = FOCUS ? (FOCUS !== FOCUSED && FOCUS) : r.el || (location.hash.includes('/') && 'dnav');
  if (FOCUS) FOCUSED = FOCUS;
  if (go) setTimeout(() => {                                   // after route() has scrolled to the top
    const el = document.querySelector(`.srow[data-sid="${CSS.escape(go)}"]`) || document.getElementById(go);
    if (el) { el.scrollIntoView({ block: FOCUS ? 'center' : 'start' }); if (FOCUS) el.classList.add('focus'); }
  });
};

/* REPORT (Tomas, 23 Nov 2026: "People should be able to select the sensors for the view, or type the name"). The weekly
   sensor report, the same five queries as the keeper's Grafana report (app/weekly.py), for anyone who opens the node:
   GET /weekly. The node counts; the page draws. The choices live in the address, #data/report?m=&s=&bad=&high=&w=&wk=&lang=,
   so a report is passed on as a link. Without the token the node offers its outdoor sensors only.
   At a glance (Tomas, 23 Nov 2026: "more graphical, like graphana graphics"; the paper register with the air colours):
   the week chosen (wk, the last complete one by default), its tiles, the places by day in Indonesia's air index (ISPU),
   then the charts over the whole window. Every band, count and verdict is the node's (GET /weekly summary). */
const repState = () => { const p = new URLSearchParams(location.hash.split('?')[1] || ''); return { m: p.get('m') || '', s: (p.get('s') || '').split(',').filter(Boolean), bad: p.get('bad') || '', high: p.get('high') || '', w: p.get('w') || '8', wk: p.get('wk') || '', lang: p.get('lang') === 'id' ? 'id' : 'en' }; };
let REPSEQ = 0, REPLAST = null, SHARE_C = [];
const repGo = st => { history.replaceState(null, '', '#data/report?' + new URLSearchParams({ m: st.m, s: st.s.join(','), bad: st.bad, high: st.high, w: st.w, wk: st.wk, lang: st.lang })); reportBlock(); };
/* a day as the node described it: its ISPU band and rounded mean; grey and empty when it was not counted (heard under 18
   hours, or not at all); a thin red edge when it is a bad day inside the good band; the bad mark when the metric has no index */
const dayBlock = d => !d || !d.counted ? { cls: 'nc', text: '', title: '' } : { cls: (d.band == null ? (d.bad ? 'nb bad' : 'nb') : 'aqi-' + d.band) + (d.edge ? ' edge' : ''), text: d.mean == null ? '' : String(Math.round(d.mean)), title: '' };
/* the hours above a chart's scale as drawn (repChart nices it to 3 ticks): the two highest, and how many more */
function aboveScale(pts, top) {
  const nt = d3.scaleLinear().domain([0, top]).nice(3).domain()[1], over = pts.filter(p => p[1] > nt).sort((a, b) => b[1] - a[1]);
  return { shown: over.slice(0, 2), more: Math.max(0, over.length - 2) };
}
/* the scale of an hourly chart: the 98th percentile, like the Data door's other charts, and the hours above it, printed */
function capTop(values) {
  const s = values.filter(v => v != null).sort((a, b) => a - b);
  if (!s.length) return { top: null, over: [] };
  const i = (s.length - 1) * 0.98, top = s[Math.floor(i)] + (s[Math.ceil(i)] - s[Math.floor(i)]) * (i - Math.floor(i));
  return { top, over: values.filter(v => v != null && v > top) };
}
/* one small chart: a line per series of [Date, value], broken where the gap is wider than `gap` ms; `ref` dashed (all
   sensors), `line` the red dash (the high), `bars` instead of a line (bad days a week, 0 to 7) */
function repChart(pts, o) {
  const W = 360, H = 110, x = d3.scaleTime([o.t0, o.t1], [30, W - 6]);
  const vs = pts.concat(o.ref || []).map(p => p[1]).concat(o.line != null ? [o.line] : []);
  const y = d3.scaleLinear([0, o.top || (d3.max(vs) || 1) * 1.1], [H - 16, 6]).nice(3), Y = v => y(Math.min(v, y.domain()[1]));
  const cut = ps => ps.flatMap((p, i) => i && p[0] - ps[i - 1][0] > o.gap ? [null, p] : [p]);
  const ln = ps => d3.line().defined(p => p).x(p => x(p[0])).y(p => Y(p[1]))(cut(ps)) || '';
  /* the air index behind a daily mean (o.bands, the node's breakpoints), each band in its ISPU colour, faint */
  const bands = !o.bands ? '' : [0, ...o.bands].map((lo, i) => { const top = y.domain()[1], hi = Math.min(i < o.bands.length ? o.bands[i] : top, top);
    return lo >= top ? '' : `<rect x="30" width="${W - 36}" y="${y(hi)}" height="${Math.max(0, y(lo) - y(hi))}" style="fill:var(--aqi-${i})" opacity=".18"/>`; }).join('');
  const wk = 7 * 864e5, bw = Math.max(2, x(new Date(+o.t0 + wk)) - x(o.t0) - 3);
  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">` + bands
    + y.ticks(3).map(t => `<line x1="30" x2="${W - 6}" y1="${y(t)}" y2="${y(t)}" class="grid"/><text x="26" y="${y(t) + 4}" text-anchor="end">${fmt(t, 0)}</text>`).join('')
    + `<text x="30" y="${H - 3}">${esc(dayOf(o.t0.toISOString()))}</text><text x="${W - 6}" y="${H - 3}" text-anchor="end">${esc(dayOf(o.t1.toISOString()))}</text>`
    + (o.line != null ? `<line x1="30" x2="${W - 6}" y1="${y(o.line)}" y2="${y(o.line)}" class="linep"/>` : '')
    + (o.ref ? `<path d="${ln(o.ref)}" class="alln"/>` : '')
    + (o.bars ? pts.map(p => `<rect class="bar" x="${x(p[0])}" width="${bw}" y="${y(p[1])}" height="${Math.max(0, y(0) - y(p[1]))}"/>`).join('') : `<path d="${ln(pts)}" class="lnp"/>`)
    + `</svg>`;
}
const plusDays = (iso, n) => new Date(Date.parse(iso + 'T12:00:00Z') + n * 864e5).toISOString().slice(0, 10);
const dshort = (iso, loc = 'en-GB') => new Date(iso + 'T12:00:00').toLocaleDateString(loc, { day: 'numeric', month: 'short' });
function reportBlock() {
  const sec = $('#d-report'), st = repState(), seq = ++REPSEQ;
  if (!sec.dataset.wired) {
    sec.dataset.wired = '1';
    sec.addEventListener('change', e => {
      const t = e.target, s2 = repState();
      if (t.dataset.r === 'pick') s2.s = t.checked ? [...s2.s, t.value] : s2.s.filter(id => id !== t.value);
      else if (t.dataset.r === 'find') return;
      else if (t.dataset.r) s2[t.dataset.r] = t.value;
      if (t.dataset.r === 'm') { s2.s = []; s2.bad = ''; s2.high = ''; }   // each metric starts at its own lines (GET /weekly)
      repGo(s2);
    });
    sec.addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.share) { repShare(); return; }
      if (b.dataset.pdf) { printWeekly(); return; }
      if (b.dataset.dl) { shareSave(+b.dataset.dl); return; }
      const s2 = repState();
      if (b.dataset.rm) s2.s = s2.s.filter(id => id !== b.dataset.rm);
      else if (b.dataset.lang) s2.lang = b.dataset.lang;
      else if (b.dataset.reset) { s2.m = ''; s2.s = []; s2.bad = ''; s2.high = ''; s2.w = '8'; s2.wk = ''; }
      else return;
      repGo(s2);
    });
    sec.addEventListener('input', e => {
      if (e.target.dataset.r !== 'find') return;
      const q = e.target.value.trim().toLowerCase();
      sec.querySelectorAll('.rlist label').forEach(l => { l.hidden = !!q && !l.textContent.toLowerCase().includes(q); });
    });
    sec.addEventListener('keydown', e => {   // Enter in the name box picks the first match not yet picked
      if (e.target.dataset.r !== 'find' || e.key !== 'Enter') return;
      e.preventDefault();
      const c = [...sec.querySelectorAll('.rlist label:not([hidden]) input')].find(i => !i.checked && !i.disabled);
      if (c) { const s2 = repState(); s2.s = [...s2.s, c.value]; e.target.value = ''; repGo(s2); }
    });
  }
  if (!sec.innerHTML) sec.innerHTML = `<h2>Report</h2><p class="fine">Reading the node…</p>`;
  const u = '/weekly?' + new URLSearchParams({ metric: st.m, sensors: st.s.join(','), bad: st.bad, high: st.high, weeks: st.w, wk: st.wk, lang: st.lang });
  fetch(u, { headers: DOORS_AUTH() }).then(r => r.json().then(j => [r.ok, j])).then(([ok, j]) => {
    if (seq !== REPSEQ) return;   // a newer choice has already asked
    if (!ok) { sec.innerHTML = `<h2>Report</h2><p class="fine">${esc(j.detail || j.error || 'The node did not answer.')} <button type="button" class="link" data-reset="1">Start again</button></p>`; return; }
    REPLAST = j;
    /* the week the node chose goes back into the address, so a link and a printout show this week next Monday too */
    if (st.wk !== j.wk) history.replaceState(null, '', '#data/report?' + new URLSearchParams({ m: st.m, s: st.s.join(','), bad: st.bad, high: st.high, w: st.w, wk: j.wk, lang: st.lang }));
    const L = j.words, loc2 = j.lang === 'id' ? 'id-ID' : 'en-GB', names = Object.fromEntries(j.sensors.map(o => [o.id, o.label])), t0 = new Date(j.t0 || Date.now()), t1 = new Date(j.t1 || Date.now());
    const para = p => `<p>${esc(p).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')}</p>`;
    const bySrc = d3.groups(j.sensors, o => o.source);
    const pick = `<div class="rpick">`
      + `<label>${esc(L.v_metric)}<select data-r="m">${j.metrics.map(m => `<option value="${esc(m)}"${m === j.metric ? ' selected' : ''}>${esc(mWord(m))}</option>`).join('')}</select></label>`
      + `<label>${esc(L.v_bad)}<input type="number" step="any" data-r="bad" value="${esc(j.bad)}"></label>`
      + `<label>${esc(L.v_high)}<input type="number" step="any" data-r="high" value="${esc(j.high)}"></label>`
      + `<label>${esc(L.week_pick)}<select data-r="wk">${[...j.week_starts].reverse().map((w, i) => `<option value="${esc(w)}"${w === j.wk ? ' selected' : ''}>${esc(dshort(w, loc2))} – ${esc(dshort(plusDays(w, 6), loc2))}${i === 0 ? ' · ' + esc(L.so_far) : ''}</option>`).join('')}</select></label>`
      + `<label>${esc(L.weeks_n)}<select data-r="w">${[4, 8, 12].map(n => `<option${n === j.weeks ? ' selected' : ''}>${n}</option>`).join('')}</select></label>`
      + `<span class="rlang" role="group" aria-label="language"><button type="button" data-lang="en" aria-pressed="${j.lang === 'en'}">English</button> · <button type="button" data-lang="id" aria-pressed="${j.lang === 'id'}">Bahasa Indonesia</button></span></div>`
      + `<label class="rpick"><span class="vh">${esc(L.find)}</span><input type="search" class="rfind" data-r="find" placeholder="${esc(L.find)}" aria-label="${esc(L.find)}"></label>`
      + `<div class="rtags">${j.picked.map(id => `<button type="button" data-rm="${esc(id)}" aria-label="remove">${esc(names[id] || id)} ×</button>`).join('')}</div>`
      + (j.sensors.length ? `<div class="rlist">${bySrc.map(([src, os]) => `<h4>${esc(src)}</h4>` + os.map(o => `<label><input type="checkbox" data-r="pick" value="${esc(o.id)}"${j.picked.includes(o.id) ? ' checked' : j.picked.length >= j.max_sensors ? ' disabled' : ''}>${esc(o.label)}</label>`).join('')).join('')}</div>` : `<p class="fine">${esc(L.none)}</p>`);
    const P = j.parts, table = (part, mark) => !P[part] ? '' : `<div class="tscroll"><table class="tbl rep"><tr>${P[part].cols.map((c, i) => `<th${i > 1 ? ' class="n"' : ''}>${esc(c)}</th>`).join('')}</tr>`
      + P[part].rows.map(row => `<tr>${row.map((cell, i) => `<td${i > 1 ? ' class="n' + (mark(i, cell) ? ' wr' : '') + '"' : ''}>${esc(cell ?? '–')}</td>`).join('')}</tr>`).join('') + `</table></div>`;
    const S = j.summary;
    const wd = iso => new Date(iso + 'T12:00:00').toLocaleDateString(loc2, { weekday: 'short' });
    const tile = (v, l, cls = '') => `<div class="rtile ${cls}"><b>${esc(v)}</b><span>${esc(l)}</span></div>`;
    const when = (day, at) => day ? `${wd(day)} ${at || ''}`.trim() : '';
    const one = S && S.sensors.length === 1 ? S.sensors[0] : null;
    const tiles = !S ? '' : `<div class="rtiles">` + (one
      ? tile(one.counted ? one.bad : '–', (one.counted === 7 ? L.bad_of : L.of_counted).replace('{n}', one.counted)) + tile(one.verdict || '–', L.verdict, one.verdict === L.worse ? 'wr' : '')
        + tile(one.peak ?? '–', L.highest_hour + ' · ' + when(one.peak_day, one.peak_at)) + tile(one.worst_mean ?? '–', L.worst_day + ' · ' + (one.worst_day ? wd(one.worst_day) : ''))
      : tile(S.overall.avg_bad ?? '–', L.avg_bad) + tile(S.overall.worst || '–', L.worst_place)
        + tile(S.overall.peak ?? '–', L.highest_hour + ' · ' + (S.overall.peak_place || '') + ' ' + when(S.overall.peak_day, S.overall.peak_at))) + `</div>`;
    const order = S ? [...S.sensors].sort((a, b) => b.bad - a.bad || (b.worst_mean || 0) - (a.worst_mean || 0)) : [];
    const grid = !S ? '' : `<div class="tscroll"><table class="rgrid"><tr><th></th>${S.sensors[0].days.map(d => `<th>${esc(wd(d.day))}</th>`).join('')}<th class="n">${esc(L.bad_days)}</th></tr>`
      + order.map(s => `<tr><td>${esc(s.label)}</td>${s.days.map(d => { const b = dayBlock(d); return `<td><span class="blk ${b.cls}" title="${esc(!d.counted ? L.not_counted : d.edge ? L.edge_note : d.day)}">${esc(b.text)}</span></td>`; }).join('')}<td class="n"><b>${s.bad}</b> / ${s.counted}</td></tr>`).join('') + `</table></div>`
      + `<p class="rlegend">${j.index ? [0, 1, 2, 3, 4].map(i => `<span class="blk aqi-${i}"></span> ${esc(L['band_' + i])}`).join(' ') + ` · <span class="blk aqi-0 edge"></span> ${esc(L.edge_note)} · ` : `<span class="blk nb bad"></span> ${esc(L.over_line)} · `}<span class="blk nc"></span> ${esc(L.not_counted)}${j.index ? ' · ' + esc(L.colours_from) : ''}</p>`;
    const daysBy = d3.groups((P.days || {}).rows || [], r => r[1]).map(([k, rs]) => [k, rs.filter(r => r[4] != null).map(r => [new Date(r[0] + 'T12:00:00'), r[4]])]);
    const meanFigs = `<div class="sms">${daysBy.map(([k, pts]) => `<figure class="sm"><figcaption><b>${esc(k)}</b></figcaption>${repChart(pts, { gap: 36 * 36e5, line: j.bad, bands: j.index, t0, t1 })}</figure>`).join('')}</div>`;
    const series = part => d3.groups((P[part] || {}).rows || [], r => r[1]).map(([k, rs]) => [k, rs.map(r => [new Date(r[0]), r[2]])]);
    const figs = (part, o) => { const ss = series(part), ref = (ss.find(([k]) => k === o.refName) || [])[1];
      return `<div class="sms">${ss.filter(([k]) => k !== o.refName).map(([k, pts]) => {
        const c = o.capped ? capTop(pts.map(p => p[1])) : null, top = c && c.top != null ? Math.max(c.top, o.line || 0) * 1.1 : o.top, ab = c ? aboveScale(pts, top) : { shown: [], more: 0 };
        return `<figure class="sm"><figcaption><b>${esc(k)}</b></figcaption>${repChart(pts, { ...o, ref, t0, t1, top })}`
          + (ab.shown.length ? `<p class="fine">${esc(L.above_cap)}: ${ab.shown.map(p => `${fmt(p[1], 0)} (${esc(dayOf(p[0].toISOString()))} ${esc(hhmm(p[0].toISOString()))})`).join(', ')}${ab.more ? ' · +' + ab.more : ''}</p>` : '') + `</figure>`; }).join('')}</div>`; };
    /* a redraw keeps where you were: the focused control (a box by its value) and what was typed in the name box */
    const at = sec.contains(document.activeElement) ? document.activeElement : null, was = at && { r: at.dataset.r, v: at.value };
    const typed = (sec.querySelector('[data-r=find]') || {}).value || '';
    sec.innerHTML = `<div class="dsh"><h2>${esc(L.title)}</h2>${L.how.split('\n\n').map(para).join('')}</div>` + pick
      + (!j.picked.length ? `<p class="fine">${esc(L.pick)}</p>` : tiles + `<div class="rbtns">${j.wk_complete ? `<button type="button" class="ybtn" data-pdf="1" title="${esc(L.pdf_hint)}">${esc(L.pdf)}</button>` : ''}${j.shareable ? `<button type="button" class="ybtn" data-share="1">${esc(L.share)}</button>` : ''}</div>${j.wk_complete ? `<p class="fine">${esc(L.pdf_hint)}</p>` : ''}<div class="rshare" hidden></div>`
        + `<h3>${esc(L.the_week)}</h3>` + grid
        + `<h3>${esc(L.daily_mean)}</h3>` + meanFigs
        + `<h3>${esc(L.p_badweeks)}</h3>` + figs('badweeks', { bars: true, top: 7 })
        + `<h3>${esc(L.p_hours)}</h3>` + figs('hours', { gap: 3 * 36e5, line: j.high, refName: L.high_line, capped: true })
        + `<h3>${esc(L.p_daily)}</h3>` + figs('daily', { gap: 36 * 36e5, refName: L.all })
        + `<h3>${esc(L.p_weeks)}</h3>` + table('weeks', (i, c) => c === L.worse)
        + `<h3>${esc(L.p_baddays)}</h3>` + (P.baddays && P.baddays.rows.length ? table('baddays', (i, c) => i === 2 && c < j.full_day) : '<p class="fine">–</p>'));
    const find = sec.querySelector('[data-r=find]');
    if (find && typed) { find.value = typed; find.dispatchEvent(new Event('input', { bubbles: true })); }
    const back = was && was.r && [...sec.querySelectorAll(`[data-r="${was.r}"]`)].find(el => was.r !== 'pick' || el.value === was.v);
    if (back) back.focus();
  }).catch(() => { if (seq === REPSEQ) sec.innerHTML = `<h2>Report</h2><p class="fine">The node did not answer. <a href="#data/report">Try again</a></p>`; });
}

/* SHARE (Tomas, 23 Nov 2026: "social sharing jpegs"; the image's job: "how bad the air was this week, and where"). One
   1080×1350 JPEG per place and, for two places or more, a comparison of the five worst, drawn here on a canvas in the
   page's paper register and its own fonts, and saved by the person. Always the visitor's view: the node is asked again
   with no token (repPublic), so a room the keeper picked never reaches an image; the panel says so when one was left out. */
const slug = t => String(t).normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/['’]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60).replace(/-+$/, '');
const sharedPlaces = ss => ss.filter(s => s.counted > 0);   // a place with no counted day gets no image
/* the comparison's rows under a title of tl lines: the pitch shrinks so the fifth row ends above the footer (1150 px) */
const compareLayout = (tl, n) => { const top = 140 + (tl - 1) * 80 + 56 + 70 + 40, row = 124; return { top, row, pitch: Math.min(168, Math.floor((1150 - row - top) / Math.max(1, n - 1))) }; };
/* the largest size up to `size` at which text fits `max` px */
function fitFont(g, text, max, size, face) { let z = size; do { g.font = face.replace('{z}', z); } while (g.measureText(text).width > max && --z > 10); return z; }
const fiveWorst = ss => [...ss].sort((a, b) => b.bad - a.bad || (b.worst_mean || 0) - (a.worst_mean || 0)).slice(0, 5);
function repPublic(a, ids) {
  const q = sens => '/weekly?' + new URLSearchParams({ metric: a.metric, sensors: sens.join(','), bad: a.bad, high: a.high, weeks: a.weeks, wk: a.wk, lang: a.lang });
  return fetch(q([])).then(r => r.json()).then(o => { const ok = new Set((o.sensors || []).map(x => x.id)), keep = ids.filter(id => ok.has(id));
    return (keep.length ? fetch(q(keep)).then(r => r.json()) : Promise.resolve(o)).then(j => ({ j, dropped: ids.length - keep.length })); });
}
const SH = { paper: '#F9F5F2', ink: '#171717', mute: '#6B6B66', nc: '#D9D4CE' };
const cssv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
/* text that fits `max` px in at most `lines` lines, the last one ellipsised */
function fitLines(g, text, max, lines) {
  const out = []; let cur = '';
  for (const w of String(text).split(/\s+/)) { const t = cur ? cur + ' ' + w : w; if (g.measureText(t).width <= max) cur = t; else { if (cur) out.push(cur); cur = w; } }
  if (cur) out.push(cur);
  if (out.length > lines) { out.length = lines; out[lines - 1] += '…'; }
  return out.map(l => { while (g.measureText(l).width > max && l.length > 2) l = l.slice(0, -2) + '…'; return l; });
}
function shareBlocks(g, days, x, y, w, h, gap, num) {
  const red = cssv('--signal-worse') || '#E62038';
  days.forEach((d, i) => {
    const b = dayBlock(d), band = /aqi-(\d)/.exec(b.cls), X = x + i * (w + gap);
    g.fillStyle = band ? cssv('--aqi-' + band[1]) : SH.nc; g.fillRect(X, y, w, h);
    if (d.edge) { g.strokeStyle = red; g.lineWidth = Math.max(4, w / 12); g.strokeRect(X + g.lineWidth / 2, y + g.lineWidth / 2, w - g.lineWidth, h - g.lineWidth); }
    if (num && b.text) { g.fillStyle = band ? cssv('--aqi-' + band[1] + '-ink') : SH.ink; g.font = `700 ${num}px "JetBrains Mono", monospace`; g.textAlign = 'center'; g.fillText(b.text, X + w / 2, y + h / 2 + num * 0.36); g.textAlign = 'left'; }
  });
}
function shareFoot(g, j, L) {
  const line = (j.bad_source === 'who' ? L.who_line : L.set_by_reader).replace('{v}', fmt(j.bad, 0)).replace('{unit}', j.unit || '');
  g.fillStyle = SH.mute; g.font = '400 30px "Figtree", sans-serif';
  fitLines(g, `${mWord(j.metric)}, ${L.mean}, ${line}. ${L.colours_from} ${L.not_calibrated}`, 936, 3).forEach((l, i) => g.fillText(l, 72, 1186 + i * 38));
  g.fillStyle = SH.ink; g.font = '700 32px "Figtree", sans-serif'; g.fillText(`${j.node || 'PLANETAI node'} · PLANETAI · Fab City`, 72, 1306);
}
const shareRange = j => { const loc = j.lang === 'id' ? 'id-ID' : 'en-GB'; return `${dshort(j.wk, loc)}–${dshort(plusDays(j.wk, 6), loc)}`; };
function shareCard(s, j) {
  const L = j.words, loc = j.lang === 'id' ? 'id-ID' : 'en-GB', c = document.createElement('canvas'); c.width = 1080; c.height = 1350;
  const g = c.getContext('2d'); g.fillStyle = SH.paper; g.fillRect(0, 0, 1080, 1350);
  g.fillStyle = SH.mute; g.font = '600 34px "JetBrains Mono", monospace'; g.fillText(`${L.air_week} · ${shareRange(j)}`.toUpperCase(), 72, 110);
  g.fillStyle = SH.ink; g.font = '800 112px "Figtree", sans-serif';
  const name = fitLines(g, s.label, 936, 2); name.forEach((l, i) => g.fillText(l, 72, 240 + i * 118));
  let y = 240 + (name.length - 1) * 118 + 64;
  g.fillStyle = SH.mute; g.font = '400 44px "Figtree", sans-serif'; g.fillText(`${mWord(j.metric)}${j.area ? ' · ' + j.area : ''}`, 72, y);
  y += 190; g.fillStyle = SH.ink; g.font = '800 184px "Figtree", sans-serif'; g.fillText(String(s.bad), 72, y);
  const nw = g.measureText(String(s.bad)).width, said = (s.counted === 7 ? L.bad_of : L.of_counted).replace('{n}', s.counted);
  fitFont(g, said, 1008 - (72 + nw + 24), 60, '600 {z}px "Figtree", sans-serif'); g.fillText(said, 72 + nw + 24, y);
  y += 60; shareBlocks(g, s.days, 72, y, 120, 120, 16, 46);
  g.fillStyle = SH.mute; g.font = '500 34px "JetBrains Mono", monospace'; g.textAlign = 'center';
  s.days.forEach((d, i) => g.fillText(new Date(d.day + 'T12:00:00').toLocaleDateString(loc, { weekday: 'narrow' }), 72 + i * 136 + 60, y + 170));
  g.textAlign = 'left';
  if (s.peak != null) { g.fillStyle = SH.ink; g.font = '400 46px "Figtree", sans-serif';
    g.fillText(`${L.highest_hour[0].toUpperCase() + L.highest_hour.slice(1)} ${s.peak} µg/m³, ${new Date(s.peak_day + 'T12:00:00').toLocaleDateString(loc, { weekday: 'short' })} ${s.peak_at}`, 72, y + 260); }
  shareFoot(g, j, L);
  return c;
}
function shareCompare(ss, j) {
  const L = j.words, c = document.createElement('canvas'); c.width = 1080; c.height = 1350;
  const g = c.getContext('2d'); g.fillStyle = SH.paper; g.fillRect(0, 0, 1080, 1350);
  g.fillStyle = SH.ink; g.font = '800 72px "Figtree", sans-serif';
  const title = fitLines(g, L.around.replace('{area}', j.area || j.node || ''), 936, 2); title.forEach((l, i) => g.fillText(l, 72, 140 + i * 80));
  let y = 140 + (title.length - 1) * 80 + 56;
  g.fillStyle = SH.mute; g.font = '600 32px "JetBrains Mono", monospace'; g.fillText(`${shareRange(j)} · ${mWord(j.metric)} · ${L.worst_first}`.toUpperCase(), 72, y);
  const rows = fiveWorst(ss), lay = compareLayout(title.length, rows.length);
  y += 70; g.textAlign = 'right'; g.fillText(`${L.bad_days}`.toUpperCase(), 1008, y); g.textAlign = 'left';
  rows.forEach((s, i) => {
    const Y = lay.top - 40 + i * lay.pitch;
    g.fillStyle = SH.ink; g.font = '700 46px "Figtree", sans-serif'; g.fillText(fitLines(g, s.label, 760, 1)[0], 72, Y + 40);
    shareBlocks(g, s.days, 72, Y + 64, 92, 56, 10, 0);
    g.textAlign = 'right'; g.fillStyle = SH.mute; g.font = '600 40px "Figtree", sans-serif'; g.fillText(`/ ${s.counted}`, 1008, Y + 118);
    const cw = g.measureText(`/ ${s.counted}`).width; g.fillStyle = SH.ink; g.font = '800 92px "Figtree", sans-serif'; g.fillText(String(s.bad), 1008 - cw - 12, Y + 118); g.textAlign = 'left';
  });
  shareFoot(g, j, L);
  return c;
}
function shareSave(i) {
  const it = SHARE_C[i]; if (!it) return;
  it.c.toBlob(bl => { const a = document.createElement('a'); a.href = URL.createObjectURL(bl); a.download = it.name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); }, 'image/jpeg', 0.92);
}
function repShare() {
  const sec = $('#d-report'), box = sec.querySelector('.rshare'), a = REPLAST; if (!box || !a) return;
  box.hidden = false; box.innerHTML = `<p class="fine">…</p>`;
  /* allSettled: a face that cannot load (no route out, a blocked file) leaves the image in the fallback face rather than no image */
  repPublic(a, a.picked).then(({ j, dropped }) => Promise.allSettled([document.fonts.load('800 112px "Figtree"'), document.fonts.load('600 34px "JetBrains Mono"')])
    .then(() => document.fonts.ready).then(() => {
      const L = j.words, ss = sharedPlaces((j.summary || {}).sensors || []);
      if (!ss.length) { box.innerHTML = `<p class="fine">${esc(dropped ? L.rooms_out : L.none)}</p>`; return; }
      SHARE_C = ss.map(s => ({ c: shareCard(s, j), name: `${slug(s.label) || 'place'}-${j.wk}.jpg` }));
      if (ss.length > 1) SHARE_C.push({ c: shareCompare(ss, j), name: `comparison-${j.wk}.jpg` });
      box.innerHTML = `<p class="fine">${esc(L.share_note)}${dropped ? ' ' + esc(L.rooms_out) : ''}</p><div class="rshots">`
        + SHARE_C.map((it, i) => `<figure><span class="rshot"></span><button type="button" class="ybtn" data-dl="${i}">${esc(L.download)} · ${esc(it.name)}</button></figure>`).join('') + `</div>`;
      box.querySelectorAll('.rshot').forEach((el, i) => el.appendChild(SHARE_C[i].c));
    })).catch(() => { box.innerHTML = `<p class="fine">${esc(a.words.no_answer)}</p>`; });
}

/* PDF (Tomas, 23 Nov 2026: "download as pdf full report"). The browser's print, on A4 portrait pages like the Place report:
   page 1 the overview of the places picked, then a page per place. Built from the visitor's view (repPublic), on paper
   whatever the screen's register, the air colours printed as they are. buildWeeklyPages() is apart from printing, so the
   visual gate can count the pages; printWeekly() prints and takes the pages away again. */
function buildWeeklyPages(j) {
  const L = j.words, S = j.summary || { sensors: [], overall: {} }, loc = j.lang === 'id' ? 'id-ID' : 'en-GB', P = j.parts || {};
  const wd = iso => new Date(iso + 'T12:00:00').toLocaleDateString(loc, { weekday: 'short' }), range = `${dshort(j.wk, loc)} – ${dshort(plusDays(j.wk, 6), loc)}`;
  const tile = (v, l, cls = '') => `<div class="rtile ${cls}"><b>${esc(v)}</b><span>${esc(l)}</span></div>`;
  const n = 1 + S.sensors.length, foot = i => `<div class="wfoot"><span>${esc(j.node || '')} · PLANETAI · Fab City · ${esc(L.not_calibrated)}</span><span>${esc(L.page.replace('{i}', i).replace('{n}', n))}</span></div>`;
  const grid = `<table class="rgrid"><tr><th></th>${(S.sensors[0] || { days: [] }).days.map(d => `<th>${esc(wd(d.day))}</th>`).join('')}<th class="n">${esc(L.bad_days)}</th></tr>`
    + [...S.sensors].sort((a, b) => b.bad - a.bad || (b.worst_mean || 0) - (a.worst_mean || 0)).map(s => `<tr><td>${esc(s.label)}</td>${s.days.map(d => { const b = dayBlock(d); return `<td><span class="blk ${b.cls}">${esc(b.text)}</span></td>`; }).join('')}<td class="n"><b>${s.bad}</b> / ${s.counted}</td></tr>`).join('') + `</table>`
    + (j.index ? `<p class="rlegend">${[0, 1, 2, 3, 4].map(i => `<span class="blk aqi-${i}"></span> ${esc(L['band_' + i])}`).join(' ')} · <span class="blk aqi-0 edge"></span> ${esc(L.edge_note)} · <span class="blk nc"></span> ${esc(L.not_counted)}</p>` : '');
  const line = (j.bad_source === 'who' ? L.who_line : L.set_by_reader).replace('{v}', fmt(j.bad, 0)).replace('{unit}', j.unit || '');
  const head = `<div class="wk">${esc(L.title)} · ${esc(mWord(j.metric))} · ${esc(range)}</div>`;
  const O = S.overall;
  const first = `<section class="wpage">${head}<h1>${esc(L.around.replace('{area}', j.area || j.node || ''))}</h1><div class="sub">${esc(L.picked_n.replace('{n}', S.sensors.length).replace('{node}', j.node || ''))} · ${esc(line)}</div>`
    + `<div class="rtiles">${tile(O.avg_bad ?? '–', L.avg_bad)}${tile(O.worst || '–', L.worst_place)}${tile(O.peak ?? '–', L.highest_hour + ' · ' + (O.peak_place || ''))}</div>`
    + `<h3>${esc(L.the_week)}</h3>${grid}<h3>${esc(L.p_how)}</h3><div class="how">${L.how.split('\n\n').map(p => `<p>${esc(p).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')}</p>`).join('')}</div>${foot(1)}</section>`;
  const t0 = new Date(j.t0), t1 = new Date(j.t1), endWk = plusDays(j.wk, 6);
  const pages = S.sensors.map((s, k) => {
    const mean = ((P.days || {}).rows || []).filter(r => r[2] === s.id && r[4] != null).map(r => [new Date(r[0] + 'T12:00:00'), r[4]]);
    const bars = ((P.badweeks || {}).rows || []).filter(r => r[1] === s.label).map(r => [new Date(r[0]), r[2]]);
    const bd = P.baddays || { cols: [], rows: [] }, rows = bd.rows.filter(r => r[1] === s.label && r[0] >= j.wk && r[0] <= endWk);
    return `<section class="wpage">${head}<h1>${esc(s.label)}</h1><div class="sub">${esc(mWord(j.metric))}${j.area ? ' · ' + esc(j.area) : ''} · ${esc(line)}</div>`
      + `<div class="rtiles">${tile(s.counted ? s.bad : '–', (s.counted === 7 ? L.bad_of : L.of_counted).replace('{n}', s.counted))}${tile(s.verdict || '–', L.verdict, s.verdict === L.worse ? 'wr' : '')}${tile(s.peak ?? '–', L.highest_hour + ' · ' + (s.peak_day ? wd(s.peak_day) + ' ' + (s.peak_at || '') : ''))}${tile(s.worst_mean ?? '–', L.worst_day + ' · ' + (s.worst_day ? wd(s.worst_day) : ''))}</div>`
      + `<h3>${esc(L.daily_mean)}</h3>${repChart(mean, { gap: 36 * 36e5, line: j.bad, bands: j.index, t0, t1 })}`
      + `<h3>${esc(L.p_badweeks)}</h3>${repChart(bars, { bars: true, top: 7, t0, t1 })}`
      + `<h3>${esc(L.p_baddays)}</h3>` + (rows.length ? `<table class="tbl rep"><tr>${bd.cols.filter((c, i) => i !== 1).map((c, i) => `<th${i ? ' class="n"' : ''}>${esc(c)}</th>`).join('')}</tr>`
        + rows.map(r => `<tr>${r.filter((v, i) => i !== 1).map((v, i) => `<td${i ? ` class="n${i === 1 && v < j.full_day ? ' wr' : ''}"` : ''}>${esc(v ?? '–')}</td>`).join('')}</tr>`).join('') + `</table>` : '<p class="fine">–</p>')
      + `${foot(k + 2)}</section>`;
  });
  const box = $('#wpages'); box.innerHTML = first + pages.join('');
  return n;
}
function printWeekly() {
  const a = REPLAST; if (!a) return;
  const box = $('#d-report .rshare');
  repPublic(a, a.picked).then(({ j }) => {
    if (!((j.summary || {}).sensors || []).length) { if (box) { box.hidden = false; box.innerHTML = `<p class="fine">${esc(j.words.rooms_out)}</p>`; } return; }   // nothing a visitor may see: no blank PDF
    buildWeeklyPages(j); document.body.classList.add('pweekly');
    const done = () => { document.body.classList.remove('pweekly'); $('#wpages').innerHTML = ''; window.removeEventListener('afterprint', done); };
    window.addEventListener('afterprint', done); window.print();
  }).catch(() => { if (box) { box.hidden = false; box.innerHTML = `<p class="fine">${esc(a.words.no_answer)}</p>`; } });
}

/* THE WORKBENCH (Tomas, 27 Oct 2026: "embeds in the same data menu", "a reduced version of the full workbench",
   "able to run offline in the node"). The node's copy of planetai.fab.city/sensors, served at /workbench and reduced
   there (workbench-node.html), drawn in a frame so its own styles and script stay out of the doors. The frame is made
   once and kept, so a refresh of Data never reloads a flash in progress; #data/workbench/<flash|test|network> picks
   its view. Its height follows its page. The full workbench is linked only when planetai.fab.city answers. */
function workbenchBlock() {
  const sec = $('#d-workbench'), view = decodeURIComponent(location.hash.split('/')[2] || '');
  let f = sec.querySelector('iframe');
  if (f) { if (view && f.contentWindow && f.contentWindow.location.hash !== '#' + view) f.contentWindow.location.hash = view; return; }
  sec.innerHTML = `<div class="dsh"><h2>Flash and test a sensor</h2><p class="blurb">Flash the Bayu and every Meshtastic radio, test a board over USB and see the network this node hears. It works with no internet: the firmware and the flasher are kept on this node. <span id="wbfull"></span></p></div>
    <iframe src="/workbench${view ? '#' + encodeURIComponent(view) : ''}" title="Sensors workbench" allow="serial"></iframe>`;
  f = sec.querySelector('iframe');
  f.onload = () => {
    const d = f.contentDocument; if (!d || !d.body) return;
    new ResizeObserver(() => { f.style.height = d.body.offsetHeight + 'px'; }).observe(d.body);
  };
  fetch('https://planetai.fab.city/sensors/manifest.webmanifest', { mode: 'no-cors', cache: 'no-store', signal: AbortSignal.timeout(5000) })
    .then(() => { $('#wbfull').innerHTML = '<a href="https://planetai.fab.city/sensors/" target="_blank" rel="noopener">The full workbench, on planetai.fab.city ↗</a>'; })
    .catch(() => {});
}

function metricTiles() {
  const S2 = D.raw ? D.raw.series : {}, src = {}, now = {};
  for (const id in S2) for (const m in S2[id]) (src[m] ||= new Set()).add(id);
  for (const id in D.stats15) for (const m in D.stats15[id]) { (src[m] ||= new Set()).add(id); const v = D.stats15[id][m][0]; if (v != null) (now[m] ||= []).push(v); }
  /* a kind only models read is drawn in the Models tab, as a value in a table, not as an empty tile here */
  const modelOnly = m => [...src[m]].every(id => (D.sens[id] || {}).kind === 'model');
  const known = new Set(FAMILY.flatMap(f => f[1])), fams = FAMILY.map(([t, ms]) => [t, ms.filter(m => src[m] && !modelOnly(m))])
    .concat([['Other', Object.keys(src).filter(m => !known.has(m) && !m.startsWith('fc_') && !modelOnly(m)).sort()]]).filter(f => f[1].length);
  if (!src[METRIC]) METRIC = (fams[0] || [, []])[1][0] || METRIC;
  /* the 24-hour trace: the median, hour by hour, of every source's hourly mean (the table, token-only) */
  const trace = m => {
    if (!D.raw) return '';
    const B = D.raw.buckets, med = B.map((_, i) => d3.median([...src[m]].map(id => ((S2[id] || {})[m] || [])[i]).filter(Boolean).map(v => v[0])));
    if (med.filter(v => v != null).length < 2) return '';
    const x = d3.scaleLinear([0, B.length - 1], [1, 99]), y = d3.scaleLinear(d3.extent(med.filter(v => v != null)), [22, 2]).nice();
    return `<svg class="tr" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true"><path d="${d3.line().defined(v => v != null).x((v, i) => x(i)).y(v => y(v))(med)}"/></svg>`;
  };
  let k = 0;
  /* every figure carries its date and its word (the layer): a tile is the median of the latest 15-minute means */
  $('#metrics').innerHTML = `<p class="fine mdate">Medians of each source’s latest 15-minute mean, ${esc(wdhm(D.as_of))} ${prov('live')}</p>` + fams.map(([t, ms]) => `<div class="fam" data-fam="${esc(t)}"><div class="fh k">${t}<span><b>${ms.length}</b> kind${ms.length === 1 ? '' : 's'}</span></div><div class="tiles">${ms.map(m => {
    const n = src[m].size, md = now[m] && now[m].length ? d3.median(now[m]) : null, dp = Math.abs(md) >= 100 ? 0 : Math.abs(md) >= 10 ? 1 : 2;
    return `<button type="button" class="mt ${m === METRIC ? 'on' : ''}" data-m="${esc(m)}" aria-pressed="${m === METRIC}" style="--i:${k++}">`
      + `<span class="sym">${esc(SYM[m] || m.slice(0, 4))}</span><span class="mn said">${esc(mWord(m))}</span>${trace(m)}`
      + `<span class="mv">${md == null ? '<b>—</b>' : num(`metric.${m}.median`, fmt(md, dp), `median of ${now[m].length} sources’ 15-minute means`, `<b>${fmt(md, dp)}</b>`)} <span class="said">${esc(unitOf(m))}</span></span>`
      + `<span class="ms">${n} source${n === 1 ? '' : 's'}</span></button>`; }).join('')}</div></div>`).join('');
  document.querySelectorAll('#metrics .mt').forEach(b => b.onclick = () => { METRIC = b.dataset.m;
    document.querySelectorAll('#metrics .mt').forEach(x => { x.classList.toggle('on', x === b); x.setAttribute('aria-pressed', String(x === b)); });
    sensorsBlock(); document.getElementById('sensors').scrollIntoView({ behavior: CLOCK.reduced() ? 'auto' : 'smooth', block: 'start' }); });
}

/* THE API, from the documentation the node carries (data/docs_site.json, cut from docs/site/api.md by `make learn`):
   every route, its access, and whether this screen may read it; a curl line to copy; GET routes this screen can read
   open in place. The node's own words, never a second copy. */
let APIDOC = null;
async function apiBlock() {
  const el = $('#api');
  if (!APIDOC) APIDOC = await fetch('/static/docs_site.json').then(r => r.ok ? r.json() : []).catch(() => []);
  const secs = APIDOC.filter(x => x.page === 'api.md' && /### (GET|POST|PUT|DELETE|PATCH) /.test(x.text || ''));
  const docs = D.health.docs || 'https://planetai.fab.city/docs/', tok = !!DOORS_TOKEN(), open = D.share === 'open';
  const can = a => a === 'public' || (a === 'open' && (open || tok)) || (tok && a !== 'public' && a !== 'open');
  const RX = /### (GET|POST|PUT|DELETE|PATCH) (\S+)\s+Access:\s*(\w+)\s*([\s\S]*?)(?=### (?:GET|POST|PUT|DELETE|PATCH) |$)/g;
  const first = t => t.split(/\s\|\s|\s#{2,} /)[0].replace(/`/g, '').replace(/\s+/g, ' ').trim().split(/(?<=\.)\s/).slice(0, 2).join(' ');
  const routes = secs.map(sec => ({ title: sec.title.replace(/^HTTP API · /, ''), rows: [...sec.text.matchAll(RX)].map(m => ({ method: m[1], path: m[2], access: m[3], say: first(m[4]) })) }))
    .filter(g => g.rows.length);
  const n = routes.reduce((a, g) => a + g.rows.length, 0);
  el.innerHTML = `<div class="dsh"><h2>API</h2><p class="blurb">Everything on these pages is one of ${n} routes on this node, at <span class="mono">${esc(location.origin)}</span>, each answering JSON. `
    + `A route marked token wants <span class="mono">Authorization: Bearer &lt;token&gt;</span>; <code>planetai ui</code> prints the tokens. `
    + `<a href="${esc(docs)}api/" target="_blank" rel="noopener">The full reference ↗</a> · <a href="/llms.txt">llms.txt</a> for agents · MCP at <span class="mono">/mcp</span> with the admin token.</p></div>`
    + `<label class="afind"><span class="k">find</span><input type="search" id="afind" placeholder="a route, a word: readings, alerts, cells…" autocomplete="off"></label>`
    + routes.map(g => `<div class="ag"><div class="agh k">${esc(g.title)}<span>${g.rows.length}</span></div>${g.rows.map(r => {
      const yes = can(r.access), path = r.path, curl = `curl ${location.origin}${path}${r.access === 'public' || (r.access === 'open' && open) ? '' : ' -H "Authorization: Bearer $TOKEN"'}`;
      const go = r.method === 'GET' && yes && !/[{]/.test(path);
      return `<details class="ar" data-q="${esc((r.method + ' ' + path + ' ' + r.say + ' ' + g.title).toLowerCase())}"><summary><span class="am">${r.method}</span><span class="ap mono">${esc(path)}</span>`
        + `<span class="aa ${r.access}">${esc(r.access)}</span><span class="ay ${yes ? 'yes' : ''}">${yes ? 'this screen reads it' : 'needs the token'}</span></summary>`
        + `<p class="as">${esc(r.say)}</p><div class="ac"><code>${esc(curl)}</code><button type="button" class="sbtn" data-copy="${esc(curl)}">copy</button>${go ? `<a class="sbtn" href="${esc(path)}" target="_blank" rel="noopener">open ↗</a>` : ''}</div></details>`; }).join('')}</div>`).join('');
  $('#afind').oninput = e => { const q = e.target.value.trim().toLowerCase();
    el.querySelectorAll('.ar').forEach(r => { r.hidden = !!q && !r.dataset.q.includes(q); });
    el.querySelectorAll('.ag').forEach(g => { g.hidden = ![...g.querySelectorAll('.ar')].some(r => !r.hidden); }); };
  el.querySelectorAll('[data-copy]').forEach(b => b.onclick = () => { navigator.clipboard && navigator.clipboard.writeText(b.dataset.copy).then(() => { b.textContent = 'copied'; setTimeout(() => { b.textContent = 'copy'; }, 1400); }); });
}

function sensorsBlock() {
  if (!D.raw) { $('#sensors').innerHTML = `<div class="dh"><h2>Every source, last 24 hours</h2></div><p class="fine">The hourly table, GET /aggregates, is the household’s own readings hour by hour, so the node gives it only to a screen holding the token. Unlock this screen in ${UNLOCK_AT} to draw it; the issues, the models, the Index and the ledger below are open.</p>`; return; }
  const B = D.raw.buckets, ids = Object.keys(D.raw.series).filter(id => D.raw.series[id][METRIC]);
  const rows = ids.map(id => ({ id, s: D.sens[id] || { name: id, local: false, kind: 'sensor' }, a: D.raw.series[id][METRIC] }))
    .map(r => ({ ...r, d: ((D.ngeo && D.ngeo.dist[r.id]) || { m: 0 }).m / 1000 /* the node's metres */, last: (r.a.filter(Boolean).pop() || [])[0] }))
    .sort((a, b) => (b.s.local - a.s.local) || (a.d - b.d));
  const vals = rows.flatMap(r => r.a.filter(Boolean).flatMap(v => [v[1], v[2]])).sort(d3.ascending);
  const lo = Math.min(0, d3.min(vals) ?? 0), cap = d3.quantile(vals, .98) ?? 1, top = METRIC === 'pm25' ? Math.max(cap, D.issues.air.line * 1.2) : cap;
  const line = METRIC === 'pm25' ? D.issues.air.line : null, W = 300, H = 34, x = d3.scaleLinear([0, B.length - 1], [2, W - 2]), y = d3.scaleLinear([lo, top], [H - 3, 3]).clamp(true);
  const spark = a => {
    const pts = a.map((v, i) => v ? [i, v] : null);
    const band = d3.area().defined(p => p).x(p => x(p[0])).y0(p => y(p[1][1])).y1(p => y(p[1][2]))(pts);
    const ln = d3.line().defined(p => p).x(p => x(p[0])).y(p => y(p[1][0]))(pts);
    const over = line != null ? pts.filter(p => p && p[1][0] > line).map(p => `<rect x="${x(p[0]) - 3}" y="${H - 3}" width="6" height="3" fill="var(--signal-worse)"/>`).join('') : '';
    const clip = pts.filter(p => p && p[1][2] > top).length ? `<text x="${W - 2}" y="9" text-anchor="end" class="lab">↑ ${fmt(d3.max(a.filter(Boolean), v => v[2]), 0)}</text>` : '';
    return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" class="sp"><path d="${band}" class="bandp"/><path d="${ln}" class="lnp"/>`
      + (line != null ? `<line x1="0" x2="${W}" y1="${y(line)}" y2="${y(line)}" class="linep"/><text x="2" y="${y(line) < 12 ? y(line) + 10 : y(line) - 3}" class="lab">${lineLab(D.issues.air)}</text>` : '') + over + clip + `</svg>`;
  };
  const grp = (t, rs) => rs.length ? `<div class="gh k">${t} · ${rs.length}</div>` + rs.map(r => `<div class="srow" data-sid="${esc(r.id)}"><span class="t">${esc(plain(r.s.name || r.id))}<small>${srcLink({ ...r.s, sensor_id: r.s.sensor_id || r.id }, esc(r.s.source || ''))}${r.s.lat != null ? ` · ${fmt(r.d, 1)} km` : ''}${r.s.indoor ? ' · inside' : ''}</small></span>${spark(r.a)}<span class="c">${num(r.id + '.' + METRIC, fmt(r.last, (D.metrics[METRIC] || {}).dp ?? 1), line != null ? `the line ${line}` : `one scale, ${fmt(lo, 0)} to ${fmt(top, 0)}`)}</span></div>`).join('') : '';
  $('#sensors').innerHTML = `<div class="dh"><h2>${said(labelOf(METRIC))}, every source, last 24 hours</h2><span class="k">one scale, ${fmt(lo, 0)} to ${fmt(top, 0)} ${said(unitOf(METRIC))} · band = the hour’s low to high · line = its mean${line != null ? ' · red: over the line' : ''}</span></div>`
    + grp(asHouse('This house'), rows.filter(r => r.s.local)) + grp('Around it', rows.filter(r => !r.s.local && r.s.kind !== 'model')) + grp('Models', rows.filter(r => r.s.kind === 'model'))
    + `<div class="axis"><span></span><span class="mono k">${hhmm(B[0])} yesterday → ${hhmm(B[B.length - 1])} today</span><span></span></div>`;
  calibrateOnRows();
}

function issuesBlock() {
  const out = [];
  for (const k of D.order.filter(ISSUES_DRAWN)) for (const dk of ['room', 'yard', 'ring']) {
    const it = D.issues[k], s = it.series[dk]; if (!s) continue;
    const W = 360, H = 110, x = d3.scaleLinear([0, s.length - 1], [30, W - 6]), vs = s.filter(v => v != null).sort(d3.ascending);
    const top = Math.max(it.line ?? 0, d3.quantile(vs, .98)) * 1.1, lo = k === 'heat' ? Math.floor(vs[0] - 1) : 0, y = d3.scaleLinear([lo, top], [H - 16, 6]).nice(3);
    const ln = d3.line().defined(v => v != null).x((v, i) => x(i)).y(v => y(Math.min(v, y.domain()[1])))(s);
    const days = D.dates.map(dt => D.at[dt + '|0']).filter(j => j != null);
    out.push(`<figure class="sm"><figcaption><b>${said(it.name)}</b> · ${said(D.labels[dk])} ${prov((it.provenance || {})[dk] || 'model')}</figcaption><svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">`
      + y.ticks(3).map(t => `<line x1="30" x2="${W - 6}" y1="${y(t)}" y2="${y(t)}" class="grid"/><text x="26" y="${y(t) + 4}" text-anchor="end">${fmt(t, 0)}</text>`).join('')
      + days.map(j => `<line x1="${x(j)}" x2="${x(j)}" y1="6" y2="${H - 16}" class="grid"/><text x="${x(j) + 3}" y="${H - 4}">${dayOf(D.buckets[j]).slice(8)}</text>`).join('')
      + (it.line != null ? `<line x1="30" x2="${W - 6}" y1="${y(it.line)}" y2="${y(it.line)}" class="linep"/><text x="34" y="${y(it.line) - 3}" class="lab">${lineLab(it)}</text>` : '') + `<path d="${ln}" class="lnp" style="stroke-width:${dk === 'room' ? 1.6 : 1.1}"/></svg></figure>`);
  }
  $('#issues7').innerHTML = `<h2>Every issue, every distance, seven days</h2><div class="sms">${out.join('')}</div><p class="fine">Hourly, from GET /issues/days. Each drawing keeps its own scale, capped at the 98th percentile; the red dash is the line. Day numbers mark local midnight.</p>`;
}

/* Where each source publishes what this node read from it, opened in a new tab (Tomas, 15 Oct: every sensor and every
   value links to its source). A kit with its own public page links to that page; a source this house runs itself (its
   own radio, its own inventory) has no page and gets no link. */
const SRC_URL = {
  smartcitizen: s => `https://smartcitizen.me/kits/${String(s.sensor_id || '').replace(/^\D+-/, '')}`,
  airgradient: () => 'https://app.airgradient.com/', purpleair: () => 'https://map.purpleair.com/',
  baliairdispatch: () => 'https://baliairdispatch.com/', 'fablabs-io': s => (s.meta || {}).url || 'https://www.fablabs.io/labs',
  openstreetmap: () => 'https://www.openstreetmap.org/', 'open-meteo': () => 'https://open-meteo.com/en/docs',
  'forecast-om': () => 'https://open-meteo.com/en/docs', 'open-meteo-cams': () => 'https://open-meteo.com/en/docs/air-quality-api',
  'open-meteo-marine': () => 'https://open-meteo.com/en/docs/marine-weather-api', firms: () => 'https://firms.modaps.eosdis.nasa.gov/map/',
  'modis-lst': () => 'https://lpdaac.usgs.gov/products/mod11a1v061/',
  'landsat-lst': () => 'https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature',
  'earth-engine': () => 'https://developers.google.com/earth-engine/datasets',
  earth: () => 'https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL',
};
const srcLink = (s, label) => { const f = SRC_URL[(s || {}).source], u = f && f(s);
  return u ? `<a href="${esc(u)}" target="_blank" rel="noopener">${label} ↗</a>` : label; };
/* MODELS AND THE SATELLITE: one table, a row per value under a row per source, which says how often that source
   is fetched in words and that a model is partial. The unit is the node's where it has one (GET /issues → metrics);
   a model's own kinds keep theirs here. A share is printed as a percent. The node's counters about its own fetching
   (how many years are cached, a forecast's lead hours) say nothing about the place and are not drawn. */
const CADENCE = { PT5M: 'every 5 minutes', PT15M: 'every 15 minutes', PT1H: 'hourly', PT3H: 'every 3 hours', PT6H: 'every 6 hours', P1D: 'daily', P7D: 'weekly', P30D: 'monthly', P1M: 'monthly', P1Y: 'yearly' };
const MINTERNAL = /^(years_cached|fc_)/;
const MUNIT = { pm25_model: 'µg/m³', pm10_model: 'µg/m³', o3: 'µg/m³', no2: 'µg/m³', co: 'µg/m³', dust: 'µg/m³', temp_model: '°C', humidity_model: '%',
  pressure_model: 'hPa', wind_speed: 'km/h', wind_direction: '°', precipitation: 'mm', sea_surface_temp: '°C', wave_direction: '°', night_lights: 'nW/cm²/sr',
  businesses_per_km2: 'per km²', roads_km: 'km', river_flow_m3s: 'm³/s', river_largest_m3s: 'm³/s', river_upland_km2: 'km²', river_to_sea_km: 'km', basin_up_km2: 'km²', river_order: 'Strahler', buildings: 'buildings', sat_buildings: 'buildings', sat_buildings_yearly: 'buildings' };
const MWORD = { built_frac: 'built up', crop_frac: 'cropland', tree_frac: 'trees', water_frac: 'water', ndvi_median: 'greenness (NDVI, median)',
  land_change_score: 'land change, score', land_change_since_2017: 'land change since 2017', land_change_yoy: 'land change, last year',
  sat_buildings: 'buildings, from the satellite', sat_buildings_yearly: 'buildings in the yearly count, from the satellite', sat_height_m_yearly: 'building height, from the satellite',
  sat_confidence: 'satellite buildings, confidence', osm_building_coverage: 'buildings mapped in OpenStreetMap',
  river_m: 'the nearest river, away', river_flow_m3s: 'its flow, long-term average', river_order: 'its order', river_upland_km2: 'ground that drains into it',
  river_to_sea_km: 'how far it still runs to the sea', river_largest_m3s: 'the largest river in the square, its flow', basin_up_km2: 'ground upstream of the node’s basin' };
const mrow = o => {
  const m = o.metric, share = /(_frac|_share|_coverage|_confidence)$/.test(m);
  const unit = share ? '%' : MUNIT[m] ?? (/_m(_yearly)?$/.test(m) ? 'm' : /_s$/.test(m) ? 's' : /^poi_/.test(m) ? 'places' : unitOf(m));
  const v = share ? o.value * 100 : o.value, dp = Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 1 ? 1 : 3;
  return { what: MWORD[m] || mWord(m).replace(/^poi /, '').replace(/ m$/, ''), v: fmt(v, dp), unit };
};
function modelsBlock() {
  const by = d3.group(D.observations.filter(o => !MINTERNAL.test(o.metric)), o => o.sensor_id);
  const at = os => d3.max(os, o => o.ts), head = (id, os) => { const c = os[0].cadence;
    return `<tr class="grp" id="m-${esc(id)}"><th colspan="4"><b>${said(os[0].name || (D.sens[id] || {}).name || id)}</b> <span>${esc(CADENCE[c] || c || '')}`
      + ` · as of ${esc(when(at(os)))}</span> ${prov('model')} ${srcLink({ sensor_id: id, ...(D.sens[id] || {}), source: (D.sens[id] || {}).source || os[0].source }, 'source')}</th></tr>`; };
  $('#models').innerHTML = `<h2>Models and the satellite</h2><p class="blurb">What the models and the satellite say about this point, ${D.observations.length} values from ${by.size} sources. `
    + `A model is partial, whatever its quality: it is the place as a model sees it, never measured here.</p>`
    + `<table class="tbl mtab"><thead><tr><th>what</th><th class="n">value</th><th>unit</th><th class="hide">as of</th></tr></thead>`
    + [...by].map(([id, os]) => `<tbody>${head(id, os)}` + os.map(o => { const r = mrow(o);
      return `<tr><td>${esc(r.what)}</td><td class="n">${r.v}</td><td class="u">${said(r.unit || '—')}</td><td class="hide mono">${o.ts === at(os) ? '' : esc(when(o.ts))}</td></tr>`; }).join('') + `</tbody>`).join('')
    + `</table>`;
}
/* CORRECTIONS — a sensor a keeper named beside a better one, corrected against it (GET /calibrate, the calibrate pack).
   The corrected number lives on this page only, and only while it has been at least a tenth closer on days the line
   never saw; every other row says why not. calibrateRows is pure: it takes the parsed answer, or { state: 'failed' }
   for no answer, and gives the HTML (a 404 is the pack switched off, said by calibrateBlock); calibrateMarks gives the Readings row its one line. */
/* a side stuck on one value is not being paired: the state says which, after whatever else it says */
function cwhy(r) {
  const o = r[r.stuck], said = (() => {
    const CWORDS = { fields: 'needs four or five parts', date: 'a date is not a date', 'until-before-since': 'the last day is before the first',
      'since-in-future': 'the first day is in the future', same: 'both ids are the same', duplicate: 'this sensor is already in an earlier pair' };
    const w = r.why || {}, id = s => (r[s] || {}).id, N = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const day = s => { const d = new Date(String(s).slice(0, 10) + 'T00:00:00Z'); return `${d.getUTCDate()} ${N[d.getUTCMonth() + 1]}`; };
    // last_paired is an hour; its day is the node's (D.tz) where the page knows it, else the string's own clock
    const local = s => typeof doorsLocal === 'function' && typeof D !== 'undefined' && D && D.tz ? doorsLocal(s, D.tz) : s;
    if (r.shown) return r.last_paired ? `shown, last checked ${day(local(r.last_paired))}` : 'shown';
    if (w.reason === 'malformed') return `cannot read "${r.entry}": ${CWORDS[w.problem] || w.problem}`;
    if (w.reason === 'refused') {
      const t = w.test, who = id(w.side);
      return t === 'unknown' ? `not known to this node: ${who}` : t === 'not-a-sensor' ? `${who} is not a sensor`
        : t === 'sensor-is-station' ? 'a public station cannot be the one corrected' : t === 'no-channel' ? `${w.source} declares no ${r.metric} channel`
        : t === 'indoor-outdoor' ? 'one is indoors and the other outdoors' : `${w.metres} m apart`;
    }
    if (w.reason === 'flat') return 'no line: one of the two read one value for two weeks';
    if (w.reason === 'young') return r.line ? `too young: ${w.days} of ${w.need_days} days checked` : `too young: ${w.hours} of ${w.need_hours} hours together`;
    if (w.reason === 'measured-closer') return 'not shown: measured is closer';
    if (w.reason === 'not-a-tenth') return 'not shown: not a tenth closer';
    if (w.reason === 'withdrawn') return `withdrawn: nothing beside it since ${day(w.since)}`;
    return 'nothing beside it for six weeks';
  })();
  return said + (o ? `, ${o.name || o.id} is stuck on one value` : '');
}
/* an hour that started more than 3 hours before now is old: its number says which hour, and Readings draws no mark */
function calibrateRows(j, docs, word = x => x, now = Date.now()) {
  const state = (j || {}).state, say = t => `<p class="fine">${t}</p>`;
  if (state === 'off') return say(`No sensor on this node is corrected against another. Name a pair in Set up, under Calibrate. <a href="${esc((docs || 'https://planetai.fab.city/docs/') + 'calibrate/')}" target="_blank" rel="noopener">How it works</a>.`);
  if (state !== 'ok') return say('The corrections could not be read.');
  const rows = j.rows || [], N = Math.max(0, ...rows.map(r => (r.checked || {}).days || 0)), u = r => said(r.unit || '');
  const MO = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const local = s => typeof doorsLocal === 'function' && typeof D !== 'undefined' && D && D.tz ? doorsLocal(s, D.tz) : String(s);
  const at = r => { if (!r.hour || now - Date.parse(r.hour) <= 3 * 3600e3) return ''; const s = local(r.hour);
    return ` at ${s.slice(11, 16)} ${+s.slice(8, 10)} ${MO[+s.slice(5, 7) - 1]}`; };
  const against = r => { const f = r.reference || {}, n = esc(f.name || f.id);
    return f.own ? `${n}, your own sensor${r.metres == null ? ', distance not known' : `, ${r.metres} m`}`
      : `${n}${f.network && !String(f.name || '').endsWith(`(${f.network})`) ? ` (${esc(f.network)})` : ''}${f.official ? ', official station' : ''}${f.from_index ? ', its numbers are an index converted back' : ''}`; };
  const could = (j.could || []).map(c => `<p class="fine">You could name: ${esc(c.a.name || c.a.id)} and ${esc(c.b.name || c.b.id)} (${c.metres} m, ${esc(word(c.metric))}). `
    + `Write the one to correct first: <code>${esc(c.a.id)} ${esc(c.b.id)} ${esc(c.metric)} &lt;the day they were put together&gt;</code></p>`).join('');
  const tr = r => r.sensor ? `<tr><td>${esc(r.sensor.name || r.sensor.id)} <span class="fine">${esc(word(r.metric))}</span></td>`
      + `<td class="n">${r.measured == null ? '—' : `${fmt(r.measured, 1)} ${u(r)}${at(r)}`}</td><td class="n">${r.shown ? `${fmt(r.corrected, 1)} ${u(r)}` : '—'}</td><td>${against(r)}</td>`
      + `<td class="n">${r.checked ? `off by ${fmt(r.checked.measured, 1)} → ${fmt(r.checked.corrected, 1)}` : '—'}</td><td>${esc(cwhy(r))}</td></tr>`
    : `<tr><td colspan="6">${esc(cwhy(r))}</td></tr>`;
  return `<p class="fine">A straight line fitted on the last 14 days against the sensor named. Shown only while it has been closer on days the line never saw. `
    + `The measured number is what the node stores, alerts on and shares.</p>`
    + (rows.length ? `<div class="tscroll"><table class="tbl ctab"><thead><tr><th>sensor</th><th class="n">measured</th><th class="n">corrected</th><th>against</th>`
      + `<th class="n">last checked days</th><th>state</th></tr></thead><tbody>${rows.map(tr).join('')}</tbody></table></div>` : '') + could;
}
function calibrateMarks(j, metric, now = Date.now()) {
  const out = {};
  for (const r of (j || {}).rows || []) if (r.shown && r.metric === metric && r.sensor && !(r.hour && now - Date.parse(r.hour) > 3 * 3600e3))
    out[r.sensor.id] = `<a href="#data/calibrate">corrected ${fmt(r.corrected, 1)} against ${esc((r.reference || {}).name || (r.reference || {}).id)}</a>`;
  return out;
}
let CALP = null; // the answer, fetched once per page load; a locked screen is asked again once it is unlocked
const calibrateGet = () => CALP || (CALP = doorsFetch('/calibrate').then(async r => ({ status: r.status, j: r.ok ? await r.json().catch(() => null) : null }))
  .catch(() => ({ status: 0, j: null })).then(a => { if (a.status === 403) CALP = null; return a; }));
function calibrateOnRows() {
  if (!DOORS_TOKEN()) return Promise.resolve();
  const m = METRIC;
  return calibrateGet().then(({ j }) => { if (m !== METRIC) return; const mk = calibrateMarks(j, m);
    // two draws before the answer: a row that already has its mark keeps the one
    for (const el of document.querySelectorAll('#sensors .srow[data-sid]')) if (mk[el.dataset.sid] && !el.querySelector('.cmark'))
      el.querySelector('.t').insertAdjacentHTML('beforeend', `<small class="cmark">${mk[el.dataset.sid]}</small>`); });
}
async function calibrateBlock() {
  const el = $('#calibrate'), head = `<h2>Corrections</h2>`, { status, j } = await calibrateGet();
  if (status === 403) { el.innerHTML = head + `<p class="lede">What is corrected against what is the household’s, so only a screen holding a node token reads it: unlock this one in ${UNLOCK_AT}.</p>`; return; }
  if (status === 404) { el.innerHTML = head + `<p class="fine">The Calibrate pack is off on this node. Switch it on in Set up, under Packs.</p>`; return; }
  el.innerHTML = head + calibrateRows(j || { state: 'failed' }, (D.health || {}).docs, mWord);
}
/* PREDICT — this node's own readings, forecast by a general model that runs here (GET /predict, the predict pack). A day
   is drawn only when the model beat "yesterday repeated" on enough days; otherwise it says why. predictRows is pure: it
   takes the parsed answer, or { state: 'off' } for a 404 and { state: 'failed' } for no answer, and gives the HTML. */
function pwhy(d, why) {
  const r = (why || {}).reason;
  if (r === 'sparse') return 'too many hours missing';
  if (r === 'waiting') return 'not made yet today';
  if (d.days == null) return r === 'young' ? `too young: ${why.have} of ${why.need} days` : '';
  return d.days >= 7 ? 'yesterday is closer' : `too young: ${d.days} of 7 days`;
}
function predictRows(j, docs, word = x => x) {
  const state = (j || {}).state, say = t => `<p class="fine">${t}</p>`;
  if (state === 'off') return say(`This node does not forecast its own readings. <code>planetai models pull amazon/chronos-2</code> turns it on (456 MB). <a href="${esc((docs || 'https://planetai.fab.city/docs/') + 'predict/')}" target="_blank" rel="noopener">How it works</a>.`);
  if (state === 'no-answer') return say('The models container is not answering.');
  if (state === 'no-model') return say('No model is pulled.');
  if (state === 'young') return say('No series has 14 days yet.');
  if (state !== 'ok') return say('The forecast could not be read.');
  const m = j.model || {}, rows = j.rows || [], N = Math.max(0, ...rows.map(r => Math.max(r.today.days || 0, r.tomorrow.days || 0)));
  const day = (r, d) => d.shown ? `${fmt(d.low, 1)}–${fmt(d.high, 1)} ${said(r.unit || '')}` : `— <span class="fine">${esc(pwhy(d, r.why))}</span>`;
  const v = x => x == null ? '—' : fmt(x, 1);
  const off = (r, k) => r.today[k] == null && r.tomorrow[k] == null ? '—' : `${v(r.today[k])} · ${v(r.tomorrow[k])} ${said(r.unit || '')}`;
  return `<p class="fine">${esc(m.name)} · general model, not adapted here</p><div class="tscroll"><table class="tbl ptab"><thead><tr><th>series</th><th>today</th><th>tomorrow</th>`
    + `<th class="n">off by${N ? `, last ${N} days` : ''}</th><th class="n hide">yesterday repeated</th></tr></thead><tbody>`
    + rows.map(r => `<tr><td>${esc(r.sensor)} <span class="fine">${esc(word(r.metric))}${r.indoor ? ', inside' : ''}</span></td><td>${day(r, r.today)}</td><td>${day(r, r.tomorrow)}</td>`
      + `<td class="n">${off(r, 'model')}</td><td class="n hide">${off(r, 'naive')}</td></tr>`).join('') + `</tbody></table></div>`;
}
async function predictBlock() {
  const el = $('#predict'), head = `<h2>Its own readings, forecast</h2>`;
  const r = await doorsFetch('/predict').catch(() => null);
  if (r && r.status === 403) { el.innerHTML = head + `<p class="lede">What this node expects of its own sensors is the household’s, so only a screen holding a node token reads it: unlock this one in ${UNLOCK_AT}.</p>`; return; }
  const j = r && r.ok ? await r.json().catch(() => null) : null;
  el.innerHTML = head + predictRows(j || { state: r && r.status === 404 ? 'off' : 'failed' }, (D.health || {}).docs, mWord);
}
/* IMAGES — every image the household added (SPEC_eyes step 1), with its facts of arrival, and its words to edit: the
   kind, the note, and key: value lines (meta). The act token edits; the admin token deletes, file and row. */
const IKINDS = { phone: 'Phone', camera: 'Fixed camera', microscope: 'Microscope', drone: 'Drone', balloon: 'Balloon or kite' };
// What the image model found: its words, and each finding filed under a flows class, as rows a person can edit or
// delete. Saving the rows confirms them: they are the household's from then on, with its name.
// ponytail: EYES_CLASSES in main.py, copied; the node files anything else under other
const FCLASSES = ['plant', 'animal', 'habitat', 'food', 'water', 'compost', 'waste_residual', 'plastic_waste', 'packaging', 'wood', 'metal',
  'textile', 'electronics', 'filament', 'fuel', 'electricity', 'part', 'filter', 'furniture', 'tool', 'appliance', 'garment', 'micromobility', 'vehicle', 'goods', 'other'];
const LIVING = ['plant', 'animal'];
// GRIIS's word for this country (SPEC_species step 2); a species not on the list says nothing, never "native"
const INTRO = t => (t.introduced ? ` · <b>${esc(t.introduced)}</b> in ${esc(t.where)}` : t.where ? ` · ${esc(t.where)}` : '')
  // what others recorded in the seven cells, from GBIF's open records (SPEC_species step 3)
  // the seven cells are the node's, not the picture's: a walk's image far away is counted against home
  + (t.others > 0 ? ` · recorded by others in this node's seven cells ${+t.others}×` : t.others === 0 ? " · no open record of it in this node's seven cells yet" : '');
const frow = f => `<div class="frow"><input data-g="name" aria-label="what" value="${esc(f.name || '')}">`
  + `<select data-g="class" aria-label="class">${FCLASSES.map(c => `<option${c === f.class ? ' selected' : ''}>${c}</option>`).join('')}</select><input data-g="count" aria-label="how many" type="number" min="0" value="${f.count ?? ''}">`
  + `<label title="a problem for the place"><input data-g="issue" type="checkbox"${f.issue ? ' checked' : ''}>issue</label><button data-g="x" aria-label="delete this finding">×</button>`
  // a living thing's scientific name, and what GBIF matched it to (SPEC_species step 1); a changed name is asked again on save
  + `<input data-g="sci" aria-label="scientific name" placeholder="scientific name" value="${esc(f.scientific || '')}"${LIVING.includes(f.class) ? '' : ' hidden'}>`
  + (f.taxon ? `<span class="fine mono"><a href="https://www.gbif.org/species/${+f.taxon.key}" target="_blank" rel="noopener">${esc(f.taxon.name)}</a> · ${esc(f.taxon.rank)} · GBIF${INTRO(f.taxon)}</span>` : '') + `</div>`;
// What a confirmed image found that a home keeps, each a button that adds it to Things with the photo linked
// (SPEC_inventory step 3). Only on a screen holding the admin token, which TKEEP says: null until /things answered.
let TKEEP = null;
const asThings = (a, cid) => !(a && a.confirmed_by && TKEEP) ? '' : (a.findings || []).filter(f => TKEEP.classes.includes(f.class)).map(f => {
  const had = TKEEP.things.some(t => t.capture_id === +cid && t.name === f.name);
  return had ? `<span class="fine mono">${esc(f.name)}: in Things</span>`
    : `<button data-g="thing" data-class="${esc(f.class)}" data-name="${esc(f.name)}" data-count="${f.count || 1}">+ ${esc(f.name)} as a thing</button>`;
}).join(' ');
const seen = (a, cid) => !a ? `<p class="fine">Not described yet.</p>`
  : `<div class="seen"><p>${esc(a.summary || '')}</p><div class="frows">${(a.findings || []).map(frow).join('')}</div><button data-g="add">+ a finding</button>`
    + `<div class="acts">${asThings(a, cid)}</div>`
    + `<p class="fine mono">${a.confirmed_by ? `confirmed by ${esc(a.confirmed_by)}` : 'model, not confirmed'} · ${esc(a.model)}, on this machine · <a href="${esc(a.vocab || '')}" target="_blank" rel="noopener">flows 1.0</a></p></div>`;
const rowsOf = card => [...card.querySelectorAll('.frow')].map(r => ({ class: r.querySelector('[data-g=class]').value, name: r.querySelector('[data-g=name]').value.trim(),
  count: r.querySelector('[data-g=count]').value === '' ? null : +r.querySelector('[data-g=count]').value, issue: r.querySelector('[data-g=issue]').checked,
  scientific: r.querySelector('[data-g=sci]').value.trim() || null })).filter(f => f.name);
/* THINGS — what this home keeps (SPEC_inventory step 2): one card a thing, its use, its state, whether it is offered.
   The admin token only, and it never leaves: the node counts them per class as private readings. Idle = used yearly
   or never, which the household says once rather than logging every use. */
const TWORDS = { used: { weekly: 'Every week', monthly: 'Every month', yearly: 'A few times a year', never: 'Never' },
  condition: { works: 'Works', needs_repair: 'Needs a repair', broken: 'Broken' }, offer: { no: 'Not offered', lend: 'Would lend it', give: 'Would give it away' } };
const tsel = (k, v) => `<label>${{ used: 'How often it is used', condition: 'State', offer: 'Offer' }[k]}<select data-t="${k}">`
  + Object.entries(TWORDS[k]).map(([o, w]) => `<option value="${o}"${o === v ? ' selected' : ''}>${w}</option>`).join('') + `</select></label>`;
const tcard = (t, classes) => `<div class="icard" data-id="${t.id || ''}"><label>What<input data-t="name" maxlength="120" value="${esc(t.name || '')}"></label>`
  + `<label>Class<select data-t="class">${classes.map(c => `<option${c === t.class ? ' selected' : ''}>${c}</option>`).join('')}</select></label>`
  + `<label>How many<input data-t="count" type="number" min="1" value="${t.count || 1}"></label>`
  + tsel('used', t.used || 'monthly') + tsel('condition', t.condition || 'works') + tsel('offer', t.offer || 'no')
  + (t.capture_id ? `<p class="fine"><a href="#data/d-images">from image ${+t.capture_id}</a></p>` : '')
  + `<div class="acts"><button data-a="save">${t.id ? 'Save' : 'Add'}</button>${t.id ? '<button data-a="del">Delete</button>' : ''}</div><p class="fine" role="status"></p></div>`;
/* The usual day, hour by hour: Node's What it remembers draws it (doors-node.js usualBlock); it stays here beside the
   other drawings of readings. */
/* the usual day, hour by hour: bars from zero when the issue has a line, so the line sits at its true height; the
   line's label in a right margin and the hours under the bars, so neither is clipped or drawn over a bar. 410 units
   wide at 11, so a phone's 358 px draws the hours at about 10 px, not the 6 px a 480-wide drawing shrank them to. */
const dayStrip = (h, it) => { const v = Object.entries(h || {}).map(([k, x]) => [+k, x]); if (v.length < 12) return '';
  const line = it ? it.line : null, lo = line != null ? 0 : Math.min(...v.map(x => x[1])), hi = Math.max(...v.map(x => x[1]), line ?? -Infinity) || 1;
  const Y = x => 8 + 52 * (1 - (x - lo) / ((hi - lo) || 1)), W = 15;
  return `<svg viewBox="0 0 410 80" style="width:min(410px,100%);height:auto" role="img" aria-label="the usual day, hour by hour">`
    + v.map(([k, x]) => { const y = Y(x); return `<rect x="${k * W + 2}" y="${y.toFixed(1)}" width="${W - 4}" height="${(60 - y).toFixed(1)}" fill="currentColor" opacity=".55"><title>${String(k).padStart(2, '0')}:00 · ${x}</title></rect>`; }).join('')
    + (line != null ? `<line x1="0" x2="${24 * W}" y1="${Y(line).toFixed(1)}" y2="${Y(line).toFixed(1)}" class="linep"/><text x="${24 * W + 4}" y="${(Y(line) + 3.5).toFixed(1)}" font-size="11" class="lab">${lineLab(it)}</text>` : '')
    + [0, 6, 12, 18, 23].map(k => `<text x="${k * W + W / 2}" y="76" font-size="11" text-anchor="middle" fill="currentColor">${String(k).padStart(2, '0')}</text>`).join('') + `</svg>`; };
/* THINGS and IMAGES are tables (Tomas, 14 Oct: "it needs to build a table and not add all as cards"). A card, the
   whole form, opens only in a dialog: to add or edit a thing, to look at or edit one image, or to see all images. */
let CARDLG = null;
function cardDialog(title, html, onClose) {
  if (!CARDLG) { CARDLG = document.createElement('dialog'); CARDLG.className = 'imgdlg cardlg'; document.body.append(CARDLG); }
  CARDLG.innerHTML = `<div class="dhead"><h3>${esc(title)}</h3><button data-a="close">Close</button></div>${html}`;
  CARDLG.querySelector('[data-a=close]').onclick = () => CARDLG.close();
  CARDLG.onclose = () => { CARDLG.innerHTML = ''; if (onClose) onClose(); };
  CARDLG.showModal();
  return CARDLG;
}
const cell = v => esc(v == null || v === '' ? '—' : v);
async function thingsBlock() {
  const el = $('#d-things');
  if (CARDLG && CARDLG.open) return;   // a refresh must not wipe an edit in progress
  const r = await doorsFetch('/things').catch(() => null);
  if (r && r.status === 404) { el.innerHTML = `<h2>Things</h2><p class="fine">The things pack is off on this node. Switch it on in Set up, under Packs, to keep a list of what this home has here.</p>`; return; }
  const j = r && r.ok ? await r.json().catch(() => null) : null;
  if (!j) { el.innerHTML = `<h2>Things</h2><p class="fine">What this home keeps stays private to ${asHouse('this house')} and never leaves it. Unlock this screen with the admin key in ${UNLOCK_AT} to see it.</p>`; return; }
  const s = j.summary;
  el.innerHTML = `<h2>Things, ${s.things}</h2><p class="blurb">What this home keeps: ${s.idle} used a few times a year or never, ${s.repair} waiting for a repair, ${s.offered} offered. `
    + `Only what you offer leaves ${asHouse('the house')}: its class, name, state and count, at this node's cell, in <a class="mono" href="/offers">/offers</a>; whoever wants it writes to this node's Telegram bot, which passes the message to you.</p>`
    + `<div class="acts"><button data-a="add">Add a thing</button></div>`
    + (j.things.length ? `<table class="tbl things"><tr><th>what</th><th class="hide">class</th><th class="n">how many</th><th>used</th><th class="hide">state</th><th>offer</th><th></th></tr>`
      + j.things.map(t => `<tr><td>${cell(t.name)}${t.capture_id ? ` <a class="fine" href="#data/d-images">image</a>` : ''}</td><td class="hide">${cell(t.class)}</td><td class="n">${+t.count || 1}</td>`
        + `<td>${cell(TWORDS.used[t.used])}</td><td class="hide">${cell(TWORDS.condition[t.condition])}</td><td>${cell(TWORDS.offer[t.offer])}</td>`
        + `<td class="n"><button class="link" data-edit="${t.id}">Edit</button></td></tr>`).join('') + `</table>`
      : `<p class="fine">Nothing yet. Add what this home keeps and how often it is used: an idle drill is a drill a neighbour could borrow.</p>`);
  const open = t => {
    const dl = cardDialog(t.id ? `Edit ${t.name || 'this thing'}` : 'Add a thing', tcard(t, j.classes), thingsBlock);
    const card = dl.querySelector('.icard'), id = card.dataset.id, say = x => { card.querySelector('[role=status]').textContent = x; };
    const val = k => card.querySelector(`[data-t=${k}]`).value;
    card.querySelector('[data-a=save]').onclick = async () => {
      const body = { name: val('name'), class: val('class'), count: +val('count') || 1, used: val('used'), condition: val('condition'), offer: val('offer') };
      const r2 = await fetch(id ? `/things/${id}` : '/things', { method: id ? 'PATCH' : 'POST', headers: { ...DOORS_AUTH(), 'content-type': 'application/json' }, body: JSON.stringify(body) }).catch(() => null);
      if (r2 && r2.ok) { dl.close(); return; }
      say(`Not saved: ${r2 ? ((await r2.json().catch(() => ({}))).detail || r2.status) : 'the node did not answer'}`);
    };
    const del = card.querySelector('[data-a=del]');
    if (del) del.onclick = async () => {
      if (!confirm('Delete this thing from the node?')) return;
      const r2 = await fetch(`/things/${id}`, { method: 'DELETE', headers: DOORS_AUTH() }).catch(() => null);
      if (r2 && r2.ok) { dl.close(); return; }
      say(`Not deleted (${r2 ? r2.status : 'no answer'}).`);
    };
    card.querySelector('[data-t=name]').focus();
  };
  el.querySelector('[data-a=add]').onclick = () => open({});
  el.querySelectorAll('[data-edit]').forEach(b => b.onclick = () => open(j.things.find(t => String(t.id) === b.dataset.edit)));
}
const metaText = m => Object.entries(m || {}).map(([k, v]) => `${k}: ${v}`).join('\n');
const icardHTML = c => `<div class="icard" data-id="${c.id}"><img alt="${esc(c.note || IKINDS[c.kind] || 'an image')}">`
      + `<p class="fine mono">${esc(when(c.ts))}${c.actor ? ' · ' + esc(c.actor) : ''} · ${Math.round((c.bytes || 0) / 1024)} kB</p>`
      + `<p class="fine mono">${esc(c.cell)} · ${c.lat == null ? 'its cell only' : 'the exact point'} · ${c.outside ? 'outside the seven cells' : 'in the seven cells'}${c.at_home ? ' · at home' : ''}</p>`
      + `<label>What took it<select data-f="kind">${Object.entries(IKINDS).map(([k, t]) => `<option value="${k}"${k === c.kind ? ' selected' : ''}>${t}</option>`).join('')}</select></label>`
      + `<label>Note<input data-f="note" maxlength="500" value="${esc(c.note || '')}"></label>`
      + `<label>More, one per line as key: value<textarea data-f="meta" rows="2">${esc(metaText(c.meta))}</textarea></label>`
      + `<div data-seen>${seen(c.analysis, c.id)}</div>`
      + `<div class="acts"><button data-a="save">Save</button><button data-a="see">${c.analysis ? 'Describe again' : 'Describe'}</button>`
      + `<button data-a="ok"${c.analysis ? '' : ' hidden'}>${c.analysis && c.analysis.confirmed_by ? 'Save findings' : 'Confirm findings'}</button><button data-a="del">Delete</button></div><p class="fine" role="status"></p></div>`;
async function wireImageCard(card) {
    const id = card.dataset.id, say = t => { card.querySelector('[role=status]').textContent = t; };
    card.querySelector('[data-a=save]').onclick = async () => {
      const meta = Object.fromEntries(card.querySelector('[data-f=meta]').value.split('\n').map(l => l.split(/:(.*)/s)).filter(p => p[0].trim()).map(p => [p[0].trim(), (p[1] || '').trim()]));
      const r = await fetch(`/captures/${id}`, { method: 'PATCH', headers: { ...DOORS_AUTH(), 'content-type': 'application/json' },
        body: JSON.stringify({ kind: card.querySelector('[data-f=kind]').value, note: card.querySelector('[data-f=note]').value, meta }) }).catch(() => null);
      say(r && r.ok ? 'Saved.' : `Not saved: ${r ? ((await r.json().catch(() => ({}))).detail || r.status) : 'the node did not answer'}`);
      if (r && r.ok && window.placeImagesChanged) window.placeImagesChanged();
    };
    const see = card.querySelector('[data-a=see]'), ok = card.querySelector('[data-a=ok]');
    see.onclick = async () => {
      see.disabled = true; say('Asking the image model on this machine. A big picture can take a minute or two.');
      const r = await fetch(`/captures/${id}/describe`, { method: 'POST', headers: DOORS_AUTH() }).catch(() => null);
      const j = r ? await r.json().catch(() => ({})) : {};
      see.disabled = false;
      if (!(r && r.ok)) { say(`Not described: ${j.detail || (r ? r.status : 'the node did not answer')}`); return; }
      card.querySelector('[data-seen]').innerHTML = seen(j.analysis, id); see.textContent = 'Describe again'; ok.hidden = false; ok.textContent = 'Confirm findings'; say('');
      if (window.placeImagesChanged) window.placeImagesChanged();
    };
    ok.onclick = async () => {
      let actor = ''; try { actor = localStorage.getItem('planetai_actor') || ''; } catch (e) { /* no storage here */ }
      const r = await fetch(`/captures/${id}`, { method: 'PATCH', headers: { ...DOORS_AUTH(), 'content-type': 'application/json' },
        body: JSON.stringify({ findings: rowsOf(card), actor }) }).catch(() => null);
      const j = r ? await r.json().catch(() => ({})) : {};
      if (!(r && r.ok)) { say(`Not confirmed: ${j.detail || (r ? r.status : 'the node did not answer')}`); return; }
      card.querySelector('[data-seen]').innerHTML = seen(j.capture.analysis, id); ok.textContent = 'Save findings'; say('Saved: these findings are the household\'s now.');
      if (window.placeImagesChanged) window.placeImagesChanged();
    };
    card.querySelector('[data-seen]').addEventListener('change', e => {   // a row turned living gets its scientific name box
      if (e.target.dataset && e.target.dataset.g === 'class') e.target.closest('.frow').querySelector('[data-g=sci]').hidden = !LIVING.includes(e.target.value);
    });
    card.querySelector('[data-seen]').addEventListener('click', e => {   // delete a row, or add a blank one, before saving
      const g = e.target.dataset && e.target.dataset.g;
      if (g === 'x') e.target.closest('.frow').remove();
      if (g === 'thing') {   // a confirmed finding becomes a thing, its photo linked
        const b = e.target;
        b.disabled = true;
        fetch('/things', { method: 'POST', headers: { ...DOORS_AUTH(), 'content-type': 'application/json' },
          body: JSON.stringify({ class: b.dataset.class, name: b.dataset.name, count: +b.dataset.count || 1, capture_id: +id }) })
          .then(async r => { if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.status);
            const j = await r.json(); TKEEP.things.push(j.thing); b.outerHTML = `<span class="fine mono">${esc(b.dataset.name)}: in Things</span>`; thingsBlock(); })
          .catch(err => { b.disabled = false; say(`Not added: ${err.message}`); });
      }
      if (g === 'add') { card.querySelector('.frows').insertAdjacentHTML('beforeend', frow({ class: 'other', name: '' })); card.querySelector('.frow:last-child [data-g=name]').focus(); }
    });
    card.querySelector('[data-a=del]').onclick = async () => {
      if (!confirm('Delete this image from the node? The file goes with it, and it cannot be undone.')) return;
      const r = await fetch(`/captures/${id}`, { method: 'DELETE', headers: DOORS_AUTH() }).catch(() => null);
      if (r && r.ok) { card.remove(); if (window.placeImagesChanged) window.placeImagesChanged(); return; }
      say(r && r.status === 401 ? 'Only a screen holding the admin token deletes an image.' : `Not deleted (${r ? r.status : 'no answer'}).`);
    };
    const b = await doorsFetch(`/captures/${id}/file?w=1024`).then(r => (r.ok ? r.blob() : null)).catch(() => null);
    const im = card.querySelector('img'); if (b) { im.src = URL.createObjectURL(b); im.onload = () => URL.revokeObjectURL(im.src); }
}
const imgStatus = a => !a ? 'not described' : a.confirmed_by ? `confirmed by ${a.confirmed_by}` : 'the model’s, not confirmed';
async function imagesBlock() {
  const el = $('#d-images');
  if (CARDLG && CARDLG.open) return;   // a refresh must not wipe an edit in progress
  const rr = await doorsFetch('/captures?limit=500').catch(() => null);
  if (rr && rr.status === 404) { el.innerHTML = `<h2>Images</h2><p class="fine">The eyes pack is off on this node. Switch it on in Set up, under Packs, to keep pictures of this place here.</p>`; return; }
  const rows = rr && rr.ok ? await rr.json().catch(() => null) : null;
  TKEEP = await doorsFetch('/things').then(r => (r.ok ? r.json() : null)).catch(() => null);
  if (!rows) { el.innerHTML = `<h2>Images</h2><p class="fine">Images stay private to ${asHouse('this house')}: the picture and where it was taken. Unlock this screen in ${UNLOCK_AT} to see them.</p>`; return; }
  // what a person here has confirmed, per species (SPEC_species §4): the model's guesses are not in it
  const sp = await doorsFetch('/species').then(r => (r.ok ? r.json() : null)).catch(() => null);
  const spTable = sp && sp.species.length ? `<h3>Species confirmed, ${sp.species.length}</h3><table class="tbl species"><tr><th>species</th><th class="hide">rank</th><th class="n">seen</th><th>around here</th></tr>`
    + sp.species.map(x => `<tr><td>${x.key ? `<a href="https://www.gbif.org/species/${+x.key}" target="_blank" rel="noopener">${esc(x.name)}</a>` : esc(x.name)}</td>`
      + `<td class="hide">${cell(x.rank)}</td><td class="n">${+x.count}</td><td class="fine">${INTRO(x).replace(/^ · /, '') || '—'}</td></tr>`).join('') + `</table>` : '';
  el.innerHTML = `<h2>Images, ${rows.length}</h2><p class="blurb">What the household added, newest first, each a square on Place. The image model on this machine describes each one; what it found is its own until somebody here confirms it. Open a row to look, edit or confirm.</p>`
    + (rows.length ? `<div class="acts"><button data-a="all">See all images</button></div>` : '')
    + (rows.length ? `<table class="tbl imgs"><tr><th></th><th>when</th><th class="hide">taken with</th><th>note</th><th class="hide">what it shows</th><th>findings</th></tr>`
      + rows.map(c => `<tr data-id="${c.id}"><td class="thumb"><img alt=""></td>`
        + `<td><button class="link" data-open="${c.id}">${esc(when(c.ts))}</button>${c.actor ? `<br><span class="fine">${esc(c.actor)}</span>` : ''}</td>`
        + `<td class="hide">${cell(IKINDS[c.kind] || c.kind)}</td><td>${cell(c.note)}</td>`
        + `<td class="hide">${cell(((c.analysis || {}).findings || []).map(f => f.name).filter(Boolean).slice(0, 6).join(', '))}</td>`
        + `<td class="fine">${esc(imgStatus(c.analysis))}</td></tr>`).join('') + `</table>`
      : `<p class="fine">No images yet. Add one from Place, or from a phone unlocked from ${UNLOCK_AT}.</p>`) + spTable;
  const show = list => {
    const dl = cardDialog(list.length === 1 ? (list[0].note || IKINDS[list[0].kind] || 'Image') : `All images, ${list.length}`,
      `<div class="icards${list.length === 1 ? ' one' : ''}">${list.map(icardHTML).join('')}</div>`, () => { imagesBlock(); thingsBlock(); });
    dl.querySelectorAll('.icard').forEach(wireImageCard);
  };
  el.querySelector('[data-a=all]')?.addEventListener('click', () => show(rows));
  el.querySelectorAll('[data-open]').forEach(b => b.onclick = () => show([rows.find(c => String(c.id) === b.dataset.open)]));
  // thumbnails, one at a time, 96 px a side from the node (?w=): a drone picture is 11 MB
  for (const tr of el.querySelectorAll('tr[data-id]')) {
    const bl = await doorsFetch(`/captures/${tr.dataset.id}/file?w=96`).then(r => (r.ok ? r.blob() : null)).catch(() => null);
    const im = tr.querySelector('img'); if (bl && im) { im.src = URL.createObjectURL(bl); im.onload = () => URL.revokeObjectURL(im.src); }
  }
}

/* HOURS OVER THE LINE, per day, per issue: the node's own counts (GET /issues/days per_day) */
function perdayBlock() {
  const pd = D.order.filter(ISSUES_DRAWN).map(k => [k, D.issues[k]]);
  $('#perday').innerHTML = `<h2>Hours over the line, per day</h2><table class="tbl perday"><tr><th>day</th>${pd.map(([, it]) => `<th class="n">${esc(it.name)}</th>`).join('')}</tr>`
    + D.dates.map(dt => `<tr><td class="mono">${dLabel(dt)}</td>${pd.map(([, it]) => { const p = (it.per_day || []).find(x => x.date === dt); return `<td class="n">${p ? `${p.over} <span class="x">/ ${p.read} of ${p.of} h</span>` : '—'}</td>`; }).join('')}</tr>`).join('') + `</table>`;
}

/* THE LEDGER. Who answered, in words: the node's audit names (gui, local-model/<rung>) are kept in the row's title.
   A run of the same answer to the same alert by the same person is one row, "decided ×10", from its first time to
   its last; a time is its day and its hour, on one line. The stage filter keeps one stage. Who answered, and the
   alert's words that name the room, are the household's (Tomas, 14 Oct): a screen without the token draws the
   stage and the time of every decision and nothing else (/issues gives it no names either). */
const RUNG = { telegram: 'via Telegram', local: 'on this machine', remote: 'on another machine', online: 'online' };
const actorWord = a => { const s = String(a || '').trim(), m = s.match(/^local-model\/(.+)$/);
  return !s ? 'not named' : s === 'gui' || s === 'doors' ? 'a screen of this node' : s === 'user' ? 'someone, not named'
    : m ? `its own model, ${RUNG[m[1]] || m[1]}` : s; };
const dwhen = iso => `${dLabel(dayOf(iso)).replace(',', '')} ${hhmm(iso)}`;
const dspan = (a, b) => dwhen(a) === dwhen(b) ? dwhen(a) : dayOf(a) === dayOf(b) ? `${dwhen(a)}–${hhmm(b)}` : `${dwhen(a)} – ${dwhen(b)}`;
/* consecutive rows (newest first) with the same key become one: [{ a: the newest row, n, first, last }] */
const runs = (A, key) => A.reduce((o, a) => { const r = o[o.length - 1];
  if (r && key(r.a) === key(a)) { r.n += 1; r.first = a.ts; } else o.push({ a, n: 1, first: a.ts, last: a.ts }); return o; }, []);
/* what a row answered: an alert's words, or for a drawing the node's own note for it ("drew Rain garden on Garden plan"),
   without the "(mark 12)" the node keys it by */
const ledgerWhat = a => a.stage === 'place' ? `${a.choice || ''} ${String(a.note || '').replace(/ \((map|mark) \d+\)$/, '')}`.trim() : plain(a.text) || a.rule || '';
let LSTAGE = '';
function ledgerBlock() {
  /* the drawings' rows (D.placeActions, their own route) join the answers here and nowhere else */
  const tok = !!DOORS_TOKEN(), all = [...D.actions, ...(D.placeActions || [])].sort((a, b) => b.ts.localeCompare(a.ts));
  const stages = [...new Set(all.map(a => a.stage))];
  if (LSTAGE && !stages.includes(LSTAGE)) LSTAGE = '';
  const A = all.filter(a => !LSTAGE || a.stage === LSTAGE);
  const R = runs(A, a => [a.stage, a.alert_id, tok ? a.actor : '', tok ? ledgerWhat(a) : ''].join('|'));
  const stage = r => `${esc(r.a.stage)}${r.n > 1 ? ` <b class="x2">×${r.n}</b>` : ''}`;
  const filt = `<div class="lfilt" role="group" aria-label="Show one stage">${['', ...stages].map(x => `<button type="button" data-st="${esc(x)}" aria-pressed="${x === LSTAGE}">${x ? esc(x) : 'every stage'}${x ? ` <span>${all.filter(a => a.stage === x).length}</span>` : ''}</button>`).join('')}</div>`;
  $('#ledger').innerHTML = `<h2>Every decision, ${all.length}</h2>${filt}`
    + (tok ? `<table class="tbl ledger"><tr><th>when</th><th>stage</th><th class="hide">who</th><th>what it answered</th></tr>`
      + R.map(r => `<tr><td class="mono tw">${dspan(r.first, r.last)}</td><td class="ts">${stage(r)}</td><td class="hide" title="${esc(r.a.actor || '')}">${esc(actorWord(r.a.actor))}</td><td>${esc(ledgerWhat(r.a))}</td></tr>`).join('') + `</table>`
      : `<table class="tbl ledger"><tr><th>when</th><th>stage</th></tr>` + R.map(r => `<tr><td class="mono tw">${dspan(r.first, r.last)}</td><td class="ts">${stage(r)}</td></tr>`).join('') + `</table>`
        + `<p class="fine">Who answered, and what each alert said, stay private to ${asHouse('this house')}. Unlock this screen in ${UNLOCK_AT} to see them.</p>`);
  document.querySelectorAll('#ledger [data-st]').forEach(b => b.onclick = () => { LSTAGE = b.dataset.st; ledgerBlock(); });
}
