'use strict';
/* DATA — every raw reading this node holds, drawn. One metric at a time; every sensor that reads it is one ruled row
   (Zendesk status rows, Square devices), all on one scale capped at the 98th percentile so one spike cannot flatten
   the rest; a reading above the cap is printed. Then the issues over seven days, the models, the Index cells, the ledger. */
let METRIC = 'pm25';
/* Names and units are the node's own words (GET /issues → metrics); a metric the node has no word for keeps its key. */
const MNAME0 = { pm25: 'PM2.5', pm10: 'PM10', pm1: 'PM1', temp: 'temperature', humidity: 'humidity', pressure: 'pressure', gas_resistance: 'gas resistance',
  bme_iaq: 'indoor air index', noise: 'noise', light: 'light', aqi: 'AQI (US EPA)', pm25_raw: 'PM2.5 uncorrected', wind_speed: 'wind', precipitation: 'rain' };
const MNAME = new Proxy({}, { get: (_, m) => labelOf(m), has: (_, m) => m in MNAME0 });

/* THE INDEX (R45, 7 Oct 2026; frontend-design within the node's layer and Set up's reference lock). Every kind of
   reading this house holds, as a table of specimens by family: each tile its short symbol in the mono, the node's
   own name, the unit, how many sources read it, the median of their 15-minute means now (GET /stats, open), and,
   with the token, the 24-hour trace of the hourly medians (GET /aggregates). Press one to draw every source.
   The sections run down one page with Set up's list beside them; the list follows the scroll. */
const FAMILY = [
  ['Air', ['pm25', 'pm10', 'pm1', 'pm25_raw', 'aqi', 'bme_iaq', 'iaq', 'gas_resistance', 'o3', 'no2', 'co', 'dust', 'aod', 'pm25_model', 'pm10_model']],
  ['Weather', ['temp', 'humidity', 'pressure', 'wind_speed', 'wind_direction', 'precipitation', 'uv_index', 'temp_model', 'humidity_model', 'pressure_model']],
  ['Sound and light', ['noise', 'light']],
  ['Sea', ['sea_surface_temp', 'wave_height_m', 'wave_period_s', 'wave_direction', 'swell_height_m', 'swell_period_s']],
  ['Radio', ['lora_util_pct', 'lora_channel_pct']]];
/* a word for a key the node has no label for; the node's own label (GET /issues → metrics) always wins */
const WORD = { pm25_raw: 'PM2.5, uncorrected', bme_iaq: 'indoor air index', iaq: 'indoor air index', gas_resistance: 'gas resistance', o3: 'ozone',
  no2: 'nitrogen dioxide', co: 'carbon monoxide', dust: 'dust', aod: 'aerosol optical depth', pm25_model: 'PM2.5, modelled', pm10_model: 'PM10, modelled',
  temp_model: 'temperature, modelled', humidity_model: 'humidity, modelled', pressure_model: 'pressure, modelled', uv_index: 'UV index',
  sea_surface_temp: 'sea surface', wave_height_m: 'wave height', wave_period_s: 'wave period', wave_direction: 'wave direction',
  swell_height_m: 'swell height', swell_period_s: 'swell period', lora_util_pct: 'LoRa airtime', lora_channel_pct: 'LoRa channel use' };
const mWord = m => (D.metrics[m] || {}).label || WORD[m] || labelOf(m);
const SYM = { pm25: 'PM2.5', pm10: 'PM10', pm1: 'PM1', pm25_raw: 'PM2.5ʳ', aqi: 'AQI', bme_iaq: 'IAQ', iaq: 'IAQ', gas_resistance: 'Ω', o3: 'O₃', no2: 'NO₂', co: 'CO',
  dust: 'Dst', aod: 'AOD', pm25_model: 'PM2.5ᵐ', pm10_model: 'PM10ᵐ', temp: 'T', humidity: 'RH', pressure: 'P', wind_speed: 'W', wind_direction: 'Dir',
  precipitation: 'R', uv_index: 'UV', temp_model: 'Tᵐ', humidity_model: 'RHᵐ', pressure_model: 'Pᵐ', noise: 'dB', light: 'lx', sea_surface_temp: 'SST',
  wave_height_m: 'Hs', wave_period_s: 'Tp', wave_direction: 'Dw', swell_height_m: 'Sw', swell_period_s: 'Ts', lora_util_pct: 'LoRa', lora_channel_pct: 'Ch' };
