'use strict';
/* SHEET — the Place report's first page (SPEC_place_report §4): the screen drawn as a plan, in a black frame, with a grid
   in metres, a scale bar, a north arrow, the legend, the coordinates and the credits. Pure: no DOM and no D of its own.
   doors-placemap.js takes the picture (window.placeSheet), doors-place.js puts the sheet on #place/report, and the
   browser's print makes the PDF. reportPages draws the pages after it (§5). `esc` and `cakeSections` are the page's
   (doors-core.js, doors-cake.js). */

/* the grid's step: a round 1, 2, 2.5 or 5 × 10ⁿ m that puts five to eight lines on the longer side, the edge's 0 m
   included. With 1, 2 and 5 alone a side of 1.6 to 2 × 10ⁿ m has no such step, so 2.5 is one of them. */
function gridStep(L) {
  if (!(L > 0)) return 1;
  for (let e = 10 ** Math.floor(Math.log10(L)); ; e /= 10) for (const k of [5, 2.5, 2, 1]) if (Math.floor(L / (k * e)) >= 4) return k * e;
}
/* the lines, in the picture's own pixels: across from the left edge, up from the bottom one */
function gridLines(w, h, mpp) {
  const step = gridStep(Math.max(w, h) * mpp), px = step / mpp, at = n => Array.from({ length: Math.floor(n * mpp / step) + 1 }, (_, k) => k * px);
  return { step, px, xs: at(w), ys: at(h).map(y => h - y) };
}
const gridM = m => { const r = +m.toFixed(1); return r >= 1000 ? `${+(r / 1000).toFixed(2)} km` : `${r} m`; };   // rounded first: 999.97 m read '1000 m' beside '2 km'

/* the legend: each layer on and in view, under its section of the cake, in the cake's order, with its source */
const sheetLegend = (layers, on, z) => cakeSections(layers.filter(l => on[l.id] && (l.minz == null || z >= l.minz) && (l.maxz == null || z <= l.maxz)), on)
  .filter(s => s.rows.length).map(s => ({ name: s.name, rows: s.rows.map(r => ({ name: r.name, src: layers.find(l => l.id === r.id).src })) }));

/* the picture with its frame, grid, crosses, north arrow and, under it, the scale bar: one SVG in the picture's pixels,
   so all of it scales with the picture */
function sheetSVG(c) {
  const { w, h } = c, G = gridLines(w, h, c.mpp), u = Math.max(w, h) / 100, f = v => v.toFixed(1);
  const ink = c.dark ? '#F9F5F2' : '#171717', halo = c.dark ? '#17191D' : '#F1EFEB';
  const t = (x, y, s, a = 'start') => `<text x="${f(x)}" y="${f(y)}" text-anchor="${a}">${s}</text>`;
  const cross = G.xs.slice(1).flatMap(x => G.ys.slice(1).map(y => `M${f(x - u * .7)},${f(y)}h${f(u * 1.4)}M${f(x)},${f(y - u * .7)}v${f(u * 1.4)}`)).join('');
  const bar = c.bar / c.mpp, B = [0, 1, 2, 3].map(i => `<rect x="${f(i * bar / 4)}" y="${f(h + 2 * u)}" width="${f(bar / 4)}" height="${f(u)}" fill="${i % 2 ? '#FFFFFF' : '#171717'}"/>`).join('');
  return `<svg class="splan" viewBox="${f(-u)} ${f(-u)} ${f(w + 2 * u)} ${f(h + 7 * u)}" preserveAspectRatio="xMinYMin meet" role="img" aria-label="The map, with a grid in metres">`
    + `<image href="${c.img}" width="${w}" height="${h}"/>`
    + `<g stroke="${ink}" fill="none"><path d="${G.xs.slice(1).map(x => `M${f(x)},0V${h}`).join('') + G.ys.slice(1).map(y => `M0,${f(y)}H${w}`).join('')}" stroke-width="${f(u * .08)}" opacity=".35"/>`
    + `<path d="${cross}" stroke-width="${f(u * .15)}"/></g>`
    + `<g font-family="JetBrains Mono, monospace" font-size="${f(u * 1.15)}" fill="${ink}" stroke="${halo}" stroke-width="${f(u * .3)}" paint-order="stroke">`
    + G.xs.map(x => t(x + u * .4, h - u * .6, gridM(x * c.mpp))).join('') + G.ys.slice(1).map(y => t(u * .4, y - u * .4, gridM((h - y) * c.mpp))).join('')
    + `<path d="M${f(w - 3 * u)},${f(2.4 * u)}l${f(u)},${f(2.6 * u)}l${f(-u)},${f(-.7 * u)}l${f(-u)},${f(.7 * u)}z" fill="${ink}"/>${t(w - 3 * u, 1.9 * u, 'N', 'middle')}</g>`
    + `<rect width="${w}" height="${h}" fill="none" stroke="#171717" stroke-width="${f(u * .4)}"/>`
    + `<g font-family="JetBrains Mono, monospace" font-size="${f(u * 1.15)}" fill="#171717">${B}<rect y="${f(h + 2 * u)}" width="${f(bar)}" height="${f(u)}" fill="none" stroke="#171717" stroke-width="${f(u * .1)}"/>`
    + `${t(0, h + 4.6 * u, '0')}${t(bar, h + 4.6 * u, gridM(c.bar), 'middle')}</g></svg>`;
}

