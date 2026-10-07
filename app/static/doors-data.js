'use strict';
/* DATA — every raw reading this node holds, drawn. One metric at a time; every sensor that reads it is one ruled row
   (Zendesk status rows, Square devices), all on one scale capped at the 98th percentile so one spike cannot flatten
   the rest; a reading above the cap is printed. Then the issues over seven days, the models, the Index cells, the ledger. */
let METRIC = 'pm25';
/* Names and units are the node's own words (GET /issues → metrics); a metric the node has no word for keeps its key. */
const MNAME0 = { pm25: 'PM2.5', pm10: 'PM10', pm1: 'PM1', temp: 'temperature', humidity: 'humidity', pressure: 'pressure', gas_resistance: 'gas resistance',
  bme_iaq: 'indoor air index', noise: 'noise', light: 'light', aqi: 'AQI (US EPA)', pm25_raw: 'PM2.5 uncorrected', wind_speed: 'wind', precipitation: 'rain' };
const MNAME = new Proxy({}, { get: (_, m) => labelOf(m), has: (_, m) => m in MNAME0 });

/* #data/<sensor-id> (from a dot on Place) opens on a metric that station reads and scrolls to its row, once per link;
   #data/models opens at the models. */
let FOCUSED = '';
VIEWS.data = function () {
  const S2 = D.raw ? D.raw.series : {}, count = {}, FOCUS = decodeURIComponent(location.hash.split('/')[1] || '');
  if (FOCUS && FOCUS !== FOCUSED && S2[FOCUS] && !S2[FOCUS][METRIC]) {
    const has = Object.keys(S2[FOCUS]); METRIC = has.includes('pm25') ? 'pm25' : (Object.keys(MNAME0).find(m => has.includes(m)) || METRIC);
  }
  for (const id in S2) for (const m in S2[id]) count[m] = (count[m] || 0) + 1;
  const ms = Object.keys(MNAME0).filter(m => count[m]);
  const total = Object.values(S2).reduce((a, m) => a + Object.values(m).reduce((b, arr) => b + arr.filter(Boolean).length, 0), 0);
  $('#datahead').innerHTML = `<div class="k">Data · everything this node holds, as it reads it</div><h1>Every reading, drawn.</h1>
    <p class="lede">${D.raw ? `${total.toLocaleString('en')} hourly values from ${Object.keys(S2).length} sources over the last 24 hours` : 'The hourly values with the token'}, seven days of every issue at every distance, ${D.observations.length} model and satellite values, ${D.index_cells.length} Index cells and ${D.actions.length} decisions. Today’s open export, CC BY 4.0: <span class="mono">GET /export?day=${dayOf(D.buckets[D.now])}</span>.</p>`;
  $('#metrics').innerHTML = ms.map(m => `<button class="${m === METRIC ? 'on' : ''}" data-m="${m}">${MNAME[m]}<small>${count[m]}</small></button>`).join('');
  document.querySelectorAll('#metrics button').forEach(b => b.onclick = () => { METRIC = b.dataset.m; VIEWS.data(); });
  sensorsBlock(); issuesBlock(); modelsBlock(); cellsBlock(); ledgerBlock();
  if (FOCUS && FOCUS !== FOCUSED) {
    FOCUSED = FOCUS;
    setTimeout(() => {                                          // after route() has scrolled to the top
      const el = document.querySelector(`.srow[data-sid="${CSS.escape(FOCUS)}"]`) || document.getElementById(FOCUS)
        || (['model', 'map'].includes((D.sens[FOCUS] || {}).kind) ? document.getElementById('models') : null);
      if (el) { el.scrollIntoView({ block: 'center' }); el.classList.add('focus'); }
    });
  }
};

