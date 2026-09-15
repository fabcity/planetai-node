/* The dashboard: a shell, a page contract, and ten sections a pack registers with it.
 *
 * The shell knows four things — the dial, the lead, the four stages of the PLANETAI loop
 * (observe · decide · act · measure) and the notes at the foot — and nothing about what its
 * sections are. A pack registers one with window.PAI (the contract is further down, verbatim from
 * the design repo's kit-page.js). Adding a feature is adding a section; a section a node does not
 * have simply is not there, and a section whose data is missing prints one honest line.
 *
 * Ported by hand, once, from planetai-design/prototypes/dashboard-directions — direction H, picked
 * by Tomas on 15 September 2026. Every part below is under a banner naming the file it came from,
 * and every edit made on the way across is marked `PORTED:` and listed in
 * .superpowers/sdd/2026-09-15-modular-dashboard/task-6-report.md.
 *
 * No build step, no framework, nothing loaded from anywhere but static/. A node serves this page to
 * a household LAN and may have no route out at all.
 *
 * WHAT IT READS, and the whole of it: GET /issues (or /issues/fixtures/<name> with ?fixture=),
 * /health, /settings, /rho, /earth, /place/geojson. The node computes; the page draws. A number
 * this page works out for itself is a bug.
 */
'use strict';

/* Every file ported below opens its own scope by reading a global — window.SNAP, window.H3,
 * window.PLAN, window.K — because in the prototype the data was on disk before the first line ran.
 * Here nothing exists until boot() has answered. So each scope is pushed onto this list and run, in
 * order, by init(). That is the one structural change made to the ported code: an IIFE became a
 * push and its `})();` became a `});`. Nothing inside any of them moved.
 */
const PAI_LOAD = [];

/* THE TEN GLOBALS, AND THE SHAPE OF EACH. Nothing else on this page is global.
 *
 * They exist because every module below was ported from a prototype that read its data off disk
 * before the first line ran (see the note above), and they are written here in one place because a
 * global whose shape is only discoverable by reading the code that writes it is how the page came
 * to assert, for a week, that live tiles were off on a node whose keeper had turned them on.
 *
 *   window.SNAP      what boot() fetched, normalised: { issues, health, base:{captured_utc}, rho,
 *                    funnel, peer, fixture }. `issues` is GET /issues' whole body.
 *   window.H3        the geometry and the readings the sections draw, assembled in boot() from that
 *                    body: { publication, ladder, nav:{chain,cells,plates}, grain_table, claims,
 *                    radio, settings, source, sensors:[station], metrics, asks,
 *                    node:{lat,lon,name} }. `geometry: null` from the node leaves only the last
 *                    four, and every section that needs the rest says so.
 *   window.SETTINGS  GET /settings — describe()'s { unlocked, runtime:[row], bootstrap:[row] } —
 *                    WITH every unmasked runtime key flattened onto it as KEY: value, so
 *                    window.SETTINGS.MAP_TILES is the string the keeper set. flatSettings() does it,
 *                    in boot(), and it is the only place that knows the endpoint's shape.
 *   window.EARTH     GET /earth, or null. window.TRUST, window.FORECAST: the same, from /trust and
 *                    /forecast.
 *   window.PLAN      GET /place/geojson projected to metres by plan(), or null.
 *   window.PAI       the section contract: { STAGES, register, render, wall, sections, problems,
 *                    has }. docs/PACKS.md is its documentation.
 *   window.K         kit.js: the four card kinds, the signs, esc/fmt, and — after initKit() — the
 *                    bound data S, ISS, ORDER, DIST, LAB, LOC, VIEW, STATE.
 *   window.KH        kit-h3.js: { H, address, grid, km2, edge, sited }. H is window.H3.
 *   window.KN        kit-nav.js: a position and the moves out of it ({ N, where, link, … }).
 *   window.KMAP      kit-map.js: the offline plan ({ map, caption, frameOf, MAX_SPAN_M }).
 *   window.GROUND    the ground module's own frame maths, for the sections that reuse it
 *                    ({ figure, frame, BASES, SIZE }); window.WALL is the wall's ({ render, start,
 *                    field, dial, grain }).
 */

/* ================================================================= kit.js — the four card kinds, the signs, and the two attributes ==== */
/* The four card kinds, the signs, and the attributes the targets are written in terms of.
 *
 * All three directions build from this and nothing else, so they differ in their organising idea
 * and not in their skin. If a rule about what a card IS ends up in a direction's own file, the
 * three have stopped being comparable and the comparison in DIRECTIONS_2026-09.md is worthless.
 *
 * These are drawings. There is no fetch here, nothing is arranged, no button does anything, and
 * every number comes out of window.SNAP — which is node #1 on 6 September replayed through the real
 * engine, plus three synthetic contributions that say so.
 *
 * The four kinds, and the whole of T3:
 *
 *   readout   one number, its unit, its comparison, its source line
 *   stack     the four distances on one scale
 *   series    a trace with an axis, a time origin, the line, and a text alternative
 *   row       a ledger, an index, a unit or a sensor row
 *
 * Everything else on any of the three pages — the hero, the ask, the plan, the satellite, the
 * funnel, the index — is composed from those four plus the sign library. A fifth kind is a STOP.
 *
 * Two attributes carry the two complaints:
 *
 *   data-num / data-cmp   a numeral and the thing it is compared against. Never one without the
 *                         other: where a pack declares no comparison, data-cmp carries the pack's
 *                         own reason and the page prints it, at the same size, in the same place.
 *   data-ref              a link to an id on this page. Every component except the header and the
 *                         hero has one in or one out.
 *
 * One honesty note about `cmp`. The node supplies the line, its source, each cell's source and age,
 * and the sentence's own comparison clause. The COMPARISON MODE — line, normal, ring, region,
 * last_period, none — is a declaration, and in Release 2 it arrives on the contribution. Here the
 * word is chosen from that declaration and the numbers in it are the node's. No arithmetic happens
 * in this file: `cmpText` reads values, it does not derive them.
 */
'use strict';

/* PORTED: the prototype read window.SNAP at load time, because a drawing has its snapshot on disk
 * before the first line runs. Here nothing exists until boot() has answered, so these are bound by
 * initKit(), which the boot sequence calls, and the language is the household's own from /health. */
let S, ISS, ORDER, DIST, LAB, LOC = 'en';

const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* The node already formatted every number it sent; this only sets the places the issue declared. */
const fmt = (v, dp = 0) => (v == null || isNaN(v) ? '—' : Number(v).toFixed(dp));

const sign = (id, cls = '') =>
  `<svg class="sg ${cls}" aria-hidden="true"><use href="static/signs.svg#sign-${id}"/></svg>`;

/* Provenance is a glyph and a word, ink only, square. A fixture is a committed snapshot, so nothing
 * on it was measured just now: `live` is coerced to `cached`, exactly as the node's own page does. */
/* PORTED: the prototype coerced `live` to `cached` because every number in it came off a committed
 * snapshot. This page reads a live node OR a fixture and knows which, so the caller passes the word
 * and this prints it. `?fixture=` is what says `cached` (see lead()). */
const pill = (word, note = '') => {
  if (!word) return '';
  const w = String(word);
  return `<span class="pill prov" title="${esc(note)}">`
    + `<svg class="sg" aria-hidden="true"><use href="static/signs.svg#sign-prov-${esc(w)}"/></svg>`
    + esc(w) + `</span>`;
};

const age = m => m == null ? '' : m < 1 ? 'just now' : m < 60 ? `${Math.round(m)} min ago`
  : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} days ago`;

let seq = 0;
const uid = p => `${p}-${++seq}`;

/* --------------------------------------------------------------------------- the comparison */
/* What a numeral is measured against, in words, from what the node sent. Returns {text, none}. */
function cmpText(o) {
  const { mode, line, unit, dp, other, otherLabel, reason } = o;
  if (mode === 'none' || !mode) {
    return { none: true, text: reason ? `no comparison yet · ${reason}` : 'no comparison yet' };
  }
  if (mode === 'line' && line) {
    /* The line's SOURCE is named once, by the why line under the sentence. Repeating it in every
       column of a stack put twenty-eight words of WHO citation under four numbers and buried the
       one thing the column is for. The comparison is the number; whose number it is, is above. */
    return { none: false, text: `against the line, ${fmt(line.value, dp)} ${unit}` };
  }
  if (other != null) {
    return { none: false, text: `against ${otherLabel}, ${fmt(other, dp)} ${unit}` };
  }
  return { none: true, text: 'no comparison yet · nothing at that distance to compare with' };
}

/* --------------------------------------------------------------------------- 1 · readout */
function readout(o) {
  const id = o.id || uid('readout');
  const c = o.cmp || { none: true, text: 'no comparison yet' };
  return `<div class="readout${o.unplaced ? ' unplaced' : ''}" data-kind="readout"`
    + ` data-component="${esc(o.component || 'readout')}" id="${esc(id)}"`
    + `${o.ref ? ` data-ref="${esc(o.ref)}"` : ''}>`
    /* PORTED: .lab is shouted, and a readout's title can be a PACK's own words — the water pack's
     * "Dissolved solids" arrives as a contribution. `µ` uppercases to `M`, so the words go in .said
     * and only the page's own separator is left to shout. */
    + `<div class="lab"><span class="said">${esc(o.title)}</span>`
    + `${o.pack ? ` · <span class="said">${esc(o.pack)}</span>` : ''}</div>`
    /* data-num is a KEY, not a label: `water.tds`, not "Dissolved solids". A gate that walks
     * [data-num] has to be able to tell which issue a numeral belongs to, and a title cannot say. */
    + `<div class="v"><span class="num${o.crossed ? ' crossed' : ''}"`
    + ` data-num="${esc(o.num || o.title)}" data-cmp="${esc(c.text)}">`
    + `${esc(fmt(o.value, o.dp))}</span>`
    + `<small>${esc(o.unit || '')}</small></div>`
    + `<div class="cmp${c.none ? ' none' : ''}">${esc(c.text)}</div>`
    + `<div class="src"><span class="said">${esc(o.source || '')}</span>`
    + `${o.age != null ? `<span class="asof">${esc(age(o.age))}</span>` : ''}`
    + `${pill(o.prov)}</div></div>`;
}

/* --------------------------------------------------------------------------- 2 · stack */
/* The four distances, each with its value, what it is measured against, its source and its word.
 * An absent distance says why. Every column links to the source card that stands behind it. */
function stack(key, d, o = {}) {
  const id = o.id || `stack-${key}`;
  const cols = DIST.map(dist => {
    const c = (d.stack || {})[dist];
    const has = c && c.value != null;
    /* A column a PACK filled carries the pack's own unit, decimal places and declared comparison.
     * Water's region is metres below a water table and its room is turbidity in NTU; reading the
     * issue's own unit and line for both painted 4.2 m red for crossing a 1.0 NTU line, which is
     * two different quantities on one scale — the thing a stack exists not to do. */
    const fill = (d.contributions || []).find(x => x.slot === `stack.${dist}` && x.placed !== false);
    const unit = fill ? fill.data.unit : d.unit;
    const dp = fill ? fill.data.dp : d.dp;
    const line = fill ? (fill.data.compare === 'line' ? d.line : null) : d.line;
    const crossed = has && line && c.value > line.value;
    const room = ((d.stack || {}).room || {}).value;
    const cmp = !has ? { none: true, text: `nothing at this distance · ${reasonFor(d, dist)}` }
      : fill ? cmpText({ mode: fill.data.compare, line, unit, dp, reason: fill.data.reason })
        : line ? cmpText({ mode: 'line', line, unit, dp })
          : dist === 'room' || room == null
            ? cmpText({ mode: 'none', reason: `${d.name[LOC]} has no line: ${noLine(d)}` })
            : cmpText({ mode: 'ring', other: room, otherLabel: 'the room', unit, dp });
    return `<div class="col" id="col-${esc(key)}-${dist}"`
      + ` data-ref="src-${esc(key)}-${dist}">`
      + `<div class="k">${esc(LAB[dist])}</div>`
      + `<div class="v"><span class="num${has ? '' : ' none'}${crossed ? ' crossed' : ''}"`
      + ` data-num="${esc(key)}.${dist}" data-cmp="${esc(cmp.text)}">`
      + `${has ? esc(fmt(c.value, dp)) : '—'}</span>`
      + (has ? `<small>${esc(unit || '')}</small>` : '') + `</div>`
      + `<div class="cmp${cmp.none ? ' none' : ''}">${esc(cmp.text)}</div>`
      + (has ? `<div class="src"><span class="said">${esc(c.source)}</span>`
        + `${c.age_minutes != null ? ' · ' + esc(age(c.age_minutes)) : ''}</div>` + pill(c.provenance)
        : '')
      + `</div>`;
  }).join('');
  return `<div class="stack" data-kind="stack" data-component="stack" id="${esc(id)}"`
    + ` role="group" aria-label="${esc(d.name[LOC])} at four distances"`
    + `${o.ref ? ` data-ref="${esc(o.ref)}"` : ` data-ref="band-${esc(key)}"`}>${cols}</div>`;
}

const noLine = d => d.kind === 'context'
  ? 'it informs, it never asks' : 'no threshold has been named for it here';
const reasonFor = (d, dist) => ({
  room: 'no sensor indoors', yard: 'no kit on the wall outside',
  ring: 'no public station reporting', region: 'no model for this point',
}[dist] || 'no source');

/* --------------------------------------------------------------------------- 3 · series */
/* Geometry only: the high and the low set the box, the node supplies every value and the line.
 * A hole in the series is a hole in the line — a run of one reading is a dot, never nothing. */
const runs = (vals, at) => {
  const out = []; let cur = [];
  (vals || []).forEach((v, i) => {
    if (v == null) { if (cur.length) { out.push(cur); cur = []; } return; }
    cur.push(at(v, i));
  });
  if (cur.length) out.push(cur);
  return out;
};

function series(key, d, o = {}) {
  const id = o.id || `series-${key}`;
  const ser = d.series || {};
  const sets = DIST.filter(x => Array.isArray(ser[x]) && ser[x].some(v => v != null));
  if (!sets.length) {
    return `<div class="series" data-kind="series" data-component="series" id="${esc(id)}"`
      + ` data-ref="band-${esc(key)}"><p class="note">The day it just had: nothing recorded yet at `
      + `any distance.</p></div>`;
  }
  const W = 720, H = o.h || 180, pad = { l: 8, r: 8, t: 10, b: 10 };
  const all = sets.flatMap(x => ser[x]).filter(v => v != null);
  const line = d.line ? d.line.value : null;
  const hi = Math.max(...all, line || 0) * 1.1 || 1, lo = Math.min(...all, 0);
  const n = Math.max(...sets.map(x => ser[x].length));
  const X = i => pad.l + (i / Math.max(1, n - 1)) * (W - pad.l - pad.r);
  const Y = v => H - pad.b - ((v - lo) / (hi - lo || 1)) * (H - pad.t - pad.b);
  const dash = { room: '', yard: '4 3', ring: '1 5', region: '6 4' };
  const broken = sets.some(k => runs(ser[k], () => 0).length > 1);
  let s = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="`
    + `${esc(d.name[LOC])}, ${sets.length} traces over 24 hours, ${esc(fmt(lo, d.dp))} to `
    + `${esc(fmt(hi, d.dp))} ${esc(d.unit)}${line != null ? `, the line ${esc(fmt(line, d.dp))}` : ''}`
    + `${broken ? ', broken where nothing was recorded' : ''}">`;
  if (line != null) s += `<line x1="${pad.l}" x2="${W - pad.r}" y1="${Y(line)}" y2="${Y(line)}"`
    + ` stroke="var(--signal-worse)" stroke-dasharray="3 6" stroke-opacity=".8"/>`;
  sets.forEach(k => {
    const op = k === 'room' ? 1 : .55;
    runs(ser[k], (v, i) => [X(i), Y(v)]).forEach(r => {
      s += r.length > 1
        ? `<polyline points="${r.map(p => p.join(',')).join(' ')}" fill="none" stroke="var(--ink)"`
          + ` stroke-width="1.6" vector-effect="non-scaling-stroke"`
          + `${dash[k] ? ` stroke-dasharray="${dash[k]}"` : ''} stroke-opacity="${op}"/>`
        : `<circle cx="${r[0][0]}" cy="${r[0][1]}" r="1.8" fill="var(--ink)" fill-opacity="${op}"/>`;
    });
  });
  s += `</svg>`;
  const legend = sets.map(k =>
    `<span><i class="${k === 'room' ? '' : k === 'ring' ? 'dot' : 'dash'}"></i>${esc(LAB[k])}</span>`)
    .join('');
  // The text alternative sits beside the drawing at every width, not behind it.
  const first = ser[sets[0]].find(v => v != null), last = [...ser[sets[0]]].reverse().find(v => v != null);
  const altCmp = line != null
    ? `against the line, ${fmt(line, d.dp)} ${d.unit} · ${d.line.source}`
    : `no comparison yet · ${noLine(d)}`;
  return `<div class="series" data-kind="series" data-component="series" id="${esc(id)}"`
    + ` data-ref="band-${esc(key)}">`
    + `<div class="ax top"><span>${esc(fmt(hi, d.dp))} ${esc(d.unit)}</span>`
    + `${line != null ? `<span>the line ${esc(fmt(line, d.dp))}</span>` : ''}</div>`
    + s
    + `<div class="ax bot"><span>24 h ago</span><span>now</span></div>`
    + `<p class="alt"><span data-num="${esc(key)}.day" data-cmp="${esc(altCmp)}">`
    + `${esc(LAB[sets[0]])} opened the day at ${esc(fmt(first, d.dp))} and closed it at `
    + `${esc(fmt(last, d.dp))} ${esc(d.unit)}</span> — ${esc(altCmp)}.`
    + `${broken ? ' The line breaks where nothing was recorded.' : ''}</p>`
    + `<div class="legend">${legend}</div></div>`;
}

/* --------------------------------------------------------------------------- 4 · row */
function row(o) {
  const id = o.id || uid('row');
  const qty = (o.qty || []).map(q => q.value == null
    ? `<span class="none">—</span>`
    : `<span data-num="${esc(q.num)}" data-cmp="${esc(q.cmp)}">${esc(q.value)}</span>`).join('');
  const tag = o.href ? 'a' : 'div';
  return `<${tag} class="row ${o.cls || ''}" data-kind="row"`
    + ` data-component="${esc(o.component || 'row')}" id="${esc(id)}"`
    + `${o.ref ? ` data-ref="${esc(o.ref)}"` : ''}`
    + `${o.href ? ` href="${esc(o.href)}"` : ''}`
    + `${o.cols ? ` style="--row-cols:${o.cols}"` : ''}>`
    + (o.left || '')
    + (o.name ? `<span class="name">${esc(o.name)}</span>` : '')
    + (o.state ? `<span class="state${o.state === 'act' ? ' act' : ''}">${esc(o.state)}</span>` : '')
    + (o.line ? `<span class="line said"${o.lineRole ? ` data-role="${esc(o.lineRole)}"` : ''}>`
      + `${esc(o.line)}</span>` : '')
    + (o.signs ? `<span class="signs">${o.signs}</span>` : '')
    + (qty ? `<span class="qty">${qty}</span>` : '')
    + `</${tag}>`;
}

/* --------------------------------------------------------------------- the composites */
const kicker = (key, d) =>
  `<div class="k" data-component="kicker" id="kicker-${esc(key)}" data-ref="band-${esc(key)}">`
  + `<span class="issue" data-role="issue">${esc(d.name[LOC])}</span> `
  + `<span class="state${d.state === 'act' ? ' act' : ''}" data-role="state">${esc(d.state)}</span>`
  + (d.reason_text ? ` <span class="said">· ${esc(d.reason_text[LOC])}</span>` : '') + `</div>`;

/* The numeral inside the sentence is the monument, and it carries its comparison like every other
 * numeral on the page. The node formatted it; this finds it in its own sentence to set it. */
function sentence(key, d, cls = 'big') {
  const s = d.sentence ? d.sentence[LOC] : '';
  const cell = (d.stack || {})[d.headline];
  const n = cell && cell.value != null ? fmt(cell.value, d.dp) : null;
  const crossed = !!(d.line && cell && cell.value != null && cell.value > d.line.value
    && (d.state === 'act' || d.state === 'notable'));
  const cmp = d.line
    ? cmpText({ mode: 'line', line: d.line, unit: d.unit, dp: d.dp })
    : cmpText({ mode: 'none', reason: noLine(d) });
  const marked = n
    ? esc(s).replace(esc(n), `<b class="mono${crossed ? ' crossed' : ''}" data-role="numeral"`
      + ` data-num="${esc(key)}.headline" data-cmp="${esc(cmp.text)}"`
      + ` id="num-${esc(key)}">${esc(n)}</b>`)
    : esc(s);
  return `<p class="${cls}" data-component="sentence" data-role="sentence" id="sentence-${esc(key)}"`
    + ` data-ref="stack-${esc(key)}">${marked}</p>`;
}

const why = (key, d) => d.line
  ? `<p class="why" data-component="why" id="why-${esc(key)}" data-ref="num-${esc(key)}">`
    + `${esc(d.line.source)} · ${esc(fmt(d.line.value, d.dp))} ${esc(d.line.unit || d.unit)}</p>`
  : `<p class="why" data-component="why" id="why-${esc(key)}" data-ref="sentence-${esc(key)}">`
    + `No line: ${esc(noLine(d))}</p>`;

/* The ask, and the words that stand in for one. T1 asks for the open ask OR "nothing to do", and
 * the shipped page has neither when there is nothing to do — it renders a hidden div. A household
 * that has to infer "nothing to do" from an absence has not been told anything. */
/* PORTED: `ref` is new. The strip was only ever drawn in the lead, where `sentence-<key>` is on the
 * page; the act section draws one per issue with an open ask, and on a node whose headline is some
 * other issue that id does not exist — a component pointing at nothing, which is what T5 counts. */
function ask(key, d, ref) {
  const a = (d.open_asks || [])[0];
  const id = `ask-${key}`;
  if (!a) {
    /* Two different absences, and saying "nothing to do" for both is a contradiction a reader can
     * see: the kicker's own reason for `notable` is "over the line, and nobody has been asked to do
     * anything", and a strip underneath it reading "Nothing to do" says the opposite of the line
     * above it. An issue that is over its line with no rule asking for anything is not quiet — it
     * is unattended, and the page should say which. */
    const unattended = d.state === 'notable' || d.state === 'act';
    return `<div class="ask none" data-component="askStrip" data-role="ask" id="${esc(id)}"`
      + ` data-ref="${esc(ref || `sentence-${key}`)}"><div class="what">`
      + (unattended ? 'Nothing has been asked.' : 'Nothing to do.')
      + `<small>${esc(d.name[LOC])} is ${esc(d.state)}`
      + (unattended ? ', and no rule here asks anybody to do anything about it.'
        : ', and no reading here has asked for anything.')
      + `</small></div></div>`;
  }
  return `<div class="ask" data-component="askStrip" data-role="ask" id="${esc(id)}"`
    + ` data-ref="${esc(ref || `sentence-${key}`)}">`
    + `<div class="what">${esc(a.text ? String(a.text).split('\n')[0] : a.says[LOC])}`
    + `<small>${esc(a.how[LOC])}</small></div>`
    + `<button type="button" class="go">I did this</button></div>`;
}

/* PORTED: `plan` is not an id on this page; the figure the caption belongs to is the ground map.
 * A node with no coordinates yet has no cell and no caption, and prints neither. */
const stamp = () => {
  const c = (S.health || {}).cell;
  const said = c ? c.caption : '';
  return said ? `<div class="stamp" data-component="stamp" id="stamp"`
    + ` data-ref="ground-figure">${esc(said)}</div>` : '';
};

/* PORTED: the prototype added eight hours because its fixture is node #1 and node #1 is on WITA. A
 * reading belongs to the place it was taken in, and GET /health publishes NODE_TZ for exactly this.
 * A node with no zone set says UTC rather than drawing the viewer's clock as if it were the node's. */
const asof = () => {
  const t = new Date(S.issues.as_of);
  const tz = S.health && S.health.tz;
  let when = `${String(t.getUTCHours()).padStart(2, '0')}:`
    + `${String(t.getUTCMinutes()).padStart(2, '0')} UTC`;
  if (tz) {
    try {
      when = new Intl.DateTimeFormat('en-GB', { timeZone: tz, hour: '2-digit', minute: '2-digit',
        hour12: false }).format(t);
    } catch { /* a zone this browser does not know: UTC, said as UTC */ }
  }
  return `<span class="asof" data-role="asof" id="asof">As of ${esc(when)} · `
    + `${esc(String(S.base.captured_utc || '').slice(0, 10))}</span>`;
};

/* rho as a row of rings, answered first, with the caption naming reported against observed. */
/* PORTED: `ref` is new, for the same reason the ask strip's is. The row's link out was always the
 * funnel, and the wall has no funnel on it. */
function rhoRow(small, ref) {
  /* GET /rho may be slow, refused or absent, and this is called from the wall, which nobody is
   * standing at. A dereference here took the whole wall down before innerHTML was ever assigned. */
  if (!S.rho) {
    return `<p class="note" data-component="rhoRow" id="rho" data-ref="${esc(ref || 'header')}">`
      + `This node has not said how many of its asks were answered: GET /rho did not come back.</p>`;
  }
  const r = S.rho, total = r.alerts_act, closed = r.acted;
  let s = '';
  for (let i = 0; i < total; i++) s += sign(i < closed ? 'rho-closed' : 'rho-open', i < closed ? 'closed' : '');
  /* The row is a texture of signs and the CAPTION is the readable part of it, so the caption is
   * what carries the role and what the three-metre floor is measured against. A sign is measured
   * against --sign-floor; a cap height is measured against a distance. */
  return `<div class="rho${small ? ' small' : ''}" data-component="rhoRow"`
    + ` id="rho" data-ref="${esc(ref || 'funnel')}" role="img" aria-label="${closed} of ${total} asks answered">${s}</div>`
    + `<p class="note" data-role="rho" data-num="rho"`
    + ` data-cmp="against the ${total} asks this node sent in 30 days">`
    + `${closed} of ${total} asks answered · median ${r.median_minutes} min</p>`;
}

/* The funnel: four stages, four latencies and the 2x2. Counted, never sized by a gauge — each bar
 * is a share of the first stage and the number is beside it. */
/* PORTED: the funnel was one of the prototype's three synthetic contributions — the stage split and
 * the 2x2 were invented for the drawing. No endpoint on this node computes them, so the caller asks
 * whether S.funnel is there before drawing it, and the act section stands without it. */
function funnel() {
  const f = S.funnel, top = f.stages[0].n;
  const lat = f.latencies_minutes;
  const gaps = ['', 'reached_to_acknowledged', 'acknowledged_to_deployed', 'deployed_to_closed'];
  const mins = m => m == null ? '' : m < 120 ? `${m} min` : `${Math.round(m / 60)} h`;
  const rows = f.stages.map((st, i) =>
    `<div class="st"><span class="k">${esc(st.label[LOC])}</span>`
    + `<span class="bar"><i style="width:${(100 * st.n / top).toFixed(1)}%"></i></span>`
    + `<span class="lat"><span data-num="funnel.${st.key}"`
    + ` data-cmp="against ${top} asks reached">${st.n}</span>`
    + `${gaps[i] ? ` · +${esc(mins(lat[gaps[i]]))}` : ''}</span></div>`).join('');
  const m = f.matrix;
  const cell = (n, k) => `<div><b data-num="funnel.${k}" data-cmp="against ${top} asks reached">`
    + `${n}</b></div>`;
  return `<div class="funnel" data-component="funnel" id="funnel" data-ref="rho">`
    + rows
    + `<div class="m2">`
    + `<div class="h"></div><div class="h">the reading came back</div><div class="h">still over</div>`
    + `<div class="h">answered</div>${cell(m.answered_cleared, 'answered_cleared')}`
    + `${cell(m.answered_still, 'answered_still')}`
    + `<div class="h">not answered</div>${cell(m.unanswered_cleared, 'unanswered_cleared')}`
    + `${cell(m.unanswered_still, 'unanswered_still')}</div>`
    + `<p class="note">${esc(f.source)}. ${pill(f.provenance)}</p></div>`;
}

/* A peer node: another node's number, and the sentence saying what it must never become. */
function peerRow() {
  const p = S.peer;
  return `<div class="peer" data-component="peers" id="peer" data-ref="rho">${sign('machine')}`
    + `<div><b>${esc(p.node)}</b>`
    + `<span class="note"><span data-num="peer.pm25" data-cmp="no comparison yet · a peer is never `
    + `compared with this node's own reading">${esc(fmt(p.value.value, p.value.dp))} `
    + `${esc(p.value.unit)}</span> ${pill(p.value.provenance)} · heard ${esc(age(p.heard_minutes_ago))}`
    + ` · about ${esc(String(p.km))} km away</span>`
    + `<span class="note">${esc(p.never[LOC])}</span></div></div>`;
}

/* A slot the vocabulary does not contain. It lands on the page with the pack's name on it. */
function unplaced(c) {
  return readout({
    id: `unplaced-${c.pack}`, num: `${c.pack}.unplaced`, component: 'unplaced', unplaced: true,
    pack: c.pack,
    title: c.data.title[LOC], value: c.data.value, unit: c.data.unit, dp: c.data.dp,
    source: `${c.pack} asked for ${c.slot}, which this page has no place for`,
    prov: c.provenance, ref: 'band-water',
    cmp: cmpText({ mode: 'none', reason: c.data.reason }),
  });
}

/* A contribution a pack made to a slot that does exist. */
function contribution(c, key) {
  if (c.slot !== 'band.readout') return '';
  return readout({
    id: `contrib-${c.pack}-readout`, num: `${key}.${c.data.metric || 'readout'}`,
    component: 'readout', pack: c.pack,
    title: c.data.title[LOC], value: c.data.value, unit: c.data.unit, dp: c.data.dp,
    source: c.data.source, prov: c.provenance, ref: `stack-${key}`,
    cmp: cmpText({ mode: c.data.compare, reason: c.data.reason }),
  });
}

/* --------------------------------------------------------------------- the wireframe views */
const WF = {
  network: [
    ['What leaves this house', ['t', 's', 'box:figure', 'cap:six facts, in and out', 'bar', 'bar']],
    ['Other nodes', ['t', 'bar', 'bar', 'cap:the peer, display-only', 'bar']],
    ['The machine in the corner', ['t', 'bar', 'bar', 'bar', 'bar']],
    ['The Fab City Index', ['t', 'cols:4', 'bar']],
  ],
  setup: [
    ['How this node was told to behave', ['t', 's']],
    ['Issues, in order', ['cap:drag order, saved as NODE_ISSUES', 'ctl', 'ctl', 'ctl', 'ctl', 'ctl', 'bar']],
    ['Sources · Alerts · Packs · Keys · The tree', ['bar', 'ctl', 'bar', 'ctl', 'bar', 'ctl']],
    ['Open this on another screen', ['cap:http://<node>:8080/', 'bar']],
  ],
  arrange: [
    ['Arrange', ['cap:a way out that loses nothing', 'ctl']],
    ['The bands, in order', ['bar:ctl', 'bar:ctl', 'bar:ctl', 'bar:ctl', 'bar:ctl']],
    ['Hidden', ['cap:findable, and reset asks', 'ctl']],
  ],
};

