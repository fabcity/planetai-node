#!/usr/bin/env node
/* measure.mjs — the node dashboard, measured from computed layout rather than looked at.
 *
 * ORIGIN. This file is the September UX review's skeleton script, moved into the repo it measures
 * and extended. It was written for Part 2 of that review and lived at
 * `planetai-design/design/audit/2026-09/ux-review/skeleton/measure.mjs` on branch
 * `ux-review-2026-09`; every number in `docs/design/UX_REVIEW_2026-09_skeleton.md` came out of it.
 * Everything above the `TARGETS` section is that script, unchanged except where marked. There is
 * one of these and there must stay one of these: a second measuring script is two sets of numbers
 * that can disagree about the same page.
 *
 * WHAT IS NEW HERE, and why each one exists:
 *   · the page under test is an argument, not a constant. `PAI_STATIC` points at any `app/static`
 *     tree and `PAI_PAGE` at a standalone HTML file, so the shipped page, a redesign branch and a
 *     drawing that happens to be HTML are all measured by the same code on the same day.
 *   · `PAI_OUT` puts the renders somewhere other than beside this file.
 *   · COLLECT also reads the attributes the redesign's targets are written in terms of —
 *     data-num, data-cmp, data-ref, data-kind, aria-hidden, the accessible name of an SVG — and
 *     records DOM order, which T6 is about.
 *   · `targets` computes T1-T7 per render and prints one table. A target with no script behind it
 *     is an opinion.
 *
 * Per render it writes three things:
 *
 *   <name>.json         every visible element: tag, role, data-component, box, margin/padding/gap,
 *                       font-size/weight/line-height, z-index, position; plus every text line box.
 *   <name>_wire.png     a wireframe on a blank ground: text as grey bars at its real line boxes,
 *                       images/canvases/SVGs hatched, controls outlined, nothing else.
 *   <name>_guides.png   the same drawing with a 1 px guide at every left edge three or more
 *                       elements share.
 *
 * Nothing is written to either container. Every request for `/static/*` and for the document
 * itself is intercepted and fulfilled from `PAI_STATIC`, so what is measured is that tree's page
 * against the containers' live API. The refused state is produced by fulfilling `/issues` with the
 * exact 403 body `app/main.py` builds at SHARE_LEVEL=off — no setting on either node is touched.
 *
 * Usage:
 *   node measure.mjs render <job>...      one or more job names (or "all")
 *   node measure.mjs steps                320 -> 1920 in 20 px steps on Now and Wall
 *   node measure.mjs stall <job>          layout with the API stalled, then released
 *   node measure.mjs sheets               contact sheet per view from the wireframes
 *   node measure.mjs header               the header's shape against the node's own name and place
 *   node measure.mjs targets              T1-T7 per render, against the targets table
 *   node measure.mjs audit <job>...       T9: bytes per refresh, axe, named SVGs, motion
 *   node measure.mjs shots <job>...       JPEG, one device pixel: the fold and the whole page
 *   node measure.mjs analyse <table>      grid spacing rhythm lines align type headings order
 *                                         dist wall dom anatomy components stack
 *   node measure.mjs list                 the job table
 *
 * Env: PAI_STATIC   the app/static tree to serve (default: this repo's)
 *      PAI_PAGE     a standalone HTML file to measure instead of a node page (Phase 1 directions)
 *      PAI_OUT      where renders are written (default: beside this file)
 *      PAI_DESIGN_REPO  where playwright is installed (default: ../planetai-design)
 *      PAI_ADMIN_TOKEN, PAI_ACT_TOKEN   the setup-unlocked and arrange jobs only.
 *      Never printed, never written to any output file.
 *
 * Playwright is a DEV dependency of the sibling design repo and not of this one: a node installs
 * this repository and must never be asked for a browser. So it is resolved by path, and a machine
 * without it is told rather than crashed at.
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const DESIGN = process.env.PAI_DESIGN_REPO || path.resolve(ROOT, '../planetai-design');
let chromium;
try {
  chromium = createRequire(path.join(DESIGN, 'package.json'))('playwright').chromium;
} catch (e) {
  console.error(`  - measure.mjs needs playwright, which is a dev dependency of ${DESIGN}\n`
    + `    (npm install there, or set PAI_DESIGN_REPO). Nothing was measured.`);
  process.exit(3);
}

/* The page under test. STATIC is the tree whose index.html, dashboard.js and dashboard.css are
 * served; PAGE overrides the document alone, for a drawing that carries its own everything. */
const STATIC = process.env.PAI_STATIC
  ? path.resolve(process.env.PAI_STATIC) : path.join(ROOT, 'app/static');
const PAGE = process.env.PAI_PAGE ? path.resolve(process.env.PAI_PAGE) : null;
const OUT = process.env.PAI_OUT ? path.resolve(process.env.PAI_OUT) : HERE;
fs.mkdirSync(OUT, { recursive: true });

const POP = 'http://127.0.0.1:8081';        // bootstrapped, SHARE_LEVEL=open
const EMPTY = 'http://127.0.0.1:8082';      // fresh install, BOOTSTRAP=0
const FIXTURE = process.env.PAI_FIXTURE || 'node1-2026-09-06';

// The node's own refusal, from app/main.py:744, for SHARE_LEVEL=off on /issues.
const REFUSAL = p => JSON.stringify({ error:
  `this node is set to SHARE_LEVEL=off, so ${p} answers only this machine or a request carrying a `
  + `token. Set SHARE_LEVEL to open in the dashboard's Set up view to let anything on your network `
  + `read it.` });

const MIME = { '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml',
  '.json': 'application/json', '.html': 'text/html', '.ttf': 'font/ttf', '.woff2': 'font/woff2' };

const WIDTHS = [375, 390, 768, 1440];
const VIEWS = ['now', 'network', 'setup', 'setup-unlocked', 'wall', 'arrange'];

/* ------------------------------------------------------------------ the job table */
function jobs() {
  const j = [];
  for (const v of VIEWS) for (const w of WIDTHS) j.push({ name: `${v}_populated_${w}`, view: v, w, state: 'populated' });
  j.push({ name: 'wall_populated_1920_dark', view: 'wall', w: 1920, state: 'populated', dark: true });
  for (const w of [390, 1440]) {
    j.push({ name: `now_empty_${w}`, view: 'now', w, state: 'empty', wireOnly: true });
    j.push({ name: `now_refused_${w}`, view: 'now', w, state: 'refused', wireOnly: true });
  }
  /* The live path, which is a different weight from the fixture path and is the one T9 is about.
   * `?fixture=` refetches the whole committed snapshot every refresh — one 75 kB file — where a
   * node makes thirteen small calls. Measuring only the fixture would report a budget failure the
   * household never pays, and measuring only the node would miss that a design round's own rig is
   * heavier than the thing it is reviewing. */
  for (const w of [390, 1440]) j.push({ name: `now_live_${w}`, view: 'now', w, state: 'live' });
  j.push({ name: 'wall_live_1920_dark', view: 'wall', w: 1920, state: 'live', dark: true });
  return j;
}

