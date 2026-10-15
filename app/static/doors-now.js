'use strict';
/* NOW — the household's first screen, read in the order a person asks (Tomas, 15 Oct; the plan heads the markup in
   doors.html): right now, as one block (the sentence and its day); what to do; did it work, and yesterday; around the
   house. Married to the node's rules: every part is one of the four card kinds (data-kind), names its learn mark, the
   routes it reads and its stage; every figure carries its comparison; the node's words are never shouted; provenance
   is a pill in ink. The scales are Place's: the kicker links there and draws no rail. */
VIEWS.now = function () {
  rows(); drawNow();
  aroundMap($('#rose')); thingsLine($('#nthings')); rememberLoad().then(() => decision());   /* the usual hour joins "Nothing to do now" */
};
/* YESTERDAY and DID IT WORK: the short part of the diary (Tomas, 14 Oct: the diary split between Now and Node, whose
   "What it remembers" keeps the record). Under the decision and quiet: yesterday's day entry said plainly from its own
   numbers; then, for the issue on screen, the last time the node asked, what was done, what happened after and the
   node's verdict. Framed only while something is asked. The admin token only: the house's learnings never reach a
   screen without it (doorsFetch does not even ask), nor the Wall. Read once a visit; switching issue redraws. */
let NOWL = null;
const LEARN_PACK = { air: 'air-quality', heat: 'heat' };
const VERDICT = { helps: 'It helps here.', no_clear_difference: 'No clear difference here yet.', worse: 'So far it seems to make it worse here.', too_early: 'Too early to say.' };
async function rememberLoad() {
  const get = u => doorsFetch(u).then(r => r.ok ? r.json() : null).catch(() => null);
  const [l, d, h] = await Promise.all([get('/learned'), get('/learned/search?scale=day&limit=1'), get('/household')]);
  NOWL = l ? { rows: l.learnings || [], day: ((d || {}).results || [])[0] || null, people: h ? h.people || {} : null } : null;
  nowRemember();
}
/* the hour this issue is usually worst, from the node's own `usual` learnings (28 days); said beside "Nothing to do now" */
function usualLine(k) {
  const u = NOWL ? NOWL.rows.filter(r => r.kind === 'usual' && r.issue === k && r.status === 'holding' && r.numbers) : [];
  return u.length ? `It is usually worst ${u.map(r => `around <span class="mono">${String(r.numbers.high_hour).padStart(2, '0')}:00</span> ${r.key.startsWith('outdoor') ? 'outside' : 'inside'} (${num(`${r.key}.usual.high`, fmt(r.numbers.high, 1), 'the median of that hour, 28 days')} ${said(r.numbers.unit)})`).join(' and ')}.` : '';
}
const firstSentence = s => String(s || '').split(/(?<=\.)\s/)[0];
/* yesterday's entry, condensed: for heat the feels-like inside, else the air inside against the line (its hours over
   the line are /issues/days' own count, at the house) and outside beside it; else the entry's own first sentences */
