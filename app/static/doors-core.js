'use strict';
/* PLANETAI node — the five doors (R34–R41 in planetai-design, docs/decisions/2026-10-07-doors.md), over the node's own
   answers (doors-load.js). Served at /doors beside the dashboard while it is tried.
   core: helpers, the one moment (S), the router, the register, Ask the node with Learn inside it. */
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const WD = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'], MO = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
/* A wire time says its own local hour; read it from the string, never re-derive it (DST-safe). */
const dayOf = iso => iso.slice(0, 10), hourOf = iso => +iso.slice(11, 13), hhmm = iso => iso.slice(11, 16);
const dLabel = d => { const t = new Date(d + 'T12:00:00Z'); return `${WD[t.getUTCDay()]}, ${t.getUTCDate()} ${MO[t.getUTCMonth()]}`; };
const wdhm = iso => `${dLabel(dayOf(iso)).split(',')[0]} ${hhmm(iso)}`;
const fmt = (v, dp) => v == null || Number.isNaN(+v) ? '—' : (+v).toFixed(dp);
const plain = s => String(s ?? '').replace(/[\p{Extended_Pictographic}\u{FE0F}\u{200D}]/gu, '').replace(/\s+/g, ' ').trim();
/* the node's own Sentinel-2 annual median for a year (GET /earth/frame.png, open) */
const SAT = y => `/earth/frame.png?year=${y}&source=sentinel`;
const km = ([lon1, lat1], [lon2, lat2]) => d3.geoDistance([lon1, lat1], [lon2, lat2]) * 6371;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

/* ---- the node's rules, as helpers (docs/site/design.md, tools/check_ui.py) ---- */
const NODE = '/static/';                           // the node's own frozen layer: theme, tokens, signs, learn.json, fonts
// The node's own words are never uppercased (µ uppercases to M): anything the node wrote goes in .said.
const said = x => `<span class="said">${esc(x)}</span>`;
// A sign from the node's signs.svg; counting signs repeat, never grow, and never draw under --sign-floor (12 px).
const sign = (id, cls = '') => `<svg class="sg ${cls}" aria-hidden="true"><use href="${NODE}signs.svg#${id}"/></svg>`;
// Provenance is ink only and square: the glyph, then one of the five words. Anything else is an absence, not a provenance.
const PROV = ['live', 'partial', 'model', 'cached', 'example'];
const prov = w => PROV.includes(w) ? `<span class="pill">${sign('sign-prov-' + w)}${w}</span>` : `<span class="gap">${esc(w)}</span>`;
// Every numeral carries its comparison: data-num names it, data-cmp says against what (the visual gate reads both).
const num = (key, v, cmp, inner) => `<span data-num="${esc(key)}" data-cmp="${esc(cmp)}">${inner ?? esc(v)}</span>`;
const unitOf = m => (D.metrics[m] || {}).unit || '';
const labelOf = m => (D.metrics[m] || {}).label || m.replace(/_/g, ' ');

/* One clock for the whole page (design.md, Motion): surfaces subscribe; it stops when the tab is hidden or nobody
   is subscribed, and it never starts under reduced motion. Transform and opacity only. */
const CLOCK = { subs: new Map(), raf: 0,
  reduced: () => matchMedia('(prefers-reduced-motion: reduce)').matches,
  on(id, fn) { if (this.reduced()) return false; this.subs.set(id, fn); this.run(); return true; },
  off(id) { this.subs.delete(id); },
  run() { if (this.raf || !this.subs.size || document.hidden) return; const f = t => { this.raf = 0; if (!this.subs.size || document.hidden) return; this.subs.forEach(fn => fn(t)); this.raf = requestAnimationFrame(f); }; this.raf = requestAnimationFrame(f); } };
document.addEventListener('visibilitychange', () => CLOCK.run());