function wireframe(view) {
  const spec = WF[view] || [];
  return `<div class="wf" data-component="wireframe" id="wf-${esc(view)}" data-ref="wf-note">`
    + spec.map(([title, parts]) => `<div class="box"><div class="cap">${esc(title)}</div>`
      + parts.map(p => {
        const [k, arg] = p.split(':');
        if (k === 'cap') return `<div class="cap">${esc(arg)}</div>`;
        if (k === 'cols') return `<div class="cols">`
          + Array.from({ length: +arg }, () => `<div class="ctl"></div>`).join('') + `</div>`;
        if (k === 'ctl') return `<div class="ctl"></div>`;
        if (k === 'box') return `<div class="ctl" style="height:120px"></div>`;
        if (k === 'bar' && arg === 'ctl') return `<div style="display:grid;grid-template-columns:1fr auto auto auto;gap:8px;align-items:center">`
          + `<div class="bar"></div><div class="ctl" style="width:34px;height:30px"></div>`
          + `<div class="ctl" style="width:34px;height:30px"></div>`
          + `<div class="ctl" style="width:34px;height:30px"></div></div>`;
        return `<div class="bar ${k === 'bar' ? '' : k}"></div>`;
      }).join('') + `</div>`).join('')
    + `<p class="note" id="wf-note" data-ref="wf-${esc(view)}">Drawn, not built. Grey is where text `
    + `goes, an outline is where a control goes. This view is Phase 2's; the drawing says where it `
    + `lives and how it reads.</p></div>`;
}

/* --------------------------------------------------------------------- the page's own state */
/* PORTED: a direction captured its views with ?view=, because a drawing is captured and never
 * navigated. This page is navigated, so the view is the hash — #now, #network, #setup, #wall — the
 * way the page it replaces routed, and ?view= is still read so a render can be asked for one
 * directly. ?state= stays: it is how the empty node and the refused page are captured. */
let VIEW = 'now';
let STATE = 'populated';
function readView() {
  const q = new URLSearchParams(location.search);
  const h = (location.hash || '').replace(/^#/, '');
  VIEW = h || q.get('view') || 'now';
  STATE = q.get('state') || 'populated';
  if (window.K) Object.assign(window.K, { VIEW, STATE });
}

/* The empty node and the refused page, from the same drawing. A direction has to answer for the
 * tester's first hour and for the stranger with no token, and a drawing that only ever shows a full
 * node is a drawing that has not been asked the hard question. */
function emptySnapshot() {
  for (const k of Object.keys(ISS)) {
    const d = ISS[k];
    d.state = 'none'; d.open_asks = []; d.contributions = [];
    d.stack = { room: null, yard: null, ring: null, region: null };
    d.series = { room: null, yard: null, ring: null, region: null };
    d.readouts = []; d.provenance = [];
    d.reason_text = { en: 'no source yet', id: 'belum ada sumber', es: 'aún no hay fuente' };
    d.sentence = { en: emptyLine(k), id: emptyLine(k), es: emptyLine(k) };
  }
  S.issues.headline = ORDER[0];
  S.rho = { window_days: 30, alerts_act: 0, acted: 0, rho: null, median_minutes: null };
  S.funnel = { ...S.funnel, stages: S.funnel.stages.map(s => ({ ...s, n: 0 })),
    matrix: { answered_cleared: 0, answered_still: 0, unanswered_cleared: 0, unanswered_still: 0 } };
  S.peer = null;
}
const emptyLine = k => ({
  air: 'No air sensor here yet, and no model for this point.',
  heat: 'No temperature and humidity here yet.',
  coast: 'No marine model for this point yet.',
  land: 'No satellite record yet for this square.',
  water: 'No water probe here yet.',
}[k] || 'Nothing here yet.');

const REFUSED = {
  household: 'This node is not sharing its readings with the network.',
  node: "this node is set to SHARE_LEVEL=off, so /issues answers only this machine or a request "
    + "carrying a token. Set SHARE_LEVEL to open in the dashboard's Set up view to let anything on "
    + "your network read it.",
  todo: 'Ask whoever set this node up to turn sharing on, or open this page on the machine the node '
    + 'runs on.',
};

function refusedPage() {
  return `<div class="refused" data-component="refused" id="refused" data-ref="header">`
    + `<p class="big" data-role="sentence">${esc(REFUSED.household)}</p>`
    + `<p class="why">${esc(REFUSED.node)}</p>`
    + `<p class="note">${esc(REFUSED.todo)}</p></div>`;
}

/* Every module reads these. The functions are bound now; the data and the view are bound by
 * initKit() once boot() has answered, because until then there is nothing to bind. */
window.K = { esc, fmt, sign, pill, age, uid, cmpText,
  readout, stack, series, row, kicker, sentence, why, ask, stamp, asof, rhoRow, funnel,
  peerRow, unplaced, contribution, wireframe, refusedPage, noLine, reasonFor, REFUSED };

/* The one place the page's data is bound. boot() has answered by now; nothing above this line ran
 * against a global that was not there. */
function initKit() {
  S = window.SNAP;
  /* the household's own language, off /health, which answers at every share level. /issues carries
     every sentence in all three and no way to choose between them. */
  LOC = ((S.health || {}).locale) || 'en';
  ISS = S.issues.issues;
  ORDER = S.issues.order;
  DIST = S.issues.distances;
  LAB = S.issues.labels[LOC] || S.issues.labels.en;
  readView();
  if (STATE === 'empty') emptySnapshot();
  Object.assign(window.K, { S, ISS, ORDER, DIST, LAB, LOC, VIEW, STATE });
}

/* ================================================================= kit-h3.js — an address and a grid ==== */
/* The H3 parts, shared by D, E and F, and by nothing else.
 *
 * `kit.js` holds the four card kinds and knows nothing about grids. This holds what the three
 * H3-navigated directions need on top: an address, a cell drawn inside its parent, a grid with
 * things placed in it, and the three sentences H3 forces the page to be honest about. It adds no
 * fifth card kind — a grid is a drawing inside a card, the way the plan and the day already are.
 *
 * Every id, edge, area and path comes from `h3.js`, which `make-h3.mjs` computed with h3-js from
 * the committed fixture's own coordinates. Nothing here knows what a hexagon is; it places paths
 * somebody else projected, which is the same division the node's dashboard already keeps with
 * `kilometre-cells.json`.
 *
 * THREE THINGS H3 MAKES THE PAGE SAY, and all three are measured rather than asserted:
 *
 *   1. A cell is not the thing. The node's three indoor sensors carry ONE coordinate, so they are
 *      in one cell at every resolution down to 15. H3 cannot tell the room from the wall outside
 *      here; custody can, and does. A page that navigates by cell has to say where the grid stops
 *      answering.
 *   2. Containment is exact in the index and approximate on the ground. Two of the seven res-9
 *      children of this node's cell reach 6 m past their own parent's furthest vertex, and all
 *      seven index to it exactly. A page that moves by parent and child should show that, not
 *      quietly round it off.
 *   3. The four distances are not four resolutions, and two of them are the wrong way round. The
 *      cell that contains the ring is res 4, 26 km to an edge; the cell that contains "the region"
 *      is res 5, 9.9 km. The ring is the bigger of the two. That is not a drawing problem — it is
 *      the vocabulary disagreeing with the geometry, and it was invisible until the grid was drawn.
 */
/* Wrapped, because these are classic scripts sharing one script scope: `kit.js` declares `esc` at
 * top level and a second top-level `const esc` here is "Identifier 'esc' has already been declared"
 * — which, being a parse error, takes this whole file with it and leaves `window.KH` undefined. */
PAI_LOAD.push(function () {
'use strict';

const H = window.H3;
const { esc, fmt, pill, row, readout, cmpText, sign } = window.K;

/* ------------------------------------------------------------------ reading a cell out loud */
const km2 = m2 => m2 >= 1e6 ? `${(m2 / 1e6).toFixed(m2 >= 1e7 ? 0 : 2)} km²`
  : `${Math.round(m2).toLocaleString()} m²`;
const edge = m => m >= 1000 ? `${(m / 1000).toFixed(m >= 10000 ? 0 : 1)} km` : `${Math.round(m)} m`;

/* An H3 id is fifteen characters and a household will never read it as a word. It is still the one
 * thing that makes a reading citable by anybody else, so it is printed in full, in the mono, once
 * per object — never repeated, never truncated into something that looks like a different id. */
const address = (id, res) =>
  `<span class="addr mono"><span class="res">res ${res}</span> ${esc(id)}</span>`;

/* PORTED: frame() is gone with the drawing it was for. */
/* ------------------------------------------------------------------ a grid with things in it */
/* Cells, and what is read in them. A cell that holds nothing is drawn and left empty rather than
 * dropped: "no station is reading there" is the answer to half the questions this page exists for.
 *
 * State is weight, fill and dash — never hue. The settled vocabulary: this node's own cell carries
 * the heavier stroke, a cell somebody else reads in carries a fill, a cell nobody reads in carries
 * a hairline.
 */
function grid(draw, opts = {}) {
  const own = new Set(opts.own || []);
  const read = new Set(opts.read || []);
  const box = draw.box;
  const cells = draw.cells.map(c => {
    const isOwn = own.has(c.id), isRead = read.has(c.id);
    return `<path d="${c.d}" fill="var(--cells)"`
      + ` fill-opacity="${isOwn ? 0.18 : isRead ? 0.07 : 0}"`
      + ` stroke="var(--ink)" stroke-opacity="${isOwn ? 0.7 : isRead ? 0.4 : 0.18}"`
      + ` stroke-width="${isOwn ? 2.5 : isRead ? 1.5 : 1}"`
      + `${isOwn || isRead ? '' : ' stroke-dasharray="4 4"'}><title>${esc(c.id)}</title></path>`;
  }).join('');
  const pts = (draw.points || []).map(p =>
    `<circle cx="${p.x}" cy="${p.y}" r="${p.local ? 5.5 : 3.5}"`
    + ` fill="${p.local ? 'var(--cells)' : 'var(--ground)'}" stroke="var(--ink)"`
    + ` stroke-width="${p.local ? 2 : 1.4}"><title>${esc(p.name || p.sensor_id)} · `
    + `${p.km == null ? 'distance unknown' : `${esc(String(p.km))} km`}</title></circle>`).join('');
  return `<svg class="hexgrid" viewBox="0 0 ${box} ${box}" role="img"`
    + ` aria-label="${esc(opts.label || 'the grid around this node')}">`
    + `<g class="cells">${cells}</g><g class="pts">${pts}</g></svg>`;
}

/* PORTED: rung(), the four HONEST sentences and leaving() are gone. They read h3.js fields a build
 * step computed for the drawings — truncation, disk, rungs, leaves, ring_reach_km — which GET
 * /issues does not publish, and nothing on this page called them. Code that reads a field the node
 * never sends is a trap, not a spare part.
 */
/* Has this node been sited? /health publishes lat and lon as float(os.getenv("NODE_LAT", 0) or 0),
 * so absent and unset both arrive as exactly 0 — the test is "both falsy", and the only place it
 * misreads is within about 55 m of where the equator meets the prime meridian, which is open water.
 *
 * It lives here, on the kit every module already reads, because it was private to the ground module
 * and the other three surfaces that draw a distance did not have it: the stations printed each
 * neighbour's distance from the Gulf of Guinea as fact, the grain line counted stations in a cell in
 * that water, the wall drew nineteen cells of it, and the claims were centred on it. One predicate,
 * read by all four. */
const sited = () => !!(H.node.lat || H.node.lon);

window.KH = { H, address, grid, km2, edge, sited };

});

/* ================================================================= kit-nav.js — a position, and the moves out of it ==== */
/* Navigation, when navigation is the grid. Shared by G, H and I, and by nothing else.
 *
 * `kit.js` holds the four card kinds. `kit-h3.js` holds an address, a frame and a grid, which D, E
 * and F hang off a page that is still a document. This holds the part those three do not have: a
 * position, and the moves out of it.
 *
 * THE WHOLE VOCABULARY OF MOVEMENT, and there is no other:
 *
 *   out      cellToParent          one resolution coarser, seven cells become one
 *   in       cellToChildren        one resolution finer, this cell becomes seven
 *   across   gridDisk(cell, 1)     the six that share an edge with this one
 *   home     latLngToCell          back to the cell this node stands in, at this resolution
 *
 * There is no back button, no breadcrumb of its own and no zoom slider, because each of those is a
 * second way of saying one of the four. The address in the bar is the H3 index, and the query string
 * is `?cell=<index>` — so a reader who copies the URL has copied a place, and a reader who reads
 * the URL out loud has said something another node can resolve exactly. That is the argument for
 * navigating this way at all: the address is portable and the four distances are not.
 *
 * WHAT A NODE WOULD PUBLISH. Not this file's eleven plates: one. The plate the reader is standing
 * on is 3.0 kB of JSON — the cell, the two steps around it, each one's parent, neighbours, area and
 * contents — and every move asks for the next one. `app/ground.py` already computes all of it
 * (latlng_to_cell, grid_disk, cell_to_children); what it does not do is publish it per cell.
 *
 * WHAT IT CANNOT DO, said on the page and not only here:
 *   · the plate ends. Two steps out from what the node published, there is no next cell — not
 *     because the grid stops but because this node has not been asked for it. A page that drew a
 *     door there would be drawing the planet.
 *   · a cell is not custody. At the grain a street is drawn at, this house's cell holds two of
 *     somebody else's sensors, and no amount of resolution fixes that: "mine" is not a place.
 */
PAI_LOAD.push(function () {
'use strict';

const H = window.H3;
const { esc, fmt, pill } = window.K;
const { address, km2, edge } = window.KH;
const N = H.nav;

/* ------------------------------------------------------------------ where the reader is */
const Q = new URLSearchParams(location.search);

/* A direction names the resolution it opens at; the reader's own position wins over it. An id in
 * the query that this node never published is not an error to hide — it is the honest answer "that
 * is not a place I was told about", and the page says so. */
function where(defaultRes) {
  const asked = Q.get('cell');
  const res = Math.max(N.res_min, Math.min(N.res_max, +(Q.get('res') || defaultRes || 8)));
  const id = asked || N.chain[res];
  return { id, known: !!N.cells[id], res: N.cells[id] ? N.cells[id].res : res, asked: !!asked };
}

/* Every link keeps the view and the state it was pressed in. A wall that navigated itself back to
 * the Now view on the first press would be a wall nobody can use. */
function link(id, extra = {}) {
  const q = new URLSearchParams(location.search);
  q.set('cell', id);
  for (const [k, v] of Object.entries(extra)) v == null ? q.delete(k) : q.set(k, v);
  return '?' + q.toString();
}

/* ------------------------------------------------------------------ reading the plate */
const cell = id => N.cells[id] || null;
const plate = res => N.plates[res];

/* The children of a cell are the cells one plate finer whose parent is this one. They are not
 * stored: storing seven ids per cell for eleven resolutions was 25 kB of a file that says the same
 * thing twice, and the plate below already carries every `parent`. */
function childrenOf(id) {
  const c = cell(id);
  if (!c || c.res >= N.res_max) return [];
  return plate(c.res + 1).cells.filter(k => (N.cells[k] || {}).parent === id);
}

const sensorsIn = id => ((cell(id) || {}).sensors || []).map(i => H.sensors[i]);

/* Everything read inside a cell, as flat rows: a station, what it measures, and its 15-minute mean.
 * Nothing is averaged across stations. Two stations in one cell are two rows, because the whole
 * reason to draw cells is that they are not one number — and a mean of two strangers' sensors is a
 * number nobody measured. */
function readingsIn(id) {
  const out = [];
  for (const s of sensorsIn(id)) {
    for (const [metric, r] of Object.entries(s.read || {})) {
      out.push({ sensor: s, metric, ...r });
    }
  }
  return out.sort((a, b) => (a.sensor.local === b.sensor.local ? 0 : a.sensor.local ? -1 : 1)
    || a.metric.localeCompare(b.metric));
}

/* ------------------------------------------------------------------ the address bar */
/* Out, in, across and home, and the address between them. A move the node did not publish is drawn
 * as a dead control with the reason on it rather than left off: "there is nothing finer here" and
 * "I was not told about that" are different sentences, and a household deserves the second one. */
function bar(id, opts = {}) {
  const c = cell(id);
  if (!c) {
    return `<div class="navbar" id="navbar" data-component="navbar" data-ref="plate">`
      + `<div class="here"><span class="unknown">This node was not told about that cell.</span>`
      + `<div class="sub">${address(id, '?')}</div></div>`
      + `<a class="mv home" href="${link(N.chain[opts.res || 8])}">back to this node’s own cell</a>`
      + `</div>`;
  }
  const kids = childrenOf(id);
  const up = c.parent;
  const home = N.chain[c.res];
  const sensors = sensorsIn(id).length;
  return `<div class="navbar" id="navbar" data-component="navbar" data-ref="plate">`
    + (up
      ? `<a class="mv out" href="${link(up)}" data-move="out"><span class="cap">out</span>`
        + `<span class="to">resolution ${c.res - 1} · ${esc(km2(N.cells[up].area_m2))}</span></a>`
      : `<span class="mv out off"><span class="cap">out</span><span class="to">${c.parent_outside
        ? 'not published: the plate ends here' : 'the coarsest this node publishes'}</span></span>`)
    + `<div class="here" id="here">`
    + `<div class="a">${address(id, c.res)}</div>`
    + `<div class="sub"><span data-num="cell.area" data-cmp="against ${esc(km2(H.ladder[c.res]
      .own_area_m2))}, this node’s own cell at this resolution">${esc(km2(c.area_m2))}</span>`
    + ` · ${esc(edge(c.edge_m))} to an edge`
    + (id === home ? ' · this node stands here' : '')
    + (c.pentagon ? ' · a pentagon: one of the twelve, and it has five neighbours' : '')
    + `</div></div>`
    + (kids.length
      ? `<a class="mv in" href="${link(kids.find(k => (cell(k).sensors || []).length)
        || kids[0])}" data-move="in"><span class="cap">in</span>`
        + `<span class="to">${kids.length} of ${c.children_total} children · resolution `
        + `${c.res + 1}</span></a>`
      : `<span class="mv in off"><span class="cap">in</span><span class="to">${c.res >= N.res_max
        ? `resolution ${N.res_max} is as fine as this node publishes`
        : 'not published: the plate ends here'}</span></span>`)
    + `<div class="across" role="group" aria-label="the cells around this one">`
    + `<span class="cap">across</span>`
    + (c.neighbours.length
      ? c.neighbours.map((n, i) => {
        const nc = cell(n), has = (nc.sensors || []).length;
        return `<a class="nb${has ? ' has' : ''}" href="${link(n)}" data-move="across"`
          + ` title="${esc(n)}">${i + 1}${has ? `<i>${has}</i>` : ''}</a>`;
      }).join('')
      : `<span class="none">the plate ends here</span>`)
    + (c.neighbours.length < c.neighbours_total
      ? `<span class="none">${c.neighbours_total - c.neighbours.length} of `
        + `${c.neighbours_total} not published</span>` : '')
    + `</div>`
    + (id === home ? '' : `<a class="mv home" href="${link(home)}">home</a>`)
    + `<span class="count">${sensors
      ? `${sensors} ${sensors === 1 ? 'station' : 'stations'} here` : 'nothing reads here'}</span>`
    + `</div>`;
}

/* ------------------------------------------------------------------ the plate, drawn */
/* One drawing, three weights: where you are, where you can go, and what the node published around
 * it. State is weight, fill and dash — never hue, which is the rule the layer settled and the only
 * one that survives a wall at three metres in the dark. */
function plateSvg(id, opts = {}) {
  const c = cell(id);
  const res = c ? c.res : (opts.res || 8);
  const d = plate(res).draw;
  const kids = c ? new Set(c.neighbours) : new Set();
  const paths = d.cells.map(x => {
    const me = x.id === id, nb = kids.has(x.id);
    const has = ((cell(x.id) || {}).sensors || []).length;
    return `<path d="${x.d}" fill="var(--cells)"`
      + ` fill-opacity="${me ? 0.2 : has ? 0.08 : 0}"`
      + ` stroke="var(--ink)" stroke-opacity="${me ? 0.85 : nb ? 0.45 : 0.18}"`
      + ` stroke-width="${me ? 3 : nb ? 1.5 : 1}"`
      + `${me || nb ? '' : ' stroke-dasharray="4 4"'}><title>${esc(x.id)}</title></path>`;
  }).join('');
  const pts = (d.points || []).map(p =>
    `<circle cx="${p.x}" cy="${p.y}" r="${p.local ? 5.5 : 3.5}"`
    + ` fill="${p.local ? 'var(--cells)' : 'var(--ground)'}" stroke="var(--ink)"`
    + ` stroke-width="${p.local ? 2 : 1.4}"><title>${esc(p.name || p.sensor_id)}</title></circle>`)
    .join('');
  return `<svg class="hexgrid" viewBox="0 0 ${d.box} ${d.box}" role="img"`
    + ` aria-label="${esc(opts.label || `resolution ${res}: the cell this page is standing in, the `
      + `${c ? c.neighbours.length : 0} published around it, and every station inside them`)}">`
    + `<g class="cells">${paths}</g><g class="pts">${pts}</g></svg>`;
}

/* ------------------------------------------------------------------ what the moves cost to say */
const NAV_HONEST = {
  plateEnds: () => `This node published ${N.steps} steps around itself at each of `
    + `${N.res_max - N.res_min + 1} resolutions — ${N.cell_count} cells, ${'3.0'} kB for the one `
    + `you are standing on. Past that edge the grid carries on and this node does not: a dashboard `
    + `that drew a door there would be drawing the planet.`,
  /* The floor, as a position rather than a paragraph. */
  floor: () => `Everything finer than resolution ${H.settings.PRESENCE_RES_FLOOR} is this machine’s `
    + `own. That is the floor no settings box may pass — app/main.py — and this node announces `
    + `itself at resolution ${H.settings.RETICULUM_PRESENCE_RES}, `
    + `${km2(H.radio.area_m2)}, which is the whole of what a stranger on the radio learns `
    + `about where it is.`,
  perStation: () => `Each number here is one station’s own 15-minute mean. GET /issues publishes `
    + `the street as a single fenced median and never a value per station, so a page that navigates `
    + `by cell is asking the node to publish something it currently does not.`,
};

window.KN = { N, where, link, cell, plate, childrenOf, sensorsIn, readingsIn, bar, plateSvg,
  NAV_HONEST };

});

/* ================================================================= kit-map.js — the ground under the grid ==== */
/* The ground under the grid: the real place, with the cells laid on top of it.
 *
 * Tomas read direction H and said the hexagons feel abstract — keep a map under the scales, with
 * the cells over the place the node actually stands in. This draws that, and it is the same drawing
 * the node's own dashboard already makes: `planetai-design/data/place.geojson`, which is
 * **OpenStreetMap** (ODbL) as the `place` pack keeps it on disk, plus the buildings one satellite
 * pass found that OSM does not have.
 *
 * NO TILE SERVER, and that is not a shortcut. A slippy map means a node fetching tiles, and a
 * household node that fetches tiles tells somebody else's machine where it is every time anybody
 * opens the page. Everything drawn here was fetched once by a pack and is on the node's own disk.
 * For photographic ground there are four real Sentinel passes of this same place, also on disk —
 * they are the satellite section, not a backdrop.
 *
 * IT FOLLOWS NODE_DASHBOARD_PLAN_SPEC.md, WHICH IS ALREADY SETTLED. Seven rules, and the four that
 * bite here:
 *
 *   1  project every vertex, never resample, never simplify. `make-plan.mjs` did it in the node's
 *      own local formula; this places what it computed. geoPath was measured dropping corners from
 *      855 of 2,713 buildings on this exact dataset.
 *   2  draw back to front: ground, kilometre edge, green, roads, buildings, satellite-only
 *      buildings, uses, the cells, the node. The grid sits OVER the town, not under it — the index
 *      is a thing laid on a place and the drawing should say so.
 *   3  colour is a role and comes from a token: buildings `--ink` at .82, roads `--ink`, green
 *      `--rings`, satellite-only `--satellite-only`, cells and the node `--cells`. Orange means
 *      what only the satellite knows, and nothing else.
 *   5  two of node #1's buildings are points, not footprints. They are counted and not drawn: the
 *      caption says 2,904 and 2,902 are on the map.
 *
 * THE FRAME IS THE CELLS, not the map. The dial decides the resolution, the resolution decides the
 * cells, and the cells decide how much ground is in view — so turning the dial zooms the map, and a
 * reader never has to line up two pictures. Past 20 km across the plan stops being drawn as
 * buildings and becomes the rectangle it actually is, because 26,311 vertices inside a 26 km
 * hexagon is a smudge, and a smudge that took 400 kB to draw.
 */
PAI_LOAD.push(function () {
'use strict';

const H = window.H3;
/* PORTED: the plan arrives from GET /place/geojson after boot() and may never arrive at all — the
 * place pack need not be installed, and the route is refused to anything but this machine or a
 * token. So it is read when it is drawn, never captured at load, and its absence is one line. */
const P = () => window.PLAN;
const NOPLAN = ref => `<p class="note" data-component="absent" id="plan-absent" data-ref="${ref}">`
  + `This node has no plan of its own ground. GET /place/geojson is on no share allowlist at any `
  + `level — it is the exact building footprints within PLACE_RADIUS_M of the address — so it `
  + `needs a token, or this page open on the machine the node runs on. The place pack fetches it `
  + `once and keeps it on that machine's disk.</p>`;
const { esc } = window.K;
const { km2, edge } = window.KH;

/* Past this the plan is a rectangle with a sentence on it rather than three thousand buildings. */
const MAX_SPAN_M = 20000;

const ROAD_W = { motorway: 2.2, trunk: 2.2, primary: 1.8, secondary: 1.6, tertiary: 1.3,
  residential: 1.0, unclassified: 1.0, living_street: .9, service: .6, footway: .5, path: .5 };

const d2 = v => Math.round(v * 100) / 100;

/* A flat [x,y,x,y,…] ring in metres to an SVG path. No rounding beyond two decimals, no smoothing,
 * no dropping of short segments: every vertex make-plan.mjs kept is drawn. */
function ring(flatXY) {
  let s = 'M';
  for (let i = 0; i < flatXY.length; i += 2) s += `${d2(flatXY[i])},${d2(flatXY[i + 1])}` + (i + 2 < flatXY.length ? 'L' : '');
  return s + 'Z';
}
function line(flatXY) {
  let s = 'M';
  for (let i = 0; i < flatXY.length; i += 2) s += `${d2(flatXY[i])},${d2(flatXY[i + 1])}` + (i + 2 < flatXY.length ? 'L' : '');
  return s;
}
/* Cull by frame, because at resolution 11 the view is 100 m across and 2,902 buildings are not. */
const hits = (flatXY, f, off = 0) => {
  for (let i = off; i < flatXY.length; i += 2) {
    if (flatXY[i] >= f.x0 && flatXY[i] <= f.x1 && flatXY[i + 1] >= f.y0 && flatXY[i + 1] <= f.y1) return true;
  }
  return false;
};

function frameOf(cellsM, pad = 0.06) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const c of cellsM) {
    for (let i = 1; i < c.length; i += 2) {
      x0 = Math.min(x0, c[i]); x1 = Math.max(x1, c[i]);
      y0 = Math.min(y0, c[i + 1]); y1 = Math.max(y1, c[i + 1]);
    }
  }
  const w = x1 - x0, h = y1 - y0, m = Math.max(w, h) * pad;
  return { x0: x0 - m, y0: y0 - m, x1: x1 + m, y1: y1 + m, w: w + 2 * m, h: h + 2 * m,
    span: Math.max(w, h) + 2 * m };
}

/* ------------------------------------------------------------------ the map */
/* opts.satOnly draws the satellite's own buildings and nothing else, for the satellite section.
 * opts.cells is the set of cell ids to draw heavy; everything else in the plate is a hairline. */
function map(res, opts = {}) {
  const plate = H.nav.plates[res];
  if (!plate) return '';
  if (!P()) return NOPLAN(opts.ref || 'dial');
  const f = frameOf(plate.cells_m);
  const u = f.span / 620;                        // metres per nominal pixel at the drawn size
  const heavy = new Set(opts.cells || [plate.centre]);
  const coarse = f.span > MAX_SPAN_M;
  const id = `map-${res}${opts.satOnly ? '-sat' : ''}`;

  const cells = plate.cells_m.map(c => {
    const on = heavy.has(c[0]);
    return `<path d="${ring(c.slice(1))}" fill="${on ? 'var(--cells)' : 'none'}"`
      + ` fill-opacity="${on ? 0.1 : 0}" stroke="${on ? 'var(--cells)' : 'var(--ink)'}"`
      + ` stroke-opacity="${on ? 1 : 0.3}" stroke-width="${d2((on ? 2 : 0.5) * u)}"`
      + `><title>${esc(c[0])}</title></path>`;
  }).join('');

  let ground = '';
  if (coarse) {
    /* Everything this node has drawn of its own ground, to scale, inside a cell that dwarfs it. */
    const [bx0, by0, bx1, by1] = P().bbox_m;
    ground = `<rect x="${bx0}" y="${by0}" width="${bx1 - bx0}" height="${by1 - by0}"`
      + ` fill="var(--ink)" fill-opacity="0.12" stroke="var(--ink)" stroke-opacity="0.5"`
      + ` stroke-width="${d2(u)}"/>`;
  } else if (opts.satOnly) {
    ground = `<g>` + P().sat.filter(sat => hits(sat, f, 1)).map(sat =>
      `<path d="${ring(sat.slice(1))}" fill="var(--satellite-only)"`
      + ` fill-opacity="${d2(0.2 + 0.3 * sat[0])}" stroke="var(--satellite-only)"`
      + ` stroke-width="${d2(0.7 * u)}"/>`).join('') + `</g>`
      /* The town underneath, as a hairline, so a reader can tell the satellite's buildings from
       * empty ground rather than from nothing at all. */
      + `<g fill="none" stroke="var(--ink)" stroke-opacity="0.22" stroke-width="${d2(0.6 * u)}">`
      + P().buildings.filter(b => hits(b, f)).map(b => `<path d="${ring(b)}"/>`).join('') + `</g>`;
  } else {
    ground =
      `<circle cx="0" cy="0" r="1000" fill="none" stroke="var(--ink)" stroke-opacity="0.35"`
      + ` stroke-width="${d2(u)}" stroke-dasharray="${d2(4 * u)} ${d2(4 * u)}"/>`
      + `<g fill="var(--rings)" fill-opacity="0.26">`
      + P().green.filter(g => hits(g, f)).map(g => `<path d="${ring(g)}"/>`).join('') + `</g>`
      + `<g fill="none" stroke="var(--ink)" stroke-opacity="0.65">`
      + P().roads.filter(r => hits(r, f, 1)).map(r =>
        `<path d="${line(r.slice(1))}" stroke-width="${d2((ROAD_W[r[0]] || .8) * u)}"/>`).join('')
      + `</g>`
      + `<g fill="var(--ink)" fill-opacity="0.82">`
      + P().buildings.filter(b => hits(b, f)).map(b => `<path d="${ring(b)}"/>`).join('') + `</g>`
      + `<g fill="var(--satellite-only)" fill-opacity="0.35" stroke="var(--satellite-only)"` // sat
      + ` stroke-width="${d2(0.7 * u)}">`
      + P().sat.filter(sat => hits(sat, f, 1)).map(sat => `<path d="${ring(sat.slice(1))}"/>`).join('')
      + `</g>`
      + `<g fill="var(--cells)">`
      + P().poi.filter(p => p[0] >= f.x0 && p[0] <= f.x1 && p[1] >= f.y0 && p[1] <= f.y1)
        .map(p => `<circle cx="${p[0]}" cy="${p[1]}" r="${d2(4.5 * u)}"/>`).join('')
      + `</g>`;
  }

  /* Every station with a coordinate that falls in view, so the map answers "who is reading here"
     with the same marks the abstract drawings use. */
  const MK = Math.cos(H.node.lat * Math.PI / 180) * 111320;
  const pts = H.sensors.map(s => ({ s,
    x: (s.lon - H.node.lon) * MK, y: -(s.lat - H.node.lat) * 111320 }))
    .filter(p => p.x >= f.x0 && p.x <= f.x1 && p.y >= f.y0 && p.y <= f.y1)
    .map(p => `<circle cx="${d2(p.x)}" cy="${d2(p.y)}" r="${d2((p.s.local ? 5.5 : 3.5) * u)}"`
      + ` fill="${p.s.local ? 'var(--cells)' : 'var(--ground)'}" stroke="var(--ink)"`
      + ` stroke-width="${d2((p.s.local ? 2 : 1.4) * u)}">`
      + `<title>${esc(p.s.name || p.s.sensor_id)}</title></circle>`).join('');

  return `<svg class="planmap" id="${id}" viewBox="${d2(f.x0)} ${d2(f.y0)} ${d2(f.w)} ${d2(f.h)}"`
    + ` role="img" aria-label="${esc(opts.label
      || `the ground around this node at resolution ${res}: ${coarse
        ? `a cell ${edge(H.ladder[res].edge_m)} to an edge, with everything this node has mapped of `
          + `its own ground drawn to scale inside it`
        : `${P().counts.buildings_drawn} buildings, ${P().counts.roads} roads and the cells laid over `
          + `them`}`)}">`
    + `<rect x="${d2(f.x0)}" y="${d2(f.y0)}" width="${d2(f.w)}" height="${d2(f.h)}"`
    + ` fill="var(--ground)"/>`
    + ground
    + `<g>${cells}</g>`
    + pts
    + `<circle cx="0" cy="0" r="${d2(7 * u)}" fill="var(--cells)"/>`
    + `</svg>`;
}

/* The caption under a map, which has to say what a reader cannot see: where the shapes came from,
 * how wide the view is, and — when the cell has outgrown the map — that the map has stopped. */
function caption(res) {
  if (!P()) return `resolution ${res} · no plan on this node`;
  const f = frameOf(H.nav.plates[res].cells_m);
  const coarse = f.span > MAX_SPAN_M;
  const across = f.span >= 10000 ? `${Math.round(f.span / 1000)} km` : f.span >= 1000
    ? `${(f.span / 1000).toFixed(1)} km` : `${Math.round(f.span)} m`;
  return `resolution ${res} · ${across} across · `
    + (coarse
      ? `wider than the ${(P().span_m[0] / 1000).toFixed(1)} km this node has mapped, so the map is `
        + `its outline`
      : `${P().counts.buildings_drawn} of ${P().counts.buildings} buildings · ${P().counts.roads} roads`)
    + ` · OpenStreetMap, kept on this node’s disk`;
}

window.KMAP = { map, caption, frameOf, MAX_SPAN_M };

});

