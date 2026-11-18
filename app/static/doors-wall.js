'use strict';
/* WALL, WALKING OUT ON THE SATELLITE (18 Nov 2026; planetai-design node-docs/superpowers/specs/2026-11-18-wall-scales-map
   -design.md and its mockup). It replaced the Wall as instruments (8 Nov): Tomas, 18 Nov, asked for "more prominence to
   a satellite map showing the data of the node changing in three scales, from base node, to community node scale, to
   city node scale". The map is doors-wallmap.js's; this file draws what is around it and keeps the one clock.
   The Wall's rules hold as they were (tests/test_doors.py): nothing under --wf, now 20 px at 1920×1080; no sensor, room
   or kit named; every figure with its time and one of the five words; chrome only under a pointer or the keyboard; and
   "what is asked now" is wallAsk, the same answer Now and the phone read.
   - THE MAP, left: the base node's seven cells, then the community's, then the city's, a replayed day at each size. The
     day is split between the size's chapters (wallStory), one layer each; the wind and the swell move on it.
   - THE COLUMN, right: the time, the lead issue's sentence and what is asked now; the size's name and a row per chapter,
     the chapter on the map lit with its word and its words; the node thinking aloud, once its model has written.
   - THE STRIP, under both: fine dust, heat, the swell and the wind at the replayed hour, each with its 24 hours as a thin
     line, and the clock. Stepped, never tweened: only the camera glides, and that is MapLibre's own.
   Under reduced motion it is one still frame: the base size at the last hour. */
/* Every duration on the Wall, named after the datum it paces. The replay loop is the layer's token, --motion-replay-loop. */
const WALL_TIME = {
  HOUR_STEP: () => (parseFloat(css('--motion-replay-loop')) || 30) / 24,    /* s: one replayed hour of the last 24 */
  NARR_EVERY: 10 * 60e3,                                                    /* ms: a new reading by the node's model */
  NARR_CHAR: 1000 / 11,                                                     /* ms: one character typed, about two words a second */
  NARR_LINE: 3000,                                                          /* ms: one line of a story longer than its box, rolling */
  STALE: 15 * 60e3,                                                         /* ms: no poll this long and the readings are old */
};
/* Never a name on the wall (Tomas, 14 Oct 2026): anyone in the room reads it, and a sensor's name is a room, a kit or an
   address ("K ROOM - BAYU HOLES"); a kicker's reason names who answered. The house is its cell, a public station a dot;
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
/* `stale` only when the node's readings are old: no poll in the last 15 minutes (three at the 300 s default), or none
   since the restart. /health's last_error is not read: one failing portal of twenty sets it while the rest are fresh. */
const wallStale = h => !(Date.now() - Date.parse(h.last_poll || '') < WALL_TIME.STALE);
/* a source in the Wall's own words, never a sensor's name: a name can be a room, a kit or a point ("Sea, 5 km off
   (-8.79, 115.13)"); a count of sensors is said as it is, a model by the service, anything else as "a model" */
const wallSrc = s => /^\d+ sensors?$/.test(s || '') ? s : /CAMS/i.test(s || '') ? 'CAMS' : /open-meteo/i.test(s || '') ? 'Open-Meteo' : 'a model';
const wpw = w => `<span class="wpw">${esc(w)}</span>`;
const COMPASS16 = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
/* THE DAY IN THE STRIP: the last 24 hours, an hour a row. Dust and heat are the issues' own series at the issue's
   headline distance; the swell and the wind are /wall's hourly Open-Meteo rows, which a screen with no token may read. */
