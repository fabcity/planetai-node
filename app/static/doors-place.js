'use strict';
/* PLACE — the ground around the house, as a small GIS (SPEC_place_microgis §4, the v2 drawing of 4 Nov 2026): the cake
   on the left (doors-placemap.js panel(), doors-cake.js), the screen in the middle, black in both registers, with its
   tools, scales and hour on it, the tool column on the right, and a lower band: what is selected or returned, and the
   place in figures. One map: the satellite is its base where the node holds it, and the then and now sits in the lower
   band under "what changed, year on year". Every layer is real geometry: H3 cells from the node (GET /geo/*), the plan
   from OpenStreetMap, the stations at their own coordinates, the satellite frames as photographs.

   Kept from PHASE 4a (14–15 Oct): the species as a table (never cards), token only, with GBIF's open records counted
   and never drawn; five layers on; no WebGL draws the map still; 44 px tools, Done ends measuring, From the house is
   one tap; the cell's own edge and area in km², once. */
const GEO = {};
async function geo(name, url) { return GEO[name] || (GEO[name] = await fetch(url).then(r => r.json())); }
let YEAR = 2025, COMPARE = true, PAST = null;   /* the satellite opens as then | now (Tomas, 7 Oct) */
VIEWS.place = function () {
  const h = D.health, area = D.geometry.ladder.find(l => l.res === h.cell.res).own_area_m2 / 1e6;   // the node's own figure for this cell, not the resolution's average
  $('#placehead').innerHTML = `<div class="k">Place · ${said(D.registry.place)}</div>
    <h1>The ground around the house</h1>
    <p class="lede mono">${esc(h.cell.id)} · res ${h.cell.res} · ${h.cell.edge_m} m edge · ${area.toFixed(2)} km²${DOORS_TOKEN() ? ` · ${fmt(D.point[1], 3)}, ${fmt(D.point[0], 3)}` : ''}</p>`;
  $('#paddimg').innerHTML = DOORS_TOKEN() ? `<button class="addimg" id="addimg" data-learn="place-image" data-reads="/captures" data-stage="observe" data-pack="core" title="An image this household took: it lands on the map where it was taken">+ Add an image</button>` : '';
  /* the Ask line opens the node's own Ask pane with its question: one place to ask, whichever door it was typed on.
     UI_ASK off is the keeper's switch for every ask, so the line is not drawn at all. */
  $('#pask').hidden = !!D.askOff;
  $('#pask').onsubmit = e => {
    e.preventDefault(); const q = $('#paskq').value.trim();
    if (D.askOff) return;
    if ($('#askpane').hidden) $('#askbtn').click();
    if (q) { $('#q').value = q; $('#paskq').value = ''; $('#qform').requestSubmit(); }
  };
  if ($('#addimg')) $('#addimg').onclick = () => addImage();
  /* a phone: the cake and the tools are two disclosures under the screen */
  document.querySelectorAll('.psbar button').forEach(b => b.onclick = () => {
    const bench = document.querySelector('.bench'), open = bench.dataset.sheet === b.dataset.s ? '' : b.dataset.s;
    bench.dataset.sheet = open; document.querySelectorAll('.psbar button').forEach(x => x.setAttribute('aria-expanded', String(x.dataset.s === open)));
  });
  speciesBlock(); placeTools(); figures(); placeMap(); layer();
};
/* FOLDING (SPEC_place_microgis §4): each side folds to a 36 px strip with its name down it, and a press on the strip
   opens it again; Map only folds both, and the screen takes the window's height (doors.html); Full screen is the
   browser's own, on the screen, so the keys, the readout and the controls come along. Each side is remembered in this
   browser, read and written in try/catch: without storage the page opens unfolded and folds all the same. */
