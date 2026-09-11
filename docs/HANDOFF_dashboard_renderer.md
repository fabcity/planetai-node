# Handoff: the dashboard as a modular renderer (Release 2 of prompt 5b), mid-flight

11 September 2026. Branch `the-dashboard-draws`, worktree `planetai-node-dashboard/`.

**This branch does not pass `make test`, and its last commit says so in its subject line.** Two
suites fail, both for the same reason: the page was replaced and parts of it have not been ported
yet. The list is exact and short, and it is in "What is left" below. Do not merge this until it is
green; do work from it rather than starting again, because the hard parts are done.

Release 1 (`GET /issues`, the four issue declarations, the engine) shipped in **v0.44** and is live
on node #1. Read `docs/HANDOFF_issues.md` first — it carries the information model, the five things
the original brief had wrong, and the decisions this release is built on.

## Where to stand

```bash
cd "planetai-node-dashboard"          # a worktree; the main checkout has another session in it
git log --oneline origin/main..HEAD   # four commits, then one WIP
bash tests/all                        # 29 of 31, and the two failures are below
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

## What is left

Two suites are red. Everything below is *unported surface*, not a bug.

**`tests/test_shipped.py`** — these strings are gone from the page and the features behind them have
not been rebuilt:

| missing | what to build |
|---|---|
| `data-card="trust"`, `Every sensor reported all week`, `still gathering its first week` | the **trust card**. §2.3: trust findings sit in the place band, beside the sensors they doubt. `/trust` is not fetched yet. Node #1 has a live example: `sc-19874` at `coverage_7d: 41`. |
| `function drawRing(` | the **ring card**. Decided: the Stack owns "the street"; this card shows the ring's *shape* — lowest, p25, p75, highest, who, how far — and **not** a second median. Reads `/nearby`. |
| `function drawForecast(` | the **forecast strip**. `/forecast` is empty on node #1 until `FORECAST_BMKG_ADM4` is set. |
| `baliairdispatch.com`, `api.bmkg.go.id`, `open-meteo.com` | the **attribution lines** each pack requires. They belong on the bands that use those sources and in Figures. |
| `s.meta&&s.meta.url` | a sensor card links to its own kit's page where the source gives one. |
| `h.cell?h.cell.caption:''` | a literal-match artefact; the cell stamp *is* rendered. Reword the assertion rather than the code. |

**`tests/test_dashboard.py`** — tests the MAD fence by lifting it out of `index.html` and running it
in node. **The fence moved to the node in Release 1** (`app/issues/engine.py: fenced_median`) and is
tested by `tests/test_issues_engine.py`. Repoint this suite at the engine, keeping its docstring:
the reasoning about Tukey failing at three stations is the valuable part.

~~**2.6** `check_theme.py`~~ **done.** It holds `app/static/planetai-theme.css`, `signs.svg` and
`kilometre-cells.json` to the sibling design checkout byte for byte, forgives the one `src:` line by
decision and nothing else, and is blocking in `make lint`. The old report-only fixture under
`docs/design/` is gone. Still open: **2.7** visual baselines with Playwright. **2.8** docs and
CHANGELOG. **2.9** prove, screenshot, hold for Tomas.

## Decisions already taken — do not reopen

1. **The Stack owns "the street."** The ring card shows the ring's shape. On live data the two read
   14.6 and 13.9 and both said "the street", which is what this settles.
2. **`/static/{name}` takes a name, not a path.** The six renderer files are on `COMPANIONS`.
   `planetai-theme.css` declares `fonts/jetbrains-mono-latin.woff2`, a nested path that cannot
   match, so **that one request 404s by decision** — `dashboard.css` declares the same family at the
   flat name. It is one named pair in `check_ui.py`'s `DEAD_BY_DECISION`. **Do not widen it**, and
   `check_theme` must forgive exactly that line and no other.
3. **Both satellite records ship.** `/earth/year.png` is the node's own AlphaEarth layer (`model`,
   and the card says "Not a photograph"); `/earth/frame.png?source=sentinel` is imagery (`partial`,
   with its credits). `/earth`'s `imagery` key lists the years. Never merge the two lists.
4. **`ANATOMY` stays in the page.** It could move into `/issues`; do not. The page must stay
   renderable from a fixture alone, which is what makes a design round possible.

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

Nothing has been rendered in a browser. The page parses, `make lint` passes, 29 of 31 suites pass,
and every assertion above is static. **No screenshot exists, nothing has been seen by a person, and
§2.9's rule stands: nothing reaches a tester before Tomas looks.** The Bahasa and Spanish in
`WORDS` and in `app/issues/*.yml` are assistant-written; PR #1 (`es-messages`) is the review channel.
