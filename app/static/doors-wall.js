'use strict';
/* WALL, AS INSTRUMENTS (8 Nov 2026; designed 7 Nov in planetai-design/prototypes/wall-variation-instruments, after
   Tomas's Google Stitch screen of that day and the OP-XY site it was made from). It replaced the walk (house → street
   → ring → region on its own map; Tomas, 8 Nov: "Drop the map"). It draws the room's air, heat, sea and wind as
   apparatus on one black screen and replays the last 24 hours on it.
   The Wall's rules hold as they were (tests/test_doors.py): nothing under --wf, 28 px at 1920×1080; no sensor, room or
   kit named; every figure with its time and one of the five words; chrome only under a pointer or the keyboard; and
   "what is asked now" is wallAsk, the same answer Now and the phone read.
   - THE LEAD SCREEN: a header ramp (the four readings at the replayed hour, a name cell and a value cell each) over a
     stage of line art on a datum rail: fig. 1 the air drawn in and the dust settling in a jar, the day's curve inside
     it against the line; fig. 2 a thermometer for the apparent heat; fig. 3 the swell over the day with a staff at the
     hour; fig. 4 a vane turned to where the wind comes from, one streak for every 5 km/h. Under it the info line.
   - Each reading keeps its domain hue (pass-3 DESIGN.md: air grey, heat yellow, sea blue, wind mint) on its stroke and
     its digits, nothing else. The line is red, a line only. The stage is drawn in the screen's own pixels, so its words
     are --wf exactly, at any size of wall.
   - THE MOTION, one clock, one datum: the replayed hour. Every WALL_TIME.HOUR_STEP the stage steps to the next of the
     last 24 hours: the particles settle a band and are as many as that hour's µg/m³, the column and the meniscus stand
     at that hour, the swell's carrier moves a quarter wave on and the staff steps along it, the vane turns to that
     hour's bearing, the beam tips. Stepped, never tweened (no transition anywhere on the Wall); nothing counts up; the
     last hour is held, then the day starts again. Under reduced motion the stage is one still frame, at the last hour.
   - Under it: the title and sentence the engine wrote for the lead issue with what is asked now; the node thinking
     aloud in a small screen of its own, open only when its model has written something (Tomas, 8 Nov: "Yes, narration
     there", where the dust at four distances was); and a balance of the house against the line with the stations
     nearby counted. While the narration is shut the balance takes its column. */
/* Every duration on the Wall, named after the datum it paces. The replay loop is the layer's token, --motion-replay-loop. */
const WALL_TIME = {
  HOUR_STEP: () => (parseFloat(css('--motion-replay-loop')) || 30) / 24,    /* s: one replayed hour of the last 24 */
  HOLD: 4,                                                                  /* replayed hours the last hour is held */
  NARR_EVERY: 10 * 60e3,                                                    /* ms: a new reading by the node's model */
  NARR_CHAR: 1000 / 11,                                                     /* ms: one character typed, about two words a second */
  NARR_LINE: 3000,                                                          /* ms: one line of a story longer than its box, rolling */
  STALE: 15 * 60e3,                                                         /* ms: no poll this long and the readings are old */
};
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
const wallStale = h => !(Date.now() - Date.parse(h.last_poll || '') < WALL_TIME.STALE);
/* when a figure is from: the hour if today, the day if this year, the month and year if older */
function wallWhen(ts) {
  const t = new Date(ts); if (!ts || Number.isNaN(+t)) return '';
  const f = o => new Intl.DateTimeFormat('en-GB', { timeZone: D.tz, ...o }).format(t), now = new Date();
  const same = o => f(o) === new Intl.DateTimeFormat('en-GB', { timeZone: D.tz, ...o }).format(now);
  return same({ year: 'numeric', month: 'numeric', day: 'numeric' }) ? hhmm(ts) : same({ year: 'numeric' }) ? f({ day: 'numeric', month: 'short' }) : f({ month: 'short', year: 'numeric' });
}
/* one observation, newest: its value, when, and the engine's provenance word for it */
function wallObs(sid, metric) {
  const o = (D.observations || []).filter(r => r.sensor_id === sid && r.metric === metric && r.value != null).sort((a, b) => Date.parse(b.ts) - Date.parse(a.ts))[0];
  return o ? { v: o.value, ts: o.ts, word: o.kind === 'model' ? 'model' : 'partial' } : null;
}
/* a source in the Wall's own words, never a sensor's name: a name can be a room, a kit or a point ("Sea, 5 km off
   (-8.79, 115.13)"); a count of sensors is said as it is, a model by the service, anything else as "a model" */
const wallSrc = s => /^\d+ sensors?$/.test(s || '') ? s : /CAMS/i.test(s || '') ? 'CAMS' : /open-meteo/i.test(s || '') ? 'Open-Meteo' : 'a model';
const wpw = w => `<span class="wpw">${esc(w)}</span>`;
const COMPASS16 = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
/* THE DAY ON THE STAGE: the last 24 hours, an hour a row, of what the instruments draw. Each reading says where it is
   from in the Wall's words (wallSrc), its provenance word, and the time of each hour's figure. The issues' series are
   the engine's own (dust and heat at the issue's headline distance); sea and wind are the models' hourly rows (the
   token's /aggregates). Without the token a model's latest reading stands for every hour, with its own time. */
