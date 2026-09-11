#!/usr/bin/env node
/* Visual baselines for the node dashboard. Not run by `make lint`: it needs a browser.
 *
 *   python3 tools/shots.py            # builds the bundles, then calls this
 *
 * The page is loaded over http:// from a routed origin rather than file://, because the renderer
 * asks for `/static/<name>` and `/issues/fixtures/<name>` and both of those are absolute. Nothing
 * is served from a port: every request is fulfilled by playwright from disk, so two sessions
 * running this at once cannot collide, and there is no node to stand up and no database behind it.
 *
 * The route mirrors app/main.py's COMPANIONS exactly, including its refusals: `/static/<name>`
 * takes a NAME, so `/static/fonts/jetbrains-mono-latin.woff2` 404s here as it does on a node. That
 * is the one dead reference this project has decided to live with, and a baseline that quietly
 * resolved it would be a baseline of a page no household has.
 */
// playwright lives in the sibling planetai-design checkout, not here: a node's tarball has no
// node_modules and is not going to grow one for a tool no household runs. ESM resolves packages
// from the importing file's own tree and ignores NODE_PATH, so the path is passed in.
const { chromium } = await import(process.env.PLAYWRIGHT_ENTRY);
import { readFileSync, existsSync, mkdirSync, writeFileSync, readdirSync } from 'node:fs';
import { extname, basename } from 'node:path';

const [BUNDLES, OUT, ROOT] = process.argv.slice(2);
const STATIC = `${ROOT}/app/static`;
const ORIGIN = 'http://node.invalid';
const WIDTHS = [375, 768, 1440, 1920];

const TYPES = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css',
                '.svg': 'image/svg+xml', '.json': 'application/json', '.woff2': 'font/woff2',
                '.ttf': 'font/ttf', '.txt': 'text/plain' };

// COMPANIONS, as app/main.py has it: a flat name, resolved in app/static and then in its fonts/
// subdirectory. Anything with a slash in it is not a name and is refused.
function companion(name) {
  if (name.includes('/')) return null;
  for (const p of [`${STATIC}/${name}`, `${STATIC}/fonts/${name}`]) if (existsSync(p)) return p;
  return null;
}

const browser = await chromium.launch();
const rows = [];
let bad = 0;

for (const f of readdirSync(BUNDLES).filter(n => n.endsWith('.json'))) {
  const fixture = basename(f, '.json');
  const body = readFileSync(`${BUNDLES}/${f}`, 'utf8');
  for (const view of ['now', 'wall']) {
    for (const width of WIDTHS) {
      // reducedMotion on every pass: the satellite loop is the only thing that moves, and a shot
      // taken mid-cut is a shot of nothing. The loop itself is proven by tests, not by a picture.
      const ctx = await browser.newContext({ viewport: { width, height: 1100 },
                                             deviceScaleFactor: 1, reducedMotion: 'reduce' });
      const page = await ctx.newPage();
      const errors = [];
      page.on('pageerror', e => errors.push(String(e)));
      page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

      const missed = [];
      await page.route('**/*', route => {
        const url = new URL(route.request().url());
        if (url.origin !== ORIGIN) return route.abort();
        if (url.pathname === '/') {
          return route.fulfill({ contentType: 'text/html', body: readFileSync(`${STATIC}/index.html`, 'utf8') });
        }
        if (url.pathname === `/issues/fixtures/${fixture}`) {
          return route.fulfill({ contentType: 'application/json', body });
        }
        if (url.pathname.startsWith('/static/')) {
          const p = companion(url.pathname.slice('/static/'.length));
          if (!p) { missed.push(url.pathname); return route.fulfill({ status: 404, body: 'not a name this node serves' }); }
          return route.fulfill({ contentType: TYPES[extname(p)] || 'application/octet-stream', body: readFileSync(p) });
        }
        // Everything else is a request the fixture path is not supposed to make. Record it: a
        // renderer that reaches the network with ?fixture= set has stopped being renderable from a
        // fixture alone, which is the property that makes a design round possible.
        missed.push(url.pathname);
        return route.fulfill({ status: 404, body: 'no' });
      });

      // `&theme=dark` is how a wall screen boots (dashboard.js's boot()), so the wall is reached the
      // way a wall reaches it rather than by clicking the nav after the fact — which raced with
      // boot() and produced a page with two views' DOM in it.
      await page.goto(`${ORIGIN}/?fixture=${fixture}${view === 'wall' ? '&theme=dark' : ''}`, { waitUntil: 'load' });
      await page.waitForSelector('[data-component]', { timeout: 10000 }).catch(() => {});
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(250);

      const seen = await page.evaluate(() => ({
        components: [...document.querySelectorAll('[data-component]')].map(e => e.dataset.component),
        broken: [...document.querySelectorAll('[data-component][data-error="1"]')].map(e => e.dataset.component),
        bands: [...document.querySelectorAll('[data-band]')].map(e => e.dataset.band),
        sideways: document.documentElement.scrollWidth > window.innerWidth + 1,
        height: document.documentElement.scrollHeight,
      }));
      // jpeg, like the shots already in docs/design/shots: these are committed so a review has
      // something to look at, and a full-page PNG of a 9800px page is megabytes in a tarball that
      // goes to households. The assertions above are what is actually checked; the picture is for
      // a person.
      const name = `${fixture}-${view}-${width}.jpg`;
      mkdirSync(OUT, { recursive: true });
      await page.screenshot({ path: `${OUT}/${name}`, fullPage: true, type: 'jpeg', quality: 72 });

      // The mono is expected to 404 at its nested path, by decision (docs/HANDOFF_issues.md §2).
      const unexpected = missed.filter(p => p !== '/static/fonts/jetbrains-mono-latin.woff2');
      const ok = !errors.length && !seen.broken.length && !seen.sideways && !unexpected.length;
      if (!ok) bad++;
      rows.push({ name, ok, height: seen.height, sideways: seen.sideways,
                  components: [...new Set(seen.components)].sort(), bands: seen.bands,
                  broken: seen.broken, errors, unexpected });
      console.log(`  ${ok ? '✓' : '✗'} ${name.padEnd(34)} ${String(seen.height).padStart(5)}px tall  `
        + `${[...new Set(seen.components)].length} components`
        + (seen.sideways ? '  SCROLLS SIDEWAYS' : '')
        + (seen.broken.length ? `  BROKEN: ${seen.broken.join(',')}` : '')
        + (unexpected.length ? `  FETCHED: ${[...new Set(unexpected)].join(',')}` : '')
        + (errors.length ? `  ERROR: ${errors[0].slice(0, 90)}` : ''));
      await ctx.close();
    }
  }
}
await browser.close();
writeFileSync(`${OUT}/shots.json`, JSON.stringify(rows, null, 2) + '\n');
console.log(`\n  ${rows.length} shots in ${OUT}, ${bad} with something wrong`);
process.exit(bad ? 1 : 0);
