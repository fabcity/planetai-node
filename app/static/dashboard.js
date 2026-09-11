/* The node dashboard. A renderer, and nothing else.
 *
 * The node computes; this file draws. Everything on the page — which issue leads, what state it is
 * in and why, the same quantity at four distances, the line and where it came from, the sentence in
 * the household's own language — arrives from GET /issues already worked out. There is no mean, no
 * median, no apparent temperature and no threshold in this file. If you find yourself needing one,
 * it belongs in app/issues/engine.py, and tools/check_ui.py will fail the page if you put it here.
 *
 * The contract, in the order it runs, with these names so the gates can find them:
 *
 *   snapshot()            the ONLY place that fetches STATE. Returns one object, or one marked
 *                         `refused`. One thing is fetched outside it and it is bytes rather than
 *                         state: the satellite frames, by frameSrc(), once, cached for the life of
 *                         the document. They cannot be an <img src> (the node wants its token and a
 *                         browser will not put a header on an image) and they must never be part of
 *                         a refresh (7 MB against a 60 kB budget, every twenty seconds).
 *   COMPONENTS            pure (data, ctx) => string. No DOM, no fetch, no colour, no exceptions
 *                         escaping. Each returns markup whose root carries data-component="<name>".
 *   ANATOMY               which components make each kind of band. Changing what a band shows is
 *                         editing a list.
 *   layout(snap)          the page order. Arrange edits this and saves it as UI_LAYOUT.
 *   render(snap, view)    the ONLY writer to the DOM.
 *   ctx                   {locale, register, fmt, sign, pill, now, as_of}, built once per render.
 *
 * A seam worth knowing and NOT acting on yet: ANATOMY could move into /issues, so a node could carry
 * what its own bands show. Do not do that now — the page would stop being renderable from a fixture
 * alone, and that is the property that makes a design round possible.
 */
'use strict';

// ---------------------------------------------------------------------------------- what it reads
const QS = new URLSearchParams(location.search);
const FIXTURE = QS.get('fixture');
const ONLY = QS.get('only');
const KIOSK = QS.get('kiosk') === '1';
const LOCALES = ['en', 'id', 'es'];
const DISTANCES = ['room', 'yard', 'ring', 'region'];
// One frame holds for --motion-satellite-year. Read from the layer rather than retyped, so the
// design repo stays the only place that number lives.
const MOTION_YEAR = () => {
  const v = getComputedStyle(document.documentElement).getPropertyValue('--motion-satellite-year').trim();
  const n = parseFloat(v) || 4;
  return /ms$/.test(v) ? n : n * 1000;
};
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;

const tok_ = () => localStorage.getItem('planetai_admin') || localStorage.getItem('planetai_act') || '';
const auth_ = () => (tok_() ? { authorization: 'Bearer ' + tok_() } : {});

// ------------------------------------------------------------------------------------ the fetcher
/* The only function in this file that touches the network.
 *
 * At SHARE_LEVEL=off a reader with no token gets the shell, /health and nothing else — which is a
 * real state a phone on the house WiFi will be in, not an error. It comes back as a snapshot marked
 * `refused` carrying the server's own sentence, and render() draws the shell and that sentence. A
 * blank page would be the node lying about being broken.
 */
async function snapshot() {
  const get = async (path, fallback = null) => {
    try {
      const r = await fetch(path, { headers: auth_() });
      if (r.status === 403) return { __refused: (await r.json().catch(() => ({}))).error || 'refused' };
      if (!r.ok) return fallback;
      return await r.json();
    } catch (e) {
      return fallback;
    }
  };

  if (FIXTURE) {
    const snap = await get('/issues/fixtures/' + encodeURIComponent(FIXTURE));
    if (!snap || snap.__refused) return { refused: (snap && snap.__refused) || 'no such fixture', health: {} };
    return { ...snap, fixture: FIXTURE };
  }

  let placeStatus = 0;
  const place = await fetch('/place/geojson', { headers: auth_() })
    .then(r => { placeStatus = r.status; return r.ok ? r.json() : null; }).catch(() => null);
  const [health, issues, alerts, rho, report, earth, trust, nearby, forecast, sensors, sparks] = await Promise.all([
    get('/health', {}), get('/issues'), get('/alerts?limit=40', []),
    get('/rho', {}), get('/report/latest', {}), get('/earth', {}),
    get('/trust', []), get('/nearby'), get('/forecast'), get('/sensors', []),
    get('/sparks?metric=pm25&hours=24', {}),
  ]);
  const refused = [issues, alerts, rho].map(x => x && x.__refused).find(Boolean);
  if (refused) return { refused, health: health && !health.__refused ? health : {} };
  // The four below are the ported cards' own sources. A refusal on one of them is NOT a refused
  // page — /issues can answer while /sensors does not — so it is turned into an absence and the
  // card that reads it draws the empty state it already has.
  const open_ = v => (v && v.__refused ? null : v);
  return { health, issues, alerts, rho, report, earth, place, placeStatus,
           trust: open_(trust) || [], nearby: open_(nearby), forecast: open_(forecast),
           sensors: open_(sensors) || [], sparks: (open_(sparks) || {}).series || {} };
}

// -------------------------------------------------------------------------------------- the words
/* Everything a person reads that is not a sentence the node wrote. Kept here, keyed by locale, for
 * the same reason the node keeps its own: a string typed inline is a string nobody can translate.
 * The id and es are ASSISTANT-WRITTEN and have not been read by a native speaker — see CHANGELOG.
 */
const WORDS = {
  en: { now: 'Now', watches: 'What this place watches', notWatched: 'not watched here',
        theDay: 'The day it just had', whereItStands: 'Where it stands', sources: 'Sources',
        thePlace: 'The place', theLoop: 'The loop', figures: 'Figures', figure: 'Figure',
        source: 'Source', asOf: 'As of', word: 'Word', answerOn: 'Answer on Telegram, not here.',
        stale: 'stale', didThis: 'I did this', noted: 'noted', theLine: 'the line',
        headlineRule: 'The issue with most to say leads. Ties go to the order this place chose, which is set under Set up → Issues.',
        refused: 'This node is not sharing its readings with the network.',
        trust: {
          title: 'What the node doubts about its own sensors',
          ok: 'Every sensor reported all week.',
          sub: '{n} of {all} sensors need a look.',
          subOk: '{all} local sensors, seven-day coverage.',
          none: 'No local sensor yet.',
          young: 'still gathering its first week',
          cov: '{pct}% of the week',
          frozen: ', {n} frozen channels' },
        ring: {
          title: 'The shape of the ring',
          none: 'No neighbours yet. This node has not fetched the public stations around it, so its readings speak for this address and nothing else. Bali only: set BAD_ENABLED=1.',
          one: 'One neighbour reporting, {km} km away. One is an anecdote: nothing here can tell a fire in the lane from a haze over the island.',
          silent: 'No neighbour is reporting right now, so there is nothing to compare this address against.',
          shape: '{n} neighbours. Lowest {lo}, middle half {p25} to {p75}, highest {hi}, all in {unit}. Nearest {km} km.',
          youAbove: 'You read {v} {unit}, above the middle half of them. Whatever this is, it is closer to you than to them.',
          youBelow: 'You read {v} {unit}, below the middle half of them.',
          youIn: 'You read {v} {unit}, inside the middle half they are reading. Nothing here is unusual to this address.',
          youNone: 'You have no outdoor sensor of your own, so there is nothing to put on this line.',
          tipBox: 'the middle half of your neighbours, {p25} to {p75} {unit}',
          tipSpan: 'the whole ring, {lo} to {hi} {unit}',
          tipYou: 'you, {v} {unit}' },
        stations: {
          title: 'Who is out there, and how far',
          sub: '{n} of {all} stations counted, within {km} km{skipped}. None of them is ours: what this node reads itself is kept out of this list.',
          skipped: ', {n} left out as indoors',
          empty: 'Nothing fetched yet. Once the node polls, every station within {km} km appears here with its distance.',
          row: '{km} km away \u00b7 {net} \u00b7 {when}',
          justNow: 'just now', ago: '{n} min ago', quiet: 'not reporting',
          indoors: 'indoors, not counted', unknownNet: 'unknown network' },
        fc: {
          title: 'The day it is about to have',
          none: 'No forecast yet. Set FORECAST_BMKG_ADM4 to this point\u2019s village code, or turn on Open-Meteo, and the next day of wind and rain appears here. `planetai run forecast verify` finds the code.',
          wind: 'The wind comes from the {dir} at {kmh} km/h.',
          rain: 'Rain expected from {at}, {mm} mm over the day.',
          dry: 'No rain expected in the next day.',
          far: 'The forecast point is {km} km from this node, which is another place.',
          gap: 'The two forecasts differ by up to {c} \u00b0C over the day; neither is the truth.',
          step: 'wind from {dir} {kmh} km/h \u00b7 {sky}',
          stepDry: 'dry', stepRain: '{mm} mm rain', stepCloud: ' \u00b7 {n}% cloud',
          notPredict: 'The node fetches this; it does not predict.' } },
  id: { now: 'Sekarang', watches: 'Yang dipantau di sini', notWatched: 'tidak dipantau di sini',
        theDay: 'Hari yang baru lewat', whereItStands: 'Posisinya', sources: 'Sumber',
        thePlace: 'Tempat', theLoop: 'Lingkar', figures: 'Angka', figure: 'Angka',
        source: 'Sumber', asOf: 'Per', word: 'Kata', answerOn: 'Jawab di Telegram, bukan di sini.',
        stale: 'basi', didThis: 'Saya sudah', noted: 'dicatat', theLine: 'batas',
        headlineRule: 'Isu dengan hal terpenting tampil lebih dulu. Jika seri, urutannya mengikuti pilihan tempat ini, diatur di Set up → Issues.',
        refused: 'Node ini tidak membagikan bacaannya ke jaringan.',
        trust: {
          title: 'Yang diragukan node tentang sensornya sendiri',
          ok: 'Semua sensor melapor sepanjang minggu.',
          sub: '{n} dari {all} sensor perlu diperiksa.',
          subOk: '{all} sensor lokal, cakupan tujuh hari.',
          none: 'Belum ada sensor lokal.',
          young: 'masih mengumpulkan minggu pertamanya',
          cov: '{pct}% dari minggu ini',
          frozen: ', {n} kanal beku' },
        ring: {
          title: 'Bentuk lingkar',
          none: 'Belum ada tetangga. Node ini belum mengambil stasiun publik di sekitarnya, jadi bacaannya hanya berbicara untuk alamat ini. Khusus Bali: setel BAD_ENABLED=1.',
          one: 'Satu tetangga melapor, {km} km jauhnya. Satu itu anekdot: tidak ada di sini yang bisa membedakan kebakaran di gang dari kabut di atas pulau.',
          silent: 'Tidak ada tetangga yang melapor sekarang, jadi tidak ada pembanding untuk alamat ini.',
          shape: '{n} tetangga. Terendah {lo}, setengah tengah {p25} sampai {p75}, tertinggi {hi}, semua dalam {unit}. Terdekat {km} km.',
          youAbove: 'Anda membaca {v} {unit}, di atas setengah tengah mereka. Apa pun ini, sumbernya lebih dekat ke Anda daripada ke mereka.',
          youBelow: 'Anda membaca {v} {unit}, di bawah setengah tengah mereka.',
          youIn: 'Anda membaca {v} {unit}, di dalam setengah tengah yang mereka baca. Tidak ada yang luar biasa di alamat ini.',
          youNone: 'Anda belum punya sensor luar ruangan sendiri, jadi tidak ada yang bisa ditaruh di garis ini.',
          tipBox: 'setengah tengah tetangga Anda, {p25} sampai {p75} {unit}',
          tipSpan: 'seluruh lingkar, {lo} sampai {hi} {unit}',
          tipYou: 'Anda, {v} {unit}' },
        stations: {
          title: 'Siapa di luar sana, dan seberapa jauh',
          sub: '{n} dari {all} stasiun dihitung, dalam {km} km{skipped}. Tidak satu pun milik kita: apa yang dibaca node ini sendiri tidak masuk daftar ini.',
          skipped: ', {n} dikeluarkan karena di dalam ruangan',
          empty: 'Belum ada yang diambil. Begitu node menarik data, setiap stasiun dalam {km} km muncul di sini dengan jaraknya.',
          row: '{km} km jauhnya \u00b7 {net} \u00b7 {when}',
          justNow: 'baru saja', ago: '{n} menit lalu', quiet: 'tidak melapor',
          indoors: 'di dalam ruangan, tidak dihitung', unknownNet: 'jaringan tidak diketahui' },
        fc: {
          title: 'Hari yang akan datang',
          none: 'Belum ada prakiraan. Setel FORECAST_BMKG_ADM4 ke kode desa titik ini, atau nyalakan Open-Meteo, dan sehari angin dan hujan berikutnya muncul di sini. `planetai run forecast verify` mencari kodenya.',
          wind: 'Angin datang dari {dir} pada {kmh} km/jam.',
          rain: 'Hujan diperkirakan mulai {at}, {mm} mm sepanjang hari.',
          dry: 'Tidak ada hujan diperkirakan sehari ke depan.',
          far: 'Titik prakiraan berjarak {km} km dari node ini, yang berarti tempat lain.',
          gap: 'Kedua prakiraan berbeda hingga {c} \u00b0C sepanjang hari; tidak satu pun adalah kebenaran.',
          step: 'angin dari {dir} {kmh} km/jam \u00b7 {sky}',
          stepDry: 'kering', stepRain: 'hujan {mm} mm', stepCloud: ' \u00b7 awan {n}%',
          notPredict: 'Node mengambil data ini; ia tidak meramal.' } },
  es: { now: 'Ahora', watches: 'Lo que vigila este lugar', notWatched: 'no se vigila aquí',
        theDay: 'El día que acaba de pasar', whereItStands: 'Dónde está', sources: 'Fuentes',
        thePlace: 'El lugar', theLoop: 'El bucle', figures: 'Cifras', figure: 'Cifra',
        source: 'Fuente', asOf: 'A las', word: 'Palabra', answerOn: 'Responde en Telegram, no aquí.',
        stale: 'viejo', didThis: 'Hice esto', noted: 'anotado', theLine: 'el límite',
        headlineRule: 'La cuestión con más que decir va primero. Los empates siguen el orden que eligió este lugar, en Set up → Issues.',
        refused: 'Este nodo no comparte sus lecturas con la red.',
        trust: {
          title: 'Lo que el nodo duda de sus propios sensores',
          ok: 'Todos los sensores informaron toda la semana.',
          sub: '{n} de {all} sensores necesitan una revisi\u00f3n.',
          subOk: '{all} sensores locales, cobertura de siete d\u00edas.',
          none: 'Todav\u00eda no hay sensor local.',
          young: 'a\u00fan reuniendo su primera semana',
          cov: '{pct}% de la semana',
          frozen: ', {n} canales congelados' },
        ring: {
          title: 'La forma del anillo',
          none: 'A\u00fan no hay vecinos. Este nodo no ha tra\u00eddo las estaciones p\u00fablicas a su alrededor, as\u00ed que sus lecturas hablan de esta direcci\u00f3n y de nada m\u00e1s. S\u00f3lo en Bali: pon BAD_ENABLED=1.',
          one: 'Un vecino informando, a {km} km. Uno es una an\u00e9cdota: nada aqu\u00ed distingue un fuego en el callej\u00f3n de una bruma sobre la isla.',
          silent: 'Ning\u00fan vecino est\u00e1 informando ahora, as\u00ed que no hay con qu\u00e9 comparar esta direcci\u00f3n.',
          shape: '{n} vecinos. M\u00ednimo {lo}, mitad central de {p25} a {p75}, m\u00e1ximo {hi}, todo en {unit}. El m\u00e1s cercano a {km} km.',
          youAbove: 'Lees {v} {unit}, por encima de la mitad central de ellos. Sea lo que sea, est\u00e1 m\u00e1s cerca de ti que de ellos.',
          youBelow: 'Lees {v} {unit}, por debajo de la mitad central de ellos.',
          youIn: 'Lees {v} {unit}, dentro de la mitad central que ellos leen. Nada aqu\u00ed es inusual para esta direcci\u00f3n.',
          youNone: 'No tienes sensor exterior propio, as\u00ed que no hay nada que poner en esta l\u00ednea.',
          tipBox: 'la mitad central de tus vecinos, de {p25} a {p75} {unit}',
          tipSpan: 'todo el anillo, de {lo} a {hi} {unit}',
          tipYou: 't\u00fa, {v} {unit}' },
        stations: {
          title: 'Qui\u00e9n hay ah\u00ed fuera, y a qu\u00e9 distancia',
          sub: '{n} de {all} estaciones contadas, dentro de {km} km{skipped}. Ninguna es nuestra: lo que este nodo lee por s\u00ed mismo queda fuera de esta lista.',
          skipped: ', {n} fuera por estar en interiores',
          empty: 'A\u00fan no se ha tra\u00eddo nada. En cuanto el nodo consulte, cada estaci\u00f3n dentro de {km} km aparece aqu\u00ed con su distancia.',
          row: 'a {km} km \u00b7 {net} \u00b7 {when}',
          justNow: 'ahora mismo', ago: 'hace {n} min', quiet: 'sin informar',
          indoors: 'en interiores, no contada', unknownNet: 'red desconocida' },
        fc: {
          title: 'El d\u00eda que est\u00e1 por venir',
          none: 'A\u00fan no hay pron\u00f3stico. Pon FORECAST_BMKG_ADM4 con el c\u00f3digo de aldea de este punto, o enciende Open-Meteo, y el pr\u00f3ximo d\u00eda de viento y lluvia aparece aqu\u00ed. `planetai run forecast verify` encuentra el c\u00f3digo.',
          wind: 'El viento viene del {dir} a {kmh} km/h.',
          rain: 'Se espera lluvia desde las {at}, {mm} mm a lo largo del d\u00eda.',
          dry: 'No se espera lluvia en el pr\u00f3ximo d\u00eda.',
          far: 'El punto del pron\u00f3stico est\u00e1 a {km} km de este nodo, que es otro lugar.',
          gap: 'Los dos pron\u00f3sticos difieren hasta {c} \u00b0C a lo largo del d\u00eda; ninguno es la verdad.',
          step: 'viento del {dir} {kmh} km/h \u00b7 {sky}',
          stepDry: 'seco', stepRain: '{mm} mm de lluvia', stepCloud: ' \u00b7 {n}% de nubes',
          notPredict: 'El nodo trae esto; no predice.' } },
};