function wallDay24() {
  /* without /issues/days there are no buckets: the replay takes /aggregates' hours, else 24 whole hours up to the as-of time */
  const rb = (D.raw || {}).buckets || [], top = Math.floor(Date.parse(D.as_of) / 3600e3) * 3600e3;
  const B = D.buckets.length ? D.buckets.slice(-24) : rb.length ? rb.slice(-24) : [...Array(24)].map((_, i) => new Date(top - (23 - i) * 3600e3).toISOString());
  const at = new Map(((D.raw || {}).buckets || []).map((b, j) => [Date.parse(b), j]));
  const raw = (sid, m) => B.map(b => { const j = at.get(Date.parse(b)), s = j == null ? null : ((D.raw.series[sid] || {})[m] || [])[j]; return s ? s[0] : null; });
  const issue = k => {
    const it = D.issues[k], d = it && (it.hero_distance || 'room'), v = it && it.series && (it.series[d] || []).slice(-24);
    if (!v || !v.some(x => x != null)) return null;
    const s = (it.stack || {})[d] || {};
    return { v, ts: B, d, line: it.line, room: (it.series.room || []).slice(-24), rword: (it.provenance || {}).room || 'partial', lsrc: /WHO/.test(it.line_source || '') ? 'WHO' : 'this place’s own', unit: it.unit, dp: it.dp ?? 0,
      word: (it.provenance || {})[d] || s.provenance || 'partial', src: wallSrc(s.source), series: it.series, stack: it.stack };
  };
  const model = (sid, m, unit, dp, src) => {
    let v = raw(sid, m), ts = B;
    if (!v.some(x => x != null)) { const o = wallObs(sid, m); if (!o) return null; v = B.map(() => o.v); ts = B.map(() => o.ts); }
    return { v, ts, unit, dp, word: 'model', src };
  };
  const near = D.sensors.filter(s => s.kind === 'sensor' && !s.local && !s.indoor).map(s => {   /* an indoor station is somebody's room, not the air nearby */
    const v = raw(s.sensor_id, 'pm25'); if (!v.some(x => x != null)) v[23] = ((D.stats15[s.sensor_id] || {}).pm25 || [])[0] ?? null; return v; });
  const dust = issue('air'), house = dust && dust.room.some(x => x != null) ? { v: dust.room, ts: B, dp: dust.dp, line: dust.line, word: dust.rword } : null;
  return { B, dust, house, heat: issue('heat'), sea: model('marine-point', 'swell_height_m', 'm', 1, 'Open-Meteo'),
    wind: model('om-point', 'wind_speed', 'km/h', 0, 'Open-Meteo'), dir: model('om-point', 'wind_direction', '°', 0, 'Open-Meteo'), near };
}
const WALL = { R: null, h: null, t0: 0, still: null };
const WDOM = { air: 'var(--d-air)', heat: 'var(--d-heat)', sea: 'var(--d-sea)', wind: 'var(--d-wind)' };
/* SVG in the stage's own pixels: a word is --wf, a line is a pixel, at any size of wall */
const sx = n => n.toFixed(1);
const tx = (x, y, s, a = 'start', c = '') => `<text x="${sx(x)}" y="${sx(y)}" text-anchor="${a}"${c ? ` fill="${c}"` : ''}>${esc(s)}</text>`;
const fits = (f, w, ...say) => say.find(s => s.length * f * 0.6 <= w) ?? '';
const pth = (d, c, w, more = '') => `<path d="${d}" fill="none" stroke="${c}" stroke-width="${sx(w)}"${more}/>`;
const frac = x => x - Math.floor(x), seed = (j, k) => frac(Math.sin(j * 12.9898 + k * 78.233) * 43758.5453);
/* the dust's scale: twice the line, or past most of the day; an hour above it is drawn at the top and said */
const dustTop = r => { const s = r.v.filter(x => x != null).sort((a, b) => a - b); return Math.max((r.line ?? 0) * 2, (s[Math.floor(s.length * .9)] || 1) * 1.2); };

