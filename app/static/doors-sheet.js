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
  const made = `Made on PLANETAI ${h.version || ''}, ${c.date || ''} · ${D.node.name}`;
  return `<article class="sheet" aria-label="The sheet"><div class="sin"><div class="smap">${c.img ? sheetSVG(c) : `<p class="snone">${esc(c.none)}</p>`}</div>`
    + `<div class="sleg"><h2>${esc(D.node.name)}</h2><p class="k">Place${c.rung ? ` · ${esc(c.rung)}, res ${esc(c.res)}` : ''}</p>`
    + (c.img ? `<p class="shouse"><span><i></i>This house, drawn as its res-10 cell</span></p>` : '') + leg + (maps ? `<h3>your maps</h3>${maps}` : '')
    + `<div class="sfoot"><p class="mono">${where}</p><p>${[...(c.credits || []), made].map(esc).join(' · ')}</p></div></div></div></article>`;
}

/* THE REPORT'S PAGES (SPEC_place_report §5), A4 portrait after the sheet: the place in figures, what the node holds about
   its place, what changed (none without satellite years) and the sources with how to cite. Each has the head line, and
   N counts the pages there. The rows come as the band, the years and the cake make them (doors-place.js reportParts). */
function reportPages(D, r) {
  const h = D.health || {}, row = (...c) => `<tr>${c.map(x => `<td>${x}</td>`).join('')}</tr>`, credits = [...new Set(r.credits)];
  const cake = r.cake.map(s => `<tr><th colspan="4">${esc(s.name)}</th></tr>` + (s.rows.length
    ? s.rows.map(x => row(esc(x.name), esc(x.src), x.held, x.fill ? `<code>${esc(x.fill)}</code>` : esc(x.none || ''))).join('') : row('<span class="fine">none yet</span>', '', '', ''))).join('');
  const pages = [
    r.figures + (r.index ? `<p class="fine">${esc(r.index.name)} has its own report on the Fab City Index, which says the rest about the city: `
      + `<a href="${esc(r.index.url)}" target="_blank" rel="noopener">${esc(r.index.url)}</a></p>` : ''),
    `<h3 class="pmh">what the node holds about its place</h3><table class="tbl rcake"><tr><th>layer</th><th>source</th><th>held</th><th>to fill it</th></tr>${cake}</table>`,
    r.change,
    `<h3 class="pmh">sources and how to cite</h3>${credits.map(c => `<p>${esc(c)}</p>`).join('')}`
      + (credits.some(c => /OpenStreetMap/.test(c)) ? '<p>A map made from OpenStreetMap is a Produced Work under the ODbL, so it carries the credit and nothing more.</p>' : '')
      + `<h3 class="pmh">to cite this report</h3><p class="mono">${esc(`${D.node.name}, Place report, cell ${(h.cell || {}).id}, PLANETAI ${h.version}, made ${r.date}.`)}</p>`,
  ].filter(Boolean);
  return pages.map((b, i) => `<article class="rpage" aria-label="Page ${i + 1} of ${pages.length}"><p class="rhead">${esc(`${D.node.name} · Place report · page ${i + 1} of ${pages.length}`)}</p>${b}</article>`).join('');
}

const SHEETS = { gridStep, gridLines, sheetLegend, sheetSVG, sheetHTML, reportPages };
if (typeof window !== 'undefined') Object.assign(window, SHEETS);
if (typeof module !== 'undefined') module.exports = SHEETS;