const DSECTIONS = [['d-readings', 'Readings'], ['issues7', 'Issues, 7 days'], ['models', 'Models and satellite'], ['cells', 'Index cells'],
  ['perday', 'Hours over the line'], ['d-images', 'Images'], ['d-things', 'Things'], ['d-learned', 'What worked'], ['d-usual', 'What is usual'], ['d-diary', 'Diary'], ['ledger', 'Decisions'], ['api', 'API']];

/* #data/<sensor-id> (from a dot on Place) opens on a metric that station reads and scrolls to its row, once per link;
   #data/models opens at the models, #data/api at the API. */
let FOCUSED = '', DSPY = null, TILED = false;
VIEWS.data = function () {
  const S2 = D.raw ? D.raw.series : {}, FOCUS = decodeURIComponent(location.hash.split('/')[1] || '');
  if (FOCUS && FOCUS !== FOCUSED && S2[FOCUS] && !S2[FOCUS][METRIC]) {
    const has = Object.keys(S2[FOCUS]); METRIC = has.includes('pm25') ? 'pm25' : (FAMILY.flatMap(f => f[1]).find(m => has.includes(m)) || has[0] || METRIC);
  }
  const total = Object.values(S2).reduce((a, m) => a + Object.values(m).reduce((b, arr) => b + arr.filter(Boolean).length, 0), 0);
  $('#datahead').innerHTML = `<div class="k">Data · everything this node holds, as it reads it</div><h1>Every reading, drawn.</h1>
    <p class="lede">${D.raw ? `${total.toLocaleString('en')} hourly values from ${Object.keys(S2).length} sources over the last 24 hours` : 'The hourly values with the token'}, seven days of every issue at every distance, ${D.observations.length} model and satellite values, ${D.index_cells.length} Index cells and ${D.actions.length} decisions. Today’s open export, CC BY 4.0: <a class="mono" href="/export?day=${dayOf(D.buckets[D.now])}">GET /export?day=${dayOf(D.buckets[D.now])}</a>.</p>`;
  dataNav(); metricTiles();
  sensorsBlock(); issuesBlock(); modelsBlock(); cellsBlock(); ledgerBlock(); apiBlock(); imagesBlock(); thingsBlock(); learnedBlock();
  if (FOCUS && FOCUS !== FOCUSED) {
    FOCUSED = FOCUS;
    setTimeout(() => {                                          // after route() has scrolled to the top
      const el = document.querySelector(`.srow[data-sid="${CSS.escape(FOCUS)}"]`) || document.getElementById(FOCUS)
        || (['model', 'map'].includes((D.sens[FOCUS] || {}).kind) ? document.getElementById('models') : null);
      if (el) { el.scrollIntoView({ block: 'center' }); el.classList.add('focus'); }
    });
  }
};

/* the list beside the sections, Set up's own; it marks the section in view */
function dataNav() {
  $('#dnav').innerHTML = DSECTIONS.map(([id, t]) => `<a href="#data/${id}" data-s="${id}">${t}</a>`).join('');
  document.querySelectorAll('#dnav a').forEach(a => a.onclick = ev => { ev.preventDefault(); document.getElementById(a.dataset.s).scrollIntoView({ behavior: CLOCK.reduced() ? 'auto' : 'smooth', block: 'start' }); });
  if (DSPY) DSPY.disconnect();
  DSPY = new IntersectionObserver(es => { for (const e of es) if (e.isIntersecting) document.querySelectorAll('#dnav a').forEach(a => a.classList.toggle('on', a.dataset.s === e.target.id)); },
    { rootMargin: '-30% 0px -60% 0px' });
  DSECTIONS.forEach(([id]) => { const el = document.getElementById(id); el && DSPY.observe(el); });
}