/* ================================================================= kit-page.js — the page contract ==== */
/* The page contract: a lead, four stages of one loop, and the notes.
 *
 *     observe → decide → act → measure → observe …
 *
 * This is the PLANETAI logic laid out as the page's own spine. A node OBSERVES its place — sensors,
 * the ground, the satellite, the radio. It DECIDES what may be said about it, and at what grain. It
 * ACTS by asking somebody to do something. It MEASURES whether that worked and how long it took, and
 * the loop closes. Every section on the page belongs to one stage, and the page is read in the order
 * the loop runs.
 *
 * WHY THIS IS A CONTRACT AND NOT A LAYOUT. Tomas asked for a structure a node can extend and then
 * propose back — Meshtastic and Reticulum today, an open hardware manager and local making next,
 * community packs after that. So the page does not know what its sections are. Packs register them:
 *
 *     window.PAI.register({
 *       id: 'ground',            // unique; becomes the band's DOM id
 *       pack: 'place',           // the pack that owns it; 'core' for the renderer's own
 *       stage: 'observe',        // observe · decide · act · measure
 *       title: 'The ground',     // the band's kicker, in the house voice
 *       order: 10,               // position within its stage; lower first
 *       needs: ['PLAN'],         // globals it reads. Absent → the band says so and does not fail
 *       controls(ctx) → html,    // optional: a control strip for this section (a toggle, a selector)
 *       render(ctx)   → html,    // the body. Captions belong here; explanations do not
 *       wall(ctx)     → html,    // optional: what it contributes to the wall at ctx.RES
 *       notes(ctx)    → [{ id, text }],   // the explanations, gathered at the bottom of the page
 *     });
 *
 * and the shell renders whatever registered, stage by stage. A section from a pack a node does not
 * have simply is not there; a section whose data is missing prints one honest line instead of a
 * blank. Adding a feature is adding a file. Proposing it back is sending the file.
 *
 * WHAT A SECTION MAY NOT DO. Invent a fifth card kind (readout · stack · series · row are the four,
 * and a drawing is a drawing inside a card). Colour a state by hue. Print a numeral without
 * `data-num`/`data-cmp`. Leave a component with no `data-ref` in or out. Put its explanation in its
 * body — that goes in `notes()`, and the shell puts every note at the bottom where Tomas asked for
 * them. None of this is enforced here; all of it is measured by tests/visual/measure.mjs.
 *
 * In Phase 2 this same shape is a pack's `dashboard` contribution, declared in its pack.yaml and
 * served by the node as one more static file. Nothing here is a framework: it is an array, a sort,
 * and a join.
 */
PAI_LOAD.push(function () {
'use strict';

const STAGES = [
  ['observe', 'Observe', 'what is read, seen and heard about this place'],
  ['decide', 'Decide', 'what may be said about it, and at what grain'],
  ['act', 'Act', 'what has been asked, of whom'],
  ['measure', 'Measure', 'whether it worked, and how long it took'],
];
const STAGE_INDEX = Object.fromEntries(STAGES.map(([k], i) => [k, i]));

const sections = [];
const problems = [];

function register(mod) {
  const missing = ['id', 'pack', 'stage', 'title', 'render'].filter(k => !mod[k]);
  if (missing.length || !(mod.stage in STAGE_INDEX)) {
    problems.push(`${mod.id || '?'}: ${missing.length ? `missing ${missing.join(', ')}`
      : `unknown stage ${mod.stage}`}`);
    return;
  }
  if (sections.some(s => s.id === mod.id)) { problems.push(`${mod.id}: registered twice`); return; }
  sections.push({ order: 50, needs: [], ...mod });
}

/* A global path like 'H3.nav.plates' resolves or does not. */
const has = path => path.split('.').reduce((o, k) => (o == null ? o : o[k]), window) != null;

function bandFor(ctx, s) {
  const { esc } = window.K;
  const absent = (s.needs || []).filter(n => !has(n));
  let body, controls = '';
  if (absent.length) {
    body = `<p class="note" data-component="absent" id="${esc(s.id)}-absent" data-ref="${esc(s.id)}">`
      + `The ${esc(s.pack)} pack has nothing here yet: ${esc(absent.join(', '))} `
      + `${absent.length === 1 ? 'is' : 'are'} not on this node.</p>`;
  } else {
    /* The control strip is inside the same try as the body. The contract promises a pack author
       that one section cannot take the page down, and controls() is a section's code like any
       other: thrown from here it escaped render() and route(), #page was never assigned, and the
       whole Now view was blank paper. It is the last hook that was outside a guard. */
    try {
      controls = s.controls ? (s.controls(ctx) || '') : '';
      body = s.render(ctx) || '';
    }
    catch (e) {
      /* And the strip goes with it: a control pointing at a body that did not render is a link to
         an id that is not on the page, which is the thing T5 counts. */
      controls = '';
      body = `<p class="note" data-component="failed" id="${esc(s.id)}-failed" data-ref="${esc(s.id)}">`
        + `${esc(s.pack)} · ${esc(s.id)} did not render: ${esc(e.message)}. A failure is not an `
        + `answer, so the rest of the page is still here.</p>`;
    }
  }
  return `<section class="band" id="${esc(s.id)}" data-band="${esc(s.stage)}:${esc(s.id)}"`
    + ` data-pack="${esc(s.pack)}" data-stage="${esc(s.stage)}">`
    + `<div class="k"><span>${esc(s.title)}</span><span class="pack">${esc(s.pack)}</span></div>`
    + controls + body + `</section>`;
}

/* The page: the lead the shell passes in, then the four stages in loop order, then the notes. */
function render(ctx, lead, opts = {}) {
  const { esc } = window.K;
  /* `only` is the whole of the Now/Network split: one registry, two views, and the notes band at
     the foot then lists the sections on the view a reader is actually on. */
  const keep = opts.only ? new Set(opts.only) : null;
  const ordered = sections.filter(s => !keep || keep.has(s.id)).slice().sort((a, b) =>
    STAGE_INDEX[a.stage] - STAGE_INDEX[b.stage] || a.order - b.order || a.id.localeCompare(b.id));
  let html = lead || '';
  for (const [key, name, what] of STAGES) {
    const mine = ordered.filter(s => s.stage === key);
    if (!mine.length) continue;
    html += `<div class="stage" id="stage-${key}" data-stage="${key}">`
      + `<div class="stagehead"><span class="n">${STAGE_INDEX[key] + 1}</span>`
      + `<h2>${esc(name)}</h2><span class="what">${esc(what)}</span>`
      + `<span class="loop" aria-hidden="true">${STAGES.map(([k]) =>
        `<i class="${k === key ? 'on' : ''}"></i>`).join('')}</span></div>`
      + mine.map(s => bandFor(ctx, s)).join('') + `</div>`;
  }
  html += notesBand(ctx, ordered);
  if (problems.length) {
    html += `<p class="note" id="pai-problems">Registration problems: ${esc(problems.join('; '))}</p>`;
  }
  return html;
}

/* Every explanation on the page, in one place at the bottom, each pointing back at the section it
 * explains. The sections keep their captions and lose their paragraphs; a household that wants to
 * know why is one scroll from the answer and a household that does not is never interrupted. */
function notesBand(ctx, ordered) {
  const { esc } = window.K;
  const groups = [];
  for (const s of ordered) {
    if (!s.notes) continue;
    let ns = [];
    try { ns = s.notes(ctx) || []; } catch { ns = []; }
    ns = ns.filter(n => n && n.text);
    if (ns.length) groups.push({ section: s, notes: ns.map((n, i) => ({ ...n, id: n.id || `${s.id}-note-${i}` })) });
  }
  if (!groups.length) return '';
  /* One fold per section: its title, its pack and how many notes it holds, so a reader can tell
   * which fold holds what without opening all of them. Measured with every note open, the notes
   * were a third of the page — about 3,000 px of prose under a page meant to be read in a minute.
   * Folded they are one line each, still at the bottom, still one press from the answer. */
  return `<section class="band notes" id="notes" data-band="notes"><div class="k">`
    + `<span>Notes</span><span class="pack">why the page says what it says · `
    + `${groups.reduce((a, g) => a + g.notes.length, 0)} notes</span></div>`
    + groups.map(g => `<details class="fold notefold" id="notes-${esc(g.section.id)}"`
      + ` data-component="notes" data-ref="${esc(g.section.id)}">`
      + `<summary><span class="t">${esc(g.section.title)}</span>`
      + `<span class="pack">${esc(g.section.pack)}</span>`
      + `<span class="n">${g.notes.length}</span></summary>`
      + `<dl class="notelist">` + g.notes.map(n =>
        `<div class="noteitem" id="${esc(n.id)}"><dt><a href="#${esc(g.section.id)}">`
        + `${esc(g.section.title)}</a></dt><dd>${n.html ? n.text : esc(n.text)}</dd></div>`).join('')
      + `</dl></details>`).join('')
    + `</section>`;
}

/* The wall: whatever the registered sections say they can show at three metres, in loop order. */
function wall(ctx) {
  const ordered = sections.slice().sort((a, b) =>
    STAGE_INDEX[a.stage] - STAGE_INDEX[b.stage] || a.order - b.order);
  return ordered.filter(s => s.wall && (s.needs || []).every(has))
    .map(s => { try { return s.wall(ctx) || ''; } catch { return ''; } }).join('');
}

window.PAI = { STAGES, register, render, wall, sections, problems, has };

});

/* ================================================================= h/mods/ground.js ==== */
/* The ground: the real place under the cells, from a tile server or from this node's own disk.
 *
 * Tomas looked at the offline plan and asked for the thing it deliberately is not — "actually
 * embedding live open street map with satellite view, which should change scales when we change it
 * in the interface automatically." He was told what that costs: a page that fetches tiles tells the
 * tile server which square of the planet is being looked at, every time anybody opens it. He said
 * build it. So this builds it, prints the cost beside the picture, and keeps the offline plan one
 * press away.
 *
 * THREE BASES, one control strip:
 *   sat    Sentinel-2 cloudless, EOX. A 2020 mosaic, not today's sky. Serves to zoom 18.
 *   osm    OpenStreetMap's own raster tiles. Serves to zoom 19. Their usage policy applies.
 *   plan   kit-map.js: OpenStreetMap kept on this node's disk. No request leaves the machine.
 *
 * THE FRAME IS STILL THE CELLS. The dial sets the resolution, the resolution sets the 19 cells of
 * the plate, and the zoom is the largest of 0..19 at which their bounding box fits in the square —
 * so turning the dial zooms the map and a reader never lines up two pictures. Integer zooms only:
 * a fractional zoom means resampling tiles, and a tile drawn at 1.3× is a blur with an argument.
 *
 * TILES ARE WEB MERCATOR. The offline plan is drawn in the node's own local frame — metres east and
 * north of the node, make-plan.mjs — and this is drawn in EPSG:3857 because that is the only frame a
 * tile server speaks. At 8.8° south Mercator's scale is within 1.2% of true and constant to a part
 * in a thousand across a 5 km frame, so the cells land on the same pixels either way; at resolution
 * 2 and 3 the frame is hundreds of kilometres and the difference is visible, and there the plan is
 * already a rectangle. Boundaries are drawn vertex to vertex, straight, the way kit-h3.js does.
 *
 * Nothing here fetches. Tiles are `<img>` elements the browser asks for on its own, with the
 * browser's default referrer, which OpenStreetMap requires — measured: the same tile with no
 * Referer is a 403 "Access blocked" placeholder, with one it is the map. Do not set
 * referrerpolicy="no-referrer" on these.
 */
