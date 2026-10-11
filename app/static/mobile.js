'use strict';
/* mobile.js — the phone page (SPEC_mobile §5–§7): one scrollable page, Now / Place / Node. The data is D from
   doors-load.js (loadD with the phone's route subset); the page writes no household sentence — title, tagline,
   plain, the action and the button labels are the wire's, character for character.
   The seven one-line helpers are copied from doors-core.js, which boots the doors on load and cannot be imported. */
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const hhmm = iso => iso ? iso.slice(11, 16) : '';
const fmt = (v, dp) => v == null || Number.isNaN(+v) ? '—' : (+v).toFixed(dp);
const NODE = '/static/';
const said = x => `<span class="said">${esc(x)}</span>`;
const sign = (id, cls = '') => `<svg class="sg ${cls}" aria-hidden="true"><use href="${NODE}signs.svg#${id}"/></svg>`;
const PROV = ['live', 'partial', 'model', 'cached', 'example'];
const prov = w => PROV.includes(w) ? `<span class="pill">${sign('sign-prov-' + w)}${w}</span>` : `<span class="gap">${esc(w)}</span>`;
const num = (key, v, cmp, inner) => `<span data-num="${esc(key)}" data-cmp="${esc(cmp)}">${inner ?? esc(v)}</span>`;
const SAT = y => `/earth/frame.png?year=${y}&source=sentinel`;
const ANSWER_STAGE = { done: 'acted', not_now: 'acknowledged', doesnt_fit: 'dismissed' };

/* the four distances drawn as one scale, the line as a rule (Tomas, 11 Oct: "a bit more visual") — hand-drawn
   SVG, no library; the numerals stay in the grid below it */
function ladderSVG(it) {
  const ds = ['room', 'yard', 'ring', 'region'].map(k => ({ k, st: (it.stack || {})[k] })).filter(d => d.st && d.st.value != null);
  if (!ds.length) return '';
  const vals = ds.map(d => d.st.value).concat(it.line != null ? [it.line] : []);
  const max = Math.max(...vals) * 1.12 || 1, PAD = 7;
  const x = v => (PAD + (v / max) * (100 - 2 * PAD)).toFixed(2);
  const short = k => esc((D.labels[k] || k).replace(/^the /, ''));
  let s = `<svg class="ladder" viewBox="0 0 100 30" role="img" aria-label="The four distances against the line">`
    + `<line class="track" x1="${PAD}" y1="15" x2="${100 - PAD}" y2="15"/>`;
  if (it.line != null) s += `<line class="rule" x1="${x(it.line)}" y1="5" x2="${x(it.line)}" y2="24"/>`
    + `<text class="rl" x="${x(it.line)}" y="4" text-anchor="middle">line</text>`;
  for (const d of ds) {
    const hero = d.k === (it.hero_distance || 'region');
    s += `<circle class="dot${hero ? ' hero' : ''}" cx="${x(d.st.value)}" cy="15" r="${hero ? 2.6 : 1.7}"/>`
      + `<text x="${x(d.st.value)}" y="29" text-anchor="middle">${short(d.k)}</text>`;
  }
  return s + `</svg>`;
}

/* seven days of an issue as a sparkline, its line dashed — the doors' strips, pocket size. Missing hours
   keep their place in the week: the line breaks where the wire has no reading, never slides left. */
function sparkSVG(o) {
  const raw = ((o.series || {})[o.hero_distance || 'region']) || [];
  const ser = raw.filter(v => v != null);
  if (ser.length < 8) return '';
  const max = Math.max(...ser, o.line != null ? o.line : -Infinity), min = Math.min(...ser, 0), span = (max - min) || 1;
  const y = v => (25 - ((v - min) / span) * 22).toFixed(1);
  const n = raw.length - 1;
  let d = '', pen = false;
  raw.forEach((v, i) => {
    if (v == null) { pen = false; return; }
    d += `${pen ? 'L' : 'M'}${(i / n * 100).toFixed(1)},${y(v)}`;
    pen = true;
  });
  return `<svg class="spark" viewBox="0 0 100 28" preserveAspectRatio="none" aria-hidden="true">`
    + (o.line != null ? `<line class="rule" x1="0" y1="${y(o.line)}" x2="100" y2="${y(o.line)}"/>` : '')
    + `<path d="${d}"/></svg>`;
}