let D, S = { issue: null, i: 0 };
const ISSUES_DRAWN = k => D.issues[k].series && Object.values(D.issues[k].series).some(Boolean);
function val(k, dist, i) { const s = (D.issues[k].series || {})[dist]; return s ? s[i] : null; }
function evAt(k, i) {
  const t = D.buckets[i];
  return D.events.filter(e => e.issue === k && e.opened_at.slice(0, 13) <= t.slice(0, 13) && (e.cleared_at == null || e.cleared_at.slice(0, 13) >= t.slice(0, 13)));
}
function answerWords(a) { return a ? { w: `${a.stage} · ${a.actor} · ${hhmm(a.ts)}`, closed: a.stage === 'acted' } : { w: 'no answer yet', closed: false }; }
/* The last hour's mean of one metric at one sensor, from the raw hourly table. */
/* The last hour's mean of one metric at one sensor, from the raw hourly table (token-only); without it the 15-minute
   mean GET /stats gives every screen at `open`. */
function lastRaw(id, metric) {
  if (!D.raw) return ((D.stats15[id] || {})[metric] || [])[0] ?? null;
  const s = ((D.raw.series[id] || {})[metric]) || []; for (let i = s.length - 1; i >= 0; i--) if (s[i]) return s[i][0]; return null;
}

const DOORS = ['now', 'place', 'node', 'data', 'wall', 'setup'];   /* setup is a page, opened by the gear, not a door in the menu */
/* #data/<sensor-id> opens a door at one thing: the part after the slash is the door's to read */
const view = () => { const d = location.hash.slice(1).split('/')[0]; return DOORS.includes(d) ? d : 'now'; };
const VIEWS = {};
let userTheme = 'light';
function route() {
  const v = view();
  document.querySelectorAll('.view').forEach(el => { el.hidden = el.dataset.view !== v; });
  document.querySelectorAll('.doors a').forEach(a => a.classList.toggle('on', a.dataset.v === v));
  document.body.dataset.view = v;
  if (v !== 'wall' && typeof flowStop === 'function') { const w = $('#wfield'); w && flowStop(w); }
  if (v !== 'wall' && typeof WALLMAP !== 'undefined' && WALLMAP.stop) WALLMAP.stop();
  // the wall is the keeper's register: dark, always (Decision 15); every other door keeps the reader's choice
  document.documentElement.dataset.theme = v === 'wall' ? 'dark' : userTheme;
  VIEWS[v]();
  learnList(); window.scrollTo(0, 0);
}

Promise.all([loadD(), fetch(NODE + 'learn.json').then(r => r.json()).catch(() => ({ marks: {} }))]).then(async ([d, l]) => {
  D = d; D.learn = l.marks;
  D.dates = [...new Set(D.buckets.map(dayOf))];
  D.at = {}; D.buckets.forEach((b, i) => { D.at[dayOf(b) + '|' + hourOf(b)] = i; });
  S.issue = D.lead; S.i = D.buckets.length - 1; D.now = S.i;
  D.sens = Object.fromEntries(D.sensors.map(s => [s.sensor_id, s]));
  /* the cells and distances the flow, the Wall and Node draw are the node's answers (js/nodegeo.js) */
  knownNodes(D); foot();
  if (D.askOff) $('#askbtn').hidden = true;                 /* UI_ASK off: no ask here either */
  $('#who').innerHTML = `${esc(D.node.name)}<small>${esc(D.node.place || '')}</small>`;
  $('#asof').textContent = `${new URLSearchParams(location.search).get('fixture') ? 'CAPTURE' : 'LIVE'} · as of ${hhmm(D.as_of)} · ${D.health.version || ''}${DOORS_TOKEN() ? '' : ' · locked'}`;
  try { D.ngeo = await nodeGeo(D); } catch (e) { D.ngeo = null; D.ngeoErr = e.message; }
  route();
  window.addEventListener('hashchange', route);
  let t; window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(() => VIEWS[view()](), 120); });
}).catch(refused);

/* At SHARE_LEVEL=off a screen without the token is refused /issues, and the doors have nothing to draw. That is a real
   state a phone on the house's WiFi will be in, not an error: draw the node's name (/health answers at every level),
   the node's own sentence, and the one way in, the token. Without this the page stayed blank and could not be unlocked. */
