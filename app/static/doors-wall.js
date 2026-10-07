'use strict';
/* metres from the node, the node's answer (js/nodegeo.js); a station it has no answer for sorts last */
const mFrom = s => ((D.ngeo && D.ngeo.dist[s.sensor_id]) || { m: Infinity }).m;

/* WALL — the node's wall anatomy (docs/site/wall.md), always dark, one viewport. The back button first in keyboard
   order; the chips; the flow by scale (js/flow.js) with its hour strip; the headline issue with "Answer on Telegram,
   not here." and never a button that answers; the counts; the ρ row counted, never sized; the fragments; the foot.
   R39 placement: bands ruled by hairlines (mono `4b3c372c`); the left column is exactly the drawing's square, its strip
   flush beneath (the HBO Max telemetry bar `c44e6dca`, Windy `b64ab20b`); the right column's first line sits on the
   drawing's top edge and its last on the strip's bottom edge, so the two columns share two lines. */
let WVAR = 'pm25';
VIEWS.wall = function () {
  const k = D.lead, it = D.issues[k], b = D.buckets[D.now];
  const carried = Object.keys(D.metrics).filter(m => Object.values(D.stats15).some(x => x[m] && x[m][0] != null));
  const chips = [WVAR, ...carried.filter(m => m !== WVAR)].slice(0, 4);
  const moving = !CLOCK.reduced() && !!D.raw;   /* the hours replay only from the hourly table, which needs the token */
  const ask = (it.open_asks || []).length ? said(it.open_asks[0].text || '') : `Nothing has been asked.<small>${said(it.name)} is ${esc(it.state)}, and no rule here asks anybody to do anything about it.</small>`;
  $('#wallv').innerHTML = `
    <div class="wtop"><button class="wback" onclick="location.hash='#now'">← back</button>
      <span class="wchips">${chips.map(m => `<button class="${m === WVAR ? 'on' : ''}" data-m="${m}">${said(labelOf(m))}</button>`).join('')}${carried.length > 4 ? `<a href="#data">+${carried.length - 4} more</a>` : ''}</span>
      <span class="k wid">${said(D.registry.name)} · ${said(D.node.place)} · #wall · share level ${esc(D.share || 'off')} · ${moving ? 'the last 6 hours, replayed every 30 s' : 'the last half hour, held still'}</span>
      <span class="k">${said(labelOf(WVAR))} · ${said(unitOf(WVAR))} · 15-min means</span></div>
    <div class="wgrid">
      <section class="wl" data-kind="row"><div id="wfield" role="img" aria-label="The stations around this house on its own map, their readings hour by hour, and the wind now"></div><div id="wtime" class="flowtime"></div></section>
      <section class="wr"><div class="whead">
        <div class="k">${said(it.name)} <span class="state">${esc(it.state)}</span> · ${said(it.reason_text || '')}</div>
        <p class="wsent">${it.pix ? `<svg class="pix" aria-hidden="true"><use href="${NODE}signs.svg#${it.pix}"/></svg>` : ''}<span class="said">${esc(it.sentence).replace(/(\d+(?:\.\d+)?)(?=\s*(?:°C|µg|%|m\b))/, m0 => num(`${k}.${it.hero_distance}`, m0, `against the line, ${it.line} ${it.unit}`, `<b class="numf">${m0}</b>`))}</span></p>
        <p class="wwhy said">${esc(it.plain || '')}</p>
        <div class="wask">${ask}<b>Answer on Telegram, not here.</b></div></div>
        <div class="wnarr" id="wnarr" data-learn="ask" data-reads="/ask/status /ask" data-stage="observe" data-pack="core"></div>
        <div class="wcount"><div class="wflow" id="wside"></div>
        <div class="wrho" id="wrho" data-kind="row"></div></div>
      </section>
    </div>
    <div class="wfrag" id="wfrag"></div>
    <div class="wfoot k">Read at ${new Intl.DateTimeFormat('en-GB', { timeZone: D.tz, hour: '2-digit', minute: '2-digit' }).format(new Date(D.as_of))} · planetai-node ${esc(D.health.version)} · <b>stale</b> · ${moving ? 'a disc is a station’s hourly mean; the window replays every 30 s · press an hour to go to it' : 'reduced motion: nothing moves; press an hour to go to it'}</div>`;
  document.querySelectorAll('.wchips button').forEach(c => c.onclick = () => { WVAR = c.dataset.m; VIEWS.wall(); });
  rhoRow(); frags(); narrDraw();
  if (!NARR.busy && Date.now() - NARR.at > NARR_EVERY) narrate();
  // the drawing's square sets the left column: the main band's height less the strip, never more than 46% of the width
  const g = $('.wgrid'), S = Math.floor(Math.min(g.clientHeight - 76, g.clientWidth * .46));
  g.style.setProperty('--ws', S + 'px');
  wallMap({ el: $('#wfield'), side: $('#wside'), time: $('#wtime'), size: S });
};
/* The ρ row: counted, never sized. One ring per alert up to 40, one per 10 up to 400, then one per 100; the caption
   names the unit and gives the exact counts. Closed rings are the answered ones, first. */