/* ------------------------------------------------------------------ the browser */
async function open(job) {
  const base = job.state === 'empty' ? EMPTY : POP;
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: job.w, height: job.w >= 1920 ? 1080 : 900 },
    deviceScaleFactor: 1, colorScheme: 'light', reducedMotion: 'reduce',
  });

  /* A drawing that happens to be HTML: one file, no fetch, no views to switch between. It is
   * opened from disk and measured by exactly the same COLLECT as a node page, which is the only
   * reason a direction's numbers can be set beside the shipped page's. */
  if (PAGE) {
    const page = await ctx.newPage();
    if (job.dark) await page.emulateMedia({ colorScheme: 'dark' });
    await page.goto('file://' + PAGE, { waitUntil: 'load' });
    if (job.dark) await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'dark'));
    await page.waitForTimeout(500);
    return { browser, page };
  }

  // Serve PAI_STATIC's tree for the document and every companion file.
  await ctx.route('**/*', async route => {
    const u = new URL(route.request().url());
    if (u.origin !== base) return route.continue();
    /* PAI_LIVE=1 measures what the container actually serves instead of the PAI_STATIC tree.
       Used to re-measure a finding against the code as shipped. */
    let file = null;
    if (process.env.PAI_LIVE !== '1') {
      if (u.pathname === '/' || u.pathname === '/index.html') file = 'index.html';
      else if (u.pathname.startsWith('/static/')) file = u.pathname.slice(8);
    }
    if (file) {
      const p = path.join(STATIC, file);
      if (fs.existsSync(p)) return route.fulfill({
        status: 200, body: fs.readFileSync(p),
        headers: { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' } });
    }
    if (job.state === 'refused' && !/^\/(static|health)/.test(u.pathname))
      return route.fulfill({ status: 403, contentType: 'application/json', body: REFUSAL(u.pathname) });
    return route.continue();
  });

  const page = await ctx.newPage();
  const q = [];
  if (job.state === 'populated') q.push(`fixture=${FIXTURE}`);   // 'live' reads the node itself
  if (job.dark) q.push('theme=dark');
  await page.goto(base + '/' + (q.length ? '?' + q.join('&') : ''), { waitUntil: 'networkidle' });

  // ?theme=dark boots straight to the wall and body.wallview hides the header, so there is no nav
  // button to press (Part 1, H9). Every other view is reached from the nav.
  const already = await page.evaluate(() => document.body.classList.contains('wallview'));
  const target = job.view.startsWith('setup') ? 'setup' : job.view;
  if (!(already && target === 'wall') && target !== 'now') await page.click(`button[data-view="${target}"]`);

  // Arrange needs no token to enter: the bar and the per-band controls render for anyone, and only
  // Done refuses (Part 1, A8). Set up does, and it is the only job that reads one.
  if (job.view === 'setup-unlocked') {
    const t = process.env.PAI_ADMIN_TOKEN;
    if (!t) throw new Error('PAI_ADMIN_TOKEN not set — needed for ' + job.view);
    await page.fill('#tok', t);
    await page.click('#btn-unlock');
    await page.waitForSelector('#setup-body:not([hidden])', { timeout: 10000 });
    // The pane opens on Issues, which is one field. Alerts is the widest form in the product —
    // eight inputs, two toggles and a select — and is what Part 1 shot. Measure that one.
    await page.getByRole('button', { name: 'Alerts', exact: true }).click();
    await page.waitForTimeout(400);
  }
  await page.waitForTimeout(1200);
  return { browser, page };
}

/* ------------------------------------------------------------------ the measurement */
const COLLECT = () => {
  const sx = window.scrollX, sy = window.scrollY;
  /* Cap height and ascent, measured from the rasterised face rather than assumed from a ratio.
     actualBoundingBoxAscent of "H" IS the cap height in px; fontBoundingBoxAscent puts the
     baseline under a line box's top. Memoised per font shorthand. */
  const _mc = document.createElement('canvas').getContext('2d'), _mm = new Map();
  const metrics = (fw, fs, ff) => {
    const key = `${fw} ${fs}px ${ff}`;
    if (_mm.has(key)) return _mm.get(key);
    _mc.font = key;
    const h = _mc.measureText('H'), x = _mc.measureText('x');
    const m = { cap: Math.round(h.actualBoundingBoxAscent * 100) / 100,
      xh: Math.round(x.actualBoundingBoxAscent * 100) / 100,
      asc: Math.round(h.fontBoundingBoxAscent * 100) / 100,
      desc: Math.round(h.fontBoundingBoxDescent * 100) / 100 };
    _mm.set(key, m); return m;
  };
  const CTRL = new Set(['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA', 'SUMMARY', 'LABEL']);
  const MEDIA = new Set(['SVG', 'CANVAS', 'IMG', 'VIDEO', 'PICTURE']);
  const els = [], lines = [];
  /* DOM order, which is what T6 compares position against. querySelectorAll is document order, so
   * the index a walk assigns IS the DOM order; it is recorded rather than reconstructed later,
   * because a later sort loses it. */
  let domIndex = 0;
  for (const el of document.querySelectorAll('*')) {
    domIndex++;
    const tag = el.tagName.toUpperCase();
    if (el.ownerSVGElement) continue;                    // svg internals draw as one hatched box
    if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'LINK' || tag === 'HEAD') continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    const n = v => Math.round(parseFloat(v) * 100) / 100 || 0;
    els.push({
      tag, id: el.id || null,
      cls: (el.getAttribute('class') || '').split(/\s+/).filter(Boolean).slice(0, 4).join(' ') || null,
      role: el.getAttribute('role') || null,
      dc: el.getAttribute('data-component') || null,
      db: el.getAttribute('data-band') || null,
      dcard: el.getAttribute('data-card') || null,
      /* The four attributes the redesign's targets are written in terms of. They are read here
       * whether or not the page under test carries any of them: the shipped page carries none, and
       * a baseline of zero is a measurement. T3 counts data-kind; T4 pairs data-num with
       * data-cmp; T5 pairs data-component with data-ref. */
      dkind: el.getAttribute('data-kind') || null,
      drole: el.getAttribute('data-role') || null,
      dnum: el.hasAttribute('data-num') ? (el.getAttribute('data-num') || '') : null,
      dcmp: el.hasAttribute('data-cmp') ? (el.getAttribute('data-cmp') || '') : null,
      dref: el.getAttribute('data-ref') || null,
      dom: domIndex,
      /* Whether an SVG names itself. T9 asks that every one is named or hidden; the shipped page
       * was measured on this by axe and this records it per element rather than per page. */
      named: tag === 'SVG'
        ? (el.getAttribute('aria-hidden') === 'true' ? 'hidden'
          : (el.getAttribute('aria-label') || el.querySelector(':scope > title') ? 'named' : 'no'))
        : null,
      /* Inherited, not own: the hero's ground is an <img> inside <div class="bg" aria-hidden>, so
       * asking the image alone says it carries a reading when the page has said it does not. */
      hidden: !!el.closest('[aria-hidden="true"]'),
      x: Math.round((r.x + sx) * 100) / 100, y: Math.round((r.y + sy) * 100) / 100,
      w: Math.round(r.width * 100) / 100, h: Math.round(r.height * 100) / 100,
      mt: n(cs.marginTop), mr: n(cs.marginRight), mb: n(cs.marginBottom), ml: n(cs.marginLeft),
      pt: n(cs.paddingTop), pr: n(cs.paddingRight), pb: n(cs.paddingBottom), pl: n(cs.paddingLeft),
      rg: n(cs.rowGap), cg: n(cs.columnGap),
      fs: n(cs.fontSize), fw: cs.fontWeight, lh: cs.lineHeight === 'normal' ? 'normal' : n(cs.lineHeight),
      ff: (cs.fontFamily || '').split(',')[0].replace(/["']/g, ''),
      z: cs.zIndex, pos: cs.position, disp: cs.display,
      br: cs.borderRadius, minh: cs.minHeight,
      bw: [cs.borderTopWidth, cs.borderRightWidth, cs.borderBottomWidth, cs.borderLeftWidth]
        .map(v => Math.round(parseFloat(v) * 100) / 100 || 0).join(' '),
      gtc: cs.gridTemplateColumns && cs.gridTemplateColumns !== 'none' ? cs.gridTemplateColumns : null,
      kind: MEDIA.has(tag) ? 'media' : CTRL.has(tag) || el.getAttribute('role') === 'button' ? 'control' : 'box',
      depth: (() => { let d = 0, p = el; while ((p = p.parentElement)) d++; return d; })(),
      kids: el.children.length,
      hasText: [...el.childNodes].some(c => c.nodeType === 3 && c.nodeValue.trim()),
    });
  }
  // text line boxes, from the real ranges
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const t = walker.currentNode, s = (t.nodeValue || '').replace(/\s+/g, ' ').trim();
    if (!s) continue;
    const p = t.parentElement; if (!p) continue;
    const cs = getComputedStyle(p);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
    const range = document.createRange(); range.selectNodeContents(t);
    const rects = [...range.getClientRects()].filter(r => r.width > 0 && r.height > 0);
    if (!rects.length) continue;
    // characters per line: exact for a wrapping block, by finding the break offsets
    let cpl = null;
    if (rects.length > 1 && s.length >= 40) {
      cpl = []; let last = 0, line = 0;
      for (let i = 1; i <= t.nodeValue.length; i++) {
        const rr = document.createRange();
        rr.setStart(t, i - 1); rr.setEnd(t, i);
        const b = rr.getClientRects()[0]; if (!b) continue;
        const which = rects.findIndex(x => b.top >= x.top - 1 && b.bottom <= x.bottom + 1);
        if (which > line) { cpl.push(i - 1 - last); last = i - 1; line = which; }
      }
      cpl.push(t.nodeValue.length - last);
      cpl = cpl.map(c => Math.max(0, c));
    }
    const _fs = parseFloat(cs.fontSize);
    const _m = metrics(cs.fontWeight, _fs, cs.fontFamily);
    for (const r of rects) lines.push({
      x: Math.round((r.x + sx) * 100) / 100, y: Math.round((r.y + sy) * 100) / 100,
      w: Math.round(r.width * 100) / 100, h: Math.round(r.height * 100) / 100,
      cap: _m.cap, base: Math.round((r.y + sy + _m.asc) * 100) / 100,
      fs: Math.round(_fs * 100) / 100, fw: cs.fontWeight,
      lh: cs.lineHeight === 'normal' ? 'normal' : Math.round(parseFloat(cs.lineHeight) * 100) / 100,
      ff: (cs.fontFamily || '').split(',')[0].replace(/["']/g, ''),
      tt: cs.textTransform, chars: s.length, nlines: rects.length, cpl,
      owner: (p.tagName + (p.id ? '#' + p.id : '') + (p.className && typeof p.className === 'string' ? '.' + p.className.split(/\s+/)[0] : '')),
      text: s.slice(0, 90),
    });
  }
  // the accessibility heading outline, as the browser sees it
  const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6,[role="heading"]')]
    .filter(h => h.getBoundingClientRect().height > 0)
    .map(h => ({ lvl: +(h.getAttribute('aria-level') || h.tagName[1] || 0), tag: h.tagName,
      fs: parseFloat(getComputedStyle(h).fontSize), y: Math.round(h.getBoundingClientRect().y + sy),
      text: (h.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 70) }));
  const landmarks = [...document.querySelectorAll('header,nav,main,section,footer,aside,form,[role]')]
    .filter(l => l.getBoundingClientRect().height > 0)
    .map(l => ({ tag: l.tagName, role: l.getAttribute('role'), id: l.id || null,
      label: l.getAttribute('aria-label') || null }));
  return {
    doc: { w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight,
      vw: innerWidth, vh: innerHeight },
    els, lines, headings, landmarks,
  };
};

/* ------------------------------------------------------------------ the drawing */
function wireHTML(data, guides) {
  const { doc, els, lines } = data;
  const edges = guides ? sharedEdges(els) : [];
  const parts = [];
  for (const e of els) {
    if (e.kind === 'media') parts.push(
      `<i class="hatch" style="left:${e.x}px;top:${e.y}px;width:${e.w}px;height:${e.h}px"></i>`);
    else if (e.kind === 'control') parts.push(
      `<i class="ctrl" style="left:${e.x}px;top:${e.y}px;width:${e.w}px;height:${e.h}px"></i>`);
  }
  for (const l of lines) {
    const h = Math.max(2, Math.min(l.h * 0.62, l.fs * 0.72));
    parts.push(`<i class="bar" style="left:${l.x}px;top:${l.y + (l.h - h) / 2}px;width:${l.w}px;height:${h}px"></i>`);
  }
  for (const x of edges) parts.push(`<i class="guide" style="left:${x}px;height:${doc.h}px"></i>`);
  return `<!doctype html><meta charset="utf-8"><style>
  html,body{margin:0;padding:0;background:#fff}
  body{width:${doc.w}px;height:${doc.h}px;position:relative}
  i{position:absolute;display:block}
  .bar{background:#b4b4b4}
  .ctrl{border:1px solid #222;background:transparent}
  .hatch{border:1px solid #555;background:repeating-linear-gradient(45deg,#00000014 0 4px,#0000 4px 8px)}
  .guide{width:1px;top:0;background:#e0322f;opacity:.85}
  </style><body>${parts.join('')}</body>`;
}

function sharedEdges(els) {
  const c = new Map();
  for (const e of els) { const k = Math.round(e.x); c.set(k, (c.get(k) || 0) + 1); }
  return [...c.entries()].filter(([, n]) => n >= 3).map(([x]) => x).sort((a, b) => a - b);
}

async function draw(browser, data, file, guides) {
  const p = await browser.newPage({ viewport: { width: Math.min(data.doc.w, 2000), height: 900 },
    deviceScaleFactor: 1 });
  await p.setContent(wireHTML(data, guides), { waitUntil: 'load' });
  await p.screenshot({ path: file, fullPage: true });
  await p.close();
}

/* ------------------------------------------------------------------ commands */
async function render(names) {
  const all = jobs();
  const want = names[0] === 'all' ? all : all.filter(j => names.includes(j.name));
  if (!want.length) { console.error('no such job:', names.join(' ')); process.exit(2); }
  for (const j0 of want) {
    // A live render measures different code, so it must never land on a v0.52 filename.
    const job = process.env.PAI_LIVE === '1' ? { ...j0, name: j0.name + '_live' } : j0;
    let h;
    try {
      h = await open(job);
      const data = await h.page.evaluate(COLLECT);
      data.job = { ...job, commit: '43d508d', fixture: job.state === 'populated' ? FIXTURE : null };
      if (!job.wireOnly) fs.writeFileSync(path.join(OUT, job.name + '.json'), JSON.stringify(data));
      await draw(h.browser, data, path.join(OUT, job.name + '_wire.png'), false);
      if (!job.wireOnly) await draw(h.browser, data, path.join(OUT, job.name + '_guides.png'), true);
      const sf = path.join(OUT, 'sizes.json');
      const sizes = fs.existsSync(sf) ? JSON.parse(fs.readFileSync(sf, 'utf8')) : {};
      sizes[job.name] = { w: data.doc.w, h: data.doc.h };
      fs.writeFileSync(sf, JSON.stringify(sizes, null, 1));
      console.log(`${job.name}  doc ${data.doc.w}x${data.doc.h}  els ${data.els.length}  lines ${data.lines.length}`);
    } catch (e) {
      console.error(`${job.name}  FAILED  ${e.message}`);
    } finally { if (h) await h.browser.close(); }
  }
}

/* Phase 1.3 — step the viewport and record every width at which the skeleton changes. */
async function steps() {
  const out = {};
  for (const view of ['now', 'wall']) {
    const job = { name: view, view, w: 1440, state: 'populated' };
    const h = await open(job);
    const rows = [];
    for (let w = 320; w <= 1920; w += 20) {
      await h.page.setViewportSize({ width: w, height: view === 'wall' ? 1080 : 900 });
      await h.page.waitForTimeout(70);
      rows.push({ w, ...await h.page.evaluate(() => {
        /* Only a RENDERED grid has resolved px tracks. On a hidden view getComputedStyle returns
           the specified value ("minmax(0, 1.5fr) minmax(0, 1fr)"), which counts as four tokens and
           reads as a phantom breakpoint. Rendered or nothing. */
        const cols = sel => {
          const e = document.querySelector(sel);
          if (!e || !e.getClientRects().length) return null;
          const v = getComputedStyle(e).gridTemplateColumns;
          return /px/.test(v) ? v.split(' ').filter(Boolean).length : null;
        };
        const wrap = document.querySelector('.view.on .wrap') || document.querySelector('.wall');
        const wr = wrap ? wrap.getBoundingClientRect() : null;
        const bands = [...document.querySelectorAll('[data-band],.band,.hero')]
          .filter(b => b.getBoundingClientRect().height > 0)
          .map(b => (b.getAttribute('data-band') || b.id || b.className.split(' ')[0]));
        const head = document.querySelector('header .wrap');
        return {
          hero: cols('.hero'), stack: cols('.stack'), sensors: cols('.sensors'),
          idx: cols('.index .row'), setup: cols('.setup'), row2: cols('.wall .row2'),
          cellrow: cols('.cellrow'), askstrip: cols('.askstrip'), unit: cols('.unit'),
          ledger: cols('.ledger .al'), bandhead: cols('.bandhead'),
          net: document.querySelector('svg.net') ? getComputedStyle(document.querySelector('svg.net')).display : null,
          headH: head ? Math.round(head.getBoundingClientRect().height) : null,
          headWrap: head ? (head.scrollHeight > head.clientHeight + 2 ? 'wrapped' : 'one-row') : null,
          brandS: document.querySelector('.brand .s') ? getComputedStyle(document.querySelector('.brand .s')).display : null,
          wrapW: wr ? Math.round(wr.width) : null, wrapX: wr ? Math.round(wr.x) : null,
          docH: document.documentElement.scrollHeight,
          bands: bands.join(','),
        };
      }) });
    }
    out[view] = rows;
    await h.browser.close();
  }
  fs.writeFileSync(path.join(OUT, 'steps.json'), JSON.stringify(out));
  // report only the widths where something changed
  for (const [view, rows] of Object.entries(out)) {
    const keys = Object.keys(rows[0]).filter(k => k !== 'w' && k !== 'docH' && k !== 'wrapW' && k !== 'wrapX');
    console.log(`\n--- ${view} ---`);
    for (let i = 1; i < rows.length; i++) {
      const ch = keys.filter(k => rows[i][k] !== rows[i - 1][k]);
      if (ch.length) console.log(`${rows[i].w}px  ` + ch.map(k => `${k}: ${rows[i - 1][k]} -> ${rows[i][k]}`).join('; '));
    }
  }
}

/* Phase 6.5 — layout with /issues stalled, then released. */
async function stall(name) {
  const job = jobs().find(j => j.name === name) || { name, view: 'now', w: 1440, state: 'populated' };
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: job.w, height: 900 },
    deviceScaleFactor: 1, reducedMotion: 'reduce' });
  let release;
  const gate = new Promise(r => { release = r; });
  await ctx.route('**/*', async route => {
    const u = new URL(route.request().url());
    if (u.origin !== POP) return route.continue();
    // PAI_LIVE=1 measures what the container serves, exactly as `render` does
    let file = null;
    if (process.env.PAI_LIVE !== '1') {
      if (u.pathname === '/' || u.pathname === '/index.html') file = 'index.html';
      else if (u.pathname.startsWith('/static/')) file = u.pathname.slice(8);
    }
    if (file) {
      const p = path.join(STATIC, file);
      if (fs.existsSync(p)) return route.fulfill({ status: 200, body: fs.readFileSync(p),
        headers: { 'content-type': MIME[path.extname(p)] || 'application/octet-stream' } });
    }
    // the document and its companions are not API calls and must not wait on the gate
    if (process.env.PAI_LIVE === '1' && (u.pathname === '/' || /^\/static\//.test(u.pathname)))
      return route.continue();
    await gate;                       // every API call waits
    return route.continue();
  });
  const page = await ctx.newPage();
  await page.goto(POP + `/?fixture=${FIXTURE}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);
  const before = await page.evaluate(BOXES);
  release();
  await page.waitForTimeout(2500);
  const after = await page.evaluate(BOXES);
  const moved = [];
  for (const [k, v] of Object.entries(before)) if (after[k]) {
    const d = Math.round(Math.abs(after[k].y - v.y));
    if (d > 0) moved.push({ el: k, before: Math.round(v.y), after: Math.round(after[k].y), dy: d });
  }
  const out = { job: job.name, before, after, moved: moved.sort((a, b) => b.dy - a.dy),
    beforeH: before.__docH, afterH: after.__docH };
  const suffix = process.env.PAI_LIVE === '1' ? '_live' : '';
  fs.writeFileSync(path.join(OUT, `stall_${job.name}${suffix}.json`), JSON.stringify(out));
  console.log(`doc height ${before.__docH} -> ${after.__docH}`);
  for (const m of moved.slice(0, 20)) console.log(`  ${m.el}: y ${m.before} -> ${m.after}  (${m.dy} px)`);
  await browser.close();
}
const BOXES = () => {
  const o = { __docH: document.documentElement.scrollHeight };
  for (const el of document.querySelectorAll('header,nav,main,section[id],.hero,.index,#bands,#place,#loop,#figures,.band')) {
    const r = el.getBoundingClientRect(); if (!r.height) continue;
    const k = el.tagName + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.split(/\s+/)[0] : '');
    if (!o[k]) o[k] = { y: r.y + scrollY, h: r.height };
  }
  return o;
};

/* The header's shape against the node's own data (S-11).
 *
 * The header is a wrapping flex row, so it reflows where the CONTENT stops fitting, not at a width
 * anything declares. That makes its shape a function of the node's name and place string. This
 * steps 320 -> 1400 in 10 px steps for several node shapes and reports the widths at which the row
 * structure changes, and which of those changes make the header TALLER as the viewport widens.
 *
 * The name and place are set on the rendered page rather than on the node: they are the two strings
 * a node's own config supplies, and nothing on either container is touched.
 */
const HEADER_CASES = [
  ['node #1, as the fixture ships it', null, null],
  ["node #1's registry place, 37 chars", null, 'Ungasan, Badung, Bali, ID · community'],
  ['a long place line, 51 chars', null, 'Kelurahan Ungasan, Kabupaten Badung, Bali, Indonesia'],
  ['a very long place line, 78 chars', null,
    'Banjar Kelod, Kelurahan Ungasan, Kecamatan Kuta Selatan, Kabupaten Badung, Bali'],
  ['a longer node name', 'meaningful-design-rooftop', 'Ungasan, Badung, Bali, ID · community'],
  ['both long', 'meaningful-design-group-rooftop',
    'Kelurahan Ungasan, Kabupaten Badung, Bali, Indonesia'],
];
const HEADER_SHAPE = () => {
  const wrap = document.querySelector('header .wrap');
  const kids = [...wrap.children].map(e => {
    const b = e.getBoundingClientRect(); return { top: b.top, bot: b.bottom };
  });
  const lines = [];
  for (const k of kids.sort((a, b) => a.top - b.top)) {
    const l = lines.find(L => k.top < L.bot - 2 && k.bot > L.top + 2);
    if (l) { l.top = Math.min(l.top, k.top); l.bot = Math.max(l.bot, k.bot); } else lines.push({ ...k });
  }
  return { rows: lines.length, h: Math.round(wrap.getBoundingClientRect().height) };
};
async function header() {
  const browser = await chromium.launch();
  const rows = [];
  for (const [label, name, place] of HEADER_CASES) {
    const p = await browser.newPage({ viewport: { width: 1920, height: 900 }, deviceScaleFactor: 1 });
    await p.goto(POP + `/?fixture=${FIXTURE}`, { waitUntil: 'networkidle' });
    await p.waitForTimeout(1400);
    const place_ = await p.evaluate(([n, pl]) => {
      if (n) { const h = document.querySelector('.brand h1, #nodename'); if (h) h.textContent = n; }
      const s = document.getElementById('nodeplace');
      if (pl) s.textContent = pl;
      return { px: Math.round(s.getBoundingClientRect().width),
        clipped: s.scrollWidth > s.clientWidth, text: s.textContent.length };
    }, [name, place]);
    const flips = [], grew = [];
    let prev = null;
    for (let w = 320; w <= 1400; w += 10) {
      await p.setViewportSize({ width: w, height: 900 });
      await p.waitForTimeout(40);
      const r = await p.evaluate(HEADER_SHAPE);
      const key = `${r.rows}/${r.h}`;
      if (prev && key !== prev) {
        flips.push(w);
        if (r.h > +prev.split('/')[1]) grew.push(w);
      }
      prev = key;
    }
    rows.push([label, place_.text, place_.px + (place_.clipped ? ' clipped' : ''),
      flips.join(' ') || 'none', grew.join(' ') || '—']);
    await p.close();
  }
  console.log(tbl(['node', 'place chars', 'place px', 'the header reflows at', 'and grows at'], rows));
  await browser.close();
}

/* Contact sheet: one view at every measured width, side by side, at ONE scale so the widths can
 * be compared as widths. Drawn from the wireframes, not the screenshots. */
async function sheets() {
  const browser = await chromium.launch();
  const sizes = JSON.parse(fs.readFileSync(path.join(OUT, 'sizes.json'), 'utf8'));
  for (const v of VIEWS) {
    const names = WIDTHS.map(w => `${v}_populated_${w}`)
      .concat(v === 'wall' ? ['wall_populated_1920_dark'] : [])
      .filter(n => fs.existsSync(path.join(OUT, n + '_wire.png')));
    if (!names.length) continue;
    const sw = names.reduce((a, n) => a + sizes[n].w, 0);
    const mh = Math.max(...names.map(n => sizes[n].h));
    const sc = Math.min(2300 / sw, 4600 / mh);
    const html = `<!doctype html><meta charset="utf-8"><style>
      body{margin:0;background:#efefef;font:11px/1.4 ui-monospace,monospace;display:flex;gap:12px;
        padding:12px;align-items:flex-start}
      figure{margin:0;background:#fff;border:1px solid #999}
      img{display:block;width:100%}figcaption{padding:4px 6px;border-top:1px solid #999}
      </style><body>${names.map(n => `<figure style="flex:0 0 ${Math.round(sizes[n].w * sc)}px">`
        + `<img src="${n}_wire.png"><figcaption>${n} — ${sizes[n].w} x ${Math.round(sizes[n].h)} px`
        + ` (drawn at ${(sc * 100).toFixed(0)} %)</figcaption></figure>`).join('')}</body>`;
    const f = path.join(OUT, `_sheet_${v}.html`);
    fs.writeFileSync(f, html);
    const p = await browser.newPage({ viewport: { width: 2400, height: 900 }, deviceScaleFactor: 1 });
    await p.goto('file://' + f, { waitUntil: 'load' });
    await p.screenshot({ path: path.join(OUT, `${v}_contact.png`), fullPage: true });
    await p.close();
    fs.unlinkSync(f);
    console.log(`${v}_contact.png  ${names.length} widths at ${(sc * 100).toFixed(0)} %`);
  }
  await browser.close();
}

/* ======================================================================== ANALYSE
 * Every table in UX_REVIEW_2026-09_skeleton.md comes out of one of these. They read the JSON the
 * render step wrote and print a markdown table; nothing here touches the browser or the node.
 */
const VIEW_ORDER = ['now', 'network', 'setup', 'setup-unlocked', 'wall', 'arrange'];
const load = n => JSON.parse(fs.readFileSync(path.join(OUT, n + '.json'), 'utf8'));
const sets = () => fs.readdirSync(OUT)
  .filter(f => /_populated_\d+\.json$/.test(f) && !f.startsWith('stall_'))
  .map(f => f.replace(/\.json$/, ''))
  .sort((a, b) => {
    const [va, wa] = [a.replace(/_populated_.*/, ''), +a.match(/(\d+)/)[1]];
    const [vb, wb] = [b.replace(/_populated_.*/, ''), +b.match(/(\d+)/)[1]];
    return VIEW_ORDER.indexOf(va) - VIEW_ORDER.indexOf(vb) || wa - wb;
  });
const r1 = v => Math.round(v * 10) / 10;
const tbl = (head, rows) => [`| ${head.join(' | ')} |`,
  `|${head.map(() => '---').join('|')}|`, ...rows.map(r => `| ${r.join(' | ')} |`)].join('\n');
const has = (e, c) => e.cls && e.cls.split(' ').includes(c);
const pick = (d, c) => d.els.filter(e => has(e, c));
const one = (d, c) => pick(d, c)[0] || null;

/* 1.1 / 1.4 — the grid as rendered */
function aGrid() {
  const rows = [];
  for (const n of sets()) {
    const d = load(n), view = n.replace(/_populated_.*/, ''), w = +n.match(/(\d+)$/)[1];
    // the wall has no .wrap: it is its own padded box, so that is the container to measure
    const wraps = pick(d, 'wrap').filter(e => e.h > 0);
    const body = view === 'wall' ? d.els.find(e => has(e, 'wall') && e.tag === 'DIV')
      : (wraps.find(e => e.y > 40) || wraps[0]);
    const hdr = d.els.find(e => e.tag === 'HEADER');
    const main = d.els.find(e => e.tag === 'MAIN');
    // the view's primary grid
    const prim = { now: '.hero', network: '.grid', setup: '.gate', 'setup-unlocked': '.setup',
      wall: '.row2', arrange: '.hero' }[view];
    const g = d.els.find(e => has(e, prim.replace('.', '')) && e.gtc);
    const tracks = g ? g.gtc.split(/\s+(?![^(]*\))/).filter(Boolean) : [];
    rows.push([view, w,
      g ? tracks.length : '—',
      g ? tracks.map(t => Math.round(parseFloat(t))).join(' + ') : '—',
      g ? r1(g.cg) : '—',
      body ? r1(body.x + body.pl) : '—',
      body ? r1(body.w - body.pl - body.pr) : '—',
      hdr ? `${r1(hdr.h)} ${hdr.pos}` : '—',
      main ? r1(main.y) : '—',
      r1(d.doc.h)]);
  }
  console.log(tbl(['view', 'width', 'cols', 'track px', 'gutter', 'left margin', 'content w',
    'header h/pos', 'main top', 'doc h'], rows));
}

/* 2.1 — the spacing histogram */
function aSpacing(perView) {
  const all = new Map(), byView = new Map();
  const where = new Map();                     // value -> set of "view .class prop"
  for (const n of sets()) {
    const d = load(n), view = n.replace(/_populated_.*/, '');
    const m = byView.get(view) || new Map(); byView.set(view, m);
    for (const e of d.els) for (const [k, v] of [['mt', e.mt], ['mr', e.mr], ['mb', e.mb], ['ml', e.ml],
      ['pt', e.pt], ['pr', e.pr], ['pb', e.pb], ['pl', e.pl], ['rg', e.rg], ['cg', e.cg]]) {
      if (!v) continue;
      const val = Math.round(v * 10) / 10;
      all.set(val, (all.get(val) || 0) + 1); m.set(val, (m.get(val) || 0) + 1);
      const key = `${e.cls || e.tag.toLowerCase()}·${k}`;
      if (!where.has(val)) where.set(val, new Set());
      if (where.get(val).size < 6) where.get(val).add(key);
    }
  }
  const on4 = v => Math.abs(v - Math.round(v / 4) * 4) < 0.01;
  const vals = [...all.entries()].sort((a, b) => a[0] - b[0]);
  const off = vals.filter(([v]) => !on4(v));
  console.log(`distinct values: ${vals.length}; on the 4 pt measure: ${vals.length - off.length}; off it: ${off.length}`);
  console.log(`instances: ${[...all.values()].reduce((a, b) => a + b, 0)}, of which off-measure: ${off.reduce((a, b) => a + b[1], 0)}`);
  console.log('\n**Every distinct value, and how often it appears**\n');
  console.log(tbl(['px', 'n', 'on 4 pt', 'where (first few)'],
    vals.map(([v, n]) => [v, n, on4(v) ? '✓' : '✗', [...(where.get(v) || [])].join(', ')])));
  if (perView) {
    console.log('\n**Per view**\n');
    console.log(tbl(['view', 'distinct', 'off-measure distinct', 'off-measure instances'],
      [...byView.entries()].map(([v, m]) => {
        const vs = [...m.entries()], o = vs.filter(([x]) => !on4(x));
        return [v, vs.length, o.length, o.reduce((a, b) => a + b[1], 0)];
      })));
  }
}

/* 2.2 — the recurring vertical relationships */
function aRhythm() {
  const rel = new Map();
  const add = (name, view, w, px, what) => {
    const k = name; if (!rel.has(k)) rel.set(k, []);
    rel.get(k).push({ view, w, px: Math.round(px * 10) / 10, what });
  };
  for (const n of sets()) {
    const d = load(n), view = n.replace(/_populated_.*/, ''), w = +n.match(/(\d+)$/)[1];
    const by = c => pick(d, c);
    // band to band: the gap between one .band's bottom and the next .band's top
    const bands = d.els.filter(e => has(e, 'band') || has(e, 'hero')).sort((a, b) => a.y - b.y);
    for (let i = 1; i < bands.length; i++) {
      const g = bands[i].y - (bands[i - 1].y + bands[i - 1].h);
      if (g >= 0 && g < 200) add('band to band (box gap)', view, w, g, `${bands[i - 1].cls} -> ${bands[i].cls}`);
      // the real separation is the next band's own padding-top, not a margin between boxes
      add('band to band (the next band pads itself)', view, w, bands[i].pt, bands[i].id || bands[i].cls);
    }
    // kicker (.k) to the title/sentence under it, inside the same parent box
    for (const box of [...by('hero'), ...by('bandhead'), ...by('wall')]) {
      const k = d.els.find(e => has(e, 'k') && e.y >= box.y && e.y < box.y + box.h && e.x >= box.x);
      const big = d.els.find(e => has(e, 'big') && e.y > (k ? k.y : -1) && e.y < box.y + box.h);
      if (k && big) add('kicker to sentence', view, w, big.y - (k.y + k.h), box.cls);
      // only when the two stack: in a .bandhead above 900 the sub sits in column two, beside the
      // title, and the vertical distance between them is not a rhythm at all
      const why = d.els.find(e => has(e, 'why') && big && e.y > big.y && e.y < box.y + box.h
        && Math.abs(e.x - big.x) < 2);
      if (big && why) add('sentence to why', view, w, why.y - (big.y + big.h), box.cls);
    }
    // why/body to the source line under it
    for (const col of by('col')) {
      const v = d.els.find(e => has(e, 'v') && e.y >= col.y && e.y < col.y + col.h);
      const src = d.els.find(e => has(e, 'src') && e.y >= col.y && e.y < col.y + col.h);
      if (v && src) add('value to source line', view, w, src.y - (v.y + v.h), 'stack .col');
    }
    // card to card in a row
    const cards = by('card').concat(by('sensor')).sort((a, b) => a.y - b.y || a.x - b.x);
    for (let i = 1; i < cards.length; i++)
      if (Math.abs(cards[i].y - cards[i - 1].y) < 2) {
        const g = cards[i].x - (cards[i - 1].x + cards[i - 1].w);
        if (g >= 0 && g < 120) add('card to card in a row', view, w, g, cards[i].cls);
      }
    // hero to index
    const hero = one(d, 'hero'), idx = one(d, 'index');
    if (hero && idx) add('hero to index', view, w, idx.y - (hero.y + hero.h), '');
  }
  for (const [name, xs] of rel) {
    const vals = [...new Set(xs.map(x => x.px))].sort((a, b) => a - b);
    console.log(`\n**${name}** — ${vals.length} distinct value${vals.length === 1 ? '' : 's'}: ${vals.join(', ')} px`);
    const byVal = new Map();
    for (const x of xs) { const k = x.px; if (!byVal.has(k)) byVal.set(k, []); byVal.get(k).push(`${x.view}@${x.w}${x.what ? ' ' + x.what : ''}`); }
    console.log(tbl(['px', 'n', 'occurrences (first 5)'],
      [...byVal.entries()].sort((a, b) => a[0] - b[0])
        .map(([v, o]) => [v, o.length, o.slice(0, 5).join('; ')])));
  }
}

/* 2.3 — line length and line height on every wrapping block */
function aLines() {
  const rows = [];
  for (const n of sets()) {
    const d = load(n), view = n.replace(/_populated_.*/, ''), w = +n.match(/(\d+)$/)[1];
    const seen = new Set();
    for (const l of d.lines) {
      if (!l.cpl || l.cpl.length < 2) continue;
      const key = view + w + l.owner + l.text.slice(0, 20);
      if (seen.has(key)) continue; seen.add(key);
      const mx = Math.max(...l.cpl), md = Math.round(l.cpl.reduce((a, b) => a + b, 0) / l.cpl.length);
      const floor = w <= 560 ? [35, 60] : [60, 75];
      const lh = l.lh === 'normal' ? null : Math.round(l.lh / l.fs * 100) / 100;
      /* The brief scopes line-height to running prose: sentences, why-paragraphs, help lines and
         the report. A kicker, a chip, a numeral and a display sentence are not body text and a
         1.5 floor does not apply to them. */
      const PROSE = /\.(why|sub|help|note|rep|line|txt|story)\b/;
      const DISPLAY = /\.(big|k|chip|num|mono|state|iss|lab|t|yr|tally|pill|src|cap|when|st)\b/;
      const prose = !DISPLAY.test(l.owner)
        && (PROSE.test(l.owner) || /^(P|TD|LI)$/.test(l.owner.split('.')[0].split('#')[0]));
      rows.push([view, w, l.owner, l.cpl.length, md, mx,
        mx > floor[1] ? `over ${floor[1]}` : md < floor[0] ? `under ${floor[0]}` : 'in band',
        l.fs, lh === null ? 'normal' : lh,
        !prose ? 'n/a — not prose' : lh !== null && (lh < 1.5 || lh > 1.75) ? '✗' : '✓',
        l.text.slice(0, 44)]);
    }
  }
  console.log(tbl(['view', 'w', 'block', 'lines', 'med cpl', 'max cpl', 'line-length-control',
    'px', 'lh', 'line-height', 'text'], rows));
}

/* 3 — alignment */
function aAlign() {
  for (const n of sets()) {
    const d = load(n), view = n.replace(/_populated_.*/, ''), w = +n.match(/(\d+)$/)[1];
    const c = new Map();
    for (const e of d.els) { const k = Math.round(e.x); c.set(k, (c.get(k) || 0) + 1); }
    const shared = [...c.entries()].filter(([, k]) => k >= 3).sort((a, b) => b[1] - a[1]);
    if (!shared.length) { console.log(`\n### ${view} @ ${w} — no edge shared by three`); continue; }
    const dom = shared[0];
    console.log(`\n### ${view} @ ${w} — dominant left edge **${dom[0]} px** (${dom[1]} elements); ${shared.length} edges shared by three or more`);
    console.log('edges: ' + shared.sort((a, b) => a[0] - b[0]).map(([x, k]) => `${x}(${k})`).join(' '));
    // near-misses: an element within 12 px of the dominant edge but not on it
    const near = d.els.filter(e => { const dx = e.x - dom[0]; return dx !== 0 && Math.abs(dx) > 2 && Math.abs(dx) <= 12; })
      .map(e => [`${e.tag}${e.id ? '#' + e.id : ''}${e.cls ? '.' + e.cls.split(' ')[0] : ''}`,
        r1(e.x), r1(e.x - dom[0])]);
    if (near.length) {
      const byEl = new Map();
      for (const [k, x, dx] of near) if (!byEl.has(k)) byEl.set(k, [x, dx]);
      console.log('\n' + tbl(['element', 'actual x', 'delta from dominant'],
        [...byEl.entries()].map(([k, [x, dx]]) => [k, x, (dx > 0 ? '+' : '') + dx])));
    }
  }
}

/* 4.1 — the type scale actually in use */
function aType() {
  const combos = new Map();
  for (const n of sets()) {
    const d = load(n);
    for (const l of d.lines) {
      const lh = l.lh === 'normal' ? 'normal' : Math.round(l.lh * 10) / 10;
      const k = `${l.fs}|${l.fw}|${lh}|${l.ff}`;
      if (!combos.has(k)) combos.set(k, { fs: l.fs, fw: l.fw, lh, ff: l.ff, n: 0, who: new Set() });
      const c = combos.get(k); c.n++; if (c.who.size < 5) c.who.add(l.owner);
    }
  }
  const rows = [...combos.values()].sort((a, b) => b.fs - a.fs || a.fw - b.fw)
    .map(c => [c.fs, c.fw, c.lh, c.ff, c.n, [...c.who].join(', ')]);
  console.log(`**${rows.length} distinct size x weight x line-height x family combinations.**\n`);
  console.log(tbl(['px', 'weight', 'line-height', 'family', 'instances', 'on (first few)'], rows));
  // sizes that carry more than one weight, and weights that carry more than one size
  const bySize = new Map();
  for (const c of combos.values()) {
    if (!bySize.has(c.fs)) bySize.set(c.fs, new Set());
    bySize.get(c.fs).add(c.fw + '/' + c.ff);
  }
  console.log('\n**One size, more than one meaning**\n');
  console.log(tbl(['px', 'weight/family combinations on it'],
    [...bySize.entries()].filter(([, s]) => s.size > 1).sort((a, b) => b[0] - a[0])
      .map(([fs, s]) => [fs, [...s].join(', ')])));
}

/* 4.2 — heading outline as the browser sees it, against the visual outline */
function aHeadings() {
  for (const n of sets()) {
    const d = load(n), view = n.replace(/_populated_.*/, ''), w = +n.match(/(\d+)$/)[1];
    if (w !== 1440 && w !== 390) continue;
    const big = d.lines.filter(l => l.fs >= 20).sort((a, b) => a.y - b.y)
      .map(l => ({ y: Math.round(l.y), fs: l.fs, tag: l.owner.split('.')[0].split('#')[0], text: l.text.slice(0, 46) }));
    console.log(`\n### ${view} @ ${w}`);
    console.log('a11y outline: ' + (d.headings.length
      ? d.headings.map(h => `h${h.lvl}@${h.y} "${h.text.slice(0, 34)}"`).join(' · ') : '**none**'));
    console.log('\n' + tbl(['y', 'px', 'element', 'reads as a title'],
      big.slice(0, 14).map(b => [b.y, b.fs, b.tag,
        d.headings.some(h => Math.abs(h.y - b.y) < 40) ? 'yes — is a heading' : '**div/p, not a heading**'])));
  }
}

/* 4.3 / 4.4 — reading order and weight in the first viewport */
function aOrder() {
  for (const n of sets()) {
    const d = load(n), view = n.replace(/_populated_.*/, ''), w = +n.match(/(\d+)$/)[1];
    if (view !== 'now' || (w !== 390 && w !== 1440)) continue;
    const vh = d.doc.vh;
    const fold = d.els.filter(e => e.y < vh && e.y + e.h > 0 && e.w * e.h > 400);
    const named = fold.filter(e => e.hasText || e.kind !== 'box' || e.dc);
    const dom = named.map((e, i) => ({ ...e, dom: i }));
    // by position means the way a reader meets it: rows first, then left to right inside a row.
    // A two-pixel difference in y between two things on the same line is not an order.
    const bypos = [...dom].sort((a, b) => (Math.abs(a.y - b.y) <= 8 ? a.x - b.x : a.y - b.y));
    console.log(`\n### Now @ ${w} — the first ${vh} px, ${fold.length} elements`);
    console.log(tbl(['by position', 'element', 'DOM order', 'diverges'],
      bypos.slice(0, 16).map((e, i) => [i + 1,
        `${e.tag}${e.id ? '#' + e.id : ''}${e.cls ? '.' + e.cls.split(' ')[0] : ''} (${r1(e.y)})`,
        e.dom + 1, i === e.dom ? '' : '**yes**'])));
    /* Area clipped to the fold, and scaffold dropped: a box whose area is within 15 % of a box it
       contains is that box's wrapper, not a mark on the screen. */
    const ca = e => Math.max(0, Math.min(vh, e.y + e.h) - Math.max(0, e.y)) * Math.min(e.w, w);
    const SCAFFOLD = e => ['HTML', 'BODY', 'MAIN'].includes(e.tag)
      || has(e, 'wrap') || (e.tag === 'SECTION' && has(e, 'view'));
    const cand = fold.map((e, i) => ({ ...e, ca: ca(e), i })).sort((a, b) => b.ca - a.ca);
    const area = cand.filter(e => !SCAFFOLD(e) && !cand.some(o => o.i > e.i && o.ca >= e.ca * 0.85
      && o.x >= e.x - 1 && o.y >= e.y - 1
      && o.x + o.w <= e.x + e.w + 1 && o.y + o.h <= e.y + e.h + 1)).slice(0, 8);
    console.log('\n**Top elements by pixel area in the first viewport**\n');
    console.log(tbl(['element', 'w x h', 'px²', 'share of fold'],
      area.map(e => [`${e.tag}${e.id ? '#' + e.id : ''}${e.cls ? '.' + e.cls.split(' ')[0] : ''}`,
        `${r1(e.w)} x ${r1(e.h)}`, Math.round(e.ca),
        (100 * e.ca / (w * vh)).toFixed(1) + '%'])));
    // the largest piece of TEXT in the fold
    const t = d.lines.filter(l => l.y < vh).sort((a, b) => b.fs - a.fs)[0];
    if (t) console.log(`\nLargest type in the fold: **${t.fs} px** ${t.fw} on ${t.owner} — "${t.text.slice(0, 50)}"`);
  }
}

/* 5.1 / 5.2 / 5.3 — distribution and density */
function aDist() {
  const rows = [], dens = [];
  for (const n of [...sets(), 'wall_populated_1920_dark']) {
    const d = load(n), view = n.replace(/_populated_.*/, '') + (/dark/.test(n) ? ' (dark)' : '');
    const w = d.doc.vw;
    const vh = d.doc.vh, foldPx = w * vh;
    const hdr = d.els.find(e => e.tag === 'HEADER');
    const hero = one(d, 'hero');
    const idx = one(d, 'index');
    const firstBand = d.els.filter(e => has(e, 'band') && e.h > 0).sort((a, b) => a.y - b.y)[0];
    const clip = e => e ? Math.max(0, Math.min(vh, e.y + e.h) - Math.max(0, e.y)) * Math.min(e.w, w) : 0;
    /* Marked ground is the UNION of what is drawn, not the sum: a text line inside a bordered
       control is one mark, not two. Rasterised on a 4 px grid over the first viewport. */
    const G = 4, gw = Math.ceil(w / G), gh = Math.ceil(vh / G), grid = new Uint8Array(gw * gh);
    const mark = (x, y, ww, hh) => {
      for (let gy = Math.max(0, Math.floor(y / G)); gy < Math.min(gh, Math.ceil((y + hh) / G)); gy++)
        for (let gx = Math.max(0, Math.floor(x / G)); gx < Math.min(gw, Math.ceil((x + ww) / G)); gx++)
          grid[gy * gw + gx] = 1;
    };
    for (const l of d.lines) if (l.y < vh) mark(l.x, l.y, l.w, l.h);
    for (const e of d.els) if (e.y < vh && (e.kind === 'media' || e.kind === 'control')) mark(e.x, e.y, e.w, e.h);
    const ink = grid.reduce((a, b) => a + b, 0) * G * G;
    rows.push([view, w, (100 * clip(hdr) / foldPx).toFixed(1), (100 * clip(hero) / foldPx).toFixed(1),
      (100 * clip(idx) / foldPx).toFixed(1), (100 * clip(firstBand) / foldPx).toFixed(1),
      (100 * (1 - ink / foldPx)).toFixed(1)]);
    const words = d.lines.filter(l => l.y < vh).reduce((a, l) => a + l.text.split(/\s+/).length, 0);
    dens.push([view, w, d.els.filter(e => e.y < vh).length,
      (1000 * d.els.filter(e => e.y < vh).length / foldPx).toFixed(3), words,
      d.els.length, r1(d.doc.h), (1000 * d.els.length / (w * d.doc.h)).toFixed(3)]);
  }
  console.log('**5.1 — the first viewport, share of its pixels**\n');
  console.log(tbl(['view', 'w', 'header %', 'hero %', 'index %', 'first band %', 'unmarked ground %'], rows));
  console.log('\n**5.3 — density**\n');
  console.log(tbl(['view', 'w', 'els in fold', 'els / 1000 px² (fold)', 'words in fold',
    'els on page', 'doc h', 'els / 1000 px² (page)'], dens));
  // 5.2 band share of the whole page
  console.log('\n**5.2 — what each band takes of the whole page**\n');
  for (const w of [390, 1440]) {
    const d = load(`now_populated_${w}`);
    const bands = d.els.filter(e => has(e, 'band') || has(e, 'hero') || has(e, 'index'))
      .filter(e => e.h > 0).sort((a, b) => a.y - b.y);
    console.log(`\nNow @ ${w} — page ${r1(d.doc.h)} px\n`);
    console.log(tbl(['order', 'band', 'top', 'height', '% of page'],
      bands.map((b, i) => [i + 1, `${b.id ? '#' + b.id : ''}.${(b.cls || '').split(' ')[0]}`,
        r1(b.y), r1(b.h), (100 * b.h / d.doc.h).toFixed(1)])));
  }
}

/* 5.4 — the wall, measured in millimetres */
function aWall() {
  const d = load('wall_populated_1920_dark');
  const MM = 0.63;                            // 1 px at 1920 on a 55-inch 16:9 panel
  const seen = new Set(), rows = [];
  for (const l of d.lines.sort((a, b) => b.cap - a.cap)) {
    const k = l.owner + l.fs; if (seen.has(k)) continue; seen.add(k);
    const mm = l.cap * MM;
    rows.push([l.owner, l.fs, l.cap, mm.toFixed(1), (mm / 3).toFixed(1),
      mm >= 9 ? '✓ 3 m' : mm >= 6 ? `only ${(mm / 3).toFixed(1)} m` : `**only ${(mm / 3).toFixed(1)} m**`,
      l.text.slice(0, 40)]);
  }
  console.log('1920 px wide on a 55-inch 16:9 panel: 1 px = 0.63 mm. The floor is 3 mm of cap height per metre of viewing distance, so 9 mm at three metres.\n');
  console.log(tbl(['element', 'font px', 'cap px', 'cap mm', 'max distance m', 'at 3 m', 'text'], rows));
}

/* 6.1 — the DOM skeleton */
function aDom() {
  const rows = [];
  for (const n of sets()) {
    const d = load(n), view = n.replace(/_populated_.*/, ''), w = +n.match(/(\d+)$/)[1];
    if (w !== 1440) continue;
    const depth = Math.max(...d.els.map(e => e.depth));
    // a wrapper with no layout role: one child, no text of its own, no grid/flex, no border, no padding
    /* A wrapper with no layout role: one child, no text of its own, no grid or flex, no border,
       no padding, not positioned — and not a drawing. An <svg> with one <use> in it is a mark,
       not a box around something. */
    const wrap = d.els.filter(e => e.kind !== 'media' && e.kind !== 'control'
      && e.kids === 1 && !e.hasText && !/grid|flex/.test(e.disp)
      && e.bw === '0 0 0 0' && !e.pt && !e.pb && !e.pl && !e.pr && e.pos === 'static');
    console.log(`\n### ${view} @ ${w}`);
    console.log(`landmarks: ${d.landmarks.filter(l => ['HEADER', 'NAV', 'MAIN', 'FOOTER', 'ASIDE', 'FORM'].includes(l.tag))
      .map(l => l.tag.toLowerCase() + (l.id ? '#' + l.id : '') + (l.label ? ` "${l.label}"` : '')).join(', ') || '**none**'}`);
    console.log(`sections: ${d.landmarks.filter(l => l.tag === 'SECTION').length} · roles: ${[...new Set(d.landmarks.filter(l => l.role).map(l => l.role))].join(', ') || '—'}`);
    console.log(`elements ${d.els.length} · deepest nesting ${depth} · wrappers with no layout role **${wrap.length}**`);
    if (wrap.length) console.log('  ' + wrap.slice(0, 10).map(e => `${e.tag}${e.cls ? '.' + e.cls.split(' ')[0] : ''}@${Math.round(e.y)}`).join(' '));
  }
}

/* 6.2 — the anatomy actually rendered.
 * Ancestry is reconstructed from DOM order + depth: the parent of the element at index i is the
 * nearest earlier element with depth one less. That is exact, and it is the only way to tell a
 * component that BELONGS to a band from one that merely overlaps it on screen. */
function aAnatomy() {
  for (const n of sets()) {
    const d = load(n), view = n.replace(/_populated_.*/, ''), w = +n.match(/(\d+)$/)[1];
    if (w !== 1440) continue;
    const parent = new Array(d.els.length).fill(-1);
    const stack = [];
    d.els.forEach((e, i) => {
      while (stack.length && d.els[stack[stack.length - 1]].depth >= e.depth) stack.pop();
      parent[i] = stack.length ? stack[stack.length - 1] : -1;
      stack.push(i);
    });
    const bandOf = i => { let k = i; while (k >= 0) { const e = d.els[k];
      if (e.db) return e.db;
      if (e.id === 'wallbox' || e.id === 'netbody' || e.id === 'pane') return e.id;
      k = parent[k]; } return '(loose)'; };
    const byBand = new Map();
    d.els.forEach((e, i) => { if (!e.dc) return;
      const b = bandOf(parent[i] >= 0 ? parent[i] : i);
      if (!byBand.has(b)) byBand.set(b, []); byBand.get(b).push(e.dc); });
    console.log(`\n### ${view} @ ${w} — every data-component, in DOM order, by the band that owns it\n`);
    console.log(tbl(['band', 'rendered'], [...byBand.entries()].map(([k, v]) => [k, v.join(' → ')])));
  }
}

/* 6.3 — one component, measured in every view it appears in */
function aComponents() {
  const want = ['pill', 'chip', 'unit', 'card', 'k', 'stamp', 'sensor', 'num', 'btn', 'peer', 'tag'];
  const m = new Map();
  for (const n of sets()) {
    const d = load(n), view = n.replace(/_populated_.*/, ''), w = +n.match(/(\d+)$/)[1];
    if (w !== 1440) continue;
    for (const e of d.els) for (const c of want) if (has(e, c)) {
      const k = c + '|' + view;
      if (!m.has(k)) m.set(k, { c, view, n: 0, pad: new Set(), fs: new Set(), br: new Set(), h: new Set(), bw: new Set() });
      const r = m.get(k); r.n++;
      r.pad.add(`${e.pt} ${e.pr} ${e.pb} ${e.pl}`);
      r.fs.add(e.fs); r.br.add(e.br); r.h.add(Math.round(e.h)); r.bw.add(e.bw);
    }
  }
  const byC = new Map();
  for (const r of m.values()) { if (!byC.has(r.c)) byC.set(r.c, []); byC.get(r.c).push(r); }
  const rows = [];
  for (const [c, rs] of byC) {
    if (rs.length < 2) continue;
    for (const r of rs) rows.push([`.${c}`, r.view, r.n, [...r.pad].join(' / '),
      [...r.fs].join(', '), [...r.br].join(', '), [...r.h].sort((a, b) => a - b).join(', '),
      [...r.bw].join(' / ')]);
    const pads = new Set(rs.flatMap(r => [...r.pad])), fss = new Set(rs.flatMap(r => [...r.fs]));
    rows.push([`**.${c}**`, `**${rs.length} views**`, '', pads.size > 1 ? `**${pads.size} paddings**` : 'one padding',
      fss.size > 1 ? `**${fss.size} sizes**` : 'one size', '', '', '']);
  }
  console.log(tbl(['component', 'view', 'n', 'padding t r b l', 'font px', 'radius', 'heights', 'border w'], rows));
}

/* 6.4 — stacking */
function aStack() {
  const z = new Map(), rows = [];
  for (const n of sets()) {
    const d = load(n), view = n.replace(/_populated_.*/, ''), w = +n.match(/(\d+)$/)[1];
    for (const e of d.els) {
      if (e.z === 'auto' && e.pos === 'static') continue;
      const k = `${e.tag}${e.id ? '#' + e.id : ''}${e.cls ? '.' + e.cls.split(' ')[0] : ''}|${e.pos}|${e.z}`;
      if (!z.has(k)) z.set(k, { views: new Set(), pos: e.pos, zi: e.z, el: k.split('|')[0] });
      z.get(k).views.add(`${view}@${w}`);
    }
  }
  console.log('**Every positioned element and every z-index in use**\n');
  console.log(tbl(['element', 'position', 'z-index', 'seen in'],
    [...z.values()].sort((a, b) => (a.zi === 'auto' ? -1 : +a.zi) - (b.zi === 'auto' ? -1 : +b.zi))
      .map(v => [v.el, v.pos, v.zi, [...v.views].slice(0, 6).join(', ') + (v.views.size > 6 ? ` +${v.views.size - 6}` : '')])));
  // overlaps between positioned elements and ordinary content
  console.log('\n**Overlaps**\n');
  for (const n of sets()) {
    const d = load(n), view = n.replace(/_populated_.*/, ''), w = +n.match(/(\d+)$/)[1];
    const fixed = d.els.filter(e => e.pos === 'fixed' || e.pos === 'sticky');
    for (const f of fixed) {
      // its own children sit inside its box by definition; only content it covers counts
      const inside = e => e.x >= f.x && e.y >= f.y && e.x + e.w <= f.x + f.w && e.y + e.h <= f.y + f.h;
      const over = d.els.filter(e => e !== f && e.pos === 'static' && e.hasText && !inside(e)
        && e.x < f.x + f.w && e.x + e.w > f.x && e.y < f.y + f.h && e.y + e.h > f.y);
      if (over.length) rows.push([`${view}@${w}`,
        `${f.tag}${f.id ? '#' + f.id : ''}${f.cls ? '.' + f.cls.split(' ')[0] : ''} (${f.pos}, z ${f.z})`,
        over.length, over.slice(0, 3).map(e => `${e.tag}${e.cls ? '.' + e.cls.split(' ')[0] : ''}`).join(', ')]);
    }
  }
  console.log(rows.length ? tbl(['render', 'positioned element', 'elements under it', 'which'], rows)
    : 'no sticky or fixed element overlaps text at any measured width.');
}

/* ======================================================================== TARGETS
 * T1-T7 of the September redesign, each computed from the same JSON every table above reads.
 *
 * A target with no script behind it is an opinion, and the three complaints this redesign answers
 * — too much empty space, data not understandable, everything disconnected — are exactly the three
 * that sound like moods until somebody measures them. So: T2 is the empty share of the first
 * viewport, T4 is numerals with nothing to compare them to, T5 is components with no link in or
 * out. The other four are the reading they depend on.
 *
 * ROLES is the one place a target names a part of the page. A direction is a drawing and the
 * shipped page is a renderer, and both have to be measured by the same code, so each role is a
 * list of selectors tried in order and the table says which one answered. A role nothing answers
 * is reported as absent rather than skipped: the shipped page carries no data-kind at all, and
 * that zero is the baseline T3 is measured against.
 */
const ROLES = {
  sentence: ['[data-component="sentence"]', '[data-role="sentence"]', '.hero p.big', '.wall p.big'],
  numeral: ['[data-component="sentence"] b.mono', '[data-role="numeral"]', '.hero p.big b', '.wall p.big b'],
  state: ['[data-component="kicker"] .state', '[data-role="state"]', '.hero .k .state', '.wall .k .state'],
  ask: ['[data-component="askStrip"]', '[data-role="ask"]', '.askstrip'],
  asof: ['[data-role="asof"]', '.asof', '#headprov .asof', '.wall .foot'],
  index: ['[data-component="index"]', '[data-role="index"]', '#index', '.index'],
  indexRow: ['[data-component="indexRow"]', '[data-role="index-row"]', '.index .row'],
  miniStack: ['[data-component="miniStack"]', '[data-role="mini-stack"]', '.stack.mini'],
  wallIssueLine: ['[data-component="wallIndex"] .ln', '[data-role="wall-issue"]', '.wall .wi .ln'],
  /* The readable part of the rho row is its caption: the row itself is a texture of signs, and
   * a sign is measured against --sign-floor, not against a cap height. */
  rho: ['[data-role="rho"]', '.rhocap', '[data-component="rhoRow"]'],
};

/* Does any element in `d` match this role, and is its box inside the first viewport?
 * Selectors are matched against what COLLECT recorded — tag, id, class, data-component,
 * data-role — rather than re-queried in a browser, so a target is answerable from a committed
 * JSON months after the render. Only the shapes ROLES actually uses are supported, and an
 * unsupported one throws rather than quietly matching nothing. */
function matches(e, sel) {
  const M = sel.match(/^\[data-component="([^"]+)"\](?:\s+(.+))?$/);
  if (M) {
    if (M[2]) return false;             // a descendant selector: handled by the caller's own pass
    return e.dc === M[1];
  }
  const R = sel.match(/^\[data-role="([^"]+)"\]$/);
  if (R) return e.drole === R[1];
  const parts = sel.trim().split(/\s+/);
  const last = parts[parts.length - 1];
  const bits = last.match(/^([a-z0-9]+)?((?:[.#][A-Za-z0-9_-]+)*)$/i);
  if (!bits) throw new Error('measure.mjs: ROLES selector not supported: ' + sel);
  if (bits[1] && e.tag !== bits[1].toUpperCase()) return false;
  for (const b of (bits[2] || '').match(/[.#][A-Za-z0-9_-]+/g) || []) {
    if (b[0] === '#' && e.id !== b.slice(1)) return false;
    if (b[0] === '.' && !has(e, b.slice(1))) return false;
  }
  return true;
}
function role(d, name) {
  for (const sel of ROLES[name]) {
    const hit = d.els.filter(e => matches(e, sel));
    if (hit.length) return { sel, els: hit };
  }
  return { sel: null, els: [] };
}
const inFold = (e, d) => e.y < d.doc.vh && e.y + e.h > 0;
const yes = b => (b ? '✓' : '**✗**');

function aTargets() {
  const names = fs.readdirSync(OUT).filter(f => /\.json$/.test(f) && !/^stall_|^sizes/.test(f))
    .map(f => f.replace(/\.json$/, ''));
  const rows = [];
  for (const n of names.sort()) {
    const d = load(n);
    const w = d.doc.vw, vh = d.doc.vh;
    const wall = /wall/.test(n);

    /* T1 — is the first screen the whole answer? The sentence with its numeral, the state word,
     * the ask (or the words standing in for one), and when this was last true. */
    const sent = role(d, 'sentence'), num = role(d, 'numeral'), st = role(d, 'state');
    const ask = role(d, 'ask'), asof = role(d, 'asof');
    const t1 = {
      sentence: sent.els.some(e => inFold(e, d)),
      numeral: num.els.some(e => inFold(e, d)),
      state: st.els.some(e => inFold(e, d)),
      ask: ask.els.some(e => inFold(e, d) && e.h > 0),
      asof: asof.els.some(e => inFold(e, d)),
    };
    if (w >= 1440 && !wall) {
      t1.index = role(d, 'indexRow').els.filter(e => inFold(e, d)).length;
      t1.mini = role(d, 'miniStack').els.some(e => inFold(e, d));
    }

    /* T2 — the empty share of the first viewport, and the whole page in viewports.
     * Marked ground is the UNION of what is drawn, rasterised on a 4 px grid: a line of text
     * inside a bordered box counts once. This is 5.1's own measure, reused verbatim. */
    const grids = { lit: null, read: null };
    for (const which of ['lit', 'read']) {
      const G = 4, gw = Math.ceil(w / G), gh = Math.ceil(vh / G), grid = new Uint8Array(gw * gh);
      const mark = (x, y, ww, hh) => {
        for (let gy = Math.max(0, Math.floor(y / G)); gy < Math.min(gh, Math.ceil((y + hh) / G)); gy++)
          for (let gx = Math.max(0, Math.floor(x / G)); gx < Math.min(gw, Math.ceil((x + ww) / G)); gx++)
            grid[gy * gw + gx] = 1;
      };
      for (const l of d.lines) if (l.y < vh) mark(l.x, l.y, l.w, l.h);
      for (const e of d.els) {
        if (e.y >= vh || !(e.kind === 'media' || e.kind === 'control')) continue;
        /* Two readings, because the literal target has a loophole worth naming. T2 counts a pixel
         * as full if it sits inside anything carrying "text, a mark, a sign, an image or a
         * control", and a decorative full-bleed background IS an image — so a page can pass T2 by
         * putting a picture behind everything and saying nothing. `lit` is the target as written;
         * `read` drops what the page itself has marked aria-hidden, which is the page's own
         * statement that the mark carries no reading. Both are reported; a gap between them is a
         * page whose emptiness is being filled by decoration. */
        if (which === 'read' && e.hidden) continue;
        mark(e.x, e.y, e.w, e.h);
      }
      grids[which] = 100 * (1 - grid.reduce((a, b) => a + b, 0) * 16 / (w * vh));
    }
    const empty = grids.lit, emptyRead = grids.read;
    const screens = d.doc.h / vh;

    /* T3 — how many card kinds the whole interface has. Four, named and counted. */
    const kinds = [...new Set(d.els.map(e => e.dkind).filter(Boolean))].sort();

    /* T4 — no orphan numeral. `nums` is what the page DECLARES as a numeral; `drawn` is what a
     * reader actually meets, so a page carrying no data-num at all reports 0 of 0 declared against
     * a real count, rather than a clean zero that means nothing was looked at. */
    const nums = d.els.filter(e => e.dnum !== null);
    const orphanNums = nums.filter(e => e.dcmp === null);
    const drawn = d.els.filter(e => has(e, 'num') || (e.tag === 'B' && has(e, 'mono'))).length;

    /* T5 — no orphan component. A link out is this component's own data-ref naming an id on the
     * page; a link in is somebody else's data-ref naming an id inside this component. Only the
     * header and the hero may stand alone. */
    const ids = new Set(d.els.map(e => e.id).filter(Boolean));
    const refs = d.els.map(e => e.dref).filter(Boolean);
    const comps = d.els.filter(e => e.dc && !['header', 'hero'].includes(e.dc));
    const orphanComps = comps.filter(c => {
      const out = c.dref && ids.has(c.dref.replace(/^#/, ''));
      const mine = new Set(d.els.filter(e => e.id && e.x >= c.x - 1 && e.y >= c.y - 1
        && e.x + e.w <= c.x + c.w + 1 && e.y + e.h <= c.y + c.h + 1).map(e => e.id));
      const into = refs.some(r => mine.has(r.replace(/^#/, '')));
      return !(out || into);
    });

    /* T6 — reading order = DOM order in the first viewport. Rows first, then left to right inside
     * a row; eight pixels of difference in y is the same line, not an order. */
    const fold = d.els.filter(e => inFold(e, d) && e.w * e.h > 400)
      .filter(e => e.hasText || e.kind !== 'box' || e.dc);
    const byDom = [...fold].sort((a, b) => a.dom - b.dom);
    const byPos = [...fold].sort((a, b) => (Math.abs(a.y - b.y) <= 8 ? a.x - b.x : a.y - b.y));
    const diverge = byPos.filter((e, i) => byDom[i] !== e).length;

    /* T7 — the wall at three metres. 1 px = 0.63 mm at 1920 on a 55-inch 16:9 panel; the floor is
     * about 3 mm of cap height per metre, so 9 mm. */
    let t7 = '—';
    if (wall && w >= 1920) {
      const MM = 0.63;
      const want = [['sentence', sent], ['numeral', num], ['issue line', role(d, 'wallIssueLine')],
        ['rho row', role(d, 'rho')]];
      const parts = [];
      for (const [label, r] of want) {
        const caps = d.lines.filter(l => r.els.some(e => l.x >= e.x - 2 && l.x <= e.x + e.w + 2
          && l.y >= e.y - 2 && l.y + l.h <= e.y + e.h + 2)).map(l => l.cap * MM);
        if (!caps.length) { parts.push(`${label} **absent**`); continue; }
        const lo = Math.min(...caps);
        parts.push(`${label} ${lo.toFixed(1)}${lo < 9 ? ' **' : ' '}mm${lo < 9 ? '**' : ''}`);
      }
      t7 = parts.join('; ');
    }

    rows.push([n, w,
      `${yes(t1.sentence)}${yes(t1.numeral)}${yes(t1.state)}${yes(t1.ask)}${yes(t1.asof)}`
        + (t1.index === undefined ? '' : ` · idx ${t1.index} ${yes(t1.mini)}`),
      empty.toFixed(1) + ' / ' + emptyRead.toFixed(1) + ' %', screens.toFixed(1),
      kinds.length ? `${kinds.length}: ${kinds.join(' ')}` : '**0**',
      `${orphanNums.length} / ${nums.length} (${drawn} drawn)`,
      `${orphanComps.length} / ${comps.length}`,
      diverge, t7]);
  }
  console.log('T1 is sentence·numeral·state·ask·as-of in the first viewport (and at 1440 the index '
    + 'rows and the mini stack). T2 is the empty share of the first viewport and the page in '
    + 'viewports, counting every image as a mark (lit) and again ignoring aria-hidden '
    + 'decoration (read). T3 is distinct data-kind. T4 is [data-num] with no [data-cmp]. T5 is '
    + '[data-component] with no [data-ref] in or out. T6 is position-order divergences from DOM '
    + 'order. T7 is cap height at 1920 dark.\n');
  console.log(tbl(['render', 'w', 'T1', 'T2 empty lit/read', 'T2 screens', 'T3 kinds', 'T4 orphan nums',
    'T5 orphan comps', 'T6 diverge', 'T7 wall'], rows));
}

/* The renders themselves. A wireframe is what a measurement looks like; this is what a person
 * looks at, and the rule for this round is that nothing is claimed to render that was not seen in
 * one. JPEG at one device pixel, the same as every capture in the September review, so a shot from
 * this round can be set beside one from that one.
 *
 * `full` shoots the whole document; without it the shot is the first viewport, which is the thing
 * T1 and T2 are about.
 */
async function shots(names) {
  const all = jobs();
  const want = names[0] === 'all' ? all : all.filter(j => names.includes(j.name));
  if (!want.length) { console.error('no such job:', names.join(' ')); process.exit(2); }
  for (const job of want) {
    let h;
    try {
      h = await open(job);
      for (const full of [false, true]) {
        const f = path.join(OUT, `${job.name}${full ? '_full' : '_fold'}.jpg`);
        await h.page.screenshot({ path: f, fullPage: full, type: 'jpeg', quality: 82 });
        console.log(`  ${path.basename(f)}  ${(fs.statSync(f).size / 1024).toFixed(0)} kB`);
      }
    } catch (e) {
      console.error(`${job.name}  FAILED  ${e.message}`);
    } finally { if (h) await h.browser.close(); }
  }
}

/* T9 — weight, axe, named SVGs, and whether the page reads frozen.
 *
 * Four things that can only be measured with the page running, so they are their own command
 * rather than an analysis of a committed JSON. The refresh window is one poll interval plus a
 * second: the renderer refreshes every 20 s and the satellite frames are fetched once for the life
 * of the document, so a window that starts after first paint measures what a wall screen actually
 * costs per day.
 */
async function audit(names) {
  const all = jobs();
  const want = names[0] === 'all' ? all : all.filter(j => names.includes(j.name));
  const axePath = path.join(DESIGN, 'node_modules/axe-core/axe.min.js');
  const haveAxe = fs.existsSync(axePath);
  const rows = [];
  for (const job of want) {
    let h;
    try {
      h = await open(job);
      const bytes = { n: 0, b: 0, paths: {} };
      h.page.on('response', async r => {
        const u = new URL(r.url());
        try {
          const len = +(r.headers()['content-length'] || 0)
            || (await r.body().catch(() => Buffer.alloc(0))).length;
          bytes.n++; bytes.b += len;
          bytes.paths[u.pathname] = (bytes.paths[u.pathname] || 0) + len;
        } catch (e) { /* a response the browser dropped is not a measurement */ }
      });
      await h.page.waitForTimeout(21000);              // one refresh at the renderer's own cadence

      const svg = await h.page.evaluate(() => {
        const all = [...document.querySelectorAll('svg')];
        const bad = all.filter(s => s.getAttribute('aria-hidden') !== 'true'
          && !s.getAttribute('aria-label') && !s.querySelector(':scope > title')
          && !s.closest('[aria-hidden="true"]'));
        return { all: all.length, unnamed: bad.length };
      });
      /* Reduced motion is set on the context, so this asks what is still moving under it — CSS
       * animations and transitions with a non-zero duration, and SMIL, which no media query can
       * reach and which is why the layer's rule is "deleted, not tuned". */
      const motion = await h.page.evaluate(() => {
        let css = 0;
        for (const el of document.querySelectorAll('*')) {
          const c = getComputedStyle(el);
          if (c.animationName !== 'none' && parseFloat(c.animationDuration) > 0) css++;
          if (parseFloat(c.transitionDuration) > 0) css++;
        }
        return { css, smil: document.querySelectorAll('animate,animateTransform,animateMotion,set').length };
      });

      let axe = 'not run';
      if (haveAxe) {
        await h.page.addScriptTag({ path: axePath });
        const r = await h.page.evaluate(async () => {
          const res = await window.axe.run(document, { resultTypes: ['violations'] });
          return res.violations.map(v => ({ id: v.id, impact: v.impact, n: v.nodes.length }));
        });
        const bad = r.filter(v => v.impact === 'serious' || v.impact === 'critical');
        axe = bad.length
          ? '**' + bad.map(v => `${v.id} ${v.impact} ×${v.n}`).join('; ') + '**'
          : `0 serious/critical (${r.length} minor/moderate)`;
      }
      const top = Object.entries(bytes.paths).sort((a, b) => b[1] - a[1]).slice(0, 3)
        .map(([p, b]) => `${p} ${(b / 1024).toFixed(0)} kB`).join(', ');
      rows.push([job.name, `${(bytes.b / 1024).toFixed(1)} kB / ${bytes.n} req`, top,
        svg.unnamed ? `**${svg.unnamed} of ${svg.all}**` : `0 of ${svg.all}`,
        motion.css || motion.smil ? `**css ${motion.css}, smil ${motion.smil}**` : '0'
      , axe]);
      console.error(`  ${job.name} audited`);
    } catch (e) {
      rows.push([job.name, 'FAILED', e.message.slice(0, 60), '', '', '']);
    } finally { if (h) await h.browser.close(); }
  }
  console.log('One 21-second window after first paint, which is one refresh at the renderer\'s own '
    + 'cadence. Reduced motion is on, so anything still moving is something the media query cannot '
    + 'reach.\n');
  console.log(tbl(['render', 'per refresh', 'the heaviest of it', 'SVGs unnamed', 'still moving',
    'axe serious/critical'], rows));
}

const A = { grid: aGrid, spacing: () => aSpacing(true), rhythm: aRhythm, lines: aLines,
  align: aAlign, type: aType, headings: aHeadings, order: aOrder, dist: aDist, wall: aWall,
  dom: aDom, anatomy: aAnatomy, components: aComponents, stack: aStack,
  targets: aTargets };

const [cmd, ...rest] = process.argv.slice(2);
if (cmd === 'render') await render(rest.length ? rest : ['all']);
else if (cmd === 'steps') await steps();
else if (cmd === 'stall') await stall(rest[0] || 'now_populated_1440');
else if (cmd === 'sheets') await sheets();
else if (cmd === 'header') await header();
else if (cmd === 'targets') aTargets();
else if (cmd === 'audit') await audit(rest.length ? rest : ['all']);
else if (cmd === 'shots') await shots(rest.length ? rest : ['all']);
else if (cmd === 'analyse') { const f = A[rest[0]]; if (!f) { console.error('analyse: ' + Object.keys(A).join(' ')); process.exit(2); } f(); }
else if (cmd === 'list') jobs().forEach(j => console.log(j.name));
else { console.error('usage: measure.mjs render|shots|steps|stall|sheets|header|targets|audit|analyse|list');
  process.exit(2); }