const PLACE_FOLDS = 'planetai_place_folds', placeBench = () => document.querySelector('.bench');
function foldSide(sides, on) {
  const b = placeBench(); if (!b) return;
  sides.split(' ').forEach(f => b.classList.toggle(f, on));
  try { localStorage.setItem(PLACE_FOLDS, ['lc', 'rc'].filter(f => b.classList.contains(f)).join(' ')); } catch (e) { /* no storage here */ }
  sayFolds();
}
/* the arrows and Map only say what a press does next; the map takes its new size (a still map is drawn again) */
function sayFolds() {
  const b = placeBench(), PM = window.__PM || {};
  document.querySelectorAll('.pfold').forEach(x => {
    const hid = b.classList.contains(x.dataset.fold), say = `${hid ? 'Show' : 'Hide'} the ${x.dataset.fold === 'lc' ? 'layers' : 'tools'}`;
    x.setAttribute('aria-expanded', String(!hid)); x.setAttribute('aria-label', say); x.title = `${say} · ${x.dataset.fold === 'lc' ? '[' : ']'}`;
  });
  const w = document.querySelector('.tools [data-t="wide"]'); if (w) w.setAttribute('aria-pressed', String(b.classList.contains('lc') && b.classList.contains('rc')));
  if (PM.map) PM.map.resize(); else if (PM.flat && window.placeMap) window.placeMap();
}
/* Map only: both fold, and the whole screen comes into the window; pressed again, both open */
function mapOnly() {
  const b = placeBench(), both = b.classList.contains('lc') && b.classList.contains('rc');
  foldSide('lc rc', !both); if (!both) document.querySelector('.mapc').scrollIntoView({ block: 'center' });
}
function fullScreen() {
  const sc = document.querySelector('.mapc'); if (!document.fullscreenEnabled || !sc) return;
  if (document.fullscreenElement) document.exitFullscreen(); else sc.requestFullscreen();
}
window.placeWide = mapOnly; window.placeFull = fullScreen;
{ let s = ''; try { s = localStorage.getItem(PLACE_FOLDS) || ''; } catch (e) { /* no storage here */ }
  const b = placeBench();
  if (b) { s.split(' ').filter(f => f === 'lc' || f === 'rc').forEach(f => b.classList.add(f)); sayFolds(); }
  document.querySelectorAll('.pfold').forEach(x => { x.onclick = () => foldSide(x.dataset.fold, !placeBench().classList.contains(x.dataset.fold)); }); }
document.addEventListener('fullscreenchange', () => {
  const x = document.querySelector('.tools [data-t="full"]'), PM = window.__PM || {};
  if (x) x.setAttribute('aria-pressed', String(!!document.fullscreenElement));
  if (PM.map) PM.map.resize();
});

/* `/` puts the cursor in the Ask line, on Place; `[` and `]` fold a side, `\` is Map only, F full screen. None while
   somebody types, in a dialog or in the download menu: onKey's guard (doors-placemap.js). Esc closes a phone's sheet. */
const closeSheet = () => { const b = placeBench(); if (b && b.dataset.sheet) document.querySelector(`.psbar [data-s="${b.dataset.sheet}"]`).click(); };
$('#askbtn').addEventListener('click', closeSheet);   /* the sheet sits above the Ask pane: Ask opens, the sheet closes */
document.addEventListener('keydown', e => {
  const b = placeBench(), k = e.key;
  if (k === 'Escape' && b && b.dataset.sheet) { closeSheet(); return; }
  if (view() !== 'place' || e.metaKey || e.ctrlKey || e.altKey || e.target.closest('input, textarea, select, [contenteditable], dialog, .dlmenu')) return;
  if (k === '[' || k === ']') { const f = k === '[' ? 'lc' : 'rc'; foldSide(f, !b.classList.contains(f)); return; }
  if (k === '\\') { mapOnly(); return; }
  if (k === 'f' || k === 'F') { fullScreen(); return; }
  if (k !== '/' || D.askOff) return;
  e.preventDefault(); $('#paskq').focus();
});