/* fig. 1: the air drawn in, the dust settling in the jar, the day's curve inside it against the line */
function figDust(b, h, f, r) {
  const sw = Math.max(1, f / 18), dw = Math.max(2, f / 9), C = WDOM.air, base = b.y + b.h, top = b.y + 1.6 * f, v = r && r.v[h];
  let g = tx(b.x, b.y + f, fits(f, b.w, `fig. 1 fine dust in the ${r ? D.labels[r.d] || r.d : 'house'}`, 'fig. 1 fine dust', 'fig. 1'));
  const dash = r ? '' : ` stroke-dasharray="${sx(f / 3)} ${sx(f / 4)}"`;
  /* the intake: a trumpet on a stand, the chevron lit one step an hour (the air drawn in at the hour's cadence) */
  const ix = b.x + 0.07 * b.w, iw = Math.min(0.11 * b.w, 2.6 * f), rim = top + 2 * f, neck = rim + 1.8 * f, by = top + 0.5 * (base - top);
  g += pth(`M${sx(ix - iw / 2)},${sx(rim)} L${sx(ix - iw / 7)},${sx(neck)} L${sx(ix - iw / 7)},${sx(by - iw * .4)} M${sx(ix + iw / 2)},${sx(rim)} L${sx(ix + iw / 7)},${sx(neck)} L${sx(ix + iw / 7)},${sx(by - iw * .4)}`, 'var(--ink)', sw, dash)
    + `<ellipse cx="${sx(ix)}" cy="${sx(rim)}" rx="${sx(iw / 2)}" ry="${sx(iw / 9)}" fill="none" stroke="var(--ink)" stroke-width="${sx(sw)}"/>`
    + `<ellipse cx="${sx(ix)}" cy="${sx(by)}" rx="${sx(iw * .55)}" ry="${sx(iw * .42)}" fill="#000" stroke="var(--ink)" stroke-width="${sx(sw)}"${dash}/>`
    + [-.15, 0, .15].map(k => pth(`M${sx(ix - iw * .35)},${sx(by + k * iw)} L${sx(ix + iw * .35)},${sx(by + k * iw)}`, 'var(--ink)', sw)).join('')
    + pth(`M${sx(ix)},${sx(by + iw * .42)} L${sx(ix)},${sx(base)}`, 'var(--ink)', sw);
  for (let k = 0; k < 3; k++) {
    const cy = rim - 0.35 * f - k * 0.5 * f, on = r && (h % 3) === (2 - k);
    g += pth(`M${sx(ix - f * .3)},${sx(cy - f * .25)} L${sx(ix)},${sx(cy)} L${sx(ix + f * .3)},${sx(cy - f * .25)}`, on ? C : 'var(--ink)', on ? dw * .7 : sw, on ? '' : ' opacity=".35"');
  }
  /* the jar: a bell on a plinth, a swan neck from the intake */
  const jx = b.x + 0.21 * b.w, jw = b.w - 0.23 * b.w, jt = top + 0.4 * f, R = Math.min(jw * .16, (base - jt) * .25), pl = base - 0.4 * f;
  g += pth(`M${sx(ix + iw * .55)},${sx(by)} C${sx(ix + iw * 1.6)},${sx(by)} ${sx(jx - f)},${sx(jt + R + f)} ${sx(jx)},${sx(jt + R + f)}`, 'var(--ink)', sw, dash)
    + pth(`M${sx(jx)},${sx(pl)} L${sx(jx)},${sx(jt + R)} C${sx(jx)},${sx(jt)} ${sx(jx + jw)},${sx(jt)} ${sx(jx + jw)},${sx(jt + R)} L${sx(jx + jw)},${sx(pl)}`, 'var(--ink)', sw, dash)
    + `<rect x="${sx(jx - f * .5)}" y="${sx(pl)}" width="${sx(jw + f)}" height="${sx(base - pl)}" fill="#000" stroke="var(--ink)" stroke-width="${sx(sw)}"/>`
    + pth(`M${sx(jx + jw / 2)},${sx(jt + R * .12)} L${sx(jx + jw / 2)},${sx(jt - f * .3)}`, 'var(--ink)', sw) + `<circle cx="${sx(jx + jw / 2)}" cy="${sx(jt - f * .45)}" r="${sx(f * .16)}" fill="none" stroke="var(--ink)" stroke-width="${sx(sw)}"/>`;
  if (!r) return g + tx(jx + jw / 2, pl - f, 'fine dust is not read here', 'middle', 'var(--mute)');
  /* inside: the meniscus tube at the left, the day's plot in the lower part, the particles falling above it */
  const p0 = jx + 0.17 * jw, p1 = jx + 0.95 * jw, q1 = pl - 0.5 * f, inT = jt + R * .7, q0 = inT + 0.42 * (q1 - inT), tv = dustTop(r);
  const X = i => p0 + (p1 - p0) * i / 23, Y = q => q1 - (q1 - q0) * Math.min(q, tv) / tv;
  const mx = jx + 0.075 * jw, mt = inT + 0.2 * f;
  g += `<rect x="${sx(mx - f * .22)}" y="${sx(mt)}" width="${sx(f * .44)}" height="${sx(q1 - mt)}" fill="none" stroke="var(--ink)" stroke-width="${sx(sw)}"/>`;
  const MY = q => q1 - (q1 - mt) * Math.min(q, tv) / tv;
  for (let q = 0; q <= tv; q += 5) g += pth(`M${sx(mx + f * .22)},${sx(MY(q))} l${sx(f * (q % 10 ? .2 : .4))},0`, 'var(--ink)', sw);
  if (r.line != null) g += pth(`M${sx(mx - f * .4)},${sx(MY(r.line))} l${sx(f * 1.1)},0`, 'var(--signal-worse)', dw * .7);
  if (v != null) g += pth(`M${sx(mx)},${sx(q1)} L${sx(mx)},${sx(MY(v))}`, C, f * .26);
  let d = '', pk = -1;
  r.v.forEach((q, i) => { if (q == null) return; d += `${d && r.v[i - 1] != null ? 'L' : 'M'}${sx(X(i))},${sx(Y(q))}`; if (q > tv && (pk < 0 || q > r.v[pk])) pk = i; });
  g += pth(`M${sx(p0)},${sx(q1)} L${sx(p1)},${sx(q1)}`, 'var(--ink)', sw, ' opacity=".4"') + pth(d, C, dw);
  if (r.line != null) g += pth(`M${sx(p0)},${sx(Y(r.line))} L${sx(p1)},${sx(Y(r.line))}`, 'var(--signal-worse)', dw * .7, ` stroke-dasharray="${sx(f * .4)} ${sx(f * .25)}"`)
    + tx(p0 + f * .3, Y(r.line) - f * .35, `line ${fmt(r.line, r.dp)}`);
  if (pk >= 0) g += tx(Math.min(X(pk) + f * .3, p1 - f * 6), q0 + f * .2, `↑ ${fmt(r.v[pk], 0)} at ${hhmm(r.ts[pk])}`, 'start', C);
  g += pth(`M${sx(X(h))},${sx(q0 - f * .2)} L${sx(X(h))},${sx(q1)}`, 'var(--ink)', sw, ' opacity=".6"');
  if (v != null) g += `<circle cx="${sx(X(h))}" cy="${sx(Y(v))}" r="${sx(f * .22)}" fill="${C}"/>`;
  else g += tx(X(h), q0 - f * .5, `not read at ${hhmm(r.ts[h])}`, X(h) > (p0 + p1) / 2 ? 'end' : 'start', 'var(--mute)');
  /* the particles: one for every µg/m³ at the hour (counted, never sized; past 60 the figure in the ramp says it), each
     falling one of eight bands an hour and coming round at the top: the dust settling, a reading at a time */
  const n = Math.min(60, Math.round(v ?? 0)), bT = inT + 0.2 * f, bH = (q0 - f * .9 - bT) / 8;
  for (let j = 0; j < n && bH > 0; j++) {
    const band = (Math.floor(seed(j, 2) * 8) + h) % 8;
    g += `<circle cx="${sx(p0 + (p1 - p0) * seed(j, 1))}" cy="${sx(bT + (band + seed(j, 3)) * bH)}" r="${sx(Math.max(2, f / 10))}" fill="${C}"/>`;
  }
  return g;
}
/* fig. 2: a thermometer for the apparent heat, its line a red tick across the tube */
function figHeat(b, h, f, r) {
  const sw = Math.max(1, f / 18), C = WDOM.heat, base = b.y + b.h, v = r && r.v[h];
  let g = tx(b.x, b.y + f, fits(f, b.w, 'fig. 2 apparent heat', 'fig. 2 heat', 'fig. 2'));
  const cx = b.x + 0.36 * b.w, th = f * .24, ty = b.y + 2.1 * f, br = f * .56, bc = base - 1.5 * f;
  const dash = r ? '' : ` stroke-dasharray="${sx(f / 3)} ${sx(f / 4)}"`;
  g += pth(`M${sx(cx - th)},${sx(bc - br * .8)} L${sx(cx - th)},${sx(ty)} L${sx(cx + th)},${sx(ty)} L${sx(cx + th)},${sx(bc - br * .8)}`, 'var(--ink)', sw, dash)
    + `<circle cx="${sx(cx)}" cy="${sx(bc)}" r="${sx(br)}" fill="none" stroke="var(--ink)" stroke-width="${sx(sw)}"${dash}/>`
    + pth(`M${sx(cx)},${sx(bc + br)} L${sx(cx)},${sx(base)} M${sx(cx - f * .6)},${sx(base - f * .3)} L${sx(cx + f * .6)},${sx(base - f * .3)}`, 'var(--ink)', sw);
  if (!r) return g + tx(cx, ty - f * .3, 'not read', 'middle', 'var(--mute)');
  const all = r.v.concat(r.line ?? []).filter(x => x != null), lo = Math.floor(Math.min(...all) - 2), hi = Math.ceil(Math.max(...all) + 2);
  const yt = ty + f * .4, yb = bc - br - f * .2, Y = q => yb - (yb - yt) * (q - lo) / (hi - lo);
  for (let q = lo; q <= hi; q++) {
    const five = q % 5 === 0;
    g += pth(`M${sx(cx - th)},${sx(Y(q))} l${sx(-f * (five ? .45 : .2))},0`, 'var(--ink)', sw);
    if (five && q !== r.line && Y(q) > ty + f && Y(q) < yb - f * .5) g += tx(cx - th - f * .6, Y(q) + f * .35, String(q), 'end');
  }
  g += `<circle cx="${sx(cx)}" cy="${sx(bc)}" r="${sx(br * .62)}" fill="${C}"/>`;
  if (v != null) g += pth(`M${sx(cx)},${sx(bc)} L${sx(cx)},${sx(Y(v))}`, C, th * 1.1);
  else g += tx(cx + th + f * .4, yb, `not read at ${hhmm(r.ts[h])}`, 'start', 'var(--mute)');
  if (r.line != null) g += pth(`M${sx(cx - th - f * .3)},${sx(Y(r.line))} L${sx(cx + th + f * .3)},${sx(Y(r.line))}`, 'var(--signal-worse)', f / 12)
    + tx(cx + th + f * .5, Y(r.line) + f * .35, fits(f, b.x + b.w - cx - th - f * .5, `line ${fmt(r.line, 0)}`, String(fmt(r.line, 0))))
    + tx(cx - th - f * .6, Y(r.line) + f * .35, String(fmt(r.line, 0)), 'end');
  return g;
}
/* fig. 3: the swell over the last 24 hours, left to right; its carrier moves a quarter wave on with each replayed hour
   and the staff steps to the hour, its height said at the top */
