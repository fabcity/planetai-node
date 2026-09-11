# Handoff: the dashboard as a modular renderer (Release 2 of prompt 5b)

11 September 2026. Branch `the-dashboard-draws`, worktree `planetai-node-dashboard/`.

**`bash tests/all` is 31 of 31 and `make lint` passes.** The page has been rendered in a browser —
`docs/design/shots/` — and **nothing has been seen by a person other than Tomas, and nothing has
reached a beta tester.** §2.9's rule stands.

What is left is at the bottom, under "Still open".

Release 1 (`GET /issues`, the four issue declarations, the engine) shipped in **v0.44** and is live
on node #1. Read `docs/HANDOFF_issues.md` first — it carries the information model, the five things
the original brief had wrong, and the decisions this release is built on.

## Where to stand

```bash
cd "planetai-node-dashboard"          # a worktree; the main checkout has another session in it
git log --oneline origin/main..HEAD
bash tests/all                        # 31 of 31
make lint                             # includes check_theme now, and it fails rather than reports
python3 tools/shots.py                # renders every fixture, four widths, Now and the wall
```

`planetai-node/` (the main checkout) is a **different session's** working tree — the earth-cache
task. Leave it alone. If you need another tree, make another worktree.

## What is done

**The three files exist and the page is three files.**

| file | what |
|---|---|
| `app/static/index.html` | a skeleton: head, header, four view shells, mount points, Arrange bar, one `<script>`. No logic, no style. |
| `app/static/dashboard.css` | 283 lines, ported from the prototype, re-scoped from `.pai` to the node's `html[data-theme]`. No data URI, no CDN. The only literals are the four page-local tokens the layer does not name (`--mute --dim --hair --raise`). |
| `app/static/dashboard.js` | ~1,050 lines. `snapshot()` · `COMPONENTS` (20) · `COMPOSITES` (5) · `ANATOMY` · `layout()` · `render()` · `ctx`. |

**The contract holds.** `snapshot()` is the only fetcher. `render()` is the only DOM writer. Every
component is `(data, ctx) => string`, carries `data-component`, draws its own empty state, and runs
inside `piece()`'s guard — a throw draws that component's own box and names itself in the console,
and nothing else goes dark. That is improvement-plan PR 11's guarantee, structurally, so **PR 11
should be skipped**; PR 5's three fixes are carried here (`act()` returns on Cancel, `esc()` handles
`'`, Reset writes the same empty `UI_LAYOUT` that Done writes).

**The frozen layer is on the node.** `planetai-theme.css` byte-identical to the design repo;
`signs.svg` and `kilometre-cells.json` copied; `tokens.css` **adapted** and saying so at the top (its
Google Fonts `@import` removed, its four `@font-face` paths flattened). Funnel Sans, Figtree and
JetBrains Mono are self-hosted with their SIL OFL licences beside them and named in `NOTICE`.
**Circular Std is deliberately absent** — a commercial Lineto face that must not go into a public
tarball.

**`check_ui.py` learned the three files, and four of its rules were dead.** Worth knowing, because
they had been passing for weeks while checking nothing:

- rules 2/5/6/7 keyed on `--red` / `--blue` / `--green` / `--orange`, tokens the layer replaced with
  `--signal-worse` / `--cells` / `--rings` / `--satellite-only`. They could not have fired again.
- the orange rule exempts a line that mentions the satellite — and the token is *called*
  `--satellite-only`, so it exempted every use of itself.
- `BODY` was "whatever follows `</style>`", and the skeleton has no inline style, which silently
  switched off every rule that reads markup.
- rule 8 collected only refs already under `static/`, so a reference that *dropped* the prefix
  dropped out of the check with it. It also never looked at the three `<link>` hrefs, nor at
  anything the renderer writes — which is now where every image comes from.

New **rule 9** covers the stylesheets: a `url()` naming a file nothing serves, or an `@import` to a
CDN. `tokens.css` arrived with one of each. **Sixteen break-on-purpose gates fire**
(`tests/test_check_ui.py`).

## What Release 2 added after the WIP commit

**The five pieces the skeleton had lost are back, as components.**

| component | where it sits | what it reads |
|---|---|---|
| `trustCard` | the place band, beside the sensors it doubts (§2.3) | `/trust` |
| `ring` (`drawRing`) | the air band | `/nearby` |
| `stations` (`drawStations`) | the air band, under the ring | `/nearby` |
| `forecast` (`drawForecast`) | heat or air, whichever this place declared first | `/forecast` |
| the kits under each source card | every sensed band's Sources | `/sensors` |