// ----------------------------------------------------------------------------------------- pieces
const esc = s => String(s ?? '').replace(/[&<>"']/g, c =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* The three ported cards compose their own sentences, so their strings above are templates rather
 * than fragments: `{n} of {all} sensors need a look.` Concatenating fragments would fix English
 * word order into every other language, which is the one mistake a dictionary cannot correct.
 * Values are substituted verbatim — escape them before they get here, as esc() does elsewhere. */
const t = (s, v) => String(s || '').replace(/\{(\w+)\}/g, (_, k) => (v[k] == null ? '' : v[k]));

// ctx.fmt formats; it does not decide. The decimal places are the issue's own, from the node.
const mkCtx = (snap, view) => {
  const locale = LOCALES.includes(snap.locale) ? snap.locale : 'en';
  return {
    locale,
    w: WORDS[locale],
    register: view === 'wall' || QS.get('theme') === 'dark' || KIOSK ? 'dark' : 'paper',
    as_of: (snap.issues && snap.issues.as_of) || snap.as_of || null,
    fixture: snap.fixture || null,
    fmt: (v, dp = 0) => (v == null || isNaN(v) ? '—' : Number(v).toFixed(dp)),
    hhmm: ts => { try { return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); } catch (e) { return ''; } },
    sign: (id, cls = '') => `<svg class="sg ${cls}" aria-hidden="true"><use href="static/signs.svg#sign-${id}"/></svg>`,
    // `prov` is in the class on purpose: tools/check_ui.py's ink-only rule keys on that word, and a
    // pill called anything else is a pill the gate does not guard. Provenance is a glyph and a
    // word, never a colour — a coloured pill reads as a verdict on the number beside it.
    pill: (word, note = '') => word
      ? `<span class="pill prov" title="${esc(note)}"><svg class="sg" aria-hidden="true"><use href="static/signs.svg#sign-prov-${esc(word)}"/></svg>${esc(word)}</span>`
      : '',
  };
};

/* Which plan layers are switched off, and what the legend calls them. Module-level because it is a
 * view preference and not data: it survives a refresh and is not worth a round trip to the node. */
const PLAN_OFF = new Set();
const PLAN_LAYERS = { building: 'mapped', sat: 'from orbit only', road: 'roads', green: 'green', poi: 'uses' };

// ------------------------------------------------------------------------------- the ported cards
/* Three cards from the page this file replaces: the ring, the stations in it, and the forecast.
 *
 * They keep their old top-level names. `drawRing` and `drawForecast` are what tests/test_shipped.py
 * has asserted since v0.30 and what tools/check_ui.py can see; a method on an object literal is
 * invisible to both. They are registered in COMPONENTS below and obey the same contract as every
 * other component: pure, (data, ctx) => string, data-component on the root, its own empty state.
 *
 * Each also carries its old `data-card`, because that is the name the shipped gates know it by.
 */

/* The ring's SHAPE — lowest, the middle half, highest, and where this node sits on it.
 *
 * Deliberately NOT a median: the Stack owns "the street" (docs/HANDOFF_issues.md, settled 11 Sep).
 * On live data this card read 13.9 and the Stack read 14.6, both labelled the street, and one page
 * cannot say two things about one quantity.
 *
 * The axis runs the whole ring, lowest to highest, and nothing trims it. The MAD fence this page
 * used to compute moved to the node in Release 1 (app/issues/engine.py: fenced_median) and no
 * arithmetic is left here. One station at 152 therefore squashes the box against the left edge —
 * which is the true shape of that ring, and costs nothing, because all four numbers are written
 * out in the sentence underneath, where the old card could not put them.
 */
function drawRing(d, ctx) {
  const w = ctx.w.ring;
  const unit = esc((d && d.unit) || '');
  const f = v => esc(ctx.fmt(v, (d && d.dp) || 0));
  // /nearby carries its own credit and this uses it. The line after `||` is what a node that has
  // never fetched shows: with BAD_ENABLED unset there is no ring and no attribution to quote, and
  // the card still has to say where these numbers would have come from.
  const cite = esc(((d && d.attribution) || []).join(' · ')
    || 'Bali Air Dispatch, baliairdispatch.com, and the network named beside each station.');
  const card = (strip, note) =>
    `<div class="card ring" data-component="ring" data-card="nearby-ring">`
    + `<div class="k">${esc(w.title)}</div>${strip}`
    + `<p class="note">${note}</p><p class="note">${cite}</p></div>`;

  if (!d || !(d.ring || []).length) return card('', esc(w.none));
  if (!d.stations || d.stations < 2 || d.p25 == null) {
    return card('', d.stations === 1 ? t(esc(w.one), { km: f(d.nearest_km) }) : esc(w.silent));
  }
  const mine = d.mine;
  const lo = mine == null ? d.lowest : Math.min(d.lowest, mine);
  const hi = mine == null ? d.highest : Math.max(d.highest, mine);
  const pad = (hi - lo) * 0.15 || 1, A = lo - pad, B = hi + pad;
  const X = v => 10 + ((v - A) / (B - A)) * 580;
  const tips = { lo: f(d.lowest), hi: f(d.highest), p25: f(d.p25), p75: f(d.p75), unit };
  const shape = t(esc(w.shape), { ...tips, n: d.stations, km: f(d.nearest_km) });
  // No text inside this SVG. It scales with the card, so at 375 px a viewBox label lands at about
  // five pixels and cannot be read; every number lives in the sentence under it and in a title.
  const strip = `<svg class="ringstrip" viewBox="0 0 600 64" role="img" aria-label="${shape}">`
    + `<line x1="${X(d.lowest)}" x2="${X(d.highest)}" y1="32" y2="32" stroke="var(--ink)"`
    + ` stroke-width="1.5" stroke-opacity=".45"><title>${t(esc(w.tipSpan), tips)}</title></line>`
    + [d.lowest, d.highest].map(v => `<line x1="${X(v)}" x2="${X(v)}" y1="24" y2="40"`
        + ` stroke="var(--ink)" stroke-width="1.5" stroke-opacity=".45"/>`).join('')
    + `<rect x="${X(d.p25)}" y="20" width="${Math.max(1, X(d.p75) - X(d.p25))}" height="24"`
    + ` fill="var(--ink)" fill-opacity=".18"><title>${t(esc(w.tipBox), tips)}</title></rect>`
    // "you" is the one mark that is taller than the box rather than a different colour: state and
    // identity on this page are carried by weight, never by hue.
    + (mine == null ? '' : `<line x1="${X(mine)}" x2="${X(mine)}" y1="6" y2="58" stroke="var(--ink)"`
        + ` stroke-width="2.5"><title>${t(esc(w.tipYou), { v: f(mine), unit })}</title></line>`)
    + `</svg>`;
  const you = mine == null ? esc(w.youNone)
    : t(esc(mine > d.p75 ? w.youAbove : mine < d.p25 ? w.youBelow : w.youIn), { v: f(mine), unit });
  return card(strip, you + ' ' + shape);
}

/* Who is out there, and how far. The ring card is the shape; this is the list behind it.
 *
 * The row callbacks below are `r=>` with no space on purpose: that is the shape tools/check_ui.py
 * looks for when it checks that every field read off a row is a real column. A spaced arrow is a
 * callback the gate silently skips.
 */
function drawStations(d, ctx) {
  const w = ctx.w.stations;
  const km = d && d.radius_km != null ? ctx.fmt(d.radius_km, 0) : '—';
  const ring = (d && d.ring) || [];
  const when = r => r.indoor ? w.indoors
    : !r.reporting ? w.quiet
    : r.silent_minutes < 2 ? w.justNow
    : t(w.ago, { n: ctx.fmt(r.silent_minutes, 0) });
  const cards = ring.map(r=>COMPONENTS.sensorCard({
    name: r.name || r.sensor_id, value: r.pm25, unit: (d && d.unit) || '', dp: (d && d.dp) || 0,
    story: t(w.row, { km: r.km == null ? '—' : ctx.fmt(r.km, 1),
                      net: r.network || w.unknownNet, when: when(r) }),
    // this station's own 24 hours, from /sparks. A station reading 30 that has been at 30 all day
    // and one that was at 5 an hour ago are not the same news.
    spark: (ctx.sparks || {})[r.sensor_id] || null,
  }, ctx)).join('');
  const skipped = ring.filter(r=>r.indoor).length;
  const sub = cards
    ? t(esc(w.sub), { n: d.stations, all: ring.length, km: esc(km),
                      skipped: skipped ? t(esc(w.skipped), { n: skipped }) : '' })
    : t(esc(w.empty), { km: esc(km) });
  return `<div class="card" data-component="stations" data-card="nearby-stations">`
    + `<div class="k">${esc(w.title)}</div><p class="note">${sub}</p>`
    + (cards ? `<div class="sensors mt">${cards}</div>` : '') + `</div>`;
}

/* The day it is about to have. One timeline, not two interleaved: BMKG is the official forecast
 * where there is one and Open-Meteo carries the hours elsewhere, and the disagreement between them
 * is a sentence rather than a second set of rows.
 */
const COMPASS16 = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                   'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
const compass16 = deg => deg == null ? '?' : COMPASS16[Math.round((deg % 360) / 22.5) % 16];

function drawForecast(d, ctx) {
  const w = ctx.w.fc;
  // /forecast always names both archives; the line after `||` is for a node whose forecast pack has
  // never run, where the card exists and the endpoint's own credit does not.
  const cite = esc(((d && d.attribution) || []).join(' · ')
    || 'BMKG, api.bmkg.go.id. Open-Meteo, open-meteo.com, CC-BY 4.0, when it is on.');
  const card = (steps, note) => `<div class="card fc" data-component="forecast" data-card="forecast">`
    + `<div class="k">${esc(w.title)}</div><p class="note">${note}</p>${steps}`
    + `<p class="note">${cite} ${esc(w.notPredict)}</p></div>`;

  const hours = (d && d.hours) || [];
  if (!hours.length) return card('', esc(w.none));
  const now = Date.now();
  const all = hours.filter(h => new Date(h.ts).getTime() >= now - 3.6e6);
  const primary = all.some(h => h.source === 'forecast-bmkg') ? 'forecast-bmkg' : 'forecast-om';
  const fut = all.filter(h => h.source === primary);
  const gaps = all.filter(h => h.source === 'forecast-gap' && h.fc_temp_gap != null);
  const wind = fut.filter(h => h.fc_wind_speed != null);
  const rain = fut.filter(h => h.fc_rain > 0.2);
  const far = ((d && d.far_from_node) || [])[0];
  const w0 = wind[0];
  const note = [
    w0 ? t(esc(w.wind), { dir: esc(compass16(w0.fc_wind_direction)), kmh: esc(ctx.fmt(w0.fc_wind_speed, 0)) }) : '',
    rain.length
      ? t(esc(w.rain), { at: esc(ctx.hhmm(rain[0].ts)),
                         mm: esc(ctx.fmt(fut.reduce((a, h) => a + (h.fc_rain || 0), 0), 1)) })
      : esc(w.dry),
    far ? t(esc(w.far), { km: esc(ctx.fmt(far.km, 1)) }) : '',
    gaps.length ? t(esc(w.gap), { c: esc(ctx.fmt(Math.max(...gaps.map(h => h.fc_temp_gap)), 1)) }) : '',
    ((d && d.sources) || []).filter(s => s.sensor_id !== 'forecast-gap')
      .map(s => esc(s.name || s.sensor_id)).join(' · '),
  ].filter(Boolean).join(' ');
  const steps = fut.slice(0, 8).map(h => COMPONENTS.sensorCard({
    name: ctx.hhmm(h.ts), value: h.fc_temp, unit: '°C', dp: 0,
    story: t(w.step, {
      dir: compass16(h.fc_wind_direction), kmh: ctx.fmt(h.fc_wind_speed, 0),
      sky: (h.fc_rain > 0.2 ? t(w.stepRain, { mm: ctx.fmt(h.fc_rain, 1) }) : w.stepDry)
         + (h.fc_cloud == null ? '' : t(w.stepCloud, { n: ctx.fmt(h.fc_cloud, 0) })),
    }),
  }, ctx)).join('');
  return card(`<div class="sensors mt">${steps}</div>`, note);
}

// ------------------------------------------------------------------------------------- COMPONENTS
/* Each one is (data, ctx) => string. Pure: no DOM, no fetch, no colour literal, and every one draws
 * its own empty state rather than being hidden by somebody else.
 */
/* Red is "a signal that got worse or crossed a line", and the NODE decides whether this place has
 * crossed one — not the page, by comparing two numbers it happens to have. A model's point sample
 * sitting over the WHO 24-hour line while the node itself calls the issue `quiet` is the page
 * shouting over the node, and on a model-only node that is every evening: the VM's first live
 * render put a red 17 next to the words NOTHING TO SAY.
 *
 * `scale` and `day` still mark every value past the line, because there the line is drawn beside
 * the mark and the reader can see what the mark means. A numeral has no line next to it.
 */
const crossed_ = (d, cell) => !!(d.line && cell && cell.value != null && cell.value > d.line.value
  && (d.state === 'act' || d.state === 'notable'));

/* A 24-hour trace at tile size, restored from the page this replaces. A number with no shape behind
 * it does not tell a household whether the room is filling or clearing, which is the first thing
 * anybody wants from a sensor tile — and it is the cheapest thing on the page, because the node
 * already sends the hours: `/issues` carries `series` per distance, and `/sparks` carries one array
 * per sensor. Nothing is fetched for this and nothing is computed from it.
 *
 * Geometry only, like `scale` and `day`: the high and the low set the box, and that is all. The
 * last reading carries a dot so the eye finds `now` without a label — at 26 px a label is five
 * pixels tall and is not read.
 */
function spark(vals, ctx, opt = {}) {
  const v = (vals || []).filter(x => x != null);
  if (v.length < 2) return '';
  const W = 132, H = 26, hi = Math.max(...v), lo = Math.min(...v), span = hi - lo || 1;
  const n = vals.length;
  const at = (x, i) => [(i / (n - 1)) * W, H - 2 - ((x - lo) / span) * (H - 4)];
  const pts = vals.map((x, i) => (x == null ? null : at(x, i).join(','))).filter(Boolean).join(' ');
  let last = null;
  for (let i = n - 1; i >= 0; i--) if (vals[i] != null) { last = at(vals[i], i); break; }
  const dp = opt.dp || 0;
  return `<svg class="spark" viewBox="0 0 ${W} ${H}" role="img" preserveAspectRatio="none"`
    + ` aria-label="the last ${n} hours, ${esc(ctx.fmt(lo, dp))} to ${esc(ctx.fmt(hi, dp))}`
    + `${opt.unit ? ' ' + esc(opt.unit) : ''}">`
    + `<polyline points="${pts}" fill="none" stroke="var(--ink)" stroke-width="1.4"`
    + ` vector-effect="non-scaling-stroke" stroke-opacity=".7"/>`
    + (last ? `<circle cx="${last[0]}" cy="${last[1]}" r="2.4" fill="var(--ink)"/>` : '')
    + `</svg>`;
}

const COMPONENTS = {

  kicker(d, ctx) {
    const why = d.reason_text ? d.reason_text[ctx.locale] : '';
    return `<div class="k" data-component="kicker">`
      + `<span class="issue">${esc(d.name ? d.name[ctx.locale] : '')}</span>`
      + `<span class="state${d.state === 'act' ? ' act' : ''}">${esc(d.state || '')}</span>`
      + (why ? `<span>· ${esc(why)}</span>` : '') + `</div>`;
  },

  sentence(d, ctx) {
    const s = d.sentence ? d.sentence[ctx.locale] : '';
    if (!s) return `<p class="big" data-component="sentence">—</p>`;
    // the numeral is the monument. The node already formatted it; this only finds it to set it.
    const cell = (d.stack || {})[d.headline];
    const n = cell && cell.value != null ? ctx.fmt(cell.value, d.dp) : null;
    const crossed = crossed_(d, cell);
    const marked = n
      ? esc(s).replace(esc(n), `<b class="mono${crossed ? ' crossed' : ''}">${esc(n)}</b>`)
      : esc(s);
    return `<p class="big" data-component="sentence">${marked}</p>`;
  },

  why(d, ctx) {
    const line = d.line
      ? `${esc(d.line.source)}${d.line.value != null ? ` · ${ctx.fmt(d.line.value, d.dp)} ${esc(d.line.unit || d.unit || '')}` : ''}`
      : '';
    return `<p class="why" data-component="why">${esc(d.reason_text ? d.reason_text[ctx.locale] : '')}`
      + (line ? ` <span class="note">${line}</span>` : '') + `</p>`;
  },

  chips(d, ctx) {
    const st = d.stack || {};
    const bits = DISTANCES.filter(x => st[x]).map(x =>
      `<span class="chip">${esc((ctx.issues_labels || {})[x] || x)} · ${esc(st[x].source)}</span>`);
    return `<div class="chips" data-component="chips">${bits.join('')}</div>`;
  },

  stamp(d, ctx) {
    return `<div class="stamp" data-component="stamp">${esc(d.cell ? d.cell.caption : '')}</div>`;
  },

  /* The Stack: one quantity at room · yard · ring · region. The one component this redesign adds
   * that the layer does not name — planetai-design R11 owes it a spec. An absent distance says why
   * rather than showing a blank, because "no kit on the wall outside" is information. */
  stack(d, ctx, mini = false) {
    const st = d.stack || {};
    const cols = DISTANCES.map(id => {
      const c = st[id];
      const has = c && c.value != null;
      const crossed = crossed_(d, c);
      const label = esc((ctx.issues_labels || {})[id] || id);
      return `<div class="col"><div class="k">${label}</div>`
        + `<div class="v"><span class="num${has ? '' : ' none'}${crossed ? ' crossed' : ''}">`
        + `${has ? esc(ctx.fmt(c.value, d.dp)) : '—'}</span>`
        + (has ? `<small>${esc(d.unit || '')}</small>` : '') + `</div>`
        + (mini ? '' : `<div class="src">${esc(c ? c.source : ctx.w.notWatched)}</div>`
                     + (c ? ctx.pill(c.provenance, c.fallback || '') : ''))
        + `</div>`;
    }).join('');
    return `<div class="stack${mini ? ' mini' : ''}" data-component="stack" role="group"`
      + ` aria-label="${esc(d.name ? d.name[ctx.locale] : '')} — ${esc(ctx.w.whereItStands)}">${cols}</div>`;
  },

  miniStack(d, ctx) { return COMPONENTS.stack(d, ctx, true); },

  /* Dots on one scale, with the line drawn. Geometry only: every value and the line come from the
   * node, and the only arithmetic here is turning a number into an x. */
  scale(d, ctx) {
    const st = d.stack || {};
    const vals = DISTANCES.map(x => st[x] && st[x].value).filter(v => v != null);
    if (vals.length < 2) return '';
    const line = d.line ? d.line.value : null;
    const max = Math.max(...vals, line ? line * 1.2 : 0) * 1.15 || 1;
    const W = 600, x = v => 18 + (v / max) * (W - 36);
    let s = `<svg class="scale" data-component="scale" viewBox="0 0 ${W} 56" role="img"`
      + ` aria-label="${esc(d.name ? d.name[ctx.locale] : '')}: each distance on one scale${line ? ', with ' + esc(ctx.w.theLine) : ''}">`
      + `<line x1="18" x2="${W - 18}" y1="34" y2="34" stroke="var(--ink)" stroke-opacity=".3"/>`;
    if (line != null) {
      const lx = x(line);
      s += `<line x1="${lx}" x2="${lx}" y1="8" y2="44" stroke="var(--ink)" stroke-dasharray="3 3"/>`
        + `<text x="${lx + 6}" y="14" class="mono" font-size="10" fill="var(--ink)" fill-opacity=".7">`
        + `${esc(ctx.fmt(line, d.dp))}</text>`;
    }
    const items = DISTANCES.map(id => {
      const c = st[id];
      return c && c.value != null ? { id, v: c.value, cx: x(c.value) } : null;
    }).filter(Boolean).sort((a, b) => a.cx - b.cx);
    items.forEach(it => {
      const cr = line != null && it.v > line;
      // Every dot names itself on hover. Three distances reading close together cannot all carry a
      // label — the loop below drops the one with no room rather than overprinting it — and this is
      // where that value went.
      s += `<circle cx="${it.cx}" cy="34" r="${it.id === 'room' ? 6 : 4.5}"`
        + ` fill="${it.id === 'region' ? 'var(--ground)' : cr ? 'var(--signal-worse)' : 'var(--ink)'}"`
        + ` stroke="${cr ? 'var(--signal-worse)' : 'var(--ink)'}" stroke-width="1.5">`
        + `<title>${esc((ctx.issues_labels || {})[it.id] || it.id)} ${esc(ctx.fmt(it.v, d.dp))}`
        + `${d.unit ? ' ' + esc(d.unit) : ''}</title></circle>`;
    });
    // Two rows, and each one remembers where its own last label ended. The old rule alternated on
    // the gap to the PREVIOUS point only, so three distances close together put the first and third
    // back on the same row: node #1's heat band drew REGION 28.1 through RING 31.7. A label with
    // room on neither row is dropped rather than overprinted — every value is in the stack above,
    // and an unreadable label is worse than none.
    const ends = [-1e9, -1e9];
    items.forEach(it => {
      const label = ((ctx.issues_labels || {})[it.id] || it.id).toUpperCase()
        + ' ' + ctx.fmt(it.v, d.dp);
      const half = label.length * 3.1;                // ~6.2px per mono glyph at font-size 10
      const row = ends.findIndex(e => it.cx - half > e + 6);
      if (row < 0) return;
      ends[row] = it.cx + half;
      s += `<text x="${it.cx}" y="${row ? 22 : 52}" text-anchor="middle" class="mono" font-size="10"`
        + ` letter-spacing=".06em" fill="var(--ink)" fill-opacity=".8">${esc(label)}</text>`;
    });
    return s + `</svg>`;
  },

  /* The day it just had. The series are the node's, on one set of buckets, so the traces line up. */
  day(d, ctx) {
    const ser = d.series || {};
    const sets = DISTANCES.filter(x => Array.isArray(ser[x]) && ser[x].some(v => v != null));
    if (!sets.length) {
      return `<div class="day" data-component="day"><p class="note">`
        + `${esc(ctx.w.theDay)} — nothing recorded yet at any distance.</p></div>`;
    }
    const W = 720, H = 220, pad = { l: 34, r: 12, t: 14, b: 18 };
    const all = sets.flatMap(x => ser[x]).filter(v => v != null);
    const line = d.line ? d.line.value : null;
    const hi = Math.max(...all, line || 0) * 1.1 || 1, lo = Math.min(...all, 0);
    const n = Math.max(...sets.map(x => ser[x].length));
    const X = i => pad.l + (i / Math.max(1, n - 1)) * (W - pad.l - pad.r);
    const Y = v => H - pad.b - ((v - lo) / (hi - lo || 1)) * (H - pad.t - pad.b);
    const dash = { room: '', yard: '4 3', ring: '1 5', region: '6 4' };
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" preserveAspectRatio="none"`
      + ` aria-label="${esc(ctx.w.theDay)}: ${sets.length} traces over 24 hours">`;
    if (line != null) {
      s += `<line x1="${pad.l}" x2="${W - pad.r}" y1="${Y(line)}" y2="${Y(line)}"`
        + ` stroke="var(--signal-worse)" stroke-dasharray="3 6" stroke-opacity=".8"/>`;
    }
    sets.forEach(k => {
      const pts = ser[k].map((v, i) => (v == null ? null : `${X(i)},${Y(v)}`)).filter(Boolean).join(' ');
      if (pts) {
        s += `<polyline points="${pts}" fill="none" stroke="var(--ink)" stroke-width="1.6"`
          + ` vector-effect="non-scaling-stroke"${dash[k] ? ` stroke-dasharray="${dash[k]}"` : ''}`
          + ` stroke-opacity="${k === 'room' ? 1 : .55}"/>`;
      }
    });
    s += `</svg>`;
    const legend = sets.map(k =>
      `<span><i class="${k === 'room' ? '' : k === 'ring' ? 'dot' : 'dash'}"></i>`
      + `${esc((ctx.issues_labels || {})[k] || k)}</span>`).join('');
    return `<div class="day" data-component="day"><div class="trace">${s}</div>`
      + `<div class="legend">${legend}</div></div>`;
  },

  /* A quantity as repeated signs. `per` is how much one sign is worth, so the row is countable. */
  unitRow(d, ctx) {
    const per = d.per || 1;
    const full = Math.floor((d.n || 0) / per);
    const rem = (d.n || 0) / per - full;
    let row = '';
    for (let i = 0; i < Math.min(full, 200); i++) row += ctx.sign(d.sign, d.cls || '');
    if (rem >= 0.25) row += `<span class="part">${ctx.sign(d.sign, d.cls || '')}</span>`;
    return `<div class="unit" data-component="unitRow"><div class="lab">${esc(d.label)}<b>${esc(d.sub || '')}</b></div>`
      + `<div class="row">${row}</div>`
      + (d.cap ? `<div class="cap">${esc(d.cap)}</div>` : '') + `</div>`;
  },

  readout(d, ctx) {
    return `<div class="unit" data-component="readout"><div class="lab">${esc(d.label)}</div>`
      + `<div class="v"><span class="num">${esc(ctx.fmt(d.value, d.dp || 0))}</span>`
      + `<small>${esc(d.unit || '')}</small></div>`
      + (d.source ? `<div class="cap">${esc(d.source)} ${ctx.pill(d.provenance)}</div>` : '') + `</div>`;
  },

  /* ρ as a row of rings, answered first. The count comes from /rho — node #1 is at 58 and 21, not
   * the 28 and 14 the prototype drew. */
  rhoRow(d, ctx) {
    const total = d.alerts_act || 0, closed = d.acted || 0;
    if (!total) {
      return `<div class="rho${d.small ? ' small' : ''}" data-component="rhoRow" role="img"`
        + ` aria-label="no asks yet"><span class="note">no asks yet</span></div>`;
    }
    let s = '';
    for (let i = 0; i < Math.min(total, 120); i++) s += ctx.sign(i < closed ? 'rho-closed' : 'rho-open', i < closed ? 'closed' : '');
    return `<div class="rho${d.small ? ' small' : ''}" data-component="rhoRow" role="img"`
      + ` aria-label="${closed} of ${total} asks answered">${s}</div>`;
  },

  /* The ask strip. It carries the HEADLINE issue's ask, so the hero and the instruction cannot
   * disagree — they are the same issue. An ask whose reading came back is still listed, and says
   * so, because ρ counts it; it just stops driving the hero. */
  askStrip(d, ctx) {
    const ask = (d.open_asks || [])[0];
    if (!ask) return `<div class="askstrip" data-component="askStrip" hidden></div>`;
    const says = (ask.says || {})[ctx.locale] || '';
    const how = (ask.how || {})[ctx.locale] || '';
    return `<div class="askstrip" data-component="askStrip" data-alert="${esc(String(ask.id))}">`
      + `<div class="what">${esc(says)}<small>${esc(how)}</small></div>`
      + `<button type="button" class="go" data-act="${esc(String(ask.id))}">${esc(ctx.w.didThis)}</button>`
      + `</div>`;
  },

  /* What the node doubts about its own instruments. §2.3: trust findings belong in the place band,
   * beside the sensors they are about, not in the room with the readings they cast doubt on.
   *
   * The two numbers in the filter are the pack's own: 60 % is packs/trust/rules.yml's coverage_low
   * line and 168 hours is a week. /trust answers with measurements and no verdict, so the verdict
   * is here — and a sensor under a week old reads 0 % coverage while being perfectly healthy,
   * which is the whole reason that first clause exists.
   * ponytail: the doubt rule is copied from the pack rather than derived from it. It moves behind
   * /trust the day that endpoint returns a verdict per sensor.
   */
  trustCard(d, ctx) {
    const w = ctx.w.trust;
    const rows = d.rows || [];
    const doubt = rows.filter(r=>r.age_hours < 168 || r.coverage_7d < 60 || r.frozen_channels > 0);
    const body = !rows.length ? ''
      : doubt.length
      ? doubt.map(r=>{
        const cov = r.age_hours < 168 ? esc(w.young) : t(esc(w.cov), { pct: esc(String(r.coverage_7d)) });
        const froz = r.frozen_channels ? t(esc(w.frozen), { n: r.frozen_channels }) : '';
        return `<div class="vit"><span>${esc(r.name || r.sensor_id)}</span><span>${cov}${froz}</span></div>`;
      }).join('')
      : `<p class="note">${esc(w.ok)}</p>`;
    const sub = !rows.length ? esc(w.none)
      : doubt.length ? t(esc(w.sub), { n: doubt.length, all: rows.length })
        : t(esc(w.subOk), { all: rows.length });
    return `<div class="card trust" data-component="trustCard" data-card="trust">`
      + `<div class="k">${esc(w.title)}</div><p class="note">${sub}</p>${body}</div>`;
  },

  // The three ported cards, so piece() draws each inside its own guard like everything else.
  ring: drawRing,
  stations: drawStations,
  forecast: drawForecast,

  sensorCard(d, ctx) {
    return `<div class="sensor" data-component="sensorCard">`
      + `<div class="top"><span class="n">${esc(d.name)}</span>`
      + `<span class="v"><span class="num">${esc(ctx.fmt(d.value, d.dp || 0))}</span><small>${esc(d.unit || '')}</small></span></div>`
      + (d.story ? `<div class="story">${esc(d.story)}</div>` : '')
      + (d.spark ? spark(d.spark, ctx, { dp: d.dp, unit: d.unit }) : '')
      + `<div class="row">${ctx.pill(d.provenance)}${d.chip ? `<span class="chip">${esc(d.chip)}</span>` : ''}</div>`
      // The kits behind an aggregate, each linked to its own page where the source gives one. Only
      // an account kit has a `url` in its meta; a public station never does, and /sensors strips
      // the key entirely for a reader the node does not trust. So the link appears exactly where
      // somebody can actually open it.
      // Capped: the ring card listed seven of them, and seven ids stacked under a number is not a
      // list anybody reads. The names come from /sensors, so a fixture that carries none — the
      // committed one predates `planetai snapshot` — falls back to the raw id, which is the one
      // case where the cap matters most.
      + (d.kits && d.kits.length ? `<div class="kits">${d.kits.slice(0, 4).map(k => k.url
          ? `<a href="${esc(k.url)}" target="_blank" rel="noopener noreferrer">${esc(k.name)}</a>`
          : `<span>${esc(k.name)}</span>`).join('')}`
        + (d.kits.length > 4 ? `<span class="more">+${d.kits.length - 4}</span>` : '') + `</div>` : '')
      + `</div>`;
  },

  indexRow(d, ctx) {
    const st = d.stack || {};
    const mini = DISTANCES.filter(x => st[x] && st[x].value != null)
      .map(x => `<b>${esc(ctx.fmt(st[x].value, d.dp))}</b>`).join(' ');
    return `<a class="row" data-component="indexRow" href="#band-${esc(d.key)}"${d.watched ? '' : ' aria-disabled="true"'}>`
      + `<span class="name">${esc(d.name ? d.name[ctx.locale] : d.key)}</span>`
      + `<span class="state${d.state === 'act' ? ' act' : ''}">${esc(d.state)}</span>`
      + `<span class="line">${esc(d.sentence ? d.sentence[ctx.locale] : '')}</span>`
      + `<span class="mini">${mini}</span></a>`;
  },

  ledger(d, ctx) {
    const rows = (d.alerts || []).slice(0, 14).map(a => {
      const done = a.acted_at;
      return `<div class="al"><span class="when mono">${esc(ctx.hhmm(a.ts))}</span>`
        + `<span class="iss${a.level === 'act' ? ' act' : ''}">${esc(a.level || '')}</span>`
        + `<span class="txt">${esc(String(a.text || '').split('\n')[0])}`
        + `<span class="meta">${esc(a.rule_id || '')}</span></span>`
        + `<span class="do">${done
            ? `<span class="done">${ctx.sign('rho-closed', 'closed')} ${esc(ctx.w.noted)} ${esc(ctx.hhmm(done))}</span>`
            : a.level === 'act'
              ? `<button type="button" data-act="${esc(String(a.id))}">${esc(ctx.w.didThis)}</button>` : ''}</span></div>`;
    }).join('');
    return `<div class="ledger" data-component="ledger">${rows || `<p class="note">nothing yet</p>`}</div>`;
  },

  report(d, ctx) {
    if (!d || !d.text) return `<div class="rep" data-component="report"><p class="note">no report yet</p></div>`;
    return `<div class="rep" data-component="report">`
      + `<div class="k">${esc(ctx.hhmm(d.ts))}${d.sent === false ? ' · held for quiet hours' : ''}</div>`
      + `<p>${esc(d.text)}</p></div>`;
  },

  /* Two satellite records, one component, told apart by the pill. `model` is this node's own
   * AlphaEarth layer — a description of every 10 m pixel, never a photograph. `partial` is
   * Sentinel-2 or Landsat imagery from Earth Engine. A hard cut once every --motion-satellite-year,
   * never a cross-fade; under reduced motion it stands on the latest year. Nothing coloured sits on
   * a frame: the frame's own stamp stays, because the PNG has to stand alone when somebody saves it.
   */
  satellite(d, ctx) {
    const frames = d.frames || [];
    if (!frames.length) {
      return `<div class="sat" data-component="satellite"><p class="note">${esc(d.empty || 'no frames yet')}</p></div>`;
    }
    // `data-src`, not `src`. /earth/year.png and /earth/frame.png need the node's token at
    // SHARE_LEVEL=off and a browser cannot put a header on an <img>, so every frame came back 403
    // and a household that HAD unlocked the page saw every number and no pictures. wireSatellites()
    // fetches them the way the rest of the page fetches — see FRAMES there.
    const imgs = frames.map((y, i) =>
      `<img data-src="${esc(d.src(y))}" alt="${esc(d.caption ? d.caption(y) : String(y))}"`
      + ` class="${i === frames.length - 1 ? 'on' : ''}" data-i="${i}">`).join('');
    const chg = d.change ? `<img data-src="${esc(d.change.src)}" alt="${esc(d.change.alt)}" data-i="change">` : '';
    const ctl = d.controls
      ? `<button type="button" data-sat="play" aria-label="Play the years">${REDUCED ? 'motion off' : 'play'}</button>`
        + `<input type="range" data-sat="slider" min="0" max="${frames.length - 1}" value="${frames.length - 1}" aria-label="Year">`
        + (d.change ? `<button type="button" data-sat="mode" aria-pressed="false">what changed</button>` : '')
      : '';
    return `<div class="sat" data-component="satellite" data-id="${esc(d.id)}"`
      + ` data-frames="${esc(frames.join(','))}">`
      + `<div class="sat-loop">${imgs}${chg}</div>`
      + `<div class="sat-bar"><span class="yr mono" data-sat="year">${esc(String(frames[frames.length - 1]))}</span>`
      // the pill before the controls, so it lands beside the year on both cards. After them it
      // wrapped below on the card that has controls and sat inline on the card that does not, and
      // the one thing that tells the two records apart moved between them.
      + `${ctx.pill(d.provenance)}<span class="sat-ctl">${ctl}</span></div>`
      + `<div class="sat-credit">${(d.credit || []).map(esc).join('<br>')}</div></div>`;
  },

  /* The node's own kilometre: the plan, drawn from /place/geojson over the res-8 ground.
   *
   * /place/geojson needs a token at EVERY share level — it is the exact shape of the buildings
   * around a household, the one thing SHARE_LEVEL never hands out. So on a phone on the house WiFi
   * with no token this card has a ground and no plan, and it says which, because a card that goes
   * blank reads as a broken node rather than a private one.
   *
   * Ported from the page this replaces, with three changes. Every colour is a role token now
   * (the old one had #8A8378 and two rgba() literals inline). The node marker's pulsing <animate>
   * is gone: motion is bound to the cadence of its own datum and a marker has no datum, so under
   * R6 it is deleted rather than tokenised. And the legend's buttons carry data attributes rather
   * than inline onclick, because render() is the only thing here that touches the DOM.
   */
  planCard(d, ctx) {
    const plan = d.plan;
    if (!plan || !plan.features) {
      const why = d.status === 403
        ? 'The plan is the shape of this building, so this node answers it only on the machine it '
          + 'runs on, or to a request carrying a token. Unlock in Set up to draw it here.'
        : d.status ? `Could not read the map from this node (${d.status}). Trying again on the next refresh.`
                   : '';
      return `<div class="plan" data-component="planCard">`
        + `<img src="static/node-ground.svg" alt="The node's own kilometre, drawn from its coordinates">`
        + (why ? `<p class="note">${esc(why)}</p>` : '')
        + `<div class="cap mono">${esc(d.caption || '')}</div></div>`;
    }
    const F = plan.features;
    if (!F.length) {
      // Two different situations, and only one is worth a band: a node whose place pack has never
      // run has no table at all, and nobody needs telling about a pack they did not enable.
      const t = (plan.diag || {}).tables || {};
      if (!t.place_features) return '';
      const h = (plan.diag || {}).hint || 'No map stored for this point yet. On the node: planetai run place refresh';
      return `<div class="plan" data-component="planCard"><p class="note">`
        + `${esc(h.charAt(0).toUpperCase() + h.slice(1))}</p></div>`;
    }
    const [clon, clat] = plan.center, R = plan.radius_m || 1000, S = 500 / (R * 1.05);
    const px = ([lon, lat]) => [500 + (lon - clon) * 111320 * Math.cos(clat * Math.PI / 180) * S,
                                500 - (lat - clat) * 111320 * S];
    const ring = r => r.map(px).map(pt => pt.map(v => v.toFixed(1)).join(',')).join(' ');
    const poly = g => g.type === 'Polygon' ? `M${ring(g.coordinates[0])}Z`
      : g.type === 'MultiPolygon' ? g.coordinates.map(pg => `M${ring(pg[0])}Z`).join(' ') : '';
    /* The first [lon,lat] of any geometry, however deeply nested. A poi is usually a Point, but
     * OpenStreetMap also carries amenities as open ways — Garuda Wisnu Kencana, inside node #1's
     * kilometre, is one — and for a LineString `coordinates[0][0]` is a number, not a pair.
     * Destructuring that number threw, and the whole kilometre went blank with no message. */
    const firstPt = g => { let c = g && g.coordinates; while (Array.isArray(c) && Array.isArray(c[0])) c = c[0]; return c; };
    const L = { building: '', sat: '', road: '', green: '', poi: '' };
    const counts = { building: 0, sat: 0, road: 0, green: 0, poi: 0 };
    let skipped = 0;
    for (const f of F) {
      const k = f.properties.kind, g = f.geometry;
      if (!Object.prototype.hasOwnProperty.call(L, k)) continue;
      try {
        if (k === 'road' && g.type === 'LineString') {
          const w = /^(primary|secondary|trunk)$/.test(f.properties.highway) ? 2.2
            : /^(tertiary|residential|unclassified)$/.test(f.properties.highway) ? 1.4 : 0.6;
          L.road += `<polyline points="${ring(g.coordinates)}" stroke-width="${w}"/>`; counts.road++;
        } else if (k === 'poi') {
          const c = px(firstPt(g));
          L.poi += `<circle cx="${c[0].toFixed(1)}" cy="${c[1].toFixed(1)}" r="4.5" fill="var(--cells)">`
            + `<title>${esc(f.properties.name || f.properties.category || '')}</title></circle>`;
          counts.poi++;
        } else if (g.type === 'Polygon' || g.type === 'MultiPolygon') {
          L[k] += `<path d="${poly(g)}"/>`; counts[k]++;
        } else { skipped++; }
      } catch (e) { skipped++; }   // one unusual object must never cost the whole kilometre
    }
    const off = k => (PLAN_OFF.has(k) ? ' hidden' : '');
    const h = Math.round(500 + R * S + 80);
    const svg = `<svg viewBox="0 0 1000 ${h}" role="img" aria-label="The kilometre around this node">`
      + `<defs><clipPath id="pc"><circle cx="500" cy="500" r="${R * S}"/></clipPath></defs>`
      + `<circle cx="500" cy="500" r="${R * S}" fill="none" stroke="var(--hair)"/>`
      + `<g clip-path="url(#pc)">`
      + `<g class="veg"${off('green')}>${L.green}</g>`
      + `<g class="road"${off('road')}>${L.road}</g>`
      + `<g class="fig"${off('building')}>${L.building}</g>`
      + `<g class="sat"${off('sat')}>${L.sat}</g>`
      + `<g${off('poi')}>${L.poi}</g></g>`
      + `<circle cx="500" cy="500" r="7" fill="var(--cells)"/>`
      + `<text x="500" y="${500 + R * S + 28}" text-anchor="middle" class="mono label">`
      + `${R} M · NORTH UP · ${esc(d.node || '')}</text>`
      + `<line x1="${500 - R * S}" y1="${500 + R * S + 52}" x2="${500 - R * S + 200 * S}"`
      + ` y2="${500 + R * S + 52}" stroke="var(--ink)" stroke-opacity=".5"/>`
      + `<text x="${500 - R * S}" y="${500 + R * S + 70}" class="mono label">200 m</text></svg>`;
    const legend = Object.entries(PLAN_LAYERS).filter(([k]) => counts[k])
      .map(([k, label]) => `<button type="button" data-layer="${k}"${PLAN_OFF.has(k) ? ' class="off"' : ''}>`
        + `<i class="${k}"></i>${esc(label)} ${counts[k].toLocaleString()}</button>`).join('');
    return `<div class="plan" data-component="planCard">${svg}`
      + `<div class="plan-legend">${legend}</div>`
      + (skipped ? `<div class="cap">${skipped} shape${skipped === 1 ? '' : 's'} this plan has no way to draw</div>` : '')
      + `<div class="cap mono">${esc(d.caption || '')}</div></div>`;
  },

  /* Every number on the page, its source, its as-of and its word. Generated from /issues'
   * provenance, so a figure with no row here cannot be drawn — which is what makes `live` earned. */
  figures(d, ctx) {
    const rows = (d.rows || []).map(r =>
      `<tr><td>${esc(r.figure)}</td><td class="mono">${esc(r.value == null ? '—' : String(r.value))}`
      + ` ${esc(r.unit || '')}</td><td>${esc(r.source)}</td>`
      + `<td>${ctx.pill(r.provenance)}</td></tr>`).join('');
    // Figures is the one wide thing on this page, and a table that will not fit narrows to nothing
    // or pushes the whole page sideways. It scrolls inside its own box instead.
    return `<div class="figwrap"><table class="figs" data-component="figures">`
      + `<thead><tr><th>${esc(ctx.w.figure)}</th><th></th><th>${esc(ctx.w.source)}</th><th>${esc(ctx.w.word)}</th></tr></thead>`
      + `<tbody>${rows || `<tr><td colspan="4" class="note">nothing to show yet</td></tr>`}</tbody></table></div>`;
  },
};

// ---------------------------------------------------------------------------------------- ANATOMY
/* What each kind of band is made of. Changing what a band shows is editing one of these lists —
 * that is the whole point of the file being arranged this way.
 */
const ANATOMY = {
  hero:           ['kicker', 'sentence', 'why', 'chips', 'miniStack', 'askStrip', 'rhoRow', 'stamp'],
  'issue.sensed': ['kicker', 'sentence', 'why', 'stack', 'scale', 'day', 'ringCards', 'forecastStrip', 'sources'],
  'issue.context': ['kicker', 'sentence', 'why', 'readouts', 'satellites'],
  place:          ['planCard', 'units', 'trustCard'],
  loop:           ['rhoRow', 'report', 'ledger'],
  figures:        ['figures'],
  wall:           ['kicker', 'sentence', 'why', 'satellite', 'wallIndex', 'rhoRow', 'stamp'],
  index:          ['indexRow'],
};

// ----------------------------------------------------------------------------------------- layout
/* The page order: the hero, the index, one band per declared issue, then the place, the loop and
 * the figures. Arrange edits this and saves it as UI_LAYOUT, exactly as it always has.
 */
let LAYOUT = null;

function layout(snap) {
  const order = ((snap.issues || {}).order) || [];
  const base = ['hero', 'index', ...order.map(k => 'issue:' + k), 'place', 'loop', 'figures'];
  if (!LAYOUT) return base;
  const hidden = new Set(LAYOUT.hidden || []);
  const wanted = (LAYOUT.order || []).filter(x => base.includes(x));
  const rest = base.filter(x => !wanted.includes(x));
  return [...wanted, ...rest].filter(x => !hidden.has(x));
}

// ------------------------------------------------------------------------------------- composites
/* A few anatomy entries are groups rather than single components: a band's Sources column is many
 * sensorCards, a context band's readouts are many readouts. They live here, they call COMPONENTS,
 * and they are as pure as the things they call.
 */
const COMPOSITES = {
  /* One card per distance, carrying the value the NODE computed for it, and under each the kits
   * that went into it. Not one card per sensor with its own number: the engine aggregates per
   * sensor and publishes only the result (engine._cell keeps the ids, not the values), and working
   * a per-sensor figure out here would be the page computing again. When /issues publishes the
   * per-sensor values, this becomes one card each and the names below become their headings. */
  sources(d, ctx) {
    const st = d.stack || {};
    const kit = {};
    (ctx.sensors || []).forEach(s => {
      kit[s.sensor_id] = { name: s.name || s.sensor_id, url: (s.meta&&s.meta.url) || null };
    });
    const cards = DISTANCES.filter(x => st[x]).map(x => COMPONENTS.sensorCard({
      name: st[x].source, value: st[x].value, unit: d.unit, dp: d.dp,
      provenance: st[x].provenance,
      chip: st[x].n > 1 ? `${st[x].n} sensors` : (ctx.issues_labels || {})[x] || x,
      story: st[x].age_minutes != null ? `last reading ${st[x].age_minutes} min ago` : '',
      // the same 24 hours the band's own chart draws, at tile size, for this distance alone
      spark: (d.series || {})[x] || null,
      kits: (st[x].sensors || []).map(id => kit[id] || { name: id, url: null }),
    }, ctx)).join('');
    return `<div class="sensors">${cards || `<p class="note">${esc(ctx.w.notWatched)}</p>`}</div>`;
  },

  /* The ring belongs to air and to nothing else: /nearby is one archive of one metric. Same shape
   * as `satellites` below — the band asks for it, the composite decides whether this issue is the
   * one it is about. */
  ringCards(d, ctx) {
    if (d.key !== 'air') return '';
    const near = { ...(ctx.nearby || {}), unit: d.unit, dp: d.dp };
    return piece('ring', near, ctx) + piece('stations', near, ctx);
  },

  /* The forecast is weather, and weather is not an issue (§2): it is context that feeds air and
   * heat. One card, so it goes on whichever of those two this place declared first — set once per
   * render, in render(), rather than guessed here. */
  forecastStrip(d, ctx) {
    if (!ctx.forecast_owner || d.key !== ctx.forecast_owner) return '';
    return piece('forecast', ctx.forecast || {}, ctx);
  },
  readouts(d, ctx) {
    // Nothing, not an empty box. The band is a two-column grid, so an empty <div> here took half of
    // Land and left the two satellite cards squeezed into the right-hand column with a hole beside
    // them. A composite with nothing to say says nothing; `sources` below draws a sentence instead,
    // because "no sensor at this distance" IS something to say and an absent readout is not.
    const rows = (d.readouts || []).map(r => COMPONENTS.readout({
      label: r.label ? r.label[ctx.locale] : r.metric, value: r.value, dp: r.dp, unit: r.unit,
      source: r.source, provenance: r.provenance,
    }, ctx)).join('');
    return rows ? `<div class="grid g3">${rows}</div>` : '';
  },
  /* Land gets the satellite component twice: this node's own record, and the imagery — two records,
   * two provenance words, never merged. Everything else gets neither. */
  satellites(d, ctx) {
    if (d.key !== 'land') return '';
    const e = ctx.earth || {};
    const own = COMPONENTS.satellite({
      id: 'sat-own', frames: e.frames || [], provenance: 'model', controls: true,
      src: y => `/earth/year.png?year=${y}`,
      caption: y => `This node's own satellite layer for ${y}`,
      change: e.png ? { src: '/earth/change.png', alt: 'Where the land changed between the last two years' } : null,
      // Said on the card, not just in a comment: this is a rendering of a model, and a household
      // looking at grey land needs to know it is not a picture of their village from space.
      credit: ['Not a photograph. This is the node\'s own copy of a model\'s 64-number description '
               + 'of every 10 m pixel, flattened to one number and drawn in grey.',
               e.attribution || ''].filter(Boolean),
      // /earth works out which command comes next — fetch, then change, then frames — and says so
      // in `hint`. Preferring it over a guess here is the same rule as everywhere else on this
      // page: the node knows, so the node says. The fallback names the whole sequence.
      empty: e.hint || 'No satellite record yet. On the node: planetai run earth fetch, then '
                     + 'planetai run earth change, then planetai run earth frames.',
    }, ctx);
    const img = (e.imagery || {});
    const sen = COMPONENTS.satellite({
      id: 'sat-imagery', frames: img.sentinel || [], provenance: 'partial', controls: false,
      src: y => `/earth/frame.png?source=sentinel&year=${y}`,
      caption: y => `Sentinel-2 annual median for ${y}`,
      credit: img.credit || [],
      empty: 'No imagery yet — on the node: planetai run earth-engine timelapse',
    }, ctx);
    return `<div class="grid g2">${own}${sen}</div>`;
  },
  units(d, ctx) {
    return (d.units || []).map(u => COMPONENTS.unitRow(u, ctx)).join('')
      || `<p class="note">nothing mapped around this node yet</p>`;
  },
  wallIndex(d, ctx) {
    const rows = (d.issues || []).map(i =>
      `<div><span class="name">${esc(i.name ? i.name[ctx.locale] : '')}</span>`
      + `<span class="st">${esc(i.state)}</span>`
      + `<span class="ln">${esc(i.sentence ? i.sentence[ctx.locale] : '')}</span></div>`).join('');
    return `<div class="wi">${rows}</div>`;
  },
};

/* One component, drawn inside its own guard. A throw draws that component's own box and names
 * itself in the console; nothing else on the page goes dark. This replaces the single try/catch
 * that wrapped the whole of the old refresh(), where one bad card took every card below it — three
 * releases running, and the satellite cards were drawn last.
 */
function piece(name, data, ctx) {
  try {
    const fn = COMPONENTS[name] || COMPOSITES[name];
    if (!fn) throw new Error('no component named ' + name);
    return fn(data, ctx) || '';
  } catch (e) {
    console.error('component', name, e);
    return `<div class="card" data-component="${esc(name)}" data-error="1"><p class="note">`
      + `This part could not be drawn from what the node returned. The rest of the page is unaffected.</p></div>`;
  }
}

const assemble = (names, data, ctx) => names.map(n => piece(n, data, ctx)).join('');

// -------------------------------------------------------------------------------------- the bands
function issueBand(key, iss, ctx) {
  const d = { ...iss, key };
  const kind = d.kind === 'context' ? 'issue.context' : 'issue.sensed';
  const quiet = d.state === 'quiet' || d.state === 'none';
  return `<section class="band${quiet ? ' quiet' : ''}" id="band-${esc(key)}" data-band="issue:${esc(key)}">`
    + `<div class="bandhead">${piece('kicker', d, ctx)}`
    + `<h2 class="t">${piece('sentence', d, ctx)}</h2>${piece('why', d, ctx)}</div>`
    + `<div class="grid g2">`
    + assemble(ANATOMY[kind].filter(n => !['kicker', 'sentence', 'why'].includes(n)), d, ctx)
    + `</div></section>`;
}

function bandFor(id, snap, ctx) {
  const iss = (snap.issues || {}).issues || {};
  if (id.startsWith('issue:')) {
    const k = id.slice(6);
    return iss[k] ? issueBand(k, iss[k], ctx) : '';
  }
  if (id === 'hero') {
    const head = (snap.issues || {}).headline;
    const d = head && iss[head] ? { ...iss[head], key: head, cell: (snap.health || {}).cell } : { cell: (snap.health || {}).cell };
    // The mount's own id travels with the markup that replaces it. Without it the FIRST render
    // works and every one after it throws: outerHTML removes the element getElementById just found,
    // and the next refresh — twenty seconds later, or the moment somebody opens another view —
    // looks for a node that is no longer there. index.html calls these mount points; they have to
    // survive being rendered into.
    return `<div class="hero" id="hero" data-band="hero">`
      + `<div class="bg" aria-hidden="true"><img src="static/node-ground.svg" alt=""></div>`
      + `<div>${piece('kicker', d, ctx)}${piece('sentence', d, ctx)}${piece('why', d, ctx)}`
      + `${piece('chips', d, ctx)}${piece('miniStack', d, ctx)}</div>`
      + `<div class="side">${piece('askStrip', d, ctx)}`
      + `${piece('rhoRow', { ...(snap.rho || {}), small: true }, ctx)}${piece('stamp', d, ctx)}</div></div>`;
  }
  if (id === 'index') {
    const order = (snap.issues || {}).order || [];
    const undecl = (snap.issues || {}).undeclared || [];
    const rows = [...order, ...undecl].filter(k => iss[k])
      .map(k => piece('indexRow', { ...iss[k], key: k }, ctx)).join('');
    // One root, not two: the note has its own mount in the skeleton (#index-note) and render()
    // fills it. Returned here it was inserted as a sibling, and the next render — which replaces
    // #index and not the sibling — left the old one behind and added another.
    return `<div class="index" id="index" data-band="index">${rows}</div>`;
  }
  if (id === 'place') {
    return `<section class="band" id="place" data-band="place">`
      + `<div class="bandhead"><div class="k">${esc(ctx.w.thePlace)}</div></div>`
      + `<div class="grid g21">${assemble(ANATOMY.place, { caption: (snap.health || {}).cell ? snap.health.cell.caption : '',
        status: snap.placeStatus, plan: snap.place, node: (snap.health || {}).node, units: [],
        rows: snap.trust || [] }, ctx)}</div></section>`;
  }
  if (id === 'loop') {
    return `<section class="band" id="loop" data-band="loop">`
      + `<div class="bandhead"><div class="k">${esc(ctx.w.theLoop)}</div></div>`
      + piece('rhoRow', snap.rho || {}, ctx)
      + `<div class="grid g2 mt">${piece('report', snap.report || {}, ctx)}`
      + `${piece('ledger', { alerts: snap.alerts || [] }, ctx)}</div></section>`;
  }
  if (id === 'figures') {
    const rows = Object.entries(iss).flatMap(([, v]) => v.provenance || []);
    return `<section class="band" id="figures" data-band="figures">`
      + `<div class="bandhead"><div class="k">${esc(ctx.w.figures)}</div></div>`
      + piece('figures', { rows }, ctx) + `</section>`;
  }
  return '';
}

function wallView(snap, ctx) {
  const iss = (snap.issues || {}).issues || {};
  const head = (snap.issues || {}).headline;
  const d = head && iss[head] ? { ...iss[head], key: head, cell: (snap.health || {}).cell } : { cell: (snap.health || {}).cell };
  const e = snap.earth || {};
  const img = e.imagery || {};
  const useImagery = (img.sentinel || []).length > 0;
  const sat = COMPONENTS.satellite({
    id: 'wall-sat',
    frames: useImagery ? img.sentinel : (e.frames || []),
    provenance: useImagery ? 'partial' : 'model',
    controls: false,                                   // R6: the wall is an instruction, not a control
    src: y => useImagery ? `/earth/frame.png?source=sentinel&year=${y}` : `/earth/year.png?year=${y}`,
    caption: y => `${y}`,
    credit: useImagery ? (img.credit || []) : [e.attribution || ''],
    empty: '',
  }, ctx);
  const stale = (snap.health || {}).last_poll && ctx.staleFor(snap.health.last_poll);
  return `<div class="bg" aria-hidden="true"><img src="static/node-ground.svg" alt=""></div>`
    // The only control on the wall, and it acts on the view rather than on anything the node knows.
    // Without it a laptop that reached the wall from the nav has no way back, because the header is
    // gone; a kiosk never shows a pointer and nobody presses it.
    + `<button type="button" class="exit" data-view="now">${esc(ctx.w.now)}</button>`
    + `<div class="row2"><div>${piece('kicker', d, ctx)}${piece('sentence', d, ctx)}${piece('why', d, ctx)}</div>`
    + `<div class="satwrap">${sat}</div></div>`
    + piece('wallIndex', { issues: ((snap.issues || {}).order || []).map(k => iss[k]).filter(Boolean) }, ctx)
    + piece('rhoRow', snap.rho || {}, ctx)
    + `<div class="foot"><span>${esc((snap.health || {}).node || '')}</span>`
    + `<span>${esc((snap.health || {}).cell ? snap.health.cell.caption : '')}</span>`
    + (stale ? `<span class="st">${esc(ctx.w.stale)}</span>` : '')
    + `<span>${esc(ctx.w.answerOn)}</span></div>`;
}

// --------------------------------------------------------------------------------------- render
/* The only function that writes to the DOM. Everything above builds strings.
 *
 * ?only=<band> shows one band, for a wall screen or a capture. An unknown name shows the whole
 * page rather than a blank one — a typo in a URL should not look like a broken node.
 */
let LAST = null;

function render(snap, view) {
  const ctx = mkCtx(snap, view);
  ctx.issues_labels = ((snap.issues || {}).labels || {})[ctx.locale] || {};
  ctx.earth = snap.earth || {};
  ctx.nearby = snap.nearby || null;
  ctx.forecast = snap.forecast || null;
  ctx.sensors = snap.sensors || [];
  ctx.sparks = snap.sparks || {};
  // Which issue carries the forecast. Declared order decides, so a node watching only air gets it
  // on air and one watching both gets it once, on whichever it put first.
  ctx.forecast_owner = (((snap.issues || {}).order) || []).find(k => k === 'heat' || k === 'air') || null;
  ctx.staleFor = ts => {
    const poll = (snap.health || {}).poll_seconds || 300;
    return ts ? (Date.now() - new Date(ts)) / 1000 > poll * 2 : false;
  };

  document.documentElement.dataset.theme = ctx.register === 'dark' ? 'dark' : '';
  if (!document.documentElement.dataset.theme) delete document.documentElement.dataset.theme;
  // R6 again: the wall carries no chrome. The header is five buttons and belongs on a page someone
  // is standing at, not on a screen across a room.
  document.body.classList.toggle('wallview', view === 'wall');

  const h = snap.health || {};
  document.getElementById('nodename').textContent = h.node || 'node';
  document.getElementById('nodeplace').textContent =
    [h.city, h.kind, ctx.as_of ? `${ctx.w.asOf} ${ctx.hhmm(ctx.as_of)}` : ''].filter(Boolean).join(' · ');
  document.getElementById('headprov').innerHTML =
    ctx.fixture ? ctx.pill('cached', 'rendered from a committed snapshot, not from live readings')
                : ctx.pill(ctx.staleFor(h.last_poll) ? 'cached' : 'live', h.last_poll || '');

  // SHARE_LEVEL=off with no token: the shell, and the node's own sentence about why. Not a blank.
  if (snap.refused) {
    document.getElementById('hero').outerHTML =
      `<div class="hero" id="hero"><div><p class="big">${esc(ctx.w.refused)}</p>`
      + `<p class="why">${esc(snap.refused)}</p></div></div>`;
    ['index', 'bands', 'place', 'loop', 'figures'].forEach(id => {
      const el = document.getElementById(id); if (el) el.innerHTML = '';
    });
    return;
  }

  if (view === 'wall') {
    document.getElementById('wallbox').innerHTML = wallView(snap, ctx);
    wireSatellites(document.getElementById('wallbox'));
    return;
  }

  const order = layout(snap);
  const want = ONLY && order.includes(ONLY) ? [ONLY] : order;
  const bands = document.getElementById('bands');
  bands.innerHTML = '';
  const note = document.getElementById('index-note');
  if (note) note.textContent = '';
  for (const id of want) {
    const html = bandFor(id, snap, ctx);
    if (!html) continue;
    // Each of these five replaces a mount point from index.html, and the markup carries that mount's
    // id so the next render finds it again. A mount that is missing is skipped rather than thrown
    // on: Arrange can hide a band, and a hidden band is not an error.
    if (['hero', 'index', 'place', 'loop', 'figures'].includes(id)) {
      const el = document.getElementById(id);
      if (el) el.outerHTML = html;
      if (id === 'index' && note) note.textContent = ctx.w.headlineRule;
      continue;
    }
    bands.insertAdjacentHTML('beforeend', html);
  }
  wireSatellites(document);
  if (ARRANGING) arrangeControls();
}

// ---------------------------------------------------------------------------------- the two wires
/* R6: motion is bound to the cadence of its own datum, and there are exactly two on this page.
 * The satellite's year, here, as a hard cut and never a morph; and the 120 ms fade when a reading
 * lands, which is in dashboard.css against --motion-reading-fade. Nothing else moves.
 */
const LOOPS = {};

/* The satellite frames, fetched once and kept.
 *
 * This is the ONE fetch outside snapshot(), and the contract at the top of this file names it. It
 * is not state — it is bytes, and the rule it obeys instead is the one the 7 MB forced: the loop
 * loads once and animates from memory. Node #1's nine AlphaEarth frames are ~780 kB each and the
 * four Sentinel ~320 kB; the page refreshes every 20 seconds and §2.7 budgets 60 kB per refresh, so
 * a frame that were part of a refresh would be four hundred times the budget, every twenty seconds,
 * for ever. Keyed by URL at module level, so a re-render hands the same <img> the same object URL
 * and nothing goes back to the node.
 *
 * A kiosk that RELOADS still pays the 7 MB again — a reload is a new document and a new module.
 * That is not solved here and is not solvable here; it wants a cache header on the node.
 */
const FRAMES = {};
const frameSrc = url => FRAMES[url] || (FRAMES[url] = fetch(url, { headers: auth_() })
  .then(r => (r.ok ? r.blob() : Promise.reject(new Error('HTTP ' + r.status))))
  .then(b => URL.createObjectURL(b))
  .catch(e => { delete FRAMES[url]; throw e; }));          // so a failure can be retried, not cached

/* Fill one <img>. The frame on screen goes first and the rest follow, so a nine-frame loop shows
 * its latest year immediately instead of after 7 MB. A frame that will not load says so on the
 * card rather than leaving the browser's broken-image glyph, which reads as a broken node. */
function loadFrames(el) {
  const imgs = [...el.querySelectorAll('.sat-loop img[data-src]')];
  const first = imgs.find(im => im.classList.contains('on')) || imgs[0];
  const one = im => frameSrc(im.dataset.src).then(u => { im.src = u; im.removeAttribute('data-src'); })
    .catch(() => {
      im.remove();
      if (!el.querySelector('.sat-loop img')) {
        const box = el.querySelector('.sat-loop');
        if (box) box.innerHTML = `<p class="note">The node has these frames and would not hand them `
          + `over. Unlock under Set up, or set SHARE_LEVEL to open.</p>`;
      }
    });
  if (!first) return Promise.resolve();
  return one(first).then(() => Promise.all(imgs.filter(im => im !== first).map(one)));
}

function wireSatellites(root) {
  root.querySelectorAll('[data-component="satellite"][data-frames]').forEach(el => {
    const id = el.dataset.id;
    if (LOOPS[id]) { clearInterval(LOOPS[id]); delete LOOPS[id]; }
    const frames = el.dataset.frames.split(',').filter(Boolean);
    loadFrames(el);
    const imgs = [...el.querySelectorAll('.sat-loop img')];
    const yr = el.querySelector('[data-sat="year"]');
    const sl = el.querySelector('[data-sat="slider"]');
    const play = el.querySelector('[data-sat="play"]');
    const mode = el.querySelector('[data-sat="mode"]');
    const st = { i: frames.length - 1, mode: 'years' };
    const show = () => {
      imgs.forEach(im => im.classList.toggle('on',
        st.mode === 'change' ? im.dataset.i === 'change' : +im.dataset.i === st.i));
      if (yr) yr.textContent = st.mode === 'change' ? 'what changed' : frames[st.i];
      if (sl) { sl.value = st.i; sl.disabled = st.mode === 'change'; }
      if (mode) mode.setAttribute('aria-pressed', String(st.mode === 'change'));
    };
    const stop = () => { if (LOOPS[id]) { clearInterval(LOOPS[id]); delete LOOPS[id]; } if (play) play.textContent = REDUCED ? 'motion off' : 'play'; };
    const run = () => {
      if (REDUCED) return;                       // stands on the latest year, and reads frozen
      st.mode = 'years';
      LOOPS[id] = setInterval(() => { st.i = (st.i + 1) % frames.length; show(); }, MOTION_YEAR());
      if (play) play.textContent = 'pause';
    };
    if (play) play.onclick = () => (LOOPS[id] ? stop() : run());
    if (sl) sl.oninput = () => { stop(); st.mode = 'years'; st.i = +sl.value; show(); };
    if (mode) mode.onclick = () => { stop(); st.mode = st.mode === 'change' ? 'years' : 'change'; show(); };
    show();
    if (frames.length > 1 && !el.closest('#setup')) run();
  });
}

// ------------------------------------------------------------------------------------- the buttons
/* Closing a loop. PR 5's fix is carried here rather than inherited: `prompt(…) || 'acted'` posted
 * the action even when somebody pressed Cancel, and ρ — the one number this project exists to
 * produce — went up for a dismissed dialog. Cancel now means cancel.
 */
async function act(id, btn) {
  const note = prompt('What did you do? (a few words)');
  if (note === null) return;                                    // Cancel means cancel
  const tok = tok_();
  if (!tok) {
    toast('This screen has no token, so it cannot record that. Reply /act ' + id + ' on Telegram, '
      + 'or run planetai ui on the node for a token that only closes loops.', true);
    return;
  }
  try {
    const r = await fetch('/actions', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'X-Agent': 'dashboard', ...auth_() },
      body: JSON.stringify({ alert_id: Number(id), stage: 'acted', note: note || 'acted' }),
    });
    if (!r.ok) throw new Error(String(r.status));
    if (btn) btn.replaceWith(Object.assign(document.createElement('span'),
      { className: 'done', textContent: 'noted · the ring closes' }));
  } catch (e) {
    toast('The node did not record that. Nothing was written; try again in a moment.', true);
  }
}