function yesterdayWords(e, k) {
  const n = e.numbers || {}, i = n['indoor-pm25'], o = n['outdoor-pm25'], h = n['indoor-heat'], A = D.issues.air || {};
  const today = dayOf(D.buckets[D.now]), y = new Date(Date.parse(today + 'T12:00:00Z') - 864e5).toISOString().slice(0, 10);
  const day = String(e.period_start).slice(0, 10), head = day === y ? 'Yesterday' : `On ${dLabel(day)}`;
  const lineName = /^WHO\b/.test(A.line_source || '') ? 'the WHO line' : 'the line', cmp = A.line != null ? `${lineName}, ${A.line} µg/m³` : 'no line';
  const pd = A.hero_distance === 'room' ? (A.per_day || []).find(p => p.date === day) : null;
  let s;
  if (k === 'heat' && h) s = `${head} it felt like ${num('yesterday.heat.mean', fmt(h.mean, 1), 'the day’s mean, inside')} °C inside on average, ${num('yesterday.heat.max', fmt(h.max, 1), 'the day’s hottest hour, inside')} at its hottest (${hhmm(h.max_at)}).`;
  else if (i || o) {
    s = head + (i ? ` the air inside averaged ${num('yesterday.inside.mean', fmt(i.mean, 1), cmp)} µg/m³, ${num('yesterday.inside.max', fmt(i.max, 1), cmp)} at its worst (${hhmm(i.max_at)})`
      + (pd ? (pd.over ? `, over ${lineName} for ${num('yesterday.inside.over', pd.over, `of ${pd.read} hours read`)} hour${pd.over === 1 ? '' : 's'}` : `, never over ${lineName}`) : '') : '')
      + (o ? `${i ? '; outside' : ' the air outside'} averaged ${num('yesterday.outside.mean', fmt(o.mean, 1), cmp)}${i ? (o.mean > i.mean ? ', worse' : o.mean < i.mean ? ', cleaner' : ', the same') : ' µg/m³'}` : '') + '.';
  } else s = esc(String(e.text || '').split(/(?<=\.)\s/).slice(1, 3).join(' ')) || 'No readings from this house’s own sensors.';
  const al = Object.values(n.alerts || {}), raised = al.reduce((a, x) => a + x.raised, 0), acted = al.reduce((a, x) => a + x.acted, 0);
  return s + (raised ? ` ${num('yesterday.alerts', raised, 'alerts sent that day')} alert${raised === 1 ? '' : 's'}, ${num('yesterday.acted', acted, `of ${raised} alerts`)} acted on.` : '');
}
function nowRemember() {
  const el = $('#nremember'), k = S.issue, it = D.issues[k] || {};
  el.hidden = !NOWL;
  if (!NOWL) return;
  const day = NOWL.day, pack = LEARN_PACK[k], wd = iso => `${dLabel(dayOf(iso))} at ${hhmm(iso)}`;
  const yest = day ? `<h3>Yesterday</h3><p>${yesterdayWords(day, k)} <a href="#node/remember/day/${esc(String(day.period_start).slice(0, 10))}">the whole entry ›</a></p>` : '';
  let h = '';
  /* an issue that never asks (no line) has nothing that could have worked */
  if (pack) {
    const rank = { holding: 0, weakening: 0, too_early: 1 };
    const w = NOWL.rows.filter(r => r.kind === 'worked' && r.issue === pack && r.status in rank).sort((a, b) => rank[a.status] - rank[b.status] || b.n - a.n)[0];
    const N = (w && w.numbers) || {}, C = N.cases || {}, U = N.unit || it.unit, [lo, hi] = N.after_hours || [];
    const c = [...(C.acted || []).map(x => ({ ...x, acted: true })), ...(C.unanswered || [])].sort((a, b) => Date.parse(b.at) - Date.parse(a.at))[0];
    const ev = D.events.filter(e => e.issue === k).sort((a, b) => Date.parse(b.opened_at) - Date.parse(a.opened_at))[0];
    /* asked now is the node's one answer (`asking`), said once, in What to do above; an event answered but not yet
       cleared asks nothing (it said "is asking now" beside a Decide card that said Done, 15 Oct) */
    const asked = ev && !ev.cleared_at ? ((it.asking || []).length ? `The node is asking now, since ${wd(ev.opened_at)}: see What to do, above.` : `The node last asked ${wd(ev.opened_at)}: see What to do, above.`) : ev ? `The node last asked ${wd(ev.opened_at)}${ev.action ? `: ${said(ev.action)}` : '.'} <span class="x">${esc(answerWords(ev.answer).w)}.</span>`
      : `The node has not asked about ${said(it.name.toLowerCase())} in the last seven days.`;
    const after = c ? `<p>${c.acted ? `Done ${wd(c.at)}${c.note ? `: “${esc(c.note)}”` : ''}` : `Not answered, ${wd(c.at)}`}. Inside went from `
      + `${num(`${k}.case.before`, fmt(c.before, 1), 'the hour before')} to ${num(`${k}.case.after`, fmt(c.after, 1), `the ${lo}–${hi} h after`)} ${said(U)} in the ${lo}–${hi} h after`
      + `${c.street == null ? '' : `; the street ${num(`${k}.case.street`, (c.street > 0 ? '+' : '') + fmt(c.street, 1), 'the street’s change over the same hours')}`}.</p>` : '';
    const verdict = w ? `<p><b>${VERDICT[N.verdict] || (w.status === 'too_early' ? VERDICT.too_early : '')}</b> ${said(firstSentence(w.statement))}${w.status === 'weakening' ? ' <span class="x">· weakening</span>' : ''}</p>`
      : `<p class="x">Nothing learned yet: the node checks once a day, and needs an alert somebody acted on.</p>`;
    const who = w && (w.for_whom || []).length ? `matters here: ${said(w.for_whom.join(', '))}`
      : NOWL.people && !Object.values(NOWL.people).some(Boolean) ? '<a href="#node/remember/who">who lives here? ›</a>' : '';
    h += `<h3>Did it work</h3><p>${asked}</p>${after}${verdict}`
      + `<p class="dm">${who ? `${who} · ` : ''}<a href="#node/remember">every case, on Node ›</a></p>`;
  }
  h += yest;
  el.innerHTML = h;
  el.hidden = !h;
}
// The things this home keeps, in one line (SPEC_inventory step 2), for a screen holding the admin token; nothing otherwise.
async function thingsLine(el) {
  const r = await doorsFetch('/things').catch(() => null);
  const s = r && r.ok ? ((await r.json().catch(() => null)) || {}).summary : null;
  el.hidden = !(s && s.things);
  if (!el.hidden) el.innerHTML = `<a href="#data/d-things">${s.things} things, ${s.idle} idle, ${s.repair} need${s.repair === 1 ? 's' : ''} repair ›</a>`;
}
function drawNow() {
  /* a phone draws the day alone and the week as one row a day it can press (weekRows): 13 px cells are no target */
  const phone = innerWidth <= 480;
  dayWeek({ el: $('#svg'), issue: S.issue, head: $('#fighead'), scale: $('#figline'), week: !phone, pick: j => { S.i = j; drawNow(); } });
  $('#week').hidden = !phone; if (phone) weekRows($('#week'));
  readout(); nowRemember();
}