function sensorsBlock() {
  if (!D.raw) { $('#sensors').innerHTML = `<div class="dh"><h2>Every source, last 24 hours</h2></div><p class="fine">The hourly table, GET /aggregates, is the household’s own readings hour by hour, so the node gives it only to a screen holding the token. Unlock this screen under Node to draw it; the issues, the models, the Index and the ledger below are open.</p>`; return; }
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
      + (line != null ? `<line x1="0" x2="${W}" y1="${y(line)}" y2="${y(line)}" class="linep"/>` : '') + over + clip + `</svg>`;
  };
  const grp = (t, rs) => rs.length ? `<div class="gh k">${t} · ${rs.length}</div>` + rs.map(r => `<div class="srow" data-sid="${esc(r.id)}"><span class="t">${esc(plain(r.s.name || r.id))}<small>${esc(r.s.source || '')}${r.s.lat != null ? ` · ${fmt(r.d, 1)} km` : ''}${r.s.indoor ? ' · inside' : ''}</small></span>${spark(r.a)}<span class="c">${num(r.id + '.' + METRIC, fmt(r.last, METRIC === 'pressure' ? 0 : 1), line != null ? `the line ${line}` : `one scale, ${fmt(lo, 0)} to ${fmt(top, 0)}`)}</span></div>`).join('') : '';
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
      + (it.line != null ? `<line x1="30" x2="${W - 6}" y1="${y(it.line)}" y2="${y(it.line)}" class="linep"/>` : '') + `<path d="${ln}" class="lnp" style="stroke-width:${dk === 'room' ? 1.6 : 1.1}"/></svg></figure>`);
  }
  $('#issues7').innerHTML = `<h2>Every issue, every distance, seven days</h2><div class="sms">${out.join('')}</div><p class="fine">Hourly, from GET /issues/days. Each drawing keeps its own scale, capped at the 98th percentile; the red dash is the line. Day numbers mark local midnight.</p>`;
}

function modelsBlock() {
  const by = d3.group(D.observations, o => o.sensor_id), nm = { 'ee-point': 'Earth Engine, within 1 km', 'marine-point': 'Open-Meteo marine', 'om-point': 'Open-Meteo weather', 'cams-point': 'CAMS air quality', 'earth-point': 'AlphaEarth' };
  $('#models').innerHTML = `<h2>Models and the satellite</h2>` + [...by].map(([id, os]) => `<div class="gh k">${esc(nm[id] || id)} · ${os.length}</div>`
    + `<table class="tbl"><tr><th>metric</th><th class="n">value</th><th class="hide">cadence</th><th class="hide">as of</th></tr>`
    + os.map(o => `<tr><td>${esc(o.metric.replace(/_/g, ' '))}</td><td class="n">${fmt(o.value, Math.abs(o.value) < 1 ? 3 : 1)}</td><td class="hide mono">${esc(o.cadence || '')}</td><td class="hide mono">${esc((o.ts || '').slice(0, 16).replace('T', ' '))}</td></tr>`).join('') + `</table>`).join('');
}
function cellsBlock() {
  $('#cells').innerHTML = `<h2>Fab City Index cells</h2><table class="tbl"><tr><th>cell</th><th class="n">value</th><th class="hide">unit</th><th>word</th></tr>`
    + D.index_cells.map(c => `<tr><td>${esc(c.cell.replace('|', ' · '))}</td><td class="n">${fmt(c.value, 2)}</td><td class="hide">${esc(c.unit)}</td><td>${prov(c.state)}</td></tr>`).join('') + `</table>`;
}
function ledgerBlock() {
  const pd = D.order.filter(ISSUES_DRAWN).map(k => [k, D.issues[k]]);
  $('#perday').innerHTML = `<h2>Hours over the line, per day</h2><table class="tbl"><tr><th>day</th>${pd.map(([, it]) => `<th class="n">${esc(it.name)}</th>`).join('')}</tr>`
    + D.dates.map(dt => `<tr><td class="mono">${dLabel(dt)}</td>${pd.map(([, it]) => { const p = (it.per_day || []).find(x => x.date === dt); return `<td class="n">${p ? `${p.over} <span class="x">/ ${p.read} of ${p.of} h</span>` : '—'}</td>`; }).join('')}</tr>`).join('') + `</table>`;
  const A = [...D.actions].sort((a, b) => b.ts.localeCompare(a.ts));
  $('#ledger').innerHTML = `<h2>Every decision, ${A.length}</h2><table class="tbl"><tr><th>when</th><th>stage</th><th class="hide">who</th><th>what it answered</th></tr>`
    + A.map(a => `<tr><td class="mono">${wdhm(a.ts)}</td><td>${esc(a.stage)}</td><td class="hide">${esc(a.actor)}</td><td>${esc(plain(a.text) || a.rule || '')}</td></tr>`).join('') + `</table>`;
}