function toast(msg, bad) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.toggle('bad', !!bad);
  t.classList.add('on');
  setTimeout(() => t.classList.remove('on'), 4200);
}

// --------------------------------------------------------------------------------------- arrange
let ARRANGING = false;
async function loadLayout() {
  if (LAYOUT) return LAYOUT;
  // A fixture is a file, not a node: there is nowhere a saved arrangement could have come from, and
  // this was the one request that stopped `?fixture=` being renderable from the fixture alone —
  // which is the property a design round depends on. tools/shots.mjs counts any request it makes.
  if (FIXTURE) return (LAYOUT = { order: [], hidden: [] });
  try {
    const d = await fetch('/settings', { headers: auth_() }).then(r => r.json());
    const r = (d.runtime || []).find(x => x.key === 'UI_LAYOUT');
    LAYOUT = r && r.value ? JSON.parse(r.value) : { order: [], hidden: [] };
  } catch (e) { LAYOUT = { order: [], hidden: [] }; }
  return LAYOUT;
}
function arrangeControls() {
  document.querySelectorAll('[data-band]').forEach(el => {
    if (el.querySelector(':scope > .arr')) return;
    const id = el.dataset.band;
    const bar = document.createElement('div');
    bar.className = 'arr';
    bar.innerHTML = `<button type="button" data-move="-1" aria-label="Move up">←</button>`
      + `<button type="button" data-move="1" aria-label="Move down">→</button>`
      + `<button type="button" data-hide="1" aria-label="Hide">✕</button>`;
    bar.onclick = ev => {
      const b = ev.target.closest('button'); if (!b) return;
      const order = layout(LAST);
      if (b.dataset.hide) { LAYOUT.hidden = [...(LAYOUT.hidden || []), id]; }
      else {
        const i = order.indexOf(id), j = i + Number(b.dataset.move);
        if (j < 0 || j >= order.length) return;
        const next = [...order]; next.splice(j, 0, next.splice(i, 1)[0]);
        LAYOUT.order = next;
      }
      render(LAST, 'now');
    };
    el.prepend(bar);
  });
}
/* Reset writes the same empty UI_LAYOUT that Done writes, so it survives a reload instead of
 * coming back from the node on the next poll. (Improvement plan PR 5, D3.) */