/* The week on a phone: one button a day, its 24 hours a strip (over the line red, a missing hour left empty) and
   its hours over the line, the count /issues/days gives. Pressing a day moves the moment to that day, same hour. */
function weekRows(el) {
  const k = S.issue, it = D.issues[k], sd = (it.series || {})[it.hero_distance] || [], h0 = hourOf(D.buckets[S.i]), cur = dayOf(D.buckets[S.i]);
  const lo = d3.min(sd) ?? 0, top = Math.max(it.line ?? 0, d3.max(sd) ?? 0), span = top - lo || 1;   /* shaded from the week's own low, as the drawing's strip */
  el.innerHTML = D.dates.map(dt => {
    const pd = (it.per_day || []).find(p => p.date === dt), cells = d3.range(24).map(h => { const j = D.at[dt + '|' + h], v = j == null ? null : sd[j];
      return v == null ? '' : `<rect x="${h * 10 + .5}" y="0" width="9" height="14" fill="${it.line != null && v > it.line ? 'var(--signal-worse)' : 'currentColor'}" opacity="${it.line != null && v > it.line ? 1 : (.1 + .75 * (v - lo) / span).toFixed(2)}"/>`; }).join('');
    return `<button data-d="${dt}" aria-pressed="${dt === cur}"><span>${esc(dLabel(dt).split(' ').slice(0, 2).join(' ').replace(',', ''))}</span><svg viewBox="0 0 240 14" preserveAspectRatio="none" aria-hidden="true">${cells}</svg>`
      + `<span class="o">${pd ? num(`${k}.over.${dt}`, pd.over ? `${pd.over} h` : '0', `hours over the line, of ${pd.read} read`) : ''}</span></button>`;
  }).join('');
  el.querySelectorAll('button').forEach(b => b.onclick = () => {
    const d = b.dataset.d, js = d3.range(24).map(h => D.at[d + '|' + h]).filter(j => j != null);
    const j = D.at[d + '|' + h0] ?? js[js.length - 1]; if (j != null) { S.i = j; drawNow(); }
  });
}

function readout() {
  const k = S.issue, it = D.issues[k], i = S.i, b = D.buckets[i], dp = it.dp, U = it.unit, isNow = i === D.now;
  const w = (it.provenance || {})[it.hero_distance] || 'model';
  $('#kick').innerHTML = isNow ? `Right now · ${said(it.name)} at <span class="mono">${hhmm(b)}</span> ${prov(w)}`
    : `${said(it.name)} · ${esc(dLabel(dayOf(b)))} at <span class="mono">${hhmm(b)}</span> ${prov(w)} · ${D.now - i} h before the capture`;
  $('#back').hidden = isNow;
  const cell = D.health.cell || {}, rung = D.geometry.ladder.find(l => l.res === cell.res);
  $('#cellink').innerHTML = cell.edge_m && rung ? `${cell.edge_m} m · ${fmt(rung.own_area_m2 / 1e6, 2)} km² ›` : '';
  const cmp = it.line != null ? `against the line, ${fmt(it.line, dp)} ${U}` : 'this issue has no line';
  const n = x => num(`${k}.${it.hero_distance}`, x, cmp, `<b class="numf">${esc(x)}</b>`);
  let s, tag = '';
  if (isNow) {
    /* the split, same as the wall's: the title is the sentence's qualitative head — no number, no
       indicator — and the tagline explains it, smaller and not bold. Older nodes send no title:
       the sentence stands in, its first figure marked as before. */
    s = esc(it.title || it.sentence).replace(/(\d+(?:\.\d+)?)(?=\s*(?:°C|µg|%|m\b))/, (m0) => n(m0));
    tag = it.tagline || '';
  }
  else {
    /* a past hour speaks the engine's words too (hours[i]): what it was doing, then the reading and whose
       line. A capture older than the hours key has none, and says only that nothing is here to read. */
    const h = (it.hours || [])[i];
    s = h ? esc(h[0]) : `<span class="gone">Nothing was recorded at ${hhmm(b)}.</span>`;
    tag = h ? h[1] : '';
  }
  $('#sentence').innerHTML = (it.pix ? `<svg class="pix" aria-hidden="true"><use href="${NODE}signs.svg#${it.pix}"/></svg>` : '') + `<span class="said">${s}${tag ? `<span class="ntag">${esc(tag)}</span>` : ''}</span>`;
  /* the four distances, one quiet line: the drawing above already draws three of them */
  $('#ladder').innerHTML = ['room', 'yard', 'ring', 'region'].map(dk => {
    const x = isNow ? (it.stack[dk] || {}).value : val(k, dk, i);
    const pw = (it.provenance || {})[dk] || ((it.stack[dk] || {}).provenance), hourly = (it.series || {})[dk];
    return `<span class="d ${x == null ? 'none' : ''}"><span class="x">${said(D.labels[dk])}</span>`
      + `<span class="v">${x == null ? '—' : num(`${k}.${dk}`, fmt(x, dp), cmp)}${x == null ? '' : `<small>${said(U)}</small>`}</span>`
      + (x == null ? `<span class="gap">${hourly ? 'not recorded' : (isNow ? 'none' : 'no hours here')}</span>` : prov(pw)) + `</span>`;
  }).join('');
  decision(); rowsValues();
}