/* ---- the day as a dial (SPEC_mobile §11.1): the last 24 hours round a clock face, now at the top, the hours
   back anticlockwise, the line a dashed circle. A thumb drag reads an hour's pair from /issues/days hours —
   the engine's words, never the page's. Hand-drawn SVG, the theme's own blue (var(--cells)) for under the line. */
let dialK = null, dialSel = null;   /* the dial's own issue and hour; the lead is the default, now is null */
function dialIssues() {
  return D.order.filter(k => {
    const o = D.issues[k] || {};
    const ser = ((o.series || {})[o.hero_distance || 'room']) || [];
    return (o.hours || []).length >= 8 && ser.filter(v => v != null).length >= 8;
  }).sort((a, b) => (a === leadKey ? -1 : b === leadKey ? 1 : 0));
}
function dialHTML() {
  const ks = dialIssues();
  if (!ks.length) return '';
  if (!dialK || !ks.includes(dialK)) { dialK = ks[0]; dialSel = null; }
  const o = D.issues[dialK], n = 24;
  const ser = (((o.series || {})[o.hero_distance || 'room']) || []).slice(-n);
  const hrs = (o.hours || []).slice(-n), B = (D.buckets || []).slice(-n);
  const line = o.line, max = Math.max((line != null ? line : 0) * 1.25, ...ser.filter(v => v != null), 1e-9);
  const R0 = 56, R1 = 138, r = v => R0 + (R1 - R0) * Math.min(v, max) / max, a = i => -Math.PI / 2 - (n - 1 - i) * 2 * Math.PI / n;
  const P = (rad, ang) => `${(rad * Math.cos(ang)).toFixed(1)},${(rad * Math.sin(ang)).toFixed(1)}`;
  let g = '';
  ser.forEach((v, i) => {
    const a0 = a(i) - Math.PI / n + .02, a1 = a(i) + Math.PI / n - .02, rr = v == null ? R0 + 4 : r(v), over = v != null && line != null && v >= line;
    g += `<path class="dseg ${v == null ? 'none' : over ? 'over' : 'under'}" data-i="${i}" data-over="${over ? 1 : 0}" d="M${P(R0, a0)}L${P(rr, a0)}A${rr},${rr} 0 0 1 ${P(rr, a1)}L${P(R0, a1)}A${R0},${R0} 0 0 0 ${P(R0, a0)}Z"`
      + ` opacity="${i === (dialSel ?? n - 1) ? 1 : .55}"/>`;
    if (i % 6 === 5 || i === n - 1) {
      const t = B[i] ? hhmm(B[i]) : '', x = (R1 + 22) * Math.cos(a(i)), y = (R1 + 22) * Math.sin(a(i));
      g += `<text class="dtick" x="${x.toFixed(1)}" y="${(y + 3).toFixed(1)}" text-anchor="middle">${i === n - 1 ? 'now' : t}</text>`;
    }
  });
  if (line != null) g += `<circle class="dline" r="${r(line).toFixed(1)}"/>`
    + `<text class="dtick dval" x="4" y="${(-r(line) - 4).toFixed(1)}">line ${esc(fmt(line, o.dp))} ${esc(o.unit || '')}</text>`;
  const i = dialSel ?? n - 1, now = dialSel == null;
  const pair = now ? [o.title, o.tagline] : (hrs[i] || []);
  let s = `<div class="dialwrap">`;
  if (ks.length > 1) s += `<div class="dtabs" role="group" aria-label="The issue the dial reads">`
    + ks.map(k => `<button class="dtab${k === dialK ? ' on' : ''}" data-dial="${esc(k)}">${said(D.issues[k].name)}</button>`).join('') + `</div>`;
  s += `<svg class="dial" viewBox="-179 -179 358 358" role="img" aria-label="The last 24 hours of ${esc(o.name || dialK)}, now at the top">${g}</svg>`
    + `<div class="dmid"><div class="h">${now ? 'NOW' : (B[i] ? hhmm(B[i]) : '')}</div>`
    + `<div class="t2">${pair[0] ? said(pair[0]) : ''}</div><div class="g">${pair[1] ? esc(pair[1]) : ''}</div></div>`
    + `<p class="dlegend">Now sits at the top and the hours run back anticlockwise. Each wedge is an hour, its length the reading inside the house; the dashed circle is the line. Drag round the dial to read an hour.</p></div>`;
  return s;
}
/* the drag: pointer position → hour index, anticlockwise from the top. The svg is redrawn on every pick,
   so it is looked up fresh each time, and the pointer's client coordinates do the rest. */