async function layoutSave(reset) {
  LAYOUT = reset ? { order: [], hidden: [] } : LAYOUT;
  const tok = localStorage.getItem('planetai_admin');
  if (!tok) { toast('Arranging needs the admin token — unlock under Set up.', true); return; }
  try {
    await fetch('/settings', {
      method: 'PUT',
      headers: { 'content-type': 'application/json', authorization: 'Bearer ' + tok, 'X-Agent': 'dashboard' },
      body: JSON.stringify({ UI_LAYOUT: (LAYOUT.order.length || LAYOUT.hidden.length) ? JSON.stringify(LAYOUT) : '' }),
    });
    toast(reset ? 'Back to the default order.' : 'Saved on the node.');
  } catch (e) { toast('Could not save the layout.', true); }
  ARRANGING = false;
  document.getElementById('arrbar').hidden = true;
  document.querySelectorAll('.arr').forEach(el => el.remove());
  render(LAST, 'now');
}

// ------------------------------------------------------------------------------------------ views
function show(v) {
  if (v === 'arrange') {
    ARRANGING = true;
    document.getElementById('arrbar').hidden = false;
    show('now');
    return;
  }
  document.querySelectorAll('section.view').forEach(s => s.classList.toggle('on', s.id === v));
  document.querySelectorAll('nav.views button').forEach(b => b.classList.toggle('on', b.dataset.view === v));
  if (LAST) render(LAST, v);
  if (v === 'setup') loadSetup();
  window.scrollTo(0, 0);
}

