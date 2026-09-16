#!/usr/bin/env bash
# The visual gate for the production dashboard: the same script that measured Phase 1, run against
# app/static with the committed fixture, and compared against numbers THIS rig measured against
# THIS page — never against docs/design/REDESIGN_2026-09_ground.md's Phase 1 numbers, which were
# captured against a container nobody can reconstruct and are not comparable to a hermetic render.
#
#   bash tests/visual/gate.sh
#
# Not in tests/all: Playwright lives in planetai-design's node_modules, not this repo's, so `make
# test` must not depend on it. Run this before shipping instead.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

# path.resolve(ROOT, PAI_DESIGN_REPO) in measure.mjs now resolves a relative PAI_DESIGN_REPO for
# that script — createRequire() there demands an absolute path and throws on a relative one, which
# used to be gate.sh's whole failure. This line does the same resolution here, so the -d check
# below (which runs before measure.mjs is ever started) checks the same directory measure.mjs will
# actually use, and this file is correct on its own rather than depending on the callee's fix.
DESIGN="$(cd "${PAI_DESIGN_REPO:-../planetai-design}" 2>/dev/null && pwd)" || DESIGN=""
[ -n "$DESIGN" ] && [ -d "$DESIGN/node_modules/playwright" ] || { echo "  playwright is not in ${PAI_DESIGN_REPO:-../planetai-design} (resolved: ${DESIGN:-<not found>}); npm install there"; exit 2; }

OUT="${PAI_OUT:-/tmp/pai-gate}"; mkdir -p "$OUT"
export PAI_STATIC="$PWD/app/static" PAI_OUT="$OUT" PAI_DESIGN_REPO="$DESIGN" PAI_Q="?fixture=node1-2026-09-06"

# now_populated_390/1440: everything T1-T5 below is read off these two. wall_populated_1920_dark:
# T7 and the 1,080 px check. All three go through serveNodeAPI() in measure.mjs — no node, no
# container, no network; see that function's own comment for what changed on 2026-09 and why.
node tests/visual/measure.mjs render now_populated_1440 now_populated_390 >/dev/null
PAI_Q="?fixture=node1-2026-09-06&view=wall" node tests/visual/measure.mjs render wall_populated_1920_dark >/dev/null
node tests/visual/measure.mjs shots now_populated_1440 now_populated_390 wall_populated_1920_dark >/dev/null

node - <<'JS'
const fs = require('fs'), out = process.env.PAI_OUT;
const j = n => JSON.parse(fs.readFileSync(`${out}/${n}.json`, 'utf8'));
const fails = [];