function dialPick(e) {
  const svg = document.querySelector('svg.dial'); if (!svg) return;
  const b = svg.getBoundingClientRect();
  const x = e.clientX - b.left - b.width / 2, y = e.clientY - b.top - b.height / 2;
  let ang = Math.atan2(y, x) + Math.PI / 2; if (ang < 0) ang += 2 * Math.PI;
  const back = Math.round((2 * Math.PI - ang) / (2 * Math.PI / 24)) % 24;
  dialSel = back === 0 ? null : 23 - back;
  drawNow();
}

/* the phone's subset (SPEC_mobile §8): never the token-only three, never rho/cells */
const MOBILE_ROUTES = {
  issues: 'issues', days: 'issues/days?days=7', health: 'health', settings: 'settings',
  stats: 'stats', sensors: 'sensors', reach: 'reach', observations: 'observations', earth: 'earth',
};

let D = null, leadKey = null, refusedSentence = null, refusedHealth = null;

const hasToken = () => { try { return !!localStorage.getItem('planetai_act'); } catch (e) { return false; } };
const bootOff = () => { const a = $('#asking'); if (a) a.remove(); };

async function boot() {
  /* an explicit ?layout=mobile is remembered in this browser (§4.2); storage that throws remembers nothing */
  try {
    const q = new URLSearchParams(location.search);
    if (q.get('layout') === 'mobile') localStorage.setItem('planetai_layout', 'mobile');
  } catch (e) { /* no storage here */ }
  const foot = $('#fulldoors'); if (foot) foot.href = '/?layout=doors' + (location.hash || '');
  try {
    D = await loadD(MOBILE_ROUTES);
    leadKey = D.lead;
    drawAll();
  } catch (e) {
    /* /issues refused this screen (the default SHARE_LEVEL=off): the node's own sentence, then the unlock field */
    const [h, r] = await Promise.all([
      fetch('/health').then(x => x.ok ? x.json() : ({})).catch(() => ({})),
      fetch('/issues', { headers: DOORS_AUTH() }).then(async x => x.ok ? null : (await x.json().catch(() => ({}))).error || null).catch(() => null),
    ]);
    refusedHealth = h; refusedSentence = r || e.message;
    drawRefused();
  }
  bootOff();
}

function drawAll() {
  const h = D.health || {};
  document.documentElement.lang = h.locale || 'en';
  $('#who').innerHTML = `${esc(D.node.name || h.node || 'this node')}<small>${esc(D.node.place || '')}</small>`;
  $('#asof').textContent = `as of ${hhmm(D.as_of)}`;
  drawNow(); drawPlace(); drawNode(h);
}