function wallDay24(W) {
  /* without /issues/days there are no buckets: the replay is 24 whole hours ending at /aggregates' last hour, else at the
     as-of time's */
  const rb = (D.raw || {}).buckets || [], top = rb.length ? Date.parse(rb[rb.length - 1]) : Math.floor(Date.parse(D.as_of) / 3600e3) * 3600e3;
  const B = D.buckets.length ? D.buckets.slice(-24) : [...Array(24)].map((_, i) => new Date(top - (23 - i) * 3600e3).toISOString());
  const issue = k => {
    const it = D.issues[k], d = it && (it.hero_distance || 'room'), v = it && it.series && (it.series[d] || []).slice(-24);
    if (!v || !v.some(x => x != null)) return null;
    const s = (it.stack || {})[d] || {};
    return { v, ts: B, line: it.line, dp: it.dp ?? 0, word: (it.provenance || {})[d] || s.provenance || 'partial', src: wallSrc(s.source) };
  };
  const Hr = (W || {}).hours, hour = (k, dp) => Hr && (Hr[k] || []).some(x => x != null) ? { v: Hr[k], ts: Hr.buckets, dp, word: 'model', src: 'Open-Meteo' } : null;
  return { B, dust: issue('air'), heat: issue('heat'), sea: hour('swell_m', 1), wind: hour('wind_kmh', 0) };
}
/* s: the size on the map (an index of WALL.story); h: the replayed hour; map: wallMapMount's handle, null when none */
const WALL = { R: null, W: null, story: [], map: null, s: 0, h: null, t0: 0, still: null };
/* a thin line for the 24 hours, the hour marked, the red line where the reading has one */
function wallSpark(r, h) {
  const ys = r.v.filter(x => x != null); if (!ys.length) return '';
  const lo = Math.min(...ys, r.line ?? Infinity), hi = Math.max(...ys, r.line ?? -Infinity);
  const X = i => (i / 23 * 100).toFixed(1), Y = x => (96 - (x - lo) / (hi - lo || 1) * 92).toFixed(1);
  let d = ''; r.v.forEach((x, i) => { if (x != null) d += `${d && r.v[i - 1] != null ? 'L' : 'M'}${X(i)},${Y(x)}`; });
  return `<svg class="wsp" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">${r.line != null ? `<path class="wl" d="M0,${Y(r.line)} L100,${Y(r.line)}"/>` : ''}<path d="${d}"/><path class="wh" d="M${X(h)},0 L${X(h)},100"/></svg>`;
}
/* one gauge: its name and source, the figure at the hour with its unit, time and word (or that it is not read), a needle
   turned to where it goes when it has a "from" bearing, and its day */
function wallGauge(name, r, h, unit, hue, from) {
  const v = r && r.v[h];
  const fig = v == null ? `<b>—</b><span>${r ? `not read at ${hhmm(r.ts[h])}` : 'not read here'}</span>`
    : `<b class="wnum">${fmt(v, r.dp)}<u>${esc(unit)}</u></b>${from == null ? '' : `<svg class="wdir" viewBox="-10 -10 20 20" aria-hidden="true"><path transform="rotate(${((from + 180) % 360).toFixed(2)})" d="M0,-8 L4,4 L0,1.5 L-4,4 Z"/></svg>`}<span>${hhmm(r.ts[h])} ${wpw(r.word)}</span>`;
  return `<div class="wg" style="--c:var(${hue})"><div class="wgh"><span>${esc(name)}</span><span>${esc((r && r.src) || '')}</span></div><div class="wrv">${fig}</div>${r ? wallSpark(r, h) : ''}</div>`;
}
const wallFrom = d => d == null ? '' : ` from ${COMPASS16[Math.round(d / 22.5) % 16]}`;
/* the size on the map, in the column and over the map. The column: its name and a row for each chapter, the one on the
   map lit with its word; a size with nothing yet says so in one line and keeps its cells on the map. Over the map, as the
   approved mockup has them (Tomas, 18 Nov): the size and its cells at the top left, the chapter's words at the bottom
   left with where they are from, and the three sizes as nested hexagons at the bottom right, this one lit. */