async function refused(e) {
  const [h, r] = await Promise.all([fetch('/health').then(x => x.json()).catch(() => ({})),
    fetch('/issues', { headers: DOORS_AUTH() }).then(async x => x.ok ? null : (await x.json().catch(() => ({}))).error || (await x.text().catch(() => ''))).catch(() => null)]);
  $('#who').innerHTML = `${esc(h.node || 'this node')}<small>${esc(h.city || '')}</small>`;
  $('#asof').textContent = `${h.version || ''} · locked`;
  document.querySelectorAll('.view').forEach(el => { el.hidden = el.dataset.view !== 'setup'; });
  $('#setupv2').innerHTML = `<header class="sh"><div class="k">${esc(h.node || 'this node')} · not sharing with this screen</div><h1>This node is not sharing its readings with this screen.</h1>`
    + `<p class="lede">${esc(r || e.message)}</p><p class="lede">Unlock this screen with a token, or ask whoever set this node up to turn sharing on (Set up → Sharing). <code>planetai ui</code> on the node prints the tokens.</p></header>`
    + `<form class="unlock2" id="sunlock"><label>Admin token<input type="password" id="stok" autocomplete="off" placeholder="changes settings, reads everything"></label>`
    + `<label>Token for closing a loop<input type="password" id="sact" autocomplete="off" placeholder="answers alerts, changes nothing"></label>`
    + `<div><button type="submit" class="sbtn primary">Unlock this screen</button></div></form>`;
  $('#sunlock').onsubmit = ev => { ev.preventDefault(); const t1 = $('#stok').value.trim(), t2 = $('#sact').value.trim();
    try { if (t1) localStorage.setItem('planetai_admin', t1); if (t2) localStorage.setItem('planetai_act', t2); } catch (x) { /* no storage here */ } location.reload(); };
}

document.querySelectorAll('.reg button').forEach(b => b.onclick = () => {
  userTheme = b.dataset.r; document.querySelectorAll('.reg button').forEach(o => o.classList.toggle('on', o === b)); route(); });

/* ---------- Ask the node, and Learn inside it ----------
   Learn is the node's own learn mode (app/static/learn.json): every part names a mark, and the list says what the
   docs say about it, which routes the part reads, which pack drew it and which stage of the loop it belongs to.
   The questions offered are the marks' own. */
function learnList() {
  const v = view(), on = $('#learn').checked, pane = document.querySelector(`.view[data-view="${v}"]`);
  const parts = pane ? [...pane.querySelectorAll('[data-learn]')] : [];
  document.body.classList.toggle('learn', on);
  parts.forEach((el, n) => el.dataset.n = n + 1);
  $('#learnlist').innerHTML = on ? parts.map((el, n) => {
    const m = D.learn[el.dataset.learn] || {};
    return `<li><i>${n + 1}</i><span><b>${esc(m.title || el.dataset.learn)}</b>${el.dataset.stage ? ` <span class="k">${esc(el.dataset.stage)}</span>` : ''}<br>${esc(plain(m.more || ''))}`
      + `<span class="reads">${(el.dataset.reads || '').split(' ').filter(Boolean).map(r => `<code>GET ${esc(r)}</code>`).join(' ')}${el.dataset.pack ? ` <code>${esc(el.dataset.pack)}</code>` : ''}`
      + `${m.page ? ` · <a href="https://planetai.fab.city/docs/${esc(m.page.replace('.md', '/'))}">${esc(m.page_title || m.page)}</a>` : ''}</span></span></li>`;
  }).join('') : '';
  const qs = [...new Set(parts.flatMap(el => ((D.learn[el.dataset.learn] || {}).questions || {}).en || []))].slice(0, 4);
  $('#try').innerHTML = qs.map(q => `<button>${esc(q)}</button>`).join('');
  document.querySelectorAll('#try button').forEach(b => b.onclick = () => { $('#q').value = b.textContent; });
}
$('#askbtn').onclick = () => { const open = $('#askpane').hidden; $('#askpane').hidden = !open; $('#askbtn').setAttribute('aria-expanded', String(open)); if (open) { learnList(); $('#q').focus(); } };
$('#askclose').onclick = () => { $('#askpane').hidden = true; $('#askbtn').setAttribute('aria-expanded', 'false'); $('#learn').checked = false; learnList(); };
$('#learn').onchange = learnList;
/* the token is set and cleared on Set up → This screen (doors-setup.js), kept where the dashboard keeps it */
/* POST /ask, the node's own: it streams `event: token` blocks; only the words are drawn here, the dashboard's ask pane
   keeps the ledger of what it read. One question at a time, no thread. */