/* ---- Now (§5.1) ---- */
function drawNow() {
  const it = D.issues[leadKey] || D.issues[D.lead] || {};
  const hd = it.hero_distance || 'region';
  const hero = (it.stack || {})[hd] || {};
  const cmp = it.line != null ? `against the line, ${fmt(it.line, it.dp)} ${it.unit}` : 'this issue has no line';
  let s = `<div aria-live="polite">`
    + `<p class="t">${it.pix ? `<span class="pix" aria-hidden="true">${sign(it.pix)}</span> ` : ''}${said(it.title || it.sentence || '')}</p>`
    + (it.tagline ? `<p class="tag">${esc(it.tagline)}</p>` : '') + `</div>`
    + `<div class="hero"><span class="v">${num(`${it.metric}.${hd}`, hero.value, cmp, `<b>${esc(fmt(hero.value, it.dp))}</b>`)}</span>`
    + `<span class="u">${esc(it.unit || '')}</span> ${prov(hero.provenance)}`
    + `<p class="cmp">${esc(cmp)}</p>`
    + (it.plain ? `<p class="plain">${said(it.plain)}</p>` : '') + `</div>`;
  s += ladderSVG(it);
  s += dialHTML();
  /* the four distances, 2 × 2, an absent one prints none in the gap style */
  s += `<div class="grid">` + ['room', 'yard', 'ring', 'region'].map(dk => {
    const st = (it.stack || {})[dk];
    return `<div class="cell"><div class="l">${esc(D.labels[dk] || dk)}</div>`
      + (st && st.value != null
        ? `<div class="v">${num(`${it.metric}.${dk}`, st.value, cmp, esc(fmt(st.value, it.dp)))} <span class="u">${esc(it.unit || '')}</span></div>${prov(st.provenance)}`
        : `<div class="v"><span class="gap">none</span></div>`)
      + `</div>`;
  }).join('') + `</div>`;
  s += decideHTML(it);
  /* the other issues, one row each */
  const others = D.order.filter(k => k !== leadKey && D.issues[k]);
  if (others.length) {
    s += `<div class="rows">` + others.map(k => {
      const o = D.issues[k], ohd = o.hero_distance || 'region', ov = (o.stack || {})[ohd] || {};
      return `<button class="rowb" data-lead="${esc(k)}"><span class="rh"><span class="n">${o.pix ? `<span class="pix" aria-hidden="true">${sign(o.pix)}</span> ` : ''}${said(o.name)}</span>`
        + `<span class="st${o.state === 'act' ? ' act' : ''}">${esc(o.state || '')}</span>`
        + (ov.value != null ? `<span class="v">${esc(fmt(ov.value, o.dp))} ${esc(o.unit || '')}</span>` : '')
        + `</span><span class="t2">${said(o.title || o.sentence || '')}</span>${sparkSVG(o)}</button>`;
    }).join('') + `</div>`;
  }
  $('#now-v').innerHTML = s;
}

/* ---- the Decide card (§6) ---- */
function decideHTML(it) {
  const e = (D.events || []).find(x => x.issue === leadKey && !x.cleared_at);
  if (!e) {
    return `<div class="decide"><p class="dq">Nothing is asked now.</p>`
      + `<p class="dm">${it.line != null ? `${esc(fmt(it.line, it.dp))} ${esc(it.unit || '')} · ${esc(it.line_source || '')}` : 'this issue has no line'}</p></div>`;
  }
  let s = `<div class="decide" id="decide"><div class="k">decide · ${said(it.name)} · ${esc(e.kind)} since ${hhmm(e.opened_at)}`
    + `${e.last_seen_at ? ` · watching, last seen ${hhmm(e.last_seen_at)}` : ''}`
    + `${e.peak != null ? ` · peak ${esc(fmt(e.peak, it.dp))} ${esc(it.unit || '')}` : ''}</div>`
    + `<p class="dq">${said(e.action || 'The node asked for nothing specific.')}</p>`;
  const B = D.buttons || {};
  if (e.asking && DOORS_TOKEN()) {
    s += `<div class="ans" role="group" aria-label="Answer">`
      + ['done', 'not_now', 'doesnt_fit'].map(b => `<button data-ev="${e.id}" data-stage="${ANSWER_STAGE[b]}">${said(B[b] || b)}</button>`).join('')
      + `</div>`;
  } else if (e.asking) {
    s += `<p class="dm">${e.message && e.message.sent
      ? 'The node sent this to Telegram. Answer there, or <a href="#unlock" data-unlock>unlock this phone</a> to answer here.'
      : '<a href="#unlock" data-unlock>Unlock this phone</a> to answer here.'}</p>`;
  }
  if (e.answer) {
    const a = e.answer, Bw = { acted: B.done, acknowledged: B.not_now, dismissed: B.doesnt_fit };
    s += `<p class="dm" role="status">answered: ${said(Bw[a.stage] || a.stage)}${a.actor ? ` by ${esc(a.actor)}` : ''} at ${hhmm(a.ts)}`
      + `${a.held_until ? ` · held until ${hhmm(a.held_until)}` : ''}${a.note ? ` · “${esc(a.note)}”` : ''}</p>`;
  }
  return s + `<p class="dm" id="answered" role="status"></p></div>`;
}