function wallChapters(h) {
  const S = WALL.story[WALL.s], el = $('#wscale'), cap = $('#wcap'); if (!el) return;
  if (!S) { el.innerHTML = $('#wwhere').innerHTML = $('#whex').innerHTML = cap.innerHTML = ''; return; }
  const n = S.chapters.length, ci = n ? chapterAt(h, n) : -1, ch = S.chapters[ci];
  el.innerHTML = `<h2>${esc(S.name)} <span>· ${esc(S.what)}</span></h2><ul class="wchap">${S.chapters.map((c, j) =>
    `<li${j === ci ? ' class="on"' : ''} style="--c:var(${c.hue})"><i></i><div class="wr"><span class="t">${esc(c.title)}</span><b class="n">${esc(c.n[0] ?? '—')}<u>${esc(c.n[1])}</u>${j === ci ? wpw(c.word) : ''}</b></div></li>`).join('')}</ul>`
    + (n ? '' : '<p class="wnone">The node holds nothing at this size yet.</p>');
  $('#wwhere').innerHTML = `<b>${esc(S.name)}</b><span>${S.cells.length} cells · res ${S.res} · ${fmt(S.km2, 1)} km²</span>`;
  cap.hidden = !ch; cap.style && cap.style.setProperty('--c', ch ? `var(${ch.hue})` : 'var(--ink)');
  cap.innerHTML = ch ? `${esc(ch.says)}<span class="wcs">${esc(ch.src)} · ${esc(ch.word)}</span>` : '';
  $('#whex').innerHTML = wallHexes();
}
/* the three sizes as the seven-cell rule drawn three times, larger each size (the mockup's radii); the size on the map
   lit, its own cell in the cells' blue */
function wallHexes() {
  const R = [3.5, 6, 9.5], hex = (x, y, r, me) => `<polygon${me ? ' class="me"' : ''} points="${[0, 1, 2, 3, 4, 5].map(i => { const a = Math.PI / 180 * (60 * i - 30); return `${(x + r * Math.cos(a)).toFixed(1)},${(y + r * Math.sin(a)).toFixed(1)}`; }).join(' ')}"/>`;
  return WALL.story.map((S, i) => {
    const r = R[i] ?? R[2], w = Math.sqrt(3) * r, z = (2 * (w + r) + 4).toFixed(1), at = [[0, 0], [w, 0], [w / 2, -1.5 * r], [-w / 2, -1.5 * r], [-w, 0], [-w / 2, 1.5 * r], [w / 2, 1.5 * r]];
    return `<div class="s${i === WALL.s ? ' on' : ''}"><svg width="${z}" height="${z}" viewBox="${-z / 2} ${-z / 2} ${z} ${z}" aria-hidden="true">${at.map(([x, y], j) => hex(x, y, r * .92, !j)).join('')}</svg>${esc(S.k)}</div>`;
  }).join('');
}
/* one replayed hour, drawn whole: the strip, the column's chapters and the map */
function wallDraw(h) {
  WALL.h = h; const R = WALL.R; if (!R || !$('#wallv')) return;
  const Hr = (WALL.W || {}).hours || {}, wd = atHour(Hr.wave_from || [], h), dr = atHour(Hr.wind_from || [], h);
  $('#wstrip').innerHTML = wallGauge('fine dust', R.dust, h, 'µg/m³', '--d-air') + wallGauge('apparent heat', R.heat, h, '°C', '--d-heat')
    + wallGauge(`swell${wallFrom(wd)}`, R.sea, h, 'm', '--d-sea', wd) + wallGauge(`wind${wallFrom(dr)}`, R.wind, h, 'km/h', '--d-wind', dr)
    + `<div class="wclock"><b>${hhmm(R.B[h])}</b>of the last 24 h</div>`;
  wallChapters(h);
  if (WALL.map) WALL.map.hour(h);
  headFit();
}
/* a size on the map: the camera to its cells at the next wallDraw, a cut when asked (a redraw, reduced motion), else
   MapLibre's glide */
function wallScale(s, cut) { WALL.s = s; if (WALL.map) WALL.map.go(s, cut); }
/* the column fits whole: past it the tagline goes first, then the Telegram line (node #1, 10 Nov: a three-line
   sentence put the ask under the bottom of the screen) */