`drawRing` and `drawForecast` keep their old top-level names: `tests/test_shipped.py` has asserted
`function drawRing(` since v0.30 and a method on an object literal is invisible to it. They are
registered in `COMPONENTS` and obey the same contract as everything else. The ring and the forecast
are reached through `COMPOSITES.ringCards` / `COMPOSITES.forecastStrip`, which gate on the issue the
band is about — the same shape as `satellites`, which is land's.

**The ring card shows the shape and no median**, per the decision below. Its axis runs lowest to
highest with nothing trimming it: the fence moved to the node in Release 1, all four numbers are in
the sentence underneath, and one station at 152 squashing the box against the left edge is the true
shape of that ring rather than a picture to be corrected.

**Attribution comes from the endpoint** (`/nearby.attribution`, `/forecast.attribution`) with the
literal as the fallback a node that has never fetched shows. Both archives are named on the cards
that use them.

**A kit links to its own page where `/sensors` gives one.** An account kit has a `url` in its meta;
a public station never does, and `/sensors` strips the key entirely for a reader the node does not
trust — so the link appears exactly where somebody can open it.

**Sources is still one card per distance**, carrying the value the node computed, with the kits
behind it listed under it. Not one card per sensor with its own number: `engine._cell` keeps the
sensor ids and not their values, and working a per-sensor figure out in the page would be the page
computing again. §3 wants one card per sensor; that lands when `/issues` publishes the per-sensor
values, and the names under each card become their headings.

**`tests/test_dashboard.py` calls the engine.** It used to lift the fence out of `index.html` with a
regular expression and run it in node. Its docstring is kept — the reasoning about Tukey failing at
three stations is the valuable part — and it gained the other half: a `mad =` or a `fence =` in
`dashboard.js` fails the suite.

**`tools/check_theme.py` is a gate.** It holds `planetai-theme.css`, `signs.svg` and
`kilometre-cells.json` to the sibling design checkout line by line, forgives the one `src:` line by
decision (normalised on the basename, reported) and nothing else, and is blocking in `make lint`.
Six break-on-purpose cases. The design repo is absent on a node and in CI, where it prints one line
and exits 0.

**`tools/shots.py` renders the page.** Every fixture, Now and the wall, 375 · 768 · 1440 · 1920. It
fails on a page error, a component that drew its guard box, a page that scrolls sideways, or a
request the fixture path should not have made. No node, no database, no port: playwright fulfils
every request from disk, mirroring `COMPANIONS` including its refusals. Shots are JPEG in
`docs/design/shots/` and are excluded from the tester tarball along with the tool.

### What the first render found

Eight shots, and the first run was red on all eight. Worth reading, because four of the five were
invisible to every static gate in the repo:

1. **Every paragraph rendered in the browser's default serif, on white.** `tokens.css` puts the base
   typography on `body.fc`, and this body carries no `fc` class on purpose: that rule pins the
   background and the text colour to fixed Fab City values the wall's dark register could never
   flip, and its `.fc a` outranks the page's link colour. So nothing set a body font, a background
   or a colour at all. `dashboard.css` declares the base in the programme layer's own roles now.
2. **The ground drew at 900×600 in the corner.** The rules said `.hero .bg svg`, `.wall .bg svg`,
   `.plan>svg`; the renderer writes an `<img>` — one cached request instead of 4 kB in every
   document. The plan's copy pushed the page sideways at 375 and 768.
3. **Figures pushed the page sideways at 375.** It scrolls inside its own box now.
4. **`?fixture=` still fetched `/settings`**, which is the one request that stopped the page being
   renderable from a fixture alone — the property a design round depends on.
5. **The wall carried the header**: five buttons on a screen across a room, against R6. Gone, with
   one `NOW` exit in its place, because the wall is reachable from the nav and a laptop that got
   there had no way back. The wall's kicker ran its words together (`HEATACT· AN OPEN ASK`).

Also: the trust card said "No local sensor yet." and "Every sensor reported all week." at once, and
the four new eyebrows carried full stops that no other eyebrow on the page has.

## Proven on `pai-clean`, 11 September

The branch rsynced into `~/planetai` in the lima VM (excluding `.env`, `VERSION`, `data/`,
`config/`, `backups/`, `out/`, `exports/`), `docker compose up -d --build app`, at
`v0.44.2-8-g067a6d7`. Barcelona coordinates, Open-Meteo and CAMS, no sensors of its own — so this
proves the machinery, not the numbers.