PAI_LOAD.push(function () {
'use strict';

const H = window.H3;
const { esc, row } = window.K;
const { edge } = window.KH;

const TILE = 256;
const SIZE = 600;                   // logical px of the lead's square; the wall passes its own
const FILL = 0.9;                   // the cells may take this much of the square
const EQUATOR_M = 40075016.686;     // Web Mercator's circumference, metres

const BASES = {
  sat: { name: 'satellite', host: 'tiles.maps.eox.at', maxZ: 18,
    url: (z, x, y) => `https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/g/${z}/${y}/${x}.jpg`,
    credit: 'Sentinel-2 cloudless by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2020)' },
  osm: { name: 'street map', host: 'tile.openstreetmap.org', maxZ: 19,
    url: (z, x, y) => `https://tile.openstreetmap.org/${z}/${x}/${y}.png`,
    credit: '© OpenStreetMap contributors' },
  plan: { name: 'plan, offline', host: null, credit: 'OpenStreetMap, kept on this node’s disk' },
};
/* Which base when nobody has pressed one. Tomas's rule: from resolution 9 inward, the plan. The
 * node's own map is about 3 km across; the res-9 plate is 1.6 km, so from 9 the plan fills the
 * frame edge to edge — the generated drawing is the better picture there and it sends nothing. At 8
 * the plate is 4.2 km and the plan covers the middle with paper round it, which Tomas looked at and
 * preferred the tiles for; coarser still the plan is a rectangle and the tiles take over. A pressed
 * base always wins over the rule. */
/* PORTED, and this is the node owner's own rule. Live tiles are OFF unless a keeper turns them on:
 * MAP_TILES is public, defaults to `off`, and only with it on does a tile ever appear — and then
 * only at resolution 8 and coarser, because from 9 inward the node's own plan fills the frame and
 * sends nothing. A pressed base still wins for that page view. */
const PLAN_FROM = 9;
/* ONE predicate, read in both places, so the strip can never offer what baseOf would refuse. */
const tilesAllowed = (res, settings) =>
  (settings || {}).MAP_TILES === 'on' && res < PLAN_FROM;
const autoBase = (res, settings) => tilesAllowed(res, settings) ? 'sat' : 'plan';
/* A PRESS MAY ONLY EVER REDUCE WHAT LEAVES THE HOUSE. The prototype's comment said the opposite —
 * "a pressed base always wins over the rule" — and it was written for a drawing, before MAP_TILES
 * existed. On a node it is not a preference: a link in a page cannot be allowed to override the
 * keeper's setting, because following it sends this household's own kilometre to somebody else's
 * machine. So `plan` is always pressable and the two live bases are honoured only where they are
 * also offered. */
const baseOf = (q, res) =>
  (q in BASES && (q === 'plan' || tilesAllowed(res, window.SETTINGS))) ? q : autoBase(res, window.SETTINGS);

/* ------------------------------------------------------------------ Web Mercator, in pixels */
/* World pixel coordinates at zoom z: the whole planet is 256·2^z px across. */
const px = z => TILE * Math.pow(2, z);
const lngX = (lng, z) => (lng + 180) / 360 * px(z);
const latY = (lat, z) => {
  const r = lat * Math.PI / 180;
  return (1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * px(z);
};
/* Ground metres per pixel at this latitude and zoom — the caption's "across" comes from this. */
const mPerPx = (lat, z) => EQUATOR_M * Math.cos(lat * Math.PI / 180) / px(z);

/* Everything the mosaic and its caption need, computed once. `size` is the square's logical
 * width; the zoom is the largest at which the plate's bounding box fits FILL of it, capped by what
 * the base serves. */
function frame(res, size = SIZE, base = 'sat') {
  const plate = H.nav.plates[res];
  const B = BASES[base];
  let lat0 = 90, lat1 = -90, lng0 = 180, lng1 = -180;
  for (const c of plate.cells_ll) {
    for (let i = 1; i < c.length; i += 2) {
      lat0 = Math.min(lat0, c[i]); lat1 = Math.max(lat1, c[i]);
      lng0 = Math.min(lng0, c[i + 1]); lng1 = Math.max(lng1, c[i + 1]);
    }
  }
  const maxZ = B.maxZ == null ? 19 : B.maxZ;
  let z = 0;
  for (let t = 0; t <= maxZ; t++) {
    const w = lngX(lng1, t) - lngX(lng0, t), h = latY(lat0, t) - latY(lat1, t);
    if (Math.max(w, h) <= size * FILL) z = t; else break;
  }
  const ox = lngX(H.node.lon, z) - size / 2, oy = latY(H.node.lat, z) - size / 2;
  /* Only the tiles the square touches. y is clamped to the planet; x wraps round it. */
  const n = Math.pow(2, z);
  const tiles = [];
  for (let ty = Math.floor(oy / TILE); ty * TILE < oy + size; ty++) {
    if (ty < 0 || ty >= n) continue;
    for (let tx = Math.floor(ox / TILE); tx * TILE < ox + size; tx++) {
      tiles.push({ x: ((tx % n) + n) % n, y: ty, left: tx * TILE - ox, top: ty * TILE - oy });
    }
  }
  const m = mPerPx(H.node.lat, z);
  return { res, size, base, z, ox, oy, tiles, plate,
    across_m: size * m, tile_m: TILE * m,
    X: lng => lngX(lng, z) - ox, Y: lat => latY(lat, z) - oy };
}

/* ------------------------------------------------------------------ the drawing */
const d1 = v => Math.round(v * 10) / 10;

/* The mosaic and the cells over it. Positions are percentages of the square so the same markup
 * scales to the lead's column and to a wall; the `size` only decides the zoom and the tile grid.
 * Each tile is drawn a pixel large so percentage rounding never opens a hairline seam.
 *
 * The tiles load eagerly. Every tile of the mosaic is on screen whenever the figure is, so lazy
 * loading defers them and saves nothing — measured: with loading="lazy" not one of twelve tiles
 * had arrived 600 ms after the load event, and the rendered page showed cells over bare paper. */
function figure(ctx, opts = {}) {
  const res = opts.res || ctx.RES;
  const base = baseOf(opts.base || ctx.Q.get('base'), res);
  if (base === 'plan') return ctx.KMAP.map(res);
  const f = frame(res, opts.size || SIZE, base);
  const B = BASES[base];
  const pc = v => `${(100 * v / f.size).toFixed(3)}%`;
  const tiles = f.tiles.map(t =>
    `<img src="${B.url(f.z, t.x, t.y)}" width="${TILE}" height="${TILE}" loading="eager" alt=""`
    + ` style="left:${pc(t.left)};top:${pc(t.top)};width:calc(${pc(TILE)} + 1px);`
    + `height:calc(${pc(TILE)} + 1px)" onerror="this.remove()">`).join('');

  /* State is weight and fill, never hue. On a photograph the only colours are ink and --cells, and
   * the hairlines get a --ground halo underneath so they survive a dark roof or a dark sea. */
  const path = c => {
    let s = 'M';
    for (let i = 1; i < c.length; i += 2) {
      s += `${d1(f.X(c[i + 1]))},${d1(f.Y(c[i]))}` + (i + 2 < c.length ? 'L' : '');
    }
    return s + 'Z';
  };
  const others = f.plate.cells_ll.filter(c => c[0] !== f.plate.centre).map(path).join('');
  const own = f.plate.cells_ll.find(c => c[0] === f.plate.centre);
  const cells = `<path d="${others}" fill="none" stroke="var(--ground)" stroke-opacity=".55"`
    + ` stroke-width="2.5"/>`
    + `<path d="${others}" fill="none" stroke="var(--ink)" stroke-opacity=".6" stroke-width=".75"/>`
    + (own ? `<path d="${path(own)}" fill="var(--cells)" fill-opacity=".1" stroke="var(--cells)"`
      + ` stroke-width="2.5"><title>${esc(own[0])}</title></path>` : '');

  const inFrame = (x, y) => x >= 0 && x <= f.size && y >= 0 && y <= f.size;
  const pts = H.sensors.map(s => ({ s, x: f.X(s.lon), y: f.Y(s.lat) }))
    .filter(p => inFrame(p.x, p.y))
    .map(p => `<circle cx="${d1(p.x)}" cy="${d1(p.y)}" r="${p.s.local ? 5.5 : 3.5}"`
      + ` fill="${p.s.local ? 'var(--cells)' : 'var(--ground)'}" stroke="var(--ink)"`
      + ` stroke-width="${p.s.local ? 2 : 1.4}"><title>${esc(p.s.name || p.s.sensor_id)}</title>`
      + `</circle>`).join('');

  return `<div class="groundmap" data-base="${base}" data-z="${f.z}">`
    + `<div class="tiles">${tiles}</div>`
    + `<svg viewBox="0 0 ${f.size} ${f.size}" role="img" aria-label="${esc(`resolution ${res} over `
      + `${B.name} tiles at zoom ${f.z}: the cell this node stands in, the ${f.plate.cells.length - 1}`
      + ` around it, and every station in view`)}">`
    + `<g>${cells}</g><g>${pts}</g>`
    + `<circle cx="${d1(f.X(H.node.lon))}" cy="${d1(f.Y(H.node.lat))}" r="7" fill="var(--cells)"/>`
    + `</svg></div>`;
}

/* ------------------------------------------------------------------ not sited yet */
/* A node that has just been plugged in has no coordinates. app/main.py's GET /health reads
 * NODE_LAT/NODE_LON out of the environment with `float(os.getenv("NODE_LAT", 0) or 0)` and rounds to
 * three decimals, so an unsited node publishes exactly 0 for both — absent and unset arrive the same
 * way. The test is therefore "both are falsy": 0, null and undefined all mean the same thing here,
 * and the only real place it would misread is within about 55 m of the point where the equator meets
 * the prime meridian, which is open water in the Gulf of Guinea.
 *
 * It matters because H3 answers for (0, 0) as readily as for anywhere else: without this the plate,
 * the cells and the map would all be drawn over that water and presented to a household as their own
 * ground. The page this replaces drew the computed H3 ground instead, and so does this — it is in
 * app/main.py's COMPANIONS and tools/check_ui.py names it as computed geometry. The register travels
 * in the URL because the drawing is an <img>, a document of its own that no stylesheet on this page
 * reaches: without it the ground drew the dark register's blue on the paper page at 2.29:1. */
const sited = window.KH.sited;

function unsited(ctx) {
  return `<figure class="gridwrap mapwrap" id="ground-figure" data-component="ground" data-ref="dial">`
    + `<img src="static/node-ground.svg?variant=${ctx.register}" alt="the resolution ladder as `
    + `hexagons, drawn by this node; it stands for no particular place until this one has been sited">`
    + `<figcaption class="cap">This node has not been sited yet, so there is no ground to draw. `
    + `Setting NODE_LAT and NODE_LON — <code>planetai setup</code>, or the Set up view — gives it a `
    + `cell, the stations near it, the plan of its own kilometre and every distance on this page. `
    + `Until then the drawing above is the grid itself and not this place.</figcaption></figure>`;
}

/* ------------------------------------------------------------------ the lead figure */
function lead(ctx) {
  if (!sited()) return unsited(ctx);
  const res = ctx.RES;
  const base = baseOf(ctx.Q.get('base'), res);
  /* Pressing the base the rule would have chosen anyway clears the choice, so the rule is back in
   * charge the next time the dial turns rather than a stale press outliving it. */
  /* Only what may be pressed is drawn. A link to a live base while tiles are off would be one click
     between a keeper's setting and this household's kilometre reaching a tile server, and the page
     offering it is the page arguing with the node. */
  const allowed = tilesAllowed(res, window.SETTINGS);
  const strip = `<div class="ctlstrip" role="group" aria-label="the ground under the cells">`
    + Object.entries(BASES).filter(([k]) => k === 'plan' || allowed).map(([k, b]) =>
      `<a class="${k === base ? 'on' : ''}" href="${ctx.qlink({ base: k === autoBase(res, window.SETTINGS) ? null : k })}">`
      + `${esc(b.name)}</a>`).join('')
    + `<span class="auto">${allowed
      ? `plan from resolution ${PLAN_FROM} · tiles coarser`
      : (window.SETTINGS || {}).MAP_TILES === 'on'
        ? `the plan fills the frame from resolution ${PLAN_FROM} in, and sends nothing`
        : 'live tiles are off on this node · turn MAP_TILES on under Set up to offer them'
      }</span></div>`;

  let key, cap;
  if (base === 'plan') {
    key = `<span><i class="own"></i>the cell this node stands in</span>`
      + `<span><i></i>buildings, roads, green — OpenStreetMap</span>`
      + `<span><i class="sat-only"></i>only the satellite knows</span>`;
    cap = esc(ctx.KMAP.caption(res));
  } else {
    const f = frame(res, SIZE, base), B = BASES[base];
    key = `<span><i class="own"></i>the cell this node stands in</span>`
      + `<span><i></i>the ${f.plate.cells.length - 1} cells around it</span>`
      + `<span><svg class="stn" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="4.5"`
      + ` fill="var(--cells)" stroke="var(--ink)" stroke-width="1.5"/></svg>this node’s own station · `
      + `<svg class="stn" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="3.5"`
      + ` fill="var(--ground)" stroke="var(--ink)" stroke-width="1.2"/></svg>another</span>`;
    cap = `resolution ${res} · <span data-num="ground.across" data-cmp="against one cell here, `
      + `${esc(edge(H.ladder[res].edge_m))} to an edge">${esc(edge(f.across_m))}</span> across · `
      + `zoom <span data-num="ground.zoom" data-cmp="against ${B.maxZ}, the finest ${esc(B.host)} `
      + `serves">${f.z}</span> · <span data-num="ground.tiles" data-cmp="against 0 for the offline `
      + `plan">${f.tiles.length}</span> tiles from ${esc(B.host)} · ${esc(B.credit)}`;
  }
  return `<figure class="gridwrap mapwrap" id="ground-figure" data-component="ground" data-ref="dial">`
    + strip + figure(ctx, { base, size: SIZE })
    + `<div class="gridkey">${key}</div>`
    + `<figcaption class="cap">${cap}</figcaption></figure>`;
}

/* ------------------------------------------------------------------ what this map sends out */
/* Two rows: the base in use, and the one it is measured against. Nothing here is a warning; it is
 * a count of requests and the name of the machine that receives them. */
function render(ctx) {
  if (!sited()) {
    return `<p class="note" data-component="groundOut" id="ground-out-plan" data-ref="ground-figure">`
      + `Nothing is being fetched for a map, because there is no place to fetch one for. A sited `
      + `node draws its own plan from this machine's disk and sends nothing; live tiles, if a keeper `
      + `turns them on, send one request per tile to somebody else's machine.</p>`;
  }
  const res = ctx.RES;
  const base = baseOf(ctx.Q.get('base'), res);
  const cols = 'minmax(0,210px) minmax(0,1fr) auto';
  const who = (b, m) => `<span class="who"><b>${esc(b)}</b><span class="m">${esc(m)}</span></span>`;
  const live = (k, verb) => {
    const f = frame(res, SIZE, k), B = BASES[k];
    return row({
      id: `ground-out-${k}`, component: 'groundOut', ref: 'ground-figure', cols,
      left: who(B.host, `${B.name} · zoom ${f.z}`),
      line: `${verb} one request per tile to ${B.host}, from the device this page is open on. Each `
        + `names a square of ground ${edge(f.tile_m)} wide, so the server learns which `
        + `${edge(f.across_m)} of the planet is being looked at, and from which address.`,
      qty: [{ num: `ground.requests.${k}`, value: `${f.tiles.length} requests`,
        cmp: 'against 0 for the offline plan' }],
    });
  };
  const plan = row({
    id: 'ground-out-plan', component: 'groundOut', ref: 'ground-figure', cols,
    left: who('this node', 'plan, offline'),
    line: 'Every shape is on this machine’s disk, fetched once by the place pack. Opening the page '
      + 'asks nothing of anybody.',
    qty: [{ num: 'ground.requests.plan', value: '0 requests',
      cmp: `against the ${frame(res, SIZE, 'sat').tiles.length} the satellite base sends` }],
  });
  return base === 'plan' ? plan + live('sat', 'Switched on, the satellite base sends')
    : live(base, 'This view sends') + plan;
}

/* ------------------------------------------------------------------ the notes */
function notes(ctx) {
  if (!sited()) {
    return [{ id: 'ground-unsited', text: 'This node has no coordinates, so nothing on this page can '
      + 'say where it is. GET /health publishes lat and lon rounded to three decimals and an unsited '
      + 'node publishes zero for both, which is a real point in the Gulf of Guinea — so the page '
      + 'draws the grid itself rather than a map of open water labelled as this household’s ground.' }];
  }
  const base = baseOf(ctx.Q.get('base'), ctx.RES);
  const f = frame(ctx.RES, SIZE, base === 'plan' ? 'sat' : base);
  return [
    { id: 'ground-rule', text: `From resolution ${PLAN_FROM} inward the ground is this node’s own `
      + 'plan unless a live base is pressed — Tomas’s rule. The plan is about 3 km across and the '
      + 'resolution-9 plate is 1.6 km, so from 9 the plan fills the frame edge to edge; it is the '
      + 'better drawing there, every vertex is the node’s own, and it sends nothing. At 8 the plate '
      + 'is 4.2 km and the plan sits in the middle with paper round it, so the tiles show there and '
      + `coarser — but only when a keeper has set MAP_TILES to on, which on this node it is `
      + `${(window.SETTINGS || {}).MAP_TILES === 'on' ? 'is' : 'is not'}. Off, the plan is the ground `
      + 'at every stop and the page sends nothing at all.' },
    { id: 'ground-why-live', text: 'The live bases are here because Tomas asked for them: a real map '
      + 'with a satellite view that rescales when the dial turns. He was told what it costs — a page '
      + 'that fetches tiles tells the tile server which square of the planet is being looked at, '
      + 'every time anybody opens it — and asked for it anyway. So it is built, the cost is printed '
      + 'beside the picture, and the offline plan is one press away in the same strip.' },
    { id: 'ground-cost', text: `What leaves: one request per tile, ${f.tiles.length} for this view, `
      + `from the device the page is open on to ${BASES[f.base].host}. Each request names a tile by `
      + `zoom, column and row, which is a square of ground ${edge(f.tile_m)} wide, and carries the `
      + `device's own address. The server does not learn that this is a PLANETAI node or where the `
      + `node itself stands beyond that square; it does learn that somebody at that address looks at `
      + `this ${edge(f.across_m)}${S.health.city ? ` of ${S.health.city}` : ''}, and how often. The `
      + `plan sends nothing.` },
    { id: 'ground-zoom', text: 'The zoom follows the dial because the frame is the cells, not the '
      + 'map. The dial sets the resolution, the resolution sets the nineteen cells of the plate, and '
      + 'the zoom is the largest of 0 to 19 at which their bounding box fits nine tenths of the '
      + 'square. H3 steps by seven in area and a tile zoom by four, so one stop on the dial moves the '
      + 'zoom by one or two levels, and the cell in the middle stays the same size on the page at '
      + 'every stop within a factor of two.' },
    { id: 'ground-frames', text: 'Tiles are Web Mercator, EPSG:3857, because that is the only frame a '
      + 'tile server speaks. The offline plan is drawn in the node\'s own local frame — metres east '
      + 'and north of the node, which make-plan.mjs computed and kit-map.js places. At 8.8° south '
      + 'Mercator\'s scale is within 1.2% of true and constant to a part in a thousand across a 5 km '
      + 'frame, so the cells fall on the same pixels either way. At resolution 2 and 3 the frame is '
      + 'hundreds of kilometres and the difference shows; there the plan is already a rectangle, and '
      + 'the tiles are the only base that is a picture at all.' },
    { id: 'ground-osm-policy', text: 'OpenStreetMap\'s tiles come from volunteer-run servers under a '
      + 'usage policy: light use, attribution, a real browser referrer, no bulk downloading. One '
      + 'household opening one page is inside it; a fleet of nodes refreshing a map every minute '
      + 'would not be, and the same tile fetched without a referrer is refused with a placeholder '
      + 'that says so. The attribution is in the caption, and this page asks for tiles only when '
      + 'somebody opens it.' },
    { id: 'ground-s2', text: 'The satellite base is EOX\'s Sentinel-2 cloudless mosaic for 2020: '
      + 'many passes stitched into one cloud-free picture, six years old. It is a ground to read '
      + 'the cells against, not an observation of today — the sky, the season and the newest roofs '
      + 'in it are none of this week\'s. What this node\'s own satellite passes saw of the same '
      + 'ground is the satellite section, dated.' },
  ];
}

/* PORTED: this module's CSS is in dashboard.css, under a banner naming this file. */

window.GROUND = { figure, frame, BASES, SIZE };

window.PAI.register({
  id: 'ground', pack: 'place', stage: 'observe', title: 'The ground', order: 0,
  needs: ['H3.nav'],
  lead, render, notes,
});

});

/* ================================================================= h/mods/sensors.js ==== */
/* What the stations read — the sensor list, filed by the cell each station falls in at the dial.
 *
 * Tomas asked for "the sensor lists in now, with sensor graphics and ability to select what to
 * show (air, temperature, humidity and other sensor variables), as well as having links to the
 * sources of sensor data." This is that, as one module of the air-quality pack.
 *
 * WHAT IT SHOWS. Every station in the fixture that carries a coordinate — fourteen — grouped by the
 * H3 cell it falls in AT THE RESOLUTION THE DIAL STANDS AT. Turn the dial to 4 and all fourteen
 * are one group; turn it to 9 and they are nine. Nothing else about a row changes when the dial
 * moves: a station's number is its own 15-minute mean whatever cell it is filed under, which is
 * the point of filing rather than averaging.
 *
 * WHAT IT DOES NOT DO. Average across stations (GET /issues publishes the street as one fenced
 * median, and this page shows the thing the median hides). Draw a trace it does not have: the
 * capture carries an hourly series for two stations, both PM2.5, so two rows have a trace and the
 * rest have one tick at the value, at now. Compare a number with a line drawn for a different
 * quantity: the Air line is the WHO 24-hour guideline for PM2.5 and is not a PM10 line; the Heat
 * line is for apparent temperature and no station here reports that directly. Where the line does
 * not apply the row says "no comparison yet" and why, at the same size, in the same place.
 *
 * Sources are links, because a reading somebody else took is only citable if the reader can go
 * and look: a Smart Citizen kit to its public page, a Bali Air Dispatch station to the
 * observatory, whose attribution line is required and printed under the list.
 */
PAI_LOAD.push(function () {
'use strict';

const { esc, fmt, age, cmpText, noLine } = window.K;
const DEFAULT_VAR = 'pm25';

/* The variable the reader chose, or PM2.5. A key the fixture does not know is not an error to
 * draw a blank for; it is the default. */
const chosen = (ctx, metrics) => {
  const v = ctx.Q.get('var');
  return v && metrics[v] ? v : DEFAULT_VAR;
};

/* Every variable at least one station carries, in the order the fixture declares them. A selector
 * that offered battery voltage when nothing here reports it would be a control that does nothing. */
const carried = H => Object.keys(H.metrics).filter(v => H.sensors.some(s => s.read[v]));

/* The line a variable may be measured against: the issue's line, and only when the issue's own
 * metric IS this variable. Fifteen micrograms is a PM2.5 line; printing it under PM10 would be a
 * comparison nobody declared. */
function lineFor(ctx, v) {
  const m = ctx.H.metrics[v];
  const iss = m && m.issue ? ctx.ISS[m.issue] : null;
  if (!iss) return { line: null, cmp: `no comparison yet · no issue on this page claims ${m ? m.label : v}` };
  if (!iss.line) return { line: null, cmp: `no comparison yet · ${noLine(iss)}` };
  if (iss.metric && iss.metric !== v) {
    return { line: null, cmp: `no comparison yet · the ${iss.name.en} line, `
      + `${fmt(iss.line.value, m.dp)} ${iss.line.unit || iss.unit}, is drawn for ${iss.metric}, not ${m.label}` };
  }
  return { line: iss.line,
    cmp: `${cmpText({ mode: 'line', line: iss.line, unit: m.unit, dp: m.dp }).text} · ${iss.line.source}` };
}

/* One value scale for every graphic in the section, so a tick in one row and a trace in another
 * are read against the same height. The node's values set the box; the line is in it when it
 * applies, so the headroom under the line is visible rather than implied. */
function scaleFor(H, v, line) {
  const vals = [];
  for (const s of H.sensors) {
    if (s.read[v]) vals.push(s.read[v].value);
    for (const b of s.series[v] || []) vals.push(b.min, b.max);
  }
  if (line) vals.push(line.value);
  if (!vals.length) return null;
  let lo = Math.min(...vals), hi = Math.max(...vals);
  const pad = (hi - lo) * 0.08 || 1;
  /* A concentration does not go below zero, so the scale must not either: a box that opened at
   * -1.0 µg/m³ was drawing headroom under a floor. Temperature may. */
  lo = lo >= 0 ? Math.max(0, lo - pad) : lo - pad;
  hi += pad;
  return { lo, hi, Y: y => 4 + (1 - (y - lo) / (hi - lo)) * (48 - 4 - 14) };
}

/* The drawing inside a row. 240 by 48: a light min–max band, an ink polyline of the hourly means,
 * the line dashed in the signal colour where it applies, and the axis words. A station with no
 * series gets one tick at the value at now, and no line pretending to be its day. */
function graphic(s, v, m, sc, line) {
  const W = 240, Hh = 48, l = 2, r = 2;
  const r15 = s.read[v];
  const ser = s.series[v];
  let body = '', label;
  if (line) body += `<line x1="${l}" x2="${W - r}" y1="${sc.Y(line.value).toFixed(1)}"`
    + ` y2="${sc.Y(line.value).toFixed(1)}" stroke="var(--signal-worse)" stroke-dasharray="3 5"/>`;
  if (ser && ser.length) {
    const n = ser.length;
    const X = i => (l + (i / Math.max(1, n - 1)) * (W - l - r)).toFixed(1);
    const band = ser.map((b, i) => `${X(i)},${sc.Y(b.max).toFixed(1)}`)
      .concat(ser.map((b, i) => `${X(i)},${sc.Y(b.min).toFixed(1)}`).reverse()).join(' ');
    body += `<polygon points="${band}" fill="var(--ink)" fill-opacity=".1"/>`
      + `<polyline points="${ser.map((b, i) => `${X(i)},${sc.Y(b.mean).toFixed(1)}`).join(' ')}"`
      + ` fill="none" stroke="var(--ink)" stroke-width="1.5"/>`
      + `<text x="${l}" y="${Hh - 2}">24 h ago</text>`;
    const lo = Math.min(...ser.map(b => b.min)), hi = Math.max(...ser.map(b => b.max));
    label = `${m.label}, ${n} hourly means: opened the day at ${fmt(ser[0].mean, m.dp)} and closed `
      + `it at ${fmt(ser[n - 1].mean, m.dp)} ${m.unit}; low ${fmt(lo, m.dp)}, high ${fmt(hi, m.dp)}`
      + (line ? `; the line ${fmt(line.value, m.dp)}` : '');
  } else {
    const y = sc.Y(r15.value).toFixed(1);
    body += `<line x1="${W - r - 1}" x2="${W - r - 1}" y1="${(+y - 4).toFixed(1)}" y2="${(+y + 4).toFixed(1)}"`
      + ` stroke="var(--ink)" stroke-width="2"/>`;
    label = `${m.label} ${fmt(r15.value, m.dp)} ${m.unit}, one 15-minute mean at now`;
  }
  body += `<text x="${W - r}" y="${Hh - 2}" text-anchor="end">now</text>`;
  return `<svg class="spark" viewBox="0 0 ${W} ${Hh}" role="img" aria-label="${esc(label)}">${body}</svg>`;
}

function station(ctx, s, v, m, sc, L, ref) {
  const r = s.read[v];
  /* PORTED: the drawing's stations carried `label`; GET /issues publishes the same thing as
     `source`, read off the sensor id the way app/sources.py assigns it. */
  const src = s.url
    ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.source)}</a>` : esc(s.source);
  const silent = r && r.silent_minutes > 60
    ? ` · <span class="silent">silent</span> ${esc(age(r.silent_minutes))}` : '';
  const ser = s.series[v];
  const alt = ser && ser.length
    ? `<span class="alt">opened the day at ${esc(fmt(ser[0].mean, m.dp))}, closed at `
      + `${esc(fmt(ser[ser.length - 1].mean, m.dp))} ${esc(m.unit)}</span>` : '';
  /* km is null when the node has no coordinates: the engine publishes unknown rather than a distance
     from (0, 0). Say unknown — a neighbour's distance from the Gulf of Guinea is not a fact. */
  const meta = `${s.local ? 'this house' : s.km == null ? 'distance unknown'
    : `${esc(String(s.km))} km`} · ${s.indoor ? 'indoor' : 'outdoor'}`
    + ` · ${src}${silent}`;
  const key = `${m.issue || v}.${s.sensor_id}.${v}`;
  const crossed = r && L.line && r.value > L.line.value;
  const cmp = !r ? (Object.keys(s.read).length ? 'does not measure this' : 'nothing read in this capture')
    : L.cmp;
  return `<div class="row station${s.local ? ' mine' : ''}${r ? '' : ' quiet'}" data-kind="row"`
    + ` data-component="station" id="st-${esc(s.sensor_id)}" data-ref="${esc(ref)}">`
    + `<span class="who"><b>${esc(s.name || s.sensor_id)}</b><span class="m">${meta}</span>${alt}</span>`
    + `<span class="pic">${r && sc ? graphic(s, v, m, sc, L.line) : ''}</span>`
    + `<span class="qty">${r
      ? `<span class="num${crossed ? ' crossed' : ''}" data-num="${esc(key)}" data-cmp="${esc(cmp)}">`
        + `${esc(fmt(r.value, m.dp))}</span><small>${esc(m.unit)}</small>`
      : `<span class="none">—</span>`}</span>`
    + `<span class="cmp">${esc(cmp)}</span></div>`;
}

/* Stations by the cell they fall in at the dial's resolution: this node's own cell first, then by
 * distance. Two stations in one cell are two rows — the whole reason to draw cells is that they
 * are not one number. */
function groups(ctx) {
  const by = new Map();
  for (const s of ctx.H.sensors) {
    /* '' is a station outside the two steps this node published at this resolution — not an error
       and not a cell, and the header for that group says so rather than printing a blank id. */
    const c = s.chain[ctx.RES] || '';
    if (!by.has(c)) by.set(c, []);
    by.get(c).push(s);
  }
  const own = ctx.N.chain[ctx.RES];
  /* Unsited, every km is null: the groups keep the order the node sent and the header says the
     distance is not known rather than ordering the neighbourhood by a number that is not one. */
  const kms = ss => ss.map(s => s.km).filter(k => k != null);
  return [...by.entries()].map(([cell, ss]) => ({
    cell, ss: ss.slice().sort((a, b) => (a.km ?? Infinity) - (b.km ?? Infinity)), own: cell === own,
    km: kms(ss).length ? Math.min(...kms(ss)) : null,
    kmMax: kms(ss).length ? Math.max(...kms(ss)) : null,
  })).sort((a, b) => (a.own ? -1 : b.own ? 1 : 0) || (a.km ?? Infinity) - (b.km ?? Infinity));
}

const KM = g => g.own ? 'this node’s own cell'
  : g.km == null ? 'distance unknown — this node has no coordinates'
  : g.km === g.kmMax ? `${g.km} km` : `${g.km}–${g.kmMax} km`;
const CELLHEAD = (ctx, g) => g.cell ? ctx.KH.address(g.cell, ctx.RES)
  : `<span class="addr mono">outside the ${ctx.N.steps} steps this node published at resolution `
    + `${ctx.RES}</span>`;

window.PAI.register({
  id: 'sensors', pack: 'air-quality', stage: 'observe', title: 'What the stations read', order: 20,
  needs: ['H3.sensors'],

  controls(ctx) {
    const v = chosen(ctx, ctx.H.metrics);
    return `<div class="ctlstrip" id="sensors-vars" data-component="varStrip" data-ref="sensors-list"`
      + ` role="group" aria-label="variable shown, ${esc(ctx.H.metrics[v].label)}">`
      + carried(ctx.H).map(k => `<a class="${k === v ? 'on' : ''}" href="${esc(ctx.qlink({ var: k }))}">`
        + `${esc(ctx.H.metrics[k].label)}</a>`).join('') + `</div>`;
  },

  render(ctx) {
    const H = ctx.H;
    if (!H.sensors.length) {
      return `<p class="note" id="sensors-list" data-ref="sensors">No station with a coordinate `
        + `in this capture.</p>`;
    }
    const v = chosen(ctx, H.metrics), m = H.metrics[v];
    const L = lineFor(ctx, v);
    const sc = scaleFor(H, v, L.line);
    const gs = groups(ctx);
    let html = `<div class="stations" id="sensors-list">`;
    for (const g of gs) {
      const id = `sensors-cell-${g.cell || 'outside'}`;
      html += `<div class="cellhead" id="${id}" data-component="cellGroup" data-ref="dial">`
        + CELLHEAD(ctx, g)
        + `<span class="n"><b data-num="sensors.cell.${esc(g.cell || 'outside')}.n" data-cmp="against `
        + `${H.sensors.length} stations with a coordinate in this capture">${g.ss.length}</b> `
        + `${g.ss.length === 1 ? 'station' : 'stations'} · ${KM(g)}</span></div>`
        + g.ss.map(s => station(ctx, s, v, m, sc, L, id)).join('');
    }
    html += `</div>`;
    const carry = H.sensors.filter(s => s.read[v]).length;
    const traced = H.sensors.filter(s => (s.series[v] || []).length).length;
    const attrib = [...new Set(H.sensors.map(s => s.attribution).filter(Boolean))];
    html += `<p class="cap" id="sensors-cap" data-ref="sensors-list">`
      + `<span data-num="sensors.carry" data-cmp="against ${H.sensors.length} stations with a `
      + `coordinate in this capture">${carry} of ${H.sensors.length}</span> stations carry `
      + `${esc(m.label)} · <span data-num="sensors.traced" data-cmp="against ${carry} stations that `
      + `carry ${esc(m.label)}">${traced}</span> ${traced === 1 ? 'has' : 'have'} an hourly series; the `
      + `rest show one 15-minute mean as a tick at now — no hourly series in this capture`
      + (sc ? ` · one scale for every graphic, ${esc(fmt(sc.lo, m.dp))} to ${esc(fmt(sc.hi, m.dp))} `
        + `${esc(m.unit)}${L.line ? `, the line dashed at ${esc(fmt(L.line.value, m.dp))}` : ''}` : '')
      + ` · sources: ${attrib.map(esc).join(' · ')}</p>`;
    return html;
  },

  notes(ctx) {
    const H = ctx.H, v = chosen(ctx, H.metrics), m = H.metrics[v];
    const gt = r => H.grain_table.find(g => g.res === r) || {};
    const traced = H.sensors.filter(s => Object.keys(s.series).length);
    const quiet = H.sensors.filter(s => !Object.keys(s.read).length);
    const oldest = Math.max(0, ...H.sensors.flatMap(s => Object.values(s.read).map(r => r.silent_minutes || 0)));
    const air = ctx.ISS.air, heat = ctx.ISS.heat;
    return [
      { id: 'sensors-note-station', text: ctx.KN.NAV_HONEST.perStation() },
      { id: 'sensors-note-series', text: `${traced.length} of the ${H.sensors.length} stations carry `
        + `an hourly series in this capture — ${traced.map(s => `${s.name} (${s.local ? 'this house'
          : `${s.km} km`}, ${Object.keys(s.series).map(k => H.metrics[k].label).join(', ')})`).join(' and ')}`
        + ` — so those rows have a trace with its min–max band and the others have one tick at the `
        + `15-minute mean, drawn at now. No trace was drawn where none was recorded.` },
      { id: 'sensors-note-dial', text: `The groups follow the dial: at resolution 4 all `
        + `${H.sensors.length} stations are in ${gt(4).occupied} cell, at 9 they are in `
        + `${gt(9).occupied}, and this node’s own ${gt(9).mine_in_my_cell} share one cell at every `
        + `resolution because they carry one coordinate. Regrouping changes which header a row sits `
        + `under and nothing in the row: a station’s number is its own, not its cell’s.` },
      { id: 'sensors-note-line', text: `${air.name.en}’s line, ${fmt(air.line ? air.line.value : null,
        H.metrics.pm25.dp)} ${air.unit}, is ${air.line ? air.line.source : 'not declared'} and is drawn `
        + `against PM2.5 only. ${heat.name.en}’s line${heat.line ? `, ${fmt(heat.line.value, 1)} `
          + `${heat.line.unit || heat.unit}, is for ${heat.metric}, which no station here reports `
          + `directly` : ' is not declared'}. Every other variable prints “no comparison yet” with the `
        + `reason, at the same size, in the same place — the number is never left to look compared.` },
      { id: 'sensors-note-sources', text: `Smart Citizen kits link to their public page on `
        + `smartcitizen.me. Stations that came through Bali Air Dispatch link to baliairdispatch.com, `
        + `whose attribution line — “Bali Air Dispatch, baliairdispatch.com” — is required and printed `
        + `under the list; each of those rows also names the network the station is on. `
        + (quiet.length ? `${quiet.length} of them (${quiet.map(s => s.name).join(', ')}) carry no `
          + `15-minute mean in this capture and are listed with a dash. ` : '')
        + `A station whose last reading is more than 60 minutes old is marked with the word “silent” `
        + `and the age — a word, not a colour. ${oldest > 60 ? '' : `None is in this capture; the oldest `
          + `reading is ${oldest} min.`}` },
      { id: 'sensors-note-mesh', text: `The Meshtastic device in this house`
        + `${H.radio && H.radio.mesh_sensor ? ` (${H.radio.mesh_sensor.name})` : ''} carries no `
        + `coordinate, so it falls in no cell and is not in this list. It appears under the radio.` },
    ];
  },

  /* The wall: this node's own stations and the chosen variable, in the column grammar wall.js lays
   * its own numbers in, so the three sit on one line with them and read at three metres. */
  wall(ctx) {
    const H = ctx.H, v = chosen(ctx, H.metrics), m = H.metrics[v];
    const L = lineFor(ctx, v);
    return H.sensors.filter(s => s.local).map(s => {
      const r = s.read[v];
      return `<div class="col" id="wall-st-${esc(s.sensor_id)}"><h3>${esc(s.name || s.sensor_id)}</h3>`
        + `<div class="line">` + (r
          ? `<span class="num${L.line && r.value > L.line.value ? ' crossed' : ''}"`
            + ` data-num="${esc(`${m.issue || v}.${s.sensor_id}.${v}`)}" data-cmp="${esc(L.cmp)}">`
            + `${esc(fmt(r.value, m.dp))}</span><small>${esc(m.unit)} · ${esc(m.label)}, this house</small>`
          : `<span class="none">—</span><small>${esc(m.label)}: nothing read</small>`)
        + `</div></div>`;
    }).join('');
  },
});

/* PORTED: this module's CSS is in dashboard.css, under a banner naming this file. */

});

/* ================================================================= h/mods/satellite.js ==== */
/* satellite · earth · observe
 *
 * Four real Sentinel-2 passes of this place — about 3 km across, 10 m a pixel, 2016 to 2025 — and
 * the one thing the satellite has said about it that the map did not already know: 1,874 buildings.
 *
 * Decision 2 of 8 September governs the frames. They are brightness matched across years so that
 * the only thing differing between them is structure; they say so beside the year and carry a
 * permanent provenance word; nothing in green, red, blue or orange sits on the photograph. The
 * `land` issue itself has no reading in this capture, and the section says that rather than
 * implying a year-over-year number the earth pack has not produced here.
 */
PAI_LOAD.push(function () {
'use strict';

const { esc, fmt, pill, row } = window.K;
const { H, km2 } = window.KH;
const { map, caption } = window.KMAP;

/* PORTED, and this is the one section that could not be carried over as drawn. The prototype loaded
 * four Sentinel PNGs out of the design repository. A node serves nothing but the names in
 * app/main.py's COMPANIONS allowlist, so those files do not exist here — and the node's own earth
 * pack is the more honest source anyway: GET /earth names the years it has fetched, and
 * GET /earth/frame.png?year= serves one. They are annual medians from somebody else's cluster, so
 * they are `partial`, which is the word the route's own docstring uses. A node that has fetched
 * none says so in one line rather than showing four broken frames. */
const IMAGERY = () => ((window.EARTH || {}).imagery || {});
const frameUrl = y => `/earth/frame.png?source=sentinel&year=${y}`;
const yearUrl = y => `/earth/year.png?year=${y}`;
const YEARS = () => (IMAGERY().sentinel || []);
const P = () => window.PLAN;

/* PORTED, and added back. Direction H's drawing showed somebody else's imagery and nothing of this
 * node's OWN satellite record — the AlphaEarth layer the earth pack keeps, a model's 64-number
 * description of every 10 m pixel flattened to one number and drawn in grey. GET /earth/year.png
 * serves one year of it and GET /earth names the years it has. app/main.py's own docstring is
 * emphatic that a page must never let a reader take one for the other, so they are two figures with
 * two provenance words, and this one says in its caption that it is a rendering of a model.
 *
 * The controls are hooked by data-sat=, never by ids: the same component is drawn more than once on
 * a page and an id cannot be. */
function record(ctx) {
  const years = (window.EARTH || {}).frames || [];
  const hint = (window.EARTH || {}).hint || '';
  if (!years.length) {
    return `<figure class="satown" data-component="satellite" id="sat-own" data-ref="sat-map">`
      + `<figcaption class="cap">This node has no record of its own yet: the earth pack fetches the `
      + `embeddings on command — <code>planetai run earth fetch</code>`
      + `${hint ? ` · ${esc(hint)}` : ''}</figcaption></figure>`;
  }
  const last = years[years.length - 1];
  return `<figure class="satown" data-component="satellite" id="sat-own" data-ref="sat-map">`
    + `<div class="frames">` + years.map(y =>
      `<img src="${yearUrl(y)}" data-sat="year" data-year="${y}"`
      + `${y === last ? ' class="on"' : ''} alt="this node's own AlphaEarth layer for ${y}, drawn in `
      + `grey: a model's description of every 10 m pixel, not a photograph">`).join('') + `</div>`
    + `<div class="satctl">`
    + `<button type="button" data-sat="play" aria-pressed="false">Play</button>`
    + `<input type="range" data-sat="slider" min="0" max="${years.length - 1}"`
    + ` value="${years.length - 1}" aria-label="year">`
    + `<button type="button" data-sat="mode" data-mode="years">Years</button>`
    + `<span class="yr" data-sat="label">${last}</span>`
    + pill('model', 'a model’s description of every 10 m pixel, drawn in grey')
    + `</div>`
    + `<figcaption class="cap">This node’s own AlphaEarth record, ${years.length} `
    + `${years.length === 1 ? 'year' : 'years'} · a rendering of a model, not a photograph · `
    + `<code>planetai run earth fetch</code> adds a year</figcaption></figure>`;
}

window.PAI.register({
  id: 'satellite', pack: 'earth', stage: 'observe', order: 30,
  title: 'What the satellite says',
  needs: ['PLAN', 'H3.claims'],
  render(ctx) {
    const land = ctx.ISS.land;
    const region = H.claims.find(c => c.key === 'region');
    const res = Math.max(ctx.RES, 8);
    const years = YEARS();
    const frames = years.map(y =>
      `<figure class="frame" data-component="satFrame" id="sat-${y}" data-ref="sat-map">`
      /* A frame that 404s must not delete its own figure: the caption two lines down still counts
         it, and a count with nothing under it is presence fabricated from absence. The figure stays
         and says what is missing. */
      + `<img src="${frameUrl(y)}" loading="lazy"`
      + ` onerror="this.hidden=true;this.parentNode.classList.add('missing')"`
      + ` alt="Sentinel-2 annual median, ${y}, the square this node keeps; brightness matched `
      + `across the years so only structure differs between them">`
      + `<p class="note miss">This node no longer has the ${y} pass on disk.</p>`
      + `<figcaption><span class="yr">${y}</span>${pill('partial', 'an annual median from '
        + 'somebody else’s cluster, not a pass this node made')}</figcaption></figure>`).join('');
    const strip = years.length
      ? `<div class="satstrip" id="sat-strip" data-component="satStrip" data-ref="sat-map">`
        + frames + `</div>`
        + `<p class="cap">Sentinel-2 annual medians · ${years.length} `
        + `${years.length === 1 ? 'year' : 'years'} · ${esc((IMAGERY().credit || []).join(' '))}</p>`
      : `<p class="note" id="sat-strip" data-component="satStrip" data-ref="sat-map">This node has `
        + `no satellite passes on disk yet, so there are none to show. `
        + `${esc((window.EARTH || {}).hint || 'The earth pack fetches them on command.')}</p>`;
    return strip + record(ctx)
      + `<div class="two-up">`
      + `<figure class="gridwrap mapwrap" id="sat-map" data-component="satMap" data-ref="sat-strip">`
      + map(res, { satOnly: true,
        label: `the ${P().counts.sat} buildings one satellite pass found that OpenStreetMap does not `
          + `have, over the outlines of the ones it does` })
      + `<div class="gridkey"><span><i class="sat-only"></i>only the satellite knows it is there`
      + `</span><span><i class="none"></i>on the map already</span></div>`
      + `<figcaption class="cap">${esc(caption(res))}</figcaption></figure>`
      + `<div class="reads">`
      + row({ id: 'sat-count', component: 'satCount', ref: 'sat-map',
        cols: 'minmax(0,210px) minmax(0,1fr) auto',
        left: `<span class="who"><b>Buildings only the satellite knows</b>`
          + `<span class="m">confidence 0.3 to 1.0</span></span>`,
        line: `Against ${P().counts.buildings.toLocaleString()} OpenStreetMap buildings on the same `
          + `ground.`,
        qty: [{ num: 'claim.sat.buildings', value: P().counts.sat.toLocaleString(),
          cmp: `against ${P().counts.buildings.toLocaleString()} the map already had` }] })
      + row({ id: 'sat-square', component: 'satSquare', ref: 'sat-map',
        cols: 'minmax(0,210px) minmax(0,1fr) auto',
        left: `<span class="who"><b>The square this node keeps</b>`
          + `<span class="m">EARTH_RADIUS_M=5000, 10 m a pixel</span></span>`,
        line: `packs/earth/pack.yaml · fetched once on command, compared with arithmetic.`,
        qty: [{ num: 'claim.region.km2', value: `${region.area_km2} km²`,
          cmp: `against the ${H.claims[0].area_km2} km² the widest source here covers` }] })
      /* `native` is null when the claim has no footprint: geometry.py's _claim() publishes an empty
         covering for a radius of zero or less rather than inventing a metre nobody declared, and
         EARTH_RADIUS_M=0 is a keeper's setting away. Dereferencing it turned this whole section into
         its "did not render" line, so the row says what the setting says instead. */
      + (region.native
        ? row({ id: 'sat-grain', component: 'satGrain', ref: 'sat-map',
          cols: 'minmax(0,210px) minmax(0,1fr) auto',
          left: `<span class="who"><b>At the grain its own data has</b>`
            + `<span class="m">resolution ${region.native.res}</span></span>`,
          line: `${region.native.cells.toLocaleString()} cells; compactCells leaves `
            + `${region.native.compact.toLocaleString()} covering the same ground exactly.`,
          qty: [{ num: 'claim.region.saving', value: `${region.native.saving}×`,
            cmp: `smaller, for the same ground` }] })
        : `<p class="note" id="sat-grain" data-component="satGrain" data-ref="sat-map">`
          + `${esc(region.declared)} covers no ground, so there is no covering to compact and no `
          + `grain to state.</p>`)
      + `<p class="cap">${esc(land.state === 'none'
        ? `land: ${land.reason_text[ctx.LOC]} in this capture`
        : `land_change_yoy ${fmt((land.stack.room || {}).value, land.dp)} ${land.unit}`)}</p>`
      + `</div></div>`;
  },
  notes(ctx) {
    const region = H.claims.find(c => c.key === 'region');
    return [
      { id: 'sat-matched', text: 'The frames are brightness matched across years. Measured on '
        + 'the passes as delivered, mean luminance ran 81, 116, 94, 108 and greenness flipped sign on '
        + '2019 — season and haze, not change — so a loop of the raw frames reads as something '
        + 'happening that did not. After matching every channel to 2016 the only thing that differs '
        + 'between frames is structure. That changes pixel values, which is why the page says so '
        + 'beside the year rather than passing the frames off as raw medians.' },
      { id: 'sat-colour', text: 'Nothing in green, red, blue or orange sits on the photograph. The '
        + 'photograph is a ground, never a backdrop for coloured marks — on this page green means a '
        + 'loop closed, red means a signal got worse and orange means what only the satellite knows, '
        + 'and a green-and-brown image would borrow all three.' },
      { id: 'sat-orange', text: `Orange means one thing on every page here: what only the satellite `
        + `knows. ${P().counts.sat.toLocaleString()} buildings on this ground are in a satellite pass `
        + `and not in OpenStreetMap, each with the confidence the pass gave it, drawn over the `
        + `hairline outlines of the ${P().counts.buildings.toLocaleString()} the map already had.` },
      { id: 'sat-compaction', text: region.native
        ? `EARTH_RADIUS_M=5000 at 10 m a pixel is resolution `
          + `${region.native.res}. polygonToCells on that square returns `
          + `${region.native.cells.toLocaleString()} cells and compactCells returns `
          + `${region.native.compact.toLocaleString()} covering exactly the same ground — `
          + `${region.native.saving} times smaller. This is the only place in three rounds where an H3 `
          + 'operation does something the node could not already do by hand, and it is the answer to '
          + 'how a covering this fine is ever published.'
        : `${region.declared} declares no ground, so this node has no covering of the square to `
          + 'compact and nothing to say about what compaction saves here.' },
      { id: 'sat-land', text: ctx.ISS.land.state === 'none'
        ? 'The earth pack has no reading in this capture. What is in the section is what the '
          + 'satellite has already said about this place — the passes, and the buildings it found — '
          + 'and not a year-over-year number it has not produced here.'
        : 'The land_change_yoy figure is the earth pack’s own, computed on this node from the '
          + 'embeddings it keeps.' },
    ];
  },
});

});