function headFit() {
  const hd = $('.wcol'); if (!hd || !hd.querySelectorAll) return;
  const drop = [...hd.querySelectorAll('.wtag, .wask .wtel')];
  drop.forEach(e => { e.hidden = false; });
  for (const e of drop) { if (hd.scrollHeight <= hd.clientHeight + 1) break; e.hidden = true; }
}
/* the replay's one clock: an hour every HOUR_STEP, a day at each size, then the next size */
function wallTick(now) {
  if (view() !== 'wall') return CLOCK.off('wall-replay');
  if (CLOCK.reduced()) { WALL.still = true; CLOCK.off('wall-replay'); CLOCK.off('wall-fx'); if (WALL.h !== 23 || WALL.s) { wallScale(0, true); wallDraw(23); } return; }   /* motion turned off while it ran */
  const i = Math.floor((now - WALL.t0) / (WALL_TIME.HOUR_STEP() * 1000)), s = Math.floor(i / 24) % Math.max(1, WALL.story.length), h = i % 24;
  if (s !== WALL.s) { wallScale(s); wallDraw(h); } else if (h !== WALL.h) wallDraw(h);   /* a size takes effect at its first hour */
}
const wallGet = p => doorsFetch(p).then(r => r.ok ? r.json() : null).catch(() => null);
VIEWS.wall = async function () {
  const k = D.lead, it = D.issues[k], still = CLOCK.reduced();
  const at = new Intl.DateTimeFormat('en-GB', { timeZone: D.tz, hour: '2-digit', minute: '2-digit' }).format(new Date(D.as_of));
  /* a redraw on a poll keeps the replay's hour; motion turned on or off since the last draw, even on another door, starts it over */
  if (WALL.h == null || WALL.still !== still) { WALL.h = still ? 23 : 0; WALL.s = 0; WALL.t0 = performance.now(); }
  WALL.still = still;
  if (!WALL.sized) { WALL.sized = true;
    matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', e => {           /* still at the last hour, or the replay again */
      if (view() !== 'wall') { WALL.still = null; return; }   /* changed off the Wall: it starts over when it opens */
      WALL.still = e.matches;
      if (e.matches) { CLOCK.off('wall-replay'); CLOCK.off('wall-fx'); wallScale(0, true); wallDraw(23); } else { WALL.t0 = performance.now(); CLOCK.on('wall-replay', wallTick); }
    }); }
  /* one read of /wall a draw, and /ground/meta for which ground the node holds; a screen refused either draws without it */
  const [W, G] = await Promise.all([wallGet('/wall'), wallGet('/ground/meta')]);
  WALL.W = W; WALL.story = W ? wallStory(W, D) : []; WALL.R = wallDay24(W);
  if (WALL.map) { WALL.map.destroy(); WALL.map = null; }
  $('#wallv').innerHTML = `
    <div class="wtop wchrome"><button class="wback" onclick="location.hash='#now'">← back</button><span class="wnote said" id="wnote"></span></div>
    <section class="wmap" id="wmap" data-learn="wall-map" data-reads="/wall /ground/meta /ground/imagery /ground/vector /earth/wall.png" data-stage="observe" data-pack="core">
      <div class="wmbox" id="wmbox"></div><div class="wover wwhere" id="wwhere"></div><div class="wover wcap" id="wcap" hidden></div><div class="wover whex" id="whex"></div></section>
    <aside class="wcol">
      <div class="whead" data-learn="wall-sentence" data-reads="/issues /health" data-stage="decide" data-pack="core">
        <div class="wkick"><time>${at}</time>${wallStale(D.health) ? ' · <b>the readings are old</b>' : ''}</div>
        <p class="wsent"><span class="said">${esc(it.title || it.sentence).replace(/(\d+(?:\.\d+)?)(?=\s*(?:°C|µg|%|m\b))/, m0 => num(`${k}.${it.hero_distance}`, m0, `against the line, ${it.line} ${it.unit}`, `<b class="wnum">${m0}</b>`))}</span></p>
        ${it.title && it.tagline ? `<p class="wtag said">${esc(it.tagline)}</p>` : ''}
        <div class="wask">${wallAsk(it)}</div></div>
      <div class="wscale" id="wscale"></div>
      <section class="wnarr" id="wnarr" hidden data-learn="wall-narration" data-reads="/ask/status /ask" data-stage="observe" data-pack="core"></section>
    </aside>
    <footer class="wstrip" id="wstrip" data-learn="wall-strip" data-reads="/issues /wall" data-stage="observe" data-pack="core"></footer>`;
  WALL.map = W ? wallMapMount($('#wmbox'), W, WALL.story, (G && G.on_disk) || {}) : null;
  if (!WALL.map) $('#wmbox').innerHTML = `<p class="wnomap">${W ? 'This screen cannot draw the map.' : 'The node sent no map.'}</p>`;
  wallScale(WALL.s, true); wallDraw(WALL.h); narrDraw(); document.fonts.ready.then(() => view() === 'wall' && headFit());
  if (!NARR.busy && !NARR.typing && (!NARR.next || Date.now() >= NARR.next)) narrate(); else if (NARR.shown.length < NARR.text.length) narrType();
  if (!still) CLOCK.on('wall-replay', wallTick);
};
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
let NARR_TYPE = 0;
function narrDraw() {
  const el = $('#wnarr'), note = $('#wnote'); if (!el) return;
  if (note) note.textContent = NARR.err || (NARR.model ? `the words are ${NARR.model}’s${NARR.where ? `, ${NARR.where}` : ''}` : '');
  const t = NARR.shown || NARR.prev;                  /* the text being typed, else the last one whole */
  const was = el.hidden; el.hidden = !t;
  if (was !== el.hidden) headFit();   /* the box takes room in the column, or gives it back */
  if (!t) { el.innerHTML = ''; return; }
  el.classList.toggle('busy', NARR.busy || NARR.typing);
  el.innerHTML = `<div class="nh"><span class="nl"><i class="dot" aria-hidden="true"></i>The node, thinking aloud</span>`
    + `<span>a model’s words from the node’s figures, never a reading${NARR.where === 'online' ? ' · written online' : ''}</span></div>`
    + `<div class="nw"><p class="nt said"><span id="ntext">${esc(t)}</span>${NARR.typing ? '<i class="caret" aria-hidden="true"></i>' : ''}</p></div>`;
  if (!NARR.typing) narrRoll();
}
/* a story longer than its box rolls up, a line every NARR_LINE, in a loop with its start coming round again, once it
   is typed (Tomas, 21 Oct: the end was cut and the start never came back). A second copy follows the first so the loop
   has no seam; under reduced motion it stands still at its start. */