function figSea(b, h, f, r) {
  const sw = Math.max(1, f / 18), dw = Math.max(2, f / 9), C = WDOM.sea, base = b.y + b.h, v = r && r.v[h];
  let g = tx(b.x, b.y + f, fits(f, b.w, 'fig. 3 the swell, 24 h', 'fig. 3 the swell', 'fig. 3 swell', 'fig. 3'));
  const x0 = b.x + 0.03 * b.w, x1 = b.x + 0.97 * b.w, yM = b.y + 0.62 * b.h, Am = Math.min(0.2 * b.h, 3 * f);
  g += pth(`M${sx(x0)},${sx(yM)} L${sx(x1)},${sx(yM)}`, 'var(--ink)', sw, ` stroke-dasharray="${sx(sw * 2)} ${sx(f / 4)}" opacity=".5"`);
  if (!r) return g + tx((x0 + x1) / 2, yM - f * .6, 'the sea is not read here', 'middle', 'var(--mute)');
  const mx = Math.max(2, ...r.v.filter(q => q != null)) * 1.1, A = q => Am * q / mx, lam = Math.max(f * 1.6, (x1 - x0) / 8), ph = h * lam / 4;
  const at = t => { const i = Math.floor(t), a = r.v[i], z = r.v[Math.min(23, i + 1)]; return a == null ? z : z == null ? a : a + (z - a) * (t - i); };
  let d = '';
  for (let x = x0; x <= x1; x += 3) {
    const q = at(23 * (x - x0) / (x1 - x0)); if (q == null) { d += ' '; continue; }
    d += `${/\d$/.test(d) ? 'L' : 'M'}${sx(x)},${sx(yM - A(q) * Math.sin(2 * Math.PI * (x - x0 + ph) / lam))}`;
  }
  g += pth(d.trim(), C, dw * .8);
  const sX = x0 + (x1 - x0) * h / 23, sT = yM - Am - f * .9;
  g += pth(`M${sx(sX)},${sx(base)} L${sx(sX)},${sx(sT)}`, 'var(--ink)', sw);
  for (let q = 0; q <= mx; q += 0.5) g += pth(`M${sx(sX)},${sx(yM - A(q))} l${sx(f * (q % 1 ? .2 : .4))},0`, 'var(--ink)', sw);
  if (v != null) g += `<rect x="${sx(sX - f * .2)}" y="${sx(yM - A(v) - f * .2)}" width="${sx(f * .4)}" height="${sx(f * .4)}" fill="${C}"/>`
    + tx(Math.min(Math.max(sX, x0 + f * 2), x1 - f * 2), sT - f * .3, `${fmt(v, 1)} m`, 'middle', C);
  return g + tx(x0, base - f * .4, fits(f, (x1 - x0) / 2, '24 h ago', ''));
}
/* fig. 4: a vane on a mast, turned to where the wind comes from at the hour; one streak for every 5 km/h behind its
   tail, up to eight (40 km/h) where the tail has room; past it the ramp's figure says it (more wind is more signs,
   never a bigger vane) */