$('#qsend').onclick = async () => {
  const q = $('#q').value.trim(), out = $('#qout'); if (!q) return;
  out.textContent = '…'; $('#qsend').disabled = true;
  try {
    const r = await fetch('/ask', { method: 'POST', headers: { 'content-type': 'application/json', ...DOORS_AUTH() },
      body: JSON.stringify({ messages: [{ role: 'user', content: q }], view: view(), mode: 'advanced', focus: null }) });
    if (!r.ok || !r.body) throw new Error((await r.json().catch(() => ({}))).detail || `the node answered ${r.status}`);
    const rd = r.body.getReader(), dec = new TextDecoder(); let buf = '', text = '';
    for (;;) {
      const { value, done } = await rd.read(); if (done) break;
      buf += dec.decode(value, { stream: true }); let cut;
      while ((cut = buf.indexOf('\n\n')) >= 0) {
        const block = buf.slice(0, cut); buf = buf.slice(cut + 2);
        const ev = (block.match(/^event: (.+)$/m) || [])[1], data = JSON.parse((block.match(/^data: (.+)$/m) || [])[1] || '{}');
        if (ev === 'token') { text += data.text; out.textContent = text; }
        else if (ev === 'retry') { text = ''; }
        else if (ev === 'error') throw new Error(data.message);
      }
    }
    if (!text) out.textContent = 'The node answered with nothing.';
  } catch (e) { out.textContent = `The node did not answer: ${e.message}`; }
  finally { $('#qsend').disabled = false; }
};

/* The foot of every door but the Wall: what this is, where its words are, and who it belongs to. The links are the
   node's own (/health.docs, /llms.txt) and the programme's; the classic dashboard stays one press away while the
   doors are tried. */
function foot() {
  const h = D.health, docs = h.docs || 'https://planetai.fab.city/docs/', rel = h.release || {};
  $('#foot').innerHTML = `<div><b>This node</b><p>${esc(D.node.name)}${D.node.place ? ` · ${esc(D.node.place)}` : ''} · planetai-node ${esc(h.version || '')}</p>`
    + `<p>${rel.newer ? `${esc(rel.latest)} is out: <code>planetai update</code> on the node.` : 'A node of PLANETAI, the Fab City programme’s network of homes that read their place, decide and act.'}</p></div>`
    + `<div><b>Read</b><a href="${esc(docs)}" target="_blank" rel="noopener">Documentation</a><a href="${esc(docs)}dashboard/" target="_blank" rel="noopener">These pages, explained</a>`
    + `<a href="${esc(h.llms || '/llms.txt')}">For agents: llms.txt</a>${D.askOff ? '' : '<button class="linkish" type="button" id="footask">Ask the node</button>'}</div>`
    + `<div><b>This house</b><a href="/">The classic dashboard</a><a href="#setup">Set up</a><a href="#setup/screen">Unlock this screen</a><a href="/export?day=${esc(dayOf(D.as_of))}">Today’s open data, CC BY 4.0</a></div>`
    + `<div><b>Fab City</b><a href="https://planetai.fab.city/" target="_blank" rel="noopener">PLANETAI</a><a href="https://fab.city/" target="_blank" rel="noopener">Fab City Foundation</a>`
    + `<a href="https://github.com/fabcity/planetai-node" target="_blank" rel="noopener">Source, Apache-2.0</a></div>`;
  if (!D.askOff) $('#footask').onclick = () => $('#askbtn').click();
}