function narrRoll() {
  const w = $('#wnarr .nw'), p = w && w.querySelector && w.querySelector('.nt');
  if (!p || w.classList.contains('roll') || p.offsetHeight <= w.clientHeight) return;
  w.classList.add('roll');
  { const lh = parseFloat(getComputedStyle(p).lineHeight) || 24, pad = parseFloat(getComputedStyle(w).paddingTop) || 0;   /* whole lines, never one cut across */
    w.style.height = `${pad + Math.max(1, Math.floor((w.clientHeight - pad) / lh)) * lh}px`; }
  const twin = p.cloneNode(true); twin.setAttribute('aria-hidden', 'true'); twin.querySelector('[id]')?.removeAttribute('id'); w.appendChild(twin);
  const cs = getComputedStyle(p), h = p.offsetHeight + parseFloat(cs.marginBottom), line = parseFloat(cs.lineHeight) || 24;
  w.style.setProperty('--roll-h', `${h}px`);
  w.style.setProperty('--roll-s', `${(h / line) * WALL_TIME.NARR_LINE / 1000}s`);
  w.style.setProperty('--roll-n', String(Math.max(1, Math.round(h / line))));   /* a line a step, never a slide */
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
      NARR_TYPE = setTimeout(step, CLOCK.reduced() ? 0 : WALL_TIME.NARR_CHAR);
    } else { NARR_TYPE = 0; NARR.typing = false; NARR.prev = NARR.text; NARR.next = Date.now() + WALL_TIME.NARR_EVERY; narrDraw();
      clearTimeout(NARR.timer); NARR.timer = setTimeout(narrate, WALL_TIME.NARR_EVERY); }
  };
  step();
}
const narrLater = () => { NARR.busy = false; NARR.at = Date.now(); NARR.next = Date.now() + WALL_TIME.NARR_EVERY; narrDraw(); NARR.timer = setTimeout(narrate, WALL_TIME.NARR_EVERY); };
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