/* WHAT TO DO: the decision of the moment (learn: buttons). The three answers are the node's own words. At the live
   hour, whether something is asked is the node's one answer (/issues asking), the one the Wall reads: an event still
   asking, else an alert still true. On 14 Oct this read the events alone and said "No event was open for air" beside a
   Wall showing an open ask. A past hour is history: the events open then. The frame (.decide) and the buttons are
   drawn only while something is asked; otherwise What to do is one plain line, with the hour it is usually worst. */
function decision() {
  const k = S.issue, it = D.issues[k], B = D.buttons, live = S.i === D.now, ask = live ? (it.asking || [])[0] : null;
  const head = '<h2 class="nh">What to do</h2>', usual = live ? usualLine(k) : '';
  const line = `<p class="dm">${it.line != null ? `the line <span class="mono">${fmt(it.line, it.dp)}</span> ${said(it.unit)} · ${said(it.line_source || '')}` : 'this issue has no line: it informs, it never asks'}</p>`;
  let evs = ask && ask.event_id != null ? D.events.filter(e => e.id === ask.event_id) : [];
  if (ask && !evs.length) {
    /* an alert still true that no event stands for (answered on Telegram), or an event this screen has no row for */
    $('#decide').innerHTML = head + `<div class="decide"><p class="nk">${said(it.name)} · asked since <span class="mono">${hhmm(ask.since)}</span> · still open</p>`
      + `<p class="dq">${said(ask.says || '')}</p>${ask.how ? `<p class="dm">${said(ask.how)}</p>` : ''}` + line + `</div>`;
    return;
  }
  if (!evs.length) evs = evAt(k, S.i);
  if (!evs.length) {
    $('#decide').innerHTML = head + (live ? `<p class="nothing">Nothing to do now. ${usual ? `<span class="x">${usual}</span>` : ''}</p>`
      : `<p class="nothing">Nothing was asked about ${said(it.name.toLowerCase())} at <span class="mono">${hhmm(D.buckets[S.i])}</span>.</p>`);
    return;
  }
  const e = evs[0], a = answerWords(e.answer), on = { acted: 'done', acknowledged: 'not_now', dismissed: 'doesnt_fit' }[(e.answer || {}).stage];
  /* an answer is taken only for an event still open, at the live hour: a past hour is read, never answered */
  const asking = live && !e.cleared_at && (e.asking || !!ask);
  const what = `${said(it.name)} · ${esc(e.kind)} since <span class="mono">${hhmm(e.opened_at)}</span>${e.cleared_at ? ` · cleared <span class="mono">${hhmm(e.cleared_at)}</span>` : ' · still open'}`
    + `${e.peak != null ? ` · peak ${num(`${k}.event.peak`, fmt(e.peak, it.dp), `the line ${fmt(it.line, it.dp)} ${it.unit}`)} ${said(it.unit)}` : ''}`;
  const told = `<p class="dm">${sign(a.closed ? 'sign-rho-closed' : 'sign-rho-open', a.closed ? 'closed' : '')} ${esc(a.w)}${(e.rooms || []).length ? ` · ${e.rooms.length} room${e.rooms.length === 1 ? '' : 's'}: ${said(e.rooms.map(r => r.trim()).join(', '))}` : ''}</p>`;
  if (!asking) {
    /* answered, cleared, or a past hour: nothing is asked now, so no frame and no buttons; the event is said quietly */
    $('#decide').innerHTML = head + (live ? `<p class="nothing">Nothing to do now. ${usual ? `<span class="x">${usual}</span>` : ''}</p>` : '')
      + `<p class="dm">${what}: ${said(e.action || 'the node asked for nothing specific.')}</p>` + told;
    return;
  }
  $('#decide').innerHTML = head + `<div class="decide"><p class="nk">${what}</p>`
    + `<p class="dq">${said(e.action || 'The node asked for nothing specific.')}</p>`
    /* the buttons only while the node is still asking (e.asking, from the node): once somebody answered they go, and
       the line below says who and when. A past hour is read, never answered, so it shows none either. */
    + `<div class="ans" role="group" aria-label="Answer">${['done', 'not_now', 'doesnt_fit'].map(b => `<button class="${on === b ? 'on' : ''}" data-ev="${e.id}" data-stage="${ANSWER_STAGE[b]}">${said(B[b])}</button>`).join('')}</div>`
    + `<p class="dm" id="answered" role="status"></p>` + told + `</div>`;
}

