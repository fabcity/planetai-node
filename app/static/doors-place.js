'use strict';
/* PLACE — the geographic context, as a workbench (OneSoil): pick a layer on the left, read the map, read its facts on
   the right. Every layer is real geometry: H3 cells from the node (GET /geo/*), the coast from Natural Earth 1:10m, the plan from
   OpenStreetMap, the stations at their own coordinates, the satellite frames as photographs.

   PHASE 4a (Tomas, 14–15 Oct 2026; the review's findings). The plan, in the order a household meets it:
   1. Below the map, the species somebody here confirmed, as a table (never cards): the species with its GBIF link, its
      rank, how many times seen here, where in words ("in the seven cells", "outside"), and GBIF's open records in the
      seven cells. Token only, as /species is; without it one line says where to unlock. On the map, a filled mark at
      each confirming image's point, its layer row saying "1 confirmed · Hibiscus …". GBIF's records are a count, not
      points, so no hollow marks are drawn.
   2. Five layers on (street, the node's cell, own sensors, public stations, images); the other groups collapsed with
      their count; the list never scrolls inside itself; on a phone it opens as a sheet under a "Layers 5" button.
   3. The house is named on the map, as Now's map names it.
   4. No WebGL: the map draws still (the cell, the stations, the rings), and the list and the facts draw as always.
   5. Tools are 44 px, the active one says its word, measuring ends on Done, From the house is one tap.
   6. One fact, one figure: the cell's own edge and its area in km², in the lede and in the facts alike.
   7. Land and Coast ("Changes by the year") sit below the map, after the species. */
const GEO = {};
async function geo(name, url) { return GEO[name] || (GEO[name] = await fetch(url).then(r => r.json())); }
/* Three views of the place: the map (placemap.js, every layer that has a position), and the two that do not —
   the Sentinel frames are photographs not registered to the node's point, and the change is a count, not a shape. */
let PVIEW = 'map', YEAR = 2025, COMPARE = true, PAST = null;   /* From orbit opens as then | now (Tomas, 7 Oct) */
const PVIEWS = [['map', 'Map', 'every layer with a position'], ['orbit', 'From orbit', 'then and now, Sentinel-2'], ['change', 'What changed', 'AlphaEarth, year on year']];
VIEWS.place = function () {
  const h = D.health, area = D.geometry.ladder.find(l => l.res === h.cell.res).own_area_m2 / 1e6;   // the node's own figure for this cell, not the resolution's average
  $('#placehead').innerHTML = `<div class="k">Place · ${said(D.registry.place)}</div>
    <h1 data-learn="1">The ground this node stands on.</h1>
    <p class="lede mono">${esc(h.cell.id)} · res ${h.cell.res} · ${h.cell.edge_m} m edge · ${area.toFixed(2)} km² · ${fmt(D.point[1], 4)}, ${fmt(D.point[0], 4)}</p>
    <div class="prow"><nav class="pviews" aria-label="Views of the place">${PVIEWS.map(([id, t, s]) => `<button class="${id === PVIEW ? 'on' : ''}" data-p="${id}"><b>${t}</b><span>${s}</span></button>`).join('')}</nav>`
    + `<button class="addimg" id="addimg" title="An image this household took: it lands on the map where it was taken">+ Add an image</button></div>`;
  /* the issues that change yearly and have no hours (Land, Coast): Now is for the hour, so they are said here, below
     the ground they describe — the engine's own sentence, the region's figure and its provenance (15 Oct) */
  $('#pyearly').innerHTML = yearly();
  $('#addimg').onclick = addImage;
  $('#lybtn').onclick = () => { const b = document.querySelector('.bench'); b.classList.toggle('sheet'); $('#lybtn').setAttribute('aria-expanded', b.classList.contains('sheet')); };
  speciesBlock();
  document.querySelectorAll('.pviews button').forEach(b => b.onclick = () => { PVIEW = b.dataset.p; VIEWS.place(); });
  document.querySelector('.bench').dataset.pview = PVIEW;
  if (PVIEW === 'map') placeMap(); else layer();
  reach();
};

function yearly() {
  const ks = D.order.filter(k => !ISSUES_DRAWN(k) && ((D.issues[k].stack || {}).region || {}).value != null);
  return ks.length ? `<section class="yearly" data-learn="states" data-reads="/issues" data-stage="observe" data-pack="core" data-kind="row"><h2>Changes by the year</h2>`
    + ks.map(k => { const it = D.issues[k], g = it.stack.region;
      return `<div class="fr" data-k="${k}"><span>${said(it.name)}<small class="said">${esc(it.title || it.sentence || '')}</small></span><b>${num(`${k}.region`, fmt(g.value, 1), 'no line: it informs, it never asks')} ${said(it.unit)} ${prov(g.provenance || 'model')}</b></div>`; }).join('')
    + `</section>` : '';
}
/* SPECIES CONFIRMED HERE (Tomas, 15 Oct: "species list should sit below the map"): /species, one row per taxon a person
   here confirmed, as Data › Images reads it. Where is said from the confirming images' own `outside`, which the node
   measured on arrival against its seven cells. Open records are GBIF's, counted by the node in the same seven cells. */