// ------------------------------------------------------------------------------------------- boot
async function refresh() {
  LAST = await snapshot();
  const view = [...document.querySelectorAll('section.view')].find(s => s.classList.contains('on'));
  render(LAST, view ? view.id : 'now');
}

document.addEventListener('click', ev => {
  const nav = ev.target.closest('nav.views button, .wall .exit');
  if (nav) return show(nav.dataset.view);
  const a = ev.target.closest('[data-act]');
  if (a) return act(a.dataset.act, a);
  if (ev.target.id === 'btn-arr-reset') return layoutSave(true);
  if (ev.target.id === 'btn-arr-done') return layoutSave(false);
  if (ev.target.id === 'btn-back') return show('now');
  if (ev.target.id === 'btn-unlock') return unlock();
  if (ev.target.id === 'btn-save') return saveSettings();
});

(async function boot() {
  if (KIOSK) document.body.classList.add('kiosk');
  await loadLayout();
  await refresh();
  if (KIOSK || QS.get('theme') === 'dark') show('wall');
  setInterval(refresh, 20000);
})();

// ------------------------------------------------------------------------------------------ set up
/* Ported from the page this file replaces, with one pane added. Every group a setting claims must
 * have a pane here or a household cannot reach the setting at all — tests/test_settings.py reads
 * this object and fails when the two drift, which is how the issues group got here.
 */