function figWind(b, h, f, s, dr) {
  const sw = Math.max(1, f / 18), dw = Math.max(2, f / 9), C = WDOM.wind, base = b.y + b.h, sp = s && s.v[h], deg = dr && dr.v[h];
  let g = tx(b.x, b.y + f, fits(f, b.w, 'fig. 4 the wind', 'fig. 4 wind', 'fig. 4'));
  const R = Math.max(f * 2, Math.min(0.42 * b.w, (b.h - 2.6 * f) / 2)), cx = b.x + b.w / 2, cy = b.y + 1.7 * f + R;
  g += `<circle cx="${sx(cx)}" cy="${sx(cy)}" r="${sx(R)}" fill="none" stroke="var(--ink)" stroke-width="${sx(sw)}"/>`
    + `<circle cx="${sx(cx)}" cy="${sx(cy)}" r="${sx(R * .84)}" fill="none" stroke="var(--ink)" stroke-width="${sx(sw)}" opacity=".35"/>`
    + pth(`M${sx(cx)},${sx(cy + R)} L${sx(cx)},${sx(base)} M${sx(cx - f * .6)},${sx(base - f * .3)} L${sx(cx + f * .6)},${sx(base - f * .3)}`, 'var(--ink)', sw);
  for (let k = 0; k < 16; k++) {
    const a = k * Math.PI / 8, i = k % 4 ? R * .9 : R * .76;
    g += pth(`M${sx(cx + Math.sin(a) * i)},${sx(cy - Math.cos(a) * i)} L${sx(cx + Math.sin(a) * R)},${sx(cy - Math.cos(a) * R)}`, 'var(--ink)', sw);
  }
  g += tx(cx, cy - R * .55 + f * .35, 'N', 'middle', 'var(--mute)');
  if (deg == null) return g + tx(cx, cy + f * .35, s ? `not read at ${hhmm(s.ts[h])}` : 'not read', 'middle', 'var(--mute)');
  const tip = R * .72, tail = R * .6, n = Math.min(8, Math.round((sp ?? 0) / 5));
  let vane = pth(`M${sx(cx)},${sx(cy + tail)} L${sx(cx)},${sx(cy - tip)}`, C, dw)
    + pth(`M${sx(cx - f * .32)},${sx(cy - tip + f * .55)} L${sx(cx)},${sx(cy - tip)} L${sx(cx + f * .32)},${sx(cy - tip + f * .55)}`, C, dw)
    + pth(`M${sx(cx)},${sx(cy + tail - f * .9)} L${sx(cx + f * .5)},${sx(cy + tail)} L${sx(cx)},${sx(cy + tail)}`, C, sw * 1.5);
  for (let j = 0; j < n; j++) vane += pth(`M${sx(cx - f * .5 - j * f * .28)},${sx(cy + tail * .3 + j * f * .3)} l0,${sx(f * .5)}`, C, sw * 1.5);
  return g + `<g transform="rotate(${sx(deg)} ${sx(cx)} ${sx(cy)})">${vane}</g><circle cx="${sx(cx)}" cy="${sx(cy)}" r="${sx(f * .14)}" fill="var(--ink)"/>`;
}
/* the stage: four boxes on a datum rail; on a narrow stage the jar takes a row of its own */
function wallStage(el, h, f) {
  const W = el.clientWidth, H = el.clientHeight, R = WALL.R; if (W < 8 * f || H < 6 * f) return;
  const rails = [], box = (x, w, y, hh) => ({ x, w, y, h: hh });
  let B;
  if (W >= 900) { const y = 0, hh = H - f * .9; rails.push(hh); B = [box(0, .43 * W, y, hh), box(.455 * W, .14 * W, y, hh), box(.615 * W, .2 * W, y, hh), box(.835 * W, .165 * W, y, hh)]; }
  else { const h1 = .52 * H, h2 = H - f * .9; rails.push(h1, h2); B = [box(0, W, 0, h1), box(0, .26 * W, h1 + f * .9, h2 - h1 - f * .9), box(.29 * W, .4 * W, h1 + f * .9, h2 - h1 - f * .9), box(.72 * W, .28 * W, h1 + f * .9, h2 - h1 - f * .9)]; }
  let g = '';
  for (const y of rails) {
    g += pth(`M0,${sx(y)} L${W},${sx(y)}`, 'var(--ink)', Math.max(1.5, f / 14));
    for (let x = f; x < W; x += f) g += pth(`M${sx(x)},${sx(y)} l0,${sx(f * ((x / f) % 5 ? .2 : .4))}`, 'var(--ink)', 1, ' opacity=".5"');
  }
  g += figDust(B[0], h, f, R.dust) + figHeat(B[1], h, f, R.heat) + figSea(B[2], h, f, R.sea) + figWind(B[3], h, f, R.wind, R.dir);
  el.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(wallSays(h))}">${g}</svg>`;
}
/* the stage in words, for a screen reader: the four readings at the hour */
function wallSays(h) {
  const R = WALL.R, t = r => r.ts[h] !== R.B[h] ? ` at ${hhmm(r.ts[h])}` : '', p = (r, w, u) => r && r.v[h] != null ? `${w} ${fmt(r.v[h], r.dp)} ${u}${t(r)}` : '';
  return [`At ${hhmm(R.B[h])}`, p(R.dust, 'fine dust', 'µg/m³'), p(R.heat, 'apparent heat', '°C'), p(R.sea, 'swell', 'm'),
    R.dir && R.dir.v[h] != null ? `wind from ${COMPASS16[Math.round(R.dir.v[h] / 22.5) % 16]}${t(R.dir)}${R.wind && R.wind.v[h] != null ? `, ${fmt(R.wind.v[h], 0)} km/h${t(R.wind)}` : ''}` : ''].filter(Boolean).join(', ');
}
/* a name cell and a value cell of a header ramp: the figure, its time and its word, or that it is not read */
function rampPair(name, src, r, h, val, col) {
  const n = `<div class="wrn"><b>${esc(name)}</b><span>${esc(src || '')}</span></div>`;
  if (!r || r.v[h] == null) return n + `<div class="wrv"><b>—</b><span>${r ? `not read at ${hhmm(r.ts[h])}` : 'not read here'}</span></div>`;
  return n + `<div class="wrv" style="--c:${col}"><b class="wnum">${val}</b><span>${hhmm(r.ts[h])} ${wpw(r.word)}</span></div>`;
}
const unitOn = (v, u) => `${v}<u>${esc(u)}</u>`;
/* small screen: a beam balance, the house in one pan and the line in the other, tipped by which is heavier, and the
   stations nearby counted under it, one square a station, those over the line marked red; the caption says it in words */