function rhoRow() {
  const r = D.rho, n = r.alerts_act, unit = n <= 40 ? 1 : n <= 400 ? 10 : 100, rings = Math.ceil(n / unit), closed = Math.round(r.acted / unit);
  $('#wrho').innerHTML = `<span class="rings">${d3.range(rings).map(i => sign(i < closed ? 'sign-rho-closed' : 'sign-rho-open', i < closed ? 'closed' : '')).join('')}</span>`
    + `<small>${num('rho.acted', r.acted, `of ${n} act-level alerts, ${r.window_days} days`)} of ${n} alerts answered · one ring per ${unit === 1 ? 'alert' : unit} · half within ${r.median_minutes} min</small>`;
}
/* The fragments each section gives the wall: the first five, then "+N more in Now". Here, every station's last 15 minutes. */
function frags() {
  const st = D.sensors.filter(s => s.kind === 'sensor').map(s => ({ ...s, v: ((D.stats15[s.sensor_id] || {})[WVAR] || [])[0] })).filter(s => s.v != null)
    .sort((a, b) => (b.local - a.local) || (mFrom(a) - mFrom(b)));   // nearest first, by the node's own metres
  $('#wfrag').innerHTML = st.slice(0, 5).map(s => `<div><span class="said">${esc(plain(s.name))}</span>${num(s.sensor_id + '.' + WVAR, fmt(s.v, 1), WVAR === 'pm25' ? `the line ${D.issues.air.line}` : 'no line', `<b>${fmt(s.v, 1)}</b>`)}<small class="said">${esc(unitOf(WVAR))} · ${s.local ? (s.indoor ? 'this house, inside' : 'this house') : 'public'}</small></div>`).join('')
    + (st.length > 5 ? `<a href="#now" class="more">+${st.length - 5} more in Now</a>` : '');
}

/* THE NODE, THINKING ALOUD (R44, 7 Oct 2026). A live reading of the figures by the node's own model, typed onto the
   wall as it is written: what they mean now, what they could mean over the next hours. It asks POST /ask, the ask
   pane's route, so the model is the one the keeper chose under Set up → Model (AGENT_PREFER): this machine, another
   on the house's network, or an online provider. When it is online the wall says the figures leave the house. The
   context is /ask's own, scrubbed of every place, name and id; nothing is stored. A model's words, never a reading,
   and the line under them says so. Again every 3 minutes while the wall is on screen, each time from another angle. */
const NARR = { text: '', at: 0, busy: false, model: null, where: null, read: [], err: null, timer: 0 };
const NARR_EVERY = 3 * 60e3;
/* Plain words for people who know nothing about units or maps (Tomas, 7 Oct): tried on node #1's qwen3:4b until it
   read like a neighbour, said what the readings suggest without promising, and closed on the next few hours. */
/* Every 3 minutes (Tomas, 7 Oct), each time from another angle, so the wall does not say the same thing twice in a row. */
const NARR_ANGLES = ['what is happening right now', 'what has changed over the last few hours', 'how warm it feels inside the home',
  'how inside the home compares with the street and the neighbourhood', 'how today compares with the last few days'];