/* What each settings group is called here and what it is for.
 *
 * A LOOKUP, not the list. The list of groups and their ORDER come from the node — `/settings` hands
 * back what `app/settings.py`'s RUNTIME declares, and `planetai config` reads the same rows in the
 * same order, so the terminal and this page walk the same menu. A group the node gains that nothing
 * here names still gets a tab, titled by its own name: before this, its keys were unreachable from
 * the dashboard and visible in the CLI, and nothing said so.
 */
const GROUPS = {
  issues: ['Issues', "What this place watches, in order. The first one is where the page starts; whichever has something to say takes the top of it. Your preset guessed from a map — change it. What matters here is decided by the people who live here."],
  sources: ['Sources', 'What the node reads: your sensors, your account, and the public references around you.'],
  alerts: ['Alerts', "Reports at the hours you choose, in this node's own time zone. Between them, only what you asked to be interrupted for."],
  packs: ['Packs', 'Which packs load. Code packs stay off until you allow them; read one before you do.'],
  integrations: ['Integrations', 'Home Assistant over MQTT, and the Reticulum bridge.'],
  keys: ['Keys', 'What packs need to reach outside services. Secrets are never shown again once saved.'],
  agent: ['Model', 'Which model answers the Telegram bot. The strongest reachable is used.'],
  node: ['The tree', 'Who this node reports to, and who may report to it.'],
  bootstrap: ['Bootstrap', 'Read once at start. Edit .env on the node and run planetai restart.'],
};
let GROUP = null, DESC = null, PACKS = [];

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
  || 'This node declares this group; nothing in the dashboard describes it yet. `planetai config` shows the same keys.';