/* ================================================================= h/mods/reticulum.js ==== */
/* reticulum · reticulum · observe
 *
 * What this node says about where it is over the radio, and what it has heard other nodes say. The
 * whole of it is a cell: Reticulum announces the H3 cell this node stands in at
 * RETICULUM_PRESENCE_RES, never finer than PRESENCE_RES_FLOOR, never a coordinate. A peer is
 * therefore known as a cell and a rough distance — which is the privacy property the scheme exists
 * for, and the thing a drawing of it has to show rather than tidy away with a pin.
 *
 * This is the first pack section in the folder that is not the renderer's own: it registers with the
 * page contract exactly the way a Meshtastic section, an open hardware manager, or a community pack
 * would, and the page knows nothing about it except what it declares here.
 */
PAI_LOAD.push(function () {
'use strict';

const { esc, fmt, age, row } = window.K;
const { H, address, km2, edge } = window.KH;
const R = H.radio;

window.PAI.register({
  id: 'reticulum', pack: 'reticulum', stage: 'observe', order: 40,
  title: 'What leaves this house by radio',
  needs: ['H3.radio'],
  render(ctx) {
    const pr = ctx.S.peer;
    const cands = R.candidates.length;
    const drawing = `<figure class="gridwrap" id="radio-map" data-component="radioMap"`
      + ` data-ref="radio-rows">`
      /* PORTED: the drawing had a projected cell set of its own. GET /issues publishes the announce
         resolution's plate already — it is inside the two steps nav publishes at every resolution —
         so this draws the same cells from the node's own geometry rather than a second copy. */
      + ctx.KMAP.map(R.res, { cells: [R.mine].concat(R.candidates), ref: 'radio-rows',
        label: `the cell this node announces itself in at resolution ${R.res}, and the `
          + `${cands} cells a peer ${R.peer_km} km away could be in` })
      + `<div class="gridkey"><span><i class="own"></i>what this node announces</span>`
      + `<span><i class="read"></i>where the peer could be</span>`
      + `<span><i class="none"></i>heard nothing</span></div>`
      + `<figcaption class="cap">resolution ${R.res} · ${esc(edge(R.edge_m))} to an edge · `
      + `${esc(km2(R.area_m2))}</figcaption></figure>`;
    const rows = `<div class="reads" id="radio-rows" data-ref="radio-map">`
      + row({ id: 'radio-reticulum', component: 'announce', ref: 'radio-map',
        cols: 'minmax(0,210px) minmax(0,1fr) auto',
        left: `<span class="who"><b>What this node announces</b>`
          + `<span class="m">RETICULUM_PRESENCE_RES ${R.res}</span></span>`,
        line: `The cell, and nothing else. Never a coordinate, never finer than resolution `
          + `${H.settings.PRESENCE_RES_FLOOR}.`,
        qty: [{ num: 'nav.announce.km2', value: km2(R.area_m2),
          cmp: `against ${km2(H.ladder[H.publication.res].own_area_m2)}, the grain GET /health rounds to` }],
      })
      + `<div class="sub-addr">${address(R.mine, R.res)}</div>`
      + (pr ? row({ id: 'radio-peer', component: 'peers', ref: 'radio-map',
        cols: 'minmax(0,210px) minmax(0,1fr) auto',
        left: `<span class="who"><b>${esc(pr.node)}</b><span class="m">heard `
          + `${esc(age(pr.heard_minutes_ago))}</span></span>`,
        line: `Announced, and this node was listening. A cell and a distance; read it as a direction `
          + `and a rough reach.`,
        qty: [{ num: 'peer.km', value: `${pr.km} km`,
          cmp: `between two cells ${edge(R.edge_m)} to an edge` },
        { num: 'peer.pm25', value: `${fmt(pr.value.value, pr.value.dp)} ${pr.value.unit}`,
          cmp: `no comparison yet · a peer is never compared with this node's own reading` }],
      }) : `<p class="cap" data-ref="radio-map">No other node has been heard.</p>`)
      + `</div>`;
    return `<div class="two-up">${drawing}${rows}</div>`;
  },
  wall(ctx) {
    const pr = ctx.S.peer;
    if (!pr) return '';
    return `<div class="col" data-component="peers" data-ref="wall-lead">`
      + `<h3 data-role="wall-issue">${esc(pr.node)}, heard</h3>`
      + `<div class="line"><span class="num" data-num="peer.km" data-cmp="a cell and a distance, `
      + `never a point">${pr.km}</span><small>km · resolution ${R.res}</small></div></div>`;
  },
  notes(ctx) {
    const pr = ctx.S.peer;
    return [
      { id: 'reticulum-cell', text: `Reticulum announces the H3 cell this node is in at resolution `
        + `${R.res} — ${edge(R.edge_m)} to an edge, ${km2(R.area_m2)} — and nothing else. It is never `
        + `finer than resolution ${H.settings.PRESENCE_RES_FLOOR}, which is the floor no settings box `
        + 'may pass. That cell is the whole of what a stranger on the radio learns about where this '
        + 'node is.' },
      { id: 'reticulum-peer', text: `The fixture kept the peer’s resolution and its distance and not `
        + `the cell it announced, so the drawing shows all ${R.candidates.length} cells `
        + `${R.peer_km} km could be in. That is not a gap in the drawing — it is the shape of what a `
        + 'radio announce actually tells you. A page that put a pin at 61 km on a bearing it was never '
        + 'sent would be inventing the one thing the scheme refuses to send.' },
      ...(pr ? [{ id: 'reticulum-never', text: pr.never[ctx.LOC] }] : []),
      { id: 'reticulum-pack', text: 'This section is a pack’s, not the page’s: it registered itself '
        + 'with the page contract the way any pack does, and the page knows nothing about Reticulum '
        + 'beyond what the section declares. A node without the reticulum pack has no such section; '
        + 'a node with a new radio adds a file.' },
    ];
  },
});

});

/* ================================================================= h/mods/meshtastic.js ==== */
/* meshtastic · meshtastic · observe
 *
 * The LoRa mesh in this house. One device, reporting over Meshtastic through a gateway on the WiFi;
 * it carries no coordinate at all, so it is in this node's cell because this node is, and it is on
 * no grid drawing in this folder for that reason. What it does carry — battery, gas, air quality
 * index, the LoRa channel's utilisation — is what a radio in a room actually knows.
 *
 * A pack section, registered the way any pack's is. The Meshtastic pack on the node parses the
 * gateway's JSON (app/sources.py, meshtastic_message); this is what that parsing is for.
 */
PAI_LOAD.push(function () {
'use strict';

const { esc, fmt, age, row } = window.K;
const { H } = window.KH;
const R = H.radio;

/* The device's own readings: it has no coordinate, so it is not in H3.sensors, and make-h3.mjs
 * carries its 15-minute means on the radio record instead. */
const READ = () => R.mesh_reads || [];

window.PAI.register({
  id: 'meshtastic', pack: 'meshtastic', stage: 'observe', order: 41,
  title: 'The mesh in this house',
  needs: ['H3.radio.mesh'],
  render(ctx) {
    const m = R.mesh, d = R.mesh_sensor;
    const last = age(Math.round((Date.parse(ctx.S.base.captured_utc) - Date.parse(m.last)) / 60000));
    const reads = READ();
    const shown = reads.filter(r => H.metrics[r.metric]).slice(0, 4);
    return `<div class="reads" id="mesh-rows" data-ref="radio-map">`
      + row({ id: 'mesh-gateway', component: 'mesh', ref: 'radio-map',
        cols: 'minmax(0,210px) minmax(0,1fr) auto',
        left: `<span class="who"><b>${esc(d ? d.name : 'the mesh')}</b>`
          + `<span class="m">${esc(m.root_topic)} · ${esc(m.gateway)}</span></span>`,
        line: `Reports over LoRa and carries no position: it is in this node's cell because this `
          + `node is. Last heard ${esc(last)}.`,
        qty: [{ num: 'nav.mesh.packets', value: String(m.packets),
          cmp: `packets since this node started` }],
      })
      + (shown.length ? shown.map(r => {
        const mt = H.metrics[r.metric];
        return row({ id: `mesh-${esc(r.metric)}`, component: 'meshReading', ref: 'mesh-gateway',
          cols: 'minmax(0,210px) minmax(0,1fr) auto',
          left: `<span class="who"><b>${esc(mt.label)}</b><span class="m">${esc(r.metric)}</span></span>`,
          line: `15-minute mean from the device in the house.`,
          qty: [{ num: `mesh.${esc(r.metric)}`, value: `${fmt(r.mean_15m, mt.dp)} ${mt.unit}`,
            cmp: mt.issue && ctx.ISS[mt.issue] && ctx.ISS[mt.issue].line
              ? `against the line, ${fmt(ctx.ISS[mt.issue].line.value, mt.dp)} ${ctx.ISS[mt.issue].unit}`
              : `no comparison yet · no line is declared for ${mt.label}` }],
        });
      }).join('') : '')
      + `</div>`;
  },
  notes() {
    const d = R.mesh_sensor;
    return [
      { id: 'mesh-noposition', text: `${d ? d.name : 'The mesh device'} carries no latitude or `
        + 'longitude, which is why it appears on no grid drawing here: a station with no coordinate '
        + 'has no cell of its own, and the page will not put it in one by assumption. It is in this '
        + 'node’s cell because this node is.' },
      { id: 'mesh-what', text: 'What a LoRa device in a room actually knows: its battery, a gas '
        + 'resistance, an air quality index, how busy its radio channel is. The Meshtastic pack turns '
        + 'the gateway’s JSON into readings the node can keep; a gateway with JSON output off is the '
        + 'commonest reason this section is empty on a new node, and `planetai meshtastic` says how '
        + 'to turn it on.' },
      { id: 'mesh-pack', text: 'A pack section, and a small one on purpose: it shows the shape a '
        + 'community pack’s contribution takes — a file that registers a title, a stage, what it '
        + 'needs, and what it says.' },
    ];
  },
});

});

/* ================================================================= h/mods/hardware.js ==== */
/* hardware · hardware · observe
 *
 * The devices this house actually runs, and the hook for the two things Tomas named as coming next:
 * an open hardware manager, and the capacity to make locally.
 *
 * What is real here is the list. Three Smart Citizen kits and one Meshtastic node are what node #1
 * has on its own ground, and everything said about them — source, indoors or out, what each
 * measures, when it last spoke — is in the fixture. Smart Citizen and Meshtastic are both open
 * hardware, which is a fact about the devices and not a claim this page makes for them.
 *
 * What is not real yet is the manager. The row that would link a device to its design files, its
 * firmware, its bill of materials and the nearest place that could make or mend it needs a pack
 * this node does not have, and the contract's answer to that is one honest line rather than a
 * blank: `needs: ['OHM']` on a second section that is not here. This file is the shape the
 * hardware pack's contribution takes; the manager is the pack.
 */
PAI_LOAD.push(function () {
'use strict';

const { esc, age, row } = window.K;
const { H, address } = window.KH;

/* The devices on this node's own ground: every station marked local, plus the mesh device, which
 * carries no coordinate and is therefore not in H3.sensors at all. */
function devices() {
  const own = H.sensors.filter(s => s.local).map(s => ({
    id: s.sensor_id, name: s.name || s.sensor_id, source: s.label, url: s.url,
    where: s.indoor ? 'indoors' : 'outdoors', metrics: Object.keys(s.read || {}),
    silent: Math.max(0, ...Object.values(s.read || {}).map(r => r.silent_minutes || 0)),
    cell: s.chain, open: s.source === 'smartcitizen',
  }));
  const m = H.radio && H.radio.mesh_sensor;
  if (m) own.push({
    id: m.sensor_id, name: m.name, source: 'Meshtastic', url: null,
    where: m.indoor ? 'indoors' : 'outdoors',
    metrics: (H.radio.mesh_reads || []).map(r => r.metric), silent: null, cell: null, open: true,
  });
  return own;
}

window.PAI.register({
  id: 'hardware', pack: 'hardware', stage: 'observe', order: 45,
  title: 'The hardware in this house',
  needs: ['H3.sensors'],
  render(ctx) {
    const list = devices();
    const cols = 'minmax(0,210px) minmax(0,1fr) auto';
    return `<div class="reads" id="hardware-rows" data-ref="sensors">`
      + list.map(d => row({
        id: `hw-${esc(d.id)}`, component: 'device', ref: 'hardware-rows', cols,
        /* The link lives in the left-hand block, which row() places as HTML; the line is text and
         * row() escapes it, so an anchor put there prints as angle brackets — measured, once. */
        left: `<span class="who"><b>${esc(d.name)}</b><span class="m">${esc(d.source)}`
          + `${d.open ? ' · open hardware' : ''}`
          + (d.url ? ` · <a href="${esc(d.url)}" target="_blank" rel="noopener">its page</a>` : '')
          + `</span></span>`,
        line: `${d.where} · measures ${d.metrics.length ? d.metrics.join(', ')
          : 'nothing this page lists'}`
          + (d.cell ? ` · ${d.cell[ctx.RES]}` : ' · no coordinate: in this node’s cell because this node is'),
        lineRole: 'device',
        qty: [{ num: `hardware.${esc(d.id)}.metrics`, value: String(d.metrics.length),
          cmp: d.silent == null ? 'metrics · no silence figure for a device with no coordinate'
            : d.silent > 60 ? `metrics · silent ${age(d.silent)}` : `metrics · heard ${age(d.silent)}` }],
      })).join('')
      + row({
        id: 'hw-manager', component: 'absent', ref: 'hardware-rows', cols, cls: 'absent',
        left: `<span class="who"><b>Open hardware manager</b><span class="m">not connected</span></span>`,
        line: 'Design files, firmware, bill of materials, and where nearby a device could be made or '
          + 'mended. A pack this node does not have; when it does, it registers here.',
        qty: [{ num: 'hardware.manager.devices', value: `0 of ${list.length}`,
          cmp: `devices with their design files on this node` }],
      })
      + `</div>`;
  },
  notes() {
    const list = devices();
    return [
      { id: 'hardware-real', text: `What is real here is the list: ${list.length} devices on this `
        + 'node’s own ground, and everything said about them is in the fixture — source, indoors or '
        + 'out, what each measures, when it last spoke. Smart Citizen and Meshtastic are both open '
        + 'hardware, which is a fact about the devices and not a claim this page makes for them.' },
      { id: 'hardware-manager', text: 'The manager row is the hook Tomas asked for and nothing more: '
        + 'an open hardware manager and the capacity to make locally are the next packs, not this '
        + 'one. When they exist they register a section the way every section here did, and this row '
        + 'stops saying "not connected". Until then the contract’s rule holds — a missing pack is one '
        + 'honest line, never a blank.' },
      { id: 'hardware-shape', text: 'This is the shape a community pack’s contribution takes: a '
        + 'title, a stage, what it needs, what it says, and its notes. A node that adds a device adds '
        + 'a row; a node that writes a pack adds a file; proposing either back is sending the file.' },
    ];
  },
});

});

/* ================================================================= h/mods/claims.js ==== */
/* claims · core · decide
 *
 * Whose word covers how much ground, and how coarse it is by the time it says it. This is the
 * section the dial exists for: a model that samples one point and a probe on a shelf both produce
 * one number, and at the grain the dial is standing on they cover 4,396 cells and 1. Resolution is
 * provenance, and this is where that stops being a footnote.
 *
 * Every footprint is a number a pack or a preset already declares — make-h3.mjs names the file each
 * came from — and the covering was computed at the grain the source itself has and then compacted.
 * The bar under each card is what compactCells left behind: mostly one grain in the middle, striped
 * at the rim.
 */
PAI_LOAD.push(function () {
'use strict';

const { esc } = window.K;
const { H, grid, km2 } = window.KH;

function claimCard(ctx, c) {
  const RES = ctx.RES;
  const n = c.cells_at[RES];
  const mine = H.claims[H.claims.length - 1];
  const bars = Object.entries(c.drawn.by_res).sort((a, b) => a[0] - b[0]);
  const total = bars.reduce((a, [, v]) => a + v, 0);
  return `<section class="claim" id="claim-${esc(c.key)}" data-component="claim" data-ref="dial">`
    + `<div class="pic gridwrap">`
    + grid(c.draw, { own: [], read: c.cells,
      label: `${c.name}: ${c.drawn.compact} cells cover ${c.area_km2} km²` })
    + `<div class="cap">${c.drawn.compact} cells, resolutions `
    + `${bars[0][0]}–${bars[bars.length - 1][0]}</div></div>`
    + `<div><h3>${esc(c.name)}</h3>`
    + `<p class="what">${esc(c.what)}</p>`
    + `<div class="facts">`
    + `<div class="fact"><span class="k">covers</span><span class="v">`
    + `<span data-num="claim.${esc(c.key)}.km2" data-cmp="against ${esc(String(mine.area_km2))} `
    + `km², the smallest thing this node says anything about">${esc(String(c.area_km2))}</span> `
    + `km²</span></div>`
    + `<div class="fact"><span class="k">cells at resolution ${RES}</span><span class="v">`
    + `<span data-num="claim.${esc(c.key)}.cells" data-cmp="against 1 cell, which is what a probe `
    + `in this room covers">${n.toLocaleString()}</span></span></div>`
    + (c.native ? `<div class="fact"><span class="k">its own grain</span><span class="v">`
      + `<span data-num="claim.${esc(c.key)}.native" data-cmp="resolution ${c.native.res}, `
      + `${esc(km2(H.ladder[c.native.res].own_area_m2))} a cell">res ${c.native.res}</span>`
      + `</span></div>` : '')
    + `</div>`
    + `<div class="grainbar" role="img" aria-label="${esc(bars.map(([r, v]) =>
      `${v} cells at resolution ${r}`).join(', '))}">`
    + bars.map(([r, v]) => `<i style="width:${(100 * v / total).toFixed(1)}%;`
      + `background:color-mix(in srgb, var(--cells) ${Math.min(60, (r - 4) * 12)}%, transparent)"`
      + ` title="${v} cells at resolution ${r}"></i>`).join('') + `</div>`
    + `<p class="decl">${esc(c.declared)} · ${esc(c.where)}</p></div></section>`;
}

window.PAI.register({
  id: 'claims', pack: 'core', stage: 'decide', order: 10,
  title: 'Whose word, over how much ground',
  needs: ['H3.claims'],
  render(ctx) {
    /* Every footprint here is a circle or a square drawn around this node. With no coordinates they
       are six coverings of the Gulf of Guinea, and the card that says how much ground a word covers
       would be covering somebody else's water. The declarations are still true; where they sit is
       not known. */
    if (!ctx.KH.sited()) {
      return `<p class="note" id="claims-unsited" data-component="absent" data-ref="claims">This `
        + `node has no coordinates, so there is no ground for these claims to cover. The footprints `
        + `are still declared — ${H.claims.map(c => c.declared).join(' · ')} — and each gets its `
        + `covering as soon as NODE_LAT and NODE_LON are set.</p>`;
    }
    return `<div class="claimgrid">${H.claims.map(c => claimCard(ctx, c)).join('')}</div>`;
  },
  wall(ctx) {
    /* The comparison the dial exists to make, as four columns a wall can carry. */
    return H.claims.slice(0, 4).map(c =>
      `<div class="col" data-component="claim" data-ref="wall-lead">`
      + `<h3 data-role="wall-issue">${esc(c.name)}</h3>`
      + `<div class="line"><span class="num" data-num="claim.${esc(c.key)}.cells"`
      + ` data-cmp="cells of resolution ${ctx.RES}; a probe in this room covers 1">`
      + `${c.cells_at[ctx.RES].toLocaleString()}</span><small>cells · ${esc(c.declared)}</small>`
      + `</div></div>`).join('');
  },
  notes() {
    return [
      { id: 'claims-declared', text: 'Every footprint here is a number a pack or a preset already '
        + 'declares — COAST_MAX_KM, BAD_RADIUS_KM, EARTH_RADIUS_M at 10 m a pixel, PLACE_RADIUS_M, '
        + 'LOCAL_RADIUS_M, and the three decimals GET /health rounds a coordinate to, which is about '
        + '110 m and the finest grain anything from this node may honestly be drawn at. Not one '
        + 'radius on this page was chosen by it.' },
      { id: 'claims-order', text: 'The cards are ordered by the ground one word covers, widest '
        + 'first. Reading down them is reading from a model that speaks for the sea to a probe on a '
        + 'shelf, and the number that changes with the dial — cells at this resolution — is how many '
        + 'cells of the grain you are standing on that word has to cover to say its one thing.' },
      { id: 'claims-note', text: H.claims.filter(c => c.note).map(c => `${c.name}: ${c.note}.`)
        .join(' ') },
      { id: 'claims-model', text: 'The one source with no declared footprint is the model point, '
        + `which covers ${H.claims[0].cells_at[8].toLocaleString()} cells at resolution 8 against `
        + 'the one a probe in this room covers. Nothing in the product says how big a model point’s '
        + 'word is, and the page will not guess for it.' },
    ];
  },
});

});

/* ================================================================= h/mods/grain.js ==== */
/* grain · core · decide
 *
 * What each stop of the dial is worth, end to end: what one cell of it holds, how many cells the
 * fourteen stations fall in there, and which side of the two lines the product already draws it is
 * on. The table is evidence and not reading, so it folds; the finding it produced is printed above
 * it, because that finding is the thing the dial was built to show and nothing in rounds one or two
 * could have shown it: resolutions 7 to 10 are one row repeated four times.
 */
PAI_LOAD.push(function () {
'use strict';

const { esc } = window.K;
const { H, km2, edge } = window.KH;

function table(ctx) {
  const flat = new Set(H.grain_table.filter(g => g.occupied === 9).map(g => g.res));
  /* PORTED: the table is wider than 390 px and scrolls inside its own box. A box that scrolls and
     cannot be focused cannot be scrolled from a keyboard — the finding that put tabindex on the
     page before this one, re-made here. */
  return `<div class="tblwrap" tabindex="0" role="region" aria-label="all eleven grains">`
    + `<table class="tbl" id="grain-table" data-component="grainTable" data-ref="dial">`
    + `<thead><tr><th>resolution</th><th>one cell</th><th>edge</th>`
    + `<th>cells the ${H.sensors.length} stations fall in</th><th>in this node's own cell</th>`
    + `<th></th></tr></thead><tbody>`
    + H.grain_table.map(g => `<tr class="${g.res === ctx.RES ? 'picked' : ''}${flat.has(g.res)
      ? ' flat' : ''}"><td class="mono">${g.res}</td><td class="mono">${esc(km2(g.area_m2))}</td>`
      + `<td class="mono">${esc(edge(g.edge_m))}</td><td class="mono">${g.occupied}</td>`
      + `<td class="mono">${g.in_my_cell}</td>`
      + `<td>${g.may_leave ? 'may leave' : ''}${g.finer_than_published
        ? 'finer than this node says where it is' : ''}</td></tr>`).join('')
    + `</tbody></table></div>`
    + `<p class="cap">Grey rows are the flat run. The row in bold is where the dial stands.</p>`;
}

window.PAI.register({
  id: 'grain', pack: 'core', stage: 'decide', order: 20,
  title: 'What each grain is worth',
  needs: ['H3.grain_table'],
  render(ctx) {
    const flat = H.grain_table.filter(g => g.occupied === 9);
    return `<p class="honest" id="flat-run" data-component="finding" data-ref="dial">Resolutions `
      + `${flat[0].res} to ${flat[flat.length - 1].res} are one row repeated ${flat.length} times. `
      + `Each is seven times finer than the one above it — `
      + `<span data-num="grain.flat.ratio" data-cmp="the area ratio across ${flat.length - 1} steps `
      + `of seven">${Math.pow(7, flat.length - 1).toLocaleString()}</span> times smaller by area over `
      + `the ${flat.length} — and every one of them answers "who is near me" with the same `
      + `${flat[0].occupied} cells and the same ${flat[0].mine_in_my_cell} sensors.</p>`
      + `<details class="fold"><summary>All eleven grains, and what each is worth</summary>`
      + table(ctx) + `</details>`;
  },
  notes() {
    const flat = H.grain_table.filter(g => g.occupied === 9);
    return [
      { id: 'grain-flat', text: `Past resolution ${flat[0].res}, on this node on this day, grain is `
        + 'precision with no information in it. Four stops of the dial, each seven times finer than '
        + 'the last, and the answer to "who is near me" does not change: the same nine cells hold '
        + 'something and the same three sensors sit in this node’s own cell. Nothing in the first two '
        + 'rounds of drawings could have shown this, because nothing in them varied the grain.' },
      { id: 'grain-lines', text: `The two marks on the dial are the product’s own lines, not this `
        + `page’s. Resolution ${H.settings.PRESENCE_RES_FLOOR} and coarser may leave this machine — `
        + `it is PRESENCE_RES_FLOOR in app/main.py, the finest any node may announce. Past resolution `
        + `${H.publication.res} is finer than this node is willing to say where it is: GET /health `
        + 'rounds a coordinate to three decimals, about 110 m, and no reading from it may be drawn '
        + 'finer than that.' },
      { id: 'grain-folded', text: 'The eleven-row table is folded because it is evidence and not '
        + 'reading. Measured, it was half a screen of a page that was already long, and the one '
        + 'sentence it exists to support is printed above it in full.' },
    ];
  },
});

});

/* ================================================================= h/mods/asks.js ==== */
/* asks · core · act
 *
 * What this node has asked of whom. The loop's third stage is the one a household actually feels:
 * a rule crossed a line, the node said so on Telegram, and somebody either did something or did
 * not. This section is the ledger of that — the open ask, the asks sent in the window, and the
 * funnel they went down — so that "act" is a thing on the page and not a verb in a slogan.
 *
 * The green button is the one control on the page that is not the dial, and it is drawn where the
 * kit draws it: in the ask strip, never anywhere else.
 */
PAI_LOAD.push(function () {
'use strict';

const { esc, fmt, age, pill, row, funnel, ask } = window.K;

/* The alerts in the fixture that asked for something, most recent first. `level: act` is the rule
 * saying a person should do something; `info` and `warn` said something and asked nothing. They
 * come through h3.js, which make-h3.mjs fills from the fixture: the id, the rule, the first line. */
const A = () => (window.H3 && window.H3.asks) || { acts: [], actions: [], levels: {} };
const ACTS = () => A().acts.slice().sort((a, b) => b.ts.localeCompare(a.ts));

window.PAI.register({
  id: 'asks', pack: 'core', stage: 'act', order: 10,
  title: 'What this node has asked',
  /* PORTED: the prototype also needed SNAP.funnel, which was one of its three synthetic
     contributions — no endpoint on this node computes a stage split or the 2x2. The ledger is the
     node's own (GET /issues publishes `asks`), so the section stands on that and draws the funnel
     only where there is one. */
  needs: ['H3.asks'],
  render(ctx) {
    const S = ctx.S, ISS = ctx.ISS;
    const acts = ACTS();
    const acted = new Set(A().actions.map(x => x.alert_id));
    const byRule = {};
    for (const a of acts) (byRule[a.rule_id] = byRule[a.rule_id] || []).push(a);
    const rules = Object.entries(byRule).sort((a, b) => b[1].length - a[1].length);
    const captured = Date.parse(S.base.captured_utc);
    return `<div class="two-up">`
      + `<div>`
      + ctx.ORDER.filter(k => ISS[k] && (ISS[k].open_asks || []).length).map(k => ask(k, ISS[k], 'asks-rows')).join('')
      + (ctx.ORDER.some(k => ISS[k] && (ISS[k].open_asks || []).length) ? ''
        : ask(S.issues.headline, ISS[S.issues.headline], 'asks-rows'))
      + `<div class="reads" id="asks-rows" data-ref="funnel">`
      + rules.map(([rule, list]) => {
        const [pack, name] = rule.split('/');
        const answered = list.filter(a => acted.has(a.id)).length;
        const latest = list[0];
        return row({ id: `ask-rule-${esc(name)}`, component: 'askRule', ref: 'funnel',
          cols: 'minmax(0,210px) minmax(0,1fr) auto',
          left: `<span class="who"><b>${esc(name.replace(/_/g, ' '))}</b>`
            + `<span class="m">${esc(pack)} · last ${esc(age(Math.round((captured
              - Date.parse(latest.ts)) / 60000)))}</span></span>`,
          line: esc(String(latest.text || '').split('\n')[0].slice(0, 140)),
          qty: [{ num: `asks.${esc(name)}.sent`, value: String(list.length),
            cmp: `asks sent in the window, of which ${answered} were answered` }],
        });
      }).join('')
      + `</div></div>`
      + `<div>${S.funnel ? funnel()
        : `<p class="note" id="funnel" data-ref="asks-rows">This node counts what it asked and what `
          + `was answered; it does not keep the stages in between, so there is no funnel to draw.</p>`
      }</div></div>`;
  },
  wall(ctx) {
    const acts = ACTS();
    /* GET /rho is its own route and may be slow, refused or absent. The contract's per-section catch
       would swallow a throw here and the fragment would simply vanish from the wall, which is the
       silence this guard exists to remove: the count of asks is this section's own and is known
       either way, so it is printed, and the comparison says plainly what is not on this node. */
    const r = ctx.S.rho;
    return `<div class="col" data-component="asksCount" data-ref="wall-lead">`
      + `<h3 data-role="wall-issue">Asks sent</h3>`
      + `<div class="line"><span class="num" data-num="asks.sent" data-cmp="${r
        ? `against ${r.acted} answered`
        : 'how many were answered is not on this node right now: GET /rho did not come back'}">`
      + `${acts.length}</span><small>${r ? `in ${r.window_days} days` : 'in the window'}`
      + `</small></div></div>`;
  },
  notes(ctx) {
    const f = ctx.S.funnel;
    return [
      { id: 'asks-what', text: 'An ask is a rule crossing a line and the node saying so to a '
        + 'person, on Telegram. It is the only thing on this page that is addressed to somebody; '
        + 'everything else is addressed to nobody in particular. "Nothing has been asked" and '
        + '"nothing to do" are two different sentences, and the ask strip says which one is true.' },
      f ? { id: 'asks-funnel', text: `The funnel counts one thing four times: how many asks reached a `
        + `phone, how many were acknowledged, how many led to something being done, how many closed `
        + `— and how long each step took. ${f.source}. The 2×2 under it splits answered against `
        + 'unanswered by whether the reading came back under the line, which is the only honest way '
        + 'to ask whether acting on an ask made a difference.' }
        : { id: 'asks-funnel', text: 'There is no funnel here. This node records that an ask was sent '
          + 'and that somebody answered it, and nothing about the stages in between — reached, '
          + 'acknowledged, deployed, closed. Drawing four stages from two facts would be inventing '
          + 'the two in the middle.' },
      { id: 'asks-button', text: 'The green button is the one control on the page that is not the '
        + 'dial. It is a response, so it is green — the layer’s rule is that orange means what only '
        + 'the satellite knows and nothing else — and it is drawn in the ask strip and nowhere else.' },
    ];
  },
});

});