function yearly() {
  const ks = D.order.filter(k => !ISSUES_DRAWN(k) && ((D.issues[k].stack || {}).region || {}).value != null);
  return ks.map(k => { const it = D.issues[k], g = it.stack.region;
      return `<div class="fr" data-k="${k}"><span>${said(it.name)}<small class="said">${esc(it.title || it.sentence || '')}</small></span><b><span class="${k === 'land' ? 'sat' : ''}">${num(`${k}.region`, fmt(g.value, 1), 'no line: it informs, it never asks')} ${said(it.unit)}</span> ${prov(g.provenance || 'model')}${g.age_minutes != null ? ` <small class="mono">${esc(wdhm(new Date(Date.parse(D.as_of) - g.age_minutes * 6e4).toISOString()))}</small>` : ''}</b></div>`; }).join('');
}
/* SPECIES CONFIRMED HERE (Tomas, 15 Oct; under the cake's species row since 4 Nov): /species, one row per taxon a person
   here confirmed, as Data › Images reads it. Where is said from the confirming images' own `outside`, which the node
   measured on arrival against its seven cells. Open records are GBIF's, counted by the node in the same seven cells. */
async function speciesBlock() {
  const el = $('#pspecies');
  const [sp, caps] = await Promise.all(['/species', '/captures?limit=500'].map(u => doorsFetch(u).then(r => (r.ok ? r.json() : null)).catch(() => null)));
  if (!sp) { el.innerHTML = `<h2>Species confirmed here</h2><p class="fine">The species somebody here confirmed stay private to this house, because where a picture was taken is the household’s. Unlock this screen in ${UNLOCK_AT} to see them.</p>`; return; }
  const S = sp.species || [];
  if (!S.length) { el.innerHTML = `<h2>Species confirmed here</h2><p class="fine">None yet. Add an image above the map; once somebody here confirms what it shows in <a href="#data/d-images">Data › Images</a>, it is counted here.</p>`; return; }
  const mine = x => f => f.taxon && x.key ? f.taxon.key === x.key : (f.scientific || (f.taxon || {}).name) === x.name;
  const where = x => {
    const cs = (caps || []).filter(c => c.analysis && c.analysis.confirmed_by && (c.analysis.findings || []).some(mine(x)));
    const out = cs.filter(c => c.outside).length, inn = cs.length - out;
    return !cs.length ? '—' : !out ? 'in the seven cells' : !inn ? 'outside the seven cells' : `${inn} in the seven cells, ${out} outside`;
  };
  const others = x => x.others > 0 ? `${+x.others} in the seven cells` : x.others === 0 ? 'none yet' : '—';
  el.innerHTML = `<h2>Species confirmed here, ${num('place.species', S.length, 'taxa a person here confirmed in an image')}</h2>`
    + `<div class="tscroll"><table class="tbl species"><tr><th>species</th><th class="hide">rank</th><th class="n">seen here</th><th>where</th><th>open records nearby</th></tr>`
    + S.map(x => `<tr><td>${x.key ? `<a href="https://www.gbif.org/species/${+x.key}" target="_blank" rel="noopener">${esc(x.name)}</a>` : esc(x.name)}`
      + `${x.introduced ? `<br><small class="fine">${esc(x.introduced)} in ${esc(x.where)}</small>` : ''}</td>`
      + `<td class="hide">${esc((x.rank || '—').toLowerCase())}</td><td class="n">${+x.count}</td><td>${where(x)}</td><td>${others(x)}</td></tr>`).join('')
    + `</table></div><p class="fine">Only what somebody here confirmed counts: the image model’s guesses do not. Seen here counts every confirmed one, in ${S.reduce((a, x) => a + x.images, 0)} image${S.reduce((a, x) => a + x.images, 0) === 1 ? '' : 's'}; open records are GBIF’s, by others, in this node’s seven cells.</p>`;
}

/* WHAT CHANGED, YEAR ON YEAR, the lower band's right (SPEC_place_microgis §4; over the satellite on the screen until
   4 Nov). The latest pass on the right, fixed; the past on the left, stepped through the passes the node keeps. Single
   shows one year at a time. The hectares that changed between the two are the node's own count (AlphaEarth, GET /earth),
   drawn only for a pair it computed. Under them the buildings the satellite counts round the node, a bar a year (the
   place pack's Open Buildings series, GET /history). The photographs are not registered to the node's point, so they
   sit beside the map, never on it. */