/* Done, Not now, Doesn't fit: POST /actions with the event's id, the same write the dashboard makes (answerEvent).
   The node takes it from this machine, or with the act or admin token; its own sentence is printed when it refuses. */
const ANSWER_STAGE = { done: 'acted', not_now: 'acknowledged', doesnt_fit: 'dismissed' };
document.addEventListener('click', async ev => {
  const b = ev.target.closest && ev.target.closest('#decide .ans button[data-ev]');
  if (!b || b.disabled) return;
  const out = $('#answered'); b.disabled = true;
  let actor = ''; try { actor = localStorage.getItem('planetai_actor') || ''; } catch (e) { /* no storage here */ }
  try {
    const r = await fetch('/actions', { method: 'POST', headers: { 'content-type': 'application/json', ...DOORS_AUTH() },
      body: JSON.stringify({ event_id: Number(b.dataset.ev), stage: b.dataset.stage, actor, note: '' }) });
    const said_ = r.ok ? '' : ((await r.json().catch(() => ({}))).detail || `the node refused it (${r.status})`);
    if (!r.ok) { out.textContent = r.status === 401 || r.status === 403 ? `${said_} · unlock this screen in Set up › This screen with the act token.` : said_; b.disabled = false; return; }
    out.textContent = b.dataset.stage === 'acknowledged' ? 'Not now. The node holds this for three hours, unless it reaches danger.' : 'Recorded.';
    D = await loadD().then(d => Object.assign(d, { learn: D.learn, dates: D.dates, at: D.at, now: D.now, sens: D.sens, ngeo: D.ngeo })); VIEWS.now();
  } catch (e) { out.textContent = `The node did not answer: ${e.message}`; b.disabled = false; }
});

/* Around the house: the issues drawn by the hour, one row each; a row moves the page to that issue. Land and Coast
   change yearly and have no hours, so they are not here: Place says them, beside the ground (doors-place.js). */
function rows() {
  $('#rows').innerHTML = D.order.filter(ISSUES_DRAWN).map(k => {
    const it = D.issues[k];
    return `<button class="row" data-k="${k}" data-kind="readout" aria-pressed="false"><span><span class="n">${said(it.name)}</span><span class="state ${it.state === 'act' ? 'act' : ''}">${esc(it.state)}</span></span>`
      + `<span class="v" data-v></span><span class="sub" data-s></span></button>`;
  }).join('');
  document.querySelectorAll('#rows .row').forEach(b => b.onclick = () => { S.issue = b.dataset.k; drawNow(); });
}
function rowsValues() {
  const date = dayOf(D.buckets[S.i]);
  document.querySelectorAll('#rows .row').forEach(r => {
    const k = r.dataset.k, it = D.issues[k];
    r.setAttribute('aria-pressed', String(k === S.issue));
    const v = val(k, it.hero_distance, S.i), pd = (it.per_day || []).find(p => p.date === date);
    r.querySelector('[data-v]').innerHTML = `${num(`${k}.${it.hero_distance}`, fmt(v, it.dp), `against the line, ${fmt(it.line, it.dp)} ${it.unit}`)}<small>${said(it.unit)}</small>`;
    r.querySelector('[data-s]').innerHTML = pd ? `${pd.over ? '<span class="over" aria-hidden="true"></span>' : ''}${num(`${k}.over.day`, pd.over, `of ${pd.read} hours read, ${pd.of - pd.read} not recorded`)} h over the line ${date === dayOf(D.buckets[D.now]) ? 'today' : 'on ' + dLabel(date).split(',')[0]} · ${pd.read} of ${pd.of} h read` : 'no count for this day';
  });
}

/* Who reads around this house, now, on the node's own street map (MapLibre for the base, deck.gl for the stations,
   as on Place). Each station at the point /sensors gives this screen, its 15-minute mean beside it (GET /stats, as the
   wall reads it); the house's own sensors as one dot at the node's point with their range. Over the air line, a red
   square. A station pressed opens it in Data. Without WebGL it falls back to the rose. */
