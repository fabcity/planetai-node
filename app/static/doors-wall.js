'use strict';
/* WALL — a public screen in a living room or a lab, read from about 3 m by people who know nothing about air science
   (docs/site/dashboard.md, the Wall). Always dark, one viewport, operated by nobody.
   PLAN (Tomas's review of 14 Oct 2026, built 15 Oct):
   - Type floor: nothing under --wf, 28 px at 1920×1080 and scaled by the viewport (doors.html, the WALL block). What
     did not survive the floor was cut, not shrunk: the kicker's reason, the "why" paragraph, the fragments row, the
     counts box, the foot, the scale bar, the countdown and the model's name.
   - Reading order, top to bottom and left to right: the sentence with the clock (the hero, as the engine writes it) →
     the map (wind, stations, the house as one mark), its caption saying in words what its red discs mean against the
     house → what the node suggests, one line ending on a word, never a room → did people here act on it (ρ in words,
     larger rings) → the narration, only when there is text.
   - Chrome (back, chips, the hour strip, the model's note) is .wchrome: invisible until a pointer is over it or the
     keyboard is in it. The back button stays first in keyboard order.
   - The narration box is collapsed until a model's text arrives, and keeps the last text, in memory, while the next one
     is written. Its label says these are a model's words. */
let WVAR = 'pm25';
/* Never a name on the wall (Tomas, 14 Oct 2026): anyone in the room reads it, and a sensor's name is a room, a kit or an
   address ("K ROOM - BAYU HOLES"); a kicker's reason names who answered. The house is one mark, a public station a disc;
   what is asked is the engine's own sentence (asking[].says), never the alert's text, which names the room. */
/* one line that ends on a word: the first sentence, cut at a word under `max` characters ("If somethin…", 14 Oct) */
const oneLine = (s, max = 90) => {
  s = String(s || '').trim(); const f = s.match(/^.*?[.!?](?=\s|$)/); s = f ? f[0] : s;
  return s.length <= max ? s : s.slice(0, max + 1).replace(/\s+\S*$/, '').replace(/[\s,;:–—-]+$/, '') + '…';
};
/* What is asked now is the node's one answer (/issues asking), the same Now's Decide card reads: an alert still open
   whose reading came back is not asked of anybody now, and the Wall said it was while Now said nothing was (14 Oct). */
function wallAsk(it) {
  const a = it.asking || [], says = a.length ? oneLine(a[0].says) : '';
  if (!a.length) return '<span class="wsay">Nothing is asked now.</span>';
  const count = a.length === 1 ? 'One thing is asked of this house.' : `${a.length} things are asked of this house.`;
  return `<span class="wsay said">${esc(says || count)}</span><span class="wtel">${says ? count + ' ' : ''}Answer on Telegram, not here.</span>`;
}
/* The map's caption: its red discs in words against the house, now, so a clean headline beside red discs is not a
   contradiction left to the reader; it reads the hour the discs are drawn at ("This house is under the clean-air line now; 3 stations nearby, in red, are over it"). */
function wallCaption(house, near, line, when = 'now') {
  if (line == null) return '';
  const n = near.filter(v => v != null && v > line).length, st = n === 1 ? 'one station nearby, in red, is' : `${n} stations nearby, in red, are`;
  if (house == null) return n ? `${st[0].toUpperCase() + st.slice(1)} over the clean-air line ${when}.` : `Every station nearby is under the clean-air line ${when}.`;
  if (house > line) return n ? `This house is over the clean-air line ${when}, and ${st} too.` : `This house is over the clean-air line ${when}; no station nearby is.`;
  return n ? `This house is under the clean-air line ${when}; ${st} over it.` : `This house and every station nearby are under the clean-air line ${when}.`;
}
/* `stale` only when the node's readings are old: no poll in the last 15 minutes (three at the 300 s default), or none
   since the restart. /health's last_error is not read: one failing portal of twenty sets it while the rest are fresh. */