function layer() {
  const el = $('#pchange'), ys = (D.earth || {}).sentinel || [], Y = D.place_yearly || [];
  let h = `<h3 class="pmh">what changed, year on year <b>Sentinel-2 · AlphaEarth</b></h3>`;
  if (!ys.length && !Y.length) { el.innerHTML = h + '<p class="fine">This node holds no satellite years yet.</p>'; return; }
  if (ys.length) {
    const NOW = ys[ys.length - 1]; if (!ys.includes(YEAR)) YEAR = NOW;
    if (!ys.includes(PAST) || PAST === NOW) PAST = ys[0];
    const ch = (D.earth.changes || []).find(c => c.year_a === PAST && c.year_b === NOW)
      || (D.earth.changes || []).find(c => c.year_a <= PAST + 1 && c.year_b === NOW);
    h += `<div id="altbar">` + (COMPARE
      ? `<span class="k">then</span><button id="yp" aria-label="Earlier">‹</button><b class="mono">${PAST}</b><button id="yn" aria-label="Later">›</button><span class="k">· now</span><b class="mono">${NOW}</b>`
        + `<label class="cmp"><input type="checkbox" id="cmp" checked> then and now</label>`
      : `<button id="yp" aria-label="Earlier">‹</button><b class="mono">${YEAR}</b><button id="yn" aria-label="Later">›</button><label class="cmp"><input type="checkbox" id="cmp"> then and now</label>`) + '</div>'
      + (COMPARE
        ? `<div class="pair"><figure><img src="${SAT(PAST)}" alt="Sentinel-2, ${PAST}"><figcaption>then · ${PAST}</figcaption></figure><figure><img src="${SAT(NOW)}" alt="Sentinel-2, ${NOW}"><figcaption>now · ${NOW}</figcaption></figure></div>`
          + (ch ? `<div class="pairnote">${ch.year_a} → ${ch.year_b}: ${num('earth.change.pair', ch.hectares_over_threshold.toFixed(1), `pixels past the change threshold ${ch.threshold}, of ${ch.pixels.toLocaleString('en')}`)} ha changed, ${(ch.share_over_threshold * 100).toFixed(1)} % of the ground, by the node’s AlphaEarth record ${prov('model')}</div>` : '')
        : `<img class="photo" src="${SAT(YEAR)}" alt="Sentinel-2 annual median, ${YEAR}, about 3 km across">`)
      + `<p class="pairnote fine">${D.earth.credit.map(esc).join(' ')} About 3 km across, not registered to the node’s point.</p>`;
  }
  if (Y.length) {
    const top = Math.max(...Y.map(r => r.value)) || 1, a = Y[0], z = Y[Y.length - 1];
    h += `<div class="fr"><span>Buildings the satellite counts<small>Open Buildings, around the node, a bar for each year</small></span>`
      + `<b>${num('place.buildings.yearly', `${Math.round(a.value)} → ${Math.round(z.value)}`, `the satellite’s count in ${a.year} against ${z.year}`)} ${prov('model')}</b></div>`
      + `<div class="years" style="grid-template-columns:repeat(${Y.length},1fr)">${Y.map(r => `<i style="height:${Math.max(1, Math.round(48 * r.value / top))}px" title="${r.year}: ${Math.round(r.value)}"></i>`).join('')}</div>`
      + `<div class="yl" style="grid-template-columns:repeat(${Y.length},1fr)">${Y.map(r => `<span>${r.year}</span>`).join('')}</div>`;
  }
  el.innerHTML = h;
  if (!ys.length) return;
  const NOW = ys[ys.length - 1], past = ys.filter(y => y !== NOW);
  const step = d => { if (COMPARE) PAST = past[Math.max(0, Math.min(past.length - 1, past.indexOf(PAST) + d))]; else YEAR = ys[Math.max(0, Math.min(ys.length - 1, ys.indexOf(YEAR) + d))]; layer(); };
  $('#yp').onclick = () => step(-1); $('#yn').onclick = () => step(1); $('#cmp').onchange = e => { COMPARE = e.target.checked; layer(); };
}