async function speciesBlock() {
  const el = $('#pspecies');
  const [sp, caps] = await Promise.all(['/species', '/captures?limit=500'].map(u => doorsFetch(u).then(r => (r.ok ? r.json() : null)).catch(() => null)));
  if (!sp) { el.innerHTML = `<h2>Species confirmed here</h2><p class="fine">The species somebody here confirmed in an image answer a screen holding a token, because where a picture was taken is the household’s. Unlock this screen in ${UNLOCK_AT}.</p>`; return; }
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

/* a fact: its name, its figure, where it is from — and, when it has one, its provenance word as the node draws it */
const facts = (rows, note) => rows.map(([t, v, s, w]) => `<div class="fr"><span>${esc(t)}${s ? `<small class="said">${esc(s)}</small>` : ''}</span><b>${esc(v)}${w ? ' ' + prov(w) : ''}</b></div>`).join('') + (note ? `<p class="fine">${note}</p>` : '');
/* counted in the node's own cell sign: filled for the count, faint for the rest, in the satellite's orange (dashboard.js of20) */
const of20 = v => `<span class="signs">${d3.range(20).map(i => sign('sign-cell', i < Math.round(v * 20) ? 'on sat' : 'off sat')).join('')}</span>`;

async function layer() {
  const el = $('#mapalt'); $('#altbar').innerHTML = ''; el.innerHTML = '';
  const LAYER = PVIEW;
  if (!D.earth || !(D.earth.sentinel || []).length && LAYER === 'orbit') {
    el.innerHTML = `<p class="fine">This node holds no satellite frames yet: <code>planetai run earth frames</code> fetches them.</p>`; $('#altfacts').innerHTML = ''; return;
  }
  if (LAYER === 'orbit') {
    /* Then | now: the latest pass on the right, fixed; the past on the left, stepped through the passes the node
       keeps. Single shows one year at a time. The hectares that changed between the two are the node's own count
       (AlphaEarth, GET /earth), drawn only for a pair it computed. */
    const ys = D.earth.sentinel, NOW = ys[ys.length - 1]; if (!ys.includes(YEAR)) YEAR = NOW;
    if (!ys.includes(PAST) || PAST === NOW) PAST = ys[0];
    const past = ys.filter(y => y !== NOW);
    const ch = (D.earth.changes || []).find(c => c.year_a === PAST && c.year_b === NOW)
      || (D.earth.changes || []).find(c => c.year_a <= PAST + 1 && c.year_b === NOW);
    $('#altbar').innerHTML = COMPARE
      ? `<span class="k">then</span><button id="yp" aria-label="Earlier">‹</button><b class="mono">${PAST}</b><button id="yn" aria-label="Later">›</button><span class="k">· now</span><b class="mono">${NOW}</b>`
        + `<label class="cmp"><input type="checkbox" id="cmp" checked> then and now</label>`
      : `<button id="yp" aria-label="Earlier">‹</button><b class="mono">${YEAR}</b><button id="yn" aria-label="Later">›</button><label class="cmp"><input type="checkbox" id="cmp"> then and now</label>`;
    el.innerHTML = COMPARE
      ? `<div class="pair"><figure><img src="${SAT(PAST)}" alt="Sentinel-2, ${PAST}"><figcaption>then · ${PAST}</figcaption></figure><figure><img src="${SAT(NOW)}" alt="Sentinel-2, ${NOW}"><figcaption>now · ${NOW}</figcaption></figure></div>`
        + (ch ? `<div class="pairnote">${ch.year_a} → ${ch.year_b}: ${num('earth.change.pair', ch.hectares_over_threshold.toFixed(1), `pixels past the change threshold ${ch.threshold}, of ${ch.pixels.toLocaleString('en')}`)} ha changed, ${(ch.share_over_threshold * 100).toFixed(1)} % of the ground, by the node’s AlphaEarth record ${prov('model')}</div>` : '')
      : `<img class="photo" src="${SAT(YEAR)}" alt="Sentinel-2 annual median, ${YEAR}, about 3 km across">`;
    const step = d => { if (COMPARE) PAST = past[Math.max(0, Math.min(past.length - 1, past.indexOf(PAST) + d))]; else YEAR = ys[Math.max(0, Math.min(ys.length - 1, ys.indexOf(YEAR) + d))]; layer(); };
    $('#yp').onclick = () => step(-1); $('#yn').onclick = () => step(1); $('#cmp').onchange = e => { COMPARE = e.target.checked; layer(); };
    $('#altfacts').innerHTML = facts([['Passes kept', ys.join(' · '), 'Sentinel-2 annual medians'], ['Landsat passes', D.earth.landsat.join(' · ')], ['Across', 'about 3 km'], ['Brightness', 'matched across years']],
      `${D.earth.credit.map(esc).join(' ')} Only the structure differs between years. The photograph is not registered to the node’s point, so nothing is drawn over it.`);
  }

  if (LAYER === 'change') {
    const E = D.earth, all = E.changes || [], ch = all.filter(c => c.year_b - c.year_a === 1).sort((a, b) => a.year_a - b.year_a), span = all.find(c => c.year_b - c.year_a > 1);
    const row = (c, t, cls = '') => `<div class="lrow ${cls}"><span class="t">${t}<small>${(c.share_over_threshold * 100).toFixed(2)} % of pixels</small></span>`
      + `<span class="signs">${d3.range(Math.round(c.hectares_over_threshold / 10)).map(() => sign('sign-cell', 'on sat')).join('')}</span><span class="c">${num('earth.change.' + c.year_b, c.hectares_over_threshold.toFixed(1), `pixels that moved more than ${D.earth.change.threshold}`)} ha</span></div>`;
    el.innerHTML = `<div class="chg"><div class="k">Hectares that changed, one square per 10 ha</div>${ch.map(c => row(c, `${c.year_a} → ${c.year_b}`)).join('')}${span ? row(span, `${span.year_a} → ${span.year_b}`, 'span') : ''}</div>`;
    const O = Object.fromEntries(D.observations.filter(o => o.sensor_id === 'ee-point').map(o => [o.metric, o.value]));
    $('#altfacts').innerHTML = `<div class="k">What the ground is made of, within 1 km</div>`
      + [['built', O.built_frac], ['trees', O.tree_frac], ['crops', O.crop_frac], ['water', O.water_frac]].filter(([, v]) => v != null)
        .map(([t, v]) => `<div class="fr col"><span>${t} <small>twentieths of the ground</small></span>${of20(v)}<b>${fmt(v * 100, 0)} % ${prov('model')}</b></div>`).join('')
      + facts([['Vegetation (NDVI median)', fmt(O.ndvi_median, 2)], ['Night lights', fmt(O.night_lights, 1), 'VIIRS radiance'], ['Changed when it moved more than', `${E.change.threshold}`, `AlphaEarth, ${E.change.metres_per_pixel} m pixels, ${E.radius_m * 2 / 1000} km square`]],
        'Orange is what only the satellite knows, and nothing else on this door is orange. Every figure here is a model’s description of the ground, never a reading.');
  }

}

function reach() {
  const R = D.reach || [], max = d3.max(R, r => r.days) || 1, word = { map: 'The satellite', model: 'Models read for this point', sensor: 'The kit in and around this house' };
  $('#reach').innerHTML = R.map(r => `<div class="lrow"><span class="t">${word[r.kind] || r.kind}<small>${r.sources} source${r.sources === 1 ? '' : 's'} · ${r.buckets.toLocaleString('en')} hours</small></span>`
    + `<span class="bar"><i style="width:${Math.max(.5, r.days / max * 100)}%"></i></span><span class="c">${r.days >= 730 ? fmt(r.days / 365.25, 1) + ' yr' : r.days + ' d'}</span></div>`).join('')
    + `<p class="fine">From ${dLabel(dayOf(R[0].oldest))} ${R[0].oldest.slice(0, 4)} for the satellite; the kit started on ${dLabel(dayOf(R[2].oldest))}.</p>`;
  $('#soon').innerHTML = [['Production and trade', 'what this place makes and what it brings in, by category, for the Fab City Index', 'open sources named, no adapter yet'],
    ['Index cells', 'the 20 cells of the Fab City Index for this place, scored where data exists', `${new Set(D.index_cells.map(c => c.cell)).size} of 20 have a value`],
    ['Water and soil', 'the other two things the purpose names, beside air', 'no source yet'], ['Forecast', 'the next day of wind and rain, from BMKG for this village', 'needs this point’s village code']]
    .map(([t, s2, c]) => `<div class="lrow two"><span class="t">${t}</span><span class="s">${s2}<br><span class="soon">${c}</span></span></div>`).join('');
}

/* ADD AN IMAGE — a quiet button beside the views, and a dialog: the file (picked or dropped), what took it, a note,
   who. POST /captures with this screen's token; the map's Images layers and the Data door's list then ask again. */
const IKIND = { phone: 'Phone', camera: 'Fixed camera', microscope: 'Microscope', drone: 'Drone', balloon: 'Balloon or kite' };
function addImage() {
  let who = ''; try { who = localStorage.getItem('planetai_actor') || ''; } catch (e) { /* no storage here */ }
  const dl = $('#imgdlg');
  if (!DOORS_TOKEN()) { dl.innerHTML = `<p>Images answer a screen holding a token only. Unlock this screen in Set up › This screen to add one.</p><form method="dialog"><button>Close</button></form>`; dl.showModal(); return; }
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
    btn.disabled = true; out.textContent = 'Sending it to the node…';
    try {
      const r = await fetch('/captures', { method: 'POST', headers: DOORS_AUTH(), body: fd }), b = await r.json().catch(() => ({}));
      if (!r.ok) { out.textContent = b.detail || `the node refused it (${r.status})`; return; }
      if (b.describing) setTimeout(() => window.placeImagesChanged && window.placeImagesChanged(), 40000);   // its description, once the model is done
      dl.close(); if (window.placeImagesChanged) window.placeImagesChanged();
    } catch (x) { out.textContent = `The node did not answer: ${x.message}`; } finally { btn.disabled = false; }
  };
}