// T1's five legs (sentence, numeral, state, ask, as-of), read the same way measure.mjs's own
// `targets` command reads them — see ROLES and role() there. A target with no script behind it is
// an opinion, so this duplicates that script's selectors rather than re-deciding what T1 means.
const ROLES = {
  sentence: ['[data-component="sentence"]', '[data-role="sentence"]', '.hero p.big', '.wall p.big'],
  numeral: ['[data-role="numeral"]', 'b.mono'],
  state: ['[data-component="kicker"] .state', '[data-role="state"]', '.hero .k .state', '.wall .k .state'],
  ask: ['[data-component="askStrip"]', '[data-role="ask"]', '.askstrip'],
  asof: ['[data-role="asof"]', '.asof', '#headprov .asof', '.wall .foot'],
};
function has(e, cls) { return (e.cls || '').split(/\s+/).includes(cls); }
function matches(e, sel) {
  const M = sel.match(/^\[data-component="([^"]+)"\](?:\s+(.+))?$/);
  if (M) return M[2] ? false : e.dc === M[1];
  const R = sel.match(/^\[data-role="([^"]+)"\]$/);
  if (R) return e.drole === R[1];
  const parts = sel.trim().split(/\s+/), last = parts[parts.length - 1];
  const bits = last.match(/^([a-z0-9]+)?((?:[.#][A-Za-z0-9_-]+)*)$/i);
  if (!bits) throw new Error('gate.sh: ROLES selector not supported: ' + sel);
  if (parts.length > 1 && !bits[2]) return false;
  if (bits[1] && e.tag !== bits[1].toUpperCase()) return false;
  for (const b of (bits[2] || '').match(/[.#][A-Za-z0-9_-]+/g) || []) {
    if (b[0] === '#' && e.id !== b.slice(1)) return false;
    if (b[0] === '.' && !has(e, b.slice(1))) return false;
  }
  return true;
}
const inFold = (e, d) => e.y < d.doc.vh && e.y + e.h > 0;

// The empty share of the first viewport — measure.mjs's own T2 "lit" reading (aTargets(), the
// `grids.lit` loop): a 4 px grid over the fold, a cell marked full when it sits inside anything
// that carries text, a mark, a sign, an image or a control. Duplicated rather than imported
// because this file has to run standalone from `node -`; the grid math itself is copied verbatim.
function emptyShare(d) {
  const w = d.doc.vw, vh = d.doc.vh, G = 4;
  const gw = Math.ceil(w / G), gh = Math.ceil(vh / G), grid = new Uint8Array(gw * gh);
  const mark = (x, y, ww, hh) => {
    for (let gy = Math.max(0, Math.floor(y / G)); gy < Math.min(gh, Math.ceil((y + hh) / G)); gy++)
      for (let gx = Math.max(0, Math.floor(x / G)); gx < Math.min(gw, Math.ceil((x + ww) / G)); gx++)
        grid[gy * gw + gx] = 1;
  };
  for (const e of d.els) {
    if (e.y >= vh || !(e.hasText || e.kind === 'media' || e.kind === 'control')) continue;
    mark(e.x, e.y, e.w, e.h);
  }
  return 100 * (1 - grid.reduce((a, b) => a + b, 0) / (gw * gh));
}

function t1legs(d) {
  const hit = name => d.els.filter(e => ROLES[name].some(sel => matches(e, sel)));
  return {
    sentence: hit('sentence').some(e => inFold(e, d)),
    numeral: hit('numeral').some(e => inFold(e, d)),
    state: hit('state').some(e => inFold(e, d)),
    ask: hit('ask').some(e => inFold(e, d) && e.h > 0),
    asof: hit('asof').some(e => inFold(e, d)),
  };
}

// Recorded by running this gate against the page as committed at 46018b0 (Task 8). Never
// docs/design/REDESIGN_2026-09_ground.md's Phase 1 numbers — those were measured against a
// prototype container nobody can reconstruct, and are not comparable to a hermetic render of the
// production page.
//   now_populated_390:  orphanNums 0, orphanComps 0, page height 8267 px, empty share 37.7%
//   now_populated_1440: orphanNums 0, orphanComps 0, page height 5261 px, empty share 61.3%
// HEIGHT_MARGIN (8%): a page that grew a whole section would clear it; a few px of font-metric
// drift between machines will not. EMPTY_MARGIN (+6 points): emptiness creeping up by a couple of
// points is layout noise (a line wrapping differently at a slightly different font); +6 points is
// roughly a whole section's worth of ground going unused, which is the H1 complaint this redesign
// exists to answer — a regression there is worth failing on, and a couple of rounding points is not.
const HEIGHT_SHIPPED = { now_populated_390: 8267, now_populated_1440: 5261 };
const EMPTY_SHIPPED = { now_populated_390: 37.7, now_populated_1440: 61.3 };
const HEIGHT_MARGIN = 1.08, EMPTY_MARGIN = 6;

for (const n of ['now_populated_1440', 'now_populated_390']) {
  const d = j(n);
  const legs = t1legs(d);
  const missing = Object.entries(legs).filter(([, ok]) => !ok).map(([k]) => k);
  if (missing.length) fails.push(`${n}: T1 leg(s) missing: ${missing.join(', ')}`);

  const orphanNums = d.els.filter(e => e.dnum && !e.dcmp).length;
  const ids = new Set(d.els.map(e => e.id).filter(Boolean));
  const inbound = new Set(d.els.filter(e => e.dref && ids.has(e.dref)).map(e => e.dref));
  const orphanComps = d.els.filter(e => e.dc && !(e.dref && ids.has(e.dref)) && !inbound.has(e.id)).length;
  const broken = (d.lines || []).map(x => typeof x === 'string' ? x : x.text || '').filter(x => /did not render|has nothing here yet/.test(x));
  if (orphanNums) fails.push(`${n}: ${orphanNums} numerals with no comparison`);
  if (orphanComps) fails.push(`${n}: ${orphanComps} components with no link in or out`);
  if (broken.length) fails.push(`${n}: ${broken.join(' | ')}`);

  const cap = HEIGHT_SHIPPED[n] * HEIGHT_MARGIN;
  if (d.doc.h > cap) fails.push(`${n}: page is ${d.doc.h} px, more than ${HEIGHT_MARGIN}x the ${HEIGHT_SHIPPED[n]} px this shipped at`);

  const empty = emptyShare(d);
  if (empty > EMPTY_SHIPPED[n] + EMPTY_MARGIN)
    fails.push(`${n}: ${empty.toFixed(1)}% empty, more than ${EMPTY_MARGIN} points over the ${EMPTY_SHIPPED[n]}% this shipped at`);
}

const w = j('wall_populated_1920_dark');
if (w.doc.h > 1080) fails.push(`wall is ${w.doc.h} px on a 1,080 px screen`);

for (const f of fails) console.log('FAIL', f);
console.log(fails.length ? `${fails.length} regression(s)` : 'ok');
process.exit(fails.length ? 1 : 0);
JS