const wallStale = h => !(Date.now() - Date.parse(h.last_poll || '') < 15 * 60e3);
VIEWS.wall = function () {
  const k = D.lead, it = D.issues[k];
  const carried = Object.keys(D.metrics).filter(m => Object.values(D.stats15).some(x => x[m] && x[m][0] != null));
  const chips = [WVAR, ...carried.filter(m => m !== WVAR)].slice(0, 4);
  const at = new Intl.DateTimeFormat('en-GB', { timeZone: D.tz, hour: '2-digit', minute: '2-digit' }).format(new Date(D.as_of));
  $('#wallv').innerHTML = `
    <div class="wtop wchrome"><button class="wback" onclick="location.hash='#now'">← back</button>
      <span class="wchips">${chips.map(m => `<button class="${m === WVAR ? 'on' : ''}" data-m="${m}">${said(labelOf(m))}</button>`).join('')}</span>
      <span class="wnote said" id="wnote"></span></div>
    <div class="wgrid">
      <section class="wl" data-kind="row"><div id="wfield" role="img" aria-label="The stations around this house on its own map, their readings, and the wind now"></div>
        <div id="wtime" class="flowtime wchrome"></div><p class="wcap said" id="wcap"></p></section>
      <section class="wr"><div class="whead">
        <div class="wkick"><time>${at}</time>${wallStale(D.health) ? ' · <b>the readings are old</b>' : ''}</div>
        <p class="wsent">${it.pix ? `<svg class="pix" aria-hidden="true"><use href="${NODE}signs.svg#${it.pix}"/></svg>` : ''}<span class="said">${esc(it.title || it.sentence).replace(/(\d+(?:\.\d+)?)(?=\s*(?:°C|µg|%|m\b))/, m0 => num(`${k}.${it.hero_distance}`, m0, `against the line, ${it.line} ${it.unit}`, `<b class="numf">${m0}</b>`))}${it.tagline ? `<span class="wtag">${esc(it.tagline)}</span>` : ''}</span></p>
        <div class="wask">${wallAsk(it)}</div></div>
        <div class="wrho" id="wrho" data-kind="row"></div>
        <div class="wnarr" id="wnarr" hidden data-learn="ask" data-reads="/ask/status /ask" data-stage="observe" data-pack="core"></div>
      </section>
    </div>`;
  document.querySelectorAll('.wchips button').forEach(c => c.onclick = () => { WVAR = c.dataset.m; VIEWS.wall(); });
  rhoRow(); narrDraw();
  if (!NARR.busy && !NARR.typing && (!NARR.next || Date.now() >= NARR.next)) narrate(); else if (NARR.shown.length < NARR.text.length) narrType();
  // the drawing's square sets the left column: the main band's height less the caption, never more than 46% of the width
  const g = $('.wgrid'), S = Math.floor(Math.min(g.clientHeight - 3.4 * parseFloat(getComputedStyle(g).fontSize), g.clientWidth * .46));
  g.style.setProperty('--ws', S + 'px');
  wallMap({ el: $('#wfield'), cap: $('#wcap'), time: $('#wtime'), size: S });
};
/* The ρ row: counted, never sized, and said in words first ("the house answered 8 of 311 alerts"; small open rings read
   as a row of letter Cs, 14 Oct). One ring per alert up to 40, one per 10 up to 400, then one per 100. Closed rings are
   the answered ones, first. */
function rhoRow() {
  const r = D.rho, n = r.alerts_act || 0;
  if (!n) { $('#wrho').innerHTML = `<p>No alert has gone out from this house in ${r.window_days} days.</p>`; return; }
  const unit = n <= 40 ? 1 : n <= 400 ? 10 : 100, rings = Math.ceil(n / unit), closed = Math.round(r.acted / unit);
  $('#wrho').innerHTML = `<p class="rsay">This house answered ${num('rho.acted', r.acted, `of ${n} act-level alerts, ${r.window_days} days`, `<b>${r.acted}</b>`)} of ${n} alerts in ${r.window_days} days.</p>`
    + `<span class="rings">${Array.from({ length: rings }, (_, i) => sign(i < closed ? 'sign-rho-closed' : 'sign-rho-open', i < closed ? 'closed' : '')).join('')}</span>`
    + `<p>${unit === 1 ? 'A ring is an alert' : `A ring is ${unit} alerts`}; a closed ring was answered.</p>`;
}

/* THE NODE, THINKING ALOUD (R44, 7 Oct 2026). A reading of the figures by the node's own model, in plain words for
   people who know nothing about air science, units or maps: what is happening inside, how it compares with the street and the
   neighbourhood, what it suggests for an ordinary day, and what the next hours may bring. It asks POST /ask, so the
   model is the one the keeper chose under Set up → Model (AGENT_PREFER): this machine, another on the house's network,
   or an online provider; the wall names the one that answered, and warns while it asks when the choice can go online.
   The context is /ask's own, scrubbed of every place, name and id; nothing is stored.
   Tomas, 7 Oct: twice as long, written at a slower pace, a new one every 10 minutes, and a countdown to the next.
   The model writes into a queue; the wall types it at a reading pace whatever the model's speed.
   The prompt lives on the node as WALL_SYSTEM; the page asks for it by name (prompt:'wall').
   15 Oct: the box is collapsed until there is text (an empty frame saying "asking its model" was the second-largest
   thing on the wall), and the last text stays up, whole, while the model writes the next; the new one is typed only
   once it has all arrived. Kept in memory, never stored. The label says these are a model's words; the model's name, a
   failure and why are chrome (#wnote), shown under a pointer or the keyboard. */
