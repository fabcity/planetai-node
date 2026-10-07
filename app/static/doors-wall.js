'use strict';
/* metres from the node, the node's answer (js/nodegeo.js); a station it has no answer for sorts last */
const mFrom = s => ((D.ngeo && D.ngeo.dist[s.sensor_id]) || { m: Infinity }).m;

/* WALL — the node's wall anatomy (docs/site/wall.md), always dark, one viewport. The back button first in keyboard
   order; the chips; the flow by scale (js/flow.js) with its hour strip; the headline issue with "Answer on Telegram,
   not here." and never a button that answers; the counts; the ρ row counted, never sized; the fragments; the foot.
   R39 placement: bands ruled by hairlines (mono `4b3c372c`); the left column is exactly the drawing's square, its strip
   flush beneath (the HBO Max telemetry bar `c44e6dca`, Windy `b64ab20b`); the right column's first line sits on the
   drawing's top edge and its last on the strip's bottom edge, so the two columns share two lines. */
let WVAR = 'pm25';
VIEWS.wall = function () {
  const k = D.lead, it = D.issues[k], b = D.buckets[D.now];
  const carried = Object.keys(D.metrics).filter(m => Object.values(D.stats15).some(x => x[m] && x[m][0] != null));
  const chips = [WVAR, ...carried.filter(m => m !== WVAR)].slice(0, 4);
  const moving = !CLOCK.reduced() && !!D.raw;   /* the hours replay only from the hourly table, which needs the token */
  const ask = (it.open_asks || []).length ? said(it.open_asks[0].text || '') : `Nothing has been asked.<small>${said(it.name)} is ${esc(it.state)}, and no rule here asks anybody to do anything about it.</small>`;
  $('#wallv').innerHTML = `
    <div class="wtop"><button class="wback" onclick="location.hash='#now'">← back</button>
      <span class="wchips">${chips.map(m => `<button class="${m === WVAR ? 'on' : ''}" data-m="${m}">${said(labelOf(m))}</button>`).join('')}${carried.length > 4 ? `<a href="#data">+${carried.length - 4} more</a>` : ''}</span>
      <span class="k wid">${said(D.registry.name)} · ${said(D.node.place)} · #wall · share level ${esc(D.share || 'off')} · ${moving ? 'the last 6 hours, replayed every 30 s' : 'the last half hour, held still'}</span>
      <span class="k">${said(labelOf(WVAR))} · ${said(unitOf(WVAR))} · 15-min means</span></div>
    <div class="wgrid">
      <section class="wl" data-kind="row"><div id="wfield" role="img" aria-label="The stations around this house on its own map, their readings hour by hour, and the wind now"></div><div id="wtime" class="flowtime"></div></section>
      <section class="wr"><div class="whead">
        <div class="k">${said(it.name)} <span class="state">${esc(it.state)}</span> · ${said(it.reason_text || '')}</div>
        <p class="wsent">${it.pix ? `<svg class="pix" aria-hidden="true"><use href="${NODE}signs.svg#${it.pix}"/></svg>` : ''}<span class="said">${esc(it.sentence).replace(/(\d+(?:\.\d+)?)(?=\s*(?:°C|µg|%|m\b))/, m0 => num(`${k}.${it.hero_distance}`, m0, `against the line, ${it.line} ${it.unit}`, `<b class="numf">${m0}</b>`))}</span></p>
        <p class="wwhy said">${esc(it.plain || '')}</p>
        <div class="wask">${ask}<b>Answer on Telegram, not here.</b></div></div>
        <div class="wcount"><div class="wflow" id="wside"></div>
        <div class="wrho" id="wrho" data-kind="row"></div></div>
      </section>
    </div>
    <div class="wfrag" id="wfrag"></div>
    <div class="wfoot k">Read at ${new Intl.DateTimeFormat('en-GB', { timeZone: D.tz, hour: '2-digit', minute: '2-digit' }).format(new Date(D.as_of))} · planetai-node ${esc(D.health.version)} · <b>stale</b> · ${moving ? 'a disc is a station’s hourly mean; the window replays every 30 s · press an hour to go to it' : 'reduced motion: nothing moves; press an hour to go to it'}</div>`;
  document.querySelectorAll('.wchips button').forEach(c => c.onclick = () => { WVAR = c.dataset.m; VIEWS.wall(); });
  rhoRow(); frags();
  // the drawing's square sets the left column: the main band's height less the strip, never more than 46% of the width
  const g = $('.wgrid'), S = Math.floor(Math.min(g.clientHeight - 76, g.clientWidth * .46));
  g.style.setProperty('--ws', S + 'px');
  wallMap({ el: $('#wfield'), side: $('#wside'), time: $('#wtime'), size: S });
};
/* The ρ row: counted, never sized. One ring per alert up to 40, one per 10 up to 400, then one per 100; the caption
   names the unit and gives the exact counts. Closed rings are the answered ones, first. */
function rhoRow() {
  const r = D.rho, n = r.alerts_act, unit = n <= 40 ? 1 : n <= 400 ? 10 : 100, rings = Math.ceil(n / unit), closed = Math.round(r.acted / unit);
  $('#wrho').innerHTML = `<span class="rings">${d3.range(rings).map(i => sign(i < closed ? 'sign-rho-closed' : 'sign-rho-open', i < closed ? 'closed' : '')).join('')}</span>`
    + `<small>${num('rho.acted', r.acted, `of ${n} act-level alerts, ${r.window_days} days`)} of ${n} alerts answered · one ring per ${unit === 1 ? 'alert' : unit} · half within ${r.median_minutes} min</small>`;
}
/* The fragments each section gives the wall: the first five, then "+N more in Now". Here, every station's last 15 minutes. */
function frags() {
  const st = D.sensors.filter(s => s.kind === 'sensor').map(s => ({ ...s, v: ((D.stats15[s.sensor_id] || {})[WVAR] || [])[0] })).filter(s => s.v != null)
    .sort((a, b) => (b.local - a.local) || (mFrom(a) - mFrom(b)));   // nearest first, by the node's own metres
  $('#wfrag').innerHTML = st.slice(0, 5).map(s => `<div><span class="said">${esc(plain(s.name))}</span>${num(s.sensor_id + '.' + WVAR, fmt(s.v, 1), WVAR === 'pm25' ? `the line ${D.issues.air.line}` : 'no line', `<b>${fmt(s.v, 1)}</b>`)}<small class="said">${esc(unitOf(WVAR))} · ${s.local ? (s.indoor ? 'this house, inside' : 'this house') : 'public'}</small></div>`).join('')
    + (st.length > 5 ? `<a href="#now" class="more">+${st.length - 5} more in Now</a>` : '');
}