const BOOLS = /^(BAD_ENABLED|OPENMETEO_ENABLED|SENSOR_INDOOR|MESH_ALERTS|HA_DISCOVERY|EXPORT_ENABLED|IPFS_PUBLISH|QUIET_HOURS|BAD_INCLUDE_INDOOR|PACKS_ALLOW_CODE)$/;

function unlock() {
  const t = document.getElementById('tok').value.trim();
  if (t) localStorage.setItem('planetai_admin', t);
  const a = document.getElementById('acttok').value.trim();
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
  document.getElementById('gate').hidden = unlocked;
  document.getElementById('setup-body').hidden = !unlocked;
  if (!unlocked) return;

  const groups = groupsOf(DESC);
  // A tab that was open when the node's groups changed under it, or a first load: take the first.
  if (!groups.includes(GROUP)) GROUP = groups[0] || null;
  if (!GROUP) { document.getElementById('pane').innerHTML = `<p class="note">This node declares no settings.</p>`; return; }
  document.getElementById('tabs').innerHTML = groups
    .map(g => `<button type="button" class="${g === GROUP ? 'on' : ''}" data-group="${esc(g)}">${esc(groupTitle(g))}</button>`).join('')
    + `<span class="acts"><button type="button" class="btn ghost" data-lock="1">Lock</button></span>`;
  document.getElementById('ptitle').textContent = groupTitle(GROUP);
  document.getElementById('pblurb').textContent = groupBlurb(GROUP);

  const pane = document.getElementById('pane');
  if (GROUP === 'bootstrap') {
    pane.innerHTML = (DESC.bootstrap || []).map(b =>
      `<div class="field"><div><label>${esc(b.label)}</label><div class="help">${esc(b.key)}</div></div>`
      + `<div><input type="text" readonly value="${esc(b.value || '')}" placeholder="not set"></div></div>`).join('');
    return;
  }
  if (GROUP === 'packs') {
    const enabled = ((DESC.runtime || []).find(r => r.key === 'PACKS_ENABLED') || {}).value || '';
    const only = enabled ? enabled.split(',').map(x => x.trim()) : null;
    pane.innerHTML = PACKS.map(p =>
      `<div class="pack"><button type="button" class="switch ${!only || only.includes(p.id) ? 'on' : ''}"`
      + ` data-pack="${esc(p.id)}"><span class="tr"></span></button>`
      + `<div><b>${esc(p.name || p.id)}</b> <span class="tag">${esc(p.kind)}</span>`
      + (p.domain ? ` <span class="tag">${esc(p.domain)}</span>` : '')
      + `<div class="help">${esc(p.description || '')}</div></div></div>`).join('');
    return;
  }
  const rows = (DESC.runtime || []).filter(r => r.group === GROUP);
  pane.innerHTML = rows.map(r => {
    const src = `<span class="src">${r.source === 'gui' ? 'set here · overrides .env' : r.source === 'env' ? 'from .env' : 'default'}</span>`;
    const left = `<div><label>${esc(r.label)}${src}</label><div class="help">${esc(r.help)}</div></div>`;
    if (BOOLS.test(r.key)) {
      return `<div class="field">${left}<div><button type="button" class="switch ${r.value === '1' ? 'on' : ''}"`
        + ` data-key="${esc(r.key)}" data-bool="1"><span class="tr"></span></button></div></div>`;
    }
    if (r.key === 'ALERT_LOCALE') {
      return `<div class="field">${left}<div><select data-key="${esc(r.key)}">`
        + [['en', 'English'], ['id', 'Bahasa Indonesia'], ['es', 'Español']].map(([v, l]) =>
          `<option value="${v}"${r.value === v ? ' selected' : ''}>${l}</option>`).join('')
        + `</select></div></div>`;
    }
    return `<div class="field">${left}<div><input data-key="${esc(r.key)}"`
      + (r.secret
        ? ` type="password" placeholder="${r.set ? 'Set — type to replace' : 'Not set'}"`
        : ` type="text" value="${esc(r.value)}"`)
      + ` autocomplete="off"></div></div>`;
  }).join('') || `<div class="empty">Nothing to set in this group.</div>`;
}