**Every route the page needs answers, and exactly one 404s:**

```
/  /static/{dashboard.js,dashboard.css,planetai-theme.css,tokens.css,signs.svg,
   kilometre-cells.json,node-ground.svg,jetbrains-mono-latin.woff2}      200
/issues /issues/fixtures /health /trust /nearby /forecast /sensors /earth /rho   200
/static/fonts/jetbrains-mono-latin.woff2                                 404   ← by decision
```

And in a browser, against the running node — `python3 tools/shots.py --url http://127.0.0.1:8080
--token <admin>`, nine shots in `docs/design/shots/live-*.jpg`:

- **no token, SHARE_LEVEL=off**: the page draws the node's own sentence about why it is not sharing,
  and not a blank. Nine endpoints refuse; the browser logs each refusal, which is a refusal being
  answered rather than an error.
- **with a token, Now and the wall, 375 · 768 · 1440 · 1920**: 18 and 19 components, no component
  in its guard box, no sideways scroll, no console error, and no non-2xx request at all. The mono's
  nested path is never even requested: `dashboard.css` declares the same family at the flat name
  first, so the browser resolves it there and never reaches the 404.

**The live render found one more thing**, and it is fixed: the hero drew a red `17` next to the
words `AIR QUIET · NOTHING TO SAY`. Red is "a signal that crossed a line", and the page was deciding
that by comparing two numbers it happened to have — a model's point sample against the WHO 24-hour
line — while the node itself was calling the issue quiet. On a model-only node that is every
evening. The numeral and the stack column are red only when the node's own state is `act` or
`notable` now; `scale` and `day` still mark every value past the line, because there the line is
drawn beside the mark.

## Still open

- **No beta tester has seen anything, and nothing has run on a real node.** `pai-clean` is a VM with
  no sensors: the room, the yard and the ring are all empty there and the page is region-only.
- **The committed fixture renders three cards empty.** `node1-2026-09-06.json` predates
  `planetai snapshot` and carries no `/nearby`, `/forecast`, `/trust` or `/sensors`, so the ring,
  the stations, the forecast and the trust card come out as their empty states — which is worth a
  picture, but is not the populated page. `planetai snapshot` answers all twelve endpoints; a
  capture taken with it renders the whole thing. **Committing a live capture of somebody's house is
  Tomas's call, not a session's.**
- **The ledger prints the alert's emoji.** §3: the emoji are a Telegram affordance and stay there.
- **The satellite loop is still ~7 MB** — see below. Not solved.
- **`app/main.py`'s COMPANIONS comment says the three `.css` files are copied from planetai-design
  and held there by `check_theme`.** Only `planetai-theme.css` is: `tokens.css` is adapted and
  `dashboard.css` is ours. `tokens.css` says so accurately at its own top. Left alone because
  Release 2 touches no `.py` under `app/`; fix it when something else opens that file.
- **2.6 · 2.7 · 2.8 are done.** `check_theme`, the baselines, and this file plus the CHANGELOG and
  `docs/DEVELOPING.md`.

## Things that will bite

- **The satellite loop is ~7 MB.** Nine AlphaEarth frames at ~780 kB, four Sentinel at ~320 kB.
  §2.7 budgets 60 kB per refresh. It must load once and animate from memory; a kiosk that reloads
  pays it again. This is not solved yet.
- **`main` moves roughly hourly.** It took four merges during this session (#25–#29). Rebase before
  you start and again before you open anything.
- **Two other sessions are live** in this repo. `tests/all` writes `/tmp/stub/httpx.py` at the start
  of every run, so two concurrent runs race on it: a suite that fails once and passes on a retry is
  that, not your diff.
- **Node #1 has a yard now**, so the Stack fills all four columns where the prototype shows three,
  and `{cmp}` can reach three clauses. The hero's 26ch/52ch budget has not been checked against that.

## Verified, and not

**Verified:** `bash tests/all` is 31 of 31. `make lint` passes, `check_theme` included. The page
renders in Chromium from the committed fixture at four widths in both views with no page error, no
component falling into its guard, no sideways scroll and no request outside the fixture — eight
JPEGs in `docs/design/shots/`.

**Not verified:** nothing has run on a node or on `pai-clean`. No live data has reached the page —
every number in those shots is the 6 September capture replayed. Nobody but Tomas has looked, and
**nothing reaches a tester before Tomas looks.** The Bahasa and Spanish in `WORDS` and in
`app/issues/*.yml` are assistant-written; PR #1 (`es-messages`) is the review channel.