function wallBalance(el, h, f) {
  const W = el.clientWidth, H = el.clientHeight, r = WALL.R.dust; if (W < 6 * f || H < 4 * f || !r || r.line == null) return;
  const hs = WALL.R.house;
  const v = hs ? hs.v[h] : null, sw = Math.max(1, f / 18), dw = Math.max(2, f / 9), near = WALL.R.near.map(s => s[h]).filter(x => x != null);
  const px = W / 2, py = f * 2.1, bl = Math.min(W * .34, f * 8), th = v == null ? 0 : -Math.max(-1, Math.min(1, (v - r.line) / r.line)) * 8 * Math.PI / 180;
  const sq = f * .42, gap = f * .2, per = Math.max(1, Math.floor((W - f) / (sq + gap))), rows = Math.ceil(near.length / per), sy = H - rows * (sq + gap);
  const pivB = sy - f * .4;
  let g = pth(`M${sx(px)},${sx(py)} L${sx(px)},${sx(pivB)} M${sx(px - f)},${sx(pivB)} L${sx(px + f)},${sx(pivB)}`, 'var(--ink)', sw)
    + pth(`M${sx(px - f * .3)},${sx(py + f * .5)} L${sx(px)},${sx(py)} L${sx(px + f * .3)},${sx(py + f * .5)}`, 'var(--ink)', sw);
  [[-1, v, 'house', WDOM.air], [1, r.line, 'line', 'var(--ink)']].forEach(([k, q, w, c]) => {
    const ex = px + k * bl * Math.cos(th), ey = py + k * bl * Math.sin(th), pan = ey + f * 1.3;
    g += pth(`M${sx(ex)},${sx(ey)} L${sx(ex - f * .8)},${sx(pan)} M${sx(ex)},${sx(ey)} L${sx(ex + f * .8)},${sx(pan)}`, 'var(--ink)', sw)
      + pth(`M${sx(ex - f * 1.1)},${sx(pan)} Q${sx(ex)},${sx(pan + f * .7)} ${sx(ex + f * 1.1)},${sx(pan)} Z`, k < 0 ? c : 'var(--signal-worse)', k < 0 ? dw * .7 : sw * 1.5)
      + tx(ex, ey - f * .45, q == null ? `${w} —` : `${w} ${fmt(q, r.dp)}`, 'middle', k < 0 ? c : '');
  });
  g += pth(`M${sx(px - bl * Math.cos(th))},${sx(py - bl * Math.sin(th))} L${sx(px + bl * Math.cos(th))},${sx(py + bl * Math.sin(th))}`, 'var(--ink)', dw * .8);
  const x0 = (W - Math.min(near.length, per) * (sq + gap) + gap) / 2;
  near.sort((a, b) => a - b).forEach((q, i) => {
    const over = q > r.line;
    g += `<rect x="${sx(x0 + (i % per) * (sq + gap))}" y="${sx(sy + Math.floor(i / per) * (sq + gap))}" width="${sx(sq)}" height="${sx(sq)}" fill="none" stroke="${over ? 'var(--signal-worse)' : 'var(--ink)'}" stroke-width="${sx(over ? dw * .7 : sw)}"/>`;
  });
  el.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="The house against the line, and the stations nearby">${g}</svg>`;
}
/* one replayed hour, drawn whole: the ramp, the stage, the balance and their info lines */
function wallDraw(h) {
  WALL.h = h; const R = WALL.R, v = $('#wallv'); if (!R || !v) return;
  const f = parseFloat(getComputedStyle(v).fontSize) || 28, at = hhmm(R.B[h]), d = R.dust, near = R.near.map(s => s[h]).filter(x => x != null);
  const dir = R.dir && R.dir.v[h] != null ? ` ${COMPASS16[Math.round(R.dir.v[h] / 22.5) % 16]}` : '';
  $('#wramp').innerHTML = rampPair('fine dust', d && d.src, d, h, d && unitOn(fmt(d.v[h], d.dp), 'µg/m³'), WDOM.air)
    + rampPair('apparent heat', R.heat && R.heat.src, R.heat, h, R.heat && unitOn(fmt(R.heat.v[h], 1), '°C'), WDOM.heat)
    + rampPair('swell', R.sea && R.sea.src, R.sea, h, R.sea && unitOn(fmt(R.sea.v[h], 1), 'm'), WDOM.sea)
    + rampPair(`wind${dir ? ` from${dir}` : ''}`, R.wind && R.wind.src, R.wind, h, R.wind && unitOn(fmt(R.wind.v[h], 0), 'km/h'), WDOM.wind);
  $('#winfo').textContent = `wall · ${D.node.place || ''} · hour ${at} of the last 24 · cell ${(D.health.cell || {}).id || ''}`;
  const hs = R.house;
  $('#wbramp').innerHTML = rampPair('house, µg/m³', '', hs, h, hs && fmt(hs.v[h], hs.dp), WDOM.air);
  $('#wcap').textContent = d ? wallCaption(hs ? hs.v[h] : null, near, d.line, `at ${at}`) : '';
  $('#wbinfo').textContent = `${near.length} stations nearby · partial`;
  wallStage($('#wstage'), h, f); wallBalance($('#wbal'), h, f);
}
/* the replay's one clock: an hour every HOUR_STEP, the last held for HOLD of them, then the day again */
function wallTick(now) {
  if (view() !== 'wall') return CLOCK.off('wall-replay');
  if (CLOCK.reduced()) { WALL.still = true; CLOCK.off('wall-replay'); if (WALL.h !== 23) wallDraw(23); return; }   /* motion turned off while it ran */
  const i = Math.floor((now - WALL.t0) / (WALL_TIME.HOUR_STEP() * 1000)) % (24 + WALL_TIME.HOLD), h = Math.min(i, 23);
  if (h !== WALL.h) wallDraw(h);
}
VIEWS.wall = async function () {
  const k = D.lead, it = D.issues[k], still = CLOCK.reduced();
  const at = new Intl.DateTimeFormat('en-GB', { timeZone: D.tz, hour: '2-digit', minute: '2-digit' }).format(new Date(D.as_of));
  /* a redraw on a poll keeps the replay's hour; motion turned on or off since the last draw, even on another door, starts it over */
  if (WALL.h == null || WALL.still !== still) { WALL.h = still ? 23 : 0; WALL.t0 = performance.now(); }
  WALL.still = still;
  WALL.R = wallDay24();
  if (!WALL.sized) { WALL.sized = true; addEventListener('resize', () => { if (view() === 'wall') wallDraw(WALL.h ?? 23); });   /* the stages are drawn in their own pixels */
    matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', e => {           /* still at the last hour, or the replay again */
      if (view() !== 'wall') return;
      WALL.still = e.matches;
      if (e.matches) { CLOCK.off('wall-replay'); wallDraw(23); } else { WALL.t0 = performance.now(); CLOCK.on('wall-replay', wallTick); }
    }); }
  $('#wallv').innerHTML = `
    <div class="wtop wchrome"><button class="wback" onclick="location.hash='#now'">← back</button><span class="wnote said" id="wnote"></span></div>
    <section class="wscr wlead" data-learn="wall-stage" data-reads="/issues /aggregates /observations" data-stage="observe" data-pack="core">
      <div class="wramp" id="wramp"></div><div class="wstage" id="wstage"></div><p class="winfo" id="winfo"></p></section>
    <div class="wlow">
      <div class="whead" data-learn="wall-sentence" data-reads="/issues /health" data-stage="decide" data-pack="core">
        <div class="wkick"><time>${at}</time>${wallStale(D.health) ? ' · <b>the readings are old</b>' : ''}</div>
        <p class="wsent"><span class="said">${esc(it.title || it.sentence).replace(/(\d+(?:\.\d+)?)(?=\s*(?:°C|µg|%|m\b))/, m0 => num(`${k}.${it.hero_distance}`, m0, `against the line, ${it.line} ${it.unit}`, `<b class="wnum">${m0}</b>`))}</span></p>
        ${it.title && it.tagline ? `<p class="wtag said">${esc(it.tagline)}</p>` : ''}
        <div class="wask">${wallAsk(it)}</div></div>
      <section class="wscr wsmall wnarr" id="wnarr" hidden data-learn="wall-narration" data-reads="/ask/status /ask" data-stage="observe" data-pack="core"></section>
      <section class="wscr wsmall" data-learn="wall-balance" data-reads="/issues /stats /aggregates" data-stage="observe" data-pack="core">
        <div class="wramp" id="wbramp"></div><div class="wstage" id="wbal"></div><p class="wcap said" id="wcap"></p><p class="winfo" id="wbinfo"></p></section>
    </div>`;
  wallDraw(WALL.h); narrDraw(); document.fonts.ready.then(() => view() === 'wall' && wallDraw(WALL.h));
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
  if (was !== el.hidden && WALL.R) wallDraw(WALL.h ?? 23);   /* the balance gains or gives up a column: redraw it at its new width */
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