/* ================================================================= h/mods/measure.js ==== */
/* measure · core · measure
 *
 * Whether it worked, and how long it took. The loop's last stage and the one that makes it a loop:
 * ρ, the share of asks that were answered; the median minutes from ask to answer; and the day the
 * node's own probes just had, which is the reading coming back — or not — after somebody acted.
 *
 * Nothing here is a gauge. ρ is a row of rings, answered first, and the numeral beside it says the
 * same thing in words; the day is a trace with its axis, its origin, its line and its text
 * alternative. The four card kinds are enough.
 */
PAI_LOAD.push(function () {
'use strict';

const { esc, fmt, row, rhoRow, series, peerRow, unplaced } = window.K;

window.PAI.register({
  id: 'measure', pack: 'core', stage: 'measure', order: 10,
  title: 'Whether it worked',
  needs: ['SNAP.rho'],
  render(ctx) {
    const { S, ISS, ORDER } = ctx;
    const hk = S.issues.headline;
    const r = S.rho;
    return `<div class="two-up">`
      + `<div>${rhoRow()}`
      + `<div class="reads" id="measure-rows" data-ref="rho">`
      + row({ id: 'measure-median', component: 'median', ref: 'rho',
        cols: 'minmax(0,210px) minmax(0,1fr) auto',
        left: `<span class="who"><b>Ask to answer</b><span class="m">median, ${r.window_days} days`
          + `</span></span>`,
        line: r.median_minutes == null ? 'Nothing has been answered yet in this window.'
          : `Half the asks that were answered were answered inside this.`,
        qty: [{ num: 'rho.median', value: r.median_minutes == null ? null
          : `${r.median_minutes} min`, cmp: `against ${r.acted} of ${r.alerts_act} asks answered` }],
      })
      + row({ id: 'measure-rho', component: 'rhoValue', ref: 'rho',
        cols: 'minmax(0,210px) minmax(0,1fr) auto',
        left: `<span class="who"><b>ρ</b><span class="m">answered ÷ asked</span></span>`,
        line: `The one number this node reports about itself to anybody.`,
        qty: [{ num: 'rho.value', value: r.rho == null ? null : fmt(r.rho, 2),
          cmp: `${r.acted} answered of ${r.alerts_act} asked in ${r.window_days} days` }],
      })
      + `</div></div>`
      + `<div>${series(hk, ISS[hk])}`
      + `${(S.issues.undeclared_slots || []).map(u => {
        const c = (ISS.water && ISS.water.contributions || []).find(x => x.slot === u.slot);
        return c ? unplaced(c) : '';
      }).join('')}</div></div>`;
  },
  notes(ctx) {
    const r = ctx.S.rho;
    return [
      { id: 'measure-rho', text: `ρ is the share of asks answered — ${r.acted} of ${r.alerts_act} `
        + `in ${r.window_days} days here — and it is the one number a node reports about itself. It `
        + 'is drawn as a row of rings, answered first, because a row a person can count is a '
        + 'measurement and a dial needle is a mood. Its definition is not this page’s to touch.' },
      { id: 'measure-day', text: 'The day is the headline issue’s own trace: the node supplies every '
        + 'value and the line, the page supplies only the box. A hole in the series is a hole in the '
        + 'line — a run of one reading is a dot, never nothing — and the text alternative beside the '
        + 'drawing says where the day opened and closed.' },
      { id: 'measure-loop', text: 'This is the stage that closes the loop. Observe put a number on '
        + 'the page; decide said how far that number may be trusted; act asked somebody to do '
        + 'something; measure is the reading coming back after they did, or did not, and how long it '
        + 'took. The next observation is the first section again.' },
      { id: 'measure-unplaced', text: 'A pack that asks for a slot this page has no place for lands '
        + 'here with the pack’s name on it, rather than being dropped — the water pack’s gauge is the '
        + 'example. That is how a community pack finds out the vocabulary has a gap without its '
        + 'reading disappearing.' },
    ];
  },
});

});

/* ================================================================= h/mods/trust.js ==== */
/* trust · trust · decide
 *
 * What this node doubts about its own sensors. Restored from the page this replaces, as a section
 * the trust pack registers: three rules exist (channel_dead, coverage_low, peer_disagreement) and
 * before that card nowhere on the node's own surfaces did a person see that a kit sat at 32% of the
 * week while reporting a fresh timestamp.
 *
 * WHY DECIDE, AND WHY THE NETWORK VIEW. Doubt is not an observation: a coverage figure is not a
 * reading of the air, it is a statement about how far a reading may be trusted, which is the decide
 * stage's whole question. And it is keeper's material rather than household material — somebody
 * fixes a kit, nobody opens a window because of it — so it sits with the radios and the hardware.
 *
 * `GET /trust` computes all of it. Nothing here counts anything: a sensor under seven days old is
 * young because the node says `age_hours < 168`, and the page prints that rather than deciding it.
 */
PAI_LOAD.push(function () {
'use strict';

const { esc, row } = window.K;

const T = () => window.TRUST || null;

window.PAI.register({
  id: 'trust', pack: 'trust', stage: 'decide', order: 30,
  title: 'What the node doubts about its own sensors',
  needs: ['TRUST'],

  render(ctx) {
    const rows = (T() || {}).rows || T() || [];
    const all = Array.isArray(rows) ? rows : [];
    if (!all.length) {
      return `<p class="note" data-component="trustCard" data-card="trust" id="trust-rows"`
        + ` data-ref="hardware-rows">No local sensor yet, so there is nothing to doubt.</p>`;
    }
    /* The node's own three conditions, read off the row rather than recomputed here. */
    const doubt = all.filter(r => r.age_hours < 168 || r.coverage_7d < 60 || r.frozen_channels > 0);
    const cols = 'minmax(0,210px) minmax(0,1fr) auto';
    const body = doubt.length
      ? doubt.map(r => {
        const young = r.age_hours < 168;
        return row({
          id: `trust-${esc(r.sensor_id)}`, component: 'trustRow', ref: 'trust-rows', cols,
          left: `<span class="who"><b>${esc(r.name || r.sensor_id)}</b>`
            + `<span class="m">${esc(r.sensor_id)}</span></span>`,
          line: young
            ? 'still gathering its first week, so its coverage is not a fault yet'
            : `${r.frozen_channels > 0 ? `${r.frozen_channels} frozen `
              + `${r.frozen_channels === 1 ? 'channel' : 'channels'}: the kit is alive and one of its `
              + `readings has not moved. ` : ''}Seven-day coverage is what the node has of it, not `
              + `what it sent.`,
          qty: [{ num: `trust.${esc(r.sensor_id)}.coverage`,
            value: young ? '—' : `${r.coverage_7d}%`,
            cmp: young ? 'under seven days old; the week is not up'
              : 'of the week, against 100% for a sensor that reported every hour' }],
        });
      }).join('')
      : `<p class="note">Every sensor reported all week.</p>`;
    const sub = doubt.length
      ? `${doubt.length} of ${all.length} sensors need a look.`
      : `${all.length} local sensors, seven-day coverage.`;
    return `<div class="reads" data-component="trustCard" data-card="trust" id="trust-rows"`
      + ` data-ref="hardware-rows"><p class="note">${esc(sub)}</p>${body}</div>`;
  },

  notes() {
    const all = ((T() || {}).rows || T() || []);
    return [
      { id: 'trust-what', text: 'Three things this node can tell about its own sensors without '
        + 'anybody looking: a channel that has stopped moving while the kit is still alive, a '
        + 'sensor that has reported for less than sixty per cent of the week, and two collocated '
        + 'kits that disagree. GET /trust computes all three; none of them is an alert, because a '
        + 'doubt is not something to interrupt a household about.' },
      { id: 'trust-young', text: 'A sensor under seven days old has no seven-day coverage and is '
        + 'said to be still gathering its first week, not shown at some low percentage. Reading 0% '
        + 'as a fault on a kit plugged in yesterday is the page inventing a problem.' },
      { id: 'trust-stage', text: `This is in decide rather than observe because a coverage figure is `
        + `not a reading of the place: it is a statement about how far a reading may be trusted, `
        + `which is the question the decide stage exists for. `
        + `${Array.isArray(all) && all.length ? `${all.length} sensors are in it.` : ''}` },
    ];
  },
});

});

/* ================================================================= h/mods/forecast.js ==== */
/* forecast · forecast · observe
 *
 * The day this place is about to have: the wind, the rain, and the next eight hours of temperature.
 * Restored from the page this replaces, as a section the forecast pack registers.
 *
 * WHY OBSERVE, AND WHY NOW. A forecast is not this node's own measurement, but it is an observation
 * of this place that the node fetched and keeps — the same class of thing as the satellite's pass or
 * the street's median, which are both in observe. And it is the most household-facing thing on the
 * page after the lead: somebody checks it before hanging the washing out, so it is on Now.
 *
 * THE NODE FETCHES THIS; IT DOES NOT PREDICT. Printed on the card, because a household reading a
 * number on their own node's screen will otherwise assume the node worked it out.
 */
PAI_LOAD.push(function () {
'use strict';

const { esc, fmt, row } = window.K;

const COMPASS16 = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
const compass16 = deg => deg == null ? '?' : COMPASS16[Math.round((deg % 360) / 22.5) % 16];
const hhmm = ts => {
  const d = new Date(ts);
  return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
};

/* Top level, not nested: a function defined inside another one still parses and tools/check_ui.py
 * cannot see it. Same reason the page this replaces kept drawRing and drawForecast at the top. */
function drawForecast(ctx) {
  const d = window.FORECAST || {};
  /* /forecast always names both archives. The line after `||` is for a node whose forecast pack has
     never run, where the section exists and the endpoint's own credit does not. */
  const cite = ((d.attribution) || []).join(' · ')
    || 'BMKG, api.bmkg.go.id. Open-Meteo, open-meteo.com, CC-BY 4.0, when it is on.';
  const hours = d.hours || [];
  const card = (body, note) => `<div class="reads" data-component="forecast" data-card="forecast"`
    + ` id="forecast-rows" data-ref="band-${esc(ctx.S.issues.headline)}">`
    + `<p class="note">${esc(note)}</p>${body}`
    + `<p class="cap">${esc(cite)}</p>`
    + `<p class="cap">The node fetches this; it does not predict.</p></div>`;
  if (!hours.length) {
    return card('', 'No forecast yet. Set FORECAST_BMKG_ADM4 to this point’s village code, or turn '
      + 'on Open-Meteo, and the next day of wind and rain appears here. planetai run forecast verify '
      + 'finds the code.');
  }
  const now = Date.now();
  const all = hours.filter(h => new Date(h.ts).getTime() >= now - 3.6e6);
  const primary = all.some(h => h.source === 'forecast-bmkg') ? 'forecast-bmkg' : 'forecast-om';
  const fut = all.filter(h => h.source === primary);
  const gaps = all.filter(h => h.source === 'forecast-gap' && h.fc_temp_gap != null);
  const wind = fut.filter(h => h.fc_wind_speed != null);
  const rain = fut.filter(h => h.fc_rain > 0.2);
  const far = (d.far_from_node || [])[0];
  const w0 = wind[0];
  const note = [
    w0 ? `The wind comes from the ${compass16(w0.fc_wind_direction)} at `
      + `${fmt(w0.fc_wind_speed, 0)} km/h.` : '',
    rain.length
      ? `Rain expected from ${hhmm(rain[0].ts)}, `
        + `${fmt(fut.reduce((a, h) => a + (h.fc_rain || 0), 0), 1)} mm over the day.`
      : 'No rain expected in the next day.',
    far ? `The forecast point is ${fmt(far.km, 1)} km from this node, which is another place.` : '',
    gaps.length ? `The two forecasts differ by up to `
      + `${fmt(Math.max(...gaps.map(h => h.fc_temp_gap)), 1)} °C over the day; neither is the truth.` : '',
  ].filter(Boolean).join(' ');
  const steps = fut.slice(0, 8).map(h => row({
    id: `fc-${esc(String(h.ts))}`, component: 'forecastHour', ref: 'forecast-rows',
    cols: 'minmax(0,110px) minmax(0,1fr) auto',
    left: `<span class="who"><b>${esc(hhmm(h.ts))}</b></span>`,
    line: `wind from ${compass16(h.fc_wind_direction)} ${fmt(h.fc_wind_speed, 0)} km/h · `
      + (h.fc_rain > 0.2 ? `${fmt(h.fc_rain, 1)} mm rain` : 'dry')
      + (h.fc_cloud == null ? '' : ` · ${fmt(h.fc_cloud, 0)}% cloud`),
    qty: [{ num: `forecast.${esc(String(h.ts))}.temp`, value: `${fmt(h.fc_temp, 0)} °C`,
      cmp: 'a forecast for this point, not a reading taken here' }],
  })).join('');
  return card(steps, note);
}

window.PAI.register({
  id: 'forecast', pack: 'forecast', stage: 'observe', order: 50,
  title: 'The day it is about to have',
  needs: ['FORECAST'],
  render: drawForecast,
  notes() {
    const d = window.FORECAST || {};
    return [
      { id: 'forecast-not-a-reading', text: 'Every number here is a forecast for a point, fetched '
        + 'from an archive and kept on this node. None of it was measured here and none of it is '
        + 'this node’s own: the node fetches it, it does not predict it, and the card says so '
        + 'under the credit rather than leaving a household to assume otherwise.' },
      { id: 'forecast-two-archives', text: 'BMKG is Indonesia’s own service and Open-Meteo is '
        + 'the fallback; both are named on the card because both are required to be. Where the two '
        + 'disagree the section says by how much and that neither is the truth, rather than picking '
        + 'one and drawing it as if there were no second answer.' },
      { id: 'forecast-point', text: `A forecast is for a point, and the nearest point an archive has `
        + `is not always this address. Where it is far enough to be another place the section says `
        + `how far${(d.far_from_node || []).length ? '' : '; on this node it does not, which means it '
        + 'is near enough'}.` },
    ];
  },
});

});

/* ================================================================= h/wall.js — the wall, and the dial turning by itself ==== */
/* The wall: a field of hexagons, and the dial turning by itself.
 *
 * A wall is read from three metres, in the dark, by somebody who did not open it. It has no mouse
 * and nobody scrolls it, so everything it says has to be on one screen. Tomas asked for a wall
 * "fully based in the hexagon system", so the wall IS the grid: the nineteen cells this node
 * published at the current resolution — its own and the two steps around it — drawn large enough
 * that a number sits inside each one, and every number is what is actually read in that cell. The
 * dial stands at one stop for eight seconds and then at the next, 2 to 12 and back, and the field
 * re-fills: at 4 every station this node hears is in one cell; at 6 they spread into five; from 7 to
 * 10 the picture does not change — which is finding 6, and this is the only surface on which a
 * household can watch it happen.
 *
 * WHY EIGHT SECONDS AND WHY NO TWEEN. The design log's rule on motion is that motion is bound to
 * the cadence of its own datum, and a motion with no datum behind it is deleted. The datum here is
 * the resolution, and a resolution is a step: there is no place between 7 and 8, so nothing here
 * morphs, slides or zooms between stops. The field is redrawn, the numbers are replaced, the stop is
 * filled. The clock is the dial itself; the thin bar under it is only that clock made visible.
 * Eight seconds is about how long it takes to read one stop out loud. Tomas asked for this
 * animation knowing the rule, and the rule is why it is a step and not a glide.
 *
 * WHAT A CELL SAYS. Nothing is averaged across stations — the reason to draw cells is that they are
 * not one number. A cell with one station shows that station's own 15-minute mean of the variable
 * the wall is set to (?var=, PM2.5 by default) and its name. A cell with several shows how many and
 * the range, low to high. This node's own cell shows its own stations' values, each one. An empty
 * cell is drawn and left empty, because "no station is reading there" is half of what a grid is for.
 * No map under the cells: at three metres a photograph behind a numeral is noise, and the hexagon
 * is the module the whole design system is built on.
 *
 * Under prefers-reduced-motion nothing turns. The wall stands at the stop it opened on and the
 * stops are still there to press. Pressing a stop, in either mode, turns the dial to it and holds it
 * for half a minute; pressing a cell names it and holds too. Arrow keys turn it.
 *
 * Modules may still contribute to the wall through the contract's wall(); their fragments sit in
 * one row under the field, the first five, with a count of the rest. At three metres ten small
 * columns are unreadable, and the field already carries the numbers that matter.
 */
PAI_LOAD.push(function () {
'use strict';

const H = window.H3;
const DWELL_MS = 8000;
const HOLD_MS = 30000;
const STILL = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const MAX_FRAGMENTS = 5;

/* One hexagon, pointy-top, centred in a 100-unit box, for the dial's stops. A stop is pressed, it is
 * never pointed at: the strip is a control, not a gauge. */
const HEX = [30, 90, 150, 210, 270, 330].map(a => {
  const r = a * Math.PI / 180;
  return `${(50 + 45 * Math.cos(r)).toFixed(1)},${(50 + 45 * Math.sin(r)).toFixed(1)}`;
}).join(' ');

/* PORTED: the wall's CSS is in dashboard.css, under a banner naming this file, and style() with it. */

/* ------------------------------------------------------------------ the parts that turn */
const at = (ctx, res) => ({ ...ctx, RES: res,
  grain: H.grain_table.find(g => g.res === res),
  HERE: { ...ctx.HERE, res, id: ctx.N.chain[res] } });

const VAR = ctx => (ctx.Q.get('var') && H.metrics[ctx.Q.get('var')] ? ctx.Q.get('var') : 'pm25');

/* The centre of a projected cell: the mean of its path's vertices. make-h3.mjs wrote the path;
 * this reads it back rather than asking for a second field it would then have to ship. */
function centroid(d) {
  const pts = d.replace(/[MZ]/g, '').split('L').map(p => p.split(',').map(Number));
  const x = pts.reduce((a, p) => a + p[0], 0) / pts.length;
  const y = pts.reduce((a, p) => a + p[1], 0) / pts.length;
  return [x, y];
}

/* ------------------------------------------------------------------ the field */
/* Nineteen cells, and in each the thing read there. State is weight, fill and dash; the hue is the
 * layer's one accent and it means "this node's own". */
function field(ctx, sel) {
  const { esc, fmt } = ctx.K, { address, km2, edge } = ctx.KH, N = ctx.N;
  /* Unsited, the plate is nineteen cells of open water and the stations are placed in them. The wall
     is the surface nobody is watching, so it says what it does not know rather than drawing the Gulf
     of Guinea at three metres and labelling it this house. */
  if (!ctx.KH.sited()) {
    return `<p class="note">This node has no coordinates, so there is no ground to draw cells on. `
      + `Setting NODE_LAT and NODE_LON — planetai setup, or the Set up view — gives this node a cell `
      + `and puts its ${H.sensors.length} stations in the cells around it.</p>`;
  }
  const res = ctx.RES, plate = H.nav.plates[res], v = VAR(ctx), M = H.metrics[v];
  const line = M.issue && ctx.ISS[M.issue] && ctx.ISS[M.issue].line ? ctx.ISS[M.issue].line : null;
  const cmpFor = () => line ? `against the line, ${fmt(line.value, M.dp)} ${ctx.ISS[M.issue].unit}`
    : `no comparison yet · no line is declared for ${M.label}`;
  const d = plate.draw;
  /* Type is sized to the cell it sits in. The plate is nineteen cells in a 600-unit box whatever
   * the resolution, so a cell is about 120 units across at every stop; a numeral a third of that
   * fits with its caption, and a numeral of fixed size ran across three cells — measured, once. */
  const cw = (() => {
    const c0 = d.cells.find(c => c.id === plate.centre) || d.cells[0];
    const xs = c0.d.replace(/[MZ]/g, '').split('L').map(p => +p.split(',')[0]);
    return Math.max(...xs) - Math.min(...xs);
  })();
  const F = { big: (cw * 0.30).toFixed(1), mid: (cw * 0.21).toFixed(1), sm: (cw * 0.085).toFixed(1),
    nm: (cw * 0.095).toFixed(1), unit: (cw * 0.085).toFixed(1) };
  const dy = { top: -(cw * 0.19), base: cw * 0.10, bot: cw * 0.25 };
  const T = (x, y, cls, txt, extra = '') => `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" text-anchor="middle"`
    + ` class="${cls}" style="font-size:${F[cls]}px"${extra}>${txt}</text>`;
  const kmRange = st => { const ks = st.map(s => s.km).filter(k => k != null);
    if (!ks.length) return 'distance unknown';
    const lo = Math.min(...ks), hi = Math.max(...ks);
    return lo === hi ? `${lo} km` : `${lo}–${hi} km`; };
  /* Cells drawn back to front: empty, then read, then this node's own on top, so its stroke wins. */
  const order = d.cells.slice().sort((a, b) => {
    const ra = a.id === plate.centre ? 2 : (H.nav.cells[a.id].sensors.length ? 1 : 0);
    const rb = b.id === plate.centre ? 2 : (H.nav.cells[b.id].sensors.length ? 1 : 0);
    return ra - rb;
  });
  let cells = '', labels = '', reading = 0;
  for (const c of order) {
    const info = H.nav.cells[c.id];
    const own = c.id === plate.centre, isSel = c.id === sel;
    const st = info.sensors.map(i => H.sensors[i]);
    const has = st.length > 0;
    cells += `<path class="cel" data-cell="${esc(c.id)}" d="${c.d}" fill="var(--cells)"`
      + ` fill-opacity="${own ? 0.14 : has ? 0.06 : 0}" stroke="var(${isSel ? '--ink' : own ? '--cells' : '--ink'})"`
      + ` stroke-opacity="${own || isSel ? 1 : has ? 0.6 : 0.22}"`
      + ` stroke-width="${isSel ? 4 : own ? 3 : has ? 1.6 : 1}"`
      + `${own || has || isSel ? '' : ' stroke-dasharray="4 4"'}><title>${esc(c.id)}</title></path>`;
    if (!has) continue;
    const [x, y] = centroid(c.d);
    const vals = st.map(s => s.read[v] ? s.read[v].value : null).filter(x => x != null);
    if (vals.length) reading++;   // cells with a reading OF THIS VARIABLE, which is what is drawn
    if (own) {
      /* this node's own cell: each of its own stations' values, in a row */
      const mine = st.filter(s => s.local), theirs = st.filter(s => !s.local);
      const mv = mine.map(s => s.read[v] ? fmt(s.read[v].value, M.dp) : '—');
      labels += T(x, y + dy.top, 'sm', `this house · ${mine.length}${theirs.length ? ` · ${theirs.length} not ours` : ''}`)
        + T(x, y + dy.base, mv.length > 2 ? 'mid' : 'big', esc(mv.join(' · ')),
          ` data-num="wall.own.${esc(v)}" data-cmp="${esc(cmpFor())}"`)
        + T(x, y + dy.bot, 'unit', `${esc(M.unit)} · ${esc(M.label)}`);
    } else if (st.length === 1) {
      const s1 = st[0], r = s1.read[v];
      labels += T(x, y + dy.top, 'nm', esc((s1.name || s1.sensor_id).slice(0, 18)))
        + T(x, y + dy.base, 'big', r ? esc(fmt(r.value, M.dp)) : '—',
          ` data-num="wall.${esc(c.id)}.${esc(v)}" data-cmp="${esc(r ? cmpFor() : `does not measure ${M.label}`)}"`)
        + T(x, y + dy.bot, 'unit', `${r ? esc(M.unit) : 'not measured'} · `
          + `${s1.km == null ? 'distance unknown' : `${s1.km} km`}`);
    } else {
      const lo = vals.length ? Math.min(...vals) : null, hi = vals.length ? Math.max(...vals) : null;
      labels += T(x, y + dy.top, 'sm', `${st.length} stations · ${kmRange(st)}`)
        + T(x, y + dy.base, vals.length && lo !== hi ? 'mid' : 'big',
          vals.length ? (lo === hi ? esc(fmt(lo, M.dp)) : `${esc(fmt(lo, M.dp))}–${esc(fmt(hi, M.dp))}`) : '—',
          ` data-num="wall.${esc(c.id)}.${esc(v)}" data-cmp="${esc(vals.length
            ? `${vals.length} of ${st.length} measure ${M.label}; low to high, never a mean; ${cmpFor()}`
            : `none measures ${M.label}`)}"`)
        + T(x, y + dy.bot, 'unit', `${esc(M.unit)} · low–high`);
    }
  }
  const pts = (d.points || []).map(p =>
    `<circle cx="${p.x}" cy="${p.y}" r="${p.local ? 4 : 2.6}" fill="${p.local ? 'var(--cells)' : 'var(--ground)'}"`
    + ` stroke="var(--ink)" stroke-width="${p.local ? 1.6 : 1.1}"><title>${esc(p.name || p.sensor_id)}</title></circle>`)
    .join('');
  const G = ctx.grain;
  const selInfo = sel && H.nav.cells[sel] ? H.nav.cells[sel] : null;
  /* `reading` and not grain_table's `occupied`: occupied counts cells with any station at all, and
     the label used to claim those cells were reading this variable where the drawing plainly says
     they do not measure it. Count the thing that is drawn. */
  return `<svg viewBox="0 0 ${d.box} ${d.box}" role="img" aria-label="resolution ${res}: the nineteen cells `
    + `this node published, ${reading} of them with a station reading ${M.label}">`
    + `<g class="cells">${cells}</g><g class="pts">${pts}</g><g class="labels">${labels}</g></svg>`
    + `<div class="cap"><span>${address(N.chain[res], res)}</span>`
    + `<span>one cell <b data-num="h3.res${res}.area" data-cmp="against ${esc(km2(H.ladder[res].own_area_m2))}, `
    + `this node's own cell at this resolution">${esc(km2(G.area_m2))}</b> · <b>${esc(edge(G.edge_m))}</b> to an edge</span>`
    + `<span>${selInfo ? `pressed: ${esc(sel)} · ${selInfo.sensors.length} ${selInfo.sensors.length === 1
      ? 'station' : 'stations'}`
      : `${esc(M.label)} · press a cell to name it`}</span></div>`;
}

/* Eleven stops. State is fill, weight and dash: the stop you are on is ink, the stops coarse enough
 * to leave this machine carry a light cells fill, the stops finer than this node says where it is
 * are dashed. */
function dial(ctx) {
  const { esc } = ctx.K, { km2, edge } = ctx.KH, N = ctx.N;
  const stops = H.grain_table.map((g, i) => {
    const on = g.res === ctx.RES;
    const above = H.grain_table[i - 1];
    const cmpEdge = above ? `against resolution ${above.res} above it, ${edge(above.edge_m)} to an edge`
      : 'the coarsest this node publishes; nothing above it here';
    return `<a class="stop${on ? ' on' : ''}${g.may_leave ? ' leaves' : ''}`
      + `${g.finer_than_published ? ' toofine' : ''}" href="${ctx.link(N.chain[g.res], { res: g.res })}"`
      + ` data-res="${g.res}"${on ? ' aria-current="true"' : ''}`
      + ` aria-label="resolution ${g.res}, one cell ${esc(km2(g.area_m2))}">`
      + `<svg viewBox="0 0 100 100" aria-hidden="true"><polygon points="${HEX}"`
      + ` fill="${on ? 'var(--ink)' : g.may_leave ? 'var(--cells)' : 'none'}"`
      + ` fill-opacity="${on ? 1 : g.may_leave ? 0.16 : 0}" stroke="var(--ink)"`
      + ` stroke-width="${on ? 3 : 1.6}"${g.finer_than_published && !on ? ' stroke-dasharray="7 5"' : ''}/>`
      + `<text x="50" y="52" text-anchor="middle" dominant-baseline="central"`
      + ` data-num="h3.res" data-cmp="against ${N.res_min} to ${N.res_max}, the resolutions this `
      + `node publishes">${g.res}</text></svg>`
      + `<span class="edge" data-num="h3.res${g.res}.edge" data-cmp="${esc(cmpEdge)}">`
      + `${esc(edge(g.edge_m))}</span>`
      + `</a>`;
  }).join('');
  return `<div class="stops" role="group" aria-label="resolution, ${N.res_min} to ${N.res_max}; `
    + `standing at ${ctx.RES}">${stops}</div>`
    + `<div class="clock" id="wall-clock" data-component="clock" data-ref="wall-dial"`
    + ` aria-hidden="true"><i></i></div>`;
}

/* What this grain says, as three numbers re-derived from the stop. */
function grain(ctx) {
  const { esc } = ctx.K, G = ctx.grain, n = H.sensors.length;
  const finest = H.grain_table[H.grain_table.length - 1];
  /* The same three counts as the Now view's grain line, and unknown for the same reason: "in this
     node's own cell" is a question about a cell this node does not have yet. */
  if (!ctx.KH.sited()) {
    return `<div class="col" data-ref="wall-dial"><h3 data-role="wall-issue">Cells with a station`
      + `</h3><div class="line"><span class="num" data-num="grain.occupied" data-cmp="no comparison `
      + `yet · this node has no coordinates, so no station has a cell">—</span>`
      + `<small>of 19 drawn</small></div></div>`
      + `<div class="col" data-ref="wall-dial"><h3 data-role="wall-issue">In this node’s cell</h3>`
      + `<div class="line"><span class="num" data-num="grain.in_my_cell" data-cmp="no comparison yet `
      + `· this node has no cell until it is sited">—</span><small>of ${n} stations</small></div></div>`;
  }
  const num = (key, v, cmp) => `<span class="num" data-num="${esc(key)}" data-cmp="${esc(cmp)}">`
    + `${esc(String(v))}</span>`;
  return `<div class="col" data-ref="wall-dial"><h3 data-role="wall-issue">Cells with a station</h3>`
    + `<div class="line">${num('grain.occupied', G.occupied, `against ${finest.occupied} at resolution `
      + `${finest.res}, the finest here`)}<small>of 19 drawn</small></div></div>`
    + `<div class="col" data-ref="wall-dial"><h3 data-role="wall-issue">In this node’s cell</h3>`
    + `<div class="line">${num('grain.in_my_cell', G.in_my_cell, `against ${n} stations in all`)}`
    + `<small>of ${n} stations</small></div></div>`
    + `<div class="col" data-ref="wall-dial"><h3 data-role="wall-issue">Of them, its own</h3>`
    + `<div class="line">${num('grain.mine_in_my_cell', G.mine_in_my_cell,
      `against the ${G.in_my_cell} in this node’s cell`)}<small>this house’s</small></div></div>`;
}

/* The modules' row: the first few fragments the contract's wall() hands over, and a count of the
 * rest, because at three metres ten small columns are unreadable and the field already carries the
 * numbers that matter. */
function more(ctx) {
  let frags = [];
  try {
    const html = window.PAI ? window.PAI.wall(ctx) || '' : '';
    frags = html.split(/(?=<div class="col")/).filter(x => x.trim());
  } catch { frags = []; }
  const shown = frags.slice(0, MAX_FRAGMENTS), rest = frags.length - shown.length;
  return shown.join('') + (rest > 0 ? `<div class="rest">+${rest} more in Now</div>` : '');
}

/* ------------------------------------------------------------------ the wall */
function render(ctx, sel) {
  const { K } = ctx, { esc } = K;
  const hk = ctx.S.issues.headline, d = ctx.ISS[hk];
  /* PORTED: body.wall hides the header, so the wall has no heading at all and axe's
     page-has-heading-one fires on it. The node's name is the page's heading on every other view and
     it is the wall's too — read out, not drawn, because the wall already says it in the foot. */
  return `<div class="wallbox" id="wall-lead" data-band="wall">`
    + `<h1 class="vh">${esc(ctx.S.health.node)} · the wall</h1>`
    + `<div class="wgrid">`
    + `<figure class="wfield" id="wall-field" data-component="wallField" data-ref="wall-dial">`
    + field(ctx, sel) + `</figure>`
    + `<div class="wside">`
    + `<div id="band-${esc(hk)}">${K.kicker(hk, d)}${K.sentence(hk, d, 'big')}${K.why(hk, d)}${K.ask(hk, d)}</div>`
    + `<div class="wdial" id="wall-dial" data-component="dial" data-ref="wall-field" role="group"`
    + ` aria-label="the dial">${dial(ctx)}</div>`
    + `<div class="wgrain" id="wall-grain" data-component="wallGrain" data-ref="wall-dial">${grain(ctx)}</div>`
    + `<div class="wrho">${K.rhoRow(false, 'wall-dial')}</div>`
    + `</div></div>`
    + `<div class="wmore" id="wall-more" data-component="wallMore" data-ref="wall-field">${more(ctx)}</div>`
    + `<div class="foot"><span>${esc(ctx.S.health.node)}</span>${K.asof()}${K.stamp()}<span class="st">stale</span>`
    + `<span>Answer on Telegram, not here.</span>`
    + `<span class="wcap">${STILL
      ? 'reduced motion is on, so the dial stands still · press a stop to turn it'
      : `the dial turns by itself every ${DWELL_MS / 1000} s · nothing interpolates between stops · `
        + 'under reduced motion it stands still'}</span></div>`
    + `</div>`;
}

/* The clock. One interval, one stop per tick, and every tick checks the wall is still on the page
 * before it touches anything: the shell may have rendered something else since. */
function start(ctx) {
  /* #wall-lead is written by this file, not by index.html, so it is looked up under the one id
     the document itself owns. tools/check_ui.py's first rule compares getElementById against the
     markup, and a rendered id can never be in it. */
  const box = () => document.querySelector('#page #wall-lead');
  if (!box()) return;
  const N = ctx.N;
  let res = ctx.RES, sel = null, timer = null, holdUntil = 0;

  function show(r) {
    const b = box();
    if (!b) { clearInterval(timer); return; }
    res = r;
    const c = at(ctx, r);
    const fl = b.querySelector('#wall-field'), dl = b.querySelector('#wall-dial'),
      gr = b.querySelector('#wall-grain'), mo = b.querySelector('#wall-more');
    if (fl) fl.innerHTML = field(c, sel);
    if (dl) dl.innerHTML = dial(c);
    if (gr) gr.innerHTML = grain(c);
    if (mo) mo.innerHTML = more(c);
    if (Date.now() < holdUntil) { const k = b.querySelector('#wall-clock'); if (k) k.classList.add('held'); }
  }
  const step = dir => { sel = null; show(res + dir > N.res_max ? N.res_min : res + dir < N.res_min ? N.res_max : res + dir); };

  if (!STILL) {
    timer = setInterval(() => {
      if (!box()) { clearInterval(timer); return; }
      if (Date.now() < holdUntil) return;
      step(1);
    }, DWELL_MS);
  }

  /* A press turns the dial here, without a reload, and holds it for a while. The href still says
   * where it went, so the address bar and a copied link say the same stop the wall shows. A press on
   * a cell names it in the caption and holds the clock the same way. */
  function hold() {
    holdUntil = Date.now() + HOLD_MS;
    const k = box() && box().querySelector('#wall-clock'); if (k) k.classList.add('held');
  }
  document.addEventListener('click', e => {
    if (!box()) return;
    const a = e.target.closest && e.target.closest('#wall-dial a.stop');
    if (a) {
      e.preventDefault();
      hold(); sel = null;
      show(+a.dataset.res);
      try { history.replaceState(null, '', a.getAttribute('href')); } catch { /* a file:// page */ }
      return;
    }
    const cel = e.target.closest && e.target.closest('#wall-field .cel');
    if (cel) { hold(); sel = cel.getAttribute('data-cell'); show(res); }
  });
  document.addEventListener('keydown', e => {
    if (!box()) return;
    if (e.key === 'ArrowRight') { hold(); step(1); }
    else if (e.key === 'ArrowLeft') { hold(); step(-1); }
  });
}

window.WALL = { render, start, field, dial, grain };

});

