'use strict';
/* PLACE — the geographic context, as a workbench (OneSoil): pick a layer on the left, read the map, read its facts on
   the right. Every layer is real geometry: H3 cells from the node (GET /geo/*), the coast from Natural Earth 1:10m, the plan from
   OpenStreetMap, the stations at their own coordinates, the satellite frames as photographs. */
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
  $('#addimg').onclick = addImage;
  document.querySelectorAll('.pviews button').forEach(b => b.onclick = () => { PVIEW = b.dataset.p; VIEWS.place(); });
  document.querySelector('.bench').dataset.pview = PVIEW;
  if (PVIEW === 'map') placeMap(); else layer();
  reach();
};

/* ADD AN IMAGE — a quiet button beside the views, and a dialog: the file (picked or dropped), what took it, a note,
   who. POST /captures with this screen's token; the map's Images layers and the Data door's list then ask again. */
const IKIND = { phone: 'Phone', camera: 'Fixed camera', microscope: 'Microscope', drone: 'Drone', balloon: 'Balloon or kite' };
function addImage() {
  let who = ''; try { who = localStorage.getItem('planetai_actor') || ''; } catch (e) { /* no storage here */ }
  const dl = $('#imgdlg');
  if (!DOORS_TOKEN()) { dl.innerHTML = `<p>Images answer a screen holding a token only. Unlock this screen under Node to add one.</p><form method="dialog"><button>Close</button></form>`; dl.showModal(); return; }
  dl.innerHTML = `<form id="imgf"><div class="k">Add an image</div><label class="drop" for="imgfile"><input type="file" id="imgfile" accept="image/jpeg,image/png,image/heic,image/heif,image/webp"><span id="imgname">Choose an image, or drop one here</span></label>`
    + `<label>What took it<select id="imgkind">${Object.entries(IKIND).map(([k, t]) => `<option value="${k}">${t}</option>`).join('')}</select></label>`
    + `<label>A note, if it needs one<input id="imgnote" maxlength="500"></label>${who ? '' : '<label>Your name<input id="imgwho" autocomplete="name"></label>'}`
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
    fd.append('note', $('#imgnote').value); fd.append('actor', by);
    btn.disabled = true; out.textContent = 'Sending it to the node…';
    try {
      const r = await fetch('/captures', { method: 'POST', headers: DOORS_AUTH(), body: fd }), b = await r.json().catch(() => ({}));
      if (!r.ok) { out.textContent = b.detail || `the node refused it (${r.status})`; return; }
      dl.close(); if (window.placeImagesChanged) window.placeImagesChanged();
    } catch (x) { out.textContent = `The node did not answer: ${x.message}`; } finally { btn.disabled = false; }
  };
}