/* THE TOOLS, the right-hand column (SPEC_place_microgis §6): the ones that run today, and the analyses and fitness tools
   the spec names, each with a dotted "not yet" until the place pack computes it. A tool that runs is a row that shows
   its command id; the chosen one is filled. Rings ask GET /geo/rings, which answers a token only. From the house is a
   tool of the screen (doors-placemap.js PM.setTool): the node measures the next press from its own point. */
const TOOLS = [
  ['tools', [['Rings and distance', 'geo.rings', 'rings'], ['From the house', 'geo.measure', null, 'from'], ['Sun and shade', 'place.sun'], ['Trees, 3-30-300', 'place.trees'], ['Built form', 'place.built'],
    ['Sealed ground', 'place.sealed'], ['Streets', 'place.streets'], ['Walk to', 'place.walk'], ['What changed', 'place.changed'], ['Where the rain goes', 'water.runoff']]],
  ['fitness', [['One more tree', 'fit.tree'], ['A roof for a panel', 'fit.roof'], ['A garden bed', 'fit.grow'], ['Catching rain', 'fit.rain']]],
];
function placeTools() {
  const PM = window.__PM || { on: {} }, on = PM.on, tok = !!DOORS_TOKEN(), a = document.activeElement;
  const keep = a && a.closest && a.closest('#ptools') && (a.dataset.layer || a.dataset.tool);   // a press from here keeps its focus through the redraw
  const btn = (n, id, attr, pressed) => `<button class="tl${pressed ? ' on' : ''}" aria-pressed="${pressed}" ${attr}${tok ? '' : ' disabled'}><span>${n}</span><code>${id}</code></button>`;
  $('#ptools').innerHTML = TOOLS.map(([h, ts]) => `<h3 class="pmh">${h}</h3>` + ts.map(([n, id, l, t]) => l ? btn(n, id, `data-layer="${l}"`, !!on[l])
    : t ? btn(n, id, `data-tool="${t}"`, PM.tool === t)
    : `<div class="tl soon" title="${id}"><span>${n}</span><code>not yet</code></div>`).join('')).join('')
    + (tok ? '' : `<p class="fine">Tools run on this node with a token. Unlock this screen in Set up.</p>`);
  document.querySelectorAll('#ptools button[data-layer]').forEach(b => b.onclick = () => window.placeLayer(b.dataset.layer, !on[b.dataset.layer]));
  document.querySelectorAll('#ptools button[data-tool]').forEach(b => b.onclick = () => PM.setTool && PM.setTool(PM.tool === b.dataset.tool ? 'select' : b.dataset.tool));
  const b = keep && document.querySelector(`#ptools [data-layer="${keep}"], #ptools [data-tool="${keep}"]`); if (b) b.focus();
}
window.placeTools = placeTools;

/* THE PLACE IN FIGURES, the lower band's right: the issues that change yearly and have no hours (Land, Coast; Now is for
   the hour), the Index cells, and what is not here yet. */
function figures() {
  const ch = ((D.earth || {}).changes || []).slice(-1)[0], nI = new Set(D.index_cells.map(c => c.cell)).size;
  $('#pfigures').innerHTML = `<h3 class="pmh">the place in figures</h3>` + yearly()
    + `<div class="fr"><span>Index cells<small>of the Fab City Index for this place · <a href="#node/cells">Node › Index cells</a></small></span>`
    + `<b>${num('place.index', `${nI} of 20`, 'cells of the Fab City Index holding a value')} ${prov('partial')}</b></div>`
    + `<div class="fr"><span>Production and trade · Water and soil · Forecast<small>coming to this place: no adapter, no source, or no village code yet</small></span><b><span class="soon">not yet</span></b></div>`
    + (ch ? `<p class="fine">Land: AlphaEarth, ${ch.year_a} → ${ch.year_b}.</p>` : '');
}

/* ADD AN IMAGE — a quiet button in the header, and a dialog: the file (picked or dropped), what took it, a note,
   who. POST /captures with this screen's token; the map's Images layers and the Data door's list then ask again.
   The image key on the screen opens the same dialog for a drawing (`to`: its point, and what to do with the picture). */