/* the name the answer carries (§6.1): one field in the card the first time, kept under planetai_actor */
function nameForm(evId, stage) {
  const d = $('#decide'); if (!d) return;
  d.insertAdjacentHTML('beforeend', `<form class="unlock" id="namef"><label for="nme">Your name</label>`
    + `<input id="nme" autocomplete="name" required><button class="sbtn primary" type="submit">Send the answer</button></form>`);
  $('#nme').focus();
  $('#namef').onsubmit = ev => {
    ev.preventDefault();
    const n = $('#nme').value.trim(); if (!n) return;
    try { localStorage.setItem('planetai_actor', n); } catch (e) { /* no storage here */ }
    answer(evId, stage);
  };
}

async function answer(evId, stage) {
  const out = $('#answered');
  let actor = ''; try { actor = localStorage.getItem('planetai_actor') || ''; } catch (e) { /* no storage here */ }
  if (!actor) { nameForm(evId, stage); return; }
  try {
    const r = await fetch('/actions', { method: 'POST', headers: { 'content-type': 'application/json', ...DOORS_AUTH() },
      body: JSON.stringify({ event_id: Number(evId), stage, actor, note: '' }) });
    if (!r.ok) {
      const detail = (await r.json().catch(() => ({}))).detail || `the node refused it (${r.status})`;
      if (out) out.textContent = r.status === 401 || r.status === 403
        ? `${detail} · Unlock this phone with the token for closing a loop.` : detail;
      return;
    }
    D = await loadD(MOBILE_ROUTES); drawAll();
  } catch (e) { if (out) out.textContent = `The node did not answer: ${e.message}`; }
}

/* ---- Place (§5.2): no heavy map library on a phone ---- */
function drawPlace() {
  const h = D.health || {}, cell = h.cell || {};
  const nos = `<p class="mut">The node does not share this with a screen at SHARE_LEVEL=off.</p>`;
  let s = '';
  if (cell.id) {
    const lad = (D.geometry.ladder || []).find(l => l.res === cell.res) || {};
    s += `<div class="facts"><div class="fact"><div class="l">The cell</div>`
      + `${esc(cell.id)} · res ${esc(String(cell.res))} · edge ${esc(fmt(cell.edge_m, 0))} m`
      + (lad.own_area_m2 ? ` · area ${fmt(lad.own_area_m2 / 1e6, 2)} km²` : '') + `</div>`;
  }
  if (D.observations) {
    const ee = Object.fromEntries((D.observations || []).filter(o => o.sensor_id === 'ee-point').map(o => [o.metric, o]));
    const fr = [['built_frac', 'built'], ['tree_frac', 'tree'], ['crop_frac', 'crop'], ['water_frac', 'water']]
      .map(([m, n]) => ({ n, v: ee[m] && ee[m].value })).filter(x => x.v != null);
    if (fr.length) {
      const total = fr.reduce((a, b) => a + b.v, 0), rest = Math.max(0, 1 - total);
      /* the ground as one segmented bar, the segments in ink weights (a remainder is what is none of them) */
      s += `<div class="fact"><div class="l">The ground within 1 km</div>`
        + `<div class="groundbar" role="img" aria-label="The ground within 1 km">`
        + fr.map((x, i) => `<span class="seg s${i}" style="width:${(x.v * 100).toFixed(1)}%"></span>`).join('')
        + (rest > 0.02 ? `<span class="seg rest" style="width:${(rest * 100).toFixed(1)}%"></span>` : '')
        + `</div><div class="groundlbl">`
        + fr.map((x, i) => `<span><i class="sw s${i}" aria-hidden="true"></i>${x.n} ${fmt(x.v * 100, 0)}%</span>`).join('')
        + ` ${prov('model')}</div></div>`;
    }
  } else s += nos;
  if (D.reach) {
    s += `<div class="fact"><div class="l">How far back the node reads</div>`
      + (D.reach || []).map(r => `<div>${esc(r.kind)} · ${(r.days || 0).toLocaleString('en')} days</div>`).join('') + `</div>`;
  } else s += nos;
  if (D.earth) {
    const years = (D.earth.sentinel || []);
    if (years.length) s += `<div class="fact"><div class="l">The ground from above, ${esc(String(years[years.length - 1]))}</div>`
      + `<img class="frame" loading="lazy" src="${SAT(years[years.length - 1])}" alt="The node's own Sentinel-2 frame for ${esc(String(years[years.length - 1]))}"></div>`;
  } else s += nos;
  if (s) s += `</div>`;
  s += `<p><a href="/?layout=doors#place">Open the map on the full dashboard</a></p>`;
  $('#place-v').innerHTML = s;
}