/* ================================================================= the shell — boot, the dial, the lead, and the four views ==== */
/* the shell: it runs at load, so it is not on PAI_LOAD. */
(function () {
'use strict';

const FIXTURE = new URLSearchParams(location.search).get('fixture');

/* ------------------------------------------------------------------ the one thing that fetches */
const tok_ = () => localStorage.getItem('planetai_admin') || localStorage.getItem('planetai_act') || '';
const auth_ = () => (tok_() ? { authorization: 'Bearer ' + tok_() } : {});

/* At SHARE_LEVEL=off a reader with no token gets the shell, /health and nothing else. That is a
 * real state a phone on the house WiFi will be in, not an error: the node answers 403 with its own
 * sentence, and the page draws the refused page. A blank would be the node lying about being
 * broken. Carried over from the page this replaces, which had it right. */
function Refused(said) { const e = new Error(said); e.refused = said; return e; }

/* A node whose database is wedged does not answer 500 — it holds the request open, which is the
 * common unattended failure and the one that left a wall screen on blank paper indefinitely. Twenty
 * seconds is longer than /issues has ever taken to compute on node #1 and short enough that a
 * household gets a sentence instead of a blank page; the abort surfaces as the honest failure line
 * the terminal catch draws, the same as any other refusal to answer. */
const TIMEOUT_MS = 20000;

async function api(path) {
  let r;
  try {
    r = await fetch(path, { headers: auth_(), signal: AbortSignal.timeout(TIMEOUT_MS) });
  } catch (e) {
    /* A hang and a dropped network arrive here the same way, and neither is an answer. Say which. */
    throw new Error(e && e.name === 'TimeoutError'
      ? `${path} did not answer within ${TIMEOUT_MS / 1000} seconds`
      : `${path} could not be reached: ${(e && e.message) || e}`);
  }
  if (r.status === 403) throw Refused((await r.json().catch(() => ({}))).error || 'refused');
  if (!r.ok) throw new Error(`${path} answered ${r.status}`);
  return r.json();
}

/* ------------------------------------------------------------------ the plan */
/* GET /place/geojson projected in this browser with the node's own formula — metres east and south
 * of the node, NODE_DASHBOARD_PLAN_SPEC.md rule 1, the same eight lines make-plan.mjs runs. Every
 * vertex is kept: geoPath's adaptive resampling was measured on this exact dataset dropping corners
 * from 855 of 2,713 buildings, which is why nothing here resamples or simplifies. */
async function plan(health) {
  const gj = await api('/place/geojson');
  const LAT = health.lat, LON = health.lon;
  const K = Math.cos(LAT * Math.PI / 180) * 111320;
  const r1 = v => Math.round(v * 10) / 10;
  const px = ([lon, lat]) => [r1((lon - LON) * K), r1(-(lat - LAT) * 111320)];
  const flat = ring => ring.flatMap(px);
  /* The first coordinate of a feature, whatever its geometry. A point of interest mapped as an open
     way made the page this replaces destructure a number, and the whole kilometre came back blank
     with nothing said. The marker goes at the feature's first point either way. */
  const firstPt = g => { let c = g && g.coordinates; while (Array.isArray(c) && Array.isArray(c[0])) c = c[0]; return c; };
  const out = { buildings: [], roads: [], green: [], sat: [], poi: [],
    counts: { buildings: 0, buildings_drawn: 0, roads: 0, green: 0, sat: 0, poi: 0, vertices: 0 } };
  let skipped = 0;
  for (const f of (gj.features || [])) {
   try {
    const kind = (f.properties || {}).kind, g = f.geometry || {};
    const rings = g.type === 'Polygon' ? g.coordinates
      : g.type === 'MultiPolygon' ? g.coordinates.flat() : null;
    if (kind === 'building') {
      out.counts.buildings++;
      /* Rule 5: some of a node's buildings are points, not footprints. Counted, never drawn — the
         caption says both numbers rather than quietly rounding one into the other. */
      if (!rings) continue;
      out.counts.buildings_drawn++;
      for (const r of rings) out.buildings.push(flat(r));
    } else if (kind === 'sat') {
      out.counts.sat++;
      if (!rings) continue;
      for (const r of rings) out.sat.push([(f.properties.confidence == null ? 0 : f.properties.confidence), ...flat(r)]);
    } else if (kind === 'green') {
      out.counts.green++;
      if (!rings) continue;
      for (const r of rings) out.green.push(flat(r));
    } else if (kind === 'road') {
      out.counts.roads++;
      if (g.type !== 'LineString') continue;
      out.roads.push([f.properties.highway || 'service', ...flat(g.coordinates)]);
    } else if (kind === 'poi') {
      out.counts.poi++;
      out.poi.push([...px(firstPt(g)), f.properties.category || 'other']);
    }
   } catch (e) { skipped++; }          // one undrawable feature must not blank the kilometre
  }
  if (!out.buildings.length && !out.roads.length && !out.sat.length) return null;
  const all = [...out.buildings, ...out.green, ...out.sat.map(s => s.slice(1)), ...out.roads.map(r => r.slice(1))];
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const r of all) {
    for (let i = 0; i < r.length; i += 2) {
      x0 = Math.min(x0, r[i]); x1 = Math.max(x1, r[i]);
      y0 = Math.min(y0, r[i + 1]); y1 = Math.max(y1, r[i + 1]);
    }
    out.counts.vertices += r.length / 2;
  }
  out.counts.vertices += out.poi.length;
  out.counts.skipped = skipped;
  out.bbox_m = [Math.round(x0), Math.round(y0), Math.round(x1), Math.round(y1)];
  out.span_m = [Math.round(x1 - x0), Math.round(y1 - y0)];
  return out;
}

/* ------------------------------------------------------------------ boot */
/* The page's one fetch sequence. /issues carries everything the sections read; /health names the
 * node and its clock; /settings says what the keeper allowed; /rho is the node's own measurement of
 * itself; /earth names the satellite years it has on disk; /place/geojson is the plan. A failure
 * leaves the global null and the section whose `needs` names it prints one honest line — never a
 * blank, never a retry loop.
 *
 * THE TWO PATHS RETURN DIFFERENT SHAPES, and this is the one place that knows it. GET /issues
 * returns the computed body directly — {order, headline, as_of, issues, stations, metrics, asks,
 * mesh, geometry, …}. GET /issues/fixtures/<name> returns the WHOLE committed snapshot with that
 * same body nested under `.issues`, and the snapshot's own `health`, `rho`, `stats` and `alerts`
 * beside it. Both are normalised here, before anything else reads either.
 */
/* GET /settings answers with app/settings.py's describe(): { unlocked, runtime: [{key, value, secret,
 * …}], bootstrap: [...] } — a list of rows, not a map of keys. Every predicate on this page asks for
 * a key by name, so the rows are flattened onto the same object here, in the one place that knows
 * the endpoint's shape. Without this `window.SETTINGS.MAP_TILES` was undefined on every load, the
 * tiles feature could never be turned on, and two sentences told the keeper the opposite of the
 * setting they had just saved.
 *
 * A value the node MASKED is not a value. describe() writes "•••• set" for every secret and, for a
 * reader without the admin token, for every key outside PUBLIC — so a masked row is left off rather
 * than compared against, and reads as unset. MAP_TILES is in PUBLIC and so arrives unmasked at every
 * share level; unset is also the safe way round for the one setting that decides whether this
 * household's kilometre is named to somebody else's machine.
 *
 * `runtime` and `bootstrap` stay on the object: the Set up pane and readLayout() read the rows. */
const MASKED = '•••• set';
function flatSettings(d) {
  const flat = {};
  for (const r of ((d || {}).runtime || [])) {
    if (r && r.key && !r.secret && r.value !== MASKED) flat[r.key] = r.value;
  }
  return { ...(d || {}), ...flat };
}

async function boot() {
  const answered = await api(FIXTURE ? `/issues/fixtures/${encodeURIComponent(FIXTURE)}` : '/issues');
  const snapshot = FIXTURE ? answered : null;
  const issues = FIXTURE ? answered.issues : answered;
  const [health, settings] = await Promise.all([
    api('/health'),
    api('/settings').catch(() => ({})),
  ]);
  /* A fixture carries the ρ of the hour it was captured; a live node keeps it at /rho, which is the
     same route the page this replaces read. Neither is computed here. */
  const rho = (snapshot && snapshot.rho) || await api('/rho').catch(() => null);
  const earth = await api('/earth').catch(() => null);
  /* What the node doubts about its own sensors, and the day this place is about to have. Two routes
     the node already serves and the page it replaces already read. A refusal or a pack that has
     never run leaves the global null, and the section whose `needs` names it prints one line. */
  const [trust, forecast] = await Promise.all([
    api('/trust').catch(() => null), api('/forecast').catch(() => null),
  ]);

  window.SNAP = { issues, health, base: { captured_utc: issues.as_of },
    rho, funnel: issues.funnel || null, peer: issues.peer || null, fixture: FIXTURE || null };
  const geo = issues.geometry || {};
  window.H3 = { ...geo, sensors: issues.stations || [], metrics: issues.metrics || {},
    asks: issues.asks || null,
    radio: { ...(geo.radio || {}), mesh: issues.mesh || null,
      mesh_sensor: issues.mesh && issues.mesh.device, mesh_reads: issues.mesh ? issues.mesh.reads : [] },
    node: { lat: health.lat, lon: health.lon, name: health.node } };
  window.SETTINGS = flatSettings(settings);
  readLayout(settings);
  window.EARTH = earth;
  window.TRUST = trust;
  window.FORECAST = forecast;
  window.PLAN = await plan(health).catch(() => null);
}

/* ------------------------------------------------------------------ Arrange */
/* Ported from the page this replaces. `UI_LAYOUT` is still what app/settings.py says it is —
 * "Managed by the dashboard's Arrange mode" — and Arrange is still a mode over Now rather than a
 * view of its own: leaving Now ends it, which is the behaviour it should always have had.
 *
 * What moved: the old page arranged five fixed band mounts, and this one arranges the sections a
 * pack registered, so an order is a list of section ids and a hide is an id taken out of the view's
 * own list before anything is drawn. */
let LAYOUT = { order: [], hidden: [] };
let ARRANGING = false;

function readLayout(settings) {
  /* A fixture is a file, not a node: there is nowhere a saved arrangement could have come from, and
     reading one is what would stop `?fixture=` being renderable from the fixture alone. */
  if (FIXTURE) return;
  try {
    const r = ((settings || {}).runtime || []).find(x => x.key === 'UI_LAYOUT');
    if (r && r.value) LAYOUT = { order: [], hidden: [], ...JSON.parse(r.value) };
  } catch { /* an unreadable arrangement is no arrangement */ }
}

/* A band hidden in Arrange must actually be gone, not left holding its last content. The page this
 * replaces cleared five fixed mounts by hand and got it wrong on all five — the ✕ silently did
 * nothing — so here the view's own list is filtered before anything is drawn and a hidden section is
 * never emitted at all. */
const want = view => view.filter(id => !(LAYOUT.hidden || []).includes(id));

/* An arrangement is a position within a stage, which is what the registry already sorts by.
 *
 * `s.order` lives on the section object a pack registered, which is shared and long-lived, so this
 * must RESTORE and not merely skip: a version that only overwrote the ids an arrangement names left
 * every other section holding whatever an earlier press had given it, and Default — which empties
 * the order — then changed nothing at all until a hard reload. The order each section registered
 * with is captured once, before anything can have moved it. */
const REGISTERED_ORDER = new Map();
function rememberOrder() {
  for (const s of window.PAI.sections) {
    if (!REGISTERED_ORDER.has(s.id)) REGISTERED_ORDER.set(s.id, s.order);
  }
}
function applyOrder() {
  const o = LAYOUT.order || [];
  for (const s of window.PAI.sections) {
    const i = o.indexOf(s.id);
    s.order = i >= 0 ? i
      : REGISTERED_ORDER.has(s.id) ? REGISTERED_ORDER.get(s.id) : s.order;
  }
}

/* ------------------------------------------------------------------ the projection */
/* GET /issues publishes a cell as an id and its boundary in degrees — geometry.plates' `cells_ll`
 * and, since this task, geometry.claims' too. The kits below were written against a build step that
 * had already projected them, and no browser here has h3 or a projection library. So the projection
 * happens once, here, in the node's own formula (rule 1 again), and nothing downstream knows what a
 * hexagon is. This derives no number the node reports: it re-expresses degrees the node sent. */
const project = (rows, lat0, lon0) => {
  const K = Math.cos(lat0 * Math.PI / 180) * 111320;
  const r1 = v => Math.round(v * 10) / 10;
  return (rows || []).map(r => {
    const o = [r[0]];
    for (let i = 1; i < r.length; i += 2) o.push(r1((r[i + 1] - lon0) * K), r1(-(r[i] - lat0) * 111320));
    return o;
  });
};

/* …and the same metres fitted into one square box, which is the `draw` shape kit-h3's grid() and
 * the wall's field() read: {box, cells: [{id, d}], points}. Uniform scale on both axes, because a
 * hexagon squashed on one of them is a different shape. */
function drawOf(cellsM, stations, box = 600) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const c of cellsM) {
    for (let i = 1; i < c.length; i += 2) {
      x0 = Math.min(x0, c[i]); x1 = Math.max(x1, c[i]);
      y0 = Math.min(y0, c[i + 1]); y1 = Math.max(y1, c[i + 1]);
    }
  }
  if (!isFinite(x0)) return { box, cells: [], points: [] };
  const w = x1 - x0, h = y1 - y0, m = Math.max(w, h, 1) * 0.04;
  const s = box / (Math.max(w, h) + 2 * m);
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const X = x => box / 2 + (x - cx) * s, Y = y => box / 2 + (y - cy) * s;
  const r1 = v => Math.round(v * 10) / 10;
  const cells = cellsM.map(c => {
    let d = 'M';
    for (let i = 1; i < c.length; i += 2) d += `${r1(X(c[i]))},${r1(Y(c[i + 1]))}` + (i + 2 < c.length ? 'L' : '');
    return { id: c[0], d: d + 'Z' };
  });
  const points = (stations || []).map(p => ({ ...p, x: r1(X(p.x)), y: r1(Y(p.y)) }))
    .filter(p => p.x >= 0 && p.x <= box && p.y >= 0 && p.y <= box);
  return { box, cells, points };
}

/* What the published geometry does not carry, derived here from what it does, once. */
function initGeometry() {
  const H = window.H3;
  const lat = H.node.lat, lon = H.node.lon;
  const K = Math.cos(lat * Math.PI / 180) * 111320;
  const xy = s => ({ ...s, x: (s.lon - lon) * K, y: -(s.lat - lat) * 111320 });
  const pts = (H.sensors || []).filter(s => s.lat != null && s.lon != null).map(xy);

  for (const res of Object.keys((H.nav || {}).plates || {})) {
    const p = H.nav.plates[res];
    p.cells_m = project(p.cells_ll, lat, lon);
    p.draw = drawOf(p.cells_m, pts);
  }
  for (const c of (H.claims || [])) {
    c.cells_m = project(c.cells_ll, lat, lon);
    c.draw = drawOf(c.cells_m, []);
  }

  /* A station's cell at each resolution. GET /issues publishes it the other way round — every cell
   * of the plate lists the stations in it — so this reads that back. A station further out than the
   * two steps the node published has no cell here at that grain, and the list says so in words
   * rather than filing it under a blank id: the plate ends, the grid does not. */
  for (const s of (H.sensors || [])) s.chain = {};
  for (const id of Object.keys((H.nav || {}).cells || {})) {
    const c = H.nav.cells[id];
    for (const i of (c.sensors || [])) if (H.sensors[i]) H.sensors[i].chain[c.res] = id;
  }
  /* The drawings called a station's origin `label`; the node publishes the same string as `source`. */
  for (const s of (H.sensors || [])) s.label = s.source;
}

/* ------------------------------------------------------------------ init */
function init() {
  initKit();
  initGeometry();
  for (const f of PAI_LOAD) f();
  rememberOrder();
}

/* ------------------------------------------------------------------ writing a setting */
/* The one write this page makes, and the same request the page it replaces made for UI_LAYOUT: PUT
 * /settings behind the admin token, with X-Agent so the audit trail knows who acted. Task 7's tiles
 * switch is this call with { MAP_TILES: 'on' | 'off' }. */
async function setSetting(key, value) {
  const tok = localStorage.getItem('planetai_admin');
  if (!tok) throw new Error('that setting needs the admin token; unlock it under Set up');
  const r = await fetch('/settings', {
    method: 'PUT',
    headers: { 'content-type': 'application/json', authorization: 'Bearer ' + tok, 'X-Agent': 'dashboard' },
    body: JSON.stringify({ [key]: value }),
  });
  if (!r.ok) throw new Error(`the node refused that setting (${r.status})`);
  window.SETTINGS = { ...(window.SETTINGS || {}), [key]: value };
  if (window.PAI_SETUP) window.PAI_SETUP.toast('Saved. Live within about twenty seconds.');
  return true;
}
window.PAI_SETTINGS = { set: setSetting };
/* The Set up pane, ported from the page this replaces, reads these two rather than keeping its own
 * copy of either: one fetcher's headers, one re-render. */
window.PAI_AUTH = auth_;
window.PAI_ROUTE = () => route();

/* ------------------------------------------------------------------ the shell */
/* The header, shared by the page and by the refused page, because a household with no token still
 * has to be able to reach the other views. The node's name is an <h1>: the page had none at all
 * before that was found by looking, and page-has-heading-one fired on every view in every state. */
const VIEWS = [['now', 'Now'], ['network', 'Network'], ['setup', 'Set up'], ['wall', 'Wall'],
  ['arrange', 'Arrange']];
function chrome(node, city, view) {
  const esc = window.K.esc;
  return `<header id="header"><div class="wrap">`
    + `<h1 class="brand"><b>${esc(node || 'PLANETAI')}</b><span>${esc(city || '')}</span></h1>`
    + `<nav class="views" aria-label="Views">` + VIEWS.map(([v, name]) =>
      `<button type="button" data-view="${v}" class="${v === view ? 'on' : ''}"`
      + `${v === view ? ' aria-current="page"' : ''}>${esc(name)}</button>`).join('')
    + `</nav></div></header>`;
}

/* SHARE_LEVEL=off and no token. /health still answers — it answers at every share level, which is
 * why the node's name and the nav are here at all — and every view draws the node's own sentence
 * about why. A blank would be the node lying about being broken, and a blank on the WALL is a black
 * shelf screen a household reads as a dead node. Both surfaces say it. */