const IKIND = { phone: 'Phone', camera: 'Fixed camera', microscope: 'Microscope', drone: 'Drone', balloon: 'Balloon or kite' };
function addImage(to) {
  let who = ''; try { who = localStorage.getItem('planetai_actor') || ''; } catch (e) { /* no storage here */ }
  const dl = $('#imgdlg');
  if (!DOORS_TOKEN()) { dl.innerHTML = `<p>Images stay private to this house. Unlock this screen in Set up › This screen to see or add them.</p><form method="dialog"><button>Close</button></form>`; dl.showModal(); return; }
  dl.innerHTML = `<form id="imgf"><div class="k">Add an image</div><label class="drop" for="imgfile"><input type="file" id="imgfile" accept="image/jpeg,image/png,image/heic,image/heif,image/webp"><span id="imgname">Choose an image, or drop one here</span></label>`
    + `<label>What took it<select id="imgkind">${Object.entries(IKIND).map(([k, t]) => `<option value="${k}">${t}</option>`).join('')}</select></label>`
    + `<label>A note, if it needs one<input id="imgnote" maxlength="500"></label>${who ? '' : '<label>Your name<input id="imgwho" autocomplete="name"></label>'}`
    + `<label class="tick"><span><input type="checkbox" id="imgseen" checked> Describe it with the image model, on this node</span></label>`
    + `<p class="fine">Its own GPS is where it was taken, else the node's cell. The file is cleaned of EXIF and GPS and kept on this node.</p>`
    + `<p class="fine" id="imgout" role="status"></p><div class="acts"><button type="button" id="imgx">Cancel</button><button type="submit">Keep it on the node</button></div></form>`;
  dl.showModal();
  const f = $('#imgf'), out = $('#imgout'), name = () => { const x = $('#imgfile').files[0]; $('#imgname').textContent = x ? x.name : 'Choose an image, or drop one here'; };
  $('#imgx').onclick = () => dl.close(); $('#imgfile').onchange = name;
  f.ondragover = e => { e.preventDefault(); f.classList.add('over'); }; f.ondragleave = () => f.classList.remove('over');
  f.ondrop = e => { e.preventDefault(); f.classList.remove('over'); if (e.dataTransfer.files[0]) { $('#imgfile').files = e.dataTransfer.files; name(); } };
  f.onsubmit = async e => {
    e.preventDefault();
    const file = $('#imgfile').files[0], btn = f.querySelector('button[type=submit]'), by = who || ($('#imgwho') && $('#imgwho').value.trim());
    if (!file) { out.textContent = 'Choose an image first.'; return; }
    if (!by) { out.textContent = 'The node records who added it: your name first.'; return; }
    if (!who) try { localStorage.setItem('planetai_actor', by); } catch (x) { /* no storage here */ }
    const fd = new FormData(); fd.append('photo', file, file.name || 'image.jpg'); fd.append('kind', $('#imgkind').value);
    fd.append('note', $('#imgnote').value); fd.append('actor', by); fd.append('describe', $('#imgseen').checked ? '1' : '');
    if (to && to.at) { fd.append('lon', to.at[0]); fd.append('lat', to.at[1]); }
    btn.disabled = true; out.textContent = 'Sending it to the node…';
    try {
      const r = await fetch('/captures', { method: 'POST', headers: DOORS_AUTH(), body: fd }), b = await r.json().catch(() => ({}));
      if (!r.ok) { out.textContent = b.detail || `the node refused it (${r.status})`; return; }
      if (b.describing) setTimeout(() => window.placeImagesChanged && window.placeImagesChanged(), 40000);   // its description, once the model is done
      dl.close(); if (window.placeImagesChanged) window.placeImagesChanged();
      if (to && to.done && b.capture) to.done(b.capture.id);
    } catch (x) { out.textContent = `The node did not answer: ${x.message}`; } finally { btn.disabled = false; }
  };
}
window.placeAddImage = addImage;