/* ---- Node (§5.3): /health only, so it always draws; the stations and the mesh from the routes the page already reads ---- */
function drawNode(h) {
  const mesh = h.mesh && h.mesh.root_topic ? h.mesh : null, radio = h.reticulum && h.reticulum.announce_s;
  let s = `<div class="facts">`
    + `<div class="fact"><div class="l">The node</div>${esc(h.node || 'this node')}${h.city ? `, in ${esc(h.city)}` : ''}</div>`
    + `<div class="fact"><div class="l">Running</div>planetai-node ${esc(h.version || '')} · schema ${esc(h.schema || '')}<br>`
    + `up ${fmt((h.uptime_s || 0) / 3600, 1)} h · ${h.polls || 0} polls · last poll ${hhmm(h.last_poll)} · ${(h.ingested || 0).toLocaleString('en')} readings since the restart</div>`;
  /* the stations: who is speaking — one dot per sensor, solid if it said something in the last hour */
  const sens = D ? (D.sensors || []) : [];
  if (sens.length) {
    const spoke = new Set();
    for (const [sid, mets] of Object.entries((D && D.stats15) || {}))
      for (const mm of Object.values(mets)) if (mm && mm[1] != null && mm[1] < 60) { spoke.add(sid); break; }
    const sources = new Set(sens.map(x => x.source)), custody = sens.filter(x => x.custody).length;
    s += `<div class="fact"><div class="l">The stations</div>`
      + `${sens.length} sensors · ${sources.size} sources · ${custody} in the house's custody`
      + `<div class="dotfield" role="img" aria-label="${spoke.size} of ${sens.length} sensors spoke in the last hour">`
      + sens.map(x => `<i class="dot${spoke.has(x.sensor_id) ? ' on' : ''}"></i>`).join('') + `</div>`
      + `<div class="mut">${spoke.size} spoke in the last hour</div></div>`;
  }
  if (mesh) {
    s += `<div class="fact"><div class="l">The mesh and the radio</div>`
      + `mesh on · ${esc(mesh.root_topic)}${mesh.gateway ? ` · gateway ${esc(mesh.gateway)}` : ''}`
      + `${mesh.packets != null ? ` · ${mesh.packets} packets${mesh.last ? `, last ${hhmm(mesh.last)}` : ''}` : ''}<br>`
      + `radio ${radio ? 'on' : 'off'}</div>`;
  } else s += `<div class="fact"><div class="l">The mesh and the radio</div>mesh off · radio ${radio ? 'on' : 'off'}</div>`;
  if (h.last_error) s += `<div class="fact"><div class="l">Lately</div><span class="mut">${esc(String(h.last_error).slice(0, 120))}${String(h.last_error).length > 120 ? '…' : ''}</span></div>`;
  if (h.release && h.release.newer) s += `<div class="fact">A newer release is out.</div>`;
  const share = D ? D.share : null;
  s += `<div class="fact"><div class="l">This phone</div>`
    + (share ? `SHARE_LEVEL=${esc(share)} · ` : '')
    + (hasToken() ? `unlocked · <a href="#lock" data-lock>Lock this phone</a>`
                  : `locked — this phone is not shown the readings · <a href="#unlock" data-unlock>Unlock this phone</a>`)
    + `</div></div>`;
  $('#node-v').innerHTML = s;
}