let NOWMAP = null;
async function aroundMap(el) {
  const theme = document.documentElement.dataset.theme || 'light', W = Math.min(360, el.parentNode.clientWidth), H = Math.round(W * 1.05);
  if (!window.maplibregl || !window.deck || !window.groundBase) return rose(el, { size: W });
  const M = 'pm25', line = (D.issues.air || {}).line, now15 = id => ((D.stats15[id] || {})[M] || [])[0] ?? null;
  const all = D.sensors.filter(s => s.lat != null && s.lon != null && s.source !== 'openstreetmap');
  const house = all.filter(s => s.local && s.kind === 'sensor'), hv = house.map(s => now15(s.sensor_id)).filter(v => v != null);
  const out = all.filter(s => !s.local && (s.kind === 'sensor' || s.kind === 'facility'))
    .map(s => ({ ...s, p: [s.lon, s.lat], v: s.kind === 'sensor' ? now15(s.sensor_id) : null }));
  const sea = all.find(s => s.sensor_id === 'marine-point'), C = (k, a = 1) => rgba(k, a);
  const base = await window.groundBase(theme);
  if (!NOWMAP || NOWMAP.theme !== theme || !el.contains(NOWMAP.map.getContainer())) {
    if (NOWMAP) NOWMAP.map.remove();
    el.innerHTML = `<div class="aroundmap" style="width:${W}px;height:${H}px"></div>`;
    let map; try { map = new maplibregl.Map({ container: el.firstChild, style: base.style, center: D.point, zoom: 11, attributionControl: false,
      dragRotate: false, pitchWithRotate: false, touchPitch: false, scrollZoom: false, fadeDuration: 0, transformRequest: window.groundRequest }); } catch (e) { NOWMAP = null; return rose(el, { size: W }); }   /* no WebGL: the rose */
    map.touchZoomRotate.disableRotation();
    /* the stations are what this map is for: the base's names step back, and the street names go */
    map.on('load', () => { if (map.getLayer('v-place-label')) map.setPaintProperty('v-place-label', 'text-opacity', .5);
      for (const l of ['v-road-label', 'v-poi-label']) if (map.getLayer(l)) map.setLayoutProperty(l, 'visibility', 'none'); });
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 80, unit: 'metric' }), 'bottom-left');
    const ov = new deck.MapboxOverlay({ interleaved: true, layers: [], pickingRadius: 6,
      getCursor: ({ isDragging, isHovering }) => isDragging ? 'grabbing' : isHovering ? 'pointer' : 'grab',
      onClick: i => { if (i.object && i.object.sensor_id) location.hash = 'data/' + encodeURIComponent(i.object.sensor_id); } });
    map.addControl(ov);
    const b = new maplibregl.LngLatBounds(D.point, D.point); out.forEach(s => b.extend(s.p)); if (sea) b.extend([sea.lon, sea.lat]);
    map.fitBounds(b, { padding: 26, duration: 0, maxZoom: 14 });
    NOWMAP = { map, ov, theme, geo: [] };
    /* the rose's rings and the cells, now on the map: the node's own answers (GET /geo/rings, /geo/grid), token-only
       because together they place it. The grid is resolution 7 (about 1.2 km to an edge) over what the map shows;
       the node's own res-8 cell is the one drawn solid. */
    map.once('idle', async () => {
      const ask = q => doorsFetch('/' + q).then(r => r.ok ? r.json() : null).catch(() => null);
      const bx = map.getBounds(), box = [bx.getWest(), bx.getSouth(), bx.getEast(), bx.getNorth()].map(v => v.toFixed(5)).join(',');
      const [rg, gr] = await Promise.all([ask('geo/rings?km=0.5,2,5,15'), ask(`geo/grid?res=7&bbox=${box}`)]);
      const loopLL = row => { const r = []; for (let i = 1; i < row.length; i += 2) r.push([row[i + 1], row[i]]); r.push(r[0]); return r; };
      const rings = rg ? rg.rings.map(g => ({ km: g.km, path: g.ring.map(([la, ln]) => [ln, la]) })) : [];
      const dash = new deck.PathStyleExtension({ dash: true }), mono = 'JetBrains Mono, monospace', px = { widthUnits: 'pixels', widthMinPixels: 1 };
      NOWMAP.geo = [
        ...(gr ? [new deck.PathLayer({ id: 'grid', data: gr.cells_ll.map(loopLL), getPath: d => d, getColor: rgba('--cells', .18), getWidth: 1, ...px })] : []),
        ...(D.ngeo ? [new deck.PolygonLayer({ id: 'cell8', data: [loopLL(D.ngeo.c8.ring)], getPolygon: d => d, getFillColor: rgba('--cells', .14), getLineColor: rgba('--cells'), lineWidthUnits: 'pixels', getLineWidth: 2 })] : []),
        new deck.PathLayer({ id: 'rings', data: rings, getPath: d => d.path, getColor: rgba('--ink', .45), getWidth: 1, ...px, extensions: [dash], getDashArray: d => d.km < 1 ? [2, 3] : [4, 4] }),
        new deck.TextLayer({ id: 'rings-l', data: rings, characterSet: 'auto', getPosition: d => d.path.reduce((a, q) => q[1] > a[1] ? q : a), getText: d => `${d.km} km`,
          getSize: 10.5, fontFamily: mono, getColor: rgba('--mute'), getTextAnchor: 'middle', getAlignmentBaseline: 'bottom', getPixelOffset: [0, -3],
          background: true, getBackgroundColor: rgba('--ground', .8), backgroundPadding: [3, 1] }),
      ];
      NOWMAP.cells = !!gr; NOWMAP.paint && NOWMAP.paint();
    });
  }
  const mono = 'JetBrains Mono, monospace', ink = C('--ink'), ground = C('--ground');
  NOWMAP.paint = () => NOWMAP.ov.setProps({ layers: [...NOWMAP.geo,
    new deck.ScatterplotLayer({ id: 'pub', data: out.filter(s => s.kind === 'sensor'), getPosition: d => d.p, radiusUnits: 'pixels', getRadius: 4.5,
      stroked: true, filled: true, getFillColor: ground, getLineColor: d => d.v == null ? C('--ink', .4) : ink, lineWidthUnits: 'pixels', getLineWidth: 1.5, pickable: true }),
    new deck.TextLayer({ id: 'fac', data: out.filter(s => s.kind === 'facility'), characterSet: 'auto', getPosition: d => d.p, getText: () => '◇', getSize: 15, getColor: ink, pickable: true }),
    new deck.ScatterplotLayer({ id: 'over', data: out.filter(s => line != null && s.v != null && s.v > line), getPosition: d => d.p, radiusUnits: 'pixels', getRadius: 2.5,
      getFillColor: C('--signal-worse'), getPixelOffset: [9, -6] }),
    new deck.TextLayer({ id: 'pub-v', data: out.filter(s => s.v != null), characterSet: 'auto', getPosition: d => d.p, getText: d => fmt(d.v, 0), getSize: 11.5,
      fontFamily: mono, getColor: ink, getTextAnchor: 'start', getAlignmentBaseline: 'center', getPixelOffset: [8, 0],
      background: true, getBackgroundColor: C('--ground', .78), backgroundPadding: [2, 0],
      fontWeight: 600 }),
    ...(sea ? [new deck.TextLayer({ id: 'sea', data: [sea], characterSet: 'auto', getPosition: d => [d.lon, d.lat], getText: () => '□ sea model', getSize: 11, fontFamily: mono, getColor: C('--mute'), getTextAnchor: 'start' })] : []),
    new deck.ScatterplotLayer({ id: 'house', data: [{ p: D.point }], getPosition: d => d.p, radiusUnits: 'pixels', getRadius: 6.5, getFillColor: ink, stroked: true, getLineColor: ground, lineWidthUnits: 'pixels', getLineWidth: 2 }),
    new deck.TextLayer({ id: 'house-l', data: [{ p: D.point }], characterSet: 'auto', getPosition: d => d.p, getPixelOffset: [0, 17], getTextAnchor: 'middle', getSize: 11, fontFamily: mono, getColor: ink,
      background: true, getBackgroundColor: C('--ground', .92), backgroundPadding: [3, 1],
      getText: () => `this house · ${house.length}${hv.length ? ` · ${fmt(d3.min(hv), 0)}–${fmt(d3.max(hv), 0)} ${unitOf(M)}` : ''}` }),
  ] });
  NOWMAP.paint();
  /* one line (Tomas, 15 Oct): what is drawn and what a press does; faint is a station not heard in 15 minutes */
  $('#rosecap').innerHTML = `${said(labelOf(M))} now at ${out.filter(s => s.v != null).length} public stations and ${house.length} in this house; press one to open it in Data.`
    + (base.street ? ' <span class="x">Map: OpenStreetMap contributors · Protomaps.</span>' : ` <span class="x">Rings and cells: ${UNLOCK_AT}.</span>`);
}