const NARR = { text: '', shown: '', prev: '', at: 0, next: 0, busy: false, typing: false, model: null, where: null, err: null, timer: 0 };
const NARR_EVERY = 10 * 60e3, NARR_CPS = 11;          /* about two words a second: read as it is written */
let NARR_TYPE = 0;
function narrDraw() {
  const el = $('#wnarr'), note = $('#wnote'); if (!el) return;
  if (note) note.textContent = NARR.err || (NARR.model ? `the words are ${NARR.model}’s${NARR.where ? `, ${NARR.where}` : ''}` : '');
  const t = NARR.shown || NARR.prev;                  /* the text being typed, else the last one whole */
  el.hidden = !t;
  if (!t) { el.innerHTML = ''; return; }
  el.classList.toggle('busy', NARR.busy || NARR.typing);
  el.innerHTML = `<div class="nh"><span class="nl"><i class="dot" aria-hidden="true"></i>The node, thinking aloud</span>`
    + `<span>a model’s words from the node’s figures, never a reading${NARR.where === 'online' ? ' · written online' : ''}</span></div>`
    + `<div class="nw"><p class="nt said"><span id="ntext">${esc(t)}</span>${NARR.typing ? '<i class="caret" aria-hidden="true"></i>' : ''}</p></div>`;
}
/* the typist: one character at a time over the last text, all at once under reduced motion; then the next in ten minutes */
function narrType() {
  if (NARR_TYPE) return;
  NARR.typing = true; narrDraw();
  const step = () => {
    if (view() !== 'wall') { NARR_TYPE = 0; return; }
    const t = document.getElementById('ntext');
    if (NARR.shown.length < NARR.text.length) {
      NARR.shown = NARR.text.slice(0, CLOCK.reduced() ? NARR.text.length : NARR.shown.length + 1);
      if (t) t.textContent = NARR.shown; else narrDraw();     /* the first letter opens a box that had nothing yet */
      NARR_TYPE = setTimeout(step, CLOCK.reduced() ? 250 : 1000 / NARR_CPS);
    } else { NARR_TYPE = 0; NARR.typing = false; NARR.prev = NARR.text; NARR.next = Date.now() + NARR_EVERY; narrDraw();
      clearTimeout(NARR.timer); NARR.timer = setTimeout(narrate, NARR_EVERY); }
  };
  step();
}
const narrLater = () => { NARR.busy = false; NARR.at = Date.now(); NARR.next = Date.now() + NARR_EVERY; narrDraw(); NARR.timer = setTimeout(narrate, NARR_EVERY); };
async function narrate() {
  if (NARR.busy || NARR.typing || view() !== 'wall') return;
  clearTimeout(NARR.timer); NARR.err = null;
  if (D.askOff) { NARR.err = ''; NARR.next = 0; narrDraw(); return; }
  NARR.busy = true;
  const st = await doorsFetch('/ask/status').then(r => r.ok ? r.json() : r.status === 404 ? { none: true } : null).catch(() => null);
  if (!st || st.none) {
    NARR.err = '';
    return narrLater();
  }
  NARR.model = null; NARR.where = null; NARR.prev = NARR.shown || NARR.prev; NARR.text = ''; NARR.shown = ''; narrDraw();
  try {
    const r = await fetch('/ask', { method: 'POST', headers: { 'content-type': 'application/json', ...DOORS_AUTH() },
      body: JSON.stringify({ messages: [{ role: 'user', content: 'speak' }], view: 'wall', mode: 'advanced', focus: null, prompt: 'wall' }) });
    if (!r.ok || !r.body) throw new Error(`the node answered ${r.status}`);
    const rd = r.body.getReader(), dec = new TextDecoder(); let buf = '';
    for (;;) {
      const { value, done } = await rd.read(); if (done) break;
      buf += dec.decode(value, { stream: true }); let cut;
      while ((cut = buf.indexOf('\n\n')) >= 0) {
        const block = buf.slice(0, cut); buf = buf.slice(cut + 2);
        const ev = (block.match(/^event: (.+)$/m) || [])[1], data = JSON.parse((block.match(/^data: (.+)$/m) || [])[1] || '{}');
        if (ev === 'token') NARR.text += data.text;
        else if (ev === 'retry') NARR.text = '';
        else if (ev === 'done') { NARR.model = data.model || null; NARR.where = data.where || null; }
        else if (ev === 'error') throw new Error(data.message);
      }
    }
    NARR.text = NARR.text.trim();
    if (!NARR.text) throw new Error('it answered with nothing');
  } catch (e) { NARR.err = 'The story returns when the node can speak again.'; NARR.text = ''; }
  if (NARR.err) return narrLater();
  NARR.busy = false; NARR.at = Date.now(); narrType();     /* the typist replaces the last text, then sets the next ten minutes on */
}