function metricTiles() {
  const S2 = D.raw ? D.raw.series : {}, src = {}, now = {};
  for (const id in S2) for (const m in S2[id]) (src[m] ||= new Set()).add(id);
  for (const id in D.stats15) for (const m in D.stats15[id]) { (src[m] ||= new Set()).add(id); const v = D.stats15[id][m][0]; if (v != null) (now[m] ||= []).push(v); }
  /* a kind only models read goes to its own family, so what the house measures leads */
  const modelOnly = m => [...src[m]].every(id => (D.sens[id] || {}).kind === 'model');
  const known = new Set(FAMILY.flatMap(f => f[1])), fams = FAMILY.map(([t, ms]) => [t, ms.filter(m => src[m] && !modelOnly(m))])
    .concat([['Models', FAMILY.flatMap(f => f[1]).filter(m => src[m] && modelOnly(m))],
             ['Other', Object.keys(src).filter(m => !known.has(m) && !m.startsWith('fc_')).sort()]]).filter(f => f[1].length);
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
  $('#metrics').innerHTML = fams.map(([t, ms]) => `<div class="fam"><div class="fh k">${t}<span><b>${ms.length}</b> kind${ms.length === 1 ? '' : 's'}</span></div><div class="tiles">${ms.map(m => {
    const n = src[m].size, md = now[m] && now[m].length ? d3.median(now[m]) : null, dp = Math.abs(md) >= 100 ? 0 : Math.abs(md) >= 10 ? 1 : 2;
    return `<button type="button" class="mt ${m === METRIC ? 'on' : ''}" data-m="${esc(m)}" aria-pressed="${m === METRIC}" style="--i:${k++}">`
      + `<span class="sym">${esc(SYM[m] || m.slice(0, 4))}</span><span class="mn said">${esc(mWord(m))}</span>${trace(m)}`
      + `<span class="mv">${md == null ? '<b>—</b>' : num(`metric.${m}.median`, fmt(md, dp), `median of ${now[m].length} sources’ 15-minute means`, `<b>${fmt(md, dp)}</b>`)} <span class="said">${esc(unitOf(m))}</span></span>`
      + `<span class="ms">${n} source${n === 1 ? '' : 's'}</span></button>`; }).join('')}</div></div>`).join('');
  if (!TILED) { $('#metrics').classList.add('enter'); TILED = true; } else $('#metrics').classList.remove('enter');
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
  const grp = (t, rs) => rs.length ? `<div class="gh k">${t} · ${rs.length}</div>` + rs.map(r => `<div class="srow" data-sid="${esc(r.id)}"><span class="t">${esc(plain(r.s.name || r.id))}<small>${esc(r.s.source || '')}${r.s.lat != null ? ` · ${fmt(r.d, 1)} km` : ''}${r.s.indoor ? ' · inside' : ''}</small></span>${spark(r.a)}<span class="c">${num(r.id + '.' + METRIC, fmt(r.last, (D.metrics[METRIC] || {}).dp ?? 1), line != null ? `the line ${line}` : `one scale, ${fmt(lo, 0)} to ${fmt(top, 0)}`)}</span></div>`).join('') : '';
  $('#sensors').innerHTML = `<div class="dh"><h2>${said(labelOf(METRIC))}, every source, last 24 hours</h2><span class="k">one scale, ${fmt(lo, 0)} to ${fmt(top, 0)} ${said(unitOf(METRIC))} · band = the hour’s low to high · line = its mean${line != null ? ' · red: over the line' : ''}</span></div>`
    + grp('This house', rows.filter(r => r.s.local)) + grp('Around it', rows.filter(r => !r.s.local && r.s.kind !== 'model')) + grp('Models', rows.filter(r => r.s.kind === 'model'))
    + `<div class="axis"><span></span><span class="mono k">${hhmm(B[0])} yesterday → ${hhmm(B[B.length - 1])} today</span><span></span></div>`;
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

function modelsBlock() {
  const by = d3.group(D.observations, o => o.sensor_id), nm = { 'ee-point': 'Earth Engine, within 1 km', 'marine-point': 'Open-Meteo marine', 'om-point': 'Open-Meteo weather', 'cams-point': 'CAMS air quality', 'earth-point': 'AlphaEarth' };
  $('#models').innerHTML = `<h2>Models and the satellite</h2>` + [...by].map(([id, os]) => `<div class="gh k">${esc(nm[id] || id)} · ${os.length}</div>`
    + `<table class="tbl"><tr><th>metric</th><th class="n">value</th><th class="hide">cadence</th><th class="hide">as of</th></tr>`
    + os.map(o => `<tr><td>${esc(o.metric.replace(/_/g, ' '))}</td><td class="n">${fmt(o.value, Math.abs(o.value) < 1 ? 3 : 1)}</td><td class="hide mono">${esc(o.cadence || '')}</td><td class="hide mono">${esc(when(o.ts))}</td></tr>`).join('') + `</table>`).join('');
}
function cellsBlock() {
  $('#cells').innerHTML = `<h2>Fab City Index cells</h2><table class="tbl"><tr><th>cell</th><th class="n">value</th><th class="hide">unit</th><th>word</th></tr>`
    + D.index_cells.map(c => `<tr><td>${esc(c.cell.replace('|', ' · '))}</td><td class="n">${fmt(c.value, 2)}</td><td class="hide">${esc(c.unit)}</td><td>${prov(c.state)}</td></tr>`).join('') + `</table>`;
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
/* WHAT WORKED HERE — the household's own evidence (SPEC_learn step 1): per alert, what the air or the heat inside did
   after someone acted, against the street and against the times nobody answered. The sentence is the node's, written
   from the numbers; under it, every case, so the proof is on the page. Admin token only: the cases carry the notes. */
// Who is in the house (SPEC_learn step 4): yes or no answers, kept here and nowhere else, that rank what the node
// learned and say why a learning matters here. They change no threshold.
const matters = x => (x.for_whom && x.for_whom.length ? ` <b>Matters here: ${esc(x.for_whom.join(', '))}.</b>` : '');
async function whoForm() {
  const h = await doorsFetch('/household').then(r => (r.ok ? r.json() : null)).catch(() => null);
  if (!h) return '';
  setTimeout(() => { const f = $('#d-learned [data-f=who]'); if (!f) return;
    f.onchange = async () => {
      const people = Object.fromEntries([...f.querySelectorAll('input')].map(i => [i.name, i.checked]));
      const r = await fetch('/household', { method: 'PUT', headers: { ...DOORS_AUTH(), 'content-type': 'application/json' }, body: JSON.stringify({ people }) }).catch(() => null);
      f.querySelector('[role=status]').textContent = r && r.ok ? 'Kept. The order below follows it from the next look.' : 'Not kept.';
    }; }, 0);
  return `<form class="household" data-f="who"><p class="fine">Who lives here? Yes or no, kept on this machine, never a name or an age. It decides which of these matter most here, and a heat or air alert that matters to someone you tick says so in its Telegram message ("you said there is a child under five"), so that line reaches Telegram. It changes no threshold.</p>`
    + Object.entries(h.choices).map(([k, w]) => `<label class="tick"><input type="checkbox" name="${esc(k)}"${h.people[k] ? ' checked' : ''}> ${esc(w)}</label>`).join(' ')
    + `<p class="fine" role="status"></p></form>`;
}
const LSTATUS = { holding: 'holding', weakening: 'weakening', too_early: 'too early to say', gone: 'no longer watched' };
async function learnedBlock() {
  const el = $('#d-learned');
  const r = await doorsFetch('/learned').catch(() => null);
  const j = r && r.ok ? await r.json().catch(() => null) : null;
  if (!j) { el.innerHTML = `<h2>What worked here</h2><p class="fine">What this house learned answers the admin token only, because its cases carry your own notes. Unlock this screen with it in ${UNLOCK_AT}.</p>`; $('#d-usual').innerHTML = ''; return; }
  usualBlock(j); diaryBlock();
  const rows = j.learnings.filter(x => x.kind === 'worked');
  const casesOf = x => { const c = (x.numbers.cases || {}).acted || [], u = x.numbers.unit || '';
    return !c.length ? '' : `<table class="tbl"><tr><th>acted</th><th class="n">before</th><th class="n">after</th><th class="n">street</th><th class="hide">note</th></tr>`
      + c.slice().reverse().map(k => `<tr><td class="mono">${esc(when(k.at))}</td><td class="n">${fmt(k.before, 1)}</td><td class="n">${fmt(k.after, 1)} ${esc(u)}</td>`
        + `<td class="n">${k.street == null ? '–' : (k.street > 0 ? '+' : '') + fmt(k.street, 1)}</td><td class="hide">${esc(k.note || '')}</td></tr>`).join('') + `</table>`; };
  el.innerHTML = `<h2>What worked here</h2><p class="blurb">For each alert, what the air or the heat inside did after someone here acted, beside what the street did and what happened the times nobody answered. Your own before and after, not an experiment: the night or the weather can do the same. Checked once a day${j.checked ? `, last ${esc(j.checked.slice(0, 16).replace('T', ' '))}` : ''}. It never leaves this house.</p>`
    + await whoForm()
    + (rows.length ? rows.map(x => `<div class="gh k">${esc(x.key)} · ${esc(LSTATUS[x.status] || x.status)}</div><p>${esc(x.statement)}${matters(x)}</p>${casesOf(x)}`).join('')
      : `<p class="fine">Nothing yet: the node checks once a day, and needs an alert someone acted on.</p>`);
}
/* WHAT IS USUAL HERE (SPEC_learn step 2): the shape of a day from this house's own sensors, the week against the three
   before, and the alerts that are mostly not answered, said as what would change them. The node changes nothing. */
/* it: the issue whose line a PM2.5 strip draws; its bars then stand on zero, so the line sits at its own height */
/* the usual day, hour by hour: bars from zero when the issue has a line, so the line sits at its true height; the
   line's label in a right margin and the hours under the bars, so neither is clipped or drawn over a bar */
const dayStrip = (h, it) => { const v = Object.entries(h || {}).map(([k, x]) => [+k, x]); if (v.length < 12) return '';
  const line = it ? it.line : null, lo = line != null ? 0 : Math.min(...v.map(x => x[1])), hi = Math.max(...v.map(x => x[1]), line ?? -Infinity) || 1;
  const Y = x => 8 + 52 * (1 - (x - lo) / ((hi - lo) || 1)), W = 18;
  return `<svg viewBox="0 0 480 80" style="width:min(480px,100%);height:auto" role="img" aria-label="the usual day, hour by hour">`
    + v.map(([k, x]) => { const y = Y(x); return `<rect x="${k * W + 2}" y="${y.toFixed(1)}" width="${W - 4}" height="${(60 - y).toFixed(1)}" fill="currentColor" opacity=".55"><title>${String(k).padStart(2, '0')}:00 · ${x}</title></rect>`; }).join('')
    + (line != null ? `<line x1="0" x2="${24 * W}" y1="${Y(line).toFixed(1)}" y2="${Y(line).toFixed(1)}" class="linep"/><text x="${24 * W + 4}" y="${(Y(line) + 3.5).toFixed(1)}" font-size="10" class="lab">${lineLab(it)}</text>` : '')
    + [0, 6, 12, 18, 23].map(k => `<text x="${k * W + W / 2}" y="76" font-size="10" text-anchor="middle" fill="currentColor">${String(k).padStart(2, '0')}</text>`).join('') + `</svg>`; };
function usualBlock(j) {
  const el = $('#d-usual'), usual = j.learnings.filter(x => x.kind === 'usual'), asks = j.learnings.filter(x => x.kind === 'asks');
  el.innerHTML = `<h2>What is usual here</h2><p class="blurb">From this house's own sensors, up to a year back: when in the day each is usually highest and lowest, weekdays against weekends, and this week against the three before. Outside is about the place; inside stays with the house.</p>`
    + (usual.length ? usual.map(x => `<div class="gh k">${esc(x.key.replace('-', ' '))} · ${esc(LSTATUS[x.status] || x.status)}${x.scope === 'place' ? ' · about the place' : ''}</div><p>${esc(x.statement)}${matters(x)}</p>${dayStrip((x.numbers || {}).by_hour, x.metric === 'pm25' && D.issues[x.issue])}`).join('')
      : `<p class="fine">Nothing yet: the node checks once a day.</p>`)
    + (asks.length ? `<h3>Alerts that may not fit</h3><p class="fine">The last 30 days of each act-level alert. Where most go unanswered, the node says what would change it; it changes nothing itself.</p>`
      + asks.map(x => `<div class="gh k">${esc(x.key)}</div><p>${esc(x.statement)}</p>`).join('') : '');
}
/* DIARY (SPEC_learn step 3): the node's digest of every day, week, month and year, in its own words and the
   household's, and a search over them and the learnings: the same search the pane and the bot ask. */
async function diaryBlock(words) {
  const el = $('#d-diary');
  const u = words ? `/learned/search?q=${encodeURIComponent(words)}` : '/learned/search?limit=20';
  const j = await doorsFetch(u).then(r => (r.ok ? r.json() : null)).catch(() => null);
  if (!j) { el.innerHTML = ''; return; }
  const rows = j.results || [];
  el.innerHTML = `<h2>Diary</h2><p class="blurb">The node writes one entry for every day, week, month and year, from its own numbers and your notes, and keeps them here. The ask pane and the bot search the same entries.</p>`
    + `<form class="acts" data-f="find"><input data-f="q" aria-label="search the diary" placeholder="smoke, purifier, October" value="${esc(words || '')}"><button>Search</button></form>`
    + (rows.length ? rows.map(x => `<div class="gh k">${esc(x.label)}${x.source === 'learning' ? ' · learning' : x.scale ? ' · ' + esc(x.scale) : ''}</div><p>${esc(x.text)}</p>`).join('')
      : `<p class="fine">${words ? 'Nothing mentions that.' : 'No entries yet: the node writes them once a day.'}</p>`);
  el.querySelector('[data-f=find]').onsubmit = e => { e.preventDefault(); diaryBlock(el.querySelector('[data-f=q]').value.trim()); };
}
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
  const j = r && r.ok ? await r.json().catch(() => null) : null;
  if (!j) { el.innerHTML = `<h2>Things</h2><p class="fine">What this home keeps answers the admin token only, and never leaves the house. Unlock this screen with it in ${UNLOCK_AT}.</p>`; return; }
  const s = j.summary;
  el.innerHTML = `<h2>Things, ${s.things}</h2><p class="blurb">What this home keeps: ${s.idle} used a few times a year or never, ${s.repair} waiting for a repair, ${s.offered} offered. `
    + `Only what you offer leaves the house: its class, name, state and count, at this node's cell, in <a class="mono" href="/offers">/offers</a>; whoever wants it writes to this node's Telegram bot, which passes the message to you.</p>`
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
  const rows = await doorsFetch('/captures?limit=500').then(r => (r.ok ? r.json() : null)).catch(() => null);
  TKEEP = await doorsFetch('/things').then(r => (r.ok ? r.json() : null)).catch(() => null);
  if (!rows) { el.innerHTML = `<h2>Images</h2><p class="fine">Images answer a screen holding a token only: the picture and where it was taken. Unlock this screen in ${UNLOCK_AT}.</p>`; return; }
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

function ledgerBlock() {
  const pd = D.order.filter(ISSUES_DRAWN).map(k => [k, D.issues[k]]);
  $('#perday').innerHTML = `<h2>Hours over the line, per day</h2><table class="tbl"><tr><th>day</th>${pd.map(([, it]) => `<th class="n">${esc(it.name)}</th>`).join('')}</tr>`
    + D.dates.map(dt => `<tr><td class="mono">${dLabel(dt)}</td>${pd.map(([, it]) => { const p = (it.per_day || []).find(x => x.date === dt); return `<td class="n">${p ? `${p.over} <span class="x">/ ${p.read} of ${p.of} h</span>` : '—'}</td>`; }).join('')}</tr>`).join('') + `</table>`;
  const A = [...D.actions].sort((a, b) => b.ts.localeCompare(a.ts));
  /* who answered, and the alert's words that name the room, are the household's (Tomas, 14 Oct): a screen without the
     token draws the stage and the time of every decision and nothing else (/issues gives it no names either) */
  if (!DOORS_TOKEN()) {
    $('#ledger').innerHTML = `<h2>Every decision, ${A.length}</h2><table class="tbl"><tr><th>when</th><th>stage</th></tr>`
      + A.map(a => `<tr><td class="mono">${wdhm(a.ts)}</td><td>${esc(a.stage)}</td></tr>`).join('') + `</table>`
      + `<p class="fine">Who answered and what each alert said answer a screen holding a token: ${UNLOCK_AT}.</p>`;
    return;
  }
  $('#ledger').innerHTML = `<h2>Every decision, ${A.length}</h2><table class="tbl"><tr><th>when</th><th>stage</th><th class="hide">who</th><th>what it answered</th></tr>`
    + A.map(a => `<tr><td class="mono">${wdhm(a.ts)}</td><td>${esc(a.stage)}</td><td class="hide">${esc(a.actor)}</td><td>${esc(plain(a.text) || a.rule || '')}</td></tr>`).join('') + `</table>`;
}