/* Who reads around this house, now — a stack: one quantity at many distances, on one scale. True bearings; distance on
   a square-root scale to 16 km. The value is each station's 15-minute mean, as the wall reads it. */
function rose(el, o) {
  const big = !!o.big, W = o.size, H = W, cx = W / 2, cy = H / 2, R = W / 2 - (big ? 34 : 22), MAXK = 16, M = o.metric || 'pm25';
  const r = d => Math.sqrt(Math.min(d, MAXK) / MAXK) * R, P = D.point, line = D.issues.air.line;
  const now15 = id => ((D.stats15[id] || {})[M] || [])[0] ?? null;
  /* by the node's own metres and bearing (js/nodegeo.js); a station it has no answer for is not placed */
  const at_ = id => { const q = D.ngeo && D.ngeo.dist[id]; return q ? { d: q.m / 1000, az: q.deg * Math.PI / 180 } : null; };
  const pts = D.sensors.filter(s => s.lat != null && s.kind !== 'model' && s.source !== 'openstreetmap' && at_(s.sensor_id)).map(s => {
    const { d, az } = at_(s.sensor_id);
    return { ...s, d, x: cx + r(d) * Math.sin(az), y: cy - r(d) * Math.cos(az), v: now15(s.sensor_id) };
  });
  const sea = D.sensors.find(s => s.sensor_id === 'marine-point');
  const f = big ? 1.5 : 1, T = (x, y, t, c = '', a = 'start') => `<text x="${x}" y="${y}" class="${c}" text-anchor="${a}">${esc(t)}</text>`;
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Stations around this node, by bearing and distance, with ${esc(labelOf(M))} now" style="font-size:${11 * f}px">`;
  for (const k of [0.5, 2, 5, 15]) s += `<circle cx="${cx}" cy="${cy}" r="${r(k)}" fill="none" stroke="currentColor" stroke-opacity=".22" stroke-dasharray="${k === 0.5 ? '2 3' : '4 4'}"/>`
    + T(cx - r(k) * .71 - 4, cy - r(k) * .71 - 4, `${k} km`, 'mute', 'end');
  s += `<line x1="${cx}" y1="${cy - R - 8}" x2="${cx}" y2="${cy - R + 4}" stroke="currentColor"/>` + T(cx, cy - R - 12, 'N', 'lab', 'middle');
  if (sea && at_(sea.sensor_id)) { const { d, az } = at_(sea.sensor_id);
    const x = cx + r(d) * Math.sin(az), y = cy - r(d) * Math.cos(az); s += `<rect x="${x - 4}" y="${y - 4}" width="8" height="8" fill="none" stroke="currentColor"/>` + T(x - 8, y + 4, 'sea model', 'mute', 'end'); }
  const house = pts.filter(p => p.local && p.kind === 'sensor'), out = pts.filter(p => !p.local), used = [[cx + 40, cy + 20]];
  const free = (x, y) => !used.some(([a, b]) => Math.abs(a - x) < 22 * f && Math.abs(b - y) < 12 * f) && (used.push([x, y]), true);
  for (const p of out) {
    const quiet = p.v == null, over = M === 'pm25' && !quiet && p.v > line;
    s += p.kind === 'facility' ? `<rect x="${p.x - 4}" y="${p.y - 4}" width="8" height="8" transform="rotate(45 ${p.x} ${p.y})" fill="none" stroke="currentColor"/>`
      : `<circle cx="${p.x}" cy="${p.y}" r="${4 * f}" fill="var(--ground)" stroke="currentColor" stroke-width="1.5" ${quiet ? 'stroke-dasharray="2 2"' : ''}/>`;
    if (p.kind !== 'facility' && !quiet && free(p.x + 7, p.y)) s += (over ? `<rect x="${p.x + 6}" y="${p.y - 9}" width="5" height="5" fill="var(--signal-worse)"/>` : '')
      + `<text x="${p.x + (over ? 13 : 7)}" y="${p.y + 4}" class="num" data-num="${esc(p.sensor_id)}.${M}" data-cmp="${esc(M === 'pm25' ? `the line ${line}` : 'no line')}">${fmt(p.v, 0)}</text>`;
  }
  const hv = house.map(p => p.v).filter(v => v != null);
  s += `<circle cx="${cx}" cy="${cy}" r="${7 * f}" fill="currentColor"/>`;
  s += T(cx + 11 * f, cy + 16 * f, `this house · ${house.length} stations`, 'lab') + (hv.length ? `<text x="${cx + 11 * f}" y="${cy + 30 * f}" class="num said">${fmt(d3.min(hv), 0)}–${fmt(d3.max(hv), 0)} ${esc(unitOf(M))}</text>` : '');
  el.innerHTML = s + `</svg>`;
  const quiet = out.filter(p => p.v == null && p.kind === 'sensor').length, fac = out.filter(p => p.kind === 'facility').map(p => p.name.trim());
  if (o.cap !== false) $('#rosecap').innerHTML = `${said(labelOf(M))}, the 15-minute mean, at ${out.filter(p => p.v != null).length} public stations and ${house.length} in this house; ${quiet} not heard in the last 15 minutes drawn dashed. `
    + (D.ngeo ? `${fac.length ? `The diamond${fac.length > 1 ? 's are' : ' is'} ${said(fac.join(', '))}; ` : ''}the square, the sea model. Bearings are true; distance is drawn on a square-root scale to 16 km so the house stays visible beside stations 15 km away.`
      : 'The stations are placed by the node’s own distances and bearings, which together say where it is, so this screen needs the token to draw them.');
}


document.addEventListener('keydown', ev => {
  if (document.activeElement !== $('#svg')) return;
  const step = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -24, ArrowDown: 24 }[ev.key];
  if (ev.key === 'End') { S.i = D.now; drawNow(); $('#svg').focus(); ev.preventDefault(); return; }
  if (step == null) return;
  S.i = Math.max(0, Math.min(D.now, S.i + step)); drawNow(); $('#svg').focus(); ev.preventDefault();
});
$('#back').onclick = () => { S.i = D.now; drawNow(); };