/* The sheet, from the picture (window.placeSheet) and the node's res-8 cell as GET /geo/cell rings it (`c8`). The
   coordinates are that cell's centre, the mean of its six corners, never the house's point: no text here is closer
   than the cell /health names. Without a picture the node's sentence stands where the map would be. */
function sheetHTML(D, c, c8) {
  const h = D.health || {}, cell = h.cell || {}, G = c.img && gridLines(c.w, c.h, c.mpp), L = c.img && c.w * c.mpp;
  const ctr = c8 && c8.length > 6 ? [0, 1].map(k => c8.slice(1).filter((_, i) => i % 2 === k).reduce((a, b) => a + b, 0) / ((c8.length - 1) / 2)) : null;
  const where = [ctr && `${ctr[0].toFixed(4)}, ${ctr[1].toFixed(4)}`, L && `${(L / 1000).toFixed(L >= 10000 ? 1 : 2)} km across`, G && `grid ${gridM(G.step)}`, cell.id && `cell ${cell.id}`]
    .filter(Boolean).map(esc).join(' · ');
  const leg = (c.legend || []).map(s => `<h3>${esc(s.name)}</h3>` + s.rows.map(r => `<p><span>${esc(r.name)}</span><small>${esc(r.src)}</small></p>`).join('')).join('');
  const maps = (c.maps || []).map(m => `<p><span>${m.colours.filter(x => /^#[0-9A-Fa-f]{6}$/.test(x)).map(x => `<i style="background:${x}"></i>`).join('')}${esc(m.name)}</span></p>`).join('');
  const name = h.place || D.node.name, say = typeof asHouse === 'function' ? asHouse : (x => x);
  const made = `Made on PLANETAI ${h.version || ''}, ${c.date || ''} · ${name}`;
  return `<article class="sheet" aria-label="The sheet"><div class="sin"><div class="smap">${c.img ? sheetSVG(c) : `<p class="snone">${esc(c.none)}</p>`}</div>`
    + `<div class="sleg"><h2>${esc(name)}</h2><p class="k">Place${c.rung ? ` · ${esc(c.rung)}, res ${esc(c.res)}` : ''}</p>`
    + (c.img && c.home !== false ? `<p class="shouse"><span><i></i>${esc(say('This house, drawn as its res-10 cell'))}</span></p>` : '') + leg + (maps ? `<h3>your maps</h3>${maps}` : '')
    + `<div class="sfoot"><p class="mono">${where}</p><p>${[...(c.credits || []), made].map(esc).join(' · ')}</p></div></div></div></article>`;
}

/* THE READING (SPEC_place_report §11), the report's first two pages: what kind of place this is, in five sections, and
   the ways to improve it, each in the frame of the Fab City Full Stack, with what the reading cannot see. `R` is GET
   /place/reading: the node's own rules, and a model's text in their place when one was written and held. Under each
   title the page says who wrote it and when, so a text a model wrote never passes as a person's. With no reading (the
   route refused or did not answer) there are no pages. */
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const longDay = iso => { const [y, m, d] = String(iso).slice(0, 10).split('-').map(Number); return `${d} ${MONTHS[m - 1]} ${y}`; };
const readingBy = R => R.written
  ? `Written by a language model on ${R.by.where} (${R.by.model}) from the node’s figures, ${longDay(R.written_at)}. The node checked its numbers.`
  : `Written by this node from its own figures, ${longDay(R.facts_at)}.`;