function drawRefused() {
  const el = document.getElementById('page');
  const v = (location.hash || '').replace(/^#/, '')
    || new URLSearchParams(location.search).get('view') || 'now';
  const said = window.K.refusedPage();
  if (v === 'wall') {
    document.documentElement.setAttribute('data-theme', 'dark');
    document.body.className = 'wall wallview';
    el.innerHTML = `<div class="wallbox"><h1 class="vh">${window.K.esc(window.NODE_NAME || 'PLANETAI')}`
      + ` · refused</h1>${said}</div>`;
  } else {
    document.documentElement.removeAttribute('data-theme');
    document.body.className = '';
    el.innerHTML = chrome(window.NODE_NAME, window.NODE_CITY, v) + `<div class="wrap">${said}</div>`;
  }
}
function main() {
  const { S, ISS, ORDER, DIST, LAB, LOC, esc, fmt, pill, kicker, sentence, why, ask, asof,
    wireframe, refusedPage, VIEW, STATE } = window.K;
  const { H, km2, edge } = window.KH;
  const { N, where, link } = window.KN;
  const PAI = window.PAI;

  document.title = `PLANETAI · ${S.health.node || 'node'}`;

  /* The dial opens at resolution 8 — the grain GET /health already publishes, and the only stop on
     this dial that has ever left this machine. */
  const HERE = where(8);
  const RES = HERE.res;
  const Q = new URLSearchParams(location.search);

  /* Everything a module may read, in one object. A module that wants more asks for it here rather
     than reaching for a global, so the contract stays a list a reader can see. */
  const ctx = {
    RES, HERE, Q, VIEW, STATE,
    S, ISS, ORDER, DIST, LAB, LOC,
    H, N, P: window.PLAN,
    K: window.K, KH: window.KH, KN: window.KN, KMAP: window.KMAP,
    grain: H.grain_table.find(g => g.res === RES),
    /* Which register the page is in, for the one drawing that cannot be told by CSS: an <img> is a
       document of its own, so the ground asks for its palette in the URL. */
    register: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'paper',
    FLOOR: H.settings.PRESENCE_RES_FLOOR,
    PUB: H.publication,
    link,
    /* The same page with some query keys changed and the rest kept — a section's own controls
       (a base layer, a variable) must not lose the dial's position or the view. */
    qlink(extra) {
      const q = new URLSearchParams(location.search);
      for (const [k, v] of Object.entries(extra)) v == null ? q.delete(k) : q.set(k, v);
      return '?' + q.toString() + (location.hash || '');
    },
  };

  /* The views are buttons and the URL is the hash, the way the page this replaces routed: one
     document served from /, no router, no build step. A span is a drawing; a button is a control. */
  const head = () => chrome(S.health.node, S.health.city, VIEW)
    + `<div class="dialwrap"><div class="wrap">${dial()}</div></div>`;

  /* One control. Each stop says what one cell of it is worth on the ground, the two lines the
     product already draws are drawn across it, and pressing a stop re-derives the whole page. */
  function dial() {
    const stops = H.grain_table.map(g => {
      const on = g.res === RES;
      return `<a class="${on ? 'on ' : ''}${g.may_leave ? 'leaves ' : ''}`
        + `${g.finer_than_published ? 'toofine' : ''}" href="${link(N.chain[g.res], { res: g.res })}"`
        + ` data-move="${g.res < RES ? 'out' : g.res > RES ? 'in' : 'here'}"`
        + ` title="one cell is ${km2(g.area_m2)}">`
        + `<span class="r">${g.res}</span><span class="s">${esc(edge(g.edge_m))}</span></a>`;
    }).join('');
    /* The dial's link out is the sentence it re-derives. On Now that is the grain line; on the
       other views it is the view's own band, because the grain line is the lead's and the lead is
       Now's. A component pointing at an id that is not on the page is what T5 counts. */
    const ref = VIEW === 'now' ? 'grain-line' : VIEW === 'network' ? 'satellite' : `view-${VIEW}`;
    return `<div class="dial" id="dial" data-component="dial" data-ref="${esc(ref)}"`
      + ` role="group" aria-label="resolution, ${N.res_min} to ${N.res_max}; `
      + `standing at ${RES}">${stops}</div>`
      + `<div class="dialkey"><span><i class="leaves"></i>may leave this machine `
      + `(resolution ${ctx.FLOOR} and coarser)</span>`
      + `<span><i class="fine"></i>finer than this node says where it is (past ${ctx.PUB.res})</span>`
      + `<span>one cell here: <b>${esc(km2(ctx.grain.area_m2))}</b></span></div>`;
  }

  /* The lead is the shell's: the node's own headline, the ask, the grain line, the as-of — and the
     figure a module offers for it (the ground module offers the map). A household opens the page to
     be told something, and that sentence is not a module's to move. */
  function lead() {
    const hk = S.issues.headline, d = ISS[hk], G = ctx.grain;
    const flat = H.grain_table.filter(g => g.occupied === G.occupied && g.in_my_cell === G.in_my_cell);
    const fig = PAI.sections.filter(s => s.lead && (s.needs || []).every(PAI.has))
      .map(s => { try { return s.lead(ctx) || ''; } catch { return ''; } }).join('');
    return `<section class="lead" id="band-${esc(hk)}" data-band="lead">`
      + kicker(hk, d) + sentence(hk, d, 'big') + why(hk, d) + ask(hk, d)
      + (!window.KH.sited()
        ? `<p class="why grainline" id="grain-line" data-component="grainLine" data-ref="dial">`
          + `At resolution ${RES} one cell is ${esc(km2(G.area_m2))}. Which cell this node stands in `
          + `is not known: it has no NODE_LAT/NODE_LON, so none of its ${H.sensors.length} stations `
          + `has a cell yet and the counts that would go here would be counts about open water.</p>`
        : `<p class="why grainline" id="grain-line" data-component="grainLine" data-ref="dial">`
      + `At resolution ${RES} one cell is ${esc(km2(G.area_m2))} and this node's `
      + `${H.sensors.length} stations fall in `
      + `<span data-num="grain.occupied" data-cmp="against ${H.sensors.length} stations in `
      + `${H.grain_table[H.grain_table.length - 1].occupied} cells at resolution `
      + `${N.res_max}, the finest this node publishes">${G.occupied}</span> of them. `
      + `${G.in_my_cell} sit in this node's own cell, of which ${G.mine_in_my_cell} are its own.`
      + (flat.length > 1 ? ` Resolutions ${flat[0].res} to ${flat[flat.length - 1].res} answer this `
        + `question identically.` : '') + `</p>`)
      + `<div class="whenline">${asof()}${window.K.stamp()}`
      + (S.fixture ? pill('cached', 'a committed snapshot, replayed through this node’s own engine')
        : pill('live', 'measured by this node')) + `</div>`
      + fig + `</section>`;
  }

  /* Decision of 15 September: Now carries the ground, the stations, the claims, the grain, the asks
     and the measure; the satellite, the two radios and the hardware are the Network view. One
     registry serves both, and the notes band follows each view's own sections. */
  const NOW = ['ground', 'sensors', 'forecast', 'claims', 'grain', 'asks', 'measure'];
  const NETWORK = ['satellite', 'reticulum', 'meshtastic', 'hardware', 'trust'];
  applyOrder();

  const el = document.getElementById('page');
  document.body.classList.toggle('wallview', VIEW === 'wall');
  if (VIEW === 'wall') {
    document.documentElement.setAttribute('data-theme', 'dark');
    document.body.classList.add('wall');
    /* PAI.render() wraps every section so one that throws prints that it did and the rest of the
       page stands. The wall had no such guard, and it is the one surface nobody is watching: a throw
       before innerHTML was assigned showed a black shelf screen and said nothing. */
    let box;
    if (STATE === 'refused') box = `<div class="wallbox">${refusedPage()}</div>`;
    else {
      try { box = window.WALL ? window.WALL.render(ctx) : `<div class="wallbox">${PAI.wall(ctx)}</div>`; }
      catch (e) {
        box = `<div class="wallbox"><h1 class="vh">${esc(S.health.node || 'this node')} · the wall</h1>`
          + `<p class="note" data-component="failed" id="wall-failed" data-ref="header">The wall did `
          + `not render: ${esc(String((e && e.message) || e))}. A failure is not an answer, so this `
          + `screen says so rather than going black.</p></div>`;
      }
    }
    el.innerHTML = box;
    if (window.WALL && window.WALL.start && STATE !== 'refused'
        && el.querySelector('#wall-lead')) window.WALL.start(ctx);
  } else if (STATE === 'refused') {
    el.innerHTML = head() + `<div class="wrap">${refusedPage()}</div>`;
  } else if (VIEW === 'now' || VIEW === 'arrange') {
    ARRANGING = VIEW === 'arrange';
    el.innerHTML = head() + `<div class="wrap">${PAI.render(ctx, lead(), { only: want(NOW) })}</div>`
      + (ARRANGING ? arrbar() : '');
    if (ARRANGING) { arrangeControls(); fillRestore(); }
  } else if (VIEW === 'network') {
    el.innerHTML = head() + `<div class="wrap">${PAI.render(ctx, '', { only: want(NETWORK) })}</div>`;
  } else {
    /* Set up, in the modular page, gains one box the drawings did not have: the sections this node
       runs, by pack, with the two moves a keeper actually makes — turn one off, and propose one
       back. Drawn, not built, like the rest of the wireframe; but drawn from the real registry, so
       the list is what this node has and not a sketch of one. */
    const setup = VIEW === 'setup' && window.PAI_SETUP ? window.PAI_SETUP.markup() : '';
    const sections = VIEW === 'setup' ? sectionsBox() : '';
    el.innerHTML = head() + `<div class="wrap"><section class="band" id="view-${esc(VIEW)}">`
      + `<div class="k">` + esc(VIEW) + `</div>` + setup + sections + wireframe(VIEW) + `</section></div>`;
    /* The pane draws itself locked, then asks the node what this reader may see. */
    if (VIEW === 'setup' && window.PAI_SETUP) window.PAI_SETUP.load();
  }

  /* The bar. Sticky at the foot, because the mode's instructions, its Default and its Done all sat
     nine screens below the fold on the page this replaces and a keeper who pressed Arrange saw three
     unexplained buttons appear beside every band and no way to finish. */
  function arrbar() {
    return `<div class="arrbar" id="arrbar" role="region" aria-label="Arrange">`
      + `<span>Arrange: ← and → move a section within its stage, ✕ hides it.</span>`
      + `<label class="vh" for="arr-restore">Put a hidden section back</label>`
      + `<select id="arr-restore"><option value="">Restore a hidden section…</option></select>`
      + `<button type="button" class="btn ghost" id="btn-arr-reset">Default</button>`
      + `<button type="button" class="btn" id="btn-arr-done">Done</button></div>`;
  }

  /* The menu that puts a hidden section back. It was markup and nothing else on the page this
     replaces — `#arr-restore` appeared once and was never referenced — so the only way back from a
     hidden band was Default, which discards every other choice too. */
  function fillRestore() {
    const sel = document.querySelector('#page #arr-restore');
    if (!sel) return;
    const hidden = LAYOUT.hidden || [];
    const name = id => (PAI.sections.find(s => s.id === id) || {}).title || id;
    sel.innerHTML = `<option value="">Restore a hidden section…</option>`
      + hidden.map(id => `<option value="${esc(id)}">${esc(name(id))}</option>`).join('');
    sel.disabled = !hidden.length;
  }

  /* Three controls on every section, and a sentence after each press saying what happened. */
  function arrangeControls() {
    const bands = [...document.querySelectorAll('#page section.band[data-band]')]
      .filter(el => el.dataset.band.includes(':'));
    const ids = bands.map(el => el.dataset.band.split(':')[1]);
    const stageOf = id => (PAI.sections.find(s => s.id === id) || {}).stage;
    bands.forEach((el, i) => {
      if (el.querySelector(':scope > .arr')) return;
      const id = ids[i];
      const bar = document.createElement('div');
      bar.className = 'arr';
      bar.innerHTML = `<button type="button" data-move="-1" aria-label="Move up">←</button>`
        + `<button type="button" data-move="1" aria-label="Move down">→</button>`
        + `<button type="button" data-hide="1" aria-label="Hide">✕</button>`;
      bar.onclick = ev => {
        const b = ev.target.closest('button');
        if (!b) return;
        const title = (PAI.sections.find(s => s.id === id) || {}).title || id;
        if (b.dataset.hide) {
          LAYOUT.hidden = [...(LAYOUT.hidden || []), id];
          say(`${title} hidden. Put it back from the menu at the foot of the page.`);
        } else {
          const from = ids.indexOf(id), to = from + Number(b.dataset.move);
          /* Across a stage boundary is not a move: the loop's order is the page's argument, not a
             preference. Saying so beats a button that looks broken. */
          if (to < 0 || to >= ids.length || stageOf(ids[to]) !== stageOf(id)) {
            say(`${title} is already ${Number(b.dataset.move) < 0 ? 'first' : 'last'} in its stage.`);
            return;
          }
          const next = [...ids];
          next.splice(to, 0, next.splice(from, 1)[0]);
          LAYOUT.order = next;
          say(`${title} moved ${Number(b.dataset.move) < 0 ? 'up' : 'down'}.`);
        }
        route();
      };
      el.prepend(bar);
    });
  }

  function sectionsBox() {
    const byPack = {};
    for (const s of PAI.sections) (byPack[s.pack] = byPack[s.pack] || []).push(s);
    const packs = Object.entries(byPack).sort(([a], [b]) => (a === 'core') - (b === 'core') || a.localeCompare(b));
    return `<div class="wf" data-component="sectionsBox" id="wf-sections" data-ref="wf-note">`
      + `<div class="box"><div class="cap">Sections on this node, by pack · ${PAI.sections.length} `
      + `registered · drag to reorder within a stage, switch off to hide, propose to send</div>`
      + packs.map(([pack, list]) =>
        `<div class="cap">${esc(pack)}${pack === 'core' ? ' · the renderer’s own' : ''}</div>`
        + list.map(s => `<div style="display:grid;grid-template-columns:minmax(0,1fr) auto auto auto;`
          + `gap:8px;align-items:center;padding:4px 0" data-component="sectionRow" id="wfs-${esc(s.id)}"`
          + ` data-ref="wf-sections"><span class="said" style="font-size:12.5px">${esc(s.title)}`
          + ` <span class="mono" style="color:var(--mute);font-size:10.5px">· ${esc(s.stage)}`
          + `${(s.needs || []).length ? ` · needs ${esc(s.needs.join(', '))}` : ''}</span></span>`
          + `<div class="ctl" style="width:34px;height:26px" title="on"></div>`
          + `<div class="ctl" style="width:34px;height:26px" title="move"></div>`
          + `<div class="ctl" style="width:78px;height:26px" title="propose back"></div></div>`).join(''))
        .join('')
      + `<div class="cap">Propose back: the section’s file, its notes and this node’s renders, sent `
      + `as one bundle for another node to try. A pack a node does not have shows here as one line `
      + `saying what it needs — never as a blank.</div></div></div>`;
  }
}

/* ------------------------------------------------------------------ the views, in the URL */
/* The hash and not a path: this page is one document served from /, it has no router and no build
 * step, and a path would need the node to serve every view's URL back as the same file. A re-render
 * is cheap here — every section draws from globals already in memory and nothing is fetched again —
 * so a view change is a render, not a fetch. */
function route() {
  readView();
  document.documentElement.removeAttribute('data-theme');
  document.body.className = '';
  main();
  window.scrollTo(0, 0);
}

/* Saying something, wherever the pane that says things is. */
function say(msg, bad) {
  if (window.PAI_SETUP) window.PAI_SETUP.toast(msg, bad);
}

/* Reset writes the same empty UI_LAYOUT that Done writes, so it survives a reload instead of coming
 * back from the node on the next read. */
async function layoutSave(reset) {
  if (reset) LAYOUT = { order: [], hidden: [] };
  const body = (LAYOUT.order.length || LAYOUT.hidden.length) ? JSON.stringify(LAYOUT) : '';
  try {
    await setSetting('UI_LAYOUT', body);
    say(reset ? 'Back to the default order.' : 'Saved on the node.');
  } catch (e) {
    say(String((e && e.message) || e), true);
  }
  history.pushState({ view: 'now' }, '', location.pathname + location.search);
  route();
}

document.addEventListener('click', ev => {
  if (ev.target.id === 'btn-arr-reset') return layoutSave(true);
  if (ev.target.id === 'btn-arr-done') return layoutSave(false);
});
document.addEventListener('change', ev => {
  if (ev.target.id !== 'arr-restore' || !ev.target.value) return;
  const id = ev.target.value;
  LAYOUT.hidden = (LAYOUT.hidden || []).filter(x => x !== id);
  const s = window.PAI.sections.find(x => x.id === id);
  say(`${(s && s.title) || id} is back.`);
  route();
});

addEventListener('hashchange', route);
addEventListener('popstate', route);
document.addEventListener('click', ev => {
  if (ev.target.id === 'btn-back') {
    history.pushState({ view: 'now' }, '', location.pathname + location.search);
    return route();
  }
  const b = ev.target.closest && ev.target.closest('nav.views button, .wall .exit');
  if (!b || !b.dataset.view) return;
  ev.preventDefault();
  /* pushState and not `location.hash =`: assigning the hash makes the browser jump to whatever
     element carries that id, which is the bug the page this replaces fixed the same way. */
  const v = b.dataset.view;
  history.pushState({ view: v }, '', v === 'now' ? location.pathname + location.search : '#' + v);
  route();
});

/* ------------------------------------------------------------------ and go */
boot().then(() => { init(); route(); }).catch(async e => {
  if (e && e.refused) {
    const h = await api('/health').catch(() => ({}));
    window.NODE_NAME = h.node; window.NODE_CITY = h.city;
    addEventListener('hashchange', drawRefused);
    document.addEventListener('click', ev => {
      const b = ev.target.closest && ev.target.closest('nav.views button');
      if (!b || !b.dataset.view) return;
      ev.preventDefault();
      const v = b.dataset.view;
      history.pushState({ view: v }, '', v === 'now' ? location.pathname + location.search : '#' + v);
      drawRefused();
    });
    drawRefused();
    return;
  }
  /* Through chrome() and the wall branch, the same two shapes drawRefused() draws and for the same
     reason: a reader whose node did not answer has lost the whole page, and the nav is how they
     reach Set up to do something about it. A bare paragraph took that away exactly when it was
     needed. /health is asked separately because it answers at every share level and often answers
     when nothing else does; when it does not, the header carries the product's own name. */
  const said = `This node did not answer: ${String((e && e.message) || e).replace(/[<>&]/g, '')}. `
    + `A failure is not an answer, so nothing is cached; reload to try again.`;
  const h = await api('/health').catch(() => ({}));
  const el = document.getElementById('page');
  const v = (location.hash || '').replace(/^#/, '')
    || new URLSearchParams(location.search).get('view') || 'now';
  if (v === 'wall') {
    document.documentElement.setAttribute('data-theme', 'dark');
    document.body.className = 'wall wallview';
    el.innerHTML = `<div class="wallbox"><h1 class="vh">${window.K.esc(h.node || 'PLANETAI')}`
      + ` · no answer</h1><p class="note">${said}</p></div>`;
  } else {
    el.innerHTML = chrome(h.node, h.city, v) + `<div class="wrap"><p class="note">${said}</p></div>`;
  }
});

})();

/* ================================================================= the Set up pane — ported from app/static/dashboard.js at 685fe1a ==== */
/* the Set up pane: lifted from the page this replaces, at 685fe1a, with as few edits as the move
 * requires.
 *
 * WHY IT IS HERE. The modular shell's Set up view is the section registry and a wireframe; this is
 * the working surface the page before it carried. Without it a keeper cannot put a token into the
 * page, so nothing can be written — the tiles switch included. It is ported, not rewritten:
 * tests/test_settings.py, test_config.py, test_shipped.py and test_share.py read this code out of
 * the file, and they read the same names they always did.
 *
 * THE FOUR EDITS THE MOVE REQUIRED, and no others:
 *   1  the markup is rendered into #page by the Set up view rather than sitting in index.html, so
 *      every lookup is a querySelector under #page. tools/check_ui.py's first rule compares
 *      getElementById against index.html's own markup, and a rendered id can never be in it.
 *   2  the two words it took from the old renderer's language table (mkCtx().w) are a map of their
 *      own here, in the same three languages.
 *   3  refresh() became route(), which is this page's re-render.
 *   4  Arrange's own restore menu came out of the click and change handlers with the plan card's
 *      layer toggles: neither is on this page, and both belong to the view this pane is not.
 */
(function () {
'use strict';

const q = sel => document.querySelector('#page ' + sel);
const qa = sel => document.querySelectorAll('#page ' + sel);
const esc = s => window.K.esc(s);
const auth_ = () => window.PAI_AUTH();
const route = () => window.PAI_ROUTE();

/* The two words this pane took from the old renderer's language table. Three languages, as before;
 * the household's own comes off GET /health and window.K.LOC carries it. */
const WORDS = {
  en: { leavesMachine: 'leaves this machine',
    openOnAnotherScreen: 'Open this on another screen in the house:' },
  id: { leavesMachine: 'keluar dari mesin ini',
    openOnAnotherScreen: 'Buka ini di layar lain di rumah:' },
  es: { leavesMachine: 'sale de esta máquina',
    openOnAnotherScreen: 'Abre esto en otra pantalla de la casa:' },
};
const W = () => WORDS[(window.K || {}).LOC] || WORDS.en;

/* The skeleton, verbatim from the page this replaces (app/static/index.html at 685fe1a) minus its
 * own <section class="view"> and .wrap, which the shell draws. Every id the measuring rig and the
 * suites drive is the id it was: #gate, #tok, #acttok, #btn-unlock, #setup-body, #tabs, #pane. */
function markup() {
  return `<h2 class="t">How this node was told to behave.</h2>`
    + `<p class="sub">Everything here is live within about twenty seconds; nothing needs a restart. `
    + `A blank field hands the setting back to <code>.env</code>. A value set here overrides the `
    + `same key in it.</p>`
    + `<div class="gate card" id="gate">`
    + `<h3 class="t">Unlock</h3>`
    + `<p class="sub">Changing settings needs the admin token. <code>planetai ui</code> on the node `
    + `prints it, and the weaker one below it.</p>`
    + `<label class="sub" for="tok">Admin token</label>`
    + `<div class="reveal"><input type="password" id="tok" placeholder="admin token" autocomplete="off">`
    + `<button type="button" data-reveal="tok" aria-pressed="false">Show</button></div>`
    + `<p class="sub" id="acttok-help">Or the token for closing a loop only — it records that `
    + `someone acted, and reads the sensors, but cannot change a setting or read a secret.</p>`
    + `<label class="sub" for="acttok">Token for closing a loop</label>`
    + `<div class="reveal"><input type="password" id="acttok" placeholder="token for closing a loop"`
    + ` autocomplete="off" aria-describedby="acttok-help">`
    + `<button type="button" data-reveal="acttok" aria-pressed="false">Show</button></div>`
    + `<div class="row mt"><button class="btn" id="btn-unlock">Unlock</button>`
    + `<button class="btn ghost" id="btn-back">Back</button></div></div>`
    + `<div class="setup" id="setup-body" hidden>`
    + `<nav class="tabs" id="tabs"></nav>`
    + `<h3 class="t" id="ptitle"></h3>`
    + `<p class="sub" id="pblurb"></p>`
    + `<p class="sub addr" id="paddr" hidden></p>`
    + `<div id="pane"></div>`
    + `<div class="savebar"><button class="btn" id="btn-save">Save changes</button>`
    + `<span class="sub" id="savenote">Live within about twenty seconds.</span></div></div>`;
}

function toast(msg, bad) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.toggle('bad', !!bad);
  t.classList.add('on');
  setTimeout(() => t.classList.remove('on'), 4200);
}

const GROUPS = {
  issues: ['Issues', "What this place watches, in order. The first one is where the page starts; whichever has something to say takes the top of it. Your preset guessed from a map — change it. What matters here is decided by the people who live here."],
  sources: ['Sources', 'What the node reads: your sensors, your account, and the public references around you.'],
  alerts: ['Alerts', "Reports at the hours you choose, in this node's own time zone. Between them, only what you asked to be interrupted for."],
  packs: ['Packs', 'Which packs load. Code packs stay off until you allow them; read one before you do.'],
  integrations: ['Integrations', 'Home Assistant over MQTT, and the Reticulum bridge.'],
  keys: ['Keys', 'What packs need to reach outside services. Secrets are never shown again once saved.'],
  agent: ['Model', 'Which model answers on Telegram. The strongest one the node can reach is used.'],
  node: ['The tree', 'Who this node reports upward to, and who may report to it. Readings stay here; hourly means, Index cells and \u03c1 travel.'],
  bootstrap: ['Bootstrap', 'Read once at start. Edit .env on the node and run planetai restart.'],
};
let GROUP = null, DESC = null, PACKS = [];
// Whether this pane holds an edit nobody has saved. Changing tab used to re-render the pane from the
// last describe(), so a typed value vanished with no warning and no way back.
let DIRTY = false;

/* The groups this node has, in the order it declares them, with bootstrap last because it is the
 * one that is read at start and cannot be changed from here. */
function groupsOf(desc) {
  const seen = [];
  for (const r of (desc.runtime || [])) if (!seen.includes(r.group)) seen.push(r.group);
  if ((desc.bootstrap || []).length) seen.push('bootstrap');
  return seen;
}
const groupTitle = g => (GROUPS[g] || [g.charAt(0).toUpperCase() + g.slice(1)])[0];
const groupBlurb = g => (GROUPS[g] || [])[1]
  || 'This node declares this group and the dashboard has no words for it yet. planetai config shows the same keys.';

const BOOLS = /^(BAD_ENABLED|OPENMETEO_ENABLED|SENSOR_INDOOR|MESH_ALERTS|HA_DISCOVERY|EXPORT_ENABLED|IPFS_PUBLISH|QUIET_HOURS|BAD_INCLUDE_INDOOR|PACKS_ALLOW_CODE)$/;

function unlock() {
  const t = q('#tok').value.trim();
  if (t) localStorage.setItem('planetai_admin', t);
  const a = q('#acttok').value.trim();
  if (a) localStorage.setItem('planetai_act', a);
  loadSetup();
}
function lock() {
  localStorage.removeItem('planetai_admin');
  localStorage.removeItem('planetai_act');
  loadSetup();
}

async function loadSetup() {
  const tok = localStorage.getItem('planetai_admin') || '';
  try {
    DESC = await fetch('/settings', { headers: tok ? { authorization: 'Bearer ' + tok } : {} }).then(r => r.json());
    PACKS = await fetch('/packs', { headers: auth_() }).then(r => r.ok ? r.json() : []).catch(() => []);
  } catch (e) { toast('The node did not answer.', true); return; }
  // values stay masked without the token, so a wrong one shows here and not at save time
  if (tok && !DESC.unlocked) { toast('That token is not right.', true); lock(); return; }
  const unlocked = !!tok && DESC.unlocked;
  q('#gate').hidden = unlocked;
  q('#setup-body').hidden = !unlocked;
  if (!unlocked) return;

  const groups = groupsOf(DESC);
  // A tab that was open when the node's groups changed under it, or a first load: take the first.
  if (!groups.includes(GROUP)) GROUP = groups[0] || null;
  if (!GROUP) { q('#pane').innerHTML = `<p class="note">This node declares no settings.</p>`; return; }
  q('#tabs').innerHTML = groups
    .map(g => `<button type="button" class="${g === GROUP ? 'on' : ''}" data-group="${esc(g)}">${esc(groupTitle(g))}</button>`).join('')
    + `<span class="acts"><button type="button" class="btn ghost" data-lock="1">Lock</button></span>`;
  q('#ptitle').textContent = groupTitle(GROUP);
  q('#pblurb').textContent = groupBlurb(GROUP);
  // The address another screen in the house should open. `planetai ui` prints it in a terminal; the
  // interface the keeper is already looking at never did, so the path to a wall screen ran through
  // the CLI. location.host is the address THIS reader used, which is the one that works.
  const addr = q('#paddr');
  if (addr) {
    const show = GROUP === 'node';
    addr.hidden = !show;
    if (show) addr.textContent = `${W().openOnAnotherScreen} http://${location.host}/`;
  }

  const pane = q('#pane');
  if (GROUP === 'bootstrap') {
    pane.innerHTML = (DESC.bootstrap || []).map(b =>
      `<div class="field"><div><label for="set-${esc(b.key)}">${esc(b.label)}</label>`
      + `<div class="help">${esc(b.key)}</div></div>`
      + `<div><input id="set-${esc(b.key)}" type="text" readonly value="${esc(b.value || '')}"`
      + ` placeholder="not set"></div></div>`).join('');
    return;
  }
  if (GROUP === 'packs') {
    const enabled = ((DESC.runtime || []).find(r => r.key === 'PACKS_ENABLED') || {}).value || '';
    const only = enabled ? enabled.split(',').map(x => x.trim()) : null;
    pane.innerHTML = PACKS.map(p =>
      `<div class="pack"><button type="button" role="switch" class="switch ${!only || only.includes(p.id) ? 'on' : ''}"`
      + ` aria-checked="${!only || only.includes(p.id)}" aria-labelledby="pack-${esc(p.id)}"`
      + ` data-pack="${esc(p.id)}"><span class="tr"></span></button>`
      + `<div><b id="pack-${esc(p.id)}">${esc(p.name || p.id)}</b> <span class="tag">${esc(p.kind)}</span>`
      + (p.domain ? ` <span class="tag">${esc(p.domain)}</span>` : '')
      + `<div class="help">${esc(p.description || '')}</div></div></div>`).join('');
    return;
  }
  /* One field. Every control here carries a name a screen reader can read and a label a pointer can
   * hit, which none of them did: axe found `label` critical eight times in the alerts group alone,
   * `button-name` critical on every toggle and `select-name` on the one select. A household keeper
   * setting up a node by voice or by keyboard heard "button" and could not tell on from off.
   *
   * A key that declares CHOICES gets them. app/settings.py has always refused a value outside them —
   * that is where `'5' is not a value REPORT_EVERY accepts` comes from — so the page was letting
   * somebody type a value the node had already decided to reject. The node knows; the node says;
   * the page draws the answer.
   */
  const rows = (DESC.runtime || []).filter(r => r.group === GROUP);
  pane.innerHTML = rows.map(r => {
    const id = 'set-' + r.key, lbl = 'lbl-' + r.key;
    const src = `<span class="src">${r.source === 'gui' ? 'set here · overrides .env' : r.source === 'env' ? 'from .env' : 'default'}</span>`;
    // The node says which settings change what leaves this machine (settings.OUTWARD). They were in
    // the same box as "Coast: max distance to sea, km": the one that decides whether the whole read
    // API answers a stranger on the WiFi looked exactly like the one that says how far the sea is.
    const out = r.outward ? `<span class="tag out">${esc(W().leavesMachine)}</span>` : '';
    const left = `<div><label id="${lbl}" for="${id}">${esc(r.label)}${out}${src}</label>`
      + `<div class="help" id="help-${r.key}">${esc(r.help)}</div></div>`;
    // Where the node's refusal is written when it refuses. Empty until then, and aria-live so a
    // reader who is not looking at this field still hears why the save did not take.
    const err = `<p class="err" id="err-${r.key}" role="alert" hidden></p>`;
    if (BOOLS.test(r.key)) {
      const on = r.value === '1';
      return `<div class="field">${left}<div><button type="button" role="switch" aria-checked="${on}"`
        + ` aria-labelledby="${lbl}" aria-describedby="help-${r.key}" id="${id}" class="switch ${on ? 'on' : ''}"`
        + ` data-key="${esc(r.key)}" data-bool="1"><span class="tr"></span></button>${err}</div></div>`;
    }
    const opts = r.key === 'ALERT_LOCALE'
      ? [['en', 'English'], ['id', 'Bahasa Indonesia'], ['es', 'Español']]
      : (r.choices || []).map(v => [v, v]);
    if (opts.length) {
      // A key at its own default has chosen nothing, and saying "6" here would be the page inventing
      // a fact it does not have: the defaults live at the call sites, not in RUNTIME. So it offers
      // the values and says plainly that none of them is set.
      const unset = !r.set;
      return `<div class="field">${left}<div><select id="${id}" aria-describedby="help-${r.key}" data-key="${esc(r.key)}">`
        + (unset ? `<option value=""${' selected'}>— not set; the node's own default applies —</option>` : '')
        + opts.map(([v, l]) => `<option value="${esc(v)}"${r.value === v ? ' selected' : ''}>${esc(l)}</option>`).join('')
        + `</select>${err}</div></div>`;
    }
    return `<div class="field">${left}<div><input id="${id}" aria-describedby="help-${r.key}" data-key="${esc(r.key)}"`
      + (r.secret
        ? ` type="password" placeholder="${r.set ? 'Set — type to replace' : 'Not set'}"`
        : ` type="text" value="${esc(r.value)}" placeholder="${r.source === 'default' ? "not set; the node's own default applies" : ''}"`)
      + ` autocomplete="off">${err}</div></div>`;
  }).join('') || `<div class="empty">Nothing to set in this group.</div>`;
  DIRTY = false;
}

async function saveSettings() {
  const tok = localStorage.getItem('planetai_admin');
  const body = {};
  if (GROUP === 'packs') {
    const all = [...qa('[data-pack]')];
    const on = all.filter(c => c.classList.contains('on')).map(c => c.dataset.pack);
    body.PACKS_ENABLED = on.length === all.length ? '' : on.join(',');
  } else {
    qa('[data-key]').forEach(el => {
      const k = el.dataset.key;
      if (el.dataset.bool) body[k] = el.classList.contains('on') ? '1' : '0';
      else if (el.type === 'password') { if (el.value) body[k] = el.value; }
      else body[k] = el.value;
    });
  }
  const r = await fetch('/settings', {
    method: 'PUT',
    headers: { 'content-type': 'application/json', authorization: 'Bearer ' + tok, 'X-Agent': 'dashboard' },
    body: JSON.stringify(body),
  });
  if (r.status === 401) { toast('That token is not right.', true); lock(); return; }
  if (r.status === 403) { toast('The node has no admin token yet. Run planetai ui.', true); return; }
  /* The node writes a sentence and the page used to throw it away. A keeper who typed 5 into "Report
   * every" got `Could not save (400).` — a status code, no field named, nothing marked, and the bad
   * value still sitting there — while the node had answered "'5' is not a value REPORT_EVERY accepts.
   * Hours between reports: 3, 4, 6, 8, 12 or 24. Default 6, which is four a day." app/settings.py
   * writes that refusal by quoting the key's own help text rather than keeping a second copy of it,
   * so it is the best sentence anybody has; it belongs beside the field it is about. */
  qa('#pane .err').forEach(e => { e.textContent = ''; e.hidden = true; });
  if (!r.ok) {
    const detail = await r.json().then(j => j && j.detail).catch(() => null);
    const said = typeof detail === 'string' ? detail : '';
    const which = Object.keys(body).find(k => said.includes(k));
    const box = which && q('#err-' + which);
    if (box) {
      box.textContent = said;
      box.hidden = false;
      const field = q('#set-' + which);
      if (field) field.focus();
      toast('Nothing was saved. The node said why, next to the setting.', true);
    } else {
      toast(said || ('Could not save (' + r.status + ').'), true);
    }
    return;
  }
  toast('Saved. Live within about twenty seconds.');
  DIRTY = false;
  loadSetup(); route();
}

document.addEventListener('input', ev => { if (ev.target.closest('#pane')) DIRTY = true; });

// the Set up pane's own clicks: unlock, save, reveal, tabs, switches, lock
//
// RESTORED. The first three of these lived in the shell's global click listener on the page this
// replaces, and carrying the pane across without them left every entry point into the token path
// drawn and dead: unlock() and saveSettings() were defined and unreachable, the gate never opened,
// and PAI_SETTINGS.set() could only ever throw for want of a token nothing could store.
document.addEventListener('click', ev => {
  if (ev.target.id === 'btn-unlock') return unlock();
  if (ev.target.id === 'btn-save') return saveSettings();
  /* A token is long, typed once, and often on a phone. Without this there is no way to check what
   * you typed before submitting it, and a wrong one only says so after a round trip. */
  const rev = ev.target.closest('[data-reveal]');
  if (rev) {
    const f = q('#' + rev.dataset.reveal);
    if (!f) return;
    const shown = f.type === 'text';
    f.type = shown ? 'password' : 'text';
    rev.setAttribute('aria-pressed', String(!shown));
    rev.textContent = shown ? 'Show' : 'Hide';
    return;
  }
  const g = ev.target.closest('[data-group]');
  if (g) {
    // An unsaved edit is the keeper's work. It used to go without a word.
    if (DIRTY && !confirm('This group has a change you have not saved. Leave it and lose the change?')) return;
    GROUP = g.dataset.group; return loadSetup();
  }
  if (ev.target.closest('[data-lock]')) return lock();
  const sw = ev.target.closest('.switch');
  if (sw) {
    sw.classList.toggle('on');
    sw.setAttribute('aria-checked', String(sw.classList.contains('on')));   // the state, not just the paint
    DIRTY = true;
  }
});

window.PAI_SETUP = { markup, load: loadSetup, toast };

})();
