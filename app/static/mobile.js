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
  /* the four distances, 2 × 2, an absent one prints none in the gap style */
  s += `<div class="grid">` + ['room', 'yard', 'ring', 'region'].map(dk => {
    const st = (it.stack || {})[dk];
    return `<div class="cell"><div class="l">${esc(D.labels[dk] || dk)}</div>`
      + (st && st.value != null
        ? `<div class="v">${num(`${it.metric}.${dk}`, st.value, cmp, esc(fmt(st.value, it.dp)))} <span class="u">${esc(it.unit || '')}</span></div>${prov(st.provenance)}`
        : `<div class="v"><span class="gap">none</span></div>`)
      + `</div>`;
  }).join('') + `</div>`;
  /* the walk out from the house (§11.2) loads a map, so it is its own page; it reads what this page reads */
  s += `<p class="walk"><a href="/?layout=walk#${esc(leadKey || D.lead || '')}">Walk out from the house →</a></p>`;
  s += decideHTML(it);
  /* the other issues, one row each */
  const others = D.order.filter(k => k !== leadKey && D.issues[k]);
  if (others.length) {
    s += `<div class="rows">` + others.map(k => {
      const o = D.issues[k], ohd = o.hero_distance || 'region', ov = (o.stack || {})[ohd] || {};
      return `<button class="rowb" data-lead="${esc(k)}"><span class="rh"><span class="n">${said(o.name)}</span>`
        + `<span class="st${o.state === 'act' ? ' act' : ''}">${esc(o.state || '')}</span>`
        + (ov.value != null ? `<span class="v">${esc(fmt(ov.value, o.dp))} ${esc(o.unit || '')}</span>` : '')
        + `</span><span class="t2">${said(o.title || o.sentence || '')}</span></button>`;
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
    if (Object.keys(ee).length) {
      s += `<div class="fact"><div class="l">The ground within 1 km</div>`
        + ['built_frac', 'tree_frac', 'crop_frac', 'water_frac'].filter(m => ee[m] && ee[m].value != null)
          .map(m => `<div>${esc(m.replace(/_frac$/, ''))} ${fmt(ee[m].value * 100, 0)}% ${prov('model')}</div>`).join('')
        + `</div>`;
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

/* ---- Node (§5.3): /health only, so it always draws ---- */
function drawNode(h) {
  const mesh = h.mesh && h.mesh.root_topic, radio = h.reticulum && h.reticulum.announce_s;
  let s = `<div class="facts">`
    + `<div class="fact"><div class="l">The node</div>${esc(h.node || 'this node')}${h.city ? `, in ${esc(h.city)}` : ''}</div>`
    + `<div class="fact"><div class="l">Running</div>planetai-node ${esc(h.version || '')} · schema ${esc(h.schema || '')}<br>`
    + `up ${fmt((h.uptime_s || 0) / 3600, 1)} h · last poll ${hhmm(h.last_poll)} · ${(h.ingested || 0).toLocaleString('en')} readings since the restart</div>`
    + `<div class="fact"><div class="l">The mesh and the radio</div>mesh ${mesh ? 'on' : 'off'} · radio ${radio ? 'on' : 'off'}</div>`;
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

/* freshness (§7): no timer — a visible-again page older than five minutes asks again */
document.addEventListener('visibilitychange', async () => {
  if (document.hidden || !D || !D.as_of) return;
  if (Date.now() - Date.parse(D.as_of) > 5 * 60 * 1000) { try { D = await loadD(MOBILE_ROUTES); drawAll(); } catch (e) { /* keep what is drawn */ } }
});

boot();