/* the same, in one line, for the block at the foot of Place (§12) */
const readingFoot = R => `Reading written ${longDay(R.written ? R.written_at : R.facts_at)} by ${R.written ? `a language model on ${R.by.where}` : 'this node'}`;
function readingPages(D, R) {
  if (!R || !R.rules) return [];
  const W = R.written, who = `<p class="rwho">${esc(readingBy(R))}</p>`, blind = R.rules.blind || [];
  /* a model's avenue to experiment keeps the lab the rules found: the facts hold its distance, the model was not asked for it */
  const lab = (R.rules.avenues.find(a => a.with) || {}).with, withOf = a => a.with || (W && a.action === 'Experiment' ? lab : null);
  const secs = R.rules.sections.map(s => `<section class="rs"><h4>${esc(s.heading)}</h4><p>${esc(W ? W.sections[s.id] : s.lines.join(' '))}</p></section>`).join('');
  const cannot = blind.length ? '<h3 class="pmh">what this reading cannot see</h3><p class="rblind">The node does not hold these yet. Each is followed by what fills it.</p><ul class="rblind">'
    + blind.map(b => `<li>${esc(b.what)}: <code>${esc(b.command)}</code></li>`).join('') + '</ul>' : '';
  /* a page is one A4 sheet and does not grow in print. The node's own avenues are short by construction and fit with
     what it cannot see. A model's are as long as it wrote them (reading.py caps each part), so past four they go on a
     page of their own with what is missing */
  const AV = W ? W.avenues : R.rules.avenues, av = (a, i) => `<div class="av"><b>${i + 1}</b><div><h4>${esc(a.title)}</h4><p class="avf">${esc(a.layer)} · ${esc(a.action)}</p>`
    + `<p>${esc(a.why)}</p><p><span class="avk">First step</span> ${esc(a.first_step)}</p>${withOf(a) ? `<p><span class="avk">With</span> ${esc(withOf(a))}</p>` : ''}</div></div>`;
  const cut = W && AV.length > 4 ? 4 : AV.length, title = '<h3 class="pmh">ways to improve it</h3>';
  return [`<h3 class="pmh">a reading of this place</h3>${who}${secs}`,
    title + who + AV.slice(0, cut).map(av).join('') + (cut < AV.length ? '' : cannot),
    cut < AV.length && title.replace('</h3>', ', continued</h3>') + AV.slice(cut).map((a, i) => av(a, cut + i)).join('') + cannot].filter(Boolean);
}

/* WHAT IS COMING (GET /forecast `days`, the rows the Now door's forecast draws): one row a day for the air, the heat,
   the rain and the sea, each against its line where the forecast has one, and under the table what the lines mean.
   A forecast is a model's, said so in the head; with no days there is no page. `tz` words the day in the node's zone. */
const WDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const fcDay = iso => { const [y, m, d] = String(iso).split('-').map(Number); return `${WDAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()]} ${d} ${MONTHS[m - 1].slice(0, 3)}`; };
function forecastPage(F) {
  const days = ((F && F.days) || []).filter(d => d && d.rows && Object.keys(d.rows).length);
  if (!days.length) return null;
  const n = v => (v == null ? null : Number(v)), over = (r, txt) => (r && r.hours_over ? `<small>${esc(txt(r))}</small>` : '');
  const cell = (v, unit, extra) => (v == null ? '<span class="fine">not held</span>' : `<b>${esc(v)}</b> ${esc(unit)}${extra || ''}`);
  const rows = days.map(d => { const a = d.rows.air, h = d.rows.heat, w = d.rows.wind_rain, s = d.rows.sea;
    return `<tr><td>${esc(fcDay(d.date))}${d.part === 'rest' ? '<small>the rest of today</small>' : ''}</td>`
      + `<td>${cell(a && n(a.peak != null ? a.peak : a.value), 'µg/m³', over(a, r => `${r.hours_over} h over ${r.line}`))}</td>`
      + `<td>${cell(h && n(h.value), '°C', over(h, r => `${r.hours_over} h over ${r.line}`))}</td>`
      + `<td>${cell(w && n(w.rain_mm), 'mm', w && w.rain_hours ? `<small>${esc(w.rain_hours)}</small>` : '')}</td>`
      + `<td>${cell(s && n(s.value), 'm')}</td></tr>`; }).join('');
  const A = days.map(d => d.rows.air).find(Boolean), H = days.map(d => d.rows.heat).find(Boolean);
  const air = days.filter(d => d.rows.air && d.rows.air.hours_over).length, hot = days.filter(d => d.rows.heat && d.rows.heat.hours_over).length;
  const many = (k, of) => (k === 0 ? 'no day' : k === of ? (of === 1 ? 'that day' : 'every day') : `${k} of ${of} days`);
  const notes = [
    A && A.line != null && `Fine dust: the highest hour of each day. The line is ${A.line} µg/m³, the WHO guideline for a day's mean. The forecast puts hours over it on ${many(air, days.filter(d => d.rows.air).length)}.`,
    H && H.line != null && `Heat: the hottest hour as it feels, with humidity counted. ${H.line} °C is the heat line this node is set to. The forecast puts hours over it on ${many(hot, days.filter(d => d.rows.heat).length)}.`,
    days.some(d => d.rows.wind_rain) && 'Rain: the day\'s total and the hours it is expected in.',
    days.some(d => d.rows.sea) && 'Sea: the highest waves of the day at the sea point the forecast reads.',
  ].filter(Boolean).map(t => `<p>${esc(t)}</p>`).join('');
  return `<h3 class="pmh">what is coming</h3><p class="rwho">A forecast from weather and air models for this place, not a measurement. It changes with every run.</p>`
    + `<table class="tbl rfc"><tr><th>day</th><th>fine dust</th><th>heat, as felt</th><th>rain</th><th>sea</th></tr>${rows}</table><div class="rfcn">${notes}</div>`;
}

/* THE REPORT'S PAGES (SPEC_place_report §5), A4 portrait after the sheet: the reading and its avenues (§11), then the place in figures, what the node holds about
   its place, what changed (none without satellite years) and the sources with how to cite. Each has the head line, and
   N counts the pages there. The rows come as the band, the years and the cake make them (doors-place.js reportParts). */
function reportPages(D, r) {
  const h = D.health || {}, row = (...c) => `<tr>${c.map(x => `<td>${x}</td>`).join('')}</tr>`, credits = [...new Set(r.credits)], read = readingPages(D, r.reading);
  const cake = r.cake.map(s => `<tr><th colspan="4">${esc(s.name)}</th></tr>` + (s.rows.length
    ? s.rows.map(x => row(esc(x.name), esc(x.src), x.held, x.fill ? `<code>${esc(x.fill)}</code>` : esc(x.none || ''))).join('') : row('<span class="fine">none yet</span>', '', '', ''))).join('');
  const name = h.place || D.node.name;
  const pages = [
    ...read,
    forecastPage(r.forecast),
    r.figures + (r.index ? `<p class="fine">${esc(r.index.name)} has its own report on the Fab City Index, which says the rest about the city: `
      + `<a href="${esc(r.index.url)}" target="_blank" rel="noopener">${esc(r.index.url)}</a></p>` : ''),
    `<h3 class="pmh">what the node holds about its place</h3><table class="tbl rcake"><tr><th>layer</th><th>source</th><th>held</th><th>to fill it</th></tr>${cake}</table>`,
    r.change,
    `<h3 class="pmh">sources and how to cite</h3>${credits.map(c => `<p>${esc(c)}</p>`).join('')}`
      + (credits.some(c => /OpenStreetMap/.test(c)) ? '<p>A map made from OpenStreetMap is a Produced Work under the ODbL, so it carries the credit and nothing more.</p>' : '')
      + (read.length ? '<p>The avenues follow the Fab City Full Stack: fab.city.</p>' : '')
      + `<h3 class="pmh">to cite this report</h3><p class="mono">${esc(`${name}, Place report, cell ${(h.cell || {}).id}, PLANETAI ${h.version}, made ${r.date}.`)}</p>`,
  ].filter(Boolean);
  return pages.map((b, i) => `<article class="rpage" aria-label="Page ${i + 1} of ${pages.length}"><p class="rhead">${esc(`${name} · Place report · page ${i + 1} of ${pages.length}`)}</p>${b}</article>`).join('');
}

const SHEETS = { gridStep, gridLines, sheetLegend, sheetSVG, sheetHTML, reportPages, readingPages, forecastPage, readingBy, readingFoot };
if (typeof window !== 'undefined') Object.assign(window, SHEETS);
if (typeof module !== 'undefined') module.exports = SHEETS;