let NARR_TURN = 0;
const narrAsk = () => "You are the voice of this home's sensor node, speaking on a screen in the living room to people who know nothing about air science, units or maps. Like a calm neighbour, say what is happening around their home right now: the air, and the heat if your context has it. Plain everyday words only. Never write units or symbols such as µg/m³, °C, PM2.5, AQI, ppm, percent or km. Say 'inside your home', 'your street', 'the neighbourhood', 'the wider area' instead of room, yard, ring or region. Instead of numbers, compare: 'clean', 'a little hazy', 'well under the safe limit', 'warmer than usual for this hour'. At most one number. Say what the readings suggest for an ordinary day, such as windows, cooking or sleep, but never promise that anything is safe. End with one sentence about the next few hours, from the forecast or the usual pattern for this hour if your context has it; if it does not, say the node will keep watching. Use only the figures in your context. Three or four short sentences, no lists, no greeting, no questions." + ` This time, start from ${NARR_ANGLES[NARR_TURN++ % NARR_ANGLES.length]}; if your context cannot say, speak about the air now.`;
function narrDraw() {
  const el = $('#wnarr'); if (!el) return;
  /* the model is named once it has answered (the done event says which rung did); while it asks, the wall says only
     that it asks, and warns when the keeper's choice lets the question go online */
  const where = NARR.where === 'online' ? `online · the figures left the house` : NARR.where || '';
  const who = NARR.busy ? ` · asking its model${NARR.leaves ? ' · it may go online, and the figures with it' : ''}` : NARR.model ? ` · ${esc(NARR.model)}${where ? ` · ${esc(where)}` : ''}` : '';
  el.innerHTML = `<div class="k">the node, thinking aloud${who}</div>`
    + (NARR.err ? `<p class="nt said">${esc(NARR.err)}</p>`
      : `<div class="nw"><p class="nt said"><span id="ntext">${esc(NARR.text)}</span>${NARR.busy ? '<i class="caret" aria-hidden="true"></i>' : ''}</p></div>`)   /* the newest line stays in view; the oldest leave the top */
    + `<div class="nf">${NARR.read.length ? `it read ${esc([...new Set(NARR.read)].join(', '))} · ` : ''}a model’s words from the node’s figures, never a reading · kept nowhere`
    + `${NARR.at && !NARR.busy ? ` · written ${new Intl.DateTimeFormat('en-GB', { timeZone: D.tz, hour: '2-digit', minute: '2-digit' }).format(new Date(NARR.at))}, again in 3 min` : NARR.busy ? ' · writing now' : ''}</div>`;
}
async function narrate() {
  if (NARR.busy || view() !== 'wall') return;
  clearTimeout(NARR.timer); NARR.busy = true; NARR.err = null; NARR.read = [];
  const st = await fetch('/ask/status', { headers: DOORS_AUTH() }).then(r => r.ok ? r.json() : r.status === 404 ? { none: true } : null).catch(() => null);
  if (!st || st.none) {
    NARR.busy = false; NARR.at = Date.now();
    NARR.err = st && st.none ? 'No model is set up on this node, so it has nothing to say aloud. Set up → Model, or planetai agent local on the node.' : 'The node did not say which model answers this screen.';
    narrDraw(); NARR.timer = setTimeout(narrate, NARR_EVERY); return;
  }
  NARR.model = null; NARR.where = null; NARR.leaves = !!st.leaves; NARR.text = ''; narrDraw();
  try {
    const r = await fetch('/ask', { method: 'POST', headers: { 'content-type': 'application/json', ...DOORS_AUTH() },
      body: JSON.stringify({ messages: [{ role: 'user', content: narrAsk() }], view: 'wall', mode: 'advanced', focus: null }) });
    if (!r.ok || !r.body) throw new Error(`the node answered ${r.status}`);
    const rd = r.body.getReader(), dec = new TextDecoder(); let buf = '';
    for (;;) {
      const { value, done } = await rd.read(); if (done) break;
      buf += dec.decode(value, { stream: true }); let cut;
      while ((cut = buf.indexOf('\n\n')) >= 0) {
        const block = buf.slice(0, cut); buf = buf.slice(cut + 2);
        const ev = (block.match(/^event: (.+)$/m) || [])[1], data = JSON.parse((block.match(/^data: (.+)$/m) || [])[1] || '{}');
        if (ev === 'token') { NARR.text += data.text; const t = document.getElementById('ntext'); if (t) t.textContent = NARR.text; else narrDraw(); }
        else if (ev === 'retry') { NARR.text = ''; narrDraw(); }
        else if (ev === 'tools') { NARR.read.push(data.name || data.tool || 'a record'); }
        else if (ev === 'done') { NARR.model = data.model || null; NARR.where = data.where || null; }
        else if (ev === 'error') throw new Error(data.message);
      }
    }
    NARR.text = NARR.text.trim() || 'The model answered with nothing.';
  } catch (e) { NARR.err = `The node’s model did not answer: ${e.message}`; }
  NARR.busy = false; NARR.at = Date.now(); narrDraw();
  NARR.timer = setTimeout(narrate, NARR_EVERY);
}