/* ---- the refused state (§5.4) and the unlock field (§6.3) ---- */
function drawRefused() {
  const h = refusedHealth || {};
  document.documentElement.lang = h.locale || 'en';
  $('#who').innerHTML = `${esc(h.node || 'this node')}<small>${esc(h.city || '')}</small>`;
  $('#asof').textContent = 'locked';
  const block = `<div class="refused"><p class="lede">${esc(refusedSentence || 'This node is not sharing its readings with this screen.')}</p>`
    + `<p class="mut">Unlock this phone with the token for closing a loop, or ask whoever set this node up to turn sharing on. <code>planetai ui</code> on the node prints the tokens.</p>`
    + unlockHTML() + `</div>`;
  $('#now-v').innerHTML = block;
  $('#place-v').innerHTML = '';
  drawNode(h);
}

function unlockHTML() {
  return `<form class="unlock" id="sunlock"><label for="sact">Token for closing a loop</label>`
    + `<input type="password" id="sact" autocomplete="off" placeholder="answers alerts, changes nothing">`
    + `<button type="submit" class="sbtn primary">Unlock this phone</button></form>`;
}

/* ---- the one click handler and the one submit handler ---- */
document.addEventListener('click', ev => {
  const t = ev.target;
  const ans = t.closest && t.closest('.decide .ans button[data-ev]');
  if (ans) { ev.preventDefault(); ans.disabled = true; answer(ans.dataset.ev, ans.dataset.stage); return; }
  const row = t.closest && t.closest('.rowb[data-lead]');
  if (row) { ev.preventDefault(); leadKey = row.dataset.lead; drawNow(); $('#now-v').scrollIntoView(); return; }
  const un = t.closest && t.closest('a[data-unlock]');
  if (un) {
    ev.preventDefault();
    if (!$('#sunlock')) ( $('#node-v') || $('main') ).insertAdjacentHTML('beforeend', unlockHTML());
    $('#sunlock').scrollIntoView(); $('#sact').focus(); return;
  }
  const dt = t.closest && t.closest('.dtab[data-dial]');
  if (dt) { ev.preventDefault(); dialK = dt.dataset.dial; dialSel = null; drawNow(); return; }
  const lock = t.closest && t.closest('a[data-lock]');
  if (lock) {
    ev.preventDefault();
    try { localStorage.removeItem('planetai_act'); localStorage.removeItem('planetai_admin'); } catch (e) { /* no storage here */ }
    location.reload();
  }
});

document.addEventListener('submit', ev => {
  if (ev.target.id !== 'sunlock') return;
  ev.preventDefault();
  const t = $('#sact').value.trim();
  if (t) { try { localStorage.setItem('planetai_act', t); } catch (e) { /* no storage here */ } location.reload(); }
});

/* the dial's drag (§11.1): pointer events, touch-action none on the dial only, so the page's scroll is untouched */
document.addEventListener('pointerdown', ev => {
  const svg = ev.target.closest && ev.target.closest('svg.dial');
  if (!svg) return;
  ev.preventDefault();
  dialPick(ev);
  const move = e2 => dialPick(e2), up = () => {
    document.removeEventListener('pointermove', move); document.removeEventListener('pointerup', up);
  };
  document.addEventListener('pointermove', move); document.addEventListener('pointerup', up);
});

/* freshness (§7): no timer — a visible-again page older than five minutes asks again */
document.addEventListener('visibilitychange', async () => {
  if (document.hidden || !D || !D.as_of) return;
  if (Date.now() - Date.parse(D.as_of) > 5 * 60 * 1000) { try { D = await loadD(MOBILE_ROUTES); drawAll(); } catch (e) { /* keep what is drawn */ } }
});

boot();