async function saveSettings() {
  const tok = localStorage.getItem('planetai_admin');
  const body = {};
  if (GROUP === 'packs') {
    const all = [...document.querySelectorAll('[data-pack]')];
    const on = all.filter(c => c.classList.contains('on')).map(c => c.dataset.pack);
    body.PACKS_ENABLED = on.length === all.length ? '' : on.join(',');
  } else {
    document.querySelectorAll('[data-key]').forEach(el => {
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
  if (r.status === 403) { toast('The node has no admin token yet — run planetai ui.', true); return; }
  toast(r.ok ? 'Saved. Live within about twenty seconds.' : 'Could not save (' + r.status + ').', !r.ok);
  if (r.ok) { loadSetup(); refresh(); }
}

// the Set up pane's own clicks: tabs, switches, lock
document.addEventListener('click', ev => {
  const g = ev.target.closest('[data-group]');
  if (g) { GROUP = g.dataset.group; return loadSetup(); }
  if (ev.target.closest('[data-lock]')) return lock();
  const sw = ev.target.closest('.switch');
  if (sw) sw.classList.toggle('on');
  const ly = ev.target.closest('[data-layer]');
  if (ly) {
    const k = ly.dataset.layer;
    PLAN_OFF.has(k) ? PLAN_OFF.delete(k) : PLAN_OFF.add(k);
    if (LAST) render(LAST, 'now');
  }
});
